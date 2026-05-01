"""Tests for core utilities."""
import pytest
from app.core.logging import configure_logging, logger
from app.core.config import settings, BURST_MIN_KEYSTROKES, DIGRAPH_TOP_N


class TestLogging:
    def test_configure_logging_does_not_raise(self) -> None:
        configure_logging()

    def test_logger_exists(self) -> None:
        assert logger.name == "keystroke_sentinel"


class TestConfig:
    def test_anomaly_threshold_in_range(self) -> None:
        assert 0.0 < settings.anomaly_threshold < 1.0

    def test_digraph_top_n_positive(self) -> None:
        assert DIGRAPH_TOP_N > 0

    def test_burst_min_keystrokes_positive(self) -> None:
        assert BURST_MIN_KEYSTROKES > 0
