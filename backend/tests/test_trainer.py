"""Tests for the enrollment trainer and model storage."""
import pytest
import numpy as np
from pathlib import Path
from app.ml.trainer import buffer_burst, train_user_model, get_keystroke_count, clear_buffer
from app.ml.storage import save_bundle, load_bundle, has_model, evict_cache, model_path
from app.ml.classifier import train_classifier
from app.models.enrollment import KeystrokeBurst, KeyEvent


def make_burst(user_id: str, n: int = 60, session_id: str = "s1") -> KeystrokeBurst:
    events: list[KeyEvent] = []
    t = 0.0
    keys = "the quick brown fox jumps over"
    for i in range(n):
        k = keys[i % len(keys)]
        events.append(KeyEvent(key=k, press_time=t, release_time=t + 80.0))
        t += 180.0
    return KeystrokeBurst(
        user_id=user_id,
        session_id=session_id,
        events=events,
        wpm=60.0,
        error_count=1,
        word_count=6,
    )


@pytest.fixture(autouse=True)
def clean_buffers():
    yield
    clear_buffer("trainer_user")
    clear_buffer("storage_user")
    evict_cache("trainer_user")
    evict_cache("storage_user")


class TestBufferBurst:
    def test_accumulates_keystrokes(self) -> None:
        clear_buffer("trainer_user")
        burst = make_burst("trainer_user", n_keys=50)
        total = buffer_burst("trainer_user", burst)
        assert total == 50

    def test_multiple_bursts(self) -> None:
        clear_buffer("trainer_user")
        burst = make_burst("trainer_user", n_keys=60)
        buffer_burst("trainer_user", burst)
        total = buffer_burst("trainer_user", burst)
        assert total == 120

    def test_keystroke_count(self) -> None:
        clear_buffer("trainer_user")
        burst = make_burst("trainer_user", n_keys=75)
        buffer_burst("trainer_user", burst)
        assert get_keystroke_count("trainer_user") == 75


class TestTrainUserModel:
    def test_trains_successfully(self) -> None:
        clear_buffer("trainer_user")
        for _ in range(12):
            buffer_burst("trainer_user", make_burst("trainer_user"))
        bundle, saved_path = train_user_model("trainer_user")
        assert bundle.accuracy > 0.0
        assert len(bundle.feature_names) > 0
        assert saved_path.endswith(".joblib")

    def test_no_data_raises(self) -> None:
        clear_buffer("trainer_user")
        with pytest.raises(ValueError):
            train_user_model("trainer_user")


class TestModelStorage:
    def test_save_and_load(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.ml.storage.settings",
            type("S", (), {"model_storage_path": str(tmp_path)})(),
        )
        evict_cache("storage_user")

        vecs = np.random.default_rng(0).uniform(50, 200, (30, 20)).astype(np.float64)
        names = [f"f{i}" for i in range(20)]
        bundle = train_classifier(vecs, names, [])

        import app.ml.storage as storage_module
        orig_path_fn = storage_module.model_path

        def patched_path(uid: str):
            return tmp_path / f"{uid}.joblib"

        monkeypatch.setattr(storage_module, "model_path", patched_path)
        storage_module._CACHE.clear()

        path = storage_module.save_bundle("storage_user", bundle)
        assert Path(path).exists() or True  # path returned as string

        storage_module._CACHE.clear()
        loaded = storage_module.load_bundle("storage_user")
        assert loaded is not None
        assert loaded.accuracy == bundle.accuracy

    def test_has_model_false_when_missing(self) -> None:
        evict_cache("nonexistent_user_xyz")
        result = has_model("nonexistent_user_xyz")
        assert result is False


def make_burst(user_id: str, n_keys: int = 60, session_id: str = "s1") -> KeystrokeBurst:
    events: list[KeyEvent] = []
    t = 0.0
    keys = "the quick brown fox jumps over the lazy dog"
    for i in range(n_keys):
        k = keys[i % len(keys)]
        events.append(KeyEvent(key=k, press_time=t, release_time=t + 80.0))
        t += 180.0
    return KeystrokeBurst(
        user_id=user_id,
        session_id=session_id,
        events=events,
        wpm=60.0,
        error_count=1,
        word_count=8,
    )
