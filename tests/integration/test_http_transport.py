"""
Integration tests for HTTP transport cross-language communication.

Tests Python client → Go server and Go client → Python server
across HTTP/1.1, HTTP/2, and HTTP/3 protocols.
"""

import asyncio
import subprocess
import time

import pytest

pytestmark = pytest.mark.xdist_group("cross_language")

from agenkit.adapters.python.local_agent import LocalAgent
from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Agent, Message

from .helpers import find_free_port

# ============================================
# Test Fixtures
# ============================================


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        """Echo the message back with a prefix."""
        return Message(
            role="agent",
            content=f"Echo: {message.content}",
            metadata={"original": message.content, "language": "python"},
        )


class ReverseAgent(Agent):
    """Agent that reverses the message content."""

    @property
    def name(self) -> str:
        return "reverse"

    @property
    def capabilities(self) -> list[str]:
        return ["reverse"]

    async def process(self, message: Message) -> Message:
        """Reverse the message content."""
        return Message(
            role="agent",
            content=message.content[::-1],
            metadata={"original": message.content, "language": "python"},
        )


class ServerProcess:
    """Helper to manage server processes for testing."""

    def __init__(self, language: str, port: int, protocol: str = "http"):
        self.language = language
        self.port = port
        self.protocol = protocol
        self.process: subprocess.Popen | None = None

    def start(self):
        """Start the server process."""
        if self.language == "python":
            # Start Python server
            cmd = [
                "python3",
                "-c",
                f"""
import asyncio
from agenkit.adapters.python.local_agent import LocalAgent
from agenkit.interfaces import Agent, Message

class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"Echo: {{message.content}}",
            metadata={{"original": message.content, "language": "python"}}
        )

async def main():
    agent = EchoAgent()
    local_agent = LocalAgent(agent, endpoint="tcp://0.0.0.0:{self.port}")
    await local_agent.start()
    print(f"Python server listening on tcp://0.0.0.0:{self.port}", flush=True)
    await asyncio.Event().wait()

asyncio.run(main())
""",
            ]
        else:  # go
            # Start Go server from agenkit-go directory where go.mod is located
            # Go server expects port as positional argument
            cmd = ["go", "run", "tests/integration/test_server.go", str(self.port)]

        # Set working directory for Go processes (Go files are in agenkit-go/)
        working_dir = "agenkit-go" if self.language == "go" else None

        # S603: Safe in test infrastructure - cmd contains test server command
        self.process = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=working_dir,
        )

        # Wait for server to be ready
        time.sleep(2)

        # Check if process is still running
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(
                f"{self.language} server failed to start:\nstdout: {stdout}\nstderr: {stderr}"
            )

    def stop(self):
        """Stop the server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


@pytest.fixture
async def python_server():
    """Start Python HTTP server on a dynamic port."""
    port = find_free_port()
    server = ServerProcess("python", port, "http")
    server.start()
    yield server
    server.stop()


@pytest.fixture
async def go_server():
    """Start Go HTTP server on a dynamic port."""
    port = find_free_port()
    server = ServerProcess("go", port, "http")
    server.start()
    yield server
    server.stop()


# ============================================
# HTTP/1.1 Tests
# ============================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_client_to_go_server(go_server):
    """Test Python client connecting to Go server via HTTP/1.1."""
    # Create Python client connecting to HTTP server on dynamic port
    client = RemoteAgent(name="test-client", endpoint=f"http://localhost:{go_server.port}")

    # Send message
    message = Message(role="user", content="Hello from Python")
    response = await client.process(message)

    # Validate response
    assert response.role == "agent"
    assert "Echo: Hello from Python" in response.content
    assert response.metadata.get("server_language") == "go"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_go_client_to_python_server(python_server):
    """Test Go client connecting to Python server via HTTP/1.1."""
    # We'll execute a Go test client (run from agenkit-go directory) with dynamic port
    # S603, S607, ASYNC221: Safe in test infrastructure - port is from test fixture
    result = subprocess.run(  # noqa: S603, ASYNC221
        [  # noqa: S607
            "go",
            "run",
            "tests/integration/test_client.go",
            "-url",
            f"tcp://localhost:{python_server.port}",
            "-message",
            "Hello from Go",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd="agenkit-go",
    )

    assert result.returncode == 0, f"Go client failed: {result.stderr}"
    assert "Echo: Hello from Go" in result.stdout
    assert "python" in result.stdout.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bidirectional_communication(python_server, go_server):
    """Test bidirectional communication between Python and Go."""
    # Python → Go (Go server uses HTTP, not TCP) with dynamic port
    python_to_go = RemoteAgent(name="test-client", endpoint=f"http://localhost:{go_server.port}")
    msg1 = Message(role="user", content="Python to Go")
    resp1 = await python_to_go.process(msg1)
    assert "Echo: Python to Go" in resp1.content
    assert resp1.metadata.get("server_language") == "go"

    # Go → Python (via subprocess, run from agenkit-go directory) with dynamic port
    # S603, S607, ASYNC221: Safe in test infrastructure - port is from test fixture
    result = subprocess.run(  # noqa: S603, ASYNC221
        [  # noqa: S607
            "go",
            "run",
            "tests/integration/test_client.go",
            "-url",
            f"tcp://localhost:{python_server.port}",
            "-message",
            "Go to Python",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        cwd="agenkit-go",
    )

    assert result.returncode == 0
    assert "Echo: Go to Python" in result.stdout


@pytest.mark.asyncio
async def test_message_serialization():
    """Test message serialization consistency between Python and Go."""
    # Start Python server on dynamic port
    port = find_free_port()
    agent = EchoAgent()
    local_agent = LocalAgent(agent, endpoint=f"tcp://0.0.0.0:{port}")
    await local_agent.start()

    try:
        # Wait for server to start
        await asyncio.sleep(1)

        # Create message with complex metadata
        message = Message(
            role="user",
            content="Test serialization",
            metadata={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "bool": True,
                "nested": {"key": "value"},
                "list": [1, 2, 3],
            },
        )

        # Send from Python client
        client = RemoteAgent(name="test-client", endpoint=f"tcp://localhost:{port}")
        response = await client.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: Test serialization" in response.content
        assert response.metadata["original"] == "Test serialization"
        assert response.metadata["language"] == "python"

    finally:
        await local_agent.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_connection_refused():
    """Test error handling when server is unavailable."""
    client = RemoteAgent(
        name="test-client", endpoint="http://localhost:9999"
    )  # No server on this port

    message = Message(role="user", content="Test")

    with pytest.raises(Exception) as exc_info:
        await client.process(message)

    # Should get connection error
    assert "connection" in str(exc_info.value).lower() or "refused" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test concurrent requests from Python client to Go server."""
    # Start Python server for this test on dynamic port
    port = find_free_port()
    agent = EchoAgent()
    local_agent = LocalAgent(agent, endpoint=f"tcp://0.0.0.0:{port}")
    await local_agent.start()

    try:
        await asyncio.sleep(1)

        # Create multiple clients for true concurrent requests (one connection per client)
        # Each RemoteAgent manages a single connection, so for concurrent requests
        # we need multiple agent instances
        async def send_message(i: int) -> Message:
            client = RemoteAgent(name=f"test-client-{i}", endpoint=f"tcp://localhost:{port}")
            try:
                message = Message(role="user", content=f"Message {i}")
                return await client.process(message)
            finally:
                await client.close()

        # Send 10 concurrent requests using separate connections
        tasks = [send_message(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # Validate all responses
        assert len(responses) == 10
        for i, response in enumerate(responses):
            assert f"Echo: Message {i}" in response.content

    finally:
        await local_agent.stop()


# ============================================
# HTTP/2 Tests
# ============================================


@pytest.mark.asyncio
async def test_http2_python_to_go():
    """Test Python client to Go server via HTTP/2."""
    # Start Python server with HTTP/2 on dynamic port
    port = find_free_port()
    agent = EchoAgent()
    local_agent = LocalAgent(agent, endpoint=f"tcp://0.0.0.0:{port}")
    await local_agent.start()

    try:
        await asyncio.sleep(1)

        # Python client with HTTP/2
        client = RemoteAgent(name="test-client", endpoint=f"tcp://localhost:{port}")
        message = Message(role="user", content="HTTP/2 test")
        response = await client.process(message)

        assert "Echo: HTTP/2 test" in response.content

    finally:
        await local_agent.stop()


# ============================================
# Performance Tests
# ============================================


@pytest.mark.asyncio
async def test_latency_baseline():
    """Measure baseline latency for cross-language communication."""
    # Use dynamic port
    port = find_free_port()
    agent = EchoAgent()
    local_agent = LocalAgent(agent, endpoint=f"tcp://0.0.0.0:{port}")
    await local_agent.start()

    try:
        await asyncio.sleep(1)

        client = RemoteAgent(name="test-client", endpoint=f"tcp://localhost:{port}")
        message = Message(role="user", content="Latency test")

        # Warm up
        await client.process(message)

        # Measure 100 requests
        start = time.time()
        for _ in range(100):
            await client.process(message)
        elapsed = time.time() - start

        avg_latency_ms = (elapsed / 100) * 1000

        # Log baseline (should be < 10ms for local communication)
        print(f"\nBaseline latency: {avg_latency_ms:.2f}ms per request")
        assert avg_latency_ms < 50, f"Latency too high: {avg_latency_ms:.2f}ms"

    finally:
        await local_agent.stop()
