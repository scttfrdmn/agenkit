#!/usr/bin/env python3
"""
Pattern Benchmarks Demo

Demonstrates how to use the pattern benchmark suite to evaluate agent patterns
using standardized test scenarios loaded from YAML specifications.

This example shows:
1. Loading pattern benchmarks from YAML specs
2. Creating an agent factory for testing
3. Running individual pattern benchmarks
4. Running the full benchmark suite
5. Analyzing results

Usage:
    python3 examples/evaluation/pattern_benchmarks_demo.py
"""

import asyncio
from pathlib import Path

from agenkit.evaluation.pattern_benchmarks import (
    PatternBenchmarkSuite,
    YAMLBenchmarkLoader,
)
from agenkit.interfaces import Agent, Message


class MockReflectionAgent(Agent):
    """Mock reflection agent for demonstration purposes."""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.iteration_count = 0

    @property
    def name(self) -> str:
        """Agent name."""
        return "mock_reflection"

    async def process(self, message: Message) -> Message:
        """Process message with reflection pattern."""
        self.iteration_count += 1

        # Simulate reflection by improving response
        improved_content = (
            f"Improved response (iteration {self.iteration_count}): {message.content}"
        )

        return Message(
            role="assistant",
            content=improved_content,
            metadata={
                "iterations": self.iteration_count,
                "improved": True,
                "pattern": "reflection",
            },
        )


async def demo_loading_benchmarks():
    """Demonstrate loading pattern benchmarks from YAML specs."""
    print("=" * 70)
    print("Pattern Benchmark Loading Demo")
    print("=" * 70)

    # Get specs directory
    specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"
    print(f"\n✓ Loading benchmarks from: {specs_dir}")

    # Create loader
    loader = YAMLBenchmarkLoader(specs_dir)
    print("✓ YAMLBenchmarkLoader created")

    # Load single pattern benchmark
    reflection_benchmark = loader.load_pattern_benchmark("reflection")
    print(f"\n✓ Loaded benchmark: {reflection_benchmark.name}")
    print(f"  Description: {reflection_benchmark.description}")

    # Generate test cases
    test_cases = await reflection_benchmark.generate_test_cases()
    print(f"  Test cases: {len(test_cases)}")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}:")
        print(f"    Input: {test_case.input[:50]}...")
        print(f"    Tags: {test_case.tags}")
        print(f"    Pattern: {test_case.metadata.get('pattern')}")

    # Load all pattern benchmarks
    all_benchmarks = loader.load_all_pattern_benchmarks()
    print(f"\n✓ Loaded {len(all_benchmarks)} total pattern benchmarks")

    pattern_names = [b._pattern_name for b in all_benchmarks]
    print(f"\nAvailable patterns: {', '.join(sorted(pattern_names)[:10])}...")

    return loader


async def demo_running_single_benchmark():
    """Demonstrate running a single pattern benchmark."""
    print("\n" + "=" * 70)
    print("Single Pattern Benchmark Demo")
    print("=" * 70)

    # Create suite and get reflection benchmark
    specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"
    suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)
    benchmark = suite.get_benchmark("reflection")

    print(f"\n✓ Running benchmark: {benchmark.name}")

    # Create agent factory
    def agent_factory(config: dict) -> Agent:
        max_iterations = config.get("max_iterations", 3)
        return MockReflectionAgent(max_iterations=max_iterations)

    # Run benchmark using suite
    results = await suite.run_benchmark(benchmark, agent_factory)

    # Display results
    print(f"\n✓ Benchmark Results for '{results['pattern']}':")
    print(f"  Total test cases: {results['summary']['total']}")
    print(f"  Passed: {results['summary']['passed']}")
    print(f"  Failed: {results['summary']['failed']}")
    print(f"  Total time: {results['summary']['total_time_ms']:.2f}ms")

    if results["summary"]["total"] > 0:
        pass_rate = (results["summary"]["passed"] / results["summary"]["total"]) * 100
        avg_time = results["summary"]["total_time_ms"] / results["summary"]["total"]
        print(f"  Pass rate: {pass_rate:.1f}%")
        print(f"  Avg time per test: {avg_time:.2f}ms")

    # Show individual test case results
    print("\n  Test Case Details:")
    for i, test_result in enumerate(results["test_cases"][:3], 1):
        status = "✓ PASS" if test_result["passed"] else "✗ FAIL"
        print(f"    {i}. {test_result['scenario_id']}: {status} ({test_result['time_ms']:.2f}ms)")

    if len(results["test_cases"]) > 3:
        print(f"    ... and {len(results['test_cases']) - 3} more test cases")

    return results


