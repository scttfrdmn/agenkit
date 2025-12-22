"""
Pluggable audit logging for security and compliance.

Provides structured audit logging with support for multiple backends
through a pluggable adapter architecture.
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from opentelemetry import trace


class AuditEventType(Enum):
    """Types of audit events."""

    AUTH_ATTEMPT = "auth_attempt"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTHORIZATION = "authorization"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    VALIDATION_FAILURE = "validation_failure"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"


class AuditSeverity(Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Structured audit event.

    Contains all information about a security-relevant event including
    timestamp, event type, severity, actor, resource, and trace context.
    """

    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor: str | None = None  # User ID, service name, or IP address
    resource: str | None = None  # Resource being accessed
    action: str | None = None  # Action being performed
    result: str | None = None  # Success, failure, denied, etc.
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None

    def __post_init__(self):
        """Add trace context if available."""
        if self.trace_id is None:
            span = trace.get_current_span()
            span_context = span.get_span_context()
            if span_context.is_valid:
                self.trace_id = format(span_context.trace_id, "032x")
                self.span_id = format(span_context.span_id, "016x")

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        # Convert enums to strings
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        # Convert timestamp to ISO format
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AuditAdapter(Protocol):
    """
    Protocol for audit log adapters.

    Adapters handle the actual logging of audit events to various backends
    (console, file, syslog, cloud services, etc.).
    """

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: The audit event to log
        """
        ...


class ConsoleAuditAdapter:
    """
    Audit adapter that logs to console.

    Useful for development and debugging. Logs human-readable messages
    to stdout/stderr.
    """

    def __init__(self, use_colors: bool = True):
        """
        Initialize console adapter.

        Args:
            use_colors: If True, use ANSI colors for severity levels
        """
        self.use_colors = use_colors
        self.colors = {
            AuditSeverity.DEBUG: "\033[36m",  # Cyan
            AuditSeverity.INFO: "\033[32m",  # Green
            AuditSeverity.WARNING: "\033[33m",  # Yellow
            AuditSeverity.ERROR: "\033[31m",  # Red
            AuditSeverity.CRITICAL: "\033[35m",  # Magenta
        }
        self.reset = "\033[0m"

    def log_event(self, event: AuditEvent) -> None:
        """Log event to console."""
        color = self.colors.get(event.severity, "") if self.use_colors else ""
        reset = self.reset if self.use_colors else ""

        # Format message
        parts = [
            f"{event.timestamp.isoformat()}",
            f"{color}{event.severity.value.upper()}{reset}",
            f"[{event.event_type.value}]",
        ]

        if event.actor:
            parts.append(f"actor={event.actor}")
        if event.resource:
            parts.append(f"resource={event.resource}")
        if event.action:
            parts.append(f"action={event.action}")
        if event.result:
            parts.append(f"result={event.result}")

        parts.append(event.message)

        # Add trace context if available
        if event.trace_id:
            parts.append(f"trace_id={event.trace_id}")

        message = " ".join(parts)

        # Write to stderr for warnings/errors, stdout for others
        stream = (
            sys.stderr
            if event.severity in (AuditSeverity.ERROR, AuditSeverity.CRITICAL)
            else sys.stdout
        )
        print(message, file=stream)


class StructuredAuditAdapter:
    """
    Audit adapter that outputs JSON structured logs.

    Logs events as JSON objects suitable for log aggregation systems
    like ELK, Splunk, CloudWatch, etc.
    """

    def __init__(self, stream=None):
        """
        Initialize structured adapter.

        Args:
            stream: Output stream (defaults to stdout)
        """
        self.stream = stream or sys.stdout

    def log_event(self, event: AuditEvent) -> None:
        """Log event as JSON."""
        json_data = json.dumps(event.to_dict())
        print(json_data, file=self.stream)


class FileAuditAdapter:
    """
    Audit adapter that logs to a file.

    Logs events to a file with optional rotation. Uses JSON format
    for structured logging.
    """

    def __init__(
        self,
        file_path: str | Path,
        structured: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
    ):
        """
        Initialize file adapter.

        Args:
            file_path: Path to log file
            structured: If True, use JSON format; otherwise human-readable
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep
        """
        self.file_path = Path(file_path)
        self.structured = structured
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Create parent directory if needed
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup logging handler
        self.logger = logging.getLogger(f"audit.{file_path}")
        self.logger.setLevel(logging.INFO)

        # Use rotating file handler
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            str(self.file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )

        if structured:
            formatter = logging.Formatter("%(message)s")
        else:
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, event: AuditEvent) -> None:
        """Log event to file."""
        if self.structured:
            message = json.dumps(event.to_dict())
        else:
            # Human-readable format
            parts = [
                f"[{event.event_type.value}]",
                f"severity={event.severity.value}",
            ]
            if event.actor:
                parts.append(f"actor={event.actor}")
            if event.resource:
                parts.append(f"resource={event.resource}")
            if event.result:
                parts.append(f"result={event.result}")
            parts.append(event.message)
            message = " ".join(parts)

        # Map severity to logging level
        level_map = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }
        level = level_map.get(event.severity, logging.INFO)

        self.logger.log(level, message)


class AuditLogger:
    """
    Main audit logger with pluggable adapters.

    Provides high-level methods for logging security events and dispatches
    events to multiple adapters simultaneously.
    """

    def __init__(self, adapters: list[AuditAdapter] | None = None):
        """
        Initialize audit logger.

        Args:
            adapters: List of audit adapters (defaults to ConsoleAuditAdapter)
        """
        self.adapters = adapters or [ConsoleAuditAdapter()]

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event to all adapters.

        Args:
            event: The audit event to log
        """
        for adapter in self.adapters:
            try:
                adapter.log_event(event)
            except Exception as e:
                # Don't let adapter failures break the application
                print(f"Audit adapter error: {e}", file=sys.stderr)

    def log_auth_attempt(
        self,
        user_id: str,
        success: bool,
        method: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
        **metadata,
    ) -> None:
        """
        Log an authentication attempt.

        Args:
            user_id: User identifier
            success: Whether authentication succeeded
            method: Authentication method (password, token, oauth, etc.)
            ip_address: Client IP address
            reason: Reason for failure (if applicable)
            **metadata: Additional metadata
        """
        event_type = AuditEventType.AUTH_SUCCESS if success else AuditEventType.AUTH_FAILURE
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING

        message = f"Authentication {'succeeded' if success else 'failed'} for user {user_id}"
        if method:
            message += f" using {method}"
        if reason and not success:
            message += f": {reason}"

        event_metadata = {"method": method, "ip_address": ip_address, **metadata}

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            actor=user_id,
            action="authenticate",
            result="success" if success else "failure",
            metadata=event_metadata,
        )

        self.log_event(event)

    def log_authorization(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: str | None = None,
        **metadata,
    ) -> None:
        """
        Log an authorization decision.

        Args:
            user_id: User identifier
            resource: Resource being accessed
            action: Action being performed
            allowed: Whether access was allowed
            reason: Reason for denial (if applicable)
            **metadata: Additional metadata
        """
        severity = AuditSeverity.INFO if allowed else AuditSeverity.WARNING

        message = f"Authorization {'granted' if allowed else 'denied'} for user {user_id} to {action} {resource}"
        if reason and not allowed:
            message += f": {reason}"

        event = AuditEvent(
            event_type=AuditEventType.AUTHORIZATION,
            severity=severity,
            message=message,
            actor=user_id,
            resource=resource,
            action=action,
            result="allowed" if allowed else "denied",
            metadata={"reason": reason, **metadata},
        )

        self.log_event(event)

    def log_rate_limit_exceeded(
        self,
        client_id: str,
        endpoint: str,
        limit: int,
        window: str,
        **metadata,
    ) -> None:
        """
        Log a rate limit violation.

        Args:
            client_id: Client identifier (user ID, IP address, API key, etc.)
            endpoint: Endpoint or resource being rate limited
            limit: Rate limit threshold
            window: Time window for rate limit
            **metadata: Additional metadata
        """
        message = (
            f"Rate limit exceeded for {client_id} on {endpoint} ({limit} requests per {window})"
        )

        event = AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.WARNING,
            message=message,
            actor=client_id,
            resource=endpoint,
            action="request",
            result="rate_limited",
            metadata={"limit": limit, "window": window, **metadata},
        )

        self.log_event(event)

    def log_validation_failure(
        self,
        message_id: str,
        reason: str,
        field: str | None = None,
        value: Any = None,
        **metadata,
    ) -> None:
        """
        Log an input validation failure.

        Args:
            message_id: Message or request identifier
            reason: Reason for validation failure
            field: Field that failed validation (if applicable)
            value: Invalid value (be careful with PII)
            **metadata: Additional metadata
        """
        message = f"Validation failure for message {message_id}: {reason}"
        if field:
            message += f" (field: {field})"

        event = AuditEvent(
            event_type=AuditEventType.VALIDATION_FAILURE,
            severity=AuditSeverity.WARNING,
            message=message,
            resource=message_id,
            action="validate",
            result="failure",
            metadata={"reason": reason, "field": field, "value": value, **metadata},
        )

        self.log_event(event)

    def log_configuration_change(
        self,
        user_id: str,
        component: str,
        parameter: str,
        old_value: Any,
        new_value: Any,
        **metadata,
    ) -> None:
        """
        Log a configuration change.

        Args:
            user_id: User who made the change
            component: Component being configured
            parameter: Parameter being changed
            old_value: Previous value
            new_value: New value
            **metadata: Additional metadata
        """
        message = f"Configuration changed: {component}.{parameter} changed from {old_value} to {new_value}"

        event = AuditEvent(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.INFO,
            message=message,
            actor=user_id,
            resource=f"{component}.{parameter}",
            action="configure",
            result="success",
            metadata={"old_value": old_value, "new_value": new_value, **metadata},
        )

        self.log_event(event)

    def log_security_violation(
        self,
        client_id: str,
        violation_type: str,
        description: str,
        severity: AuditSeverity = AuditSeverity.ERROR,
        **metadata,
    ) -> None:
        """
        Log a security violation.

        Args:
            client_id: Client identifier
            violation_type: Type of violation
            description: Description of the violation
            severity: Severity level
            **metadata: Additional metadata
        """
        message = f"Security violation ({violation_type}): {description}"

        event = AuditEvent(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=severity,
            message=message,
            actor=client_id,
            action=violation_type,
            result="violation",
            metadata=metadata,
        )

        self.log_event(event)

    def log_suspicious_activity(
        self,
        client_id: str,
        activity_type: str,
        description: str,
        indicators: list[str] | None = None,
        **metadata,
    ) -> None:
        """
        Log suspicious activity.

        Args:
            client_id: Client identifier
            activity_type: Type of suspicious activity
            description: Description of the activity
            indicators: List of indicators that triggered the alert
            **metadata: Additional metadata
        """
        message = f"Suspicious activity detected ({activity_type}): {description}"

        event = AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.WARNING,
            message=message,
            actor=client_id,
            action=activity_type,
            result="suspicious",
            metadata={"indicators": indicators or [], **metadata},
        )

        self.log_event(event)
