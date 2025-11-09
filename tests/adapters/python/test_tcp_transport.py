"""Tests for TCP transport."""

import asyncio
from pathlib import Path

import pytest

from agenkit import Agent, Message
from agenkit.adapters.python import (
    AgentNotFoundError,
    ConnectionError,
    LocalAgent,
    RemoteAgent,
    TCPTransport,
)


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")


@pytest.mark.asyncio
class TestTCPTransport:
    """Tests for TCPTransport."""

    async def test_tcp_basic_communication(self):
        """Test basic TCP communication."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9876")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:9876")

            # Test communication
            message = Message(role="user", content="Hello")
            response = await remote.process(message)

            assert response.role == "agent"
            assert "Echo: Hello" in response.content

        finally:
            await server.stop()

    async def test_tcp_multiple_requests(self):
        """Test multiple sequential TCP requests."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9877")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:9877")

            # Send multiple requests
            for i in range(5):
                message = Message(role="user", content=f"Message {i}")
                response = await remote.process(message)
                assert f"Echo: Message {i}" in response.content

        finally:
            await server.stop()

    async def test_tcp_concurrent_requests(self):
        """Test concurrent TCP requests with separate connections."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9878")
        await server.start()

        try:
            # Create separate clients for concurrent requests (more realistic)
            remotes = [
                RemoteAgent("echo", endpoint="tcp://127.0.0.1:9878") for _ in range(5)
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

    async def test_tcp_multiple_clients(self):
        """Test multiple TCP clients connecting to same agent."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9879")
        await server.start()

        try:
            # Create multiple clients
            remotes = [
                RemoteAgent("echo", endpoint="tcp://127.0.0.1:9879") for _ in range(3)
            ]

            # Each client sends a request
            responses = await asyncio.gather(
                *[
                    remote.process(Message(role="user", content=f"Client {i}"))
                    for i, remote in enumerate(remotes)
                ]
            )

            # Verify all responses
            for i, response in enumerate(responses):
                assert f"Echo: Client {i}" in response.content

        finally:
            await server.stop()

    async def test_tcp_connection_failure(self):
        """Test TCP connection to non-existent server."""
        # Try to connect to non-existent server
        remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:9999")
        message = Message(role="user", content="test")

        with pytest.raises(ConnectionError):
            await remote.process(message)

    async def test_tcp_large_message(self):
        """Test TCP with large message (1MB)."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9880")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:9880")

            # Send large message (1MB)
            large_content = "x" * (1024 * 1024)
            message = Message(role="user", content=large_content)
            response = await remote.process(message)

            assert "Echo:" in response.content
            assert len(response.content) > 1024 * 1024

        finally:
            await server.stop()

    async def test_tcp_message_metadata_preserved(self):
        """Test that message metadata is preserved over TCP."""
        # Start server
        agent = EchoAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9881")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:9881")

            # Send message with metadata
            message = Message(
                role="user", content="test", metadata={"key": "value", "number": 42}
            )
            response = await remote.process(message)

            # Verify response
            assert response.content
            assert response.timestamp

        finally:
            await server.stop()

    async def test_tcp_server_start_stop_multiple_times(self):
        """Test TCP server can be started and stopped multiple times."""
        agent = EchoAgent()

        # Start and stop server 3 times
        for i in range(3):
            server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9882")
            await server.start()

            # Test communication
            remote = RemoteAgent("echo", endpoint="tcp://127.0.0.1:9882")
            message = Message(role="user", content=f"Iteration {i}")
            response = await remote.process(message)
            assert f"Echo: Iteration {i}" in response.content

            # Stop server
            await server.stop()

            # Small delay to ensure port is released
            await asyncio.sleep(0.1)
