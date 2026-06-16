/**
 * Evaluation Framework for AgentKit
 *
 * Comprehensive evaluation tools for agent performance monitoring,
 * quality assessment, regression detection, and A/B testing.
 *
 * ## Core Modules
 *
 * ### Core (Evaluator and Base Types)
 * - `Evaluator`: Run agents against test suites and collect metrics
 * - `EvaluationResult`: Container for evaluation results and statistics
 * - `Metric`: Base interface for custom metrics
 *
 * ### Metrics (Session Tracking and Aggregation)
 * - `SessionResult`: Track individual agent sessions
 * - `MetricsCollector`: Aggregate metrics across sessions
 * - `MetricType`: Categorize metrics (success rate, quality, cost, duration)
 * - `SessionStatus`: Track session lifecycle
 *
 * ### Quality Metrics (Quality Assessment)
 * - `AccuracyMetric`: Binary correctness measurement
 * - `QualityMetrics`: Multi-dimensional quality scoring
 * - `PrecisionRecallMetric`: Classification performance
 * - `LLMJudgeMetric`: LLM-based quality evaluation
 *
 * ### Recorder (Session Recording and Replay)
 * - `SessionRecorder`: Record agent interactions
 * - `SessionReplay`: Replay recorded sessions
 * - `FileRecordingStorage`: Persistent file-based storage
 * - `InMemoryRecordingStorage`: In-memory storage for testing
 *
 * ### Regression (Quality Monitoring)
 * - `RegressionDetector`: Detect performance degradation
 * - `Severity`: Regression severity levels
 * - `Trend`: Performance trend analysis
 *
 * ### Benchmarks (Standard Benchmarks)
 * - `BenchmarkSuite`: Standard benchmark collections
 * - Predefined benchmarks for common tasks
 *
 * ### Context Metrics (Contextual Evaluation)
 * - `ContextRelevanceMetric`: Measure context relevance
 * - `GroundednessMetric`: Check factual grounding
 *
 * ### A/B Testing (Variant Comparison)
 * - `ABTest`: Compare agent variants
 * - `Variant`: Agent variant configuration
 * - Statistical significance testing
 *
 * ### Optimization (Parameter Tuning)
 * - `Optimizer`: Generic parameter optimization
 * - `BayesianOptimizer`: Bayesian optimization for agent tuning
 * - `PromptOptimizer`: Automated prompt optimization
 *
 * ## Example Usage
 *
 * ```typescript
 * import {
 *   Evaluator,
 *   AccuracyMetric,
 *   QualityMetrics,
 *   SessionRecorder,
 *   RegressionDetector,
 *   MetricsCollector,
 * } from '@agenkit/evaluation';
 *
 * // 1. Basic Evaluation
 * const evaluator = new Evaluator(
 *   agent,
 *   [new AccuracyMetric(), new QualityMetrics()],
 *   'my-eval'
 * );
 * const result = await evaluator.evaluate(testCases, 'run-001');
 *
 * // 2. Session Recording
 * const recorder = new SessionRecorder(new FileRecordingStorage('./recordings'));
 * const wrappedAgent = recorder.wrap(agent);
 * await wrappedAgent.process(message, 'session-123');
 * await recorder.finalizeSession('session-123');
 *
 * // 3. Regression Detection
 * const detector = new RegressionDetector();
 * detector.setBaseline(baselineResult);
 * const regressions = detector.detect(currentResult);
 *
 * // 4. Metrics Collection
 * const collector = new MetricsCollector();
 * collector.addSession(sessionResult);
 * const aggregates = collector.getAggregatedMetrics();
 * ```
 */

// Core evaluation
export {
  Evaluator,
  type EvaluationResult,
  type TestCase,
  getSuccessRate,
  resultToDict,
  evaluateAgent,
} from './core';

// Metrics tracking and aggregation
export {
  SessionStatus,
  MetricType,
  type MetricMeasurement,
  type ErrorRecord,
  type AggregatedMetric,
  SessionResult,
  MetricsCollector,
  createMetricMeasurement,
  createErrorRecord,
} from './metrics';

// Quality metrics
export {
  type Metric as QualityMetric,
  type Validator,
  type AccuracyMetricConfig,
  AccuracyMetric,
  type QualityMetricsConfig,
  QualityMetrics,
} from './quality-metrics';

// Session recording and replay
export {
  type InteractionRecord,
  type MessageDict,
  type SessionRecording,
  getSessionDuration,
  getTotalLatency,
  type RecordingStorage,
  FileRecordingStorage,
  InMemoryRecordingStorage,
  SessionRecorder,
  type ReplayResults,
  type ReplayInteraction,
  type ReplayComparison,
  type OutputDifference,
  SessionReplay,
  interactionRecordToDict,
  interactionRecordFromDict,
  sessionRecordingToDict,
  sessionRecordingFromDict,
} from './recorder';

