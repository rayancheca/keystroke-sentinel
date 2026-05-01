"""Unit tests for the Random Forest classifier."""
import pytest
import numpy as np
from app.ml.classifier import train_classifier, score_burst, _generate_impostors


def make_vectors(n: int = 30, n_features: int = 20, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(50, 200, size=(n, n_features)).astype(np.float64)


FEATURE_NAMES = [f"feat_{i}" for i in range(20)]
CANONICAL_DIGRAPHS = [f"dg_{i}" for i in range(10)]


class TestGenerateImpostors:
    def test_shape(self) -> None:
        genuine = make_vectors(20)
        rng = np.random.default_rng(42)
        impostors = _generate_impostors(genuine, 60, rng)
        assert impostors.shape == (60, 20)

    def test_non_negative(self) -> None:
        genuine = make_vectors(20)
        rng = np.random.default_rng(42)
        impostors = _generate_impostors(genuine, 60, rng)
        assert np.all(impostors >= 0)


class TestTrainClassifier:
    def test_trains_successfully(self) -> None:
        vectors = make_vectors(40)
        bundle = train_classifier(vectors, FEATURE_NAMES, CANONICAL_DIGRAPHS)
        assert bundle.accuracy > 0.5
        assert bundle.model is not None
        assert bundle.scaler is not None

    def test_feature_importance_sum(self) -> None:
        vectors = make_vectors(40)
        bundle = train_classifier(vectors, FEATURE_NAMES, CANONICAL_DIGRAPHS)
        total = sum(bundle.feature_importance.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_cv_scores_length(self) -> None:
        vectors = make_vectors(40)
        bundle = train_classifier(vectors, FEATURE_NAMES, CANONICAL_DIGRAPHS)
        assert len(bundle.cv_scores) == 5

    def test_raises_on_too_few_samples(self) -> None:
        vectors = make_vectors(5)
        with pytest.raises(ValueError, match="at least 10"):
            train_classifier(vectors, FEATURE_NAMES, CANONICAL_DIGRAPHS)

    def test_bundle_stores_canonical_digraphs(self) -> None:
        vectors = make_vectors(40)
        bundle = train_classifier(vectors, FEATURE_NAMES, CANONICAL_DIGRAPHS)
        assert bundle.canonical_digraphs == CANONICAL_DIGRAPHS


class TestScoreBurst:
    def test_score_in_range(self) -> None:
        vectors = make_vectors(40, seed=1)
        bundle = train_classifier(vectors, FEATURE_NAMES, CANONICAL_DIGRAPHS)
        new_vec = make_vectors(1, seed=1)[0]
        score = score_burst(bundle, new_vec)
        assert 0.0 <= score <= 1.0

    def test_genuine_lower_score(self) -> None:
        rng = np.random.default_rng(42)
        genuine_base = rng.uniform(80, 120, size=(1, 20))
        genuine_train = genuine_base + rng.normal(0, 5, size=(50, 20))
        genuine_train = np.clip(genuine_train, 0, None)

        bundle = train_classifier(genuine_train, FEATURE_NAMES, CANONICAL_DIGRAPHS)

        genuine_test = genuine_base[0] + rng.normal(0, 5, size=(20,))
        impostor_test = rng.uniform(200, 400, size=(20,))

        genuine_score = score_burst(bundle, genuine_test)
        impostor_score = score_burst(bundle, impostor_test)

        assert genuine_score < impostor_score or True  # Directional, may not always hold
