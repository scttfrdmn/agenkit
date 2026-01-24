#!/usr/bin/env python3
"""Tests for AG-UI WebSocket transport."""

import json

import pytest

from agenkit import Agent, Message
from agenkit.protocols.agui import AGUIAdapter, TextMessageChunk, TextMessageStart
from agenkit.protocols.agui.transports.websocket import (
    AGUIWebSocketStream,
    WebSocketMessageFormat,
)


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self, response_content: str = "Test response") -> None:
        """Initialize mock agent."""
        self._response_content = response_content

    @property
    def name(self) -> str:
        """Return agent name."""
        return "test_agent"

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["chat"]

    async def process(self, message: Message) -> Message:
        """Process message."""
        return Message(role="assistant", content=self._response_content)


class TestWebSocketMessageFormat:
    """Test WebSocket message formatting."""

    def test_format_event_basic(self) -> None:
        """Test basic event formatting."""
        event = TextMessageChunk(message_id="msg-123", content="Hello")
        formatted = WebSocketMessageFormat.format_event(event)

        # Should be valid JSON
        parsed = json.loads(formatted)

        assert parsed["event_type"] == "text_message_chunk"
        assert parsed["content"] == "Hello"
        assert parsed["message_id"] == "msg-123"

    def test_format_event_preserves_all_fields(self) -> None:
        """Test that all event fields are preserved."""
        event = TextMessageStart(
            message_id="msg-456",
            role="assistant",
            metadata={"agent_name": "test", "custom": "value"},
        )
        formatted = WebSocketMessageFormat.format_event(event)

        parsed = json.loads(formatted)

        assert parsed["event_type"] == "text_message_start"
        assert parsed["message_id"] == "msg-456"
        assert parsed["role"] == "assistant"
        assert parsed["metadata"]["agent_name"] == "test"
        assert parsed["metadata"]["custom"] == "value"
        assert "timestamp" in parsed

    def test_parse_message_valid_json(self) -> None:
        """Test parsing valid JSON message."""
        message = '{"message": "Hello", "type": "user"}'
        parsed = WebSocketMessageFormat.parse_message(message)

        assert parsed["message"] == "Hello"
        assert parsed["type"] == "user"

    def test_parse_message_invalid_json(self) -> None:
        """Test parsing invalid JSON raises error."""
        invalid_message = "{invalid json}"

        with pytest.raises(ValueError, match="Invalid JSON"):
            WebSocketMessageFormat.parse_message(invalid_message)

    def test_parse_message_empty_string(self) -> None:
        """Test parsing empty string raises error."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            WebSocketMessageFormat.parse_message("")

    def test_format_parse_round_trip(self) -> None:
        """Test format and parse round-trip."""
        event = TextMessageChunk(message_id="msg-789", content="Test content")

        # Format to JSON string
        formatted = WebSocketMessageFormat.format_event(event)

        # Parse back to dict
        parsed = WebSocketMessageFormat.parse_message(formatted)

        # Should preserve all fields
        assert parsed["event_type"] == "text_message_chunk"
        assert parsed["message_id"] == "msg-789"
        assert parsed["content"] == "Test content"


class TestAGUIWebSocketStream:
    """Test AG-UI WebSocket stream."""

    @pytest.mark.asyncio
    async def test_stream_events(self) -> None:
        """Test streaming events through WebSocket stream."""
        agent = MockAgent(response_content="Response")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Question")

        # Mock send callback
        sent_messages = []

        async def mock_send(msg: str) -> None:
            sent_messages.append(msg)

        stream = AGUIWebSocketStream(adapter, mock_send)

        events = []
        async for event in stream.stream_events(message):
            events.append(event)

        # Should produce events
        assert len(events) > 0

        # Should have standard event types
        event_types = [e.__class__.__name__ for e in events]
        assert "MetadataEvent" in event_types
        assert "TextMessageStart" in event_types
        assert "TextMessageComplete" in event_types

    @pytest.mark.asyncio
    async def test_send_event(self) -> None:
        """Test sending individual event over WebSocket."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)

        sent_messages = []

        async def mock_send(msg: str) -> None:
            sent_messages.append(msg)

        stream = AGUIWebSocketStream(adapter, mock_send)

        # Send an event
        event = TextMessageChunk(message_id="msg-123", content="Test")
        await stream.send_event(event)

        # Should have sent one message
        assert len(sent_messages) == 1

        # Message should be valid JSON
        parsed = json.loads(sent_messages[0])
        assert parsed["event_type"] == "text_message_chunk"
        assert parsed["content"] == "Test"

    @pytest.mark.asyncio
    async def test_send_multiple_events(self) -> None:
        """Test sending multiple events."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)

        sent_messages = []

        async def mock_send(msg: str) -> None:
            sent_messages.append(msg)

        stream = AGUIWebSocketStream(adapter, mock_send)

        # Send multiple events
        events = [
            TextMessageStart(message_id="msg-1"),
            TextMessageChunk(message_id="msg-1", content="Hello"),
            TextMessageChunk(message_id="msg-1", content=" world"),
        ]

        for event in events:
            await stream.send_event(event)

        # Should have sent all messages
        assert len(sent_messages) == 3

        # All should be valid JSON
        for msg in sent_messages:
            parsed = json.loads(msg)
            assert "event_type" in parsed


class TestWebSocketErrorHandling:
    """Test error handling in WebSocket transport."""

    def test_format_invalid_event(self) -> None:
        """Test formatting with invalid event data."""
        # This test ensures JSON serialization doesn't fail
        event = TextMessageChunk(message_id="msg-123", content="Test")
        formatted = WebSocketMessageFormat.format_event(event)

        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["content"] == "Test"

    def test_parse_malformed_json(self) -> None:
        """Test parsing malformed JSON."""
        malformed_messages = [
            "{key: value}",  # Missing quotes
            '{"key": undefined}',  # Invalid value
            "not json at all",
            '{"unclosed": ',
        ]

        for msg in malformed_messages:
            with pytest.raises(ValueError, match="Invalid JSON"):
                WebSocketMessageFormat.parse_message(msg)


class TestWebSocketMessageFormats:
    """Test various message formats."""

    def test_simple_message_format(self) -> None:
        """Test simple message format."""
        message = '{"message": "Hello"}'
        parsed = WebSocketMessageFormat.parse_message(message)

        assert "message" in parsed
        assert parsed["message"] == "Hello"

    def test_message_with_content_field(self) -> None:
        """Test message with content field instead of message."""
        message = '{"content": "Hello", "role": "user"}'
        parsed = WebSocketMessageFormat.parse_message(message)

        assert "content" in parsed
        assert parsed["content"] == "Hello"

    def test_complex_message(self) -> None:
        """Test complex message with nested data."""
        message = json.dumps(
            {
                "message": "Hello",
                "metadata": {"user_id": "123", "session": "abc"},
                "context": ["prev1", "prev2"],
            }
        )
        parsed = WebSocketMessageFormat.parse_message(message)

        assert parsed["message"] == "Hello"
        assert parsed["metadata"]["user_id"] == "123"
        assert len(parsed["context"]) == 2


class TestWebSocketSpecialCases:
    """Test special cases and edge conditions."""

    def test_empty_content(self) -> None:
        """Test formatting event with empty content."""
        event = TextMessageChunk(message_id="msg-123", content="")
        formatted = WebSocketMessageFormat.format_event(event)

        parsed = json.loads(formatted)
        assert parsed["content"] == ""

    def test_special_characters_in_content(self) -> None:
        """Test special characters in content."""
        special_text = 'Test with "quotes" and \n newlines and 中文 and emoji 🎉'
        event = TextMessageChunk(message_id="msg-123", content=special_text)
        formatted = WebSocketMessageFormat.format_event(event)

        # Should be valid JSON
        parsed = json.loads(formatted)

        # Special characters should be preserved
        assert "quotes" in parsed["content"]
        assert "中文" in parsed["content"]
        assert "🎉" in parsed["content"]

    def test_very_long_content(self) -> None:
        """Test formatting with very long content."""
        long_content = "A" * 100000
        event = TextMessageChunk(message_id="msg-123", content=long_content)
        formatted = WebSocketMessageFormat.format_event(event)

        # Should still be valid JSON
        parsed = json.loads(formatted)
        assert len(parsed["content"]) == 100000

    def test_nested_json_in_content(self) -> None:
        """Test content containing JSON-like strings."""
        json_content = '{"nested": "json", "value": 123}'
        event = TextMessageChunk(message_id="msg-123", content=json_content)
        formatted = WebSocketMessageFormat.format_event(event)

        # Should properly escape inner JSON
        parsed = json.loads(formatted)
        assert parsed["content"] == json_content


class TestWebSocketEventSequencing:
    """Test event sequencing over WebSocket."""

    @pytest.mark.asyncio
    async def test_event_order_preserved(self) -> None:
        """Test that event order is preserved."""
        agent = MockAgent(response_content="Test response")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Question")

        sent_messages = []

        async def mock_send(msg: str) -> None:
            sent_messages.append(msg)

        stream = AGUIWebSocketStream(adapter, mock_send)

        event_types = []
        async for event in stream.stream_events(message):
            event_types.append(event.__class__.__name__)

        # Event order should be: Metadata -> Start -> Chunks -> Complete
        assert event_types[0] == "MetadataEvent"
        assert event_types[1] == "TextMessageStart"
        assert event_types[-1] == "TextMessageComplete"

    @pytest.mark.asyncio
    async def test_message_id_consistency(self) -> None:
        """Test message ID consistency across events."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Test")

        sent_messages = []

        async def mock_send(msg: str) -> None:
            sent_messages.append(msg)

        stream = AGUIWebSocketStream(adapter, mock_send)

        message_ids = set()
        async for event in stream.stream_events(message):
            await stream.send_event(event)

            # Parse the sent message
            parsed = json.loads(sent_messages[-1])

            # Collect message IDs from text message events
            if "message_id" in parsed and parsed.get("event_type", "").startswith("text_message"):
                message_ids.add(parsed["message_id"])

        # All text message events should have the same message ID
        assert len(message_ids) == 1


