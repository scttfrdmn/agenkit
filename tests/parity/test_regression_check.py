"""Tests for parity regression checking.

Validates that regression checker correctly identifies feature count regressions
and missing critical features.
"""

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


class TestFeatureCountValidation:
    """Test feature count regression detection."""

    def test_all_languages_meet_minimums(self, mock_manifest):
        """Verify check passes when all languages meet minimums."""
        # Adjust mock to meet test minimums
        mock_manifest["summary"]["total"] = {
            "python": 43,
            "go": 43,
            "typescript": 36,
            "rust": 35,
            "cpp": 35,
            "zig": 25,
        }

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

        passed, errors = check_regression.check_feature_counts(mock_manifest)

        assert not passed
        assert len(errors) == 3


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

        passed, errors = check_regression.check_critical_features(mock_manifest)

        assert passed  # Should still pass despite different naming

    def test_handles_case_variations(self, mock_manifest):
        """Verify check handles case variations (e.g., ReAct vs React)."""
        # Use ReactAgent instead of ReActAgent (C++ naming)
        mock_manifest["languages"]["go"]["patterns"] = [
            "AutonomousAgent",
            "ConversationalAgent",
            "ReactAgent",  # Different casing
        ]

        passed, errors = check_regression.check_critical_features(mock_manifest)

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

        exit_code = check_regression.check_no_regressions()

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "✅ All parity checks passed" in captured.out
        assert "No regressions detected" in captured.out

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

        exit_code = check_regression.check_no_regressions()

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "❌ Parity validation failed" in captured.out
        assert "typescript" in captured.out.lower()
