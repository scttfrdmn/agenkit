"""
Regression detection for agent quality monitoring.

Detects performance degradation over time by comparing
current results to baseline and historical results.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from .core import EvaluationResult


class Severity(Enum):
    """Regression severity levels."""
    NONE = "none"
    MINOR = "minor"        # <10% degradation
    MODERATE = "moderate"  # 10-20% degradation
    MAJOR = "major"        # 20-50% degradation
    CRITICAL = "critical"  # >50% degradation


@dataclass
class Regression:
    """
    Detected regression in agent performance.

    Contains information about what degraded and by how much.
    """

    metric_name: str
    baseline_value: float
    current_value: float
    degradation_percent: float
    severity: Severity
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_regression(self) -> bool:
        """Check if this is a real regression (not improvement)."""
        return self.degradation_percent > 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "degradation_percent": self.degradation_percent,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


class RegressionDetector:
    """
    Detect performance regressions by comparing results.

    Monitors agent quality over time and alerts when performance
    degrades beyond acceptable thresholds.

    Example:
        >>> detector = RegressionDetector()
        >>> detector.set_baseline(baseline_result)
        >>>
        >>> # Later, after changes
        >>> regressions = detector.detect(current_result)
        >>> if regressions:
        ...     print(f"Found {len(regressions)} regressions!")
        ...     for r in regressions:
        ...         print(f"  {r.metric_name}: {r.degradation_percent:.1f}% worse")
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        baseline: Optional[EvaluationResult] = None
    ):
        """
        Initialize regression detector.

        Args:
            thresholds: Acceptable degradation per metric (default 10%)
            baseline: Baseline evaluation result to compare against
        """
        self.thresholds = thresholds or {
            "accuracy": 0.10,      # 10% degradation threshold
            "quality": 0.10,
            "latency": 0.20,       # 20% slower acceptable
            "context_length": 0.30  # 30% larger context acceptable
        }
        self.baseline = baseline
        self.history: List[EvaluationResult] = []

    def set_baseline(self, result: EvaluationResult) -> None:
        """
        Set baseline for comparison.

        Args:
            result: Evaluation result to use as baseline
        """
        self.baseline = result

    def detect(
        self,
        result: EvaluationResult,
        store_history: bool = True
    ) -> List[Regression]:
        """
        Detect regressions in evaluation result.

        Compares current result to baseline and identifies metrics
        that have degraded beyond acceptable thresholds.

        Args:
            result: Current evaluation result
            store_history: Whether to store result in history

        Returns:
            List of detected regressions (empty if no regressions)
        """
        if store_history:
            self.history.append(result)

        if self.baseline is None:
            # No baseline = no regressions
            return []

        regressions = []

        # Check accuracy
        if result.accuracy is not None and self.baseline.accuracy is not None:
            reg = self._check_metric(
                "accuracy",
                self.baseline.accuracy,
                result.accuracy,
                higher_is_better=True
            )
            if reg:
                regressions.append(reg)

        # Check quality_score
        if result.quality_score is not None and self.baseline.quality_score is not None:
            reg = self._check_metric(
                "quality",
                self.baseline.quality_score,
                result.quality_score,
                higher_is_better=True
            )
            if reg:
                regressions.append(reg)

        # Check latency (lower is better)
        if result.avg_latency_ms is not None and self.baseline.avg_latency_ms is not None:
            reg = self._check_metric(
                "latency",
                self.baseline.avg_latency_ms,
                result.avg_latency_ms,
                higher_is_better=False
            )
            if reg:
                regressions.append(reg)

        # Check context length
        if result.context_length is not None and self.baseline.context_length is not None:
            reg = self._check_metric(
                "context_length",
                self.baseline.context_length,
                result.context_length,
                higher_is_better=False
            )
            if reg:
                regressions.append(reg)

        # Check compression ratio (higher is better)
        if result.compression_ratio is not None and self.baseline.compression_ratio is not None:
            reg = self._check_metric(
                "compression_ratio",
                self.baseline.compression_ratio,
                result.compression_ratio,
                higher_is_better=True
            )
            if reg:
                regressions.append(reg)

        return regressions

    def _check_metric(
        self,
        name: str,
        baseline: float,
        current: float,
        higher_is_better: bool = True
    ) -> Optional[Regression]:
        """
        Check single metric for regression.

        Args:
            name: Metric name
            baseline: Baseline value
            current: Current value
            higher_is_better: Whether higher values are better

        Returns:
            Regression if detected, None otherwise
        """
        if baseline == 0:
            # Avoid division by zero
            if current == 0:
                return None
            degradation = 1.0 if higher_is_better else -1.0
        else:
            if higher_is_better:
                # For accuracy, quality: lower is worse
                degradation = (baseline - current) / baseline
            else:
                # For latency, context_length: higher is worse
                degradation = (current - baseline) / baseline

        # Check if exceeds threshold
        threshold = self.thresholds.get(name, 0.10)
        if degradation > threshold:
            severity = self._calculate_severity(degradation)
            return Regression(
                metric_name=name,
                baseline_value=baseline,
                current_value=current,
                degradation_percent=degradation * 100,
                severity=severity,
                context={
                    "threshold_percent": threshold * 100,
                    "higher_is_better": higher_is_better
                }
            )

        return None

    def _calculate_severity(self, degradation: float) -> Severity:
        """
        Calculate severity based on degradation amount.

        Args:
            degradation: Degradation as fraction (0.1 = 10%)

        Returns:
            Severity level
        """
        if degradation < 0.10:
            return Severity.NONE
        elif degradation < 0.20:
            return Severity.MINOR
        elif degradation < 0.50:
            return Severity.MODERATE
        else:
            return Severity.CRITICAL

    def get_trend(
        self,
        metric_name: str,
        window: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Get trend for metric over recent history.

        Args:
            metric_name: Metric to analyze
            window: Number of recent results to analyze

        Returns:
            Trend statistics (slope, direction, variance)
        """
        if len(self.history) < 2:
            return None

        # Get recent results
        recent = self.history[-window:]

        # Extract metric values
        values = []
        for result in recent:
            if metric_name == "accuracy" and result.accuracy is not None:
                values.append(result.accuracy)
            elif metric_name == "quality" and result.quality_score is not None:
                values.append(result.quality_score)
            elif metric_name == "latency" and result.avg_latency_ms is not None:
                values.append(result.avg_latency_ms)
            elif metric_name == "context_length" and result.context_length is not None:
                values.append(result.context_length)

        if len(values) < 2:
            return None

        # Calculate trend
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        # Linear regression slope
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0

        # Variance
        variance = sum((v - y_mean) ** 2 for v in values) / n

        return {
            "metric": metric_name,
            "slope": slope,
            "direction": "improving" if slope > 0 else "degrading" if slope < 0 else "stable",
            "variance": variance,
            "current": values[-1],
            "mean": y_mean,
            "window_size": n
        }

    def compare_results(
        self,
        result_a: EvaluationResult,
        result_b: EvaluationResult
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare two evaluation results.

        Args:
            result_a: First result (baseline)
            result_b: Second result (comparison)

        Returns:
            Dictionary of metric comparisons
        """
        comparisons = {}

        # Compare accuracy
        if result_a.accuracy is not None and result_b.accuracy is not None:
            comparisons["accuracy"] = {
                "baseline": result_a.accuracy,
                "current": result_b.accuracy,
                "change": result_b.accuracy - result_a.accuracy,
                "change_percent": ((result_b.accuracy - result_a.accuracy) / result_a.accuracy * 100)
                                 if result_a.accuracy != 0 else 0
            }

        # Compare quality
        if result_a.quality_score is not None and result_b.quality_score is not None:
            comparisons["quality"] = {
                "baseline": result_a.quality_score,
                "current": result_b.quality_score,
                "change": result_b.quality_score - result_a.quality_score,
                "change_percent": ((result_b.quality_score - result_a.quality_score) / result_a.quality_score * 100)
                                 if result_a.quality_score != 0 else 0
            }

        # Compare latency
        if result_a.avg_latency_ms is not None and result_b.avg_latency_ms is not None:
            comparisons["latency"] = {
                "baseline": result_a.avg_latency_ms,
                "current": result_b.avg_latency_ms,
                "change": result_b.avg_latency_ms - result_a.avg_latency_ms,
                "change_percent": ((result_b.avg_latency_ms - result_a.avg_latency_ms) / result_a.avg_latency_ms * 100)
                                 if result_a.avg_latency_ms != 0 else 0
            }

        return comparisons

    def clear_history(self) -> None:
        """Clear evaluation history."""
        self.history = []

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of detector state.

        Returns:
            Summary with baseline info and history count
        """
        return {
            "has_baseline": self.baseline is not None,
            "baseline_id": self.baseline.evaluation_id if self.baseline else None,
            "history_count": len(self.history),
            "thresholds": self.thresholds
        }
