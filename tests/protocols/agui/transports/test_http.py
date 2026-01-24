#!/usr/bin/env python3
"""Tests for AG-UI HTTP/SSE transport."""

import json

import pytest

from agenkit import Agent, Message
from agenkit.protocols.agui import AGUIAdapter, TextMessageChunk, TextMessageStart
from agenkit.protocols.agui.transports.http import (
    AGUISSEStream,
    SSEFormatter,
    create_sse_response_iterator,
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


class TestSSEFormatter:
    """Test SSE formatter."""

    def test_format_event_basic(self) -> None:
        """Test basic event formatting."""
        event = TextMessageChunk(message_id="msg-123", content="Hello")
        formatted = SSEFormatter.format_event(event)

        # Should start with "data:" and end with double newline
        assert formatted.startswith("data: ")
        assert formatted.endswith("\n\n")

        # Should contain valid JSON
        json_str = formatted[6:-2]  # Remove "data: " and "\n\n"
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "text_message_chunk"
        assert parsed["content"] == "Hello"
        assert parsed["message_id"] == "msg-123"

    def test_format_event_with_event_name(self) -> None:
        """Test event formatting with event name."""
        event = TextMessageStart(message_id="msg-123")
        formatted = SSEFormatter.format_event(event, include_event_name=True)

        lines = formatted.split("\n")

        # Should have: event line, data line, empty line, empty line
        assert lines[0].startswith("event: ")
        assert lines[1].startswith("data: ")
        assert lines[2] == ""
        assert lines[3] == ""

        # Event name should be correct
        assert "event: text_message_start" in formatted

    def test_format_comment(self) -> None:
        """Test comment formatting."""
        comment = SSEFormatter.format_comment("test comment")

        assert comment == ": test comment\n\n"
        assert comment.startswith(":")

    def test_format_retry(self) -> None:
        """Test retry directive formatting."""
        retry = SSEFormatter.format_retry(5000)

        assert retry == "retry: 5000\n\n"
        assert "retry:" in retry

    def test_format_event_preserves_metadata(self) -> None:
        """Test that event metadata is preserved in formatting."""
        event = TextMessageChunk(
            message_id="msg-123", content="Test", metadata={"key": "value", "num": 42}
        )
        formatted = SSEFormatter.format_event(event)

        # Extract JSON
        json_str = formatted[6:-2]
        parsed = json.loads(json_str)

        assert parsed["metadata"]["key"] == "value"
        assert parsed["metadata"]["num"] == 42


class TestAGUISSEStream:
    """Test AG-UI SSE stream."""

    @pytest.mark.asyncio
    async def test_sse_stream_basic(self) -> None:
        """Test basic SSE streaming."""
        agent = MockAgent(response_content="Hello")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        # Should have multiple SSE-formatted chunks
        assert len(chunks) > 0

        # Each chunk should be SSE format
        for chunk in chunks[:-1]:  # All except completion comment
            assert chunk.startswith("data: ")
            assert chunk.endswith("\n\n")

        # Last chunk should be completion comment
        assert chunks[-1] == ": stream_complete\n\n"

    @pytest.mark.asyncio
    async def test_sse_stream_with_event_names(self) -> None:
        """Test SSE streaming with event names."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message, include_event_names=True)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        # Should have event names in multi-line format
        # Format: "event: ...\ndata: ...\n\n"
        has_event_lines = any("event: " in c for c in chunks)
        assert has_event_lines

    @pytest.mark.asyncio
    async def test_sse_stream_events_are_valid_json(self) -> None:
        """Test that all SSE events contain valid JSON."""
        agent = MockAgent(response_content="Test")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        async for chunk in stream:
            if chunk.startswith("data: "):
                # Extract JSON
                json_str = chunk[6:-2]  # Remove "data: " and "\n\n"
                parsed = json.loads(json_str)

                # Should have event_type
                assert "event_type" in parsed
                assert "timestamp" in parsed

    @pytest.mark.asyncio
    async def test_sse_stream_message_flow(self) -> None:
        """Test complete message flow through SSE stream."""
        agent = MockAgent(response_content="Response")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Question")

        stream = AGUISSEStream(adapter, message)

        event_types = []
        async for chunk in stream:
            if chunk.startswith("data: "):
                json_str = chunk[6:-2]
                parsed = json.loads(json_str)
                event_types.append(parsed["event_type"])

        # Should have standard flow: metadata, start, chunks, complete
        assert "metadata" in event_types
        assert "text_message_start" in event_types
        assert "text_message_complete" in event_types

    @pytest.mark.asyncio
    async def test_sse_stream_error_handling(self) -> None:
        """Test SSE stream error handling."""

        class FailingAgent(Agent):
            """Agent that raises error."""

            @property
            def name(self) -> str:
                return "failing"

            @property
            def capabilities(self) -> list[str]:
                return []

            async def process(self, message: Message) -> Message:
                raise ValueError("Test error")

        agent = FailingAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        # Should have error event in the stream
        error_events = []
        for chunk in chunks:
            if chunk.startswith("data: "):
                json_str = chunk[6:-2]
                parsed = json.loads(json_str)
                if parsed.get("event_type") == "error":
                    error_events.append(parsed)

        assert len(error_events) >= 1
        assert error_events[0]["error_message"] == "Test error"


class TestCreateSSEResponseIterator:
    """Test create_sse_response_iterator convenience function."""

    @pytest.mark.asyncio
    async def test_create_iterator_basic(self) -> None:
        """Test creating SSE iterator."""
        agent = MockAgent(response_content="Test")
        message = Message(role="user", content="Hi")

        iterator = create_sse_response_iterator(agent, message)

        chunks = []
        async for chunk in iterator:
            chunks.append(chunk)

        # Should produce SSE chunks
        assert len(chunks) > 0
        assert any(c.startswith("data: ") for c in chunks)

    @pytest.mark.asyncio
    async def test_create_iterator_custom_agent_name(self) -> None:
        """Test creating iterator with custom agent name."""
        agent = MockAgent()
        message = Message(role="user", content="Hi")

        iterator = create_sse_response_iterator(agent, message, agent_name="CustomAgent")

        # Extract first metadata event
        async for chunk in iterator:
            if chunk.startswith("data: "):
                json_str = chunk[6:-2]
                parsed = json.loads(json_str)

                if parsed["event_type"] == "metadata":
                    assert parsed["data"]["agent_name"] == "CustomAgent"
                    break

    @pytest.mark.asyncio
    async def test_create_iterator_with_event_names(self) -> None:
        """Test creating iterator with event names."""
        agent = MockAgent()
        message = Message(role="user", content="Hi")

        iterator = create_sse_response_iterator(agent, message, include_event_names=True)

        chunks = []
        async for chunk in iterator:
            chunks.append(chunk)
            if len(chunks) > 3:  # Just check first few
                break

        # Should have event names in some chunks
        has_event_lines = any("event: " in c for c in chunks)
        assert has_event_lines


class TestSSEFormat:
    """Test SSE format compliance."""

    @pytest.mark.asyncio
    async def test_sse_line_endings(self) -> None:
        """Test SSE format has correct line endings."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        async for chunk in stream:
            if chunk.startswith("data: "):
                # Should end with exactly two newlines
                assert chunk.endswith("\n\n")
                assert not chunk.endswith("\n\n\n")

    @pytest.mark.asyncio
    async def test_sse_no_empty_data(self) -> None:
        """Test that SSE data lines are never empty."""
        agent = MockAgent()
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        async for chunk in stream:
            if chunk.startswith("data: "):
                # Extract data content
                content = chunk[6:-2]  # Remove "data: " and "\n\n"
                assert len(content) > 0
                assert content != ""


# FastAPI integration tests (conditional)
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from agenkit.protocols.agui.transports.http import AGUISSEEndpoint

    class TestFastAPIIntegration:
        """Test FastAPI integration."""

        def test_fastapi_endpoint_creation(self) -> None:
            """Test creating FastAPI endpoint."""
            agent = MockAgent()
            endpoint = AGUISSEEndpoint(agent)

            assert endpoint is not None

        def test_fastapi_endpoint_in_app(self) -> None:
            """Test FastAPI endpoint integrated in app."""
            agent = MockAgent(response_content="FastAPI response")
            endpoint = AGUISSEEndpoint(agent)

            app = FastAPI()
            app.add_route("/chat", endpoint, methods=["POST"])

            # Should be able to create test client
            client = TestClient(app)
            assert client is not None

        def test_fastapi_sse_request(self) -> None:
            """Test making SSE request to FastAPI endpoint."""
            agent = MockAgent(response_content="Test")
            endpoint = AGUISSEEndpoint(agent)

            app = FastAPI()
            app.add_route("/chat", endpoint, methods=["POST"])

            client = TestClient(app)
            response = client.post("/chat", json={"message": "Hello"})

            # Should return 200
            assert response.status_code == 200

            # Should have SSE content type
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Should have SSE cache control
            assert "no-cache" in response.headers.get("cache-control", "")

        def test_fastapi_sse_response_content(self) -> None:
            """Test FastAPI SSE response content."""
            agent = MockAgent(response_content="Response")
            endpoint = AGUISSEEndpoint(agent)

            app = FastAPI()
            app.add_route("/chat", endpoint, methods=["POST"])

            client = TestClient(app)
            response = client.post("/chat", json={"message": "Question"})

            # Read response body
            content = response.text

            # Should contain SSE data lines
            assert "data: " in content

            # Should contain AG-UI events
            assert "text_message_start" in content or "metadata" in content

        def test_fastapi_cors_configuration(self) -> None:
            """Test CORS configuration."""
            agent = MockAgent()
            endpoint = AGUISSEEndpoint(agent, cors_origins=["http://localhost:3000"])

            app = FastAPI()
            app.add_route("/chat", endpoint, methods=["POST"])

            client = TestClient(app)
            response = client.post(
                "/chat",
                json={"message": "Hi"},
                headers={"origin": "http://localhost:3000"},
            )

            # Should have CORS header
            assert "access-control-allow-origin" in response.headers

except ImportError:
    # FastAPI not available, skip these tests
    pass


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_empty_message(self) -> None:
        """Test handling empty message."""
        agent = MockAgent(response_content="")
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="")

        stream = AGUISSEStream(adapter, message)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        # Should still produce events
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_long_message(self) -> None:
        """Test handling very long message."""
        long_text = "A" * 10000
        agent = MockAgent(response_content=long_text)
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        # Should produce multiple chunks
        text_chunks = [c for c in chunks if "text_message_chunk" in c]
        assert len(text_chunks) > 1

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self) -> None:
        """Test handling special characters."""
        special_text = 'Test with "quotes" and \n newlines and 中文'
        agent = MockAgent(response_content=special_text)
        adapter = AGUIAdapter(agent)
        message = Message(role="user", content="Hi")

        stream = AGUISSEStream(adapter, message)

        async for chunk in stream:
            if chunk.startswith("data: "):
                # Should be valid JSON despite special characters
                json_str = chunk[6:-2]
                parsed = json.loads(json_str)

                if parsed.get("content"):
                    # Special characters should be preserved
                    assert "quotes" in str(parsed)
                    break
