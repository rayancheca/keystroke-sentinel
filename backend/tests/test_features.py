"""Unit tests for the keystroke feature extractor."""
import pytest
import numpy as np
from app.models.enrollment import KeyEvent
from app.features.extractor import (
    _dwell_times,
    _flight_times,
    _digraph_latencies,
    _stats,
    extract_features,
    build_canonical_digraphs,
)


def make_events(keys: str, base_press: float = 0.0, dwell: float = 80.0, gap: float = 100.0) -> list[KeyEvent]:
    """Create synthetic keystroke events for testing."""
    events: list[KeyEvent] = []
    t = base_press
    for key in keys:
        events.append(KeyEvent(key=key, press_time=t, release_time=t + dwell))
        t += dwell + gap
    return events


class TestDwellTimes:
    def test_basic_dwell(self) -> None:
        events = make_events("abc", dwell=80.0)
        dwell = _dwell_times(events)
        assert len(dwell) == 3
        assert all(d == pytest.approx(80.0) for d in dwell)

    def test_filters_negative_dwell(self) -> None:
        events = [KeyEvent(key="a", press_time=100.0, release_time=50.0)]  # release before press
        dwell = _dwell_times(events)
        assert len(dwell) == 0

    def test_empty_events(self) -> None:
        assert _dwell_times([]) == []


class TestFlightTimes:
    def test_basic_flight(self) -> None:
        events = make_events("ab", dwell=80.0, gap=120.0)
        flight = _flight_times(events)
        assert len(flight) == 1
        assert flight[0] == pytest.approx(120.0)

    def test_filters_large_gap(self) -> None:
        events = [
            KeyEvent(key="a", press_time=0.0, release_time=80.0),
            KeyEvent(key="b", press_time=3000.0, release_time=3080.0),
        ]
        flight = _flight_times(events)
        assert len(flight) == 0

    def test_single_event_no_flight(self) -> None:
        assert _flight_times(make_events("a")) == []


class TestDigraphLatencies:
    def test_single_digraph(self) -> None:
        events = make_events("ab", dwell=80.0, gap=100.0)
        dmap = _digraph_latencies(events)
        assert "a_b" in dmap
        assert dmap["a_b"] == pytest.approx(80.0 + 100.0)  # dwell + gap = press-to-press

    def test_multiple_digraphs(self) -> None:
        events = make_events("abc")
        dmap = _digraph_latencies(events)
        assert "a_b" in dmap
        assert "b_c" in dmap

    def test_averaging_repeated_digraph(self) -> None:
        events = make_events("ababab", dwell=80.0, gap=100.0)
        dmap = _digraph_latencies(events)
        assert "a_b" in dmap
        assert "b_a" in dmap


class TestStats:
    def test_stats_basic(self) -> None:
        values = [100.0, 200.0, 300.0]
        stats = _stats(values)
        assert stats["mean"] == pytest.approx(200.0)
        assert stats["median"] == pytest.approx(200.0)
        assert "std" in stats
        assert "p25" in stats
        assert "p75" in stats

    def test_stats_empty(self) -> None:
        stats = _stats([])
        assert stats["mean"] == 0.0
        assert stats["std"] == 0.0


class TestExtractFeatures:
    def test_vector_shape(self) -> None:
        events = make_events("the quick brown fox", dwell=80.0)
        canonical = ["t_h", "h_e", "e_ ", " _q"]
        vec, named = extract_features(events, canonical_digraphs=canonical)
        assert isinstance(vec, np.ndarray)
        assert vec.ndim == 1
        assert len(vec) > 10

    def test_named_keys(self) -> None:
        events = make_events("hello world", dwell=80.0)
        canonical = ["h_e", "e_l"]
        _, named = extract_features(events, wpm=60.0, canonical_digraphs=canonical)
        assert "dwell_mean" in named
        assert "flight_mean" in named
        assert "wpm" in named
        assert named["wpm"] == pytest.approx(60.0)
        assert "dg_h_e" in named

    def test_wpm_and_error_rate(self) -> None:
        events = make_events("test", dwell=80.0)
        _, named = extract_features(events, wpm=80.0, error_count=2, word_count=10, canonical_digraphs=[])
        assert named["wpm"] == pytest.approx(80.0)
        assert named["error_rate"] == pytest.approx(0.2)


class TestBuildCanonicalDigraphs:
    def test_selects_most_frequent(self) -> None:
        maps = [
            {"a_b": 100.0, "b_c": 120.0},
            {"a_b": 110.0, "c_d": 90.0},
            {"a_b": 105.0},
        ]
        canonical = build_canonical_digraphs(maps)
        assert canonical[0] == "a_b"

    def test_respects_top_n(self) -> None:
        maps = [{f"k{i}_k{i+1}": float(i) for i in range(100)}]
        from app.core.config import DIGRAPH_TOP_N
        canonical = build_canonical_digraphs(maps)
        assert len(canonical) <= DIGRAPH_TOP_N
