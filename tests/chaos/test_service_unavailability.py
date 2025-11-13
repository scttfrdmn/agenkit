"""
Service Unavailability Chaos Tests

Tests system resilience when services are unavailable:
- Service crashes
- Service startup delays
- Graceful shutdown during requests
- Service overload
- Dependency failure cascades

These tests validate circuit breaker and retry behavior under service failures.
"""
import asyncio
import time

import pytest

from agenkit.interfaces import Agent, Message
from tests.chaos.chaos_agents import ChaosAgent, ChaosMode, OverloadedAgent, FlakeyAgent


class SimpleAgent(Agent):
    """Simple agent for testing."""

    def __init__(self, name: str = "simple-agent"):
        self._name = name
        self._processing = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    def is_processing(self) -> bool:
        return self._processing

    async def process(self, message: Message) -> Message:
        self._processing = True
        try:
            await asyncio.sleep(0.01)  # Simulate work
            return Message(
                role="agent",
                content=f"Processed: {message.content}",
                metadata={"agent": self.name}
            )
        finally:
            self._processing = False


# ============================================
# Service Crash Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_service_crash():
    """Test behavior when service crashes."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.CRASH)

    message = Message(role="user", content="Test")

    with pytest.raises(RuntimeError) as exc_info:
        await chaos_agent.process(message)

    assert "crashed" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_service_crash_after_n_requests():
    """Test service that crashes after N successful requests."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent)
    chaos_agent.set_crash_after(3)  # Crash after 3 requests

    message = Message(role="user", content="Test")

    # First 3 requests should succeed
    for i in range(3):
        response = await chaos_agent.process(message)
        assert response.content == "Processed: Test"

    # 4th request should crash
    with pytest.raises(RuntimeError) as exc_info:
        await chaos_agent.process(message)

    assert "crashed" in str(exc_info.value)
    assert chaos_agent.get_stats()["request_count"] == 4


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_crash_mid_request():
    """Test crash during request processing."""

    class CrashingAgent(Agent):
        @property
        def name(self) -> str:
            return "crashing"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            await asyncio.sleep(0.05)  # Start processing
            raise RuntimeError("Crashed during processing")

    agent = CrashingAgent()
    message = Message(role="user", content="Test")

    with pytest.raises(RuntimeError) as exc_info:
        await agent.process(message)

    assert "Crashed during processing" in str(exc_info.value)


# ============================================
# Service Startup Delay Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_slow_service_startup():
    """Test service with slow startup (delays before accepting requests)."""

    class SlowStartupAgent(Agent):
        def __init__(self):
            self._ready = False
            self._startup_delay = 0.2  # 200ms startup

        @property
        def name(self) -> str:
            return "slow-startup"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def _ensure_ready(self):
            if not self._ready:
                await asyncio.sleep(self._startup_delay)
                self._ready = True

        async def process(self, message: Message) -> Message:
            await self._ensure_ready()
            return Message(role="agent", content=f"Processed: {message.content}")

    agent = SlowStartupAgent()
    message = Message(role="user", content="Test")

    # First request should be slow (startup delay)
    start = time.time()
    response = await agent.process(message)
    first_elapsed = time.time() - start

    assert response.content == "Processed: Test"
    assert first_elapsed >= 0.2, f"First request should take >=200ms, took {first_elapsed:.3f}s"

    # Second request should be fast (already started up)
    start = time.time()
    response = await agent.process(message)
    second_elapsed = time.time() - start

    assert second_elapsed < 0.1, f"Second request should be fast, took {second_elapsed:.3f}s"


# ============================================
# Graceful Shutdown Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_graceful_shutdown_during_request():
    """Test graceful shutdown while requests are in progress."""

    class ShutdownAgent(Agent):
        def __init__(self):
            self._shutdown = False

        @property
        def name(self) -> str:
            return "shutdown-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        def shutdown(self):
            self._shutdown = True

        async def process(self, message: Message) -> Message:
            if self._shutdown:
                raise ConnectionError("Service shutting down")

            # Simulate long-running request
            await asyncio.sleep(0.1)

            # Check again after processing
            if self._shutdown:
                raise ConnectionError("Service shut down during processing")

            return Message(role="agent", content=f"Processed: {message.content}")

    agent = ShutdownAgent()
    message = Message(role="user", content="Test")

    # Start a request
    task = asyncio.create_task(agent.process(message))

    # Shutdown immediately
    agent.shutdown()

    # Request should fail gracefully
    with pytest.raises(ConnectionError) as exc_info:
        await task

    assert "shutting down" in str(exc_info.value) or "shut down" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_shutdown_rejects_new_requests():
    """Test that shutdown service rejects new requests."""

    class ShutdownAgent(Agent):
        def __init__(self):
            self._shutdown = False

        @property
        def name(self) -> str:
            return "shutdown-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        def shutdown(self):
            self._shutdown = True

        async def process(self, message: Message) -> Message:
            if self._shutdown:
                raise ConnectionRefusedError("Service not accepting requests (shutdown)")

            return Message(role="agent", content=f"Processed: {message.content}")

    agent = ShutdownAgent()
    message = Message(role="user", content="Test")

    # Request should work
    response = await agent.process(message)
    assert response.content == "Processed: Test"

    # Shutdown
    agent.shutdown()

    # New request should be rejected
    with pytest.raises(ConnectionRefusedError) as exc_info:
        await agent.process(message)

    assert "not accepting requests" in str(exc_info.value)


