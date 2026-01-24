#!/usr/bin/env python3
"""Tests for AG-UI adapter."""

from collections.abc import AsyncIterator

import pytest

from agenkit import Agent, Message
from agenkit.protocols.agui import (
    AGUIAdapter,
    ErrorEvent,
    MetadataEvent,
    StreamingAGUIAdapter,
    TextMessageChunk,
    TextMessageComplete,
    TextMessageStart,
    wrap_agent_as_agui,
)


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(
        self,
        response_content: str = "Hello, world!",
        response_metadata: dict | None = None,
        should_raise: Exception | None = None,
    ) -> None:
        """Initialize mock agent."""
        self._response_content = response_content
        self._response_metadata = response_metadata or {}
        self._should_raise = should_raise

    @property
    def name(self) -> str:
        """Return agent name."""
        return "mock_agent"

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["chat", "reasoning"]

    async def process(self, message: Message) -> Message:
        """Process message."""
        if self._should_raise:
            raise self._should_raise

        return Message(
            role="assistant",
            content=self._response_content,
            metadata=self._response_metadata,
        )


class MockStreamingAgent(Agent):
    """Mock agent with streaming support."""

    def __init__(self, chunks: list[str]) -> None:
        """Initialize mock streaming agent."""
        self._chunks = chunks

    @property
    def name(self) -> str:
        """Return agent name."""
        return "streaming_agent"

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["chat", "streaming"]

    async def process(self, message: Message) -> Message:
        """Process message."""
        content = "".join(self._chunks)
        return Message(role="assistant", content=content)

    async def stream(self, message: Message) -> AsyncIterator[str]:
        """Stream response chunks."""
        for chunk in self._chunks:
            yield chunk


