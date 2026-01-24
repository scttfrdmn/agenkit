#!/usr/bin/env python3
"""Tests for AG-UI protocol event types and data structures."""

import json
from datetime import datetime

import pytest

from agenkit.protocols.agui import (
    AGUIEvent,
    Attachment,
    AttachmentType,
    ErrorEvent,
    EventType,
    HeartbeatEvent,
    Interrupt,
    InterruptAction,
    InterruptReason,
    InterruptResponse,
    MetadataEvent,
    StateDelta,
    TextMessageChunk,
    TextMessageComplete,
    TextMessageStart,
    ToolCallChunk,
    ToolCallComplete,
    ToolCallStart,
    parse_event,
)


class TestEventTypes:
    """Test EventType enum."""

    def test_event_type_values(self) -> None:
        """Test that all event types have correct string values."""
        assert EventType.TEXT_MESSAGE_START == "text_message_start"
        assert EventType.TEXT_MESSAGE_CHUNK == "text_message_chunk"
        assert EventType.TEXT_MESSAGE_COMPLETE == "text_message_complete"
        assert EventType.TOOL_CALL_START == "tool_call_start"
        assert EventType.TOOL_CALL_CHUNK == "tool_call_chunk"
        assert EventType.TOOL_CALL_COMPLETE == "tool_call_complete"
        assert EventType.STATE_DELTA == "state_delta"
        assert EventType.INTERRUPT == "interrupt"
        assert EventType.ERROR == "error"
        assert EventType.ATTACHMENT == "attachment"
        assert EventType.METADATA == "metadata"
        assert EventType.HEARTBEAT == "heartbeat"

    def test_interrupt_reason_values(self) -> None:
        """Test InterruptReason enum values."""
        assert InterruptReason.APPROVAL_REQUIRED == "approval_required"
        assert InterruptReason.CLARIFICATION_NEEDED == "clarification_needed"
        assert InterruptReason.TOOL_CONFIRMATION == "tool_confirmation"
        assert InterruptReason.ESCALATION == "escalation"
        assert InterruptReason.USER_REQUESTED == "user_requested"

    def test_interrupt_action_values(self) -> None:
        """Test InterruptAction enum values."""
        assert InterruptAction.APPROVE == "approve"
        assert InterruptAction.REJECT == "reject"
        assert InterruptAction.EDIT == "edit"
        assert InterruptAction.RETRY == "retry"
        assert InterruptAction.ESCALATE == "escalate"
        assert InterruptAction.CANCEL == "cancel"

    def test_attachment_type_values(self) -> None:
        """Test AttachmentType enum values."""
        assert AttachmentType.IMAGE == "image"
        assert AttachmentType.AUDIO == "audio"
        assert AttachmentType.VIDEO == "video"
        assert AttachmentType.FILE == "file"
        assert AttachmentType.TRANSCRIPT == "transcript"


class TestTextMessageEvents:
    """Test text message event types."""

    def test_text_message_start_creation(self) -> None:
        """Test creating TextMessageStart event."""
        event = TextMessageStart(message_id="msg-123", role="assistant")

        assert event.event_type == EventType.TEXT_MESSAGE_START
        assert event.message_id == "msg-123"
        assert event.role == "assistant"
        assert event.timestamp is not None
        assert event.metadata == {}

    def test_text_message_chunk_creation(self) -> None:
        """Test creating TextMessageChunk event."""
        event = TextMessageChunk(message_id="msg-123", content="Hello ")

        assert event.event_type == EventType.TEXT_MESSAGE_CHUNK
        assert event.message_id == "msg-123"
        assert event.content == "Hello "

    def test_text_message_complete_creation(self) -> None:
        """Test creating TextMessageComplete event."""
        event = TextMessageComplete(
            message_id="msg-123", content="Hello, world!", finish_reason="stop"
        )

        assert event.event_type == EventType.TEXT_MESSAGE_COMPLETE
        assert event.message_id == "msg-123"
        assert event.content == "Hello, world!"
        assert event.finish_reason == "stop"

    def test_text_message_json_serialization(self) -> None:
        """Test JSON serialization of text message events."""
        event = TextMessageChunk(message_id="msg-123", content="test")
        event_dict = event.to_dict()

        assert event_dict["event_type"] == "text_message_chunk"
        assert event_dict["message_id"] == "msg-123"
        assert event_dict["content"] == "test"
        assert "timestamp" in event_dict

        # Test to_json_line
        json_line = event.to_json_line()
        parsed = json.loads(json_line)
        assert parsed["event_type"] == "text_message_chunk"
        assert parsed["content"] == "test"


