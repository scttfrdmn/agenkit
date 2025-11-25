/**
 * Quality metrics for agent evaluation.
 *
 * Measures task success, accuracy, and response quality.
 *
 * Example:
 * ```typescript
 * const metric = new AccuracyMetric();
 * const score = await metric.measure(
 *   agent,
 *   inputMsg,
 *   outputMsg,
 *   { expected: 'Paris' }
 * );
 * console.log(`Accuracy: ${score}`); // 0.0 or 1.0
 * ```
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Base interface for metrics.
 *
 * Metrics measure agent performance on specific dimensions.
 */
export interface Metric {
  /** Metric name */
  readonly name: string;

  /**
   * Measure metric for a single interaction.
   *
   * @param agent Agent being evaluated
   * @param inputMessage Input to agent
   * @param outputMessage Agent's response
   * @param context Optional context (e.g., expected output)
   * @returns Metric score
   */
  measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number>;

  /**
   * Aggregate multiple measurements.
   *
   * @param measurements List of measurement values
   * @returns Aggregated statistics
   */
  aggregate(measurements: number[]): Record<string, number>;
}

/**
 * Validator function type.
 */
export type Validator = (expected: string, actual: string) => boolean;

/**
 * Configuration for AccuracyMetric.
 */
export interface AccuracyMetricConfig {
  /** Custom validation function */
  validator?: Validator;
  /** Whether string matching is case-sensitive (default: false) */
  caseSensitive?: boolean;
}

/**
 * Measure task accuracy.
 *
 * Compares agent output to expected output to determine correctness.
 * Supports multiple validation methods:
 * - Exact string matching
 * - Substring matching (case-insensitive by default)
 * - Custom validator functions
 *
 * Returns 1.0 if correct, 0.0 if incorrect.
 */
export class AccuracyMetric implements Metric {
  readonly name = 'accuracy';
  private validator?: Validator;
  private caseSensitive: boolean;

  constructor(config: AccuracyMetricConfig = {}) {
    this.validator = config.validator;
    this.caseSensitive = config.caseSensitive || false;
  }

  /**
   * Measure accuracy for single interaction.
   *
   * @param agent Agent being evaluated
   * @param inputMessage Input to agent
   * @param outputMessage Agent's response
   * @param context Must contain "expected" key with expected output
   * @returns 1.0 if correct, 0.0 if incorrect
   */
  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    const ctx = context || {};

    // No expected output = always correct
    if (!ctx.expected) {
      return 1.0;
    }

    const expected = ctx.expected;
    const actual = String(outputMessage.content);

    // Custom validator
    if (this.validator) {
      return this.validator(String(expected), actual) ? 1.0 : 0.0;
    }

    // Callable validator
    if (typeof expected === 'function') {
      return expected(outputMessage) ? 1.0 : 0.0;
    }

    // String matching
    let expectedStr = String(expected);
    let actualStr = actual;

    if (!this.caseSensitive) {
      expectedStr = expectedStr.toLowerCase();
      actualStr = actualStr.toLowerCase();
    }

    return actualStr.includes(expectedStr) ? 1.0 : 0.0;
  }

  /**
   * Aggregate accuracy measurements.
   *
   * @param measurements List of 0.0/1.0 values
   * @returns Accuracy statistics
   */
  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return { accuracy: 0.0, total: 0, correct: 0, incorrect: 0 };
    }

    const total = measurements.length;
    const correct = measurements.reduce((sum, m) => sum + m, 0);

    return {
      accuracy: correct / total,
      total,
      correct,
      incorrect: total - correct,
    };
  }
}

/**
 * Quality dimension weights.
 */
export interface QualityWeights {
  relevance?: number;
  completeness?: number;
  coherence?: number;
  accuracy?: number;
}

/**
 * Configuration for QualityMetrics.
 */
export interface QualityMetricsConfig {
  /** Weights for each quality dimension */
  weights?: QualityWeights;
  /** Minimum acceptable score for each dimension (0-1) */
  thresholds?: QualityWeights;
}

/**
 * Comprehensive quality scoring.
 *
 * Evaluates multiple quality dimensions:
 * - Relevance: How relevant is response to query?
 * - Completeness: Does response answer all parts?
 * - Coherence: Is response logically structured?
 * - Accuracy: Is information factually correct?
 *
 * Uses rule-based heuristics to estimate quality.
 */
export class QualityMetrics implements Metric {
  readonly name = 'quality';
  private weights: Required<QualityWeights>;
  private thresholds: QualityWeights;

  constructor(config: QualityMetricsConfig = {}) {
    this.weights = {
      relevance: 0.3,
      completeness: 0.3,
      coherence: 0.2,
      accuracy: 0.2,
      ...config.weights,
    };
    this.thresholds = config.thresholds || {};
  }

  /**
   * Measure response quality.
   *
   * @param agent Agent being evaluated
   * @param inputMessage Input query
   * @param outputMessage Agent response
   * @param context Optional context with expected output
   * @returns Quality score (0.0 to 1.0)
   */
  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    const scores = await this.ruleBasedQuality(inputMessage, outputMessage, context);

    // Weighted average
    const totalScore =
      scores.relevance * this.weights.relevance +
      scores.completeness * this.weights.completeness +
      scores.coherence * this.weights.coherence +
      scores.accuracy * this.weights.accuracy;

