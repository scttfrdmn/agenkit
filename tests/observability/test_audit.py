"""Tests for audit logging."""

import io
import json
import tempfile
from pathlib import Path

from agenkit.observability import (AuditEvent, AuditEventType, AuditLogger,
                                   AuditSeverity, ConsoleAuditAdapter,
                                   FileAuditAdapter, StructuredAuditAdapter)


def test_audit_event_creation():
    """Test creating an audit event."""
    event = AuditEvent(
        event_type=AuditEventType.AUTH_SUCCESS,
        severity=AuditSeverity.INFO,
        message="User authenticated successfully",
        actor="user123",
        action="authenticate",
        result="success",
    )

    assert event.event_type == AuditEventType.AUTH_SUCCESS
    assert event.severity == AuditSeverity.INFO
    assert event.message == "User authenticated successfully"
    assert event.actor == "user123"
    assert event.action == "authenticate"
    assert event.result == "success"
    assert event.timestamp is not None


def test_audit_event_to_dict():
    """Test converting audit event to dictionary."""
    event = AuditEvent(
        event_type=AuditEventType.AUTH_FAILURE,
        severity=AuditSeverity.WARNING,
        message="Authentication failed",
        actor="user456",
        metadata={"reason": "invalid_password"},
    )

    event_dict = event.to_dict()

    assert event_dict["event_type"] == "auth_failure"
    assert event_dict["severity"] == "warning"
    assert event_dict["message"] == "Authentication failed"
    assert event_dict["actor"] == "user456"
    assert event_dict["metadata"]["reason"] == "invalid_password"
    assert isinstance(event_dict["timestamp"], str)


def test_console_audit_adapter(capsys):
    """Test console audit adapter."""
    adapter = ConsoleAuditAdapter(use_colors=False)

    event = AuditEvent(
        event_type=AuditEventType.AUTHORIZATION,
        severity=AuditSeverity.INFO,
        message="Access granted",
        actor="user789",
        resource="document123",
        action="read",
        result="allowed",
    )

    adapter.log_event(event)

    captured = capsys.readouterr()
    assert "INFO" in captured.out
    assert "[authorization]" in captured.out
    assert "actor=user789" in captured.out
    assert "resource=document123" in captured.out
    assert "Access granted" in captured.out


def test_structured_audit_adapter():
    """Test structured audit adapter."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)

    event = AuditEvent(
        event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
        severity=AuditSeverity.WARNING,
        message="Rate limit exceeded",
        actor="client123",
        resource="/api/process",
        metadata={"limit": 100, "window": "1m"},
    )

    adapter.log_event(event)

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "rate_limit_exceeded"
    assert logged["severity"] == "warning"
    assert logged["message"] == "Rate limit exceeded"
    assert logged["actor"] == "client123"
    assert logged["metadata"]["limit"] == 100


def test_file_audit_adapter_structured():
    """Test file audit adapter with structured format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        adapter = FileAuditAdapter(str(log_path), structured=True)

        event = AuditEvent(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.INFO,
            message="Configuration updated",
            actor="admin",
            resource="timeout.max_duration",
            metadata={"old_value": 30, "new_value": 60},
        )

        adapter.log_event(event)

        # Read the log file
        assert log_path.exists()
        with open(log_path) as f:
            logged = json.loads(f.read())

        assert logged["event_type"] == "configuration_change"
        assert logged["actor"] == "admin"
        assert logged["metadata"]["old_value"] == 30


