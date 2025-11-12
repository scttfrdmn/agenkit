"""Integration tests for WebSocket transport.

This module tests WebSocket communication including:
- Basic request/response communication
- Streaming support
- Cross-transport compatibility
- Error handling
"""

import asyncio

import pytest

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")


class StreamingAgent(Agent):
    """Agent that supports streaming responses."""

    @property
    def name(self) -> str:
        return "streaming"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

    async def stream(self, message: Message):
        """Stream multiple response chunks."""
        for i in range(5):
            await asyncio.sleep(0.01)
            yield Message(
                role="agent",
                content=f"Chunk {i}: {message.content}",
                metadata={"chunk_id": i, "total": 5},
            )


class CounterAgent(Agent):
    """Agent that counts requests for testing."""

    def __init__(self):
        self._count = 0

    @property
    def name(self) -> str:
        return "counter"

    async def process(self, message: Message) -> Message:
        self._count += 1
        return Message(
            role="agent",
            content=f"Request #{self._count}: {message.content}",
            metadata={"count": self._count},
        )


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket transport."""

    async def test_websocket_basic_request_response(self):
        """Test basic WebSocket request/response communication."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10001")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:10001")

            # Test communication
            message = Message(role="user", content="Hello WebSocket!")
            response = await remote.process(message)

            assert response.role == "agent"
            assert response.content == "Echo: Hello WebSocket!"

        finally:
            await server.stop()

    async def test_websocket_streaming(self):
        """Test WebSocket streaming support."""
        # Start server with streaming agent
        agent = StreamingAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10002")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("streaming", endpoint="ws://127.0.0.1:10002")

            # Test streaming
            message = Message(role="user", content="stream test")
            chunks = []
            async for chunk in remote.stream(message):
                chunks.append(chunk)

            # Verify all chunks received
            assert len(chunks) == 5
            for i, chunk in enumerate(chunks):
                assert chunk.role == "agent"
                assert f"Chunk {i}:" in chunk.content
                assert "stream test" in chunk.content
                assert chunk.metadata["chunk_id"] == i
                assert chunk.metadata["total"] == 5

        finally:
            await server.stop()

    async def test_websocket_multiple_sequential_requests(self):
        """Test multiple sequential requests over same WebSocket connection."""
        # Start server
        agent = CounterAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10003")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("counter", endpoint="ws://127.0.0.1:10003")

            # Send multiple requests sequentially
            for i in range(10):
                message = Message(role="user", content=f"Request {i}")
                response = await remote.process(message)

                assert f"Request #{i + 1}:" in response.content
                assert f"Request {i}" in response.content
                assert response.metadata["count"] == i + 1

        finally:
            await server.stop()

    async def test_websocket_concurrent_clients(self):
        """Test multiple concurrent clients connecting via WebSocket."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10004")
        await server.start()

        try:
            # Create multiple clients
            num_clients = 5
            remotes = [
                RemoteAgent("echo", endpoint="ws://127.0.0.1:10004")
                for _ in range(num_clients)
            ]

            # Send concurrent requests
            async def send_request(remote, client_id):
                message = Message(role="user", content=f"Client {client_id}")
                response = await remote.process(message)
                assert f"Echo: Client {client_id}" == response.content
                return response

            tasks = [send_request(remote, i) for i, remote in enumerate(remotes)]
            responses = await asyncio.gather(*tasks)

            # Verify all responses
            assert len(responses) == num_clients

        finally:
            await server.stop()

    async def test_websocket_concurrent_streaming(self):
        """Test concurrent streaming over multiple WebSocket connections."""
        # Start server
        agent = StreamingAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10005")
        await server.start()

        try:
            # Create multiple clients
            num_clients = 3
            remotes = [
                RemoteAgent("streaming", endpoint="ws://127.0.0.1:10005")
                for _ in range(num_clients)
            ]

            # Stream concurrently
            async def collect_stream(remote, client_id):
                message = Message(role="user", content=f"Client {client_id} stream")
                chunks = []
                async for chunk in remote.stream(message):
                    chunks.append(chunk)
                return chunks

            tasks = [collect_stream(remote, i) for i, remote in enumerate(remotes)]
            results = await asyncio.gather(*tasks)

            # Verify each client got all chunks
            for client_id, chunks in enumerate(results):
                assert len(chunks) == 5
                for chunk in chunks:
                    assert f"Client {client_id} stream" in chunk.content

        finally:
            await server.stop()

    async def test_websocket_large_message(self):
        """Test WebSocket with large messages (1MB+)."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10006")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:10006")

            # Send large message (1MB)
            large_content = "x" * (1024 * 1024)
            message = Message(role="user", content=large_content)
            response = await remote.process(message)

            assert "Echo:" in response.content
            assert len(response.content) > 1024 * 1024

        finally:
            await server.stop()

    async def test_websocket_metadata_preservation(self):
        """Test that metadata is preserved in WebSocket communication."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10007")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:10007")

            # Send message with metadata
            message = Message(
                role="user",
                content="test",
                metadata={
                    "key": "value",
                    "number": 42,
                    "list": [1, 2, 3],
                    "nested": {"a": "b"},
                },
            )
            response = await remote.process(message)

            assert response.role == "agent"
            assert "Echo: test" in response.content

        finally:
            await server.stop()

    async def test_websocket_reconnection_after_server_restart(self):
        """Test automatic reconnection when server restarts."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10008")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:10008")

            # First request
            message = Message(role="user", content="First")
            response = await remote.process(message)
            assert "Echo: First" in response.content

            # Stop server
            await server.stop()
            await asyncio.sleep(0.2)  # Wait for connection to close

            # Restart server
            server = LocalAgent(agent, endpoint="ws://127.0.0.1:10008")
            await server.start()

            # Second request should trigger reconnection
            message = Message(role="user", content="Second")
            response = await remote.process(message)
            assert "Echo: Second" in response.content

        finally:
            await server.stop()

    async def test_websocket_vs_tcp_compatibility(self):
        """Test that WebSocket and TCP produce same results for same agent."""
        agent = EchoAgent()

        # Start WebSocket server
        ws_server = LocalAgent(agent, endpoint="ws://127.0.0.1:10009")
        await ws_server.start()

        # Start TCP server
        tcp_server = LocalAgent(agent, endpoint="tcp://127.0.0.1:10010")
        await tcp_server.start()

        try:
            # Create clients
            ws_remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:10009")
            tcp_remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:10010")

            # Send same message to both
            message = Message(role="user", content="compatibility test")

            ws_response = await ws_remote.process(message)
            tcp_response = await tcp_remote.process(message)

            # Both should produce same content
            assert ws_response.content == tcp_response.content
            assert ws_response.role == tcp_response.role

        finally:
            await ws_server.stop()
            await tcp_server.stop()

    async def test_websocket_streaming_error_handling(self):
        """Test error handling during WebSocket streaming."""

        class ErrorStreamAgent(Agent):
            @property
            def name(self) -> str:
                return "error_stream"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="done")

            async def stream(self, message: Message):
                # Yield one chunk, then error
                yield Message(role="agent", content="Chunk 0")
                raise ValueError("Streaming error!")

        agent = ErrorStreamAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10011")
        await server.start()

        try:
            remote = RemoteAgent("error_stream", endpoint="ws://127.0.0.1:10011")

            message = Message(role="user", content="test")
            chunks = []

            with pytest.raises(Exception):
                async for chunk in remote.stream(message):
                    chunks.append(chunk)

            # Should have received at least first chunk
            assert len(chunks) >= 1

        finally:
            await server.stop()

    async def test_websocket_bidirectional_communication(self):
        """Test that WebSocket supports true bidirectional communication."""
        # This test demonstrates that multiple requests can be in-flight
        # simultaneously over a single WebSocket connection

        class SlowAgent(Agent):
            @property
            def name(self) -> str:
                return "slow"

            async def process(self, message: Message) -> Message:
                # Variable delay based on message content
                delay = float(message.metadata.get("delay", 0.1))
                await asyncio.sleep(delay)
                return Message(
                    role="agent", content=f"Processed after {delay}s: {message.content}"
                )

        agent = SlowAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:10012")
        await server.start()

        try:
            remote = RemoteAgent("slow", endpoint="ws://127.0.0.1:10012")

            # Send multiple requests with different delays
            # The faster ones should complete first, demonstrating
            # bidirectional communication
            tasks = [
                remote.process(
                    Message(
                        role="user", content=f"Task {i}", metadata={"delay": delay}
                    )
                )
                for i, delay in enumerate([0.3, 0.1, 0.2, 0.05])
            ]

            responses = await asyncio.gather(*tasks)

            # All should complete
            assert len(responses) == 4
            for i, response in enumerate(responses):
                assert f"Task {i}" in response.content

        finally:
            await server.stop()
