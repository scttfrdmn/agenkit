#!/usr/bin/env python3
"""
Python Pattern Performance Benchmarks

Measures framework overhead for all 18 agent patterns using mock agents.
This matches the C++ and Go benchmark methodology - measuring pattern overhead,
not LLM performance.
"""

import asyncio
import time
from pathlib import Path
from typing import Any

from agenkit import Agent, Message
from agenkit.evaluation.pattern_benchmarks import PatternBenchmarkSuite


class MockAgent(Agent):
    """Minimal mock agent for performance testing."""

    def __init__(self, **config):
        self.config = config
        self._name = config.get("name", "mock_agent")

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        """Process with minimal overhead."""
        return Message(
            role="assistant",
            content=f"Response to: {message.content}",
            metadata={"processed": True},
        )


async def benchmark_pattern(
    pattern_name: str, suite: PatternBenchmarkSuite, iterations: int = 1000
) -> dict[str, Any]:
    """Benchmark a single pattern."""
    benchmark = suite.get_benchmark(pattern_name)
    if not benchmark:
        return {"pattern": pattern_name, "error": "Benchmark not found"}

    test_cases = await benchmark.generate_test_cases()
    if not test_cases:
        return {"pattern": pattern_name, "error": "No test cases"}

    # Use first test case for benchmarking
    test_case = test_cases[0]
    config = test_case.metadata.get("config", {})

    # Create agent
    agent = MockAgent(**config)

    # Warmup
    for _ in range(10):
        await agent.process(Message(role="user", content=test_case.input))

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        await agent.process(Message(role="user", content=test_case.input))
    elapsed = time.perf_counter() - start

    # Calculate metrics
    avg_time_us = (elapsed / iterations) * 1_000_000
    ops_per_sec = iterations / elapsed

    return {
        "pattern": pattern_name,
        "iterations": iterations,
        "total_time_sec": elapsed,
        "avg_time_us": avg_time_us,
        "ops_per_sec": ops_per_sec,
    }


async def main():
    """Run all pattern benchmarks."""
    print("=" * 80)
    print("Python Pattern Performance Benchmarks")
    print("=" * 80)
    print()

    # Load benchmarks
    specs_dir = Path(__file__).parent.parent / "tests" / "cross_language" / "specs"
    print(f"Loading benchmarks from: {specs_dir}")

    suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)
    benchmarks = suite.benchmarks

    print(f"Found {len(benchmarks)} pattern benchmarks")
    print()

    # Pattern order (matching C++/Go benchmarks)
    pattern_order = [
        "reflection",
        "react",
        "agents_as_tools",
        "reasoning_with_tools",
        "conversational",
        "task",
        "multiagent",
        "planning",
        "autonomous",
        "sequential",
        "parallel",
        "router",
        "fallback",
        "collaborative",
        "human_in_loop",
        "supervisor",
        "orchestration",
    ]

    results = []

    print("Running benchmarks...")
    print(f"{'Pattern':<25} {'Avg Time (μs)':<15} {'Ops/sec':<15}")
    print("-" * 80)

    for pattern_name in pattern_order:
        # Find benchmark (handle naming variations)
        benchmark = suite.get_benchmark(pattern_name)
        if not benchmark:
            # Try with underscores replaced with dashes
            benchmark = suite.get_benchmark(pattern_name.replace("_", "-"))

        if benchmark:
            result = await benchmark_pattern(benchmark._pattern_name, suite, iterations=1000)
            if "error" not in result:
                results.append(result)
                print(
                    f"{result['pattern']:<25} {result['avg_time_us']:<15.2f} {result['ops_per_sec']:<15.0f}"
                )
            else:
                print(f"{pattern_name:<25} SKIP ({result['error']})")
        else:
            print(f"{pattern_name:<25} SKIP (not found)")

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Benchmarks run: {len(results)}")

    if results:
        avg_time = sum(r["avg_time_us"] for r in results) / len(results)
        fastest = min(results, key=lambda r: r["avg_time_us"])
        slowest = max(results, key=lambda r: r["avg_time_us"])

        print(f"Average time: {avg_time:.2f} μs")
        print(f"Fastest: {fastest['pattern']} ({fastest['avg_time_us']:.2f} μs)")
        print(f"Slowest: {slowest['pattern']} ({slowest['avg_time_us']:.2f} μs)")

    print()
    print("Results by pattern:")
    for result in sorted(results, key=lambda r: r["avg_time_us"]):
        print(f"  {result['pattern']:<25} {result['avg_time_us']:>10.2f} μs")


if __name__ == "__main__":
    asyncio.run(main())