class TestAGUIAdapter:
    """Test AGUIAdapter class."""

    @pytest.mark.asyncio
    async def test_adapter_initialization(self) -> None:
        """Test adapter initialization."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)

        assert adapter.agent == agent
        assert adapter.agent_name == "mock_agent"

    @pytest.mark.asyncio
    async def test_adapter_custom_name(self) -> None:
        """Test adapter with custom agent name."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent, agent_name="custom_name")

        assert adapter.agent_name == "custom_name"

    @pytest.mark.asyncio
    async def test_stream_events_basic(self) -> None:
        """Test basic event streaming."""
        agent = MockAgent(response_content="Test response")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should have: Metadata, Start, Chunks, Complete
        assert len(events) >= 4

        # Check event types
        assert isinstance(events[0], MetadataEvent)
        assert isinstance(events[1], TextMessageStart)
        assert any(isinstance(e, TextMessageChunk) for e in events)
        assert isinstance(events[-1], TextMessageComplete)

    @pytest.mark.asyncio
    async def test_metadata_event_content(self) -> None:
        """Test metadata event contains agent info."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        metadata_event = events[0]
        assert isinstance(metadata_event, MetadataEvent)
        assert metadata_event.data["agent_name"] == "mock_agent"
        assert metadata_event.data["agent_type"] == "MockAgent"
        assert metadata_event.data["capabilities"] == ["chat", "reasoning"]
        assert metadata_event.data["protocol_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_text_message_start_event(self) -> None:
        """Test TextMessageStart event."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        start_event = events[1]
        assert isinstance(start_event, TextMessageStart)
        assert start_event.role == "assistant"
        assert start_event.message_id is not None
        assert start_event.metadata["agent_name"] == "mock_agent"

    @pytest.mark.asyncio
    async def test_text_message_chunks(self) -> None:
        """Test TextMessageChunk events."""
        agent = MockAgent(response_content="A" * 200)  # Long response for multiple chunks
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        chunks = []
        async for event in adapter.stream_events(message):
            if isinstance(event, TextMessageChunk):
                chunks.append(event)

        # Should have multiple chunks
        assert len(chunks) > 1

        # Each chunk should have content
        for chunk in chunks:
            assert chunk.content
            assert chunk.message_id is not None
            assert "chunk_index" in chunk.metadata

        # Chunks should reconstruct full content
        full_content = "".join(c.content for c in chunks)
        assert full_content == "A" * 200

    @pytest.mark.asyncio
    async def test_text_message_complete(self) -> None:
        """Test TextMessageComplete event."""
        agent = MockAgent(
            response_content="Test response", response_metadata={"test_key": "test_value"}
        )
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        complete_event = events[-1]
        assert isinstance(complete_event, TextMessageComplete)
        assert complete_event.content == "Test response"
        assert complete_event.finish_reason == "stop"
        assert complete_event.metadata["agent_name"] == "mock_agent"
        assert complete_event.metadata["response_metadata"]["test_key"] == "test_value"

    @pytest.mark.asyncio
    async def test_message_id_consistency(self) -> None:
        """Test message ID is consistent across events."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Get message ID from start event
        start_event = None
        for event in events:
            if isinstance(event, TextMessageStart):
                start_event = event
                break

        assert start_event is not None
        message_id = start_event.message_id

        # All text message events should have same message_id
        for event in events:
            if isinstance(event, (TextMessageStart, TextMessageChunk, TextMessageComplete)):
                assert event.message_id == message_id

    @pytest.mark.asyncio
    async def test_custom_message_id(self) -> None:
        """Test using custom message ID."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")
        custom_id = "custom-msg-123"

        events = []
        async for event in adapter.stream_events(message, message_id=custom_id):
            events.append(event)

        # All text message events should use custom ID
        for event in events:
            if isinstance(event, (TextMessageStart, TextMessageChunk, TextMessageComplete)):
                assert event.message_id == custom_id

    @pytest.mark.asyncio
    async def test_skip_metadata_emission(self) -> None:
        """Test skipping metadata event emission."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message, emit_metadata=False):
            events.append(event)

        # Should not have metadata event
        assert not any(isinstance(e, MetadataEvent) for e in events)

        # Should still have other events
        assert any(isinstance(e, TextMessageStart) for e in events)

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test error handling converts exceptions to ErrorEvents."""
        error = ValueError("Test error")
        agent = MockAgent(should_raise=error)
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should have error event
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1

        error_event = error_events[0]
        assert error_event.error_code == "ValueError"
        assert error_event.error_message == "Test error"
        assert error_event.recoverable is True

        # Should also have completion with error finish reason
        complete_events = [e for e in events if isinstance(e, TextMessageComplete)]
        assert len(complete_events) == 1
        assert complete_events[0].finish_reason == "error"
        assert "error" in complete_events[0].metadata

    @pytest.mark.asyncio
    async def test_process_non_streaming(self) -> None:
        """Test non-streaming process method."""
        agent = MockAgent(response_content="Test response")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        result = await adapter.process(message)

        assert result.role == "assistant"
        assert result.content == "Test response"
        assert "agent_name" in result.metadata


class TestStreamingAGUIAdapter:
    """Test StreamingAGUIAdapter class."""

    @pytest.mark.asyncio
    async def test_streaming_agent_native_streaming(self) -> None:
        """Test streaming with agent that supports streaming."""
        chunks = ["Hello", ", ", "world", "!"]
        agent = MockStreamingAgent(chunks)
        adapter = StreamingAGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should have metadata, start, chunks, complete
        assert len(events) >= 6  # Metadata + Start + 4 chunks + Complete

        # Check streaming chunks
        chunk_events = [e for e in events if isinstance(e, TextMessageChunk)]
        assert len(chunk_events) == 4

        # Chunks should match input
        chunk_contents = [e.content for e in chunk_events]
        assert chunk_contents == chunks

        # Complete should have full content
        complete_event = events[-1]
        assert isinstance(complete_event, TextMessageComplete)
        assert complete_event.content == "Hello, world!"
        assert complete_event.metadata.get("streamed") is True

    @pytest.mark.asyncio
    async def test_streaming_adapter_fallback(self) -> None:
        """Test StreamingAGUIAdapter falls back for non-streaming agents."""
        agent = MockAgent(response_content="Test")
        adapter = StreamingAGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should still work with chunked streaming
        assert any(isinstance(e, TextMessageStart) for e in events)
        assert any(isinstance(e, TextMessageComplete) for e in events)

    @pytest.mark.asyncio
    async def test_streaming_error_handling(self) -> None:
        """Test error handling in streaming adapter."""

        class FailingStreamAgent(Agent):
            """Agent that fails during streaming."""

            @property
            def name(self) -> str:
                return "failing_agent"

            @property
            def capabilities(self) -> list[str]:
                return []

            async def process(self, message: Message) -> Message:
                return Message(role="assistant", content="")

            async def stream(self, message: Message) -> AsyncIterator[str]:
                """Stream that raises error."""
                yield "Start"
                raise RuntimeError("Stream error")

        agent = FailingStreamAgent()
        adapter = StreamingAGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should have error event
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1
        assert error_events[0].error_code == "RuntimeError"
        assert error_events[0].error_message == "Stream error"


