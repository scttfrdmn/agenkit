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
    BayesianOptimizer: Bayesian optimization for hyperparameters
    PromptOptimizer: Automated prompt optimization

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

from .ab_testing import ABResult, ABTest, ABVariant, SignificanceLevel, StatisticalTestType, calculate_sample_size
from .bayesian_optimizer import AcquisitionFunction, BayesianOptimizer
from .benchmarks import Benchmark, BenchmarkSuite
from .context_metrics import CompressionMetrics, ContextMetrics, LatencyMetric
from .core import EvaluationResult, Evaluator, Metric
from .optimizer import Optimizer, OptimizationResult, RandomSearchOptimizer, SearchSpace
from .prompt_optimizer import OptimizationStrategy, PromptOptimizationResult, PromptOptimizer
from .quality_metrics import AccuracyMetric, PrecisionRecallMetric, QualityMetrics
from .recorder import SessionRecorder, SessionReplay
from .regression import RegressionDetector

__all__ = [
    # A/B Testing
    "ABResult",
    "ABTest",
    "ABVariant",
    "AccuracyMetric",
    "AcquisitionFunction",
    # Bayesian Optimization
    "BayesianOptimizer",
    # Benchmarks
    "Benchmark",
    "BenchmarkSuite",
    "CompressionMetrics",
    # Context tracking
    "ContextMetrics",
    "EvaluationResult",
    "Evaluator",
    "LatencyMetric",
    # Core
    "Metric",
    # Optimization
    "OptimizationResult",
    "OptimizationStrategy",
    "Optimizer",
    "PrecisionRecallMetric",
    # Prompt Optimization
    "PromptOptimizationResult",
    "PromptOptimizer",
    # Quality measurement
    "QualityMetrics",
    "RandomSearchOptimizer",
    # Regression detection
    "RegressionDetector",
    "SearchSpace",
    # Session replay
    "SessionRecorder",
    "SessionReplay",
    "SignificanceLevel",
    "StatisticalTestType",
    "calculate_sample_size",
]