class TestToolCallEvents:
    """Test tool call event types."""

    def test_tool_call_start_creation(self) -> None:
        """Test creating ToolCallStart event."""
        event = ToolCallStart(
            tool_call_id="tool-456", tool_name="search", arguments={"query": "python"}
        )

        assert event.event_type == EventType.TOOL_CALL_START
        assert event.tool_call_id == "tool-456"
        assert event.tool_name == "search"
        assert event.arguments == {"query": "python"}

    def test_tool_call_chunk_creation(self) -> None:
        """Test creating ToolCallChunk event."""
        event = ToolCallChunk(tool_call_id="tool-456", progress="Searching...", percentage=0.5)

        assert event.event_type == EventType.TOOL_CALL_CHUNK
        assert event.tool_call_id == "tool-456"
        assert event.progress == "Searching..."
        assert event.percentage == 0.5

    def test_tool_call_complete_creation(self) -> None:
        """Test creating ToolCallComplete event."""
        event = ToolCallComplete(
            tool_call_id="tool-456",
            tool_name="search",
            result={"results": ["a", "b"]},
            success=True,
        )

        assert event.event_type == EventType.TOOL_CALL_COMPLETE
        assert event.tool_call_id == "tool-456"
        assert event.tool_name == "search"
        assert event.result == {"results": ["a", "b"]}
        assert event.success is True
        assert event.error is None

    def test_tool_call_error(self) -> None:
        """Test ToolCallComplete with error."""
        event = ToolCallComplete(
            tool_call_id="tool-456",
            tool_name="search",
            result=None,
            success=False,
            error="Connection timeout",
        )

        assert event.success is False
        assert event.error == "Connection timeout"


class TestStateDelta:
    """Test StateDelta event."""

    def test_state_delta_set_operation(self) -> None:
        """Test StateDelta with set operation."""
        event = StateDelta(path=["user", "name"], operation="set", value="Alice")

        assert event.event_type == EventType.STATE_DELTA
        assert event.path == ["user", "name"]
        assert event.operation == "set"
        assert event.value == "Alice"
        assert event.previous_value is None

    def test_state_delta_delete_operation(self) -> None:
        """Test StateDelta with delete operation."""
        event = StateDelta(
            path=["user", "temp_data"], operation="delete", previous_value="old_value"
        )

        assert event.operation == "delete"
        assert event.previous_value == "old_value"

    def test_state_delta_append_operation(self) -> None:
        """Test StateDelta with append operation."""
        event = StateDelta(path=["messages"], operation="append", value={"id": 1, "text": "Hi"})

        assert event.operation == "append"
        assert event.value == {"id": 1, "text": "Hi"}

    def test_state_delta_merge_operation(self) -> None:
        """Test StateDelta with merge operation."""
        event = StateDelta(
            path=["config"], operation="merge", value={"theme": "dark", "locale": "en"}
        )

        assert event.operation == "merge"
        assert event.value == {"theme": "dark", "locale": "en"}


class TestInterrupt:
    """Test Interrupt event (HITL)."""

    def test_interrupt_approval_required(self) -> None:
        """Test Interrupt with approval required."""
        event = Interrupt(
            interrupt_id="int-789",
            reason=InterruptReason.APPROVAL_REQUIRED,
            message="Delete 100 files?",
            context={"file_count": 100},
            actions=[InterruptAction.APPROVE, InterruptAction.REJECT],
            timeout_seconds=30.0,
        )

        assert event.event_type == EventType.INTERRUPT
        assert event.interrupt_id == "int-789"
        assert event.reason == InterruptReason.APPROVAL_REQUIRED
        assert event.message == "Delete 100 files?"
        assert event.context == {"file_count": 100}
        assert event.actions == [InterruptAction.APPROVE, InterruptAction.REJECT]
        assert event.timeout_seconds == 30.0

    def test_interrupt_clarification_needed(self) -> None:
        """Test Interrupt with clarification needed."""
        event = Interrupt(
            reason=InterruptReason.CLARIFICATION_NEEDED,
            message="Which color do you prefer?",
            actions=[InterruptAction.EDIT],
        )

        assert event.reason == InterruptReason.CLARIFICATION_NEEDED
        assert event.actions == [InterruptAction.EDIT]

    def test_interrupt_default_actions(self) -> None:
        """Test Interrupt has default actions."""
        event = Interrupt(message="Question?")

        # Default actions should be approve/reject
        assert InterruptAction.APPROVE in event.actions
        assert InterruptAction.REJECT in event.actions

    def test_interrupt_response_creation(self) -> None:
        """Test InterruptResponse creation."""
        response = InterruptResponse(
            interrupt_id="int-789",
            action=InterruptAction.APPROVE,
            response="Approved with modifications",
            context={"modified": True},
        )

        assert response.interrupt_id == "int-789"
        assert response.action == InterruptAction.APPROVE
        assert response.response == "Approved with modifications"
        assert response.context == {"modified": True}


