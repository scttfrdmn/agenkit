"""
Security audit logging.

Provides comprehensive security event logging:
- Access attempts
- Permission checks
- Validation failures
- Anomaly detections
- Security violations
"""

import json
import logging
import logging.handlers
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuditEventType(Enum):
    """Types of audit events."""

    # Access events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Validation events
    INPUT_VALIDATION_FAILED = "input_validation_failed"
    OUTPUT_VALIDATION_FAILED = "output_validation_failed"

    # Permission events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"

    # Security events
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    SENSITIVE_DATA_DETECTED = "sensitive_data_detected"
    ANOMALY_DETECTED = "anomaly_detected"

    # Operational events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"


class AuditSeverity(Enum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Structured audit event.

    Contains all information needed for security auditing and compliance.
    """

    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: str | None = None
    agent_name: str | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "agent_name": self.agent_name,
            "message": self.message,
            "details": self.details,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class SecurityAuditLogger:
    """
    Security audit logger with structured logging.

    Features:
    - Structured JSON logging
    - Log rotation
    - Severity-based filtering
    - Multiple output targets
    - Searchable audit trail
    """

    def __init__(
        self,
        log_file: str = "security_audit.log",
        max_bytes: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 10,
        min_severity: AuditSeverity = AuditSeverity.INFO,
        also_log_to_console: bool = True,
    ):
        """
        Initialize security audit logger.

        Args:
            log_file: Path to log file
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            min_severity: Minimum severity to log
            also_log_to_console: Also output to console
        """
        self.min_severity = min_severity
        self.logger = logging.getLogger("agenkit.security.audit")
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )

        # JSON formatter
        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler (optional)
        if also_log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def _should_log(self, severity: AuditSeverity) -> bool:
        """Check if event should be logged based on severity."""
        severity_order = {
            AuditSeverity.INFO: 0,
            AuditSeverity.WARNING: 1,
            AuditSeverity.ERROR: 2,
            AuditSeverity.CRITICAL: 3,
        }
        return severity_order[severity] >= severity_order[self.min_severity]

    def log(self, event: AuditEvent):
        """
        Log audit event.

        Args:
            event: Audit event to log
        """
        if not self._should_log(event.severity):
            return

        # Map severity to logging level
        level_map = {
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }

        # Log as JSON
        self.logger.log(level_map[event.severity], event.to_json())

    def log_access(
        self,
        granted: bool,
        user_id: str,
        agent_name: str,
        action: str,
        details: dict[str, Any] | None = None,
    ):
        """Log access attempt."""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED if granted else AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.INFO if granted else AuditSeverity.WARNING,
            user_id=user_id,
            agent_name=agent_name,
            message=f"Access {('granted' if granted else 'denied')} for action: {action}",
            details=details or {},
        )
        self.log(event)

    def log_permission_check(
        self,
        granted: bool,
        user_id: str,
        agent_name: str,
        permission: str,
        details: dict[str, Any] | None = None,
    ):
        """Log permission check."""
        event = AuditEvent(
            event_type=AuditEventType.PERMISSION_GRANTED
            if granted
            else AuditEventType.PERMISSION_DENIED,
            severity=AuditSeverity.INFO if granted else AuditSeverity.WARNING,
            user_id=user_id,
            agent_name=agent_name,
            message=f"Permission {permission}: {('granted' if granted else 'denied')}",
            details=details or {},
        )
        self.log(event)

    def log_validation_failure(
        self,
        user_id: str,
        validation_type: str,
        reason: str,
        content_preview: str | None = None,
        agent_name: str | None = None,
    ):
        """Log validation failure."""
        # Truncate content preview
        truncated_preview = ""
        if content_preview:
            truncated_preview = content_preview[:200] + (
                "..." if len(content_preview) > 200 else ""
            )

        event = AuditEvent(
            event_type=AuditEventType.INPUT_VALIDATION_FAILED
            if validation_type == "input"
            else AuditEventType.OUTPUT_VALIDATION_FAILED,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            agent_name=agent_name or "",
            message=f"{validation_type.capitalize()} validation failed: {reason}",
            details={
                "validation_type": validation_type,
                "reason": reason,
                "content_preview": truncated_preview,
            },
        )
        self.log(event)

    def log_prompt_injection(
        self,
        user_id: str,
        score: int,
        matched_patterns: list,
        content_preview: str | None = None,
        agent_name: str | None = None,
    ):
        """Log prompt injection detection."""
        # Truncate content preview
        truncated_preview = ""
        if content_preview:
            truncated_preview = content_preview[:200] + (
                "..." if len(content_preview) > 200 else ""
            )

        event = AuditEvent(
            event_type=AuditEventType.PROMPT_INJECTION_DETECTED,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            agent_name=agent_name or "",
            message=f"Prompt injection detected (score: {score}, patterns: {len(matched_patterns)})",
            details={
                "score": score,
                "matched_patterns": matched_patterns,
                "content_preview": truncated_preview,
            },
        )
        self.log(event)

    def log_anomaly(
        self,
        user_id: str,
        anomaly_type: str,
        details: dict[str, Any] | None = None,
        agent_name: str | None = None,
    ):
        """Log anomaly detection."""
        event_details = details or {}
        event_details["anomaly_type"] = anomaly_type

        event = AuditEvent(
            event_type=AuditEventType.ANOMALY_DETECTED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            agent_name=agent_name or "",
            message=f"Anomaly detected: {anomaly_type}",
            details=event_details,
        )
        self.log(event)

    def log_agent_execution(
        self,
        user_id: str,
        agent_name: str,
        status: str,  # "started", "completed", "failed"
        duration: float | None = None,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Log agent execution."""
        event_type_map = {
            "started": AuditEventType.AGENT_STARTED,
            "completed": AuditEventType.AGENT_COMPLETED,
            "failed": AuditEventType.AGENT_FAILED,
        }

        severity_map = {
            "started": AuditSeverity.INFO,
            "completed": AuditSeverity.INFO,
            "failed": AuditSeverity.ERROR,
        }

        event_details = details or {}
        if duration is not None:
            event_details["duration_seconds"] = duration
        if error:
            event_details["error"] = error

        event = AuditEvent(
            event_type=event_type_map[status],
            severity=severity_map[status],
            user_id=user_id,
            agent_name=agent_name,
            message=f"Agent {status}" + (f" ({duration:.2f}s)" if duration else ""),
            details=event_details,
        )
        self.log(event)

    # Convenience methods for common logging scenarios

    def log_access_granted(
        self,
        user_id: str,
        resource: str,
        permission: str,
        agent_name: str | None = None,
    ):
        """Log successful access grant."""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            agent_name=agent_name or "",
            message=f"Access granted to resource: {resource}",
            details={"resource": resource, "permission": permission},
        )
        self.log(event)

    def log_access_denied(
        self,
        user_id: str,
        resource: str,
        permission: str,
        reason: str,
        agent_name: str | None = None,
    ):
        """Log access denial."""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            agent_name=agent_name or "",
            message=f"Access denied to resource: {resource}",
            details={"resource": resource, "permission": permission, "reason": reason},
        )
        self.log(event)

    def log_sensitive_data_redaction(
        self,
        user_id: str,
        fields_redacted: list,
        output_preview: str,
        agent_name: str | None = None,
    ):
        """Log sensitive data redaction."""
        # Truncate output preview
        truncated_preview = output_preview[:200] + ("..." if len(output_preview) > 200 else "")

        event = AuditEvent(
            event_type=AuditEventType.SENSITIVE_DATA_DETECTED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            agent_name=agent_name or "",
            message=f"Sensitive data redacted: {len(fields_redacted)} field(s)",
            details={
                "fields_redacted": fields_redacted,
                "output_preview": truncated_preview,
            },
        )
        self.log(event)


# Global audit logger instance (can be configured once)
_global_audit_logger: SecurityAuditLogger | None = None


def get_audit_logger() -> SecurityAuditLogger:
    """
    Get global audit logger instance.

    Returns:
        SecurityAuditLogger instance
    """
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = SecurityAuditLogger()
    return _global_audit_logger


def configure_audit_logger(
    log_file: str = "security_audit.log",
    max_bytes: int = 100 * 1024 * 1024,
    backup_count: int = 10,
    min_severity: AuditSeverity = AuditSeverity.INFO,
    also_log_to_console: bool = True,
):
    """
    Configure global audit logger.

    Args:
        log_file: Path to log file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        min_severity: Minimum severity to log
        also_log_to_console: Also output to console
    """
    global _global_audit_logger
    _global_audit_logger = SecurityAuditLogger(
        log_file, max_bytes, backup_count, min_severity, also_log_to_console
    )
