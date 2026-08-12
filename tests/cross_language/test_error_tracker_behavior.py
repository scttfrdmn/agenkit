"""
Cross-language error tracker behavior tests for Python.

Validates that Agenkit's Python ErrorTracker (p_a / P_error) behaves
consistently with the cross-language error tracker behavior specification
(#652, follow-up to #321).
"""

import json
from pathlib import Path

import pytest

from agenkit.evaluation import ErrorTracker

# Load error tracker behavior fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

with open(FIXTURES_DIR / "error_tracker_behavior.json") as f:
    ERROR_TRACKER_FIXTURES = json.load(f)

DEFAULT_TOLERANCE = 1e-6


def find_test_case(test_id: str) -> dict:
    """Find a specific test case by ID."""
    for test_case in ERROR_TRACKER_FIXTURES["test_cases"]:
        if test_case["id"] == test_id:
            return test_case
    raise ValueError(f"Test case not found: {test_id}")


def build_steps(test_case: dict) -> list[bool]:
    """Build the step outcome sequence from a fixture's `steps` or `steps_spec`."""
    if "steps" in test_case:
        return list(test_case["steps"])
    spec = test_case["steps_spec"]
    return [False] * spec["fail"] + [True] * spec["success"]


@pytest.mark.parametrize(
    "test_id",
    [tc["id"] for tc in ERROR_TRACKER_FIXTURES["test_cases"]],
)
def test_error_tracker_behavior(test_id: str) -> None:
    """Verify ErrorTracker's computed values match the shared fixture."""
    test_case = find_test_case(test_id)
    expected = test_case["expected"]
    tolerance = expected.get("tolerance", DEFAULT_TOLERANCE)

    tracker = ErrorTracker(enabled=True)
    for success in build_steps(test_case):
        tracker.record_step(success)

    assert tracker.total_steps == expected["total_steps"]
    assert tracker.failed_steps == expected["failed_steps"]
    assert tracker.per_step_error_rate() == pytest.approx(
        expected["per_step_error_rate"], abs=tolerance
    )

    if "cumulative_failure_probability_observed" in expected:
        assert tracker.cumulative_failure_probability() == pytest.approx(
            expected["cumulative_failure_probability_observed"], abs=tolerance
        )

    for steps_str, expected_p in expected["cumulative_failure_probability_steps"].items():
        n = int(steps_str)
        assert tracker.cumulative_failure_probability(steps=n) == pytest.approx(
            expected_p, abs=tolerance
        )
