"""
WebSocket handler for live keystroke telemetry streaming and anomaly scoring.
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.enrollment import KeystrokeBurst, AnomalyResult
from app.models.session import get_or_create_session, remove_session
from app.features.extractor import extract_features
from app.ml.storage import load_bundle
from app.ml.classifier import score_burst
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


async def _send_json(ws: WebSocket, data: dict) -> bool:
    """Send JSON to the client. Returns False if the send fails."""
    try:
        await ws.send_text(json.dumps(data))
        return True
    except Exception as exc:
        logger.debug("WS send failed: %s", exc)
        return False


@router.websocket("/ws/{user_id}/{session_id}")
async def keystroke_stream(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
) -> None:
    await websocket.accept()
    live = get_or_create_session(session_id, user_id)
    bundle = load_bundle(user_id)

    if bundle is None:
        await _send_json(websocket, {
            "type": "error",
            "message": "No trained model for this user. Complete enrollment first.",
        })
        await websocket.close()
        return

    logger.info("WebSocket connected: user=%s session=%s", user_id, session_id)
    await _send_json(websocket, {"type": "connected", "user_id": user_id, "session_id": session_id})

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, {"type": "error", "message": "invalid JSON"})
                continue

            if payload.get("type") == "ping":
                await _send_json(websocket, {"type": "pong"})
                continue

            if payload.get("type") != "burst":
                continue

            burst_data = payload.get("data", {})
            try:
                burst = KeystrokeBurst(**burst_data)
            except Exception as exc:
                await _send_json(websocket, {"type": "error", "message": str(exc)})
                continue

            # Reject bursts that don't match the authenticated session
            if burst.user_id != user_id or burst.session_id != session_id:
                await _send_json(websocket, {
                    "type": "error",
                    "message": "burst user_id/session_id mismatch",
                })
                continue

            if len(burst.events) < 5:
                continue

            vec, named = extract_features(
                burst.events,
                wpm=burst.wpm,
                error_count=burst.error_count,
                word_count=burst.word_count,
                canonical_digraphs=bundle.canonical_digraphs,
            )

            try:
                anomaly_score = score_burst(bundle, vec)
            except ValueError as exc:
                logger.warning(
                    "Feature dimension mismatch for user=%s: %s", user_id, exc
                )
                await _send_json(websocket, {
                    "type": "error",
                    "message": "Feature vector dimension mismatch — re-enroll to fix.",
                })
                continue

            is_anomalous = anomaly_score > settings.anomaly_threshold
            live.anomaly_history.append(anomaly_score)
            live.burst_count += 1
            live.total_keystrokes += len(burst.events)

            if is_anomalous:
                live.is_flagged = True
                logger.warning(
                    "ANOMALY: user=%s session=%s score=%.3f",
                    user_id, session_id, anomaly_score,
                )

            result = AnomalyResult(
                session_id=session_id,
                user_id=user_id,
                anomaly_score=anomaly_score,
                is_anomalous=is_anomalous,
                threshold=settings.anomaly_threshold,
                feature_snapshot={k: v for k, v in list(named.items())[:15]},
            )

            await _send_json(websocket, {
                "type": "anomaly_score",
                "data": result.model_dump(),
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: user=%s session=%s", user_id, session_id)
    finally:
        remove_session(session_id)
