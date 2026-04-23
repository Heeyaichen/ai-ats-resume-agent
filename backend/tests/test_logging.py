"""Tests for structured logging setup."""

from __future__ import annotations

import json
import logging

from backend.app.logging_config import configure_logging, get_logger


class TestLogging:
    def test_configure_sets_root_handler(self) -> None:
        configure_logging(service="test", environment="test", log_level="DEBUG")
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_get_logger_returns_bound_logger(self) -> None:
        configure_logging(service="test", environment="test")
        logger = get_logger("test-module")
        assert logger is not None

    def test_log_output_is_valid_json(self, capsys: object) -> None:
        configure_logging(service="test-svc", environment="test", log_level="INFO")
        logger = get_logger("test")
        logger.info("test message", key="value")

        captured = capsys  # type: ignore[assignment]
        output = captured.readouterr().out  # type: ignore[attr-defined]
        # At least one JSON line should be emitted.
        lines = [line for line in output.strip().splitlines() if line.strip()]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert parsed.get("event") == "test message" or parsed.get("message") == "test message"
        assert "timestamp" in parsed
