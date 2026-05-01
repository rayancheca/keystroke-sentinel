"""
Random Forest anomaly classifier for keystroke dynamics.

Framed as a one-class / binary classification problem:
  - Class 1 = enrolled user (legitimate)
  - Class 0 = synthetic impostor (generated via feature perturbation)

The classifier outputs a probability score in [0, 1] for "is legitimate user".
Anomaly score = 1 - P(class=1).
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassifierBundle:
    model: RandomForestClassifier
    scaler: StandardScaler
    feature_names: list[str]
    canonical_digraphs: list[str]
    accuracy: float
    cv_scores: list[float]
    feature_importance: dict[str, float]


def _generate_impostors(
    genuine: np.ndarray, n_impostors: int, rng: np.random.Generator
) -> np.ndarray:
    """
    Synthesize impostor samples by perturbing genuine samples.
    Impostors are drawn from a distribution with higher variance than the
    genuine population, simulating different typing rhythms.
    """
    mean = genuine.mean(axis=0)
    std = genuine.std(axis=0)

    noise_scale = rng.uniform(1.5, 3.0, size=(n_impostors, genuine.shape[1]))
    noise = rng.normal(0, std * noise_scale)

    impostors = mean + noise
    impostors = np.clip(impostors, 0, None)
    return impostors


def train_classifier(
    feature_vectors: np.ndarray,
    feature_names: list[str],
    canonical_digraphs: list[str],
    n_estimators: int = 200,
    random_state: int = 42,
) -> ClassifierBundle:
    """
    Train a Random Forest classifier on genuine enrollment vectors.

    Generates synthetic impostor samples to give the classifier a
    balanced binary classification problem.
    """
    if len(feature_vectors) < 10:
        raise ValueError(
            f"Need at least 10 feature vectors for training; got {len(feature_vectors)}"
        )

    rng = np.random.default_rng(random_state)
    n_genuine = len(feature_vectors)
    n_impostors = n_genuine * 3

    impostors = _generate_impostors(feature_vectors, n_impostors, rng)

    X = np.vstack([feature_vectors, impostors])
    y = np.array([1] * n_genuine + [0] * n_impostors, dtype=np.int32)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=10,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )

    cv_scores = cross_val_score(clf, X_scaled, y, cv=5, scoring="accuracy").tolist()
    clf.fit(X_scaled, y)

    importance = {
        name: float(imp)
        for name, imp in zip(feature_names, clf.feature_importances_)
    }
    importance = dict(
        sorted(importance.items(), key=lambda x: x[1], reverse=True)
    )

    return ClassifierBundle(
        model=clf,
        scaler=scaler,
        feature_names=feature_names,
        canonical_digraphs=canonical_digraphs,
        accuracy=float(np.mean(cv_scores)),
        cv_scores=cv_scores,
        feature_importance=importance,
    )


def score_burst(
    bundle: ClassifierBundle,
    feature_vector: np.ndarray,
) -> float:
    """
    Score a live keystroke burst.

    Returns anomaly_score in [0, 1].
      0.0 = definitely the enrolled user
      1.0 = definitely an impostor
    """
    X = feature_vector.reshape(1, -1)
    X_scaled = bundle.scaler.transform(X)
    prob_legitimate = bundle.model.predict_proba(X_scaled)[0][1]
    return float(1.0 - prob_legitimate)
