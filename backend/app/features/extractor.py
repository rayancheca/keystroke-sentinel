"""
Keystroke dynamics feature extractor.

Produces a fixed-length feature vector from a list of KeyEvents:
  - Statistical moments on dwell times (hold duration)
  - Statistical moments on flight times (inter-key latency)
  - Top-N digraph (key-pair) latency statistics
  - WPM and error rate proxy
"""
import numpy as np
from typing import Optional
from app.models.enrollment import KeyEvent
from app.core.config import DIGRAPH_TOP_N

FEATURE_NAMES: list[str] = []  # populated at module load time


def _stats(values: list[float]) -> dict[str, float]:
    """Return mean, std, median, p25, p75 for a list of floats."""
    if not values:
        return {"mean": 0.0, "std": 0.0, "median": 0.0, "p25": 0.0, "p75": 0.0}
    arr = np.array(values, dtype=np.float64)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "median": float(np.median(arr)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
    }


def _dwell_times(events: list[KeyEvent]) -> list[float]:
    return [
        max(0.0, ev.release_time - ev.press_time)
        for ev in events
        if ev.release_time >= ev.press_time
    ]


def _flight_times(events: list[KeyEvent]) -> list[float]:
    """Time between release of key[i] and press of key[i+1]."""
    times: list[float] = []
    for i in range(len(events) - 1):
        gap = events[i + 1].press_time - events[i].release_time
        if -50 <= gap <= 2000:  # filter physiologically impossible values
            times.append(float(gap))
    return times


def _digraph_latencies(events: list[KeyEvent]) -> dict[str, float]:
    """
    Compute mean latency for every key-pair (digraph).
    Returns a dict of 'A_B' -> mean_latency_ms.
    Latency = press_time[i+1] - press_time[i].
    """
    latencies: dict[str, list[float]] = {}
    for i in range(len(events) - 1):
        pair = f"{events[i].key}_{events[i + 1].key}"
        lat = events[i + 1].press_time - events[i].press_time
        if 0 < lat < 2000:
            latencies.setdefault(pair, []).append(float(lat))
    return {k: float(np.mean(v)) for k, v in latencies.items()}


# The canonical digraph set is fixed after the first enrollment;
# unknown digraphs in later bursts are filled with a neutral value.
_CANONICAL_DIGRAPHS: list[str] = []


def set_canonical_digraphs(digraphs: list[str]) -> None:
    global _CANONICAL_DIGRAPHS
    _CANONICAL_DIGRAPHS = digraphs


def get_canonical_digraphs() -> list[str]:
    return list(_CANONICAL_DIGRAPHS)


def extract_features(
    events: list[KeyEvent],
    wpm: float = 0.0,
    error_count: int = 0,
    word_count: int = 0,
    canonical_digraphs: Optional[list[str]] = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """
    Extract a fixed-length feature vector from a keystroke event list.

    Returns:
        vector: numpy array of shape (n_features,)
        named: dict mapping feature name -> value (for display)
    """
    digraphs_to_use = canonical_digraphs or _CANONICAL_DIGRAPHS

    dwell = _dwell_times(events)
    flight = _flight_times(events)
    digraph_map = _digraph_latencies(events)

    dwell_stats = _stats(dwell)
    flight_stats = _stats(flight)

    named: dict[str, float] = {}

    for stat, val in dwell_stats.items():
        named[f"dwell_{stat}"] = val

    for stat, val in flight_stats.items():
        named[f"flight_{stat}"] = val

    named["wpm"] = float(wpm)
    error_rate = error_count / max(word_count, 1)
    named["error_rate"] = error_rate
    named["keystroke_count"] = float(len(events))

    neutral_digraph = float(np.mean(list(digraph_map.values()))) if digraph_map else 150.0

    for dg in digraphs_to_use:
        named[f"dg_{dg}"] = digraph_map.get(dg, neutral_digraph)

    vector = np.array(list(named.values()), dtype=np.float64)
    return vector, named


def build_canonical_digraphs(all_digraph_maps: list[dict[str, float]]) -> list[str]:
    """
    From a list of digraph maps (one per burst), pick the top-N most
    frequently occurring digraphs as the canonical set.
    """
    freq: dict[str, int] = {}
    for dmap in all_digraph_maps:
        for k in dmap:
            freq[k] = freq.get(k, 0) + 1
    ranked = sorted(freq, key=lambda k: freq[k], reverse=True)
    return ranked[:DIGRAPH_TOP_N]
