#!/usr/bin/env python3
"""Generate enhanced parity dashboard with visualizations.

This script reads the test-parity-report.json and generates:
1. Category heatmap showing parity status across languages
2. Progress bars for each language vs target
3. Trend data for historical tracking

Part of v0.48.0 Phase 2: Parity Enforcement (Task 2.3)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Parity thresholds (from test_parity_validation.py)
TOTAL_PARITY_THRESHOLDS = {
    "go": 50.0,
    "cpp": 40.0,
    "rust": 15.0,
    "typescript": 18.0,
    "zig": 13.0,
}

# Color thresholds for status
COLOR_EXCELLENT = 80.0  # ✅ Green
COLOR_GOOD = 60.0  # 🟢 Light green
COLOR_FAIR = 40.0  # 🟡 Yellow
COLOR_POOR = 20.0  # 🟠 Orange
# Below 20% = 🔴 Red


def get_status_emoji(parity: float, threshold: float) -> str:
    """Get status emoji based on parity percentage."""
    if parity >= COLOR_EXCELLENT:
        return "✅"
    elif parity >= COLOR_GOOD:
        return "🟢"
    elif parity >= COLOR_FAIR:
        return "🟡"
    elif parity >= COLOR_POOR:
        return "🟠"
    else:
        return "🔴"


def get_threshold_status(parity: float, threshold: float) -> str:
    """Get threshold status (pass/fail)."""
    if parity >= threshold:
        return "✅ PASS"
    else:
        return "❌ FAIL"


def generate_progress_bar(parity: float, threshold: float, width: int = 40) -> str:
    """Generate ASCII progress bar for parity."""
    filled = int((parity / 100.0) * width)
    threshold_pos = int((threshold / 100.0) * width)

    bar = ""
    for i in range(width):
        if i < filled:
            bar += "█"
        elif i == threshold_pos:
            bar += "│"  # Threshold marker
        else:
            bar += "░"

    return f"[{bar}] {parity:.1f}%"


def generate_category_heatmap_ascii(
    report: dict[str, Any], python_total: int
) -> str:
    """Generate ASCII heatmap of category parity."""
    categories = ["patterns", "techniques", "safety", "adapters", "evaluation", "middleware", "memory", "budget"]
    languages = ["go", "cpp", "rust", "typescript", "zig"]

    # Calculate parity for each cell
    heatmap_data: dict[str, dict[str, float | None]] = {}

    python_categories = report["languages"]["python"]["categories"]

    for lang in languages:
        heatmap_data[lang] = {}
        lang_data = report["languages"].get(lang)

        if not lang_data:
            # Language not in report yet
            for cat in categories:
                heatmap_data[lang][cat] = None
            continue

        lang_categories = lang_data.get("categories", {})

        for cat in categories:
            python_cat_count = python_categories.get(cat, 0)
            lang_cat_count = lang_categories.get(cat, 0)

            if python_cat_count == 0:
                heatmap_data[lang][cat] = None
            else:
                parity = (lang_cat_count / python_cat_count) * 100
                heatmap_data[lang][cat] = parity

    # Generate ASCII table
    output = []
    output.append("\n### Category Parity Heatmap\n")
    output.append(
        "Status: 🟢 Excellent (≥80%) | 🟡 Good (60-80%) | 🟠 Fair (40-60%) | 🔴 Poor (<40%) | — N/A\n"
    )

    # Header
    header = f"| {'Language':<12} |"
    separator = "|" + "-" * 14 + "|"

    for cat in categories:
        header += f" {cat[:8]:<8} |"
        separator += "-" * 10 + "|"

    output.append(header)
    output.append(separator)

    # Rows
    for lang in languages:
        row = f"| {lang.upper():<12} |"

        for cat in categories:
            parity = heatmap_data[lang].get(cat)

            if parity is None:
                cell = "—"
            elif parity >= COLOR_EXCELLENT:
                cell = "🟢"
            elif parity >= COLOR_GOOD:
                cell = "🟡"
            elif parity >= COLOR_FAIR:
                cell = "🟠"
            else:
                cell = "🔴"

            row += f" {cell:^8} |"

        output.append(row)

    output.append("")
    return "\n".join(output)


def generate_progress_section(report: dict[str, Any], python_total: int) -> str:
    """Generate progress bars section."""
    output = []
    output.append("\n### Parity Progress vs Thresholds\n")
    output.append(
        "Progress bars show current parity (█) vs minimum threshold (│):\n"
    )

    for lang in ["go", "cpp", "rust", "typescript", "zig"]:
        lang_data = report["languages"].get(lang)

        if not lang_data:
            output.append(f"\n**{lang.upper()}**: Not in report yet")
            continue

        total = lang_data["total"]
        parity = (total / python_total) * 100
        threshold = TOTAL_PARITY_THRESHOLDS.get(lang, 0)

        status = get_threshold_status(parity, threshold)
        emoji = get_status_emoji(parity, threshold)

        output.append(f"\n**{lang.upper()}** {emoji} {status}")
        output.append(f"```")
        output.append(generate_progress_bar(parity, threshold))
        output.append(
            f"Tests: {total}/{python_total} | Threshold: {threshold:.1f}% | Gap to 100%: {100 - parity:.1f}%"
        )
        output.append(f"```")

    return "\n".join(output)


def generate_summary_table(report: dict[str, Any], python_total: int) -> str:
    """Generate summary table with current parity."""
    output = []
    output.append("\n### Current Test Parity Summary\n")
    output.append(
        f"**Generated**: {report['generated_at']} | **Python Baseline**: {python_total} tests\n"
    )

    output.append("| Language | Tests | Parity | Threshold | Status | Gap to Threshold |")
    output.append("|----------|-------|--------|-----------|--------|------------------|")

    # Python (reference)
    output.append(
        f"| Python | {python_total} | 100.0% | baseline | ✅ | — |"
    )

    # Other languages
    for lang in ["go", "cpp", "rust", "typescript", "zig"]:
        lang_data = report["languages"].get(lang)

        if not lang_data:
            output.append(
                f"| {lang.upper()} | N/A | N/A | N/A | ⏸️ | N/A |"
            )
            continue

        total = lang_data["total"]
        parity = (total / python_total) * 100
        threshold = TOTAL_PARITY_THRESHOLDS.get(lang, 0)

        emoji = get_status_emoji(parity, threshold)
        threshold_status = get_threshold_status(parity, threshold)

        gap_to_threshold = parity - threshold
        gap_str = f"+{gap_to_threshold:.1f}%" if gap_to_threshold >= 0 else f"{gap_to_threshold:.1f}%"

        output.append(
            f"| {lang.upper()} | {total} | {parity:.1f}% | {threshold:.1f}% | {emoji} {threshold_status} | {gap_str} |"
        )

    return "\n".join(output)


def generate_category_details(report: dict[str, Any]) -> str:
    """Generate detailed category breakdown."""
    output = []
    output.append("\n### Category Breakdown\n")

    python_categories = report["languages"]["python"]["categories"]
    categories = sorted(python_categories.keys())

    for cat in categories:
        python_count = python_categories[cat]

        output.append(f"\n#### {cat.title()}\n")
        output.append(
            f"**Python baseline**: {python_count} tests\n"
        )

        output.append("| Language | Tests | Parity | Status |")
        output.append("|----------|-------|--------|--------|")

        for lang in ["go", "cpp", "rust", "typescript", "zig"]:
            lang_data = report["languages"].get(lang)

            if not lang_data:
                output.append(f"| {lang.upper()} | N/A | N/A | ⏸️ |")
                continue

            lang_count = lang_data.get("categories", {}).get(cat, 0)

            if python_count == 0:
                parity_str = "N/A"
                status = "—"
            else:
                parity = (lang_count / python_count) * 100
                parity_str = f"{parity:.1f}%"

                if parity >= COLOR_EXCELLENT:
                    status = "✅"
                elif parity >= COLOR_GOOD:
                    status = "🟢"
                elif parity >= COLOR_FAIR:
                    status = "🟡"
                elif parity >= COLOR_POOR:
                    status = "🟠"
                else:
                    status = "🔴"

            output.append(
                f"| {lang.upper()} | {lang_count} | {parity_str} | {status} |"
            )

    return "\n".join(output)


def save_historical_data(report: dict[str, Any], history_file: Path) -> None:
    """Append current parity data to historical tracking file."""
    # Load existing history
    history = []
    if history_file.exists():
        with history_file.open() as f:
            history = json.load(f)

    # Create entry for today
    entry = {
        "date": report["generated_at"],
        "languages": {},
    }

    python_total = report["languages"]["python"]["total"]

    for lang in ["python", "go", "cpp", "rust", "typescript", "zig"]:
        lang_data = report["languages"].get(lang)
        if lang_data:
            if lang == "python":
                entry["languages"][lang] = {
                    "total": lang_data["total"],
                    "parity": 100.0,
                }
            else:
                total = lang_data["total"]
                parity = (total / python_total) * 100
                entry["languages"][lang] = {
                    "total": total,
                    "parity": parity,
                }

    # Append to history (keep last 90 days)
    history.append(entry)

    # Keep only last 90 entries
    if len(history) > 90:
        history = history[-90:]

    # Save
    with history_file.open("w") as f:
        json.dump(history, f, indent=2)


def generate_enhanced_dashboard(
    report_file: Path, output_file: Path, history_file: Path
) -> None:
    """Generate enhanced parity dashboard."""
    # Load report
    with report_file.open() as f:
        report = json.load(f)

    python_total = report["languages"]["python"]["total"]

    # Generate sections
    sections = []

    sections.append("# Test Parity Dashboard\n")
    sections.append(
        "> Automated test parity tracking across all 6 Agenkit language implementations\n"
    )

    # Summary table
    sections.append(generate_summary_table(report, python_total))

    # Progress bars
    sections.append(generate_progress_section(report, python_total))

    # Category heatmap
    sections.append(generate_category_heatmap_ascii(report, python_total))

    # Category details
    sections.append(generate_category_details(report))

    # Footer
    sections.append("\n---\n")
    sections.append(
        "\n**Documentation**: [README-test-parity.md](../README-test-parity.md)"
    )
    sections.append("\n**Raw Data**: [test-parity-report.json](../test-parity-report.json)")
    sections.append(
        "\n**Validation Tests**: [tests/test_parity_validation.py](../tests/test_parity_validation.py)\n"
    )
    sections.append(
        f"\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
    )

    # Write dashboard
    with output_file.open("w") as f:
        f.write("\n".join(sections))

    print(f"✅ Generated enhanced dashboard: {output_file}")

    # Save historical data
    save_historical_data(report, history_file)
    print(f"✅ Updated historical data: {history_file}")


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    report_file = project_root / "test-parity-report.json"
    output_file = project_root / "docs" / "TEST_PARITY.md"
    history_file = project_root / "test-parity-history.json"

    if not report_file.exists():
        print(f"❌ Parity report not found: {report_file}", file=sys.stderr)
        print("Run ./scripts/test-parity.sh first to generate the report.", file=sys.stderr)
        return 1

    try:
        generate_enhanced_dashboard(report_file, output_file, history_file)
        print("\n✅ Dashboard generation complete!")
        return 0
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
