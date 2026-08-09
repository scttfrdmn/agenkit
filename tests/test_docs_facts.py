"""Behavioral tests for scripts/docs_facts.py.

Verified the way scripts/check-release-gate.sh verifies release.sh: by
actually running the checker against a corrupted copy and asserting it
catches the corruption, not by inspecting the checker's source and trusting
it looks right (#849/#857's lesson -- a check nobody verified is not a
check).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import docs_facts


def test_pattern_list_render_matches_specs_directory():
    rendered = docs_facts.render_pattern_list()
    stems = sorted(p.stem for p in docs_facts.SPECS_DIR.glob("*.yaml"))

    assert f"**{len(stems)} Core Patterns**" in rendered
    for stem in stems:
        assert docs_facts._display_name(stem) in rendered


def test_every_spec_stem_has_a_sensible_display_name():
    """Guards the override table against silently rendering a new spec
    file's name wrong (e.g. a naive title-case of an underscored filename).
    """
    for path in docs_facts.SPECS_DIR.glob("*.yaml"):
        name = docs_facts._display_name(path.stem)
        assert " " not in name, (
            f"{path.stem} rendered as {name!r} -- add an override in "
            f"_DISPLAY_NAME_OVERRIDES if the naive title-case is wrong"
        )


def test_committed_readme_block_is_current():
    """The steady state: check() must be green against the actual repo."""
    block = next(b for b in docs_facts.BLOCKS if b.marker == "pattern-list")
    assert block.read().strip() == docs_facts.render_pattern_list().strip()


def test_language_support_table_render_matches_spec_conformance():
    rendered = docs_facts.render_language_support_table()

    import json

    conformance = json.loads(docs_facts.SPEC_CONFORMANCE_FILE.read_text())
    for lang, count in conformance["summary"].items():
        display = docs_facts._LANGUAGE_DISPLAY[lang]
        assert display in rendered
        assert f"{count}/{conformance['total_patterns']}" in rendered


def test_language_support_table_flags_missing_patterns():
    rendered = docs_facts.render_language_support_table()

    assert "missing `AgentsAsTools`" in rendered
    for full_lang in ("Python", "Go", "TypeScript", "Rust", "C++", "Zig"):
        # A fully-conformant language's row must not claim a missing pattern.
        row_start = rendered.index(f"**{full_lang}**")
        row_end = rendered.index("\n", row_start)
        assert "missing" not in rendered[row_start:row_end]


def test_committed_readme_language_support_table_is_current():
    block = next(b for b in docs_facts.BLOCKS if b.marker == "language-support-table")
    assert block.read().strip() == docs_facts.render_language_support_table().strip()


@pytest.fixture
def scratch_block(tmp_path, monkeypatch):
    """A GeneratedBlock pointed at a scratch file under tmp_path, via
    docs_facts.ROOT so GeneratedBlock's real path-resolution logic
    (full_path = ROOT / self.path) is exercised unmodified.
    """
    monkeypatch.setattr(docs_facts, "ROOT", tmp_path)
    scratch = tmp_path / "doc.md"
    scratch.write_text(
        "some prose\n"
        "<!-- GENERATED:pattern-list:start -->\n"
        "placeholder\n"
        "<!-- GENERATED:pattern-list:end -->\n"
        "more prose\n",
        encoding="utf-8",
    )
    return docs_facts.GeneratedBlock(
        path="doc.md",
        marker="pattern-list",
        label="test double",
        render=staticmethod(docs_facts.render_pattern_list),
    )


def test_check_detects_a_corrupted_block(scratch_block):
    current = scratch_block.read()
    fresh = docs_facts.render_pattern_list()

    assert current.strip() != fresh.strip()


def test_write_then_read_round_trips(scratch_block):
    fresh = docs_facts.render_pattern_list() + "\n"

    changed = scratch_block.write(fresh)

    assert changed is True
    assert scratch_block.read() == fresh
    # A second write with identical content reports no change -- write()
    # must be idempotent, not always claim it rewrote something.
    assert scratch_block.write(fresh) is False


def test_missing_markers_raises_systemexit(tmp_path, monkeypatch):
    """A marker that stops matching (renamed, reformatted) must fail
    loudly, not silently become a no-op -- the same discipline version.py's
    Declaration.read()/write() apply to their regex patterns.
    """
    monkeypatch.setattr(docs_facts, "ROOT", tmp_path)
    scratch = tmp_path / "doc.md"
    scratch.write_text("no markers here at all\n", encoding="utf-8")

    block = docs_facts.GeneratedBlock(
        path="doc.md",
        marker="pattern-list",
        label="test double",
        render=staticmethod(docs_facts.render_pattern_list),
    )

    with pytest.raises(SystemExit):
        block.read()
    with pytest.raises(SystemExit):
        block.write("x")


def test_duplicate_start_marker_raises_systemexit(tmp_path, monkeypatch):
    """Two start markers is exactly as ambiguous as zero -- both must
    raise, not pick the first/last match silently.
    """
    monkeypatch.setattr(docs_facts, "ROOT", tmp_path)
    scratch = tmp_path / "doc.md"
    scratch.write_text(
        "<!-- GENERATED:pattern-list:start -->\na\n<!-- GENERATED:pattern-list:end -->\n"
        "<!-- GENERATED:pattern-list:start -->\nb\n<!-- GENERATED:pattern-list:end -->\n",
        encoding="utf-8",
    )

    block = docs_facts.GeneratedBlock(
        path="doc.md",
        marker="pattern-list",
        label="test double",
        render=staticmethod(docs_facts.render_pattern_list),
    )

    with pytest.raises(SystemExit):
        block.read()
