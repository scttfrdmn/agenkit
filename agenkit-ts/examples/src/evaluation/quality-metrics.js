"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.LatencyMetric = exports.QualityMetrics = exports.AccuracyMetric = void 0;
exports.evaluateAgent = evaluateAgent;
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
class AccuracyMetric {
    constructor(config = {}) {
        this.name = 'accuracy';
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
    async measure(agent, inputMessage, outputMessage, context) {
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
    aggregate(measurements) {
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
exports.AccuracyMetric = AccuracyMetric;
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
class QualityMetrics {
    constructor(config = {}) {
        this.name = 'quality';
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
    async measure(agent, inputMessage, outputMessage, context) {
        const scores = await this.ruleBasedQuality(inputMessage, outputMessage, context);
        // Weighted average
        const totalScore = scores.relevance * this.weights.relevance +
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
    async ruleBasedQuality(inputMessage, outputMessage, context) {
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
    measureRelevance(input, output) {
        const inputWords = new Set(input
            .toLowerCase()
            .split(/\s+/)
            .filter(w => w.length > 3));
        const outputWords = new Set(output
            .toLowerCase()
            .split(/\s+/)
            .filter(w => w.length > 3));
        if (inputWords.size === 0)
            return 1.0;
        let overlap = 0;
        for (const word of inputWords) {
            if (outputWords.has(word))
                overlap++;
        }
        return Math.min(overlap / inputWords.size, 1.0);
    }
    /**
     * Measure completeness (response length and structure).
     */
    measureCompleteness(input, output) {
        // Heuristic: output should be at least as long as input
        const inputLength = input.split(/\s+/).length;
        const outputLength = output.split(/\s+/).length;
        if (outputLength === 0)
            return 0.0;
        if (outputLength >= inputLength)
            return 1.0;
        return outputLength / inputLength;
    }
    /**
     * Measure coherence (sentence structure).
     */
    measureCoherence(output) {
        // Heuristic: proper sentences with punctuation
        const sentences = output.split(/[.!?]+/).filter(s => s.trim().length > 0);
        if (sentences.length === 0)
            return 0.0;
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
    measureAccuracy(output, context) {
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
    aggregate(measurements) {
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
exports.QualityMetrics = QualityMetrics;
/**
 * Latency metric for measuring response time.
 */
class LatencyMetric {
    constructor() {
        this.name = 'latency';
    }
    async measure(agent, inputMessage, outputMessage, context) {
        // Latency should be measured externally and passed in context
        if (context && typeof context.latency === 'number') {
            return context.latency;
        }
        // If not provided, measure now
        const start = performance.now();
        await agent.process(inputMessage);
        return performance.now() - start;
    }
    aggregate(measurements) {
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
exports.LatencyMetric = LatencyMetric;
/**
 * Evaluate agent on multiple metrics.
 *
 * @param agent Agent to evaluate
 * @param testCases Test cases with input and expected output
 * @param metrics Metrics to compute
 * @returns Evaluation results
 */
async function evaluateAgent(agent, testCases, metrics) {
    const metricMeasurements = new Map();
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
            metricMeasurements.get(metric.name).push(score);
        }
    }
    const results = {};
    for (const metric of metrics) {
        const measurements = metricMeasurements.get(metric.name);
        results[metric.name] = metric.aggregate(measurements);
    }
    return {
        agentName: agent.name,
        totalTests: testCases.length,
        metrics: results,
    };
}
