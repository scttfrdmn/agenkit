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
    PatternBenchmark: Pattern-specific benchmarks from YAML specs
    PatternBenchmarkSuite: Suite of all 18 pattern benchmarks
    YAMLBenchmarkLoader: Load benchmarks from YAML specifications
    ContextMetrics: Track context length and compression
    QualityMetrics: Measure response quality
    RegressionDetector: Detect performance degradation
    SessionRecorder: Record sessions for replay
    BayesianOptimizer: Bayesian optimization for hyperparameters
    PromptOptimizer: Automated prompt optimization

Example:
    >>> from agenkit.evaluation import Evaluator, PatternBenchmarkSuite
    >>>
    >>> # Create evaluator
    >>> evaluator = Evaluator(agent)
    >>>
    >>> # Run pattern benchmarks
    >>> suite = PatternBenchmarkSuite.from_yaml_specs("tests/cross_language/specs")
    >>> reflection = suite.get_benchmark("reflection")
    >>> results = await suite.run_benchmark(reflection, agent_factory)
    >>>
    >>> # Check for regressions
    >>> if results['summary']['passed'] < results['summary']['total']:
    >>>     print("Pattern implementation issues detected!")
"""

from .ab_testing import (
    ABResult,
    ABTest,
    ABVariant,
    SignificanceLevel,
    StatisticalTestType,
    calculate_sample_size,
)

# Bayesian optimizer requires sklearn - make it optional
try:
    from .bayesian_optimizer import AcquisitionFunction, BayesianOptimizer
except ImportError:
    # sklearn not installed - Bayesian optimization unavailable
    AcquisitionFunction = None  # type: ignore
    BayesianOptimizer = None  # type: ignore

from .benchmarks import Benchmark, BenchmarkSuite
from .context_metrics import CompressionMetrics, ContextMetrics, LatencyMetric
from .core import EvaluationResult, Evaluator, Metric
from .optimizer import OptimizationResult, Optimizer, RandomSearchOptimizer, SearchSpace
from .pattern_benchmarks import PatternBenchmark, PatternBenchmarkSuite, YAMLBenchmarkLoader
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
    # Pattern Benchmarks
    "PatternBenchmark",
    "PatternBenchmarkSuite",
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
    "YAMLBenchmarkLoader",
    "calculate_sample_size",
]