async def demo_benchmark_suite():
    """Demonstrate using the pattern benchmark suite."""
    print("\n" + "=" * 70)
    print("Pattern Benchmark Suite Demo")
    print("=" * 70)

    # Create suite from YAML specs
    specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"
    suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)

    print(f"\n✓ Created benchmark suite with {len(suite.benchmarks)} patterns")

    # Get specific benchmark
    reflection = suite.get_benchmark("reflection")
    if reflection:
        print(f"✓ Found reflection benchmark: {reflection.name}")

    # Filter benchmarks by tag
    yaml_benchmarks = suite.get_benchmarks_by_tag("yaml_generated")
    print(f"✓ Found {len(yaml_benchmarks)} benchmarks with 'yaml_generated' tag")

    # Show suite summary
    suite_dict = suite.to_dict()
    print("\n✓ Suite Summary:")
    print(f"  Total patterns: {suite_dict['total_benchmarks']}")
    print(f"  Patterns: {', '.join(sorted(suite_dict['patterns'])[:8])}...")

    return suite


async def demo_comparing_patterns():
    """Demonstrate comparing different pattern implementations."""
    print("\n" + "=" * 70)
    print("Pattern Comparison Demo")
    print("=" * 70)

    specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"
    loader = YAMLBenchmarkLoader(specs_dir)

    # Load multiple pattern benchmarks
    patterns_to_test = ["reflection", "sequential", "parallel"]
    results_comparison = []

    print("\n✓ Comparing patterns:\n")

    for pattern_name in patterns_to_test:
        try:
            benchmark = loader.load_pattern_benchmark(pattern_name)
            test_cases = await benchmark.generate_test_cases()

            results_comparison.append(
                {
                    "pattern": pattern_name,
                    "test_cases": len(test_cases),
                    "description": benchmark.description[:60] + "...",
                }
            )

            print(f"  {pattern_name}:")
            print(f"    Test cases: {len(test_cases)}")
            print(f"    Description: {benchmark.description[:60]}...")

        except FileNotFoundError:
            print(f"  {pattern_name}: Spec not found")

    print("\n✓ Pattern comparison complete")

    return results_comparison


async def main():
    """Run all pattern benchmark demos."""
    print("\n" + "=" * 70)
    print("PATTERN BENCHMARKS DEMONSTRATION")
    print("=" * 70)
    print("\nThis demo shows how to use the pattern benchmark suite")
    print("to evaluate agent patterns using YAML test specifications.\n")

    # Demo 1: Loading benchmarks
    loader = await demo_loading_benchmarks()

    # Demo 2: Running single benchmark
    await demo_running_single_benchmark()

    # Demo 3: Using benchmark suite
    suite = await demo_benchmark_suite()

    # Demo 4: Comparing patterns
    await demo_comparing_patterns()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. YAMLBenchmarkLoader converts YAML specs to executable benchmarks")
    print("  2. PatternBenchmark provides standardized test cases per pattern")
    print("  3. PatternBenchmarkSuite manages multiple pattern benchmarks")
    print("  4. Validators are auto-generated from expected output specs")
    print("  5. Results include timing, pass/fail, and detailed metrics")
    print("\nNext Steps:")
    print("  - Implement real agent patterns (not mocks)")
    print("  - Run full benchmark suite on production agents")
    print("  - Compare performance across different configurations")
    print("  - Use results for regression testing and optimization")


if __name__ == "__main__":
    asyncio.run(main())
