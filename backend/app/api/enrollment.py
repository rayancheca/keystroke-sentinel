"""
Enrollment REST endpoints.
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models.database import get_session, UserEnrollment
from app.models.enrollment import (
    EnrollmentStart,
    EnrollmentStatus,
    KeystrokeBurst,
    TrainingResult,
)
from app.ml.trainer import buffer_burst, train_user_model, get_keystroke_count
from app.ml.storage import has_model
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(prefix="/enrollment", tags=["enrollment"])


@router.post("/start", response_model=EnrollmentStatus)
async def start_enrollment(
    body: EnrollmentStart,
    db: AsyncSession = Depends(get_session),
) -> EnrollmentStatus:
    result = await db.execute(
        select(UserEnrollment).where(UserEnrollment.user_id == body.user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserEnrollment(user_id=body.user_id)
        db.add(row)
        await db.commit()
        await db.refresh(row)

    return EnrollmentStatus(
        user_id=row.user_id,
        keystroke_count=row.keystroke_count,
        is_trained=bool(row.is_trained),
        accuracy=row.accuracy,
        progress_pct=min(100.0, row.keystroke_count / settings.enrollment_min_keystrokes * 100),
    )


@router.post("/burst")
async def submit_burst(
    burst: KeystrokeBurst,
    db: AsyncSession = Depends(get_session),
) -> dict:
    result = await db.execute(
        select(UserEnrollment).where(UserEnrollment.user_id == burst.user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="User not enrolled. Call /enrollment/start first.")

    total = buffer_burst(burst.user_id, burst)

    row.keystroke_count = total
    row.updated_at = datetime.utcnow()
    await db.commit()

    progress = min(100.0, total / settings.enrollment_min_keystrokes * 100)
    logger.info("Burst received for %s: total=%d, progress=%.1f%%", burst.user_id, total, progress)

    return {
        "user_id": burst.user_id,
        "keystroke_count": total,
        "progress_pct": progress,
        "ready_to_train": total >= settings.enrollment_min_keystrokes,
    }


@router.post("/train/{user_id}", response_model=TrainingResult)
async def train_model(
    user_id: str,
    db: AsyncSession = Depends(get_session),
) -> TrainingResult:
    count = get_keystroke_count(user_id)
    if count < settings.enrollment_min_keystrokes:
        raise HTTPException(
            status_code=400,
            detail=f"Need {settings.enrollment_min_keystrokes} keystrokes; have {count}",
        )

    try:
        bundle = train_user_model(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = await db.execute(
        select(UserEnrollment).where(UserEnrollment.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row:
        row.is_trained = 1
        row.accuracy = bundle.accuracy
        row.model_path = bundle.feature_names[0]
        row.feature_importance = json.dumps(bundle.feature_importance)
        row.updated_at = datetime.utcnow()
        await db.commit()

    return TrainingResult(
        user_id=user_id,
        accuracy=bundle.accuracy,
        cv_scores=bundle.cv_scores,
        feature_importance=bundle.feature_importance,
        model_path=str(user_id) + ".joblib",
    )


@router.get("/status/{user_id}", response_model=EnrollmentStatus)
async def enrollment_status(
    user_id: str,
    db: AsyncSession = Depends(get_session),
) -> EnrollmentStatus:
    result = await db.execute(
        select(UserEnrollment).where(UserEnrollment.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    return EnrollmentStatus(
        user_id=row.user_id,
        keystroke_count=row.keystroke_count,
        is_trained=bool(row.is_trained),
        accuracy=row.accuracy,
        progress_pct=min(100.0, row.keystroke_count / settings.enrollment_min_keystrokes * 100),
    )


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await db.execute(select(UserEnrollment))
    rows = result.scalars().all()
    return [
        {
            "user_id": r.user_id,
            "keystroke_count": r.keystroke_count,
            "is_trained": bool(r.is_trained),
            "accuracy": r.accuracy,
        }
        for r in rows
    ]
