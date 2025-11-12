"""Tests for WebSocket transport."""

import asyncio

import pytest
import websockets
from websockets.asyncio.server import serve

from agenkit import Agent, Message
from agenkit.adapters.python import (
    ConnectionClosedError,
    ConnectionError,
    LocalAgent,
    RemoteAgent,
)
from agenkit.adapters.python.websocket_transport import WebSocketTransport


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")


@pytest.mark.asyncio
class TestWebSocketTransport:
    """Tests for WebSocketTransport."""

    async def test_websocket_basic_communication(self):
        """Test basic WebSocket communication."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:9001")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:9001")

            # Test communication
            message = Message(role="user", content="Hello")
            response = await remote.process(message)

            assert response.role == "agent"
            assert "Echo: Hello" in response.content

        finally:
            await server.stop()

    async def test_websocket_multiple_requests(self):
        """Test multiple sequential WebSocket requests."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:9002")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:9002")

            # Send multiple requests
            for i in range(5):
                message = Message(role="user", content=f"Message {i}")
                response = await remote.process(message)
                assert f"Echo: Message {i}" in response.content

        finally:
            await server.stop()

    async def test_websocket_concurrent_requests(self):
        """Test concurrent WebSocket requests."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:9003")
        await server.start()

        try:
            # Create separate clients for concurrent requests
            remotes = [
                RemoteAgent("echo", endpoint="ws://127.0.0.1:9003") for _ in range(5)
            ]

            # Send concurrent requests
            messages = [Message(role="user", content=f"Message {i}") for i in range(5)]
            responses = await asyncio.gather(
                *[remote.process(msg) for remote, msg in zip(remotes, messages)]
            )

            # Verify all responses
            for i, response in enumerate(responses):
                assert f"Echo: Message {i}" in response.content

        finally:
            await server.stop()

    async def test_websocket_connection_failure(self):
        """Test WebSocket connection to non-existent server."""
        # Try to connect to non-existent server
        transport = WebSocketTransport("ws://127.0.0.1:9999")

        with pytest.raises(ConnectionError):
            await transport.connect()

    async def test_websocket_large_message(self):
        """Test WebSocket with large message (1MB)."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:9004")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:9004")

            # Send large message (1MB)
            large_content = "x" * (1024 * 1024)
            message = Message(role="user", content=large_content)
            response = await remote.process(message)

            assert "Echo:" in response.content
            assert len(response.content) > 1024 * 1024

        finally:
            await server.stop()

    async def test_websocket_reconnection(self):
        """Test WebSocket automatic reconnection after server restart."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:9005")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="ws://127.0.0.1:9005")

            # First request
            message = Message(role="user", content="First")
            response = await remote.process(message)
            assert "Echo: First" in response.content

            # Stop and restart server
            await server.stop()
            await asyncio.sleep(0.2)  # Wait for connection to close

            server = LocalAgent(agent, endpoint="ws://127.0.0.1:9005")
            await server.start()

            # Second request should trigger reconnection
            message = Message(role="user", content="Second")
            response = await remote.process(message)
            assert "Echo: Second" in response.content

        finally:
            await server.stop()

    async def test_websocket_send_binary_data(self):
        """Test WebSocket with binary data transmission."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="ws://127.0.0.1:9006")
        await server.start()

        try:
            # Create transport directly
            transport = WebSocketTransport("ws://127.0.0.1:9006")
            await transport.connect()

            # Send binary data
            test_data = b"Binary data: \x00\x01\x02\xff"
            await transport.send(test_data)

            # Note: In real usage, this would go through the protocol layer
            # which handles framing. For this test, we're just verifying
            # the transport can send binary data.

            await transport.close()

        finally:
            await server.stop()

    async def test_websocket_receive_exactly(self):
        """Test receive_exactly functionality."""
        # Create a simple WebSocket echo server
        async def echo_handler(websocket):
            async for message in websocket:
                # Echo back the message
                await websocket.send(message)

        server = await serve(echo_handler, "127.0.0.1", 9007)

        try:
            # Create transport
            transport = WebSocketTransport("ws://127.0.0.1:9007")
            await transport.connect()

            # Send data
            test_data = b"0123456789" * 10  # 100 bytes
            await transport.send(test_data)

            # Receive exactly 50 bytes
            received = await transport.receive_exactly(50)
            assert len(received) == 50
            assert received == test_data[:50]

            # Receive next 50 bytes
            received = await transport.receive_exactly(50)
            assert len(received) == 50
            assert received == test_data[50:100]

            await transport.close()

        finally:
            server.close()
            await server.wait_closed()

    async def test_websocket_connection_closed_error(self):
        """Test ConnectionClosedError when server closes connection."""
        # Create a WebSocket server that closes immediately after first message
        async def close_handler(websocket):
            async for message in websocket:
                await websocket.close()
                break

        server = await serve(close_handler, "127.0.0.1", 9008)

        try:
            # Create transport
            transport = WebSocketTransport("ws://127.0.0.1:9008")
            await transport.connect()

            # Send data
            await transport.send(b"test")

            # Try to receive - should get ConnectionClosedError
            with pytest.raises(ConnectionClosedError):
                await transport.receive()

            # Verify transport is no longer connected
            assert not transport.is_connected

        finally:
            server.close()
            await server.wait_closed()

    async def test_websocket_wss_url(self):
        """Test WebSocketTransport accepts wss:// URLs."""
        # Just verify the transport can be created with wss:// URL
        # (actual TLS testing would require certificates)
        transport = WebSocketTransport("wss://echo.websocket.org")
        assert transport._url == "wss://echo.websocket.org"

    async def test_websocket_custom_retry_params(self):
        """Test WebSocketTransport with custom retry parameters."""
        transport = WebSocketTransport(
            "ws://127.0.0.1:9999",
            max_retries=3,
            initial_retry_delay=0.1,
        )

        # Should fail to connect with custom retry settings
        with pytest.raises(ConnectionError) as exc_info:
            await transport.connect()

        assert "after 3 attempts" in str(exc_info.value)

    async def test_websocket_custom_ping_params(self):
        """Test WebSocketTransport with custom ping parameters."""
        # Create transport with custom ping settings
        transport = WebSocketTransport(
            "ws://127.0.0.1:9009",
            ping_interval=5.0,
            ping_timeout=2.0,
        )

        assert transport._ping_interval == 5.0
        assert transport._ping_timeout == 2.0

    async def test_websocket_is_connected_property(self):
        """Test is_connected property behavior."""
        # Create a simple WebSocket echo server
        async def echo_handler(websocket):
            async for message in websocket:
                await websocket.send(message)

        server = await serve(echo_handler, "127.0.0.1", 9010)

        try:
            # Create transport
            transport = WebSocketTransport("ws://127.0.0.1:9010")

            # Not connected initially
            assert not transport.is_connected

            # Connect
            await transport.connect()
            assert transport.is_connected

            # Close
            await transport.close()
            assert not transport.is_connected

        finally:
            server.close()
            await server.wait_closed()

    async def test_websocket_send_after_close(self):
        """Test that send after close attempts reconnection."""
        # Create a simple WebSocket echo server
        async def echo_handler(websocket):
            async for message in websocket:
                await websocket.send(message)

        server = await serve(echo_handler, "127.0.0.1", 9011)

        try:
            # Create transport
            transport = WebSocketTransport("ws://127.0.0.1:9011")
            await transport.connect()

            # Close connection
            await transport.close()
            assert not transport.is_connected

            # Send should trigger reconnection
            await transport.send(b"test after reconnect")
            assert transport.is_connected

            await transport.close()

        finally:
            server.close()
            await server.wait_closed()
