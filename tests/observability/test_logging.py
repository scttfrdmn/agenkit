"""Tests for logging integration with trace correlation."""

import json
import logging
from io import StringIO

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from agenkit.observability import configure_logging, get_logger_with_trace


@pytest.fixture(scope="module")
def tracer_provider():
    """Create a tracer provider for testing (module-scoped)."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield provider

    provider.force_flush()
    provider.shutdown()


@pytest.fixture
def log_stream():
    """Create a string stream for capturing log output."""
    return StringIO()


def test_configure_logging_basic(log_stream):
    """Test basic logging configuration."""
    # Configure logging with string stream
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger("test_basic")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Log a message
    logger.info("Test message")

    # Check output
    output = log_stream.getvalue()
    assert "Test message" in output


def test_trace_context_filter(tracer_provider, log_stream):
    """Test that TraceContextFilter adds trace context to logs."""
    from agenkit.observability.logging import TraceContextFilter

    # Configure logger with trace context filter
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger("test_trace")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addFilter(TraceContextFilter())

    # Create a span and log within it
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span") as span:
        span_context = span.get_span_context()

        # Create custom formatter to see attributes
        formatter = logging.Formatter(
            "%(levelname)s - %(message)s - trace_id=%(trace_id)s span_id=%(span_id)s"
        )
        handler.setFormatter(formatter)

        logger.info("Message with trace")

        # Check output contains trace IDs
        output = log_stream.getvalue()
        assert "Message with trace" in output
        assert format(span_context.trace_id, "032x") in output
        assert format(span_context.span_id, "016x") in output


def test_structured_formatter(tracer_provider, log_stream):
    """Test that StructuredFormatter produces JSON output."""
    from agenkit.observability.logging import StructuredFormatter, TraceContextFilter

    # Configure logger with structured formatter
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_structured")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addFilter(TraceContextFilter())

    # Create a span and log within it
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span") as span:
        span_context = span.get_span_context()

        logger.info("Structured message", extra={"key": "value"})

        # Parse JSON output
        output = log_stream.getvalue()
        log_data = json.loads(output.strip())

        # Check JSON structure
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Structured message"
        assert log_data["logger"] == "test_structured"
        assert log_data["key"] == "value"
        assert "timestamp" in log_data

        # Check trace context
        assert log_data["trace_id"] == format(span_context.trace_id, "032x")
        assert log_data["span_id"] == format(span_context.span_id, "016x")


def test_structured_formatter_without_span(log_stream):
    """Test StructuredFormatter works without active span."""
    from agenkit.observability.logging import StructuredFormatter, TraceContextFilter

    # Configure logger
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_no_span")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addFilter(TraceContextFilter())

    # Log without span
    logger.info("Message without span")

    # Parse JSON output
    output = log_stream.getvalue()
    log_data = json.loads(output.strip())

    # Check JSON structure
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Message without span"
    # trace_id and span_id should not be present without active span
    assert "trace_id" not in log_data or log_data["trace_id"] is None


def test_get_logger_with_trace(tracer_provider):
    """Test get_logger_with_trace returns configured logger."""
    logger = get_logger_with_trace(__name__)

    # Logger should be configured
    assert logger is not None
    assert isinstance(logger, logging.Logger)

    # Should be able to log
    logger.info("Test message")


def test_configure_logging_integration(tracer_provider):
    """Test full configure_logging integration."""
    # This test verifies that configure_logging can be called
    # We don't check output since it goes to stdout
    configure_logging(
        level=logging.INFO,
        structured=True,
        include_trace_context=True,
    )

    # Get logger and log a message
    logger = get_logger_with_trace(__name__)

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("integration-test"):
        logger.info("Integration test message", extra={"test": True})


def test_structured_formatter_handles_exceptions(log_stream):
    """Test that StructuredFormatter handles exceptions properly."""
    from agenkit.observability.logging import StructuredFormatter

    # Configure logger
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_exception")
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)

    # Log an exception
    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.error("Error occurred", exc_info=True)

    # Parse JSON output
    output = log_stream.getvalue()
    log_data = json.loads(output.strip())

    # Check error was logged
    assert log_data["level"] == "ERROR"
    assert log_data["message"] == "Error occurred"
    # Exception info should be in the output
    assert "exception" in output.lower() or "valueerror" in output.lower()


def test_logging_with_multiple_attributes(log_stream):
    """Test logging with multiple extra attributes."""
    from agenkit.observability.logging import StructuredFormatter

    # Configure logger
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_multi_attr")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Log with multiple attributes
    logger.info(
        "Multi-attribute message",
        extra={
            "user_id": "123",
            "request_id": "req-456",
            "action": "create",
            "count": 5,
        },
    )

    # Parse JSON output
    output = log_stream.getvalue()
    log_data = json.loads(output.strip())

    # Check all attributes are present
    assert log_data["user_id"] == "123"
    assert log_data["request_id"] == "req-456"
    assert log_data["action"] == "create"
    assert log_data["count"] == 5
