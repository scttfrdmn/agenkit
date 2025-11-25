/**
 * A/B Testing Framework for Agent Evaluation
 *
 * This module provides statistical A/B testing capabilities for comparing agent
 * performance with proper significance testing.
 *
 * Key Features:
 * - Statistical significance testing (t-test)
 * - Effect size calculation (Cohen's d)
 * - Confidence intervals
 * - Automated experiment orchestration
 *
 * Example:
 * ```typescript
 * const abTest = new ABTest({
 *   name: "agent_comparison",
 *   controlAgent: agentV1,
 *   treatmentAgent: agentV2,
 *   metrics: ["accuracy", "latency"]
 * });
 *
 * const results = await abTest.run(testCases, { sampleSize: 100 });
 * const accuracyResult = results.accuracy;
 *
 * if (accuracyResult.isSignificant) {
 *   console.log(`Winner: ${accuracyResult.winner}`);
 *   console.log(`Improvement: ${accuracyResult.improvementPercent.toFixed(1)}%`);
 * }
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/** Statistical significance levels */
export enum SignificanceLevel {
  /** 99.9% confidence */
  P_0_001 = 0.001,
  /** 99% confidence */
  P_0_01 = 0.01,
  /** 95% confidence (default) */
  P_0_05 = 0.05,
  /** 90% confidence */
  P_0_10 = 0.10,
}

/**
 * Represents a variant in an A/B test.
 *
 * Tracks samples and calculates basic statistics.
 */
export class ABVariant {
  readonly name: string;
  readonly agent: Agent;
  readonly samples: number[];
  readonly metadata: Record<string, unknown>;

  constructor(name: string, agent: Agent, metadata: Record<string, unknown> = {}) {
    this.name = name;
    this.agent = agent;
    this.samples = [];
    this.metadata = metadata;
  }

  /**
   * Add a measurement sample.
   */
  addSample(value: number): void {
    this.samples.push(value);
  }

  /**
   * Mean of samples.
   */
  get mean(): number {
    if (this.samples.length === 0) return 0.0;
    return this.samples.reduce((a, b) => a + b, 0) / this.samples.length;
  }

  /**
   * Standard deviation of samples.
   */
  get std(): number {
    if (this.samples.length <= 1) return 0.0;
    const mean = this.mean;
    const squaredDiffs = this.samples.map(x => Math.pow(x - mean, 2));
    const variance = squaredDiffs.reduce((a, b) => a + b, 0) / (this.samples.length - 1);
    return Math.sqrt(variance);
  }

  /**
   * Number of samples.
   */
  get sampleSize(): number {
    return this.samples.length;
  }
}

/**
 * Results of an A/B test with statistical analysis.
 */
export interface ABTestResult {
  /** Experiment name */
  experimentName: string;
  /** Control variant */
  controlVariant: ABVariant;
  /** Treatment variant */
  treatmentVariant: ABVariant;
  /** Metric being compared */
  metricName: string;
  /** P-value from statistical test */
  pValue: number;
  /** Significance level threshold */
  significanceLevel: SignificanceLevel;
  /** Effect size (Cohen's d) */
  effectSize: number;
  /** Confidence interval for difference */
  confidenceInterval: [number, number];
  /** Timestamp of test */
  timestamp: string;
  /** Whether result is statistically significant */
  isSignificant: boolean;
  /** Winner variant name (null if not significant) */
  winner: string | null;
  /** Percent improvement of treatment over control */
  improvementPercent: number;
}

/**
 * Test case for A/B testing.
 */
export interface TestCase {
  /** Input to agent */
  input: string;
  /** Expected output (for accuracy calculation) */
  expected?: string;
  /** Additional metadata */
  [key: string]: unknown;
}

/**
 * Evaluation result for a single test case.
 */
interface EvaluationResult {
  accuracy: number;
  latencyMs: number;
  input: string;
  expected?: string;
  actual: string;
  error?: string;
}

/**
 * Configuration for ABTest.
 */
export interface ABTestConfig {
  /** Experiment name */
  name: string;
  /** Control/baseline agent */
  controlAgent: Agent;
  /** Treatment/variant agent */
  treatmentAgent: Agent;
  /** Metrics to compare (default: ['accuracy']) */
  metrics?: string[];
  /** Statistical significance threshold (default: 0.05) */
  significanceLevel?: SignificanceLevel;
}

/**
 * Options for running an A/B test.
 */
export interface RunOptions {
  /** Number of samples per variant (undefined = all) */
  sampleSize?: number;
  /** Shuffle test cases before splitting */
  shuffle?: boolean;
}

/**
 * A/B testing framework for comparing agent variants.
 *
 * Provides statistical significance testing, effect size calculation,
 * and automated experiment orchestration.
 */
