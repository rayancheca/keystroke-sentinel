"""Extended API integration tests covering training endpoint and edge cases."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.database import engine, Base
from app.ml.trainer import buffer_burst, clear_buffer
from app.ml.storage import evict_cache
from app.models.enrollment import KeystrokeBurst, KeyEvent


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def make_burst(user_id: str, n_keys: int = 60) -> KeystrokeBurst:
    events: list[KeyEvent] = []
    t = 0.0
    keys = "the quick brown fox jumps over the lazy dog"
    for i in range(n_keys):
        k = keys[i % len(keys)]
        events.append(KeyEvent(key=k, press_time=t, release_time=t + 80.0))
        t += 180.0
    return KeystrokeBurst(
        user_id=user_id,
        session_id="test-s",
        events=events,
        wpm=60.0,
        error_count=1,
        word_count=8,
    )


class TestListUsers:
    async def test_empty_list(self, client: AsyncClient) -> None:
        resp = await client.get("/enrollment/users")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_created_users(self, client: AsyncClient) -> None:
        await client.post("/enrollment/start", json={"user_id": "frank"})
        await client.post("/enrollment/start", json={"user_id": "grace"})
        resp = await client.get("/enrollment/users")
        user_ids = [u["user_id"] for u in resp.json()]
        assert "frank" in user_ids
        assert "grace" in user_ids


class TestTrainEndpoint:
    async def test_train_insufficient_data(self, client: AsyncClient) -> None:
        await client.post("/enrollment/start", json={"user_id": "henry"})
        resp = await client.post("/enrollment/train/henry")
        assert resp.status_code == 400
        assert "keystrokes" in resp.json()["detail"]

    async def test_train_succeeds_with_enough_data(self, client: AsyncClient) -> None:
        user_id = "iris"
        clear_buffer(user_id)
        evict_cache(user_id)

        await client.post("/enrollment/start", json={"user_id": user_id})

        for _ in range(15):
            burst = make_burst(user_id)
            buffer_burst(user_id, burst)

        from app.models.database import AsyncSessionLocal, UserEnrollment
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserEnrollment).where(UserEnrollment.user_id == user_id)
            )
            row = result.scalar_one()
            row.keystroke_count = 15 * 60
            await db.commit()

        resp = await client.post(f"/enrollment/train/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["accuracy"] > 0.0
        assert len(data["cv_scores"]) == 5
        assert len(data["feature_importance"]) > 0

        clear_buffer(user_id)
        evict_cache(user_id)
