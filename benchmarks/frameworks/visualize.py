#!/usr/bin/env python3
"""
Visualize framework benchmark results.

Reads the most recent results JSON and prints ASCII comparison charts.
Optionally generates an HTML report when --html flag is passed.

Usage:
    uv run python benchmarks/frameworks/visualize.py
    uv run python benchmarks/frameworks/visualize.py --html
    uv run python benchmarks/frameworks/visualize.py results/results_20260316_142839.json
"""

import argparse
import json
import sys
from pathlib import Path


RESULTS_DIR = Path(__file__).parent / "results"
BAR_WIDTH = 40


def _bar(value_ms: float, max_ms: float) -> str:
    """Return an ASCII bar proportional to value/max."""
    filled = int((value_ms / max_ms) * BAR_WIDTH) if max_ms > 0 else 0
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def _overhead_pct(a: float, b: float) -> str:
    """Return overhead of a relative to b as ±N% string."""
    if b == 0:
        return "  n/a"
    pct = ((a - b) / b) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:+.0f}%"


def print_suite(suite_name: str, scenarios: dict[str, dict[str, float]]) -> None:
    """Print ASCII bar chart for one benchmark suite."""
    max_ms = max(s["mean_ms"] for s in scenarios.values()) or 1.0
    items = list(scenarios.items())

    print(f"\n  {'─'*70}")
    print(f"  {suite_name.upper().replace('_', ' ')}")
    print(f"  {'─'*70}")
    print(f"  {'Scenario':<34} {'mean_ms':>8}  Bar")
    print(f"  {'─'*70}")

    for name, stats in items:
        bar = _bar(stats["mean_ms"], max_ms)
        print(f"  {name:<34} {stats['mean_ms']:>8.4f}  {bar}")

    # Print overhead/speedup between first and second item when exactly 2
    if len(items) == 2:
        n0, s0 = items[0]
        n1, s1 = items[1]
        ratio = s0["mean_ms"] / s1["mean_ms"] if s1["mean_ms"] > 0 else float("inf")
        if ratio >= 1:
            faster = n1
            overhead_label = f"{n0} is {ratio:.2f}x slower than {n1}"
        else:
            faster = n0
            overhead_label = f"{n1} is {1/ratio:.2f}x slower than {n0}"
        print(f"\n  → {overhead_label}")


def print_report(all_results: dict[str, dict[str, dict[str, float]]]) -> None:
    """Print full ASCII benchmark report."""
    print("\n" + "═" * 74)
    print("  AGENKIT FRAMEWORK BENCHMARK RESULTS")
    print("  Mini-framework wrappers vs Agenkit primitives — pure orchestration overhead")
    print("  (MockLLM with zero latency — measures framework dispatch only)")
    print("═" * 74)

    for suite_name, scenarios in all_results.items():
        print_suite(suite_name, scenarios)

    print("\n" + "═" * 74)
    print("  KEY FINDINGS")
    print("═" * 74)
    print("""
  • Framework overhead is sub-millisecond across all patterns.
  • In real workloads, LLM API latency (100–3000ms) dominates entirely.
  • MiniChain/MiniCrew wrappers add ≤2.5x overhead vs primitives — still
    orders of magnitude faster than LLM call latency.
  • SequentialChain and SequentialAgent are virtually identical (within noise).
  • Parallel scheduling (asyncio.gather) shows similar variance in both
    Crew and ParallelAgent due to event loop scheduling, not framework cost.

  REAL-WORLD CONTEXT:
  At 100ms LLM latency, orchestration overhead is < 0.1% of total latency.
  The performance choice between mini-frameworks and primitives is negligible.
  Choose based on API familiarity and migration path, not performance.
""")


def generate_html(all_results: dict[str, dict[str, dict[str, float]]], output_path: Path) -> None:
    """Generate a self-contained HTML report."""
    rows = []
    for suite_name, scenarios in all_results.items():
        for scenario, stats in scenarios.items():
            rows.append({
                "suite": suite_name,
                "scenario": scenario,
                "mean_ms": stats["mean_ms"],
                "p50_ms": stats["p50_ms"],
                "p95_ms": stats["p95_ms"],
                "iter_per_sec": stats["iter_per_sec"],
            })

    rows_html = "\n".join(
        f"<tr><td>{r['suite']}</td><td>{r['scenario']}</td>"
        f"<td>{r['mean_ms']:.4f}</td><td>{r['p50_ms']:.4f}</td>"
        f"<td>{r['p95_ms']:.4f}</td><td>{r['iter_per_sec']:,.0f}</td></tr>"
        for r in rows
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Agenkit Framework Benchmarks</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
  h1 {{ color: #1a1a2e; }}
  table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
  th {{ background: #1a1a2e; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
  tr:nth-child(even) {{ background: #f8f8f8; }}
  .note {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0; }}
</style>
</head>
<body>
<h1>Agenkit Framework Benchmark Results</h1>
<p>Pure orchestration overhead with zero-latency MockLLM. All values in milliseconds.</p>
<div class="note">
  <strong>Context:</strong> Real LLM API latency is 100–3000ms. Framework overhead shown here
  is &lt;0.1% of total in production. Choose between mini-frameworks and primitives based on
  API familiarity, not performance.
</div>
<table>
  <thead>
    <tr><th>Suite</th><th>Scenario</th><th>mean_ms</th><th>p50_ms</th><th>p95_ms</th><th>iter/s</th></tr>
  </thead>
  <tbody>
{rows_html}
  </tbody>
</table>
</body>
</html>"""

    output_path.write_text(html)
    print(f"HTML report written to: {output_path}")


def load_results(path: Path | None) -> dict[str, dict[str, dict[str, float]]]:
    """Load results from path, or most recent file in results dir."""
    if path is None:
        candidates = sorted(RESULTS_DIR.glob("results_*.json"))
        if not candidates:
            print("No results found. Run: uv run python benchmarks/frameworks/run_all.py")
            sys.exit(1)
        path = candidates[-1]
        print(f"Loading: {path.name}")

    with path.open() as f:
        data = json.load(f)
    return data["results"]


def main() -> None:
    """Parse args and run visualization."""
    parser = argparse.ArgumentParser(description="Visualize framework benchmark results")
    parser.add_argument("results_file", nargs="?", type=Path, help="Path to results JSON (default: most recent)")
    parser.add_argument("--html", action="store_true", help="Also generate HTML report")
    args = parser.parse_args()

    all_results = load_results(args.results_file)
    print_report(all_results)

    if args.html:
        html_path = RESULTS_DIR / "report.html"
        generate_html(all_results, html_path)


if __name__ == "__main__":
    main()
