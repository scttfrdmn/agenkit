"""
Chaos Agent Infrastructure

Provides base classes and utilities for injecting chaos into agent behavior.
These agents wrap normal agents and inject various failure modes for testing.
"""
import asyncio
import random
import time
from typing import AsyncIterator, Optional

from agenkit.interfaces import Agent, Message

try:
    from agenkit.interfaces import StreamingAgent
except ImportError:
    class StreamingAgent(Agent):
        async def stream(self, message: Message) -> AsyncIterator[Message]:
            raise NotImplementedError


class ChaosMode:
    """Enumeration of chaos injection modes."""
    NONE = "none"
    TIMEOUT = "timeout"
    CONNECTION_REFUSED = "connection_refused"
    CONNECTION_DROP = "connection_drop"
    SLOW_RESPONSE = "slow_response"
    INTERMITTENT = "intermittent"
    RANDOM_ERROR = "random_error"
    MEMORY_PRESSURE = "memory_pressure"
    CRASH = "crash"


class ChaosAgent(Agent):
    """
    Agent that injects chaos for testing resilience.

    Supports various failure modes:
    - Timeouts: Delays exceeding configured timeout
    - Connection failures: Simulates network issues
    - Random errors: Probabilistic failures
    - Slow responses: Gradual performance degradation
    """

    def __init__(
        self,
        agent: Agent,
        failure_rate: float = 0.0,
        delay_ms: float = 0.0,
        chaos_mode: str = ChaosMode.NONE,
        name: Optional[str] = None,
    ):
        self._agent = agent
        self._failure_rate = failure_rate
        self._delay_ms = delay_ms
        self._chaos_mode = chaos_mode
        self._name = name or f"chaos-{agent.name}"
        self._request_count = 0
        self._failure_count = 0
        self._crash_after = None  # Set to crash after N requests

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    def set_crash_after(self, count: int):
        """Configure agent to crash after N requests."""
        self._crash_after = count

    def get_stats(self) -> dict:
        """Get chaos statistics."""
        return {
            "request_count": self._request_count,
            "failure_count": self._failure_count,
            "failure_rate": self._failure_count / max(1, self._request_count),
        }

    async def process(self, message: Message) -> Message:
        """Process with chaos injection."""
        self._request_count += 1

        # Check for crash condition
        if self._crash_after is not None and self._request_count > self._crash_after:
            raise RuntimeError("Agent crashed (simulated)")

        # Inject chaos based on mode
        if self._chaos_mode == ChaosMode.TIMEOUT:
            # Simulate timeout by waiting forever
            await asyncio.sleep(999999)

        elif self._chaos_mode == ChaosMode.CONNECTION_REFUSED:
            self._failure_count += 1
            raise ConnectionRefusedError("Connection refused (simulated)")

        elif self._chaos_mode == ChaosMode.CONNECTION_DROP:
            self._failure_count += 1
            raise ConnectionError("Connection dropped (simulated)")

        elif self._chaos_mode == ChaosMode.RANDOM_ERROR:
            if random.random() < self._failure_rate:
                self._failure_count += 1
                raise RuntimeError(f"Random failure (rate={self._failure_rate})")

        elif self._chaos_mode == ChaosMode.SLOW_RESPONSE:
            # Inject delay
            await asyncio.sleep(self._delay_ms / 1000.0)

        elif self._chaos_mode == ChaosMode.INTERMITTENT:
            # Randomly fail or succeed
            if random.random() < self._failure_rate:
                self._failure_count += 1
                raise ConnectionError("Intermittent failure (simulated)")

        elif self._chaos_mode == ChaosMode.MEMORY_PRESSURE:
            # Simulate memory pressure with large response
            large_content = "x" * (10 * 1024 * 1024)  # 10MB
            return Message(
                role="agent",
                content=large_content,
                metadata={"chaos": "memory_pressure"}
            )

        elif self._chaos_mode == ChaosMode.CRASH:
            self._failure_count += 1
            raise RuntimeError("Agent crashed (simulated)")

        # If no chaos or chaos passed, delegate to wrapped agent
        return await self._agent.process(message)


