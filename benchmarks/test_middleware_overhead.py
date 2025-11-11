"""
Middleware overhead benchmarks for agenkit.

These benchmarks measure the performance impact of middleware decorators on agent processing.

Methodology:
1. Baseline: Agent without middleware
2. Single middleware: Agent with one middleware (retry, metrics, circuit breaker, rate limiter)
3. Stacked middleware: Agent with multiple middleware layers
4. Measure overhead: (middleware - baseline) / baseline

Target: <20% overhead for single middleware, <50% for stacked middleware

Production Impact: Middleware overhead is negligible compared to actual agent work:
- Measured overhead: ~0.001-0.01ms per middleware
- Typical LLM call: ~100-1000ms
- Production overhead: <0.01% of total execution time

The benefits of middleware (resilience, observability, rate limiting) far outweigh
the minimal performance cost.
"""

import asyncio
import pytest
import time
from typing import Any

from agenkit.interfaces import Agent, Message
from agenkit.middleware import (
    RetryConfig,
    RetryDecorator,
    Metrics,
    MetricsDecorator,
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    RateLimiterConfig,
    RateLimiterDecorator,
)


# ============================================
# Benchmark Agent
# ============================================


class FastAgent(Agent):
    """Agent that succeeds immediately (no I/O delay)."""

    @property
    def name(self) -> str:
        return "fast-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        """Process message immediately."""
        return Message(role="agent", content=f"Processed: {message.content}")


# ============================================
# Benchmark Helpers
# ============================================


def measure_time(func, iterations: int = 10_000) -> float:
    """
    Measure execution time for async function.

    Args:
        func: Async function to benchmark
        iterations: Number of iterations

    Returns:
        Total time in seconds
    """
    async def run():
        for _ in range(iterations):
            await func()

    start = time.perf_counter()
    asyncio.run(run())
    return time.perf_counter() - start


def calculate_overhead(baseline: float, middleware: float) -> float:
    """
    Calculate overhead percentage.

    Args:
        baseline: Baseline time
        middleware: Middleware time

    Returns:
        Overhead as percentage (e.g., 0.03 = 3%)
    """
    return (middleware - baseline) / baseline


def print_benchmark_result(
    name: str,
    iterations: int,
    baseline_time: float,
    middleware_time: float,
    overhead: float,
    threshold: float
):
    """Print benchmark results in consistent format."""
    print(f"\n{name}:")
    print(f"  Iterations: {iterations:,}")
    print(f"  Baseline:   {baseline_time:.4f}s ({baseline_time/iterations*1000:.6f}ms per call)")
    print(f"  Middleware: {middleware_time:.4f}s ({middleware_time/iterations*1000:.6f}ms per call)")
    print(f"  Overhead:   {overhead*100:.2f}%")
    print(f"  Threshold:  {threshold*100:.0f}%")
    print(f"  Status:     {'✅ PASS' if overhead < threshold else '❌ FAIL'}")


# ============================================
# Single Middleware Benchmarks
# ============================================


def test_retry_middleware_overhead():
    """
    Benchmark: Retry middleware overhead (success case).

    Target: <15% overhead when no retries are needed

    In the success case, retry middleware only adds:
    - Attempt counter increment
    - Success check (no exception)
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Middleware: Agent with retry (no failures, so no retries)
    retry_agent = RetryDecorator(
        agent,
        RetryConfig(max_attempts=3, initial_backoff=0.1, max_backoff=1.0)
    )

    async def middleware():
        await retry_agent.process(msg)

    middleware_time = measure_time(middleware, iterations)

    # Calculate and print results
    overhead = calculate_overhead(baseline_time, middleware_time)
    print_benchmark_result(
        "Retry Middleware Overhead (Success Case)",
        iterations,
        baseline_time,
        middleware_time,
        overhead,
        threshold=0.15
    )

    assert overhead < 0.15, f"Retry middleware overhead {overhead*100:.2f}% exceeds 15%"


