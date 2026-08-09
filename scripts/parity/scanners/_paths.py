"""Shared source-file discovery for the language scanners.

Every scanner used to open-code the same two-line idiom:

    if not some_dir.exists():
        return []
    for f in some_dir.glob("*.ext"):
        ...

Both halves were wrong, and both failed silently:

1. ``glob`` is non-recursive, but several categories nest one level deeper
   (``techniques/reasoning/``, ``techniques/compositions/``,
   ``memory/strategies/``). ``techniques`` therefore reported 0 for all nine
   languages -- Python included, where 33 techniques exist.
2. Returning ``[]`` for a non-existent directory makes "the configured path is
   wrong" indistinguishable from "this language implements nothing". Three real
   paths had drifted (Zig ``adapters`` vs ``adapter``, C++/Zig memory living
   under ``infrastructure/``) and reported 0 rather than an error.

``iter_sources`` fixes (1) by recursing and (2) by raising, so a stale path is a
loud failure instead of a fake zero. Categories a language genuinely does not
implement are declared explicitly via ``NOT_IMPLEMENTED`` rather than inferred
from a missing directory.
"""

import re
from collections.abc import Iterator
from pathlib import Path

# Directory names that never contain source we want to scan.
_EXCLUDED_DIRS = frozenset(
    {
        "__pycache__",
        "node_modules",
        "build",
        "bin",
        "obj",
        "target",
        "dist",
        "zig-out",
        "zig-cache",
        ".zig-cache",
        "test",
        "tests",
        "__tests__",
    }
)


class MissingScanPathError(RuntimeError):
    """Raised when a scanner is configured with a path that does not exist.

    This is deliberately fatal. A silently-empty result is how the parity
    manifest came to report 0 LLM adapters for Zig while 7 were implemented.
    """


def iter_sources(directory: Path, pattern: str, *, required: bool = True) -> Iterator[Path]:
    """Yield source files under ``directory`` matching ``pattern``, recursively.

    Args:
        directory: Directory to scan.
        pattern: Filename glob, e.g. ``"*.py"``.
        required: If True (default), raise when ``directory`` does not exist.
            Pass False only for a category a language genuinely does not
            implement, and prefer declaring that in ``NOT_IMPLEMENTED``.

    Yields:
        Matching files, excluding private/underscore-prefixed names and build
        or test output directories.

    Raises:
        MissingScanPathError: If ``required`` and ``directory`` is absent.
    """
    if not directory.exists():
        if required:
            raise MissingScanPathError(
                f"configured scan path does not exist: {directory} "
                f"(pattern {pattern!r}). Either the source moved or the scanner "
                f"is stale -- an empty result here would silently understate parity."
            )
        return

    for path in sorted(directory.rglob(pattern)):
        if path.name.startswith((".", "_")):
            continue
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(directory).parts[:-1]):
            continue
        yield path


# Filenames that hold plumbing rather than a technique.
_NON_TECHNIQUE_STEMS = frozenset(
    {"mod", "root", "init", "index", "base", "types", "common", "artifact", "verifier"}
)

# Declaration keywords across all nine languages: Python/C++/C#/Java/Scala class,
# Go/TS type|class, Rust/C++ struct, Rust/Scala trait, Zig const, Scala object.
_DECLARATION = r"(?:class|struct|type|trait|object|const|interface|enum)"

# Subdirectories of techniques/ that hold actual techniques.
#
# Python additionally files A2A and MCP under techniques/protocols/, which no
# other language does. Those are protocol implementations, not reasoning
# techniques; counting them inflated Python's total with names like
# BedrockAdapter and ProtocolError and manufactured a gap that does not exist.
# Protocols belong in their own category (unmeasured today -- see #654).
_TECHNIQUE_SUBDIRS = frozenset({"reasoning", "compositions"})

# Composition-pattern classes that live in a composition/ directory (Zig: a
# single composition.zig file) alongside patterns/. Every language's *Agent
# scan regex was previously only pointed at patterns/, so it never saw these
# -- undercounting all nine languages by up to 3, invisibly in six of them
# because those six also ship duplicate sequential.*/parallel.*/fallback.*
# files directly inside patterns/ (see #918).
#
# That directory also holds non-agent types an unfiltered *Agent-suffix
# regex would wrongly count: Python/Go/Rust's plain-data `AgentResult`, and
# Rust's/Go's inline test-only mock structs (`CounterAgent`, `ErrorAgent`,
# `TestAgent`, etc., guarded by `#[cfg(test)]` / `_test.go` but still matched
# by a bare name regex). Restricting to this explicit set is what makes
# reusing each language's existing patterns-scan regex safe against
# composition/ without inventing a per-mock exclusion list.
COMPOSITION_AGENT_NAMES = frozenset(
    {"SequentialAgent", "ParallelAgent", "FallbackAgent", "ConditionalAgent"}
)


def scan_techniques_by_filename(
    directory: Path, pattern: str, *, required: bool = True
) -> list[str]:
    """Detect techniques as the primary type declared in each technique file.

    The previous per-language regexes required a ``Technique`` or ``Strategy``
    name suffix. No technique in this repo is named that way -- they are
    ``ChainOfThought``, ``LeastToMost``, ``GraphOfThought`` -- so every language's
    count was 0 even after the directory paths were corrected.

    Naming also diverges legitimately: Python and Go declare ``ChainOfThought``
    while Rust, C++ and Zig declare ``ChainOfThoughtAgent``. Keying off the
    filename instead of a name suffix accommodates both, and treats the file as
    the unit of implementation -- which is what "does this language implement
    chain-of-thought?" actually asks.

    Args:
        directory: The techniques directory.
        pattern: Filename glob for the language, e.g. ``"*.go"``.
        required: Pass False where the language has no techniques subsystem at
            all (C#/Java/Scala, tracked in #754), so its absence is a declared
            gap rather than a stale path.

    Returns:
        Sorted unique technique type names.
    """
    techniques: list[str] = []

    for path in iter_sources(directory, pattern, required=required):
        if path.stem in _NON_TECHNIQUE_STEMS:
            continue
        if re.search(r"(?:_test|\.test|_spec|\.spec)$", path.stem):
            continue

        relative_parts = path.relative_to(directory).parts[:-1]
        if relative_parts and relative_parts[0] not in _TECHNIQUE_SUBDIRS:
            continue

        # chain_of_thought.py / chain-of-thought.ts -> ChainOfThought
        expected = "".join(part.capitalize() for part in re.split(r"[_-]", path.stem))

        try:
            content = path.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue

        # Accept the stem itself or a suffixed variant (ChainOfThoughtAgent).
        matches = re.findall(rf"\b{_DECLARATION}\s+({re.escape(expected)}\w*)", content)
        if matches:
            techniques.append(sorted(set(matches), key=len)[0])

    return sorted(set(techniques))