class TestErrorEvent:
    """Test ErrorEvent."""

    def test_error_event_creation(self) -> None:
        """Test creating ErrorEvent."""
        event = ErrorEvent(
            error_code="TIMEOUT",
            error_message="Request timed out after 30s",
            error_details={"timeout_seconds": 30, "endpoint": "/api/search"},
            recoverable=True,
        )

        assert event.event_type == EventType.ERROR
        assert event.error_code == "TIMEOUT"
        assert event.error_message == "Request timed out after 30s"
        assert event.error_details == {"timeout_seconds": 30, "endpoint": "/api/search"}
        assert event.recoverable is True

    def test_error_event_non_recoverable(self) -> None:
        """Test non-recoverable error."""
        event = ErrorEvent(
            error_code="FATAL", error_message="Critical system failure", recoverable=False
        )

        assert event.recoverable is False


class TestAttachment:
    """Test Attachment event (multimodal)."""

    def test_attachment_image_url(self) -> None:
        """Test Attachment with image URL."""
        event = Attachment(
            attachment_id="att-001",
            attachment_type=AttachmentType.IMAGE,
            content_url="https://example.com/image.png",
            content_type="image/png",
            filename="photo.png",
            size_bytes=102400,
            metadata={"width": 800, "height": 600},
        )

        assert event.event_type == EventType.ATTACHMENT
        assert event.attachment_id == "att-001"
        assert event.attachment_type == AttachmentType.IMAGE
        assert event.content_url == "https://example.com/image.png"
        assert event.content_type == "image/png"
        assert event.filename == "photo.png"
        assert event.size_bytes == 102400
        assert event.metadata == {"width": 800, "height": 600}

    def test_attachment_inline_data(self) -> None:
        """Test Attachment with inline base64 data."""
        event = Attachment(
            attachment_type=AttachmentType.AUDIO,
            content_data="base64encodedaudiodata==",
            content_type="audio/mp3",
            filename="voice.mp3",
        )

        assert event.attachment_type == AttachmentType.AUDIO
        assert event.content_data == "base64encodedaudiodata=="
        assert event.content_url is None

    def test_attachment_transcript(self) -> None:
        """Test Attachment with transcript."""
        event = Attachment(
            attachment_type=AttachmentType.TRANSCRIPT,
            content_data="Transcribed text here",
            metadata={"language": "en", "confidence": 0.95},
        )

        assert event.attachment_type == AttachmentType.TRANSCRIPT
        assert event.metadata["language"] == "en"


class TestMetadataAndHeartbeat:
    """Test MetadataEvent and HeartbeatEvent."""

    def test_metadata_event_creation(self) -> None:
        """Test creating MetadataEvent."""
        event = MetadataEvent(
            data={"agent_name": "assistant", "capabilities": ["chat", "search"], "version": "1.0"}
        )

        assert event.event_type == EventType.METADATA
        assert event.data["agent_name"] == "assistant"
        assert event.data["capabilities"] == ["chat", "search"]
        assert event.data["version"] == "1.0"

    def test_heartbeat_event_creation(self) -> None:
        """Test creating HeartbeatEvent."""
        event = HeartbeatEvent(sequence=42)

        assert event.event_type == EventType.HEARTBEAT
        assert event.sequence == 42


