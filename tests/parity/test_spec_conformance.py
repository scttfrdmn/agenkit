"""Tests for scripts/parity/spec_conformance.py.

Two things this covers that a plain "does it run" smoke test wouldn't:
verified spec-presence counts against the actual repo (so this rots loudly
the moment a real gap opens or closes), and the cross-corpus consistency
check between specs/patterns/ and tests/cross_language/specs/ that this
directory's README promises but nothing previously enforced.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.parity import spec_conformance

CROSS_LANGUAGE_SPECS_DIR = Path(__file__).resolve().parent.parent / "cross_language" / "specs"


class TestSpecAliasCompleteness:
    def test_every_spec_file_has_an_alias_entry(self):
        """A new specs/patterns/*.yaml file with no SPEC_ALIASES entry would
        raise SystemExit today (enforced in _spec_stems()) -- this test
        makes that failure visible in `pytest` output, not just at CLI
        invocation time.
        """
        stems = {p.stem for p in spec_conformance.SPECS_DIR.glob("*.yaml")}
        assert stems <= set(spec_conformance.SPEC_ALIASES)

    def test_no_stale_alias_entries(self):
        """The reverse direction: an alias entry for a spec file that no
        longer exists is dead weight, not caught by _spec_stems()'s guard.
        """
        stems = {p.stem for p in spec_conformance.SPECS_DIR.glob("*.yaml")}
        stale = set(spec_conformance.SPEC_ALIASES) - stems
        assert not stale, f"SPEC_ALIASES has entries for deleted spec files: {stale}"


class TestSpecPresenceMatrix:
    def test_conformance_matches_verified_counts(self):
        """Locks in the counts verified when this was designed: 18/18 for
        Python/Go/TypeScript/Rust/C++/Zig, 17/18 for C#/Java/Scala (missing
        exactly agents_as_tools). A regression here means either a real
        implementation gap opened, or spec_conformance.py's detection logic
        broke -- both worth a loud failure, not a silent drift.
        """
        conformance = spec_conformance.build_conformance()

        full_18 = {"python", "go", "typescript", "rust", "cpp", "zig"}
        partial_17 = {"csharp", "java", "scala"}

        for lang in full_18:
            assert conformance["summary"][lang] == 18, (
                f"{lang}: expected 18/18, got {conformance['summary'][lang]}"
            )
        for lang in partial_17:
            assert conformance["summary"][lang] == 17, (
                f"{lang}: expected 17/18, got {conformance['summary'][lang]}"
            )

        for lang in partial_17:
            assert conformance["patterns"]["agents_as_tools"][lang] is False, (
                f"{lang}: expected agents_as_tools to be the one missing pattern"
            )

    def test_check_detects_staleness(self, tmp_path):
        fresh = spec_conformance.build_conformance()
        stale_copy = dict(fresh)
        stale_copy["summary"] = dict(fresh["summary"])
        stale_copy["summary"]["python"] = -1

        output_file = tmp_path / "spec-conformance.json"
        spec_conformance.write_conformance(stale_copy, output_file)

        errors = spec_conformance.check_conformance_current(fresh, output_file)
        assert errors


class TestCrossCorpusConsistency:
    """specs/patterns/'s own README promises pattern.name agrees with
    tests/cross_language/specs/ for every overlapping stem -- enforce it,
    per the design's verified claim that this holds today (a ratchet, not
    remediation).
    """

    @staticmethod
    def _pattern_name(path: Path) -> str:
        with path.open() as f:
            spec = yaml.safe_load(f)
        return spec["pattern"]["name"]

    def test_overlapping_stems_agree_on_pattern_name(self):
        if not CROSS_LANGUAGE_SPECS_DIR.exists():
            pytest.skip("tests/cross_language/specs/ not present")

        primary_stems = {p.stem: p for p in spec_conformance.SPECS_DIR.glob("*.yaml")}
        rival_stems = {p.stem: p for p in CROSS_LANGUAGE_SPECS_DIR.glob("*.yaml")}

        overlap = set(primary_stems) & set(rival_stems)
        assert overlap, "expected at least one overlapping stem between the two corpora"

        mismatches = []
        for stem in sorted(overlap):
            primary_name = self._pattern_name(primary_stems[stem])
            rival_name = self._pattern_name(rival_stems[stem])
            if primary_name != rival_name:
                mismatches.append((stem, primary_name, rival_name))

        assert not mismatches, (
            f"pattern.name disagrees between specs/patterns/ and "
            f"tests/cross_language/specs/ for: {mismatches}"
        )

    def test_memory_hierarchy_naming_divergence_is_the_only_known_stem_mismatch(self):
        """Documents the one known filename mismatch between the corpora
        (specs/patterns/memory_hierarchy.yaml vs
        tests/cross_language/specs/memory.yaml) so a future rename in
        either corpus is a deliberate, reviewed change rather than a
        silent drift this test would otherwise miss.
        """
        if not CROSS_LANGUAGE_SPECS_DIR.exists():
            pytest.skip("tests/cross_language/specs/ not present")

        primary_stems = {p.stem for p in spec_conformance.SPECS_DIR.glob("*.yaml")}
        rival_stems = {p.stem for p in CROSS_LANGUAGE_SPECS_DIR.glob("*.yaml")}

        assert "memory_hierarchy" in primary_stems
        assert "memory_hierarchy" not in rival_stems
        assert "memory" in rival_stems
