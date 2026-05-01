"""Integration tests for FastAPI enrollment endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.database import init_db, engine, Base


@pytest.fixture(autouse=True)
async def setup_db():
    """Create fresh tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def make_burst_payload(user_id: str, n_keys: int = 50) -> dict:
    events = []
    t = 0.0
    keys = "the quick brown fox jumps"
    for i in range(n_keys):
        key = keys[i % len(keys)]
        events.append({"key": key, "press_time": t, "release_time": t + 80.0})
        t += 180.0
    return {
        "user_id": user_id,
        "session_id": "test-session",
        "events": events,
        "wpm": 60.0,
        "error_count": 0,
        "word_count": 10,
    }


class TestHealth:
    async def test_health_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestEnrollmentStart:
    async def test_creates_user(self, client: AsyncClient) -> None:
        resp = await client.post("/enrollment/start", json={"user_id": "alice"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "alice"
        assert data["keystroke_count"] == 0
        assert data["is_trained"] is False

    async def test_idempotent(self, client: AsyncClient) -> None:
        await client.post("/enrollment/start", json={"user_id": "bob"})
        resp = await client.post("/enrollment/start", json={"user_id": "bob"})
        assert resp.status_code == 200


class TestBurstSubmission:
    async def test_submit_burst(self, client: AsyncClient) -> None:
        await client.post("/enrollment/start", json={"user_id": "charlie"})
        payload = make_burst_payload("charlie", n_keys=50)
        resp = await client.post("/enrollment/burst", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["keystroke_count"] == 50

    async def test_submit_without_enrollment(self, client: AsyncClient) -> None:
        payload = make_burst_payload("nobody", n_keys=10)
        resp = await client.post("/enrollment/burst", json=payload)
        assert resp.status_code == 404

    async def test_progress_accumulates(self, client: AsyncClient) -> None:
        await client.post("/enrollment/start", json={"user_id": "dave"})
        payload = make_burst_payload("dave", n_keys=50)
        await client.post("/enrollment/burst", json=payload)
        await client.post("/enrollment/burst", json=payload)
        resp = await client.post("/enrollment/burst", json=payload)
        assert resp.json()["keystroke_count"] == 150


class TestEnrollmentStatus:
    async def test_status_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/enrollment/status/nobody")
        assert resp.status_code == 404

    async def test_status_found(self, client: AsyncClient) -> None:
        await client.post("/enrollment/start", json={"user_id": "eve"})
        resp = await client.get("/enrollment/status/eve")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "eve"
