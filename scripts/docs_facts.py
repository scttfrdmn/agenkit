#!/usr/bin/env python3
"""Single source of truth for hand-written docs facts that drift.

Modeled directly on ``scripts/version.py``'s ``Declaration``/``check``/
``sync`` shape (see that file's docstring for the design rationale this
mirrors). The difference: a version declaration IS the whole value at its
site (a version string), so ``version.py`` substitutes a regex-captured
group in place. A docs fact is usually a sentence or list embedded in
surrounding hand-written prose, so this substitutes only the text between
a pair of HTML-comment markers, leaving the prose around it untouched.

Usage::

    scripts/docs_facts.py check   # exit 1 if any block is stale
    scripts/docs_facts.py sync    # rewrite every block from its source

``check`` is what CI runs (see #902 -- the motivating case was
``docs/parity/GAPS_ANALYSIS.md`` going five months stale while CI stayed
green throughout, because the existing parity pipeline regenerates fresh
output every run but never compared it to the committed copy).

v1 deliberately covers exactly one fact: the "18 Core Patterns" name list in
README.md, sourced from ``specs/patterns/*.yaml`` filenames. Explicitly out
of scope for this module: the README pattern-count table (sourced from
``feature-manifest.json`` via ``scripts/parity/matrix_generator.py --check``,
a separate, already-existing mechanism -- see that module rather than
duplicating it here) and test counts (change every run; state-a-number
guarantees staleness, so sibling fixes point readers at ``make test``
instead of a frozen figure). Versions are already owned by
``scripts/version.py``; this module must never become a 21st declaration
site for those.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "specs" / "patterns"

# Filename stem -> display name, for stems whose naming convention diverges
# from a naive title-case of the underscored filename (agents_as_tools.yaml
# should render "AgentsAsTools", not "Agents As Tools"). Every stem in
# SPECS_DIR must have an entry here or in the naive-title-case fallback --
# enforced by cmd_check below, so a new spec file can't silently render
# wrong.
_DISPLAY_NAME_OVERRIDES = {
    "agents_as_tools": "AgentsAsTools",
    "human_in_loop": "HumanInLoop",
    "memory_hierarchy": "MemoryHierarchy",
    "multiagent": "MultiAgent",
    "react": "ReAct",
    "reasoning_with_tools": "ReasoningWithTools",
}


def _display_name(stem: str) -> str:
    return _DISPLAY_NAME_OVERRIDES.get(stem, stem.capitalize())


def render_pattern_list() -> str:
    """The "18 Core Patterns" sentence, sourced from specs/patterns/*.yaml."""
    if not SPECS_DIR.exists():
        raise SystemExit(f"{SPECS_DIR} does not exist -- specs/patterns/ moved or was deleted")

    stems = sorted(p.stem for p in SPECS_DIR.glob("*.yaml"))
    if not stems:
        raise SystemExit(f"{SPECS_DIR} contains no *.yaml files -- nothing to list")

    names = ", ".join(_display_name(stem) for stem in stems)
    return f"**{len(stems)} Core Patterns** documented in the [Agent Patterns Book](../agent-patterns-book): {names}."


@dataclass(frozen=True)
class GeneratedBlock:
    """One marker-delimited region of hand-written prose.

    Mirrors ``version.py``'s ``Declaration``: ``read()``/``write()`` assert
    the markers appear exactly once each, for the same reason -- a marker
    pair that silently stops matching (a rename, a reformat) would turn
    this guard into a no-op rather than a loud failure.
    """

    path: str
    marker: str
    label: str
    render: staticmethod

    @property
    def full_path(self) -> Path:
        return ROOT / self.path

    def _markers(self) -> tuple[re.Pattern[str], re.Pattern[str]]:
        start = re.compile(rf"<!-- GENERATED:{re.escape(self.marker)}:start -->\n")
        end = re.compile(rf"<!-- GENERATED:{re.escape(self.marker)}:end -->\n")
        return start, end

    def read(self) -> str:
        """Return the text currently between this block's markers."""
        text = self.full_path.read_text(encoding="utf-8")
        start_re, end_re = self._markers()

        start_matches = list(start_re.finditer(text))
        end_matches = list(end_re.finditer(text))
        if len(start_matches) != 1 or len(end_matches) != 1:
            raise SystemExit(
                f"{self.path}: marker {self.marker!r} start/end appeared "
                f"{len(start_matches)}/{len(end_matches)} times, expected "
                f"exactly 1 each -- the surrounding doc changed and this "
                f"block's markers need fixing"
            )

        start_end = start_matches[0].end()
        end_start = end_matches[0].start()
        if end_start < start_end:
            raise SystemExit(f"{self.path}: {self.marker!r} end marker appears before start")
        return text[start_end:end_start]

    def write(self, new_content: str) -> bool:
        """Replace this block's content. Returns True if the file changed."""
        text = self.full_path.read_text(encoding="utf-8")
        start_re, end_re = self._markers()

        start_matches = list(start_re.finditer(text))
        end_matches = list(end_re.finditer(text))
        if len(start_matches) != 1 or len(end_matches) != 1:
            raise SystemExit(
                f"{self.path}: marker {self.marker!r} start/end appeared "
                f"{len(start_matches)}/{len(end_matches)} times, expected exactly 1 each"
            )

        start_end = start_matches[0].end()
        end_start = end_matches[0].start()
        new_text = text[:start_end] + new_content + text[end_start:]
        if new_text == text:
            return False
        self.full_path.write_text(new_text, encoding="utf-8")
        return True


BLOCKS = [
    GeneratedBlock(
        path="README.md",
        marker="pattern-list",
        label="18 Core Patterns list",
        render=staticmethod(render_pattern_list),
    ),
]

# Floor on the list's own size, mirroring version.py's _EXPECTED_DECLARATIONS
# -- quoting #868's rationale: "the reassuring count was the tell" applies
# here too. Raise this when a new block is added; never lower it silently.
_EXPECTED_BLOCKS = 1
if len(BLOCKS) < _EXPECTED_BLOCKS:
    raise SystemExit(
        f"scripts/docs_facts.py tracks {len(BLOCKS)} block(s) but expected at least "
        f"{_EXPECTED_BLOCKS}. A block was removed from BLOCKS; if that was deliberate, "
        f"lower _EXPECTED_BLOCKS in the same commit and say why."
    )


def cmd_check() -> int:
    mismatches = []
    for block in BLOCKS:
        current = block.read()
        fresh = block.render() + "\n"
        if current != fresh:
            mismatches.append((block, current, fresh))

    if mismatches:
        print(f"{len(mismatches)} generated doc block(s) are stale:\n")
        for block, current, fresh in mismatches:
            print(f"  {block.label} ({block.path}):")
            print(f"    committed: {current.strip()!r}")
            print(f"    fresh:     {fresh.strip()!r}")
        print("\nRun: scripts/docs_facts.py sync")
        return 1

    print(f"All {len(BLOCKS)} generated doc block(s) are current")
    return 0


def cmd_sync() -> int:
    changed = []
    for block in BLOCKS:
        if block.write(block.render() + "\n"):
            changed.append(block)
    for block in changed:
        print(f"  updated {block.path} ({block.marker})")
    print(f"{len(changed)} file(s) updated; {len(BLOCKS)} block(s) now current")
    return 0


def cmd_list() -> int:
    for block in BLOCKS:
        print(f"{block.marker}\t{block.path}\t{block.label}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="verify every block matches its source")
    sub.add_parser("sync", help="rewrite every block from its source")
    sub.add_parser("list", help="list tracked blocks")

    args = parser.parse_args()
    if args.command == "check":
        return cmd_check()
    if args.command == "sync":
        return cmd_sync()
    if args.command == "list":
        return cmd_list()
    return 1


if __name__ == "__main__":
    sys.exit(main())
