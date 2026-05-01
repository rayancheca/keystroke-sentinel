from dataclasses import dataclass, field
from collections import deque
from typing import Optional
from app.core.config import ANOMALY_HISTORY_LIMIT


@dataclass
class LiveSession:
    session_id: str
    user_id: str
    anomaly_history: deque = field(
        default_factory=lambda: deque(maxlen=ANOMALY_HISTORY_LIMIT)
    )
    is_flagged: bool = False
    burst_count: int = 0
    total_keystrokes: int = 0


# In-memory session store keyed by session_id
_sessions: dict[str, LiveSession] = {}


def get_or_create_session(session_id: str, user_id: str) -> LiveSession:
    if session_id not in _sessions:
        _sessions[session_id] = LiveSession(
            session_id=session_id, user_id=user_id
        )
    return _sessions[session_id]


def get_session(session_id: str) -> Optional[LiveSession]:
    return _sessions.get(session_id)


def remove_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