    return totalScore;
  }

  /**
   * Rule-based quality assessment.
   *
   * Uses heuristics to estimate quality on multiple dimensions.
   */
  private async ruleBasedQuality(
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<Required<QualityWeights>> {
    const input = String(inputMessage.content);
    const output = String(outputMessage.content);

    return {
      relevance: this.measureRelevance(input, output),
      completeness: this.measureCompleteness(input, output),
      coherence: this.measureCoherence(output),
      accuracy: this.measureAccuracy(output, context),
    };
  }

  /**
   * Measure relevance (keyword overlap).
   */
  private measureRelevance(input: string, output: string): number {
    const inputWords = new Set(
      input
        .toLowerCase()
        .split(/\s+/)
        .filter(w => w.length > 3)
    );
    const outputWords = new Set(
      output
        .toLowerCase()
        .split(/\s+/)
        .filter(w => w.length > 3)
    );

    if (inputWords.size === 0) return 1.0;

    let overlap = 0;
    for (const word of inputWords) {
      if (outputWords.has(word)) overlap++;
    }

    return Math.min(overlap / inputWords.size, 1.0);
  }

  /**
   * Measure completeness (response length and structure).
   */
  private measureCompleteness(input: string, output: string): number {
    // Heuristic: output should be at least as long as input
    const inputLength = input.split(/\s+/).length;
    const outputLength = output.split(/\s+/).length;

    if (outputLength === 0) return 0.0;
    if (outputLength >= inputLength) return 1.0;

    return outputLength / inputLength;
  }

  /**
   * Measure coherence (sentence structure).
   */
  private measureCoherence(output: string): number {
    // Heuristic: proper sentences with punctuation
    const sentences = output.split(/[.!?]+/).filter(s => s.trim().length > 0);

    if (sentences.length === 0) return 0.0;

    // Check for basic sentence structure (capital letters, reasonable length)
    let coherentSentences = 0;
    for (const sentence of sentences) {
      const trimmed = sentence.trim();
      if (trimmed.length > 3 && /^[A-Z]/.test(trimmed)) {
        coherentSentences++;
      }
    }

    return coherentSentences / sentences.length;
  }

  /**
   * Measure accuracy (if expected output provided).
   */
  private measureAccuracy(
    output: string,
    context?: Record<string, unknown>
  ): number {
    if (!context || !context.expected) {
      // No ground truth, assume accurate
      return 1.0;
    }

    const expected = String(context.expected).toLowerCase();
    const actual = output.toLowerCase();

    return actual.includes(expected) ? 1.0 : 0.0;
  }

  /**
   * Aggregate quality measurements.
   *
   * @param measurements List of quality scores
   * @returns Quality statistics
   */
  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return { mean: 0.0, min: 0.0, max: 0.0, total: 0 };
    }

    const sum = measurements.reduce((a, b) => a + b, 0);
    const mean = sum / measurements.length;
    const min = Math.min(...measurements);
    const max = Math.max(...measurements);

    return {
      mean,
      min,
      max,
      total: measurements.length,
    };
  }
}

/**
 * Latency metric for measuring response time.
 */
export class LatencyMetric implements Metric {
  readonly name = 'latency';

  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    // Latency should be measured externally and passed in context
    if (context && typeof context.latency === 'number') {
      return context.latency;
    }

    // If not provided, measure now
    const start = performance.now();
    await agent.process(inputMessage);
    return performance.now() - start;
  }

  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return { mean: 0.0, min: 0.0, max: 0.0, p50: 0.0, p95: 0.0, p99: 0.0, total: 0 };
    }

    const sorted = [...measurements].sort((a, b) => a - b);
    const sum = measurements.reduce((a, b) => a + b, 0);
    const mean = sum / measurements.length;

    const p50 = sorted[Math.floor(measurements.length * 0.5)];
    const p95 = sorted[Math.floor(measurements.length * 0.95)];
    const p99 = sorted[Math.floor(measurements.length * 0.99)];

    return {
      mean,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      p50,
      p95,
      p99,
      total: measurements.length,
    };
  }
}

/**
 * Evaluate agent on multiple metrics.
 *
 * @param agent Agent to evaluate
 * @param testCases Test cases with input and expected output
 * @param metrics Metrics to compute
 * @returns Evaluation results
 */
export async function evaluateAgent(
  agent: Agent,
  testCases: Array<{ input: Message; expected?: string }>,
  metrics: Metric[]
): Promise<EvaluationResult> {
  const metricMeasurements = new Map<string, number[]>();

  for (const metric of metrics) {
    metricMeasurements.set(metric.name, []);
  }

  for (const testCase of testCases) {
    const startTime = performance.now();
    const output = await agent.process(testCase.input);
    const latency = performance.now() - startTime;

    const context = {
      expected: testCase.expected,
      latency,
    };

    for (const metric of metrics) {
      const score = await metric.measure(agent, testCase.input, output, context);
      metricMeasurements.get(metric.name)!.push(score);
    }
  }

  const results: Record<string, Record<string, number>> = {};
  for (const metric of metrics) {
    const measurements = metricMeasurements.get(metric.name)!;
    results[metric.name] = metric.aggregate(measurements);
  }

  return {
    agentName: agent.name,
    totalTests: testCases.length,
    metrics: results,
  };
}

/**
 * Evaluation results.
 */
export interface EvaluationResult {
  agentName: string;
  totalTests: number;
  metrics: Record<string, Record<string, number>>;
}