def test_file_audit_adapter_human_readable():
    """Test file audit adapter with human-readable format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        adapter = FileAuditAdapter(str(log_path), structured=False)

        event = AuditEvent(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.ERROR,
            message="SQL injection attempt detected",
            actor="malicious_user",
        )

        adapter.log_event(event)

        # Read the log file
        assert log_path.exists()
        with open(log_path) as f:
            content = f.read()

        assert "[security_violation]" in content
        assert "actor=malicious_user" in content
        assert "SQL injection attempt detected" in content


def test_audit_logger_log_auth_attempt():
    """Test logging authentication attempt."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_auth_attempt(
        user_id="user123",
        success=True,
        method="password",
        ip_address="192.168.1.1",
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "auth_success"
    assert logged["actor"] == "user123"
    assert logged["metadata"]["method"] == "password"
    assert logged["metadata"]["ip_address"] == "192.168.1.1"


def test_audit_logger_log_authorization():
    """Test logging authorization decision."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_authorization(
        user_id="user456",
        resource="document123",
        action="delete",
        allowed=False,
        reason="insufficient_permissions",
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "authorization"
    assert logged["severity"] == "warning"
    assert logged["actor"] == "user456"
    assert logged["result"] == "denied"
    assert logged["metadata"]["reason"] == "insufficient_permissions"


def test_audit_logger_log_rate_limit_exceeded():
    """Test logging rate limit violation."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_rate_limit_exceeded(
        client_id="192.168.1.100",
        endpoint="/api/process",
        limit=100,
        window="1m",
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "rate_limit_exceeded"
    assert logged["severity"] == "warning"
    assert logged["actor"] == "192.168.1.100"
    assert logged["metadata"]["limit"] == 100


def test_audit_logger_log_validation_failure():
    """Test logging validation failure."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_validation_failure(
        message_id="msg123",
        reason="field_required",
        field="email",
        value=None,
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "validation_failure"
    assert logged["resource"] == "msg123"
    assert logged["metadata"]["field"] == "email"


def test_audit_logger_log_configuration_change():
    """Test logging configuration change."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_configuration_change(
        user_id="admin",
        component="timeout_middleware",
        parameter="max_duration",
        old_value=30,
        new_value=60,
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "configuration_change"
    assert logged["actor"] == "admin"
    assert logged["metadata"]["old_value"] == 30
    assert logged["metadata"]["new_value"] == 60


def test_audit_logger_log_security_violation():
    """Test logging security violation."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_security_violation(
        client_id="attacker",
        violation_type="sql_injection",
        description="Attempted SQL injection in search parameter",
        severity=AuditSeverity.CRITICAL,
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "security_violation"
    assert logged["severity"] == "critical"
    assert logged["actor"] == "attacker"


def test_audit_logger_log_suspicious_activity():
    """Test logging suspicious activity."""
    stream = io.StringIO()
    adapter = StructuredAuditAdapter(stream=stream)
    logger = AuditLogger([adapter])

    logger.log_suspicious_activity(
        client_id="192.168.1.200",
        activity_type="brute_force",
        description="Multiple failed login attempts",
        indicators=["10_failed_logins_1min", "different_user_agents"],
    )

    stream.seek(0)
    logged = json.loads(stream.read())

    assert logged["event_type"] == "suspicious_activity"
    assert logged["severity"] == "warning"
    assert logged["metadata"]["indicators"] == ["10_failed_logins_1min", "different_user_agents"]


def test_audit_logger_multiple_adapters(capsys):
    """Test logger with multiple adapters."""
    stream = io.StringIO()
    adapters = [
        ConsoleAuditAdapter(use_colors=False),
        StructuredAuditAdapter(stream=stream),
    ]
    logger = AuditLogger(adapters)

    logger.log_auth_attempt(user_id="user123", success=True)

    # Check console output
    captured = capsys.readouterr()
    assert "user123" in captured.out

    # Check structured output
    stream.seek(0)
    logged = json.loads(stream.read())
    assert logged["actor"] == "user123"


def test_audit_logger_default_adapter(capsys):
    """Test logger with default console adapter."""
    logger = AuditLogger()

    logger.log_auth_attempt(user_id="user456", success=False, reason="invalid_password")

    captured = capsys.readouterr()
    assert "user456" in captured.out
    assert "failed" in captured.out