# ============================================
# Service Overload Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_service_overload():
    """Test service behavior under overload."""
    base_agent = SimpleAgent()
    overloaded_agent = OverloadedAgent(
        base_agent,
        overload_threshold=5,  # Overload after 5 requests
        overload_failure_rate=0.9  # 90% failure when overloaded
    )

    message = Message(role="user", content="Test")

    # First 5 requests should succeed
    for i in range(5):
        response = await overloaded_agent.process(message)
        assert response.content == "Processed: Test"

    # After overload threshold, most requests should fail
    failures = 0
    successes = 0

    for _ in range(20):
        try:
            await overloaded_agent.process(message)
            successes += 1
        except RuntimeError as e:
            assert "overloaded" in str(e)
            failures += 1

    # Should have mostly failures (expect ~90% failure rate, allow variance)
    assert failures >= 15, f"Expected >=15 failures when overloaded, got {failures}"
    assert successes <= 5, f"Expected <=5 successes when overloaded, got {successes}"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_overload_recovery():
    """Test that service can recover from overload."""
    base_agent = SimpleAgent()
    overloaded_agent = OverloadedAgent(
        base_agent,
        overload_threshold=10,
        overload_failure_rate=0.8
    )

    message = Message(role="user", content="Test")

    # Overload the service
    for _ in range(15):
        try:
            await overloaded_agent.process(message)
        except RuntimeError:
            pass

    assert overloaded_agent.is_overloaded()

    # Reset overload state (simulates service recovery/restart)
    overloaded_agent.reset()

    # Requests should now succeed
    for _ in range(5):
        response = await overloaded_agent.process(message)
        assert response.content == "Processed: Test"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_queue_full_scenario():
    """Test behavior when service queue is full."""

    class QueueFullAgent(Agent):
        def __init__(self, max_queue_size: int = 5):
            self._max_queue_size = max_queue_size
            self._current_queue_size = 0

        @property
        def name(self) -> str:
            return "queue-full-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            if self._current_queue_size >= self._max_queue_size:
                raise RuntimeError(f"Queue full (size={self._current_queue_size})")

            self._current_queue_size += 1
            try:
                await asyncio.sleep(0.05)  # Simulate processing
                return Message(role="agent", content=f"Processed: {message.content}")
            finally:
                self._current_queue_size -= 1

    agent = QueueFullAgent(max_queue_size=3)
    message = Message(role="user", content="Test")

    # Start 3 concurrent requests (fill queue)
    tasks = [asyncio.create_task(agent.process(message)) for _ in range(3)]

    # Give them time to enter queue
    await asyncio.sleep(0.01)

    # 4th request should fail (queue full)
    with pytest.raises(RuntimeError) as exc_info:
        await agent.process(message)

    assert "Queue full" in str(exc_info.value)

    # Wait for original requests to complete
    responses = await asyncio.gather(*tasks)
    assert all(r.content == "Processed: Test" for r in responses)


# ============================================
# Dependency Failure Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_dependency_failure_cascade():
    """Test failure cascade when dependencies fail."""

    class DependencyAgent(Agent):
        @property
        def name(self) -> str:
            return "dependency"

        @property
        def capabilities(self) -> list[str]:
            return ["dependency"]

        async def process(self, message: Message) -> Message:
            raise ConnectionError("Dependency service unavailable")

    class PrimaryAgent(Agent):
        def __init__(self, dependency: Agent):
            self._dependency = dependency

        @property
        def name(self) -> str:
            return "primary"

        @property
        def capabilities(self) -> list[str]:
            return ["primary"]

        async def process(self, message: Message) -> Message:
            # Call dependency
            try:
                await self._dependency.process(message)
            except ConnectionError as e:
                # Dependency failed - cascade the failure
                raise RuntimeError(f"Failed due to dependency: {e}")

            return Message(role="agent", content="Success")

    dependency = DependencyAgent()
    primary = PrimaryAgent(dependency)
    message = Message(role="user", content="Test")

    # Primary should fail due to dependency failure
    with pytest.raises(RuntimeError) as exc_info:
        await primary.process(message)

    assert "Failed due to dependency" in str(exc_info.value)
    assert "unavailable" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_flakey_service_pattern():
    """Test service with specific failure pattern (fail-fail-succeed)."""
    base_agent = SimpleAgent()

    # Fail twice, then succeed
    flakey_agent = FlakeyAgent(
        base_agent,
        failure_pattern=[False, False, True, True]  # fail, fail, succeed, succeed
    )

    message = Message(role="user", content="Test")

    # First two requests should fail
    for i in range(2):
        with pytest.raises(RuntimeError):
            await flakey_agent.process(message)

    # Next two requests should succeed
    for i in range(2):
        response = await flakey_agent.process(message)
        assert response.content == "Processed: Test"

    # Pattern should repeat (cycle)
    with pytest.raises(RuntimeError):
        await flakey_agent.process(message)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "chaos"])
