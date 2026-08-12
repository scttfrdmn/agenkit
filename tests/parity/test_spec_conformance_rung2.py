"""Tests for scripts/parity/spec_conformance_rung2.py.

Rung 2 (#924) checks constructor-parameter conformance against
specs/patterns/*.yaml for every (pattern, language) pair rung 1 says is
implemented. The most important invariant this locks in: Python -- the
language #924's spec-fixing pass was audited against -- should report
"match" for all 18 patterns. A regression here means either the spec
audit was undone (a spec file drifted back to describing a stale
constructor) or Python's actual constructor changed without the spec
being updated to match, which is exactly the drift #924 was filed to catch.

The other 8 languages are best-effort (regex-based extraction, not an
AST) per #924's explicit scope -- this file does NOT assert those are
mismatch-free, only that the checker runs, reports something sane, and
doesn't silently swallow errors into false "match" results.
"""

from __future__ import annotations

import json

from scripts.parity import spec_conformance_rung2 as rung2


class TestNormalizeParam:
    def test_snake_camel_pascal_fold_to_same_key(self):
        assert (
            rung2.normalize_param("max_iterations")
            == rung2.normalize_param("maxIterations")
            == rung2.normalize_param("MaxIterations")
        )

    def test_distinct_params_stay_distinct(self):
        assert rung2.normalize_param("max_iterations") != rung2.normalize_param("max_steps")

    def test_hyphens_also_fold(self):
        assert rung2.normalize_param("tool-use-prompt") == rung2.normalize_param("tool_use_prompt")


class TestPythonBaselineIsClean:
    """Python is the language #924's spec-editing pass was audited
    against ("Python is authoritative for what was actually built").
    Every one of the 18 pattern specs should therefore report "match"
    against Python's real constructor/config -- if this regresses, either
    a spec regressed or Python's constructor moved out from under it.
    """

    def test_every_spec_with_an_interface_matches_python(self):
        report = rung2.build_rung2_report()
        failures = []
        for stem, per_lang in report["results"].items():
            entry = per_lang.get("python")
            if entry is None:
                continue
            if entry["status"] == "no_interface":
                continue
            if entry["status"] != "match":
                failures.append((stem, entry["status"], entry.get("missing_in_code"), entry.get("extra_in_code")))
        assert not failures, f"Python constructor/spec mismatches: {failures}"

    def test_all_18_specs_have_an_interface_section(self):
        """specs/patterns/README.md claims 8 of 18 are 'stub' files with no
        interface section. Verified as of #924: all 18 currently declare
        interface.constructor.parameters. If a file's interface section is
        later removed (reverting to stub), that's a scope change worth a
        deliberate, reviewed test update -- not a silent drop from this
        checker's coverage.
        """
        report = rung2.build_rung2_report()
        no_interface = [
            stem
            for stem, per_lang in report["results"].items()
            if per_lang.get("python", {}).get("status") == "no_interface"
        ]
        assert no_interface == []


class TestReportStructure:
    def test_report_covers_all_18_pattern_files(self):
        report = rung2.build_rung2_report()
        assert len(report["results"]) == 18

    def test_totals_sum_to_18_patterns_times_9_languages(self):
        report = rung2.build_rung2_report()
        totals = report["totals"]
        assert sum(totals.values()) == 18 * 9

    def test_report_is_json_serializable(self):
        report = rung2.build_rung2_report()
        # Round-trips cleanly -- no stray non-serializable types (e.g. Path,
        # dataclass instances) leaking into the report dict.
        json.loads(json.dumps(report))

    def test_not_present_pairs_carry_no_actual_params(self):
        """A (pattern, language) pair rung 1 says isn't implemented should
        not report fabricated 'actual_params' -- there's nothing to have
        extracted.
        """
        report = rung2.build_rung2_report()
        for per_lang in report["results"].values():
            for entry in per_lang.values():
                if entry["status"] == "not_present":
                    assert "actual_params" not in entry


class TestCheckDetectsStaleness:
    def test_check_detects_staleness(self, tmp_path):
        fresh = rung2.build_rung2_report()
        stale_copy = dict(fresh)
        stale_copy["totals"] = dict(fresh["totals"])
        stale_copy["totals"]["match"] = -1

        output_file = tmp_path / "spec-conformance-rung2.json"
        rung2.write_report(stale_copy, output_file)

        errors = rung2.check_report_current(fresh, output_file)
        assert errors

    def test_check_passes_against_its_own_fresh_output(self, tmp_path):
        fresh = rung2.build_rung2_report()
        output_file = tmp_path / "spec-conformance-rung2.json"
        rung2.write_report(fresh, output_file)

        errors = rung2.check_report_current(fresh, output_file)
        assert not errors


class TestNonGating:
    """#924 is explicit: this must not fail a build. main() only returns
    non-zero for --check against a stale file (a bookkeeping problem, not
    a conformance failure) -- never because mismatches were found.
    """

    def test_main_without_check_flag_returns_zero_regardless_of_mismatches(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rung2, "ROOT", tmp_path)
        monkeypatch.setattr(rung2.sys, "argv", ["spec_conformance_rung2.py"])
        assert rung2.main() == 0
