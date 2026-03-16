"""
Run all framework benchmarks and save results.

Usage: uv run python benchmarks/frameworks/run_all.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from benchmarks.frameworks.bench_conversational import bench as bench_conversational
from benchmarks.frameworks.bench_parallel import bench as bench_parallel
from benchmarks.frameworks.bench_router import bench as bench_router
from benchmarks.frameworks.bench_sequential import bench as bench_sequential
from benchmarks.frameworks.bench_simple_chain import bench as bench_simple_chain

RESULTS_DIR = Path(__file__).parent / "results"


def print_table(all_results: dict[str, dict[str, dict[str, float]]]) -> None:
    """Print formatted benchmark table."""
    print("\n" + "=" * 80)
    print("  Framework Benchmark Results")
    print("=" * 80)
    print(f"{'Suite':<20} {'Scenario':<32} {'mean_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'iter/s':>10}")
    print("-" * 80)

    for suite_name, scenarios in all_results.items():
        for scenario, stats in scenarios.items():
            print(
                f"{suite_name:<20} {scenario:<32} "
                f"{stats['mean_ms']:>8.4f} {stats['p50_ms']:>8.4f} "
                f"{stats['p95_ms']:>8.4f} {stats['iter_per_sec']:>10.1f}"
            )
        print()


async def main() -> None:
    """Run all benchmarks and save results."""
    print("Running framework benchmarks...")
    print("(100 iterations with 10 warmup per scenario)\n")

    all_results: dict[str, dict[str, dict[str, float]]] = {}

    suites = [
        ("simple_chain", bench_simple_chain),
        ("sequential", bench_sequential),
        ("parallel", bench_parallel),
        ("conversational", bench_conversational),
        ("router", bench_router),
    ]

    for suite_name, bench_fn in suites:
        print(f"  Running {suite_name}...", end="", flush=True)
        results = await bench_fn()
        all_results[suite_name] = results
        print(" done")

    print_table(all_results)

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"results_{timestamp}.json"
    with output_path.open("w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "results": all_results,
            },
            f,
            indent=2,
        )

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