class TestEventParsing:
    """Test event parsing from dictionaries."""

    def test_parse_text_message_start(self) -> None:
        """Test parsing TextMessageStart from dict."""
        event_dict = {
            "event_type": "text_message_start",
            "message_id": "msg-123",
            "role": "assistant",
            "timestamp": "2026-01-23T12:00:00Z",
        }

        event = parse_event(event_dict)

        assert isinstance(event, TextMessageStart)
        assert event.message_id == "msg-123"
        assert event.role == "assistant"

    def test_parse_tool_call_complete(self) -> None:
        """Test parsing ToolCallComplete from dict."""
        event_dict = {
            "event_type": "tool_call_complete",
            "tool_call_id": "tool-456",
            "tool_name": "search",
            "result": {"data": "result"},
            "success": True,
        }

        event = parse_event(event_dict)

        assert isinstance(event, ToolCallComplete)
        assert event.tool_name == "search"
        assert event.success is True

    def test_parse_interrupt(self) -> None:
        """Test parsing Interrupt from dict."""
        event_dict = {
            "event_type": "interrupt",
            "interrupt_id": "int-789",
            "reason": "approval_required",
            "message": "Approve action?",
            "actions": ["approve", "reject"],
        }

        event = parse_event(event_dict)

        assert isinstance(event, Interrupt)
        assert event.reason == "approval_required"
        assert event.message == "Approve action?"

    def test_parse_state_delta(self) -> None:
        """Test parsing StateDelta from dict."""
        event_dict = {
            "event_type": "state_delta",
            "path": ["user", "preferences"],
            "operation": "merge",
            "value": {"theme": "dark"},
        }

        event = parse_event(event_dict)

        assert isinstance(event, StateDelta)
        assert event.path == ["user", "preferences"]
        assert event.operation == "merge"
        assert event.value == {"theme": "dark"}

    def test_parse_error_event(self) -> None:
        """Test parsing ErrorEvent from dict."""
        event_dict = {
            "event_type": "error",
            "error_code": "TIMEOUT",
            "error_message": "Timed out",
            "recoverable": True,
        }

        event = parse_event(event_dict)

        assert isinstance(event, ErrorEvent)
        assert event.error_code == "TIMEOUT"
        assert event.recoverable is True

    def test_parse_attachment(self) -> None:
        """Test parsing Attachment from dict."""
        event_dict = {
            "event_type": "attachment",
            "attachment_type": "image",
            "content_url": "https://example.com/img.png",
            "content_type": "image/png",
        }

        event = parse_event(event_dict)

        assert isinstance(event, Attachment)
        assert event.attachment_type == AttachmentType.IMAGE
        assert event.content_url == "https://example.com/img.png"

    def test_parse_missing_event_type(self) -> None:
        """Test parsing fails with missing event_type."""
        event_dict = {"message_id": "msg-123"}

        with pytest.raises(ValueError, match="missing 'event_type'"):
            parse_event(event_dict)

    def test_parse_unknown_event_type(self) -> None:
        """Test parsing fails with unknown event_type."""
        event_dict = {"event_type": "unknown_event"}

        with pytest.raises(ValueError, match="Unknown event type"):
            parse_event(event_dict)


class TestJSONSerialization:
    """Test JSON serialization round-trip."""

    def test_text_message_round_trip(self) -> None:
        """Test serialize and parse text message."""
        original = TextMessageChunk(message_id="msg-123", content="Hello")
        event_dict = original.to_dict()
        parsed = parse_event(event_dict)

        assert isinstance(parsed, TextMessageChunk)
        assert parsed.message_id == original.message_id
        assert parsed.content == original.content

    def test_tool_call_round_trip(self) -> None:
        """Test serialize and parse tool call."""
        original = ToolCallStart(
            tool_call_id="tool-456", tool_name="search", arguments={"q": "test"}
        )
        event_dict = original.to_dict()
        parsed = parse_event(event_dict)

        assert isinstance(parsed, ToolCallStart)
        assert parsed.tool_call_id == original.tool_call_id
        assert parsed.tool_name == original.tool_name
        assert parsed.arguments == original.arguments

    def test_interrupt_round_trip(self) -> None:
        """Test serialize and parse interrupt."""
        original = Interrupt(
            interrupt_id="int-789",
            reason=InterruptReason.APPROVAL_REQUIRED,
            message="Confirm?",
            actions=[InterruptAction.APPROVE],
        )
        event_dict = original.to_dict()
        parsed = parse_event(event_dict)

        assert isinstance(parsed, Interrupt)
        assert parsed.interrupt_id == original.interrupt_id
        assert parsed.reason == original.reason
        assert parsed.message == original.message


class TestTimestamps:
    """Test timestamp handling."""

    def test_automatic_timestamp(self) -> None:
        """Test that events get automatic timestamps."""
        event = TextMessageStart()

        assert event.timestamp is not None
        # Should be ISO 8601 format with Z suffix
        assert event.timestamp.endswith("Z")
        # Should be parseable
        datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))

    def test_custom_timestamp(self) -> None:
        """Test setting custom timestamp."""
        custom_time = "2026-01-23T15:30:00Z"
        event = TextMessageStart(timestamp=custom_time)

        assert event.timestamp == custom_time


class TestMetadata:
    """Test event metadata."""

    def test_default_empty_metadata(self) -> None:
        """Test events have empty metadata by default."""
        event = TextMessageStart()

        assert event.metadata == {}

    def test_custom_metadata(self) -> None:
        """Test setting custom metadata."""
        metadata = {"source": "agent-1", "session_id": "sess-123"}
        event = TextMessageStart(metadata=metadata)

        assert event.metadata == metadata
        assert event.metadata["source"] == "agent-1"
        assert event.metadata["session_id"] == "sess-123"
