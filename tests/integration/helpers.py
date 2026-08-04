"""Test helpers for cross-language integration tests."""

import asyncio
import contextlib
import os
import signal
import socket
import subprocess
import time
from contextlib import asynccontextmanager

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


def wait_for_port(
    port: int,
    process: subprocess.Popen | None = None,
    timeout: float = 30.0,
    interval: float = 0.05,
) -> bool:
    """Block until a TCP port accepts connections.

    The synchronous counterpart to :func:`wait_for_server`, for fixtures that
    start a server before an event loop is available. Use this instead of a
    fixed ``time.sleep()``: a ``go run`` server has to compile first, which can
    take far longer than any sleep worth hardcoding when the machine is loaded.

    Args:
        port: Port the server is expected to listen on.
        process: Optional server subprocess. If given, polling stops early when
            the process exits, so a crashed server fails fast instead of
            burning the full timeout.
        timeout: Maximum time to wait in seconds.
        interval: Time between connection attempts in seconds.

    Returns:
        bool: True once the port accepts a connection, False on timeout or if
        the process exited.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            return False
        try:
            with socket.create_connection(("localhost", port), timeout=1.0):
                return True
        except OSError:
            pass
        time.sleep(interval)
    return False


def popen_server(cmd: list[str], cwd: str | None = None, **kwargs) -> subprocess.Popen:
    """Start a test server subprocess in its own process group.

    Always use this instead of :class:`subprocess.Popen` for a server that must be
    torn down, and pair it with :func:`terminate_server`. ``go run`` compiles the
    source and then *execs* the built binary as its own child, so signalling only
    the ``go`` wrapper leaves that binary alive, reparented to PID 1, still holding
    its port. A machine running this suite accumulated 965 such orphans holding
    11.7 GB before anyone noticed, because the wrapper does exit on SIGTERM and the
    teardown therefore reported success (#825).

    ``start_new_session`` makes the child a process-group leader so the whole tree
    can be signalled at once.
    """
    # Test infrastructure — cmd is built from literals and test-chosen ports.
    process = subprocess.Popen(cmd, cwd=cwd, start_new_session=True, **kwargs)
    # Record the group id now, while the process is certainly alive.
    # `start_new_session` makes the child its own group leader, so pgid == pid.
    # terminate_server cannot recover this later: once the wrapper is reaped,
    # os.getpgid(pid) raises ProcessLookupError even though the group still has live
    # members — and a `go run` wrapper routinely exits before its server does.
    process.agenkit_pgid = process.pid
    return process


def _wait_for_group_exit(pgid: int, timeout: float) -> bool:
    """Poll until no process remains in `pgid`. True if the group drained in time.

    Signal 0 to the group observes the grandchild that owns the port, not just the
    wrapper -- which is the whole point (#825).

    The caller must reap its own ``Popen`` first. On Linux a dead-but-unreaped
    process is still a group member, so an unwaited wrapper keeps
    ``killpg(pgid, 0)`` succeeding after everything has exited, and this burns its
    full timeout on *every* teardown before an unnecessary SIGKILL. macOS reports
    such a group as gone, so the ordering bug is invisible locally and only appears
    in CI -- which is how it got here.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.05)
    return False


def terminate_server(process: subprocess.Popen) -> None:
    """Stop a server started by :func:`popen_server`, and everything it spawned.

    Signals the whole process group, not just ``process``: under ``go run`` the
    process that owns the port is a *child* of the one Popen returned, and it does
    not die with its parent (#825).

    The group signal is sent unconditionally rather than only after
    :meth:`~subprocess.Popen.wait` times out. Waiting first would always succeed —
    the wrapper exits promptly — and that misleading success is exactly what hid
    this leak.
    """
    if process.poll() is None:
        process.terminate()

    # Prefer the pgid captured at spawn: os.getpgid() fails once the wrapper is
    # reaped, which is exactly when the surviving grandchild still needs killing.
    pgid = getattr(process, "agenkit_pgid", None)
    if pgid is None:
        try:
            pgid = os.getpgid(process.pid)
        except (ProcessLookupError, PermissionError):
            pgid = None

    # Never group-kill our own group: that would take down the test runner. This
    # can only happen if a caller used bare Popen instead of popen_server, and it
    # must fail as a surviving orphan (which the tests assert on) rather than as a
    # dead pytest.
    if pgid is not None and pgid == os.getpgid(0):
        pgid = None

    if pgid is not None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, signal.SIGTERM)

    # Reap the wrapper *before* polling the group. On Linux its unreaped zombie
    # would still count as a group member and stall the poll below for its full
    # timeout on every teardown.
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    # Escalation is driven by the *group*, not by `process`. `process.wait()` above
    # always returns promptly -- the `go run` wrapper exits on SIGTERM -- so using it
    # as the escalation trigger would mean SIGKILL never fires and a grandchild that
    # ignores SIGTERM survives indefinitely. That is the same "the wrapper's exit
    # proves nothing" mistake that caused #825 in the first place.
    if pgid is not None and not _wait_for_group_exit(pgid, timeout=5.0):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, signal.SIGKILL)


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
async def go_http_server(port: int | None = None):
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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    go_test_dir = os.path.join(current_dir, "..", "..", "agenkit-go", "tests", "integration")

    # S607, ASYNC220: Safe in test infrastructure - port is test parameter, not user input
    process = popen_server(
        ["go", "run", "test_server.go", str(port)],
        cwd=go_test_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to be ready
        server_url = f"http://localhost:{port}/health"
        if not await wait_for_server(server_url, timeout=10.0):
            # Stop the tree first, then drain: communicate() on a server that is alive
            # but not listening would block for its full timeout. The pipes stay
            # readable after the process dies, so no diagnostic output is lost.
            terminate_server(process)
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Go server failed to start on port {port}\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        yield port, process
    finally:
        terminate_server(process)


@asynccontextmanager
async def python_http_server(port: int | None = None):
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
                },
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
async def python_websocket_server(port: int | None = None):
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
                },
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


