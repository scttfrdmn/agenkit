"""
Evaluation framework for measuring agent quality and performance.

This package provides comprehensive evaluation capabilities for autonomous agents,
with special focus on extreme-scale context evaluation (1M-25M+ tokens) for
systems like endless.

Classes:
    Metric: Base class for evaluation metrics
    Evaluator: Core evaluation orchestrator
    Benchmark: Standard test interface
    BenchmarkSuite: Collection of benchmarks
    ContextMetrics: Track context length and compression
    QualityMetrics: Measure response quality
    RegressionDetector: Detect performance degradation
    SessionRecorder: Record sessions for replay

Example:
    >>> from agenkit.evaluation import Evaluator, BenchmarkSuite
    >>>
    >>> # Create evaluator
    >>> evaluator = Evaluator(agent)
    >>>
    >>> # Run benchmarks
    >>> suite = BenchmarkSuite.extreme_scale()
    >>> results = await evaluator.evaluate(suite)
    >>>
    >>> # Check for regressions
    >>> if results.quality_score < 0.85:
    >>>     print("Quality degradation detected!")
"""

from .core import Metric, Evaluator, EvaluationResult
from .benchmarks import Benchmark, BenchmarkSuite
from .context_metrics import ContextMetrics, CompressionMetrics, LatencyMetric
from .quality_metrics import QualityMetrics, AccuracyMetric, PrecisionRecallMetric
from .regression import RegressionDetector
from .recorder import SessionRecorder, SessionReplay

__all__ = [
    # Core
    "Metric",
    "Evaluator",
    "EvaluationResult",

    # Benchmarks
    "Benchmark",
    "BenchmarkSuite",

    # Context tracking
    "ContextMetrics",
    "CompressionMetrics",
    "LatencyMetric",

    # Quality measurement
    "QualityMetrics",
    "AccuracyMetric",
    "PrecisionRecallMetric",

    # Regression detection
    "RegressionDetector",

    # Session replay
    "SessionRecorder",
    "SessionReplay",
]
