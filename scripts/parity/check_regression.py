#!/usr/bin/env python3
"""Check for parity regressions.

This script validates that feature parity hasn't regressed below minimum thresholds.
Used in CI to prevent feature drift.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Minimum feature counts per language (prevents regression).
#
# Floors sit just below the counts measured after the scanner was fixed in #753.
# The previous floors were calibrated against a manifest that reported 0
# techniques for every language and 0 LLM adapters for Zig, so they were both
# too low to catch a real regression and expressed as a percentage of a
# hardcoded 43 -- which made Python, the reference implementation, report
# "125.6% parity".
#
# Measured 2026-08: python 54, go 51, cpp 47, rust 46, typescript 44, zig 44,
# csharp/java/scala 29 each.
MIN_FEATURE_COUNTS = {
    "python": 50,  # Reference implementation (54 measured)
    "go": 48,  # 51 measured
    "cpp": 44,  # 47 measured
    "rust": 43,  # 46 measured
    "typescript": 41,  # 44 measured
    "zig": 41,  # 44 measured
    # C#/Java/Scala had no floor at all until now, despite being full-parity
    # implementations since v0.71.0-v0.73.0. They trail on llm_adapters (3 vs 7)
    # and have no techniques subsystem -- see #754.
    "csharp": 27,  # 29 measured
    "java": 27,  # 29 measured
    "scala": 27,  # 29 measured
}

# Reference language that other counts are expressed relative to.
REFERENCE_LANGUAGE = "python"

# Critical features that must exist in all languages (base names, case-insensitive)
# These are checked as substring matches to handle naming variations across languages
# (e.g., TimeoutDecorator vs TimeoutMiddleware, ReActAgent vs ReactAgent)
CRITICAL_FEATURES = {
    "patterns": ["autonomous", "conversational", "react"],  # Lowercase for matching
    "middleware": ["timeout", "retry"],  # Lowercase for matching
}


def render_markdown_table(manifest: dict[str, Any]) -> str:
    """Render the parity summary as a Markdown table.

    Lives here rather than inline in the workflow so the language list and the
    pass/fail thresholds have a single source of truth. The workflow's inline
    version hardcoded six languages and the pre-#753 thresholds, so it silently
    omitted C#/Java/Scala and marked Zig ⚠️ against a stale floor.

    Args:
        manifest: Feature manifest

    Returns:
        Markdown table as a string
    """
    summary = manifest.get("summary", {}).get("total", {})
    reference_count = summary.get(REFERENCE_LANGUAGE, 0)

    lines = [
        "| Language | Features | Parity % | Floor | Status |",
        "|----------|----------|----------|-------|--------|",
    ]

    for lang, floor in MIN_FEATURE_COUNTS.items():
        count = summary.get(lang, 0)
        pct = (count / reference_count * 100) if reference_count else 0.0
        if lang == REFERENCE_LANGUAGE:
            status = "✅ Baseline"
        else:
            status = "✅" if count >= floor else "⚠️"
        lines.append(f"| {lang.title()} | {count} | {pct:.1f}% | {floor} | {status} |")

    return "\n".join(lines)


def load_manifest() -> dict[str, Any]:
    """Load feature manifest.

    Returns:
        Feature manifest dictionary
    """
    manifest_path = Path("feature-manifest.json")
    if not manifest_path.exists():
        print("❌ Error: feature-manifest.json not found")
        print("   Run: python scripts/parity/feature_scanner.py")
        sys.exit(1)

    return json.loads(manifest_path.read_text())


def check_feature_counts(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check that feature counts meet minimums.

    Args:
        manifest: Feature manifest

    Returns:
        Tuple of (passed, errors)
    """
    errors = []
    summary = manifest.get("summary", {}).get("total", {})

    for lang, min_count in MIN_FEATURE_COUNTS.items():
        actual_count = summary.get(lang, 0)

        if actual_count < min_count:
            errors.append(
                f"❌ {lang.title()}: {actual_count} features "
                f"(minimum: {min_count}) - REGRESSION DETECTED"
            )

    return len(errors) == 0, errors


def check_critical_features(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check that critical features exist in all languages.

    Uses case-insensitive substring matching to handle naming variations
    across languages (e.g., TimeoutDecorator vs TimeoutMiddleware).

    Args:
        manifest: Feature manifest

    Returns:
        Tuple of (passed, errors)
    """
    errors = []
    languages = manifest.get("languages", {})

    for category, features in CRITICAL_FEATURES.items():
        for feature_base in features:
            for lang_name, lang_data in languages.items():
                if lang_name == "python":
                    continue  # Python is baseline

                category_features = lang_data.get(category, [])
                # Check if any feature contains the base name (case-insensitive)
                found = any(feature_base in feat.lower() for feat in category_features)

                if not found:
                    errors.append(
                        f"❌ {lang_name.title()}: Missing critical feature "
                        f"containing '{feature_base}' in {category}"
                    )

    return len(errors) == 0, errors


def check_no_regressions() -> int:
    """Run all regression checks.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    print("=" * 70)
    print("Parity Regression Checker")
    print("=" * 70)
    print()

    # Load manifest
    print("Loading feature manifest...")
    manifest = load_manifest()
    print(f"✓ Loaded manifest (generated: {manifest['generated_at']})")
    print()

    # Check feature counts
    print("Checking feature counts...")
    counts_ok, count_errors = check_feature_counts(manifest)

    if counts_ok:
        print("✓ All languages meet minimum feature counts")
        # Print actual counts
        summary = manifest.get("summary", {}).get("total", {})
        # Parity is relative to the reference language's *measured* count, not to
        # a hardcoded floor -- dividing by the floor previously reported Python
        # itself at 125.6% parity with itself.
        reference_count = summary.get(REFERENCE_LANGUAGE, 0)
        for lang, count in summary.items():
            pct = (count / reference_count * 100) if reference_count else 0.0
            print(f"  - {lang.title()}: {count} features ({pct:.1f}% of {REFERENCE_LANGUAGE})")
    else:
        for error in count_errors:
            print(error)
    print()

    # Check critical features
    print("Checking critical features...")
    critical_ok, critical_errors = check_critical_features(manifest)

    if critical_ok:
        print("✓ All critical features present")
        print(f"  - {len(CRITICAL_FEATURES['patterns'])} critical patterns")
        print(f"  - {len(CRITICAL_FEATURES['middleware'])} critical middleware")
    else:
        for error in critical_errors:
            print(error)
    print()

    # Summary
    print("=" * 70)
    if counts_ok and critical_ok:
        print("✅ All parity checks passed - No regressions detected")
        print("=" * 70)
        return 0
    else:
        print("❌ Parity validation failed - Please fix regressions")
        print("=" * 70)
        return 1


def main() -> int:
    """Main entry point.

    Returns:
        Exit code
    """
    try:
        if "--markdown" in sys.argv:
            # Emit only the table, for the CI PR comment. Still exits non-zero on
            # a regression so a table can never be posted for a failing scan.
            manifest = load_manifest()
            print(render_markdown_table(manifest))
            counts_ok, _ = check_feature_counts(manifest)
            critical_ok, _ = check_critical_features(manifest)
            return 0 if counts_ok and critical_ok else 1

        return check_no_regressions()
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
