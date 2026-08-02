"""Tests for parity regression checking.

Validates that regression checker correctly identifies feature count regressions
and missing critical features.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.parity import check_regression


@pytest.fixture
def mock_manifest():
    """Mock feature manifest for testing."""
    return {
        "generated_at": "2026-02-04T00:00:00Z",
        "version": "1.0",
        "languages": {
            "python": {
                "patterns": [
                    "AutonomousAgent",
                    "ConversationalAgent",
                    "ReActAgent",
                ],
                "middleware": ["TimeoutDecorator", "RetryDecorator"],
                "llm_adapters": [],
                "memory": [],
                "techniques": [],
            },
            "go": {
                "patterns": [
                    "AutonomousAgent",
                    "ConversationalAgent",
                    "ReActAgent",
                ],
                "middleware": ["TimeoutDecorator", "RetryDecorator"],
                "llm_adapters": [],
                "memory": [],
                "techniques": [],
            },
            "typescript": {
                "patterns": [
                    "AutonomousAgent",
                    "ConversationalAgent",
                    "ReActAgent",
                ],
                "middleware": ["TimeoutMiddleware", "RetryMiddleware"],
                "llm_adapters": [],
                "memory": [],
                "techniques": [],
            },
        },
        "summary": {
            "total": {"python": 5, "go": 5, "typescript": 5},
            "patterns": {"python": 3, "go": 3, "typescript": 3},
            "middleware": {"python": 2, "go": 2, "typescript": 2},
        },
    }


# Floors used by the logic tests below.
#
# These deliberately do NOT reference MIN_FEATURE_COUNTS. Recalibrating the real
# floors is expected maintenance (they were raised in #753 once the scanner
# stopped reporting 0 techniques), and coupling these tests to those values made
# every recalibration look like a test failure. What is worth testing here is the
# comparison logic; whether the shipped floors are correctly calibrated is
# asserted separately in TestProductionFloors.
TEST_FLOORS = {
    "python": 43,
    "go": 43,
    "typescript": 35,
    "rust": 35,
    "cpp": 35,
    "zig": 25,
}


class TestFeatureCountValidation:
    """Test feature count regression detection."""

    def test_all_languages_meet_minimums(self, mock_manifest):
        """Verify check passes when all languages meet minimums."""
        mock_manifest["summary"]["total"] = {
            "python": 43,
            "go": 43,
            "typescript": 36,
            "rust": 35,
            "cpp": 35,
            "zig": 25,
        }

        with patch.object(check_regression, "MIN_FEATURE_COUNTS", TEST_FLOORS):
            passed, errors = check_regression.check_feature_counts(mock_manifest)

        assert passed
        assert len(errors) == 0

    def test_detects_regression(self, mock_manifest):
        """Verify check fails when language drops below minimum."""
        # Set TypeScript below minimum
        mock_manifest["summary"]["total"] = {
            "python": 43,
            "go": 43,
            "typescript": 30,  # Below 35 minimum
            "rust": 35,
            "cpp": 35,
            "zig": 25,
        }

        with patch.object(check_regression, "MIN_FEATURE_COUNTS", TEST_FLOORS):
            passed, errors = check_regression.check_feature_counts(mock_manifest)

        assert not passed
        assert len(errors) == 1
        assert "typescript" in errors[0].lower()
        assert "30 features" in errors[0]
        assert "minimum: 35" in errors[0]

    def test_detects_multiple_regressions(self, mock_manifest):
        """Verify check detects multiple regressions."""
        mock_manifest["summary"]["total"] = {
            "python": 43,
            "go": 40,  # Below 43 minimum
            "typescript": 30,  # Below 35 minimum
            "rust": 35,
            "cpp": 35,
            "zig": 20,  # Below 25 minimum
        }

        with patch.object(check_regression, "MIN_FEATURE_COUNTS", TEST_FLOORS):
            passed, errors = check_regression.check_feature_counts(mock_manifest)

        assert not passed
        assert len(errors) == 3

    def test_language_absent_from_manifest_is_a_regression(self, mock_manifest):
        """A language missing from the summary must fail, not pass vacuously.

        ``summary.get(lang, 0)`` means an absent language reads as 0 features.
        That is the correct behaviour -- a language dropping out of the manifest
        entirely is a worse regression than one losing features -- but it is only
        correct as long as the floor is above zero for every language.
        """
        mock_manifest["summary"]["total"] = {"python": 43, "go": 43}

        with patch.object(check_regression, "MIN_FEATURE_COUNTS", TEST_FLOORS):
            passed, errors = check_regression.check_feature_counts(mock_manifest)

        assert not passed
        assert {"typescript", "rust", "cpp", "zig"} == {
            lang
            for lang in ("typescript", "rust", "cpp", "zig")
            if any(lang in e.lower() for e in errors)
        }


class TestProductionFloors:
    """Test the shipped MIN_FEATURE_COUNTS, not the comparison logic."""

    def test_every_language_has_a_floor(self):
        """All nine implementations must be gated.

        C#, Java and Scala shipped as full-parity implementations in
        v0.71.0-v0.73.0 but had no entry here, so they could have lost every
        feature without failing the check.
        """
        expected = {
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
        assert set(check_regression.MIN_FEATURE_COUNTS) == expected

    def test_floors_are_positive(self):
        """A zero floor would make an absent language pass vacuously."""
        for lang, floor in check_regression.MIN_FEATURE_COUNTS.items():
            assert floor > 0, f"{lang} has a non-positive floor"

    def test_floors_are_below_current_measurements(self):
        """The committed manifest must clear every floor.

        Guards against raising a floor above what the scanner actually measures,
        which would leave the repo permanently red.
        """
        manifest_path = Path("feature-manifest.json")
        if not manifest_path.exists():
            pytest.skip("feature-manifest.json not generated")

        totals = json.loads(manifest_path.read_text())["summary"]["total"]

        for lang, floor in check_regression.MIN_FEATURE_COUNTS.items():
            assert lang in totals, f"{lang} has a floor but is not in the manifest"
            assert totals[lang] >= floor, (
                f"{lang}: manifest reports {totals[lang]} but floor is {floor}"
            )

    def test_reference_language_is_gated(self):
        """Percentages are computed against the reference language's count."""
        assert check_regression.REFERENCE_LANGUAGE in check_regression.MIN_FEATURE_COUNTS


