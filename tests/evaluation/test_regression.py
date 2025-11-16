"""
Tests for regression detection.

Tests RegressionDetector, Severity, and comparison functions.
"""

import pytest
from agenkit.evaluation import EvaluationResult, RegressionDetector
from agenkit.evaluation.regression import Severity, Regression


def test_regression_detector_no_baseline():
    """Test detector with no baseline returns no regressions."""
    detector = RegressionDetector()

    result = EvaluationResult(
        evaluation_id="test-1",
        agent_name="test",
        accuracy=0.8
    )

    regressions = detector.detect(result)

    assert len(regressions) == 0


def test_regression_detector_no_degradation():
    """Test detector when performance is stable."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=0.9,
        quality_score=0.85
    )

    detector = RegressionDetector(baseline=baseline)

    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.91,  # Slightly better
        quality_score=0.86
    )

    regressions = detector.detect(current)

    assert len(regressions) == 0


def test_regression_detector_accuracy_degradation():
    """Test detector identifies accuracy degradation."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=0.9
    )

    detector = RegressionDetector(baseline=baseline)

    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.7  # 22% degradation (beyond 10% threshold)
    )

    regressions = detector.detect(current)

    assert len(regressions) == 1
    assert regressions[0].metric_name == "accuracy"
    assert regressions[0].baseline_value == 0.9
    assert regressions[0].current_value == 0.7
    assert regressions[0].degradation_percent > 20


def test_regression_detector_latency_degradation():
    """Test detector identifies latency degradation."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        avg_latency_ms=100.0
    )

    detector = RegressionDetector(baseline=baseline)

    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        avg_latency_ms=150.0  # 50% slower (beyond 20% threshold)
    )

    regressions = detector.detect(current)

    assert len(regressions) == 1
    assert regressions[0].metric_name == "latency"
    assert regressions[0].degradation_percent > 20


def test_regression_detector_multiple_regressions():
    """Test detector identifies multiple regressions."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=0.9,
        quality_score=0.85,
        avg_latency_ms=100.0
    )

    detector = RegressionDetector(baseline=baseline)

    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.7,  # Degraded
        quality_score=0.65,  # Degraded
        avg_latency_ms=200.0  # Degraded
    )

    regressions = detector.detect(current)

    assert len(regressions) == 3
    metric_names = {r.metric_name for r in regressions}
    assert "accuracy" in metric_names
    assert "quality" in metric_names
    assert "latency" in metric_names


def test_regression_detector_custom_thresholds():
    """Test detector with custom thresholds."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=0.9
    )

    # Very strict threshold
    detector = RegressionDetector(
        baseline=baseline,
        thresholds={"accuracy": 0.05}  # Only 5% degradation allowed
    )

    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.85  # 5.6% degradation
    )

    regressions = detector.detect(current)

    assert len(regressions) == 1


def test_regression_severity_calculation():
    """Test severity level calculation."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=1.0
    )

    detector = RegressionDetector(baseline=baseline)

    # Minor degradation (10-20%)
    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.85  # 15% degradation
    )

    regressions = detector.detect(current)
    assert regressions[0].severity == Severity.MINOR

    # Moderate degradation (20-50%)
    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.7  # 30% degradation
    )

    regressions = detector.detect(current)
    assert regressions[0].severity == Severity.MODERATE

    # Critical degradation (>50%)
    current = EvaluationResult(
        evaluation_id="current",
        agent_name="test",
        accuracy=0.4  # 60% degradation
    )

    regressions = detector.detect(current)
    assert regressions[0].severity == Severity.CRITICAL


def test_regression_detector_history():
    """Test detector stores history when requested."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=0.9
    )

    detector = RegressionDetector(baseline=baseline)

    result1 = EvaluationResult(
        evaluation_id="test-1",
        agent_name="test",
        accuracy=0.85
    )

    result2 = EvaluationResult(
        evaluation_id="test-2",
        agent_name="test",
        accuracy=0.82
    )

    detector.detect(result1, store_history=True)
    detector.detect(result2, store_history=True)

    assert len(detector.history) == 2


def test_regression_detector_trend():
    """Test trend calculation from history."""
    detector = RegressionDetector()

    # Add results showing degrading trend
    for i in range(5):
        result = EvaluationResult(
            evaluation_id=f"test-{i}",
            agent_name="test",
            accuracy=0.9 - (i * 0.05)  # Degrading: 0.9, 0.85, 0.8, 0.75, 0.7
        )
        detector.detect(result, store_history=True)

    trend = detector.get_trend("accuracy", window=5)

    assert trend is not None
    assert trend["direction"] == "degrading"
    assert trend["slope"] < 0


def test_regression_detector_compare_results():
    """Test comparing two evaluation results."""
    result_a = EvaluationResult(
        evaluation_id="a",
        agent_name="test",
        accuracy=0.9,
        avg_latency_ms=100.0
    )

    result_b = EvaluationResult(
        evaluation_id="b",
        agent_name="test",
        accuracy=0.85,
        avg_latency_ms=120.0
    )

    detector = RegressionDetector()
    comparison = detector.compare_results(result_a, result_b)

    assert "accuracy" in comparison
    assert comparison["accuracy"]["baseline"] == 0.9
    assert comparison["accuracy"]["current"] == 0.85
    assert comparison["accuracy"]["change"] < 0

    assert "latency" in comparison
    assert comparison["latency"]["change"] == 20.0


def test_regression_detector_clear_history():
    """Test clearing history."""
    detector = RegressionDetector()

    result = EvaluationResult(
        evaluation_id="test",
        agent_name="test",
        accuracy=0.9
    )

    detector.detect(result, store_history=True)
    assert len(detector.history) == 1

    detector.clear_history()
    assert len(detector.history) == 0


def test_regression_detector_summary():
    """Test getting detector summary."""
    baseline = EvaluationResult(
        evaluation_id="baseline",
        agent_name="test",
        accuracy=0.9
    )

    detector = RegressionDetector(baseline=baseline)

    summary = detector.get_summary()

    assert summary["has_baseline"] is True
    assert summary["baseline_id"] == "baseline"
    assert "thresholds" in summary


def test_regression_to_dict():
    """Test regression serialization."""
    regression = Regression(
        metric_name="accuracy",
        baseline_value=0.9,
        current_value=0.7,
        degradation_percent=22.2,
        severity=Severity.MODERATE
    )

    data = regression.to_dict()

    assert data["metric_name"] == "accuracy"
    assert data["baseline_value"] == 0.9
    assert data["current_value"] == 0.7
    assert data["severity"] == "moderate"
    assert "timestamp" in data


def test_regression_is_regression():
    """Test is_regression property."""
    # Actual regression
    regression = Regression(
        metric_name="accuracy",
        baseline_value=0.9,
        current_value=0.7,
        degradation_percent=22.2,
        severity=Severity.MODERATE
    )

    assert regression.is_regression is True

    # Improvement (negative degradation)
    improvement = Regression(
        metric_name="accuracy",
        baseline_value=0.7,
        current_value=0.9,
        degradation_percent=-22.2,
        severity=Severity.NONE
    )

    assert improvement.is_regression is False
