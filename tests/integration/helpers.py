"""Test helpers for cross-language integration tests."""

import asyncio
import socket
import subprocess
import time
from contextlib import asynccontextmanager
from typing import Optional

import httpx


def find_free_port() -> int:
    """Find a free port on localhost.

    Returns:
        int: An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


async def wait_for_server(
    url: str,
    timeout: float = 10.0,
    interval: float = 0.1,
) -> bool:
    """Wait for a server to become available.

    Args:
        url: The URL to check (e.g., "http://localhost:8080/health")
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Returns:
        bool: True if server is available, False if timeout
    """
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(url, timeout=1.0)
                if response.status_code < 500:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(interval)
    return False


@asynccontextmanager
async def go_http_server(port: Optional[int] = None):
    """Start a Go HTTP server for testing.

    This starts the Go test server as a subprocess and waits for it to be ready.

    Args:
        port: Port to use. If None, a free port is found automatically.

    Yields:
        tuple: (port, process) - The port number and subprocess handle

    Example:
        async with go_http_server() as (port, proc):
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/")
    """
    if port is None:
        port = find_free_port()

    # Start Go server
    # Get the path to the agenkit-go directory
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    go_test_dir = os.path.join(current_dir, "..", "..", "agenkit-go", "tests", "integration")

    process = subprocess.Popen(
        ["go", "run", "test_server.go", str(port)],
        cwd=go_test_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to be ready
        server_url = f"http://localhost:{port}/health"
        if not await wait_for_server(server_url, timeout=10.0):
            process.kill()
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Go server failed to start on port {port}\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        yield port, process
    finally:
        # Cleanup
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@asynccontextmanager
async def python_http_server(port: Optional[int] = None):
    """Start a Python HTTP server for testing.

    This starts an HTTPAgentServer in the current process.

    Args:
        port: Port to use. If None, a free port is found automatically.

    Yields:
        tuple: (port, server) - The port number and server instance

    Example:
        async with python_http_server() as (port, server):
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/health")
    """
    from agenkit.adapters.python.http_server import HTTPAgentServer
    from agenkit.interfaces import Agent, Message

    if port is None:
        port = find_free_port()

    # Create a simple test agent
    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            return Message(
                role="agent",
                content=f"Echo: {message.content}",
                metadata={
                    "original": message.content,
                    "language": "python",
                }
            )

    agent = TestAgent()
    server = HTTPAgentServer(agent, host="localhost", port=port)

    try:
        # Start server
        await server.start()

        # Wait for server to be ready
        server_url = f"http://localhost:{port}/health"
        if not await wait_for_server(server_url, timeout=10.0):
            await server.stop()
            raise RuntimeError(f"Python server failed to start on port {port}")

        yield port, server
    finally:
        # Cleanup
        await server.stop()


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use.

    Args:
        port: Port number to check

    Returns:
        bool: True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return False
        except OSError:
            return True


@asynccontextmanager
async def python_websocket_server(port: Optional[int] = None):
    """Start a Python WebSocket server for testing.

    This starts a LocalAgent WebSocket server in the current process.

    Args:
        port: Port to use. If None, a free port is found automatically.

    Yields:
        tuple: (port, agent, server_task) - The port number, local agent, and asyncio task

    Example:
        async with python_websocket_server() as (port, agent, task):
            # Connect WebSocket client to ws://localhost:{port}
            pass
    """
    from agenkit.adapters.python.local_agent import LocalAgent
    from agenkit.interfaces import Agent, Message

    if port is None:
        port = find_free_port()

    # Create a simple test agent
    class TestAgent(Agent):
        @property
        def name(self) -> str:
            return "test-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            return Message(
                role="agent",
                content=f"Echo: {message.content}",
                metadata={
                    "original": message.content,
                    "language": "python",
                }
            )

    agent = TestAgent()
    local_agent = LocalAgent(agent, endpoint=f"ws://localhost:{port}")

    # Start server in background task
    server_task = asyncio.create_task(local_agent.start())

    try:
        # Wait for server to be ready (WebSocket doesn't have health check, just wait)
        await asyncio.sleep(0.5)

        yield port, local_agent, server_task
    finally:
        # Cleanup
        await local_agent.stop()
