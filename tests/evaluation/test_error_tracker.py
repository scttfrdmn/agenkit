"""Tests for ErrorTracker — per-step error rate (p_a) and compounding (P_error)."""

import math

import pytest

from agenkit.evaluation import ErrorTracker, StepResult

# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------


def test_step_result_defaults() -> None:
    r = StepResult(success=True)
    assert r.success is True
    assert r.name is None
    assert r.error is None


def test_step_result_failure_fields() -> None:
    r = StepResult(success=False, name="fetch", error="timeout")
    assert r.success is False
    assert r.name == "fetch"
    assert r.error == "timeout"


# ---------------------------------------------------------------------------
# Opt-in / disabled behavior
# ---------------------------------------------------------------------------


def test_disabled_by_default_records_nothing() -> None:
    tracker = ErrorTracker()
    assert tracker.enabled is False
    tracker.record_step(False, error="boom")
    assert tracker.total_steps == 0
    assert tracker.failed_steps == 0
    assert tracker.per_step_error_rate() == 0.0
    assert tracker.cumulative_failure_probability() == 0.0


def test_enabled_records_steps() -> None:
    tracker = ErrorTracker(enabled=True)
    tracker.record_step(True)
    tracker.record_step(False, error="x")
    assert tracker.total_steps == 2
    assert tracker.failed_steps == 1


# ---------------------------------------------------------------------------
# per_step_error_rate (p_a)
# ---------------------------------------------------------------------------


def test_per_step_error_rate_empty_is_zero() -> None:
    assert ErrorTracker(enabled=True).per_step_error_rate() == 0.0


def test_per_step_error_rate_all_success() -> None:
    t = ErrorTracker(enabled=True)
    for _ in range(5):
        t.record_step(True)
    assert t.per_step_error_rate() == 0.0


def test_per_step_error_rate_all_fail() -> None:
    t = ErrorTracker(enabled=True)
    for _ in range(4):
        t.record_step(False)
    assert t.per_step_error_rate() == 1.0


def test_per_step_error_rate_mixed() -> None:
    t = ErrorTracker(enabled=True)
    # 2 failures out of 8 -> 0.25
    outcomes = [True, False, True, True, False, True, True, True]
    for ok in outcomes:
        t.record_step(ok)
    assert t.per_step_error_rate() == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# cumulative_failure_probability (P_error = 1 - (1 - p_a) ** n)
# ---------------------------------------------------------------------------


def test_cumulative_empty_is_zero() -> None:
    assert ErrorTracker(enabled=True).cumulative_failure_probability() == 0.0


def test_cumulative_observed_uses_recorded_step_count() -> None:
    t = ErrorTracker(enabled=True)
    t.record_step(True)
    t.record_step(False)
    # p_a = 0.5, n = 2 -> 1 - 0.5^2 = 0.75
    assert t.cumulative_failure_probability() == pytest.approx(0.75)


def test_cumulative_projected_steps() -> None:
    t = ErrorTracker(enabled=True)
    t.record_step(True)
    t.record_step(False)  # p_a = 0.5
    # project over 10 steps: 1 - 0.5^10
    assert t.cumulative_failure_probability(steps=10) == pytest.approx(1 - 0.5**10)


def test_cumulative_compounding_small_rate() -> None:
    # The motivating case: a small per-step rate compounds over a long run.
    t = ErrorTracker(enabled=True)
    # p_a = 0.01 (1 failure in 100)
    t.record_step(False)
    for _ in range(99):
        t.record_step(True)
    assert t.per_step_error_rate() == pytest.approx(0.01)
    # Over 100 steps: 1 - 0.99^100 ~= 0.634
    p_error = t.cumulative_failure_probability(steps=100)
    assert p_error == pytest.approx(1 - 0.99**100)
    assert 0.63 < p_error < 0.64


def test_cumulative_zero_rate_is_zero() -> None:
    t = ErrorTracker(enabled=True)
    for _ in range(10):
        t.record_step(True)
    assert t.cumulative_failure_probability(steps=1000) == 0.0


def test_cumulative_full_rate_is_one() -> None:
    t = ErrorTracker(enabled=True)
    t.record_step(False)
    assert t.cumulative_failure_probability(steps=5) == pytest.approx(1.0)


def test_cumulative_nonpositive_steps_is_zero() -> None:
    t = ErrorTracker(enabled=True)
    t.record_step(False)
    assert t.cumulative_failure_probability(steps=0) == 0.0
    assert t.cumulative_failure_probability(steps=-3) == 0.0


def test_cumulative_in_unit_interval() -> None:
    t = ErrorTracker(enabled=True)
    for ok in [True, False, True, False, False]:
        t.record_step(ok)
    for n in range(1, 50):
        p = t.cumulative_failure_probability(steps=n)
        assert 0.0 <= p <= 1.0
        assert not math.isnan(p)


# ---------------------------------------------------------------------------
# reset + docstring example
# ---------------------------------------------------------------------------


def test_reset_clears_steps() -> None:
    t = ErrorTracker(enabled=True)
    t.record_step(True)
    t.record_step(False)
    t.reset()
    assert t.total_steps == 0
    assert t.per_step_error_rate() == 0.0


def test_docstring_example_values() -> None:
    tracker = ErrorTracker(enabled=True)
    tracker.record_step(True)
    tracker.record_step(False, error="timeout")
    assert tracker.per_step_error_rate() == 0.5
    assert round(tracker.cumulative_failure_probability(steps=10), 4) == 0.999
