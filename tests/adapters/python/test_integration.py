"""Integration tests for protocol adapter."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from agenkit.adapters.python import (
    AgentTimeoutError,
    ConnectionError,
    LocalAgent,
    RemoteAgent,
)
from agenkit.interfaces import Agent, Message


class EchoAgent(Agent):
    """Simple agent that echoes back input."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")


class SlowAgent(Agent):
    """Agent that takes time to respond."""

    def __init__(self, delay: float = 1.0):
        self.delay = delay

    @property
    def name(self) -> str:
        return "slow"

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(self.delay)
        return Message(role="agent", content=f"Slow response: {message.content}")


class ErrorAgent(Agent):
    """Agent that raises errors."""

    @property
    def name(self) -> str:
        return "error"

    async def process(self, message: Message) -> Message:
        raise ValueError("Intentional error for testing")


@pytest.mark.asyncio
class TestRemoteAgentCommunication:
    """Tests for remote agent communication."""

    async def test_basic_remote_call(self):
        """Test basic remote agent call with Unix socket."""
        # Create temporary socket path
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            # Start local agent server
            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)
            await server.start()

            try:
                # Create remote client
                remote = RemoteAgent("echo", endpoint=endpoint)

                # Make request
                msg = Message(role="user", content="Hello")
                response = await remote.process(msg)

                assert response.role == "agent"
                assert response.content == "Echo: Hello"
            finally:
                await server.stop()

    async def test_multiple_requests(self):
        """Test multiple sequential requests to same agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)
            await server.start()

            try:
                remote = RemoteAgent("echo", endpoint=endpoint)

                # Make multiple requests
                for i in range(5):
                    msg = Message(role="user", content=f"Message {i}")
                    response = await remote.process(msg)
                    assert f"Message {i}" in response.content
            finally:
                await server.stop()

    async def test_concurrent_requests(self):
        """Test concurrent requests to same agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)
            await server.start()

            try:
                # Create multiple clients
                clients = [RemoteAgent("echo", endpoint=endpoint) for _ in range(3)]

                # Make concurrent requests
                async def make_request(client: RemoteAgent, i: int) -> Message:
                    msg = Message(role="user", content=f"Request {i}")
                    return await client.process(msg)

                tasks = [make_request(client, i) for i, client in enumerate(clients)]
                responses = await asyncio.gather(*tasks)

                # All requests should succeed
                assert len(responses) == 3
                for i, response in enumerate(responses):
                    assert f"Request {i}" in response.content
            finally:
                await server.stop()

    async def test_remote_agent_timeout(self):
        """Test remote agent timeout handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            # Create slow agent
            slow_agent = SlowAgent(delay=2.0)
            server = LocalAgent(slow_agent, endpoint=endpoint)
            await server.start()

            try:
                # Create client with short timeout
                remote = RemoteAgent("slow", endpoint=endpoint, timeout=0.5)

                # Request should timeout
                msg = Message(role="user", content="test")
                with pytest.raises(AgentTimeoutError) as exc_info:
                    await remote.process(msg)

                assert "slow" in str(exc_info.value)
                assert "0.5" in str(exc_info.value)
            finally:
                await server.stop()

    async def test_connection_failure(self):
        """Test connection to non-existent agent fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "nonexistent.sock"
            endpoint = f"unix://{socket_path}"

            remote = RemoteAgent("missing", endpoint=endpoint)
            msg = Message(role="user", content="test")

            with pytest.raises(ConnectionError):
                await remote.process(msg)

    async def test_message_metadata_preserved(self):
        """Test that message metadata is preserved across remote calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)
            await server.start()

            try:
                remote = RemoteAgent("echo", endpoint=endpoint)

                # Send message with metadata
                msg = Message(role="user", content="test", metadata={"key": "value", "num": 42})
                response = await remote.process(msg)

                # Response should have content
                assert "Echo:" in response.content
            finally:
                await server.stop()

    async def test_large_message(self):
        """Test handling of large messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)
            await server.start()

            try:
                remote = RemoteAgent("echo", endpoint=endpoint)

                # Send large message (1 MB)
                large_content = "x" * (1024 * 1024)
                msg = Message(role="user", content=large_content)
                response = await remote.process(msg)

                assert "Echo:" in response.content
                assert large_content in response.content
            finally:
                await server.stop()

    async def test_server_start_stop_multiple_times(self):
        """Test starting and stopping server multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)

            # Start and stop multiple times
            for _ in range(3):
                await server.start()
                assert os.path.exists(socket_path)

                # Make a request to verify it works
                remote = RemoteAgent("echo", endpoint=endpoint)
                msg = Message(role="user", content="test")
                response = await remote.process(msg)
                assert "Echo:" in response.content

                await server.stop()
                # Socket should be cleaned up
                # Note: might take a moment for OS to clean up
                await asyncio.sleep(0.1)

    async def test_multiple_clients_same_agent(self):
        """Test multiple clients connecting to same agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            endpoint = f"unix://{socket_path}"

            echo_agent = EchoAgent()
            server = LocalAgent(echo_agent, endpoint=endpoint)
            await server.start()

            try:
                # Create multiple clients
                clients = [RemoteAgent("echo", endpoint=endpoint) for _ in range(10)]

                # Each client makes a request
                for i, client in enumerate(clients):
                    msg = Message(role="user", content=f"Client {i}")
                    response = await client.process(msg)
                    assert f"Client {i}" in response.content
            finally:
                await server.stop()
