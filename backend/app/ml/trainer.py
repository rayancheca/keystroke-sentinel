"""
Enrollment data accumulation and model training orchestration.
"""
import numpy as np
from typing import Optional
from app.features.extractor import (
    extract_features,
    build_canonical_digraphs,
    set_canonical_digraphs,
    _digraph_latencies,
)
from app.ml.classifier import train_classifier, ClassifierBundle
from app.ml.storage import save_bundle
from app.models.enrollment import KeystrokeBurst
from app.core.logging import logger

# In-memory enrollment buffer keyed by user_id
_enrollment_buffer: dict[str, list[KeystrokeBurst]] = {}
_digraph_buffer: dict[str, list[dict[str, float]]] = {}


def buffer_burst(user_id: str, burst: KeystrokeBurst) -> int:
    """Append a burst to the enrollment buffer. Returns total keystroke count."""
    _enrollment_buffer.setdefault(user_id, []).append(burst)
    dmap = _digraph_latencies(burst.events)
    _digraph_buffer.setdefault(user_id, []).append(dmap)
    total = sum(len(b.events) for b in _enrollment_buffer[user_id])
    return total


def get_keystroke_count(user_id: str) -> int:
    bursts = _enrollment_buffer.get(user_id, [])
    return sum(len(b.events) for b in bursts)


def train_user_model(user_id: str) -> ClassifierBundle:
    """
    Build canonical digraphs, extract feature vectors, and train the classifier.
    Raises ValueError if not enough data.
    """
    bursts = _enrollment_buffer.get(user_id, [])
    if not bursts:
        raise ValueError(f"No enrollment data for user {user_id}")

    digraph_maps = _digraph_buffer.get(user_id, [])
    canonical = build_canonical_digraphs(digraph_maps)
    set_canonical_digraphs(canonical)

    vectors: list[np.ndarray] = []
    for burst in bursts:
        vec, _ = extract_features(
            burst.events,
            wpm=burst.wpm,
            error_count=burst.error_count,
            word_count=burst.word_count,
            canonical_digraphs=canonical,
        )
        vectors.append(vec)

    X = np.array(vectors, dtype=np.float64)
    _, named = extract_features(
        bursts[0].events,
        canonical_digraphs=canonical,
    )
    feature_names = list(named.keys())

    logger.info(
        "Training model for %s: %d bursts, %d features, %d total keystrokes",
        user_id, len(bursts), len(feature_names), sum(len(b.events) for b in bursts),
    )

    bundle = train_classifier(X, feature_names, canonical)
    path = save_bundle(user_id, bundle)
    logger.info("Model trained for %s: accuracy=%.3f, path=%s", user_id, bundle.accuracy, path)
    return bundle


def clear_buffer(user_id: str) -> None:
    _enrollment_buffer.pop(user_id, None)
    _digraph_buffer.pop(user_id, None)
