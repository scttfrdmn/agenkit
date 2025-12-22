"""
Observability infrastructure for Agenkit using OpenTelemetry.

Provides distributed tracing, metrics export, logging integration,
and audit logging for monitoring agent interactions across Python
and Go implementations.
"""

from .audit import (AuditAdapter, AuditEvent, AuditEventType, AuditLogger,
                    AuditSeverity, ConsoleAuditAdapter, FileAuditAdapter,
                    StructuredAuditAdapter)
from .logging import configure_logging, get_logger_with_trace
from .metrics import (MetricsMiddleware, get_meter, init_metrics,
                      init_resource_metrics)
from .tracing import TracingMiddleware, get_tracer, init_tracing

__all__ = [
    # Audit Logging
    "AuditAdapter",
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "AuditSeverity",
    "ConsoleAuditAdapter",
    "FileAuditAdapter",
    # Metrics
    "MetricsMiddleware",
    "StructuredAuditAdapter",
    # Tracing
    "TracingMiddleware",
    # Logging
    "configure_logging",
    "get_logger_with_trace",
    "get_meter",
    "get_tracer",
    "init_metrics",
    "init_resource_metrics",
    "init_tracing",
]
