/// Evaluation framework for Zig
///
/// This module provides comprehensive evaluation infrastructure for AI agents,
/// including metrics collection, quality assessment, session recording,
/// and regression detection.
///
/// Usage:
/// ```zig
/// const evaluation = @import("evaluation/mod.zig");
///
/// // Create test cases
/// const test_case = try evaluation.TestCase.initExact(allocator, "input", "expected");
///
/// // Set up metrics
/// const accuracy = try evaluation.AccuracyMetric.init(allocator, true);
/// const metrics = [_]evaluation.Metric{ accuracy.asMetric() };
///
/// // Evaluate agent
/// const evaluator = try evaluation.Evaluator.init(allocator, agent, &metrics);
/// const result = try evaluator.evaluate(&test_cases, "session-1");
/// ```
const std = @import("std");

// Core evaluation types
pub const core = @import("core.zig");
pub const TestCase = core.TestCase;
pub const ErrorRecord = core.ErrorRecord;
pub const EvaluationResult = core.EvaluationResult;
pub const Metric = core.Metric;
pub const Evaluator = core.Evaluator;
pub const EvaluationError = core.EvaluationError;

// Metrics collection
pub const metrics = @import("metrics.zig");
pub const SessionStatus = metrics.SessionStatus;
pub const MetricType = metrics.MetricType;
pub const MetricMeasurement = metrics.MetricMeasurement;
pub const SessionResult = metrics.SessionResult;
pub const Statistics = metrics.Statistics;
pub const MetricsCollector = metrics.MetricsCollector;

// Quality metrics
pub const quality = @import("quality_metrics.zig");
pub const AccuracyMetric = quality.AccuracyMetric;
pub const QualityMetric = quality.QualityMetric;
pub const QualityCriteria = quality.QualityCriteria;
pub const PrecisionRecallMetric = quality.PrecisionRecallMetric;
pub const ClassificationResult = quality.ClassificationResult;

// Session recording
pub const recorder = @import("recorder.zig");
pub const Interaction = recorder.Interaction;
pub const SessionTrace = recorder.SessionTrace;
pub const SessionRecorder = recorder.SessionRecorder;
pub const RecorderStats = recorder.RecorderStats;
pub const SessionReplay = recorder.SessionReplay;

// Regression detection
pub const regression = @import("regression.zig");
pub const Severity = regression.Severity;
pub const Regression = regression.Regression;
pub const RegressionConfig = regression.RegressionConfig;
pub const BaselineMeasurement = regression.BaselineMeasurement;
pub const RegressionDetector = regression.RegressionDetector;

// Context metrics (extreme-scale evaluation)
pub const context_metrics = @import("context_metrics.zig");
pub const ContextMetric = context_metrics.ContextMetric;
pub const CompressionStats = context_metrics.CompressionStats;
pub const CompressionMetric = context_metrics.CompressionMetric;
pub const LatencyMetric = context_metrics.LatencyMetric;

// Benchmarks (standardized test suites)
pub const benchmarks = @import("benchmarks.zig");
pub const Benchmark = benchmarks.Benchmark;
pub const SimpleQABenchmark = benchmarks.SimpleQABenchmark;
pub const NeedleInHaystackBenchmark = benchmarks.NeedleInHaystackBenchmark;
pub const ExtremeScaleBenchmark = benchmarks.ExtremeScaleBenchmark;
pub const InformationRetentionBenchmark = benchmarks.InformationRetentionBenchmark;
pub const BenchmarkSuite = benchmarks.BenchmarkSuite;

// Optimization (hyperparameter tuning)
pub const optimizer = @import("optimizer.zig");
pub const ParameterType = optimizer.ParameterType;
pub const ParameterBounds = optimizer.ParameterBounds;
pub const Parameter = optimizer.Parameter;
pub const ConfigValue = optimizer.ConfigValue;
pub const SearchSpace = optimizer.SearchSpace;
pub const OptimizationStep = optimizer.OptimizationStep;
pub const OptimizationResult = optimizer.OptimizationResult;
pub const RandomSearchOptimizer = optimizer.RandomSearchOptimizer;

// A/B Testing (statistical significance)
pub const ab_testing = @import("ab_testing.zig");
pub const StatisticalTestType = ab_testing.StatisticalTestType;
pub const SignificanceLevel = ab_testing.SignificanceLevel;
pub const ABVariant = ab_testing.ABVariant;
pub const ABResult = ab_testing.ABResult;
pub const ABTest = ab_testing.ABTest;

// Bayesian Optimization (GP-based tuning)
pub const bayesian_optimizer = @import("bayesian_optimizer.zig");
pub const AcquisitionFunction = bayesian_optimizer.AcquisitionFunction;
pub const PerformanceEstimate = bayesian_optimizer.PerformanceEstimate;
pub const BayesianConfig = bayesian_optimizer.BayesianConfig;
pub const BayesianOptimizer = bayesian_optimizer.BayesianOptimizer;

// Prompt Optimization (automated prompt engineering)
pub const prompt_optimizer = @import("prompt_optimizer.zig");
pub const OptimizationStrategy = prompt_optimizer.OptimizationStrategy;
pub const PromptConfig = prompt_optimizer.PromptConfig;
pub const PromptScores = prompt_optimizer.PromptScores;
pub const OptimizationEntry = prompt_optimizer.OptimizationEntry;
pub const PromptOptimizationResult = prompt_optimizer.PromptOptimizationResult;
pub const AgentFactory = prompt_optimizer.AgentFactory;
pub const EvaluationFn = prompt_optimizer.EvaluationFn;
pub const PromptOptimizer = prompt_optimizer.PromptOptimizer;

// Error tracking (per-step error rate + failure compounding)
pub const error_tracker = @import("error_tracker.zig");
pub const StepResult = error_tracker.StepResult;
pub const ErrorTracker = error_tracker.ErrorTracker;

test {
    std.testing.refAllDecls(@This());
}
