"""Batching middleware for combining multiple requests.

This middleware collects multiple concurrent requests and processes them as a batch,
improving throughput at the cost of added latency.

Use cases:
- LLM batch processing (reduce API costs via batch endpoints)
- Database bulk operations (reduce round trips)
- High-throughput data processing (maximize resource utilization)

Trade-offs:
- Latency vs throughput: Adds wait time but improves throughput
- Memory usage: Buffers requests in queue
- Complexity: Handles partial failures and request/response mapping
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

from agenkit.interfaces import Agent, Message


@dataclass
class BatchingConfig:
    """Configuration for batching behavior."""

    max_batch_size: int = 10  # Process when we have this many requests
    max_wait_time: float = 0.1  # Process after this many seconds (100ms)
    max_queue_size: int = 1000  # Backpressure limit

    def __post_init__(self):
        """Validate configuration."""
        if self.max_batch_size < 1:
            raise ValueError("max_batch_size must be at least 1")
        if self.max_wait_time <= 0:
            raise ValueError("max_wait_time must be positive")
        if self.max_queue_size < self.max_batch_size:
            raise ValueError("max_queue_size must be >= max_batch_size")


@dataclass
class BatchingMetrics:
    """Metrics for batching middleware."""

    total_requests: int = 0
    total_batches: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    partial_batches: int = 0  # Batches with some failures
    total_wait_time: float = 0.0  # Total time requests spent waiting
    min_batch_size: Optional[int] = None
    max_batch_size: Optional[int] = None

    @property
    def avg_batch_size(self) -> float:
        """Calculate average batch size."""
        if self.total_batches == 0:
            return 0.0
        return self.total_requests / self.total_batches

    @property
    def avg_wait_time(self) -> float:
        """Calculate average wait time per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_wait_time / self.total_requests


class BatchRequest:
    """Represents a single request in a batch."""

    def __init__(self, message: Message):
        """Initialize batch request.

        Args:
            message: The message to process
        """
        self.message = message
        self.future: asyncio.Future[Message] = asyncio.Future()
        self.enqueued_at = time.time()