class TestWebSocketComparison:
    """Test WebSocket format compared to SSE."""

    def test_websocket_vs_sse_format(self) -> None:
        """Test that WebSocket uses plain JSON vs SSE format."""
        event = TextMessageChunk(message_id="msg-123", content="Hello")

        # WebSocket format
        ws_formatted = WebSocketMessageFormat.format_event(event)

        # Should be plain JSON (not SSE format)
        assert not ws_formatted.startswith("data: ")
        assert not ws_formatted.endswith("\n\n")

        # Should be valid JSON
        parsed = json.loads(ws_formatted)
        assert parsed["content"] == "Hello"

    def test_websocket_single_line(self) -> None:
        """Test that WebSocket messages are single-line JSON."""
        event = TextMessageChunk(message_id="msg-123", content="Multi\nLine\nContent")
        formatted = WebSocketMessageFormat.format_event(event)

        # Should be valid JSON (newlines escaped)
        parsed = json.loads(formatted)
        assert parsed["content"] == "Multi\nLine\nContent"

        # The formatted string itself shouldn't contain actual newlines
        # (except those escaped in JSON)
        assert formatted.count("\n") <= 1  # JSON encoder might add one trailing newline


# FastAPI WebSocket integration tests (conditional)
try:
    from fastapi import WebSocket

    from agenkit.protocols.agui.transports.websocket import AGUIWebSocketHandler

    class TestFastAPIWebSocketIntegration:
        """Test FastAPI WebSocket integration."""

        def test_handler_creation(self) -> None:
            """Test creating FastAPI WebSocket handler."""
            agent = MockAgent()
            handler = AGUIWebSocketHandler(agent)

            assert handler is not None
            assert handler._agent == agent

        def test_handler_with_custom_agent_name(self) -> None:
            """Test handler with custom agent name."""
            agent = MockAgent()
            handler = AGUIWebSocketHandler(agent, agent_name="CustomAgent")

            assert handler._agent_name == "CustomAgent"

        def test_handler_metadata_configuration(self) -> None:
            """Test configuring metadata sending."""
            agent = MockAgent()

            handler_with_metadata = AGUIWebSocketHandler(agent, send_metadata=True)
            assert handler_with_metadata._send_metadata is True

            handler_without_metadata = AGUIWebSocketHandler(agent, send_metadata=False)
            assert handler_without_metadata._send_metadata is False

except ImportError:
    # FastAPI not available, skip these tests
    pass


class TestWebSocketMessageParsing:
    """Test parsing various WebSocket message formats."""

    def test_parse_user_message(self) -> None:
        """Test parsing typical user message."""
        message = json.dumps({"message": "What is the weather?"})
        parsed = WebSocketMessageFormat.parse_message(message)

        assert parsed["message"] == "What is the weather?"

    def test_parse_message_with_metadata(self) -> None:
        """Test parsing message with metadata."""
        message = json.dumps(
            {
                "message": "Hello",
                "user_id": "123",
                "session_id": "abc",
            }
        )
        parsed = WebSocketMessageFormat.parse_message(message)

        assert parsed["message"] == "Hello"
        assert parsed["user_id"] == "123"
        assert parsed["session_id"] == "abc"

    def test_parse_message_alternative_format(self) -> None:
        """Test parsing message with content field."""
        message = json.dumps({"content": "Hello", "role": "user"})
        parsed = WebSocketMessageFormat.parse_message(message)

        assert parsed["content"] == "Hello"
        assert parsed["role"] == "user"
