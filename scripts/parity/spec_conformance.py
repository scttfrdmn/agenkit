#!/usr/bin/env python3
"""Spec-presence conformance: does a source file implementing pattern X
exist per language?

Rung 1 of #909's spec-conformance work (interface/structural conformance
against ``specs/patterns/*.yaml``, per that directory's README). Distinct
from -- and complementary to -- ``feature_scanner.py``, which counts
*classes matching a naming convention*: this asks the actual question
#913 wants answered ("does language X implement pattern Y"), while
``feature_scanner.py``/``feature-manifest.json`` remain a secondary,
diagnostic class-count metric (#913, decision: neither replaces the other
outright; this becomes the public-facing number, feature-manifest.json
stays for class-level detail).

Deliberately NOT a retrofit of feature_scanner.py: that module's unit of
measure (a directory of source files matched by a *Agent-suffix regex) is
the wrong question by design, and refactoring it risks silently breaking
its own validate_scan_paths() guard (which regex-parses each scanner's
literal ``root = Path(...)``/``<cat>_dir = root / "..."`` source shapes).
This module follows the SAME literal-shape convention on purpose, so a
future generalization of that guard can cover both without a rewrite.

Usage::

    scripts/parity/spec_conformance.py            # write spec-conformance.json
    scripts/parity/spec_conformance.py --check    # exit 1 if stale
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = ROOT / "specs" / "patterns"


@dataclass(frozen=True)
class LanguageSource:
    """Where a language's pattern implementations live, and how to find one."""

    name: str
    patterns_dir: Path
    extension: str
    # Composition-pattern classes live outside patterns_dir in a sibling
    # composition/ directory (Zig: a single file) -- see
    # scanners/_paths.py's COMPOSITION_AGENT_NAMES for the identical
    # rationale in feature_scanner.py. Not every language needs this (Zig's
    # composition.zig is handled as a literal extra path below), so it's
    # optional per language.
    composition_dir: Path | None = None


LANGUAGES: dict[str, LanguageSource] = {
    "python": LanguageSource(
        "python", ROOT / "agenkit" / "patterns", ".py", ROOT / "agenkit" / "composition"
    ),
    "go": LanguageSource(
        "go", ROOT / "agenkit-go" / "patterns", ".go", ROOT / "agenkit-go" / "composition"
    ),
    "typescript": LanguageSource(
        "typescript",
        ROOT / "agenkit-ts" / "src" / "patterns",
        ".ts",
        ROOT / "agenkit-ts" / "src" / "composition",
    ),
    "rust": LanguageSource(
        "rust",
        ROOT / "agenkit-rust" / "src" / "patterns",
        ".rs",
        ROOT / "agenkit-rust" / "src" / "composition",
    ),
    "cpp": LanguageSource(
        "cpp",
        ROOT / "agenkit-cpp" / "include" / "agenkit" / "patterns",
        ".hpp",
        ROOT / "agenkit-cpp" / "include" / "agenkit" / "composition",
    ),
    "zig": LanguageSource("zig", ROOT / "agenkit-zig" / "src" / "patterns", ".zig", None),
    "csharp": LanguageSource(
        "csharp",
        ROOT / "agenkit-cs" / "src" / "Agenkit" / "Patterns",
        ".cs",
        ROOT / "agenkit-cs" / "src" / "Agenkit" / "Composition",
    ),
    "java": LanguageSource(
        "java",
        ROOT / "agenkit-java" / "src" / "main" / "java" / "io" / "agenkit" / "patterns",
        ".java",
        ROOT / "agenkit-java" / "src" / "main" / "java" / "io" / "agenkit" / "composition",
    ),
    "scala": LanguageSource(
        "scala",
        ROOT / "agenkit-scala" / "src" / "main" / "scala" / "io" / "agenkit" / "patterns",
        ".scala",
        ROOT / "agenkit-scala" / "src" / "main" / "scala" / "io" / "agenkit" / "composition",
    ),
}

# Zig's composition code is a single file, not a directory (see
# scanners/zig_scanner.py) -- ConditionalAgent does not exist there at all
# (Zig has no ConditionalAgent anywhere), so no extra alias entry is needed
# for it, unlike the other 8 languages.
_ZIG_COMPOSITION_FILE = ROOT / "agenkit-zig" / "src" / "composition.zig"

