"""
Persist and load classifier bundles using joblib.
"""
import joblib
from pathlib import Path
from typing import Optional
from app.ml.classifier import ClassifierBundle
from app.core.config import settings
from app.core.logging import logger

_CACHE: dict[str, ClassifierBundle] = {}


def model_path(user_id: str) -> Path:
    return Path(settings.model_storage_path) / f"{user_id}.joblib"


def save_bundle(user_id: str, bundle: ClassifierBundle) -> str:
    path = model_path(user_id)
    joblib.dump(bundle, path)
    _CACHE[user_id] = bundle
    logger.info("Saved model for user %s -> %s", user_id, path)
    return str(path)


def load_bundle(user_id: str) -> Optional[ClassifierBundle]:
    if user_id in _CACHE:
        return _CACHE[user_id]
    path = model_path(user_id)
    if not path.exists():
        return None
    bundle: ClassifierBundle = joblib.load(path)
    _CACHE[user_id] = bundle
    logger.info("Loaded model for user %s from %s", user_id, path)
    return bundle


def has_model(user_id: str) -> bool:
    return user_id in _CACHE or model_path(user_id).exists()


def evict_cache(user_id: str) -> None:
    _CACHE.pop(user_id, None)