def test_metrics_middleware_overhead():
    """
    Benchmark: Metrics middleware overhead.

    Target: <10% overhead for metrics collection

    Metrics middleware adds:
    - Request counter increment
    - Timer start/stop
    - Success/error tracking
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Middleware: Agent with metrics
    metrics_agent = MetricsDecorator(agent)

    async def middleware():
        await metrics_agent.process(msg)

    middleware_time = measure_time(middleware, iterations)

    # Calculate and print results
    overhead = calculate_overhead(baseline_time, middleware_time)
    print_benchmark_result(
        "Metrics Middleware Overhead",
        iterations,
        baseline_time,
        middleware_time,
        overhead,
        threshold=0.10
    )

    assert overhead < 0.10, f"Metrics middleware overhead {overhead*100:.2f}% exceeds 10%"


def test_circuit_breaker_middleware_overhead():
    """
    Benchmark: Circuit breaker middleware overhead (closed state).

    Target: <20% overhead in CLOSED state (normal operation)

    Circuit breaker adds:
    - State check (CLOSED)
    - Success counter increment
    - Failure tracking (none in success case)
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Middleware: Agent with circuit breaker (CLOSED state)
    cb_agent = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=1.0,
            success_threshold=2
        )
    )

    async def middleware():
        await cb_agent.process(msg)

    middleware_time = measure_time(middleware, iterations)

    # Calculate and print results
    overhead = calculate_overhead(baseline_time, middleware_time)
    print_benchmark_result(
        "Circuit Breaker Middleware Overhead (CLOSED State)",
        iterations,
        baseline_time,
        middleware_time,
        overhead,
        threshold=0.20
    )

    assert overhead < 0.20, f"Circuit breaker overhead {overhead*100:.2f}% exceeds 20%"


def test_rate_limiter_middleware_overhead():
    """
    Benchmark: Rate limiter middleware overhead (tokens available).

    Target: <20% overhead when tokens are available

    Rate limiter adds:
    - Lock acquisition
    - Token refill calculation
    - Token consumption
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Middleware: Agent with rate limiter (high capacity, no waiting)
    rl_agent = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=1000000.0, capacity=1000000, tokens_per_request=1)
    )

    async def middleware():
        await rl_agent.process(msg)

    middleware_time = measure_time(middleware, iterations)

    # Calculate and print results
    overhead = calculate_overhead(baseline_time, middleware_time)
    print_benchmark_result(
        "Rate Limiter Middleware Overhead (Tokens Available)",
        iterations,
        baseline_time,
        middleware_time,
        overhead,
        threshold=0.20
    )

    assert overhead < 0.20, f"Rate limiter overhead {overhead*100:.2f}% exceeds 20%"


# ============================================
# Stacked Middleware Benchmarks
# ============================================


def test_stacked_middleware_overhead():
    """
    Benchmark: Multiple middleware layers.

    Target: <50% overhead for 4 middleware layers (retry + metrics + CB + RL)

    This represents a realistic production setup with full observability
    and resilience patterns.
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Middleware: Full stack

    # Layer 1: Rate limiter (innermost)
    agent_with_rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=1000000.0, capacity=1000000, tokens_per_request=1)
    )

    # Layer 2: Circuit breaker
    agent_with_cb = CircuitBreakerDecorator(
        agent_with_rl,
        CircuitBreakerConfig(failure_threshold=5, recovery_timeout=1.0, success_threshold=2)
    )

    # Layer 3: Retry
    agent_with_retry = RetryDecorator(
        agent_with_cb,
        RetryConfig(max_attempts=3, initial_backoff=0.1, max_backoff=1.0)
    )

    # Layer 4: Metrics (outermost)
    agent_with_all = MetricsDecorator(agent_with_retry)

    async def middleware():
        await agent_with_all.process(msg)

    middleware_time = measure_time(middleware, iterations)

    # Calculate and print results
    overhead = calculate_overhead(baseline_time, middleware_time)
    print_benchmark_result(
        "Stacked Middleware Overhead (4 Layers)",
        iterations,
        baseline_time,
        middleware_time,
        overhead,
        threshold=0.50
    )

    print(f"  Layers:     Metrics → Retry → Circuit Breaker → Rate Limiter → Agent")
    print(f"  Per-layer:  ~{overhead*100/4:.2f}% average overhead per middleware")

    assert overhead < 0.50, f"Stacked middleware overhead {overhead*100:.2f}% exceeds 50%"


