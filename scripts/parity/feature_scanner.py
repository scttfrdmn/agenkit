"""Main feature scanner orchestrator.

Coordinates all language-specific scanners to generate a comprehensive
feature manifest showing what's implemented across all 9 languages.
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Categories a language genuinely does not implement, so a missing directory is
# expected rather than a stale path. Anything NOT listed here whose configured
# path is absent is a scanner bug and fails validation.
#
# C#/Java/Scala have no techniques subsystem: only ReActAgent exists, filed under
# patterns/. Tracked in #754 -- remove entries here as they are implemented.
KNOWN_MISSING: dict[str, set[str]] = {
    "csharp": {"techniques"},
    "java": {"techniques"},
    "scala": {"techniques"},
}


def validate_scan_paths() -> list[str]:
    """Verify every directory the scanners are configured to read exists.

    A scanner that globs a path which has since moved returns an empty list,
    which is indistinguishable from "this language implements nothing". That is
    how the manifest came to report 0 LLM adapters for Zig while 7 were
    implemented, and 0 techniques for all nine languages while Python has 33.
    Checking up front turns a silent understatement into a loud failure.

    Returns:
        List of human-readable errors; empty when every path resolves.
    """
    errors: list[str] = []
    scanners_dir = Path(__file__).parent / "scanners"
    languages = ["python", "go", "typescript", "rust", "cpp", "zig", "csharp", "java", "scala"]

    for lang in languages:
        source = (scanners_dir / f"{lang}_scanner.py").read_text()

        root_match = re.search(r'root\s*=\s*Path\("([^"]+)"\)', source)
        if root_match is None:
            errors.append(f"{lang}: could not determine scan root")
            continue
        root = Path(root_match.group(1))

        if not root.exists():
            errors.append(f"{lang}: scan root does not exist: {root}")
            continue

        # Each category resolves `<category>_dir = root / "a" / "b"`, or
        # `<category>_file = root / "a.ext"` for a language whose category
        # lives in a single file rather than a directory (Zig's composition.zig).
        for category, path_expr in re.findall(
            r'(\w+)_(?:dir|file)\s*=\s*root((?:\s*/\s*"[^"]+")+)', source
        ):
            parts = re.findall(r'"([^"]+)"', path_expr)
            resolved = root.joinpath(*parts)
            if resolved.exists():
                continue
            if category in KNOWN_MISSING.get(lang, set()):
                continue  # Declared gap, not a stale path.
            errors.append(
                f"{lang}/{category}: configured path does not exist: {resolved} "
                f"(a missing path silently reports 0 features)"
            )

    return errors


def scan_all_languages() -> dict[str, Any]:
    """Scan all 9 languages and generate feature manifest.

    Returns:
        Complete feature manifest with detected features per language.
    """
    print("=" * 70)
    print("Agenkit Feature Parity Scanner")
    print("=" * 70)
    print()

    path_errors = validate_scan_paths()
    if path_errors:
        print("✗ Scan path validation failed:")
        for error in path_errors:
            print(f"   - {error}")
        print()
        raise RuntimeError(
            f"{len(path_errors)} configured scan path(s) do not exist; "
            f"fix the scanner or declare the gap in KNOWN_MISSING"
        )
    print("✓ All scan paths resolve")
    print()

    results: dict[str, Any] = {}
    languages = ["python", "go", "typescript", "rust", "cpp", "zig", "csharp", "java", "scala"]

    for lang in languages:
        print(f"Scanning {lang}...", end=" ", flush=True)

        try:
            scanner = load_scanner(lang)
            results[lang] = scanner.scan()
            print(f"✓ ({count_features(results[lang])} features)")

        except Exception as e:
            # A scan failure degrades to zeros, which reads identically to "this
            # language implements nothing" once the manifest is published. Record
            # the error and re-raise rather than shipping a manifest that
            # understates parity -- see validate_scan_paths.
            print(f"✗ (error: {e})")
            results[lang] = {
                "patterns": [],
                "middleware": [],
                "llm_adapters": [],
                "memory": [],
                "techniques": [],
                "error": str(e),
            }
            raise

    print()

    # Build complete manifest
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "1.0",
        "languages": results,
        "summary": calculate_summary(results),
    }

    return manifest


def load_scanner(language: str):
    """Load language-specific scanner module.

    Args:
        language: Language name (python, go, typescript, rust, cpp, zig,
            csharp, java, scala)

    Returns:
        Scanner module with scan() function

    Raises:
        ImportError: If scanner module not found
    """
    # Each language maps to a `<name>_scanner` module exposing scan().
    known = {
        "python",
        "go",
        "typescript",
        "rust",
        "cpp",
        "zig",
        "csharp",
        "java",
        "scala",
    }
    if language not in known:
        raise ValueError(f"Unknown language: {language}")

    import importlib

    return importlib.import_module(f"scripts.parity.scanners.{language}_scanner")


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
    languages = ["python", "go", "typescript", "rust", "cpp", "zig", "csharp", "java", "scala"]

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
