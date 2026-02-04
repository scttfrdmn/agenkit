"""Main feature scanner orchestrator.

Coordinates all language-specific scanners to generate a comprehensive
feature manifest showing what's implemented across all 6 languages.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def scan_all_languages() -> dict[str, Any]:
    """Scan all 6 languages and generate feature manifest.

    Returns:
        Complete feature manifest with detected features per language.
    """
    print("=" * 70)
    print("Agenkit Feature Parity Scanner")
    print("=" * 70)
    print()

    results: dict[str, Any] = {}
    languages = ["python", "go", "typescript", "rust", "cpp", "zig"]

    for lang in languages:
        print(f"Scanning {lang}...", end=" ", flush=True)

        try:
            scanner = load_scanner(lang)
            results[lang] = scanner.scan()
            print(f"✓ ({count_features(results[lang])} features)")

        except Exception as e:
            print(f"✗ (error: {e})")
            # Provide empty results for failed scans
            results[lang] = {
                "patterns": [],
                "middleware": [],
                "llm_adapters": [],
                "memory": [],
                "techniques": [],
                "error": str(e),
            }

    print()

    # Build complete manifest
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "languages": results,
        "summary": calculate_summary(results),
    }

    return manifest


def load_scanner(language: str):
    """Load language-specific scanner module.

    Args:
        language: Language name (python, go, typescript, rust, cpp, zig)

    Returns:
        Scanner module with scan() function

    Raises:
        ImportError: If scanner module not found
    """
    if language == "python":
        from scripts.parity.scanners import python_scanner

        return python_scanner
    elif language == "go":
        from scripts.parity.scanners import go_scanner

        return go_scanner
    elif language == "typescript":
        from scripts.parity.scanners import typescript_scanner

        return typescript_scanner
    elif language == "rust":
        from scripts.parity.scanners import rust_scanner

        return rust_scanner
    elif language == "cpp":
        from scripts.parity.scanners import cpp_scanner

        return cpp_scanner
    elif language == "zig":
        from scripts.parity.scanners import zig_scanner

        return zig_scanner
    else:
        raise ValueError(f"Unknown language: {language}")


def count_features(features: dict[str, Any]) -> int:
    """Count total features in a language's results.

    Args:
        features: Feature dict with lists of detected features

    Returns:
        Total count of features
    """
    count = 0
    for category in ["patterns", "middleware", "llm_adapters", "memory", "techniques"]:
        if category in features and isinstance(features[category], list):
            count += len(features[category])
    return count


def calculate_summary(results: dict[str, Any]) -> dict[str, Any]:
    """Calculate summary statistics across all languages.

    Args:
        results: Language results dict

    Returns:
        Summary dict with counts per category per language
    """
    summary: dict[str, dict[str, int]] = {
        "patterns": {},
        "middleware": {},
        "llm_adapters": {},
        "memory": {},
        "techniques": {},
        "total": {},
    }

    for lang, features in results.items():
        if "error" in features:
            continue

        for category in ["patterns", "middleware", "llm_adapters", "memory", "techniques"]:
            count = len(features.get(category, []))
            summary[category][lang] = count

        # Total count
        summary["total"][lang] = count_features(features)

    return summary


def write_manifest(manifest: dict[str, Any], output_file: Path) -> None:
    """Write feature manifest to JSON file.

    Args:
        manifest: Feature manifest data
        output_file: Path to output JSON file
    """
    with output_file.open("w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Manifest written to: {output_file}")
    print()


def print_summary(manifest: dict[str, Any]) -> None:
    """Print summary statistics to console.

    Args:
        manifest: Feature manifest with summary section
    """
    summary = manifest["summary"]

    print("Summary by Category:")
    print("-" * 70)

    categories = ["patterns", "middleware", "llm_adapters", "memory", "techniques"]
    languages = ["python", "go", "typescript", "rust", "cpp", "zig"]

    # Header
    print(f"{'Category':<20} " + " ".join(f"{lang:>8}" for lang in languages))
    print("-" * 70)

    # Rows
    for category in categories:
        counts = summary.get(category, {})
        row = f"{category:<20} "
        row += " ".join(f"{counts.get(lang, 0):>8}" for lang in languages)
        print(row)

    # Total row
    print("-" * 70)
    total_counts = summary.get("total", {})
    total_row = f"{'TOTAL':<20} "
    total_row += " ".join(f"{total_counts.get(lang, 0):>8}" for lang in languages)
    print(total_row)
    print()


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        # Scan all languages
        manifest = scan_all_languages()

        # Write manifest to JSON
        output_file = Path("feature-manifest.json")
        write_manifest(manifest, output_file)

        # Print summary
        print_summary(manifest)

        print("=" * 70)
        print("✓ Feature scanning complete!")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
