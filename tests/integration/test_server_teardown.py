"""Regression tests for server-process teardown (#825).

These tests exist because the integration suite leaked 965 orphaned server
processes holding 11.7 GB before anyone noticed. The reason it went unnoticed is
the important part: ``go run`` compiles the source and then *execs* the built
binary as its own child, so ``process.terminate()`` killed the wrapper, the
wrapper exited promptly, ``process.wait()`` returned success — and the process
actually holding the port survived, reparented to PID 1.

So a test that only asserts ``process.poll() is not None`` proves nothing: that
was already true while the leak was happening. Every test here asserts on the
*grandchild*, which is what the old teardown could not see.
"""

import contextlib
import os
import signal
import socket
import subprocess
import sys
import textwrap
import time

import pytest

from .helpers import find_free_port, popen_server, terminate_server, wait_for_port

# A parent that spawns a listening child and then waits, mimicking `go run`'s
# compile-then-exec shape without needing a Go toolchain. The child's PID is
# printed so the test can assert on it directly.
_PARENT_SPAWNS_LISTENER = """
import socket, subprocess, sys, time
port = int(sys.argv[1])
child = subprocess.Popen([sys.executable, "-c", '''
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1])))
s.listen(1)
while True:
    time.sleep(0.05)
''', str(port)])
print(child.pid, flush=True)
child.wait()
"""


# The exact leak shape: the wrapper exits *immediately* after spawning, while the
# child keeps the port and ignores SIGTERM. A teardown that escalates based on the
# wrapper's liveness sees a dead wrapper, concludes it is done, and leaks the child
# — which is how 965 accumulated (#825).
_PARENT_EXITS_LEAVING_STUBBORN_LISTENER = """
import socket, subprocess, sys, time
port = int(sys.argv[1])
child = subprocess.Popen([sys.executable, "-c", '''
import signal, socket, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1])))
s.listen(1)
while True:
    time.sleep(0.05)
''', str(port)])
print(child.pid, flush=True)
sys.exit(0)
"""


def _pid_alive(pid: int) -> bool:
    """True if `pid` still exists. Signal 0 checks existence without delivering."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_gone(pid: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def spawned_tree():
    """Start a parent-plus-listening-child tree; yield (wrapper, child_pid).

    Cleans up unconditionally so a failing assertion in a test does not itself
    leak the very processes these tests are about.
    """
    port = find_free_port()
    wrapper = popen_server(
        [sys.executable, "-c", textwrap.dedent(_PARENT_SPAWNS_LISTENER), str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child_pid = int(wrapper.stdout.readline().strip())
    assert wait_for_port(port, process=wrapper, timeout=10.0), "listener never came up"

    try:
        yield wrapper, child_pid
    finally:
        terminate_server(wrapper)
        if _pid_alive(child_pid):
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.fixture
def spawned_tree_ignoring_sigterm():
    """Like `spawned_tree`, but the child ignores SIGTERM and the wrapper exits at once.

    Real servers ignore or slow-walk SIGTERM (graceful-shutdown handlers that hang, a
    Go binary mid-syscall). Combining that with a wrapper that has already exited is
    what defeats every "wait on the wrapper" teardown.
    """
    port = find_free_port()
    wrapper = popen_server(
        [
            sys.executable,
            "-c",
            textwrap.dedent(_PARENT_EXITS_LEAVING_STUBBORN_LISTENER),
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child_pid = int(wrapper.stdout.readline().strip())
    # Not wait_for_port(process=wrapper): that gives up as soon as the process exits,
    # and this wrapper exits by design. The child owns the port, so poll the port.
    assert wait_for_port(port, timeout=10.0), "listener never came up"

    try:
        yield wrapper, child_pid
    finally:
        terminate_server(wrapper)
        if _pid_alive(child_pid):
            with contextlib.suppress(ProcessLookupError):
                os.kill(child_pid, signal.SIGKILL)


def test_terminate_server_kills_the_grandchild(spawned_tree):
    """The process holding the port must die, not just the wrapper.

    This is the assertion the old teardown would fail. `process.terminate()`
    reaped the wrapper and reported success while this PID kept running (#825).

    The elapsed-time bound matters: it proves SIGTERM actually reached the child's
    process group. Without it, a teardown that signals only `process.pid` still
    passes, because the SIGKILL fallback eventually sweeps the group — five seconds
    later, and without ever giving the server a chance to shut down gracefully.

    That bound also catches a Linux-only ordering bug: polling the group before
    reaping the wrapper sees the wrapper's own zombie as a live group member and
    stalls for the full timeout. macOS reports a zombie-only group as gone, so this
    assertion is the only thing standing between that bug and a green local run.
    """
    wrapper, child_pid = spawned_tree
    assert _pid_alive(child_pid)

    start = time.monotonic()
    terminate_server(wrapper)
    elapsed = time.monotonic() - start

    assert _wait_gone(child_pid), (
        f"pid {child_pid} survived teardown — this is the #825 leak: the process "
        "holding the port is a child of the one Popen returned"
    )
    assert wrapper.poll() is not None
    assert elapsed < 2.0, (
        f"teardown took {elapsed:.1f}s — the child was not reached by the group "
        "SIGTERM and had to be swept by the SIGKILL fallback"
    )


def test_terminate_server_frees_the_port(spawned_tree):
    """The port must be rebindable afterwards.

    Each leaked server kept its listener, so repeated runs also starved
    find_free_port(). Checking the PID is gone and checking the port is free are
    different claims; assert both.
    """
    wrapper, _child_pid = spawned_tree
    port = int(wrapper.args[-1])

    terminate_server(wrapper)
    assert _wait_gone(_child_pid)

    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))  # raises OSError if still held


def test_popen_server_creates_a_new_process_group(spawned_tree):
    """The group signal in terminate_server only works if the spawn opted in.

    Asserted separately because a future edit could drop start_new_session and
    still pass the kill tests on some platforms by accident.
    """
    wrapper, child_pid = spawned_tree

    assert os.getpgid(wrapper.pid) == wrapper.pid, "wrapper is not its own group leader"
    assert os.getpgid(child_pid) == wrapper.pid, "child is outside the wrapper's group"
    assert os.getpgid(wrapper.pid) != os.getpgid(os.getpid()), (
        "server shares pytest's process group — a group kill would target the test runner"
    )


def test_terminate_server_escalates_to_sigkill(spawned_tree_ignoring_sigterm):
    """A child that ignores SIGTERM must still be killed.

    Escalation cannot be driven by waiting on the wrapper: the wrapper exits on
    SIGTERM immediately, so `process.wait()` always succeeds and SIGKILL would
    never fire. Without this test, a teardown that only escalates on
    `wrapper.wait()` timing out looks correct and leaks exactly as before (#825).
    """
    wrapper, child_pid = spawned_tree_ignoring_sigterm

    terminate_server(wrapper)

    assert _wait_gone(child_pid), (
        f"pid {child_pid} ignored SIGTERM and was never escalated to SIGKILL"
    )


def test_terminate_server_is_idempotent(spawned_tree):
    """Teardown runs from both the error path and the `finally` block."""
    wrapper, child_pid = spawned_tree

    terminate_server(wrapper)
    assert _wait_gone(child_pid)
    terminate_server(wrapper)  # must not raise on an already-dead group


def test_terminate_server_survives_an_already_reaped_process():
    """A process that exited on its own must not make teardown raise."""
    process = popen_server([sys.executable, "-c", "pass"])
    process.wait()

    terminate_server(process)
