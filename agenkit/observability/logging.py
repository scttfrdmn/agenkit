"""
Logging integration for Agenkit with trace correlation.

Provides structured logging with automatic trace ID injection for
correlating logs with distributed traces.
"""

import logging
import json
from typing import Any

from opentelemetry import trace


class TraceContextFilter(logging.Filter):
    """
    Logging filter that adds trace context to log records.

    Automatically injects trace_id and span_id into log records
    when executing within a traced context.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace context to log record."""
        # Get current span
        span = trace.get_current_span()
        span_context = span.get_span_context()

        if span_context.is_valid:
            # Add trace context as attributes
            record.trace_id = format(span_context.trace_id, '032x')
            record.span_id = format(span_context.span_id, '016x')
            record.trace_flags = span_context.trace_flags
        else:
            # No active trace
            record.trace_id = None
            record.span_id = None
            record.trace_flags = None

        return True


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON with trace context included.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace context if available
        if hasattr(record, 'trace_id') and record.trace_id:
            log_data["trace_id"] = record.trace_id
            log_data["span_id"] = record.span_id

        # Add exception if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                'pathname', 'process', 'processName', 'relativeCreated', 'thread',
                'threadName', 'exc_info', 'exc_text', 'stack_info', 'trace_id',
                'span_id', 'trace_flags',
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def configure_logging(
    level: int = logging.INFO,
    structured: bool = True,
    include_trace_context: bool = True,
) -> None:
    """
    Configure logging with trace correlation.

    Args:
        level: Logging level (e.g., logging.INFO)
        structured: If True, use structured JSON logging
        include_trace_context: If True, inject trace context into logs
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Set formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    handler.setFormatter(formatter)

    # Add trace context filter if requested
    if include_trace_context:
        handler.addFilter(TraceContextFilter())

    # Add handler to root logger
    root_logger.addHandler(handler)


def get_logger_with_trace(name: str) -> logging.Logger:
    """
    Get a logger with trace context support.

    Args:
        name: Logger name

    Returns:
        Logger instance that includes trace context in logs
    """
    logger = logging.getLogger(name)

    # Ensure trace context filter is added
    has_trace_filter = any(
        isinstance(f, TraceContextFilter) for f in logger.filters
    )
    if not has_trace_filter:
        logger.addFilter(TraceContextFilter())

    return logger
