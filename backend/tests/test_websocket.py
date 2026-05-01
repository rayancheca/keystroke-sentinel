"""WebSocket integration tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import engine, Base
from app.ml.trainer import buffer_burst, clear_buffer
from app.ml.storage import evict_cache, save_bundle
from app.ml.classifier import train_classifier
from app.models.enrollment import KeystrokeBurst, KeyEvent
import numpy as np
import asyncio


@pytest.fixture(autouse=True)
def sync_setup_db():
    """Synchronous DB setup for use with TestClient (sync context)."""
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_setup())
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _make_enrolled_model(user_id: str) -> None:
    """Create and save a trained model using actual feature extraction."""
    from app.features.extractor import extract_features, build_canonical_digraphs, _digraph_latencies
    evict_cache(user_id)
    clear_buffer(user_id)

    # Generate realistic bursts
    bursts: list[KeystrokeBurst] = []
    keys_text = "the quick brown fox jumps over the lazy dog"
    rng = np.random.default_rng(42)
    for _ in range(15):
        events = []
        t = 0.0
        for k in keys_text:
            dwell = float(rng.normal(80, 10))
            gap = float(rng.normal(100, 20))
            events.append(KeyEvent(key=k, press_time=t, release_time=t + max(20.0, dwell)))
            t += max(20.0, dwell) + max(10.0, gap)
        bursts.append(KeystrokeBurst(
            user_id=user_id, session_id="enroll",
            events=events, wpm=60.0, error_count=0, word_count=8,
        ))

    digraph_maps = [_digraph_latencies(b.events) for b in bursts]
    canonical = build_canonical_digraphs(digraph_maps)

    vecs = []
    for b in bursts:
        vec, _ = extract_features(b.events, wpm=60.0, canonical_digraphs=canonical)
        vecs.append(vec)

    X = np.array(vecs, dtype=np.float64)
    _, named = extract_features(bursts[0].events, canonical_digraphs=canonical)
    feature_names = list(named.keys())

    bundle = train_classifier(X, feature_names, canonical)
    save_bundle(user_id, bundle)


def _make_burst_payload(user_id: str, session_id: str, n: int = 20) -> dict:
    events = []
    t = 0.0
    keys = "the quick brown fox"
    for i in range(n):
        k = keys[i % len(keys)]
        events.append({"key": k, "press_time": t, "release_time": t + 80.0})
        t += 180.0
    return {
        "user_id": user_id,
        "session_id": session_id,
        "events": events,
        "wpm": 60.0,
        "error_count": 0,
        "word_count": 4,
    }


class TestWebSocket:
    def test_rejects_unenrolled_user(self, client: TestClient) -> None:
        evict_cache("unenrolled")
        with client.websocket_connect("/ws/unenrolled/sess1") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "No trained model" in msg["message"]

    def test_connects_enrolled_user(self, client: TestClient) -> None:
        user_id = "ws_user_1"
        _make_enrolled_model(user_id)
        with client.websocket_connect(f"/ws/{user_id}/s1") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"
            assert msg["user_id"] == user_id
        evict_cache(user_id)

    def test_scores_burst(self, client: TestClient) -> None:
        user_id = "ws_user_2"
        session_id = "s2"
        _make_enrolled_model(user_id)
        with client.websocket_connect(f"/ws/{user_id}/{session_id}") as ws:
            ws.receive_json()  # connected frame
            burst = _make_burst_payload(user_id, session_id, n=30)
            ws.send_json({"type": "burst", "data": burst})
            # Wait for anomaly score response
            resp = ws.receive_json()
            assert resp["type"] == "anomaly_score"
            data = resp["data"]
            assert 0.0 <= data["anomaly_score"] <= 1.0
            assert data["user_id"] == user_id
        evict_cache(user_id)

    def test_ping_pong(self, client: TestClient) -> None:
        user_id = "ws_user_3"
        _make_enrolled_model(user_id)
        with client.websocket_connect(f"/ws/{user_id}/s3") as ws:
            ws.receive_json()  # connected
            ws.send_json({"type": "ping"})
            resp = ws.receive_json()
            assert resp["type"] == "pong"
        evict_cache(user_id)

    def test_rejects_mismatched_user_id(self, client: TestClient) -> None:
        user_id = "ws_user_4"
        _make_enrolled_model(user_id)
        with client.websocket_connect(f"/ws/{user_id}/s4") as ws:
            ws.receive_json()  # connected
            burst = _make_burst_payload("other_user", "s4", n=15)
            ws.send_json({"type": "burst", "data": burst})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "mismatch" in resp["message"]
        evict_cache(user_id)

    def test_ignores_small_burst(self, client: TestClient) -> None:
        user_id = "ws_user_5"
        session_id = "s5"
        _make_enrolled_model(user_id)
        with client.websocket_connect(f"/ws/{user_id}/{session_id}") as ws:
            ws.receive_json()  # connected
            burst = _make_burst_payload(user_id, session_id, n=3)
            ws.send_json({"type": "burst", "data": burst})
            ws.send_json({"type": "ping"})
            resp = ws.receive_json()
            # Should get pong, not anomaly_score (burst was too small)
            assert resp["type"] == "pong"
        evict_cache(user_id)
