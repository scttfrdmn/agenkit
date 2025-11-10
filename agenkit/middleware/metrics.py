"""Metrics collection middleware."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from agenkit.interfaces import Agent, Message


@dataclass
class Metrics:
    """Observability metrics for an agent."""

    # Request metrics
    total_requests: int = 0
    success_requests: int = 0
    error_requests: int = 0

    # Latency metrics (in seconds)
    total_latency: float = 0.0
    min_latency: float = 0.0
    max_latency: float = 0.0

    # Current state
    in_flight_requests: int = 0

    # Lock for thread-safe updates
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def average_latency(self) -> float:
        """Return average request latency in seconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency / self.total_requests

    def error_rate(self) -> float:
        """Return error rate as a percentage (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.error_requests / self.total_requests

    def snapshot(self) -> "Metrics":
        """Return a copy of the current metrics.

        Note: This is not thread-safe. Use with caution.
        """
        return Metrics(
            total_requests=self.total_requests,
            success_requests=self.success_requests,
            error_requests=self.error_requests,
            total_latency=self.total_latency,
            min_latency=self.min_latency,
            max_latency=self.max_latency,
            in_flight_requests=self.in_flight_requests,
        )

    async def reset(self) -> None:
        """Clear all metrics."""
        async with self._lock:
            self.total_requests = 0
            self.success_requests = 0
            self.error_requests = 0
            self.total_latency = 0.0
            self.min_latency = 0.0
            self.max_latency = 0.0
            self.in_flight_requests = 0


class MetricsDecorator(Agent):
    """Agent decorator that collects observability metrics."""

    def __init__(self, agent: Agent):
        """Initialize metrics decorator.

        Args:
            agent: The agent to wrap
        """
        self._agent = agent
        self._metrics = Metrics()

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    def get_metrics(self) -> Metrics:
        """Return the current metrics."""
        return self._metrics

    async def process(self, message: Message) -> Message:
        """Process message with metrics collection.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            Exception: If the underlying agent raises an error
        """
        # Record in-flight request
        async with self._metrics._lock:
            self._metrics.in_flight_requests += 1

        try:
            # Record start time
            start = time.time()

            # Call underlying agent
            response = await self._agent.process(message)

            # Record latency
            latency = time.time() - start

            # Update metrics
            async with self._metrics._lock:
                self._metrics.total_requests += 1
                self._metrics.success_requests += 1
                self._metrics.total_latency += latency

                # Update min/max latency
                if self._metrics.min_latency == 0 or latency < self._metrics.min_latency:
                    self._metrics.min_latency = latency
                if latency > self._metrics.max_latency:
                    self._metrics.max_latency = latency

            return response

        except Exception as e:
            # Record latency even on error
            latency = time.time() - start

            # Update error metrics
            async with self._metrics._lock:
                self._metrics.total_requests += 1
                self._metrics.error_requests += 1
                self._metrics.total_latency += latency

                # Update min/max latency
                if self._metrics.min_latency == 0 or latency < self._metrics.min_latency:
                    self._metrics.min_latency = latency
                if latency > self._metrics.max_latency:
                    self._metrics.max_latency = latency

            raise

        finally:
            # Record completion of in-flight request
            async with self._metrics._lock:
                self._metrics.in_flight_requests -= 1