class TestMarkdownTable:
    """Test the PR-comment table renderer."""

    def test_covers_every_gated_language(self, mock_manifest):
        """The table must list all nine languages.

        The workflow's previous inline version hardcoded six, so C#, Java and
        Scala were absent from every parity comment.
        """
        mock_manifest["summary"]["total"] = dict.fromkeys(check_regression.MIN_FEATURE_COUNTS, 100)

        table = check_regression.render_markdown_table(mock_manifest)

        for lang in check_regression.MIN_FEATURE_COUNTS:
            assert f"| {lang.title()} |" in table

    def test_reference_is_labelled_baseline_at_100_percent(self, mock_manifest):
        """The reference implementation is 100% of itself by definition."""
        mock_manifest["summary"]["total"] = dict.fromkeys(check_regression.MIN_FEATURE_COUNTS, 100)

        table = check_regression.render_markdown_table(mock_manifest)

        assert "| Python | 100 | 100.0% | 50 | ✅ Baseline |" in table

    def test_flags_a_language_below_its_floor(self, mock_manifest):
        """A count under the floor renders ⚠️, not ✅."""
        mock_manifest["summary"]["total"] = dict.fromkeys(check_regression.MIN_FEATURE_COUNTS, 100)
        mock_manifest["summary"]["total"]["zig"] = 1

        table = check_regression.render_markdown_table(mock_manifest)

        zig_row = next(line for line in table.splitlines() if line.startswith("| Zig |"))
        assert "⚠️" in zig_row
        assert "✅" not in zig_row