class TestWrapAgentAsAGUI:
    """Test wrap_agent_as_agui convenience function."""

    @pytest.mark.asyncio
    async def test_wrap_agent_basic(self) -> None:
        """Test wrapping agent with convenience function."""
        agent = MockAgent(response_content="Test")
        message = Message(role="user", content="Hello")

        events = []
        async for event in wrap_agent_as_agui(agent, message):
            events.append(event)

        # Should produce standard event sequence
        assert len(events) >= 3
        assert isinstance(events[0], MetadataEvent)
        assert isinstance(events[1], TextMessageStart)
        assert isinstance(events[-1], TextMessageComplete)

    @pytest.mark.asyncio
    async def test_wrap_agent_custom_name(self) -> None:
        """Test wrapping agent with custom name."""
        agent = MockAgent()
        message = Message(role="user", content="Hello")

        events = []
        async for event in wrap_agent_as_agui(agent, message, agent_name="CustomAgent"):
            events.append(event)

        # Metadata should have custom name
        metadata_event = events[0]
        assert isinstance(metadata_event, MetadataEvent)
        assert metadata_event.data["agent_name"] == "CustomAgent"


class TestEventSequencing:
    """Test event sequencing and ordering."""

    @pytest.mark.asyncio
    async def test_event_order(self) -> None:
        """Test events are emitted in correct order."""
        agent = MockAgent(response_content="Test")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        event_types = []
        async for event in adapter.stream_events(message):
            event_types.append(event.__class__.__name__)

        # Check order: Metadata -> Start -> Chunks -> Complete
        assert event_types[0] == "MetadataEvent"
        assert event_types[1] == "TextMessageStart"
        assert event_types[-1] == "TextMessageComplete"

        # All chunks should be between start and complete
        start_idx = event_types.index("TextMessageStart")
        complete_idx = event_types.index("TextMessageComplete")

        for i in range(start_idx + 1, complete_idx):
            assert event_types[i] == "TextMessageChunk"

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        """Test handling of empty response."""
        agent = MockAgent(response_content="")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should still have start and complete
        assert any(isinstance(e, TextMessageStart) for e in events)
        assert any(isinstance(e, TextMessageComplete) for e in events)

        # Complete should have empty content
        complete_event = [e for e in events if isinstance(e, TextMessageComplete)][0]
        assert complete_event.content == ""


class TestMessageIDGeneration:
    """Test message ID generation."""

    @pytest.mark.asyncio
    async def test_message_id_uniqueness(self) -> None:
        """Test generated message IDs are unique."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        message_ids = set()

        for _ in range(10):
            events = []
            async for event in adapter.stream_events(message):
                events.append(event)

            start_event = [e for e in events if isinstance(e, TextMessageStart)][0]
            message_ids.add(start_event.message_id)

        # All IDs should be unique
        assert len(message_ids) == 10

    @pytest.mark.asyncio
    async def test_message_id_format(self) -> None:
        """Test message ID has expected format."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hello")

        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        start_event = [e for e in events if isinstance(e, TextMessageStart)][0]
        message_id = start_event.message_id

        # Should start with "msg-" prefix
        assert message_id.startswith("msg-")

        # Should have 12 hex characters after prefix
        hex_part = message_id[4:]
        assert len(hex_part) == 12
        assert all(c in "0123456789abcdef" for c in hex_part)