// Regression detection
export {
  Severity,
  type Regression,
  isRegression,
  regressionToDict,
  type MetricComparison,
  type TrendStats,
  type RegressionDetectorConfig,
  RegressionDetector,
} from './regression';

// Benchmarks
export {
  type Benchmark,
  type TestCase as BenchmarkTestCase,
  SimpleQABenchmark,
  ReasoningBenchmark,
  type NeedleInHaystackConfig,
  NeedleInHaystackBenchmark,
  CodeGenerationBenchmark,
  ExtremeScaleBenchmark,
  InformationRetentionBenchmark,
  BenchmarkSuite,
  type SuiteResult,
  getAllBenchmarks,
  getBenchmarkByName,
  runBenchmark,
} from './benchmarks';

// Pattern Benchmarks
export {
  PatternBenchmark,
  YAMLBenchmarkLoader,
  PatternBenchmarkSuite,
  type PatternTestCase,
  type TestCaseResult,
  type BenchmarkResult,
  type SuiteResult as PatternSuiteResult,
} from './pattern-benchmarks';

// Context metrics
export {
  type AgentWithContextStats,
  ContextMetrics,
  type CompressionStats,
  createCompressionStats,
  compressionStatsToDict,
  CompressionMetrics,
} from './context-metrics';

// A/B testing
export {
  SignificanceLevel,
  ABVariant,
  type ABTestResult,
  type TestCase as ABTestCase,
  type ABTestConfig,
  type RunOptions as ABTestRunOptions,
  ABTest,
} from './ab-testing';

// Optimization
export {
  type ParameterType,
  type ParameterSpec,
  type AgentFactory,
  type ObjectiveFunction,
  SearchSpace,
  type OptimizationResult,
  getOptimizationDuration,
  getOptimizationImprovement,
  optimizationResultToDict,
  Optimizer,
} from './optimizer';

export {
  type AcquisitionFunction,
  type BayesianOptimizerConfig,
  BayesianOptimizer,
} from './bayesian-optimizer';

export {
  type OptimizationStrategy,
  type PromptAgentFactory,
  type PromptEvaluation,
  type PromptOptimizationResult,
  getPromptOptimizationDuration,
  promptOptimizationResultToDict,
  type PromptOptimizerConfig,
  type GeneticConfig,
  PromptOptimizer,
} from './prompt-optimizer';

/**
 * Helper functions for creating common metrics.
 */

/**
 * Create a quality metric measurement.
 *
 * @param name Metric name
 * @param score Score value (0.0-10.0 or normalized)
 * @param maxScore Maximum possible score (default: 1.0)
 * @param metadata Optional metadata
 * @returns Metric measurement
 */
export function createQualityMetric(
  name: string,
  score: number,
  maxScore: number = 1.0,
  metadata?: Record<string, unknown>
): import('./metrics').MetricMeasurement {
  const { createMetricMeasurement, MetricType } = require('./metrics');
  return createMetricMeasurement(
    name,
    score / maxScore,
    MetricType.QualityScore,
    metadata
  );
}

/**
 * Create a cost metric measurement.
 *
 * @param cost Cost value
 * @param currency Currency code (e.g., "USD")
 * @param metadata Optional metadata (e.g., tokens used)
 * @returns Metric measurement
 */
export function createCostMetric(
  cost: number,
  currency: string = 'USD',
  metadata?: Record<string, unknown>
): import('./metrics').MetricMeasurement {
  const { createMetricMeasurement, MetricType } = require('./metrics');
  return createMetricMeasurement('total_cost', cost, MetricType.Cost, {
    currency,
    ...metadata,
  });
}

/**
 * Create a duration metric measurement.
 *
 * @param durationSeconds Duration in seconds
 * @param metadata Optional metadata
 * @returns Metric measurement
 */
export function createDurationMetric(
  durationSeconds: number,
  metadata?: Record<string, unknown>
): import('./metrics').MetricMeasurement {
  const { createMetricMeasurement, MetricType } = require('./metrics');
  return createMetricMeasurement(
    'duration',
    durationSeconds,
    MetricType.Duration,
    metadata
  );
}

/**
 * Create a success rate metric measurement.
 *
 * @param success Whether the task succeeded
 * @param metadata Optional metadata
 * @returns Metric measurement
 */
export function createSuccessMetric(
  success: boolean,
  metadata?: Record<string, unknown>
): import('./metrics').MetricMeasurement {
  const { createMetricMeasurement, MetricType } = require('./metrics');
  return createMetricMeasurement(
    'success',
    success ? 1.0 : 0.0,
    MetricType.SuccessRate,
    metadata
  );
}