export class ABTest {
  readonly name: string;
  readonly control: ABVariant;
  readonly treatment: ABVariant;
  readonly metrics: string[];
  readonly significanceLevel: SignificanceLevel;
  readonly results: Map<string, ABTestResult>;

  constructor(config: ABTestConfig) {
    this.name = config.name;
    this.control = new ABVariant('control', config.controlAgent);
    this.treatment = new ABVariant('treatment', config.treatmentAgent);
    this.metrics = config.metrics || ['accuracy'];
    this.significanceLevel = config.significanceLevel || SignificanceLevel.P_0_05;
    this.results = new Map();
  }

  /**
   * Run A/B test experiment.
   *
   * @param testCases Test cases to evaluate
   * @param options Run options
   * @returns Dictionary of results per metric
   */
  async run(
    testCases: TestCase[],
    options: RunOptions = {}
  ): Promise<Record<string, ABTestResult>> {
    const { sampleSize, shuffle = true } = options;

    // Prepare test cases
    let cases = [...testCases];
    if (shuffle) {
      cases = this.shuffleArray(cases);
    }
    if (sampleSize !== undefined) {
      cases = cases.slice(0, sampleSize);
    }

    // Run both variants
    const controlResults = await this.evaluateVariant(this.control, cases);
    const treatmentResults = await this.evaluateVariant(this.treatment, cases);

    // Store samples for each metric and run statistical tests
    const resultMap: Record<string, ABTestResult> = {};

    for (const metric of this.metrics) {
      // Clear previous samples
      this.control.samples.length = 0;
      this.treatment.samples.length = 0;

      // Extract metric values
      for (const result of controlResults) {
        this.control.addSample(result[metric] || 0);
      }
      for (const result of treatmentResults) {
        this.treatment.addSample(result[metric] || 0);
      }

      // Run statistical test
      const testResult = this.runStatisticalTest(metric);
      this.results.set(metric, testResult);
      resultMap[metric] = testResult;
    }

    return resultMap;
  }