class TestCriticalFeatureValidation:
    """Test critical feature detection."""

    def test_all_critical_features_present(self, mock_manifest):
        """Verify check passes when all critical features exist."""
        passed, errors = check_regression.check_critical_features(mock_manifest)

        assert passed
        assert len(errors) == 0

    def test_detects_missing_critical_pattern(self, mock_manifest):
        """Verify check fails when critical pattern is missing."""
        # Remove critical pattern from Go
        mock_manifest["languages"]["go"]["patterns"] = [
            "AutonomousAgent",
            "ConversationalAgent",
            # Missing ReActAgent
        ]

        passed, errors = check_regression.check_critical_features(mock_manifest)

        assert not passed
        assert any("go" in e.lower() and "react" in e.lower() for e in errors)

    def test_detects_missing_critical_middleware(self, mock_manifest):
        """Verify check fails when critical middleware is missing."""
        # Remove critical middleware from TypeScript
        mock_manifest["languages"]["typescript"]["middleware"] = [
            "TimeoutMiddleware",
            # Missing RetryMiddleware
        ]

        passed, errors = check_regression.check_critical_features(mock_manifest)

        assert not passed
        assert any("typescript" in e.lower() and "retry" in e.lower() for e in errors)

    def test_handles_naming_variations(self, mock_manifest):
        """Verify check handles naming variations across languages."""
        # TypeScript uses Middleware suffix instead of Decorator
        mock_manifest["languages"]["typescript"]["middleware"] = [
            "TimeoutMiddleware",
            "RetryMiddleware",
        ]

        passed, _errors = check_regression.check_critical_features(mock_manifest)

        assert passed  # Should still pass despite different naming

    def test_handles_case_variations(self, mock_manifest):
        """Verify check handles case variations (e.g., ReAct vs React)."""
        # Use ReactAgent instead of ReActAgent (C++ naming)
        mock_manifest["languages"]["go"]["patterns"] = [
            "AutonomousAgent",
            "ConversationalAgent",
            "ReactAgent",  # Different casing
        ]

        passed, _errors = check_regression.check_critical_features(mock_manifest)

        assert passed  # Should pass with case-insensitive matching


class TestRegressionChecker:
    """Test overall regression checking."""

    @patch("scripts.parity.check_regression.load_manifest")
    def test_successful_validation(self, mock_load, mock_manifest, capsys):
        """Verify successful validation prints correct output."""
        # Set up valid manifest
        mock_manifest["summary"]["total"] = {
            "python": 43,
            "go": 43,
            "typescript": 36,
            "rust": 35,
            "cpp": 35,
            "zig": 25,
        }
        mock_load.return_value = mock_manifest

        with patch.object(check_regression, "MIN_FEATURE_COUNTS", TEST_FLOORS):
            exit_code = check_regression.check_no_regressions()

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "✅ All parity checks passed" in captured.out
        assert "No regressions detected" in captured.out
        # Parity is relative to the reference implementation's measured count, so
        # the reference must read as 100% of itself -- it previously reported
        # "125.6%" because the divisor was a hardcoded floor.
        assert "Python: 43 features (100.0% of python)" in captured.out

    @patch("scripts.parity.check_regression.load_manifest")
    def test_failed_validation(self, mock_load, mock_manifest, capsys):
        """Verify failed validation prints correct output."""
        # Set up manifest with regression
        mock_manifest["summary"]["total"] = {
            "python": 43,
            "go": 43,
            "typescript": 30,  # Regression
            "rust": 35,
            "cpp": 35,
            "zig": 25,
        }
        mock_load.return_value = mock_manifest

        with patch.object(check_regression, "MIN_FEATURE_COUNTS", TEST_FLOORS):
            exit_code = check_regression.check_no_regressions()

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "❌ Parity validation failed" in captured.out
        assert "typescript" in captured.out.lower()
