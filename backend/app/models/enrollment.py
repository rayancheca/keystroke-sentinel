from pydantic import BaseModel, Field
from typing import Optional


class KeyEvent(BaseModel):
    key: str
    press_time: float = Field(..., description="Timestamp of key press (ms)")
    release_time: float = Field(..., description="Timestamp of key release (ms)")


class KeystrokeBurst(BaseModel):
    user_id: str
    session_id: str
    events: list[KeyEvent]
    wpm: float = 0.0
    error_count: int = 0
    word_count: int = 0


class EnrollmentStart(BaseModel):
    user_id: str


class EnrollmentStatus(BaseModel):
    user_id: str
    keystroke_count: int
    is_trained: bool
    accuracy: Optional[float] = None
    progress_pct: float


class TrainingResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    user_id: str
    accuracy: float
    cv_scores: list[float]
    feature_importance: dict[str, float]
    model_path: str


class AnomalyResult(BaseModel):
    session_id: str
    user_id: str
    anomaly_score: float
    is_anomalous: bool
    threshold: float
    feature_snapshot: dict[str, float]
