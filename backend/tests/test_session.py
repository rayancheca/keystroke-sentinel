"""Tests for in-memory session management."""
import pytest
from app.models.session import get_or_create_session, get_session, remove_session


@pytest.fixture(autouse=True)
def clean_sessions():
    yield
    remove_session("test-session-1")
    remove_session("test-session-2")


class TestSessionStore:
    def test_creates_new_session(self) -> None:
        live = get_or_create_session("test-session-1", "user1")
        assert live.session_id == "test-session-1"
        assert live.user_id == "user1"
        assert live.burst_count == 0
        assert live.is_flagged is False

    def test_returns_existing_session(self) -> None:
        s1 = get_or_create_session("test-session-1", "user1")
        s1.burst_count = 5
        s2 = get_or_create_session("test-session-1", "user1")
        assert s2.burst_count == 5

    def test_get_session_missing(self) -> None:
        result = get_session("nonexistent-999")
        assert result is None

    def test_get_session_exists(self) -> None:
        get_or_create_session("test-session-2", "user2")
        result = get_session("test-session-2")
        assert result is not None
        assert result.user_id == "user2"

    def test_remove_session(self) -> None:
        get_or_create_session("test-session-1", "user1")
        remove_session("test-session-1")
        assert get_session("test-session-1") is None

    def test_remove_nonexistent_is_noop(self) -> None:
        remove_session("never-existed-xyz")

    def test_anomaly_history_deque(self) -> None:
        live = get_or_create_session("test-session-1", "user1")
        for i in range(5):
            live.anomaly_history.append(float(i) / 10)
        assert list(live.anomaly_history) == [0.0, 0.1, 0.2, 0.3, 0.4]