  /**
   * Evaluate a variant on test cases.
   */
  private async evaluateVariant(
    variant: ABVariant,
    testCases: TestCase[]
  ): Promise<EvaluationResult[]> {
    const results: EvaluationResult[] = [];

    for (const testCase of testCases) {
      try {
        const startTime = performance.now();
        const message = createMessage('user', testCase.input);
        const response = await variant.agent.process(message);
        const latencyMs = performance.now() - startTime;

        // Calculate accuracy (simple string matching)
        const expected = testCase.expected || '';
        const actual = String(response.content);
        const accuracy = expected && actual.toLowerCase().includes(expected.toLowerCase()) ? 1.0 : 0.0;

        results.push({
          accuracy,
          latencyMs,
          input: testCase.input,
          expected,
          actual,
        });
      } catch (error) {
        results.push({
          accuracy: 0.0,
          latencyMs: 0.0,
          input: testCase.input,
          actual: '',
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    return results;
  }

  /**
   * Run statistical significance test (independent samples t-test).
   */
  private runStatisticalTest(metricName: string): ABTestResult {
    const controlSamples = this.control.samples;
    const treatmentSamples = this.treatment.samples;

    // T-test calculation
    const { pValue, tStatistic } = this.tTest(controlSamples, treatmentSamples);

    // Cohen's d effect size
    const pooledStd = Math.sqrt(
      (Math.pow(this.control.std, 2) + Math.pow(this.treatment.std, 2)) / 2
    );
    const effectSize =
      pooledStd > 0 ? (this.treatment.mean - this.control.mean) / pooledStd : 0.0;

    // Confidence interval (simplified)
    const diffMean = this.treatment.mean - this.control.mean;
    const standardError = pooledStd * Math.sqrt(
      1 / controlSamples.length + 1 / treatmentSamples.length
    );
    const tCritical = this.getTCritical(
      controlSamples.length + treatmentSamples.length - 2,
      this.significanceLevel
    );
    const marginOfError = tCritical * standardError;
    const confidenceInterval: [number, number] = [
      diffMean - marginOfError,
      diffMean + marginOfError,
    ];

    // Determine significance and winner
    const isSignificant = pValue < this.significanceLevel;
    const winner = isSignificant
      ? this.treatment.mean > this.control.mean
        ? this.treatment.name
        : this.control.name
      : null;

    const improvementPercent =
      this.control.mean !== 0
        ? ((this.treatment.mean - this.control.mean) / Math.abs(this.control.mean)) * 100
        : 0.0;

    return {
      experimentName: this.name,
      controlVariant: this.control,
      treatmentVariant: this.treatment,
      metricName,
      pValue,
      significanceLevel: this.significanceLevel,
      effectSize,
      confidenceInterval,
      timestamp: new Date().toISOString(),
      isSignificant,
      winner,
      improvementPercent,
    };
  }

  /**
   * Independent samples t-test.
   */
  private tTest(
    sample1: number[],
    sample2: number[]
  ): { pValue: number; tStatistic: number } {
    const n1 = sample1.length;
    const n2 = sample2.length;

    if (n1 < 2 || n2 < 2) {
      return { pValue: 1.0, tStatistic: 0.0 };
    }

    const mean1 = sample1.reduce((a, b) => a + b, 0) / n1;
    const mean2 = sample2.reduce((a, b) => a + b, 0) / n2;

    const variance1 =
      sample1.reduce((sum, x) => sum + Math.pow(x - mean1, 2), 0) / (n1 - 1);
    const variance2 =
      sample2.reduce((sum, x) => sum + Math.pow(x - mean2, 2), 0) / (n2 - 1);

    // Special case: if both variances are 0 (all identical values within each group)
    if (variance1 === 0 && variance2 === 0) {
      // If means are different, it's definitely significant
      if (Math.abs(mean1 - mean2) > 0.0001) {
        return { pValue: 0.0, tStatistic: Infinity };
      }
      // If means are the same, no difference
      return { pValue: 1.0, tStatistic: 0.0 };
    }

    const pooledVariance =
      ((n1 - 1) * variance1 + (n2 - 1) * variance2) / (n1 + n2 - 2);
    const standardError = Math.sqrt(pooledVariance * (1 / n1 + 1 / n2));

    const tStatistic =
      standardError > 0 ? (mean1 - mean2) / standardError : 0.0;

    // Degrees of freedom
    const df = n1 + n2 - 2;

    // Calculate p-value (two-tailed)
    const pValue = this.tDistributionPValue(Math.abs(tStatistic), df) * 2;

    return { pValue, tStatistic };
  }

  /**
   * Approximate p-value from t-distribution (using normal approximation for simplicity).
   */
  private tDistributionPValue(t: number, df: number): number {
    // For large df (>30), t-distribution approximates normal distribution
    if (df > 30) {
      return 1 - this.normalCDF(t);
    }

    // Simplified approximation for smaller df
    // This is a rough approximation; for production, use a proper t-distribution library
    const adjustedT = t * Math.sqrt(df / (df + Math.pow(t, 2)));
    return 1 - this.normalCDF(adjustedT);
  }

  /**
   * Cumulative distribution function for standard normal distribution.
   */
  private normalCDF(x: number): number {
    // Approximation using error function
    return 0.5 * (1 + this.erf(x / Math.sqrt(2)));
  }

  /**
   * Error function approximation.
   */
  private erf(x: number): number {
    // Abramowitz and Stegun approximation
    const sign = x >= 0 ? 1 : -1;
    x = Math.abs(x);

    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;

    const t = 1 / (1 + p * x);
    const y =
      1 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

    return sign * y;
  }

  /**
   * Get t-critical value (approximation).
   */
  private getTCritical(df: number, alpha: SignificanceLevel): number {
    // Simplified lookup table for common values
    // For production, use a proper t-distribution library

    const alphaValue = alpha as number;

    if (df >= 30) {
      // Use z-scores for large df
      if (alphaValue === 0.001) return 3.291;
      if (alphaValue === 0.01) return 2.576;
      if (alphaValue === 0.05) return 1.960;
      if (alphaValue === 0.10) return 1.645;
    }

    // Rough approximation for smaller df
    const zScore = alphaValue === 0.001 ? 3.291
      : alphaValue === 0.01 ? 2.576
      : alphaValue === 0.05 ? 1.960
      : 1.645;

    return zScore * Math.sqrt((df + 3) / df);
  }

  /**
   * Shuffle array (Fisher-Yates algorithm).
   */
  private shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  /**
   * Get experiment summary.
   */
  getSummary(): Record<string, unknown> {
    const resultsObj: Record<string, unknown> = {};
    this.results.forEach((result, metric) => {
      resultsObj[metric] = {
        control: {
          name: result.controlVariant.name,
          mean: result.controlVariant.mean,
          std: result.controlVariant.std,
          sampleSize: result.controlVariant.sampleSize,
        },
        treatment: {
          name: result.treatmentVariant.name,
          mean: result.treatmentVariant.mean,
          std: result.treatmentVariant.std,
          sampleSize: result.treatmentVariant.sampleSize,
        },
        statistics: {
          pValue: result.pValue,
          isSignificant: result.isSignificant,
          effectSize: result.effectSize,
          confidenceInterval: result.confidenceInterval,
        },
        outcome: {
          winner: result.winner,
          improvementPercent: result.improvementPercent,
        },
      };
    });

    return {
      experimentName: this.name,
      variants: {
        control: this.control.name,
        treatment: this.treatment.name,
      },
      metrics: this.metrics,
      results: resultsObj,
    };
  }
}