# spec filename stem -> set of acceptable filename stems across languages
# (all languages here use snake_case or PascalCase filenames, aliased to a
# common lowercase-stripped form below). Aliases exist because naming
# legitimately diverges: Python/Go/Rust/TS/C++/Zig name the file after the
# pattern; C#/Java/Scala name the file after the class
# (AutonomousAgent.cs, not autonomous.cs); "memory_hierarchy" is spelled
# "memory" in the file-per-pattern languages (the class inside is
# MemoryHierarchy) and "MemoryAugmentedAgent" in C#/Java/Scala.
SPEC_ALIASES: dict[str, set[str]] = {
    "agents_as_tools": {"agents_as_tools", "agents-as-tools", "agentsastools", "agenttool"},
    "autonomous": {"autonomous", "autonomousagent"},
    "collaborative": {"collaborative", "collaborativeagent"},
    "conversational": {"conversational", "conversationalagent"},
    "fallback": {"fallback", "fallbackagent"},
    "human_in_loop": {"human_in_loop", "human-in-loop", "humaninloop", "humaninloopagent"},
    "memory_hierarchy": {
        "memory",
        "memory_hierarchy",
        "memoryhierarchy",
        "memoryaugmentedagent",
    },
    "multiagent": {"multiagent", "multiagentorchestrator"},
    "orchestration": {"orchestration", "orchestrationagent"},
    "parallel": {"parallel", "parallelagent"},
    "planning": {"planning", "planningagent"},
    "react": {"react", "reactagent"},
    "reasoning_with_tools": {
        "reasoning_with_tools",
        "reasoning-with-tools",
        "reasoningwithtools",
        "reasoningwithtoolsagent",
    },
    "reflection": {"reflection", "reflectionagent"},
    "router": {"router", "routeragent"},
    "sequential": {"sequential", "sequentialagent"},
    "supervisor": {"supervisor", "supervisoragent"},
    "task": {"task", "taskagent"},
}


def _spec_stems() -> list[str]:
    if not SPECS_DIR.exists():
        raise SystemExit(f"{SPECS_DIR} does not exist -- specs/patterns/ moved or was deleted")
    stems = sorted(p.stem for p in SPECS_DIR.glob("*.yaml"))
    if not stems:
        raise SystemExit(f"{SPECS_DIR} contains no *.yaml files")
    missing_aliases = set(stems) - set(SPEC_ALIASES)
    if missing_aliases:
        raise SystemExit(
            f"SPEC_ALIASES has no entry for: {sorted(missing_aliases)} -- add one so a "
            f"new spec file can't silently render as 'missing everywhere'"
        )
    return stems


def _filename_stems(directory: Path, extension: str) -> set[str]:
    if not directory.exists():
        return set()
    return {
        p.stem.lower().replace("-", "").replace("_", "") for p in directory.glob(f"*{extension}")
    }


def _has_pattern(lang: LanguageSource, spec_stem: str) -> bool:
    aliases = {a.lower().replace("-", "").replace("_", "") for a in SPEC_ALIASES[spec_stem]}

    patterns_stems = _filename_stems(lang.patterns_dir, lang.extension)
    if aliases & patterns_stems:
        return True

    if lang.composition_dir is not None:
        composition_stems = _filename_stems(lang.composition_dir, lang.extension)
        if aliases & composition_stems:
            return True

    if lang.name == "zig" and _ZIG_COMPOSITION_FILE.exists():
        content = _ZIG_COMPOSITION_FILE.read_text().lower()
        for alias in aliases:
            if f"pub const {alias}agent" in content.replace(" ", ""):
                return True

    return False


def build_conformance() -> dict:
    """Return the full spec-presence matrix: {spec: {language: bool}}."""
    stems = _spec_stems()
    matrix: dict[str, dict[str, bool]] = {}
    for stem in stems:
        matrix[stem] = {name: _has_pattern(lang, stem) for name, lang in LANGUAGES.items()}

    summary = {name: sum(1 for stem in stems if matrix[stem][name]) for name in LANGUAGES}

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "1.0",
        "total_patterns": len(stems),
        "patterns": matrix,
        "summary": summary,
    }


def write_conformance(conformance: dict, output_file: Path) -> None:
    with output_file.open("w") as f:
        json.dump(conformance, f, indent=2)
    print(f"Spec conformance written to: {output_file}")


def _normalize(conformance: dict) -> dict:
    normalized = dict(conformance)
    normalized["generated_at"] = "<normalized>"
    return normalized


def check_conformance_current(fresh: dict, output_file: Path) -> list[str]:
    if not output_file.exists():
        return [f"{output_file} does not exist -- run spec_conformance.py to create it"]
    committed = json.loads(output_file.read_text())
    if _normalize(committed) != _normalize(fresh):
        return [f"{output_file} is stale relative to a fresh regenerate"]
    return []


def print_summary(conformance: dict) -> None:
    print(f"Spec-presence conformance ({conformance['total_patterns']} patterns):")
    print("-" * 60)
    for name in LANGUAGES:
        count = conformance["summary"][name]
        print(f"  {name:<12} {count}/{conformance['total_patterns']}")


def main() -> int:
    check_only = "--check" in sys.argv
    conformance = build_conformance()
    output_file = ROOT / "spec-conformance.json"

    if check_only:
        errors = check_conformance_current(conformance, output_file)
        if errors:
            for e in errors:
                print(f"FAIL: {e}")
            print("\nRun: uv run python scripts/parity/spec_conformance.py")
            return 1
        print(f"{output_file} is current")
        return 0

    write_conformance(conformance, output_file)
    print_summary(conformance)
    return 0


if __name__ == "__main__":
    sys.exit(main())
