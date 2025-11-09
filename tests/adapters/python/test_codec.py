"""Tests for protocol adapter codec."""

from datetime import datetime

import pytest

from agenkit.adapters.python import (
    InvalidMessageError,
    MalformedPayloadError,
    UnsupportedVersionError,
)
from agenkit.adapters.python.codec import (
    create_error_envelope,
    create_request_envelope,
    create_response_envelope,
    decode_bytes,
    decode_message,
    decode_tool_result,
    encode_bytes,
    encode_message,
    encode_tool_result,
    validate_envelope,
)
from agenkit.interfaces import Message, ToolResult


class TestMessageCodec:
    """Tests for Message encoding/decoding."""

    def test_encode_message(self):
        """Test encoding a Message to dict."""
        msg = Message(role="user", content="test content", metadata={"key": "value"})

        encoded = encode_message(msg)

        assert encoded["role"] == "user"
        assert encoded["content"] == "test content"
        assert encoded["metadata"] == {"key": "value"}
        assert "timestamp" in encoded

    def test_decode_message(self):
        """Test decoding a dict to Message."""
        data = {
            "role": "agent",
            "content": "response content",
            "metadata": {"key": "value"},
            "timestamp": "2025-11-08T12:34:56.789000+00:00",
        }

        msg = decode_message(data)

        assert msg.role == "agent"
        assert msg.content == "response content"
        assert msg.metadata == {"key": "value"}
        assert isinstance(msg.timestamp, datetime)

    def test_decode_message_missing_timestamp(self):
        """Test decoding message without timestamp uses current time."""
        data = {
            "role": "user",
            "content": "test",
            "metadata": {},
        }

        msg = decode_message(data)

        assert msg.role == "user"
        assert isinstance(msg.timestamp, datetime)

    def test_decode_message_malformed(self):
        """Test decoding malformed message raises error."""
        data = {"content": "missing role"}

        with pytest.raises(MalformedPayloadError) as exc_info:
            decode_message(data)

        assert "Failed to decode message" in str(exc_info.value)

    def test_roundtrip_message(self):
        """Test encoding then decoding preserves message."""
        original = Message(role="user", content="test", metadata={"x": 1})

        encoded = encode_message(original)
        decoded = decode_message(encoded)

        assert decoded.role == original.role
        assert decoded.content == original.content
        assert decoded.metadata == original.metadata


class TestToolResultCodec:
    """Tests for ToolResult encoding/decoding."""

    def test_encode_tool_result_success(self):
        """Test encoding a successful ToolResult."""
        result = ToolResult(success=True, data={"answer": 42}, metadata={"duration_ms": 100})

        encoded = encode_tool_result(result)

        assert encoded["success"] is True
        assert encoded["data"] == {"answer": 42}
        assert encoded["error"] is None
        assert encoded["metadata"] == {"duration_ms": 100}

    def test_encode_tool_result_failure(self):
        """Test encoding a failed ToolResult."""
        result = ToolResult(success=False, data=None, error="Something went wrong")

        encoded = encode_tool_result(result)

        assert encoded["success"] is False
        assert encoded["data"] is None
        assert encoded["error"] == "Something went wrong"

    def test_decode_tool_result_success(self):
        """Test decoding a successful ToolResult."""
        data = {"success": True, "data": {"result": 123}, "error": None, "metadata": {}}

        result = decode_tool_result(data)

        assert result.success is True
        assert result.data == {"result": 123}
        assert result.error is None

    def test_decode_tool_result_failure(self):
        """Test decoding a failed ToolResult."""
        data = {"success": False, "data": None, "error": "Error message", "metadata": {}}

        result = decode_tool_result(data)

        assert result.success is False
        assert result.data is None
        assert result.error == "Error message"

    def test_decode_tool_result_malformed(self):
        """Test decoding malformed ToolResult raises error."""
        data = {"data": "missing success field"}

        with pytest.raises(MalformedPayloadError) as exc_info:
            decode_tool_result(data)

        assert "Failed to decode tool result" in str(exc_info.value)

    def test_roundtrip_tool_result(self):
        """Test encoding then decoding preserves tool result."""
        original = ToolResult(success=True, data={"x": 1}, metadata={"y": 2})

        encoded = encode_tool_result(original)
        decoded = decode_tool_result(encoded)

        assert decoded.success == original.success
        assert decoded.data == original.data
        assert decoded.metadata == original.metadata


