#!/usr/bin/env python3
"""Check for parity regressions.

This script validates that feature parity hasn't regressed below minimum thresholds.
Used in CI to prevent feature drift.
"""

import json
import sys
from pathlib import Path
from typing import Any


# Minimum feature counts per language (prevents regression)
MIN_FEATURE_COUNTS = {
    "python": 43,  # Baseline (100%)
    "go": 43,  # 100% parity
    "typescript": 35,  # ~81% minimum
    "rust": 35,  # ~81% minimum
    "cpp": 35,  # ~81% minimum
    "zig": 25,  # ~58% minimum
}

# Critical features that must exist in all languages (base names, case-insensitive)
# These are checked as substring matches to handle naming variations across languages
# (e.g., TimeoutDecorator vs TimeoutMiddleware, ReActAgent vs ReactAgent)
CRITICAL_FEATURES = {
    "patterns": ["autonomous", "conversational", "react"],  # Lowercase for matching
    "middleware": ["timeout", "retry"],  # Lowercase for matching
}


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
                found = any(
                    feature_base in feat.lower() for feat in category_features
                )

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
        for lang, count in summary.items():
            min_count = MIN_FEATURE_COUNTS.get(lang, 0)
            pct = (count / MIN_FEATURE_COUNTS["python"]) * 100
            print(f"  - {lang.title()}: {count} features ({pct:.1f}% parity)")
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
        return check_no_regressions()
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
