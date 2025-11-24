"""
Evaluation Metrics - Measure Agent Performance

Provides comprehensive metrics for evaluating agent performance:
- Success/failure tracking
- Quality scoring
- Cost tracking (integrates with budget.py)
- Time tracking
- Error analysis

Key use case: "How do you know a 30-hour agent succeeded?"
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import statistics


class SessionStatus(Enum):
    """Status of an evaluation session."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class MetricType(Enum):
    """Types of metrics that can be tracked."""

    SUCCESS_RATE = "success_rate"
    QUALITY_SCORE = "quality_score"
    COST = "cost"
    DURATION = "duration"
    ERROR_RATE = "error_rate"
    TASK_COMPLETION = "task_completion"
    CUSTOM = "custom"


@dataclass
class Metric:
    """A single metric measurement."""

    name: str
    value: float
    type: MetricType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            value=data["value"],
            type=MetricType(data["type"]),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvaluationResult:
    """Results from evaluating an agent session."""

    session_id: str
    agent_name: str
    status: SessionStatus
    start_time: str
    end_time: Optional[str] = None
    metrics: List[Metric] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metric(self, metric: Metric) -> None:
        """Add a metric to this result."""
        self.metrics.append(metric)

    def add_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record an error."""
        self.errors.append({
            "type": error_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a specific metric by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def get_metrics_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Get all metrics of a specific type."""
        return [m for m in self.metrics if m.type == metric_type]

    def duration_seconds(self) -> Optional[float]:
        """Calculate session duration in seconds."""
        if not self.end_time:
            return None

        start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
        return (end - start).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metrics": [m.to_dict() for m in self.metrics],
            "errors": self.errors,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationResult":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            agent_name=data["agent_name"],
            status=SessionStatus(data["status"]),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            metrics=[Metric.from_dict(m) for m in data.get("metrics", [])],
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "EvaluationResult":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


class MetricsCollector:
    """
    Collects and aggregates metrics across multiple evaluation sessions.

    Example:
        collector = MetricsCollector()

        # Add results from multiple runs
        collector.add_result(result1)
        collector.add_result(result2)

        # Get aggregated statistics
        stats = collector.get_statistics()
        print(f"Success rate: {stats['success_rate']:.2%}")
        print(f"Average cost: ${stats['avg_cost']:.2f}")
    """

    def __init__(self):
        self.results: List[EvaluationResult] = []

    def add_result(self, result: EvaluationResult) -> None:
        """Add an evaluation result."""
        self.results.append(result)

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate aggregate statistics across all results."""
        if not self.results:
            return {}

        # Success rate
        completed = sum(1 for r in self.results if r.status == SessionStatus.COMPLETED)
        success_rate = completed / len(self.results) if self.results else 0.0

        # Duration statistics
        durations = [r.duration_seconds() for r in self.results if r.duration_seconds() is not None]
        avg_duration = statistics.mean(durations) if durations else 0.0

        # Cost statistics (if available)
        costs = []
        for result in self.results:
            cost_metric = result.get_metric("total_cost")
            if cost_metric:
                costs.append(cost_metric.value)

        avg_cost = statistics.mean(costs) if costs else 0.0
        total_cost = sum(costs) if costs else 0.0

        # Quality scores (if available)
        quality_metrics = []
        for result in self.results:
            for metric in result.get_metrics_by_type(MetricType.QUALITY_SCORE):
                quality_metrics.append(metric.value)

        avg_quality = statistics.mean(quality_metrics) if quality_metrics else 0.0

        # Error rate
        total_errors = sum(len(r.errors) for r in self.results)
        error_rate = total_errors / len(self.results) if self.results else 0.0

        return {
            "total_sessions": len(self.results),
            "success_rate": success_rate,
            "completed": completed,
            "failed": sum(1 for r in self.results if r.status == SessionStatus.FAILED),
            "timeout": sum(1 for r in self.results if r.status == SessionStatus.TIMEOUT),
            "avg_duration_seconds": avg_duration,
            "avg_cost": avg_cost,
            "total_cost": total_cost,
            "avg_quality": avg_quality,
            "error_rate": error_rate,
            "total_errors": total_errors,
        }

    def get_success_rate(self) -> float:
        """Get overall success rate."""
        if not self.results:
            return 0.0
        completed = sum(1 for r in self.results if r.status == SessionStatus.COMPLETED)
        return completed / len(self.results)

    def get_results_by_status(self, status: SessionStatus) -> List[EvaluationResult]:
        """Get all results with a specific status."""
        return [r for r in self.results if r.status == status]

    def export_to_json(self, filepath: str) -> None:
        """Export all results to JSON file."""
        data = {
            "results": [r.to_dict() for r in self.results],
            "statistics": self.get_statistics(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def import_from_json(cls, filepath: str) -> "MetricsCollector":
        """Import results from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        collector = cls()
        for result_data in data.get("results", []):
            collector.add_result(EvaluationResult.from_dict(result_data))

        return collector


def create_quality_metric(name: str, score: float, max_score: float = 10.0, **metadata) -> Metric:
    """
    Helper to create a quality score metric.

    Args:
        name: Metric name
        score: Raw score
        max_score: Maximum possible score (default: 10.0)
        **metadata: Additional metadata

    Returns:
        Metric with normalized score (0.0-1.0)
    """
    normalized_score = min(score / max_score, 1.0)
    return Metric(
        name=name,
        value=normalized_score,
        type=MetricType.QUALITY_SCORE,
        metadata={"raw_score": score, "max_score": max_score, **metadata},
    )


def create_cost_metric(cost: float, currency: str = "USD", **metadata) -> Metric:
    """
    Helper to create a cost metric.

    Args:
        cost: Cost amount
        currency: Currency code (default: "USD")
        **metadata: Additional metadata

    Returns:
        Cost metric
    """
    return Metric(
        name="total_cost",
        value=cost,
        type=MetricType.COST,
        metadata={"currency": currency, **metadata},
    )


def create_duration_metric(duration_seconds: float, **metadata) -> Metric:
    """
    Helper to create a duration metric.

    Args:
        duration_seconds: Duration in seconds
        **metadata: Additional metadata

    Returns:
        Duration metric
    """
    return Metric(
        name="duration",
        value=duration_seconds,
        type=MetricType.DURATION,
        metadata={"duration_hours": duration_seconds / 3600, **metadata},
    )