class StreamingChaosAgent(StreamingAgent):
    """
    Streaming agent that injects chaos during streaming.

    Supports chaos injection at different points in the stream:
    - Fail immediately
    - Fail after N chunks
    - Slow streaming
    - Drop connection mid-stream
    """

    def __init__(
        self,
        agent: StreamingAgent,
        failure_rate: float = 0.0,
        fail_after_chunks: Optional[int] = None,
        delay_per_chunk_ms: float = 0.0,
        chaos_mode: str = ChaosMode.NONE,
        name: Optional[str] = None,
    ):
        self._agent = agent
        self._failure_rate = failure_rate
        self._fail_after_chunks = fail_after_chunks
        self._delay_per_chunk_ms = delay_per_chunk_ms
        self._chaos_mode = chaos_mode
        self._name = name or f"chaos-streaming-{agent.name}"
        self._chunk_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        """Non-streaming process delegates to wrapped agent."""
        return await self._agent.process(message)

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream with chaos injection."""
        chunk_count = 0

        async for chunk in self._agent.stream(message):
            chunk_count += 1

            # Inject delay per chunk
            if self._delay_per_chunk_ms > 0:
                await asyncio.sleep(self._delay_per_chunk_ms / 1000.0)

            # Random failures (before yielding)
            if self._chaos_mode == ChaosMode.INTERMITTENT:
                if random.random() < self._failure_rate:
                    raise ConnectionError(f"Intermittent stream failure at chunk {chunk_count}")

            # Yield chunk
            yield chunk

            # Fail after N chunks (after yielding)
            if self._fail_after_chunks is not None and chunk_count >= self._fail_after_chunks:
                raise ConnectionError(f"Stream failed after {chunk_count} chunks")


class FlakeyAgent(Agent):
    """
    Agent with configurable flakiness patterns.

    Useful for testing retry and circuit breaker behavior with realistic
    failure patterns (e.g., fail-fail-succeed, gradual degradation).
    """

    def __init__(
        self,
        agent: Agent,
        failure_pattern: list[bool],
        name: Optional[str] = None,
    ):
        """
        Args:
            agent: Underlying agent to wrap
            failure_pattern: List of bools indicating success/failure per request
                             e.g., [False, False, True] = fail twice, then succeed
        """
        self._agent = agent
        self._failure_pattern = failure_pattern
        self._name = name or f"flakey-{agent.name}"
        self._request_index = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    def reset(self):
        """Reset to beginning of failure pattern."""
        self._request_index = 0

    async def process(self, message: Message) -> Message:
        """Process with configured failure pattern."""
        # Get current position in pattern (cycle if exceeded)
        should_succeed = self._failure_pattern[
            self._request_index % len(self._failure_pattern)
        ]
        self._request_index += 1

        if not should_succeed:
            raise RuntimeError(f"Flakey failure at request {self._request_index}")

        return await self._agent.process(message)


class OverloadedAgent(Agent):
    """
    Agent that simulates overload conditions.

    Starts responding normally, then degrades as request count increases.
    Useful for testing circuit breaker and rate limiter behavior.
    """

    def __init__(
        self,
        agent: Agent,
        overload_threshold: int = 10,
        overload_failure_rate: float = 0.8,
        name: Optional[str] = None,
    ):
        self._agent = agent
        self._overload_threshold = overload_threshold
        self._overload_failure_rate = overload_failure_rate
        self._name = name or f"overloaded-{agent.name}"
        self._request_count = 0
        self._start_time = time.time()

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    def is_overloaded(self) -> bool:
        """Check if agent is currently overloaded."""
        return self._request_count > self._overload_threshold

    def reset(self):
        """Reset overload state."""
        self._request_count = 0
        self._start_time = time.time()

    async def process(self, message: Message) -> Message:
        """Process with overload simulation."""
        self._request_count += 1

        # If overloaded, fail probabilistically
        if self.is_overloaded():
            if random.random() < self._overload_failure_rate:
                raise RuntimeError(
                    f"Service overloaded (requests={self._request_count}, "
                    f"threshold={self._overload_threshold})"
                )

        return await self._agent.process(message)
