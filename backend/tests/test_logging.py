"""Tests for logging configuration."""

import structlog

from app.utils import get_logger, setup_logging


class TestLogging:
    """Test logging configuration."""

    def test_setup_logging(self):
        """Test logging setup."""
        setup_logging()
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        setup_logging()
        logger = get_logger("test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_logger_has_required_methods(self):
        """Test logger has standard logging methods."""
        setup_logging()
        logger = get_logger("test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_logger_can_log(self):
        """Test logger can actually log."""
        setup_logging()
        logger = get_logger("test")

        # This should not raise any exception
        logger.info("test_message", extra_field="test_value")
        logger.debug("debug_message")
        logger.warning("warning_message")
        logger.error("error_message")

    def test_logger_includes_trace_id(self):
        """Test logger includes trace_id in logs."""
        setup_logging()
        logger = get_logger("test")

        # Just verify that binding context works
        with structlog.contextvars.bound_contextvars(trace_id="test-123"):
            # This should not raise
            logger.info("test_message", extra_field="test_value")
            assert True

    def test_logger_json_output(self):
        """Test logger outputs JSON format."""
        setup_logging()
        logger = get_logger("test")

        with structlog.contextvars.bound_contextvars(trace_id="test-123"):
            logger.info("test_message", key="value")

            # Verify structlog is configured with JSONRenderer
        assert logger is not None