class TestEnvelopeCreation:
    """Tests for envelope creation functions."""

    def test_create_request_envelope(self):
        """Test creating a request envelope."""
        envelope = create_request_envelope(
            method="process", agent_name="test_agent", payload={"key": "value"}
        )

        assert envelope["version"] == "1.0"
        assert envelope["type"] == "request"
        assert "id" in envelope
        assert "timestamp" in envelope
        assert envelope["payload"]["method"] == "process"
        assert envelope["payload"]["agent_name"] == "test_agent"
        assert envelope["payload"]["key"] == "value"

    def test_create_response_envelope(self):
        """Test creating a response envelope."""
        envelope = create_response_envelope("req-123", {"result": "success"})

        assert envelope["version"] == "1.0"
        assert envelope["type"] == "response"
        assert envelope["id"] == "req-123"
        assert "timestamp" in envelope
        assert envelope["payload"] == {"result": "success"}

    def test_create_error_envelope(self):
        """Test creating an error envelope."""
        envelope = create_error_envelope(
            "req-123", "ERROR_CODE", "Error message", {"detail": "value"}
        )

        assert envelope["version"] == "1.0"
        assert envelope["type"] == "error"
        assert envelope["id"] == "req-123"
        assert "timestamp" in envelope
        assert envelope["payload"]["error_code"] == "ERROR_CODE"
        assert envelope["payload"]["error_message"] == "Error message"
        assert envelope["payload"]["error_details"] == {"detail": "value"}


class TestEnvelopeValidation:
    """Tests for envelope validation."""

    def test_validate_valid_envelope(self):
        """Test validating a valid envelope passes."""
        envelope = {
            "version": "1.0",
            "type": "request",
            "id": "req-123",
            "timestamp": "2025-11-08T12:34:56.000Z",
            "payload": {},
        }

        # Should not raise
        validate_envelope(envelope)

    def test_validate_missing_version(self):
        """Test validating envelope without version fails."""
        envelope = {
            "type": "request",
            "id": "req-123",
            "payload": {},
        }

        with pytest.raises(InvalidMessageError) as exc_info:
            validate_envelope(envelope)

        assert "version" in str(exc_info.value).lower()

    def test_validate_unsupported_version(self):
        """Test validating envelope with unsupported version fails."""
        envelope = {
            "version": "2.0",
            "type": "request",
            "id": "req-123",
            "payload": {},
        }

        with pytest.raises(UnsupportedVersionError) as exc_info:
            validate_envelope(envelope)

        assert "2.0" in str(exc_info.value)

    def test_validate_invalid_type(self):
        """Test validating envelope with invalid type fails."""
        envelope = {
            "version": "1.0",
            "type": "invalid_type",
            "id": "req-123",
            "payload": {},
        }

        with pytest.raises(InvalidMessageError) as exc_info:
            validate_envelope(envelope)

        assert "type" in str(exc_info.value).lower()

    def test_validate_missing_id(self):
        """Test validating envelope without id fails."""
        envelope = {
            "version": "1.0",
            "type": "request",
            "payload": {},
        }

        with pytest.raises(InvalidMessageError) as exc_info:
            validate_envelope(envelope)

        assert "id" in str(exc_info.value).lower()

    def test_validate_missing_payload(self):
        """Test validating envelope without payload fails."""
        envelope = {
            "version": "1.0",
            "type": "request",
            "id": "req-123",
        }

        with pytest.raises(InvalidMessageError) as exc_info:
            validate_envelope(envelope)

        assert "payload" in str(exc_info.value).lower()


class TestBytesCodec:
    """Tests for bytes encoding/decoding."""

    def test_encode_bytes(self):
        """Test encoding envelope to bytes."""
        envelope = create_request_envelope("process")
        encoded = encode_bytes(envelope)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_decode_bytes(self):
        """Test decoding bytes to envelope."""
        envelope = create_request_envelope("process")
        encoded = encode_bytes(envelope)
        decoded = decode_bytes(encoded)

        assert decoded["version"] == envelope["version"]
        assert decoded["type"] == envelope["type"]
        assert decoded["id"] == envelope["id"]

    def test_decode_invalid_json(self):
        """Test decoding invalid JSON raises error."""
        invalid_json = b"not json"

        with pytest.raises(MalformedPayloadError) as exc_info:
            decode_bytes(invalid_json)

        assert "JSON" in str(exc_info.value)

    def test_decode_invalid_utf8(self):
        """Test decoding invalid UTF-8 raises error."""
        invalid_utf8 = b"\xff\xfe"

        with pytest.raises(MalformedPayloadError) as exc_info:
            decode_bytes(invalid_utf8)

        assert "UTF-8" in str(exc_info.value)

    def test_roundtrip_bytes(self):
        """Test encoding then decoding preserves envelope."""
        original = create_request_envelope("process", "agent", {"key": "value"})
        encoded = encode_bytes(original)
        decoded = decode_bytes(encoded)

        assert decoded["version"] == original["version"]
        assert decoded["type"] == original["type"]
        assert decoded["payload"] == original["payload"]
