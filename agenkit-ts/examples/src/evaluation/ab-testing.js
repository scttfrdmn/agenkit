"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.ABTest = exports.ABVariant = exports.SignificanceLevel = void 0;
const interfaces_1 = require("../core/interfaces");
/** Statistical significance levels */
var SignificanceLevel;
(function (SignificanceLevel) {
    /** 99.9% confidence */
    SignificanceLevel[SignificanceLevel["P_0_001"] = 0.001] = "P_0_001";
    /** 99% confidence */
    SignificanceLevel[SignificanceLevel["P_0_01"] = 0.01] = "P_0_01";
    /** 95% confidence (default) */
    SignificanceLevel[SignificanceLevel["P_0_05"] = 0.05] = "P_0_05";
    /** 90% confidence */
    SignificanceLevel[SignificanceLevel["P_0_10"] = 0.1] = "P_0_10";
})(SignificanceLevel || (exports.SignificanceLevel = SignificanceLevel = {}));
/**
 * Represents a variant in an A/B test.
 *
 * Tracks samples and calculates basic statistics.
 */
class ABVariant {
    constructor(name, agent, metadata = {}) {
        this.name = name;
        this.agent = agent;
        this.samples = [];
        this.metadata = metadata;
    }
    /**
     * Add a measurement sample.
     */
    addSample(value) {
        this.samples.push(value);
    }
    /**
     * Mean of samples.
     */
    get mean() {
        if (this.samples.length === 0)
            return 0.0;
        return this.samples.reduce((a, b) => a + b, 0) / this.samples.length;
    }
    /**
     * Standard deviation of samples.
     */
    get std() {
        if (this.samples.length <= 1)
            return 0.0;
        const mean = this.mean;
        const squaredDiffs = this.samples.map(x => Math.pow(x - mean, 2));
        const variance = squaredDiffs.reduce((a, b) => a + b, 0) / (this.samples.length - 1);
        return Math.sqrt(variance);
    }
    /**
     * Number of samples.
     */
    get sampleSize() {
        return this.samples.length;
    }
}
exports.ABVariant = ABVariant;
/**
 * A/B testing framework for comparing agent variants.
 *
 * Provides statistical significance testing, effect size calculation,
 * and automated experiment orchestration.
 */
class ABTest {
    constructor(config) {
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
    async run(testCases, options = {}) {
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
        const resultMap = {};
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
    async evaluateVariant(variant, testCases) {
        const results = [];
        for (const testCase of testCases) {
            try {
                const startTime = performance.now();
                const message = (0, interfaces_1.createMessage)('user', testCase.input);
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
            }
            catch (error) {
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
    runStatisticalTest(metricName) {
        const controlSamples = this.control.samples;
        const treatmentSamples = this.treatment.samples;
        // T-test calculation
        const { pValue, tStatistic } = this.tTest(controlSamples, treatmentSamples);
        // Cohen's d effect size
        const pooledStd = Math.sqrt((Math.pow(this.control.std, 2) + Math.pow(this.treatment.std, 2)) / 2);
        const effectSize = pooledStd > 0 ? (this.treatment.mean - this.control.mean) / pooledStd : 0.0;
        // Confidence interval (simplified)
        const diffMean = this.treatment.mean - this.control.mean;
        const standardError = pooledStd * Math.sqrt(1 / controlSamples.length + 1 / treatmentSamples.length);
        const tCritical = this.getTCritical(controlSamples.length + treatmentSamples.length - 2, this.significanceLevel);
        const marginOfError = tCritical * standardError;
        const confidenceInterval = [
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
        const improvementPercent = this.control.mean !== 0
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
    tTest(sample1, sample2) {
        const n1 = sample1.length;
        const n2 = sample2.length;
        if (n1 < 2 || n2 < 2) {
            return { pValue: 1.0, tStatistic: 0.0 };
        }
        const mean1 = sample1.reduce((a, b) => a + b, 0) / n1;
        const mean2 = sample2.reduce((a, b) => a + b, 0) / n2;
        const variance1 = sample1.reduce((sum, x) => sum + Math.pow(x - mean1, 2), 0) / (n1 - 1);
        const variance2 = sample2.reduce((sum, x) => sum + Math.pow(x - mean2, 2), 0) / (n2 - 1);
        // Special case: if both variances are 0 (all identical values within each group)
        if (variance1 === 0 && variance2 === 0) {
            // If means are different, it's definitely significant
            if (Math.abs(mean1 - mean2) > 0.0001) {
                return { pValue: 0.0, tStatistic: Infinity };
            }
            // If means are the same, no difference
            return { pValue: 1.0, tStatistic: 0.0 };
        }
        const pooledVariance = ((n1 - 1) * variance1 + (n2 - 1) * variance2) / (n1 + n2 - 2);
        const standardError = Math.sqrt(pooledVariance * (1 / n1 + 1 / n2));
        const tStatistic = standardError > 0 ? (mean1 - mean2) / standardError : 0.0;
        // Degrees of freedom
        const df = n1 + n2 - 2;
        // Calculate p-value (two-tailed)
        const pValue = this.tDistributionPValue(Math.abs(tStatistic), df) * 2;
        return { pValue, tStatistic };
    }
    /**
     * Approximate p-value from t-distribution (using normal approximation for simplicity).
     */
    tDistributionPValue(t, df) {
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
    normalCDF(x) {
        // Approximation using error function
        return 0.5 * (1 + this.erf(x / Math.sqrt(2)));
    }
    /**
     * Error function approximation.
     */
    erf(x) {
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
        const y = 1 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
        return sign * y;
    }
    /**
     * Get t-critical value (approximation).
     */
    getTCritical(df, alpha) {
        // Simplified lookup table for common values
        // For production, use a proper t-distribution library
        const alphaValue = alpha;
        if (df >= 30) {
            // Use z-scores for large df
            if (alphaValue === 0.001)
                return 3.291;
            if (alphaValue === 0.01)
                return 2.576;
            if (alphaValue === 0.05)
                return 1.960;
            if (alphaValue === 0.10)
                return 1.645;
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
    shuffleArray(array) {
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
    getSummary() {
        const resultsObj = {};
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
exports.ABTest = ABTest;