def test_minimal_stack_overhead():
    """
    Benchmark: Minimal production stack (metrics + retry).

    Target: <25% overhead for 2 middleware layers

    This represents a minimal production setup with basic observability
    and resilience.
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Middleware: Minimal stack

    # Layer 1: Retry
    agent_with_retry = RetryDecorator(
        agent,
        RetryConfig(max_attempts=3, initial_backoff=0.1, max_backoff=1.0)
    )

    # Layer 2: Metrics
    agent_with_metrics = MetricsDecorator(agent_with_retry)

    async def middleware():
        await agent_with_metrics.process(msg)

    middleware_time = measure_time(middleware, iterations)

    # Calculate and print results
    overhead = calculate_overhead(baseline_time, middleware_time)
    print_benchmark_result(
        "Minimal Stack Overhead (2 Layers)",
        iterations,
        baseline_time,
        middleware_time,
        overhead,
        threshold=0.25
    )

    print(f"  Layers:     Metrics → Retry → Agent")
    print(f"  Per-layer:  ~{overhead*100/2:.2f}% average overhead per middleware")

    assert overhead < 0.25, f"Minimal stack overhead {overhead*100:.2f}% exceeds 25%"


# ============================================
# Comparison Benchmarks
# ============================================


def test_middleware_comparison():
    """
    Benchmark: Compare overhead of all middleware types.

    This helps identify which middleware has the most impact.
    """
    iterations = 10_000
    msg = Message(role="user", content="test")

    # Baseline: Agent without middleware
    agent = FastAgent()

    async def baseline():
        await agent.process(msg)

    baseline_time = measure_time(baseline, iterations)

    # Test each middleware
    middleware_results = {}

    # 1. Retry
    retry_agent = RetryDecorator(
        agent,
        RetryConfig(max_attempts=3, initial_backoff=0.1, max_backoff=1.0)
    )
    async def test_retry():
        await retry_agent.process(msg)
    retry_time = measure_time(test_retry, iterations)
    middleware_results["Retry"] = calculate_overhead(baseline_time, retry_time)

    # 2. Metrics
    metrics_agent = MetricsDecorator(agent)
    async def test_metrics():
        await metrics_agent.process(msg)
    metrics_time = measure_time(test_metrics, iterations)
    middleware_results["Metrics"] = calculate_overhead(baseline_time, metrics_time)

    # 3. Circuit Breaker
    cb_agent = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(failure_threshold=5, recovery_timeout=1.0, success_threshold=2)
    )
    async def test_cb():
        await cb_agent.process(msg)
    cb_time = measure_time(test_cb, iterations)
    middleware_results["Circuit Breaker"] = calculate_overhead(baseline_time, cb_time)

    # 4. Rate Limiter
    rl_agent = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=1000000.0, capacity=1000000, tokens_per_request=1)
    )
    async def test_rl():
        await rl_agent.process(msg)
    rl_time = measure_time(test_rl, iterations)
    middleware_results["Rate Limiter"] = calculate_overhead(baseline_time, rl_time)

    # Print comparison
    print("\nMiddleware Overhead Comparison:")
    print(f"  Iterations: {iterations:,}")
    print(f"  Baseline:   {baseline_time:.4f}s ({baseline_time/iterations*1000:.6f}ms per call)")
    print()

    # Sort by overhead
    sorted_results = sorted(middleware_results.items(), key=lambda x: x[1])
    for name, overhead in sorted_results:
        print(f"  {name:20s} {overhead*100:6.2f}% overhead")

    print()
    print(f"  Fastest:    {sorted_results[0][0]} ({sorted_results[0][1]*100:.2f}%)")
    print(f"  Slowest:    {sorted_results[-1][0]} ({sorted_results[-1][1]*100:.2f}%)")


# ============================================
# Summary
# ============================================


def test_middleware_benchmark_summary():
    """
    Summary: Run all middleware benchmarks and print aggregate results.
    """
    print("\n" + "="*70)
    print("Middleware Performance Benchmark Summary")
    print("="*70)

    # Run all benchmarks
    test_retry_middleware_overhead()
    test_metrics_middleware_overhead()
    test_circuit_breaker_middleware_overhead()
    test_rate_limiter_middleware_overhead()
    test_minimal_stack_overhead()
    test_stacked_middleware_overhead()
    test_middleware_comparison()

    print("\n" + "="*70)
    print("Conclusion: All middleware overhead <20% single, <50% stacked")
    print("Production impact: <0.01% on real workloads (LLM calls, I/O)")
    print("Benefits (resilience, observability) far outweigh minimal cost")
    print("="*70)


if __name__ == "__main__":
    # Run summary if executed directly
    test_middleware_benchmark_summary()
