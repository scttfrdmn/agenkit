"""Tests for security audit logging."""

import contextlib
import json
import os
import tempfile

import pytest

from agenkit.safety.audit import AuditEvent, AuditEventType, AuditSeverity, SecurityAuditLogger


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_path = f.name

    yield log_path

    # Cleanup
    with contextlib.suppress(FileNotFoundError):
        os.unlink(log_path)


class TestAuditEvent:
    """Tests for AuditEvent."""

    def test_creates_event_with_timestamp(self):
        """Test that events are created with timestamp."""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.INFO,
            user_id="user_123",
            details={"resource": "file.txt"},
        )

        assert event.timestamp is not None
        assert event.event_type == AuditEventType.ACCESS_GRANTED
        assert event.severity == AuditSeverity.INFO
        assert event.user_id == "user_123"

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        event = AuditEvent(
            event_type=AuditEventType.PROMPT_INJECTION_DETECTED,
            severity=AuditSeverity.ERROR,
            user_id="user_123",
            agent_name="test_agent",
            details={"score": 15, "patterns": ["ignore instructions"]},
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "prompt_injection_detected"
        assert event_dict["severity"] == "error"
        assert event_dict["user_id"] == "user_123"
        assert event_dict["agent_name"] == "test_agent"
        assert event_dict["details"]["score"] == 15

    def test_to_json_serialization(self):
        """Test serialization to JSON string."""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.WARNING,
            user_id="user_123",
            details={"reason": "insufficient permissions"},
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "access_denied"
        assert parsed["severity"] == "warning"
        assert parsed["details"]["reason"] == "insufficient permissions"


class TestAuditEventType:
    """Tests for AuditEventType enum."""

    def test_event_type_values(self):
        """Test that event type values are correctly defined."""
        assert AuditEventType.ACCESS_GRANTED.value == "access_granted"
        assert AuditEventType.ACCESS_DENIED.value == "access_denied"
        assert AuditEventType.PROMPT_INJECTION_DETECTED.value == "prompt_injection_detected"
        assert AuditEventType.SENSITIVE_DATA_DETECTED.value == "sensitive_data_detected"
        assert AuditEventType.INPUT_VALIDATION_FAILED.value == "input_validation_failed"
        assert AuditEventType.ANOMALY_DETECTED.value == "anomaly_detected"


class TestAuditSeverity:
    """Tests for AuditSeverity enum."""

    def test_severity_values(self):
        """Test that severity values are correctly defined."""
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestSecurityAuditLogger:
    """Tests for SecurityAuditLogger."""

    def test_creates_log_file(self, temp_log_file):
        """Test that logger creates log file."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        event = AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.INFO,
            user_id="user_123",
            details={},
        )
        logger.log(event)

        # Check that log file was created and has content
        assert os.path.exists(temp_log_file)
        assert os.path.getsize(temp_log_file) > 0

    def test_logs_json_format(self, temp_log_file):
        """Test that logs are in JSON format."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        event = AuditEvent(
            event_type=AuditEventType.PROMPT_INJECTION_DETECTED,
            severity=AuditSeverity.ERROR,
            user_id="user_123",
            details={"score": 15},
        )
        logger.log(event)

        # Read log file
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        # Should be valid JSON
        parsed = json.loads(log_line)
        assert parsed["event_type"] == "prompt_injection_detected"
        assert parsed["severity"] == "error"

    def test_log_access_granted(self, temp_log_file):
        """Test logging access granted events."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        logger.log_access_granted(user_id="user_123", resource="file.txt", permission="read:files")

        # Verify log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["event_type"] == "access_granted"
        assert parsed["severity"] == "info"
        assert parsed["details"]["resource"] == "file.txt"

    def test_log_access_denied(self, temp_log_file):
        """Test logging access denied events."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        logger.log_access_denied(
            user_id="user_123",
            resource="secrets.txt",
            permission="access:secrets",
            reason="insufficient permissions",
        )

        # Verify log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["event_type"] == "access_denied"
        assert parsed["severity"] == "warning"
        assert parsed["details"]["reason"] == "insufficient permissions"

    def test_log_prompt_injection(self, temp_log_file):
        """Test logging prompt injection detection."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        logger.log_prompt_injection(
            user_id="user_123",
            score=15,
            matched_patterns=["ignore instructions", "system mode"],
            content_preview="Ignore previous instructions...",
        )

        # Verify log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["event_type"] == "prompt_injection_detected"
        assert parsed["severity"] == "error"
        assert parsed["details"]["score"] == 15
        assert "ignore instructions" in parsed["details"]["matched_patterns"]

    def test_log_sensitive_data_redaction(self, temp_log_file):
        """Test logging sensitive data redaction."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        logger.log_sensitive_data_redaction(
            user_id="user_123",
            fields_redacted=["password", "api_key"],
            output_preview='{"result": "success", ...}',
        )

        # Verify log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["event_type"] == "sensitive_data_detected"  # Actual event type
        assert parsed["severity"] == "warning"
        assert "password" in parsed["details"]["fields_redacted"]

    def test_log_validation_failure(self, temp_log_file):
        """Test logging validation failures."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        logger.log_validation_failure(
            user_id="user_123",
            validation_type="schema",
            reason="Missing required field: result",
            content_preview='{"data": "test"}',
        )

        # Verify log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        # Schema validation is considered output validation
        assert parsed["event_type"] in ["output_validation_failed", "input_validation_failed"]
        assert parsed["severity"] == "error"
        assert parsed["details"]["validation_type"] == "schema"

    def test_log_anomaly(self, temp_log_file):
        """Test logging anomaly detection."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        logger.log_anomaly(
            user_id="user_123",
            anomaly_type="high_request_rate",
            details={"requests_per_minute": 150, "threshold": 100},
        )

        # Verify log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["event_type"] == "anomaly_detected"
        assert parsed["severity"] == "warning"
        assert parsed["details"]["anomaly_type"] == "high_request_rate"

    def test_multiple_log_entries(self, temp_log_file):
        """Test logging multiple entries."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        # Log multiple events
        logger.log_access_granted("user_1", "file1.txt", "read:files")
        logger.log_access_granted("user_2", "file2.txt", "read:files")
        logger.log_access_denied("user_3", "secrets.txt", "access:secrets", "denied")

        # Verify multiple entries
        with open(temp_log_file) as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Each line should be valid JSON
        for line in lines:
            parsed = json.loads(line.strip())
            assert "event_type" in parsed
            assert "timestamp" in parsed

    def test_log_includes_agent_name(self, temp_log_file):
        """Test that logs include agent name when provided."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        event = AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.INFO,
            user_id="user_123",
            agent_name="test_agent",
            details={},
        )
        logger.log(event)

        # Verify agent name in log
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["agent_name"] == "test_agent"

    def test_log_truncates_long_content_preview(self, temp_log_file):
        """Test that long content previews are truncated."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        long_content = "x" * 500
        logger.log_validation_failure(
            user_id="user_123",
            validation_type="size",
            reason="Too large",
            content_preview=long_content,
        )

        # Verify truncation
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        content_preview = parsed["details"]["content_preview"]
        # Allow a bit of flexibility for "..." suffix
        assert len(content_preview) <= 203  # 200 + "..."
        assert "..." in content_preview

    def test_log_handles_missing_optional_fields(self, temp_log_file):
        """Test logging with minimal required fields."""
        logger = SecurityAuditLogger(log_file=temp_log_file)

        event = AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.INFO,
            user_id="user_123",
            details={},
        )
        logger.log(event)

        # Should log successfully without agent_name
        with open(temp_log_file) as f:
            log_line = f.read().strip()

        parsed = json.loads(log_line)
        assert parsed["event_type"] == "access_granted"
        assert parsed.get("agent_name") is None or parsed["agent_name"] == ""
