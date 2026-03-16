"""
Mock LLM and benchmark utility for framework performance benchmarks.

MockLLM uses zero latency to measure pure framework overhead.
"""

import asyncio
import statistics
import time
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

from agenkit import Message
from agenkit.adapters.llm import LLM

# Patch OpenAILLM stub when the openai package is not installed.
# The minichain/minicrew example files import OpenAILLM at module level but
# benchmarks never actually call it.
import agenkit.adapters.llm as _llm_module  # noqa: E402

if not hasattr(_llm_module, "OpenAILLM"):

    class _OpenAILLMStub:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    _llm_module.OpenAILLM = _OpenAILLMStub  # type: ignore[attr-defined]


class MockLLM(LLM):
    """Zero-latency mock LLM for measuring framework overhead."""

    def __init__(self, response: str = "benchmark response", latency_ms: float = 0) -> None:
        """Create mock LLM with optional simulated latency."""
        self._response = response
        self._latency_ms = latency_ms

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        """Return response after optional simulated latency."""
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000)
        return Message(role="agent", content=self._response)

    async def stream(self, messages: list[Message], **kwargs: Any) -> AsyncIterator[Message]:
        """Yield single chunk."""
        response = await self.complete(messages, **kwargs)
        yield response

    @property
    def model(self) -> str:
        """Return mock model name."""
        return "mock-benchmark-llm"


async def run_benchmark(
    coro_fn: Callable[[], Coroutine[Any, Any, Any]],
    iterations: int = 100,
    warmup: int = 10,
) -> dict[str, float]:
    """
    Benchmark an async coroutine factory over multiple iterations.

    Args:
        coro_fn: Zero-argument callable that returns an awaitable
        iterations: Number of timed iterations
        warmup: Number of warmup iterations (not measured)

    Returns:
        Dict with mean_ms, p50_ms, p95_ms, p99_ms, iter_per_sec
    """
    # Warmup
    for _ in range(warmup):
        await coro_fn()

    # Timed runs
    times_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        await coro_fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        times_ms.append(elapsed_ms)

    times_sorted = sorted(times_ms)
    mean_ms = statistics.mean(times_ms)
    p50_ms = statistics.median(times_ms)

    p95_idx = int(len(times_sorted) * 0.95)
    p99_idx = int(len(times_sorted) * 0.99)
    p95_ms = times_sorted[min(p95_idx, len(times_sorted) - 1)]
    p99_ms = times_sorted[min(p99_idx, len(times_sorted) - 1)]

    iter_per_sec = 1000.0 / mean_ms if mean_ms > 0 else float("inf")

    return {
        "mean_ms": round(mean_ms, 4),
        "p50_ms": round(p50_ms, 4),
        "p95_ms": round(p95_ms, 4),
        "p99_ms": round(p99_ms, 4),
        "iter_per_sec": round(iter_per_sec, 1),
    }