@asynccontextmanager
async def python_grpc_server(port: int | None = None):
    """Start a Python gRPC server for testing.

    This starts a GRPCServer in the current process.

    Args:
        port: Port to use. If None, a free port is found automatically.

    Yields:
        tuple: (port, server) - The port number and server instance

    Example:
        async with python_grpc_server() as (port, server):
            # Connect gRPC client to localhost:{port}
            pass
    """
    from agenkit.adapters.python.grpc_server import GRPCServer
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
                },
            )

    agent = TestAgent()
    server = GRPCServer(agent, f"localhost:{port}")

    try:
        # Start server
        await server.start()

        # Wait for server to be ready (gRPC needs a brief moment to start)
        await asyncio.sleep(0.5)

        yield port, server
    finally:
        # Cleanup
        await server.stop()


async def wait_for_grpc_server(
    port: int,
    process: subprocess.Popen,
    timeout: float = 10.0,
    interval: float = 0.1,
) -> bool:
    """Wait for a gRPC server to become available.

    Args:
        port: Port number to check
        process: Server subprocess
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Returns:
        bool: True if server is available, False if timeout or process died
    """
    start = time.time()
    while time.time() - start < timeout:
        # Check if process is still running
        if process.poll() is not None:
            # Process died
            stdout, stderr = process.communicate()
            print(f"Go gRPC server exited early (code {process.returncode})")
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
            return False

        # Try to connect to the port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(("localhost", port))
                # Connection successful - server is ready
                return True
        except (ConnectionRefusedError, OSError):
            # Not ready yet, try again
            pass

        await asyncio.sleep(interval)

    return False


@asynccontextmanager
async def go_grpc_server(port: int | None = None):
    """Start a Go gRPC server for testing.

    This starts the Go gRPC test server as a subprocess.

    Args:
        port: Port to use. If None, a free port is found automatically.

    Yields:
        tuple: (port, process) - The port number and subprocess handle

    Example:
        async with go_grpc_server() as (port, proc):
            # Connect gRPC client to localhost:{port}
            pass
    """
    if port is None:
        port = find_free_port()

    # Get the path to the agenkit-go directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    go_test_dir = os.path.join(current_dir, "..", "..", "agenkit-go", "tests", "integration")

    # S607, ASYNC220: Safe in test infrastructure - port is test parameter, not user input
    process = popen_server(
        ["go", "run", "test_grpc_server.go", str(port)],
        cwd=go_test_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to be ready with proper health checking
        if not await wait_for_grpc_server(port, process, timeout=10.0):
            terminate_server(process)
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Go gRPC server failed to start on port {port}\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        yield port, process
    finally:
        terminate_server(process)