class BatchingDecorator(Agent):
    """Agent decorator that batches multiple concurrent requests.

    This middleware collects concurrent requests and processes them as a batch,
    improving throughput by amortizing per-request overhead across multiple requests.

    The batch is processed when either:
    1. max_batch_size requests have been collected, OR
    2. max_wait_time has elapsed since the first request in the batch

    Each request receives its individual result, even if other requests in the
    batch fail (partial failure support).

    Example:
        >>> config = BatchingConfig(max_batch_size=5, max_wait_time=0.05)
        >>> batching_agent = BatchingDecorator(agent, config)
        >>> # Concurrent requests will be automatically batched
        >>> results = await asyncio.gather(
        ...     batching_agent.process(msg1),
        ...     batching_agent.process(msg2),
        ...     batching_agent.process(msg3)
        ... )
    """

    def __init__(self, agent: Agent, config: Optional[BatchingConfig] = None):
        """Initialize batching decorator.

        Args:
            agent: The agent to wrap
            config: Batching configuration (uses defaults if not provided)
        """
        self._agent = agent
        self._config = config or BatchingConfig()
        self._metrics = BatchingMetrics()

        # Queue for collecting requests
        self._queue: asyncio.Queue[BatchRequest] = asyncio.Queue(
            maxsize=self._config.max_queue_size
        )

        # Background task for processing batches
        self._batch_task: Optional[asyncio.Task] = None
        self._shutdown = False

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> BatchingMetrics:
        """Return batching metrics."""
        return self._metrics

    async def _ensure_batch_processor(self):
        """Ensure batch processor task is running."""
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._batch_processor())

    async def _batch_processor(self):
        """Background task that processes batches.

        This task runs continuously, collecting requests from the queue and
        processing them as batches based on the configured thresholds.
        """
        while not self._shutdown:
            try:
                batch = await self._collect_batch()
                if batch:
                    await self._process_batch(batch)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but don't crash the processor
                print(f"Batch processor error: {e}")

    async def _collect_batch(self) -> List[BatchRequest]:
        """Collect a batch of requests from the queue.

        Returns:
            List of batch requests, empty if queue is empty
        """
        batch: List[BatchRequest] = []
        deadline = None

        try:
            # Wait for first request (blocking)
            first_request = await asyncio.wait_for(
                self._queue.get(), timeout=0.1  # Short timeout to check shutdown
            )
            batch.append(first_request)
            deadline = time.time() + self._config.max_wait_time

            # Collect more requests until batch full or timeout
            while len(batch) < self._config.max_batch_size:
                remaining_time = deadline - time.time()
                if remaining_time <= 0:
                    break

                try:
                    request = await asyncio.wait_for(
                        self._queue.get(), timeout=remaining_time
                    )
                    batch.append(request)
                except asyncio.TimeoutError:
                    break

        except asyncio.TimeoutError:
            # No requests in queue, return empty batch
            pass

        return batch

    async def _process_batch(self, batch: List[BatchRequest]):
        """Process a batch of requests.

        Args:
            batch: List of batch requests to process
        """
        if not batch:
            return

        batch_size = len(batch)
        self._metrics.total_batches += 1
        self._metrics.total_requests += batch_size

        # Update batch size metrics
        if self._metrics.min_batch_size is None:
            self._metrics.min_batch_size = batch_size
        else:
            self._metrics.min_batch_size = min(self._metrics.min_batch_size, batch_size)

        if self._metrics.max_batch_size is None:
            self._metrics.max_batch_size = batch_size
        else:
            self._metrics.max_batch_size = max(self._metrics.max_batch_size, batch_size)

        # Calculate wait times
        now = time.time()
        for req in batch:
            wait_time = now - req.enqueued_at
            self._metrics.total_wait_time += wait_time

        # Process each request individually (parallel execution)
        # Note: For true batch processing (single API call for multiple requests),
        # the underlying agent would need to support batch operations.
        # This implementation processes requests in parallel.
        results = await asyncio.gather(
            *[self._agent.process(req.message) for req in batch],
            return_exceptions=True
        )

        # Distribute results to individual futures
        successes = 0
        failures = 0

        for req, result in zip(batch, results):
            if isinstance(result, Exception):
                req.future.set_exception(result)
                failures += 1
            else:
                req.future.set_result(result)
                successes += 1

        # Update batch metrics
        if failures == 0:
            self._metrics.successful_batches += 1
        elif successes == 0:
            self._metrics.failed_batches += 1
        else:
            self._metrics.partial_batches += 1

    async def process(self, message: Message) -> Message:
        """Process message with batching.

        This method enqueues the message and waits for it to be processed as part
        of a batch.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            asyncio.QueueFull: If queue is at capacity (backpressure)
            Exception: If message processing fails
        """
        # Ensure batch processor is running
        await self._ensure_batch_processor()

        # Create batch request
        request = BatchRequest(message)

        # Enqueue request (may raise QueueFull if at capacity)
        try:
            await asyncio.wait_for(
                self._queue.put(request), timeout=1.0  # Prevent indefinite blocking
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Failed to enqueue request within timeout (queue size: {self._queue.qsize()})"
            )

        # Wait for result
        return await request.future

    async def flush(self):
        """Flush any pending requests in the queue.

        This method processes any remaining requests in the queue immediately,
        regardless of batch size thresholds. Useful for graceful shutdown.
        """
        while not self._queue.empty():
            batch = []
            try:
                while len(batch) < self._config.max_batch_size and not self._queue.empty():
                    batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

            if batch:
                await self._process_batch(batch)

    async def shutdown(self):
        """Shutdown the batching middleware.

        This method:
        1. Stops accepting new requests
        2. Flushes pending requests
        3. Cancels the batch processor task
        """
        self._shutdown = True

        # Flush any pending requests
        await self.flush()

        # Cancel batch processor
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

    def __del__(self):
        """Cleanup on deletion."""
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
