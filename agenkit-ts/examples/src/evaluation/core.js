"use strict";
/**
 * Core evaluation framework.
 *
 * Provides evaluation orchestration, result aggregation, and standardized interfaces
 * for measuring agent performance across multiple dimensions.
 *
 * Example:
 * ```typescript
 * const evaluator = new Evaluator(agent, [new AccuracyMetric()]);
 * const result = await evaluator.evaluate(testCases);
 * console.log(`Success rate: ${result.successRate}`);
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.Evaluator = void 0;
exports.getSuccessRate = getSuccessRate;
exports.resultToDict = resultToDict;
exports.evaluateAgent = evaluateAgent;
const interfaces_1 = require("../core/interfaces");
/**
 * Calculate success rate from evaluation result.
 *
 * @param result Evaluation result
 * @returns Success rate (0.0 to 1.0)
 */
function getSuccessRate(result) {
    if (result.totalTests === 0) {
        return 0.0;
    }
    return result.passedTests / result.totalTests;
}
/**
 * Convert evaluation result to plain object.
 *
 * @param result Evaluation result
 * @returns Plain object representation
 */
function resultToDict(result) {
    return {
        evaluationId: result.evaluationId,
        agentName: result.agentName,
        timestamp: result.timestamp.toISOString(),
        metrics: result.metrics,
        aggregatedMetrics: result.aggregatedMetrics,
        contextLength: result.contextLength,
        compressedLength: result.compressedLength,
        compressionRatio: result.compressionRatio,
        accuracy: result.accuracy,
        qualityScore: result.qualityScore,
        avgLatencyMs: result.avgLatencyMs,
        p95LatencyMs: result.p95LatencyMs,
        totalTests: result.totalTests,
        passedTests: result.passedTests,
        failedTests: result.failedTests,
        successRate: getSuccessRate(result),
        metadata: result.metadata,
    };
}
/**
 * Core evaluation orchestrator.
 *
 * Runs test cases against an agent, collects metrics, and aggregates results.
 * Supports custom metrics and flexible test case formats.
 *
 * Example:
 * ```typescript
 * const evaluator = new Evaluator(myAgent, [
 *   new AccuracyMetric(),
 *   new LatencyMetric(),
 * ]);
 *
 * const testCases = [
 *   { input: 'What is 2+2?', expected: '4' },
 *   { input: 'What is the capital of France?', expected: 'Paris' },
 * ];
 *
 * const result = await evaluator.evaluate(testCases);
 * console.log(`Accuracy: ${result.accuracy}`);
 * console.log(`Avg Latency: ${result.avgLatencyMs}ms`);
 * ```
 */
class Evaluator {
    /**
     * Create a new evaluator.
     *
     * @param agent Agent to evaluate
     * @param metrics List of metrics to collect (optional)
     * @param sessionId Session identifier (optional, auto-generated if not provided)
     */
    constructor(agent, metrics = [], sessionId) {
        this.agent = agent;
        this.metrics = metrics;
        this.sessionId = sessionId || `eval-${Date.now()}`;
    }
    /**
     * Evaluate agent on test cases.
     *
     * Runs each test case through the agent, collects metrics, and aggregates results.
     *
     * @param testCases Array of test cases to evaluate
     * @param evaluationId Optional evaluation identifier
     * @returns Evaluation result with metrics and statistics
     */
    async evaluate(testCases, evaluationId) {
        const evalId = evaluationId || this.generateEvaluationId();
        const result = {
            evaluationId: evalId,
            agentName: this.agent.name,
            timestamp: new Date(),
            metrics: {},
            aggregatedMetrics: {},
            totalTests: testCases.length,
            passedTests: 0,
            failedTests: 0,
            metadata: {},
        };
        // Initialize metric arrays
        for (const metric of this.metrics) {
            result.metrics[metric.name] = [];
        }
        // Track latencies for performance metrics
        const latencies = [];
        // Evaluate each test case
        for (const testCase of testCases) {
            const inputMsg = (0, interfaces_1.createMessage)('user', testCase.input);
            // Measure latency
            const startTime = Date.now();
            let outputMsg;
            try {
                outputMsg = await this.agent.process(inputMsg);
                const latency = Date.now() - startTime;
                latencies.push(latency);
                // Collect metrics
                const context = {
                    expected: testCase.expected,
                    sessionId: this.sessionId,
                    ...testCase.metadata,
                };
                for (const metric of this.metrics) {
                    const value = await metric.measure(this.agent, inputMsg, outputMsg, context);
                    result.metrics[metric.name].push(value);
                    // Track pass/fail for accuracy-like metrics
                    if (metric.name === 'accuracy' && value === 1.0) {
                        result.passedTests++;
                    }
                }
                // If no accuracy metric, use simple validation
                if (!this.metrics.some(m => m.name === 'accuracy')) {
                    if (this.checkTest(outputMsg, testCase)) {
                        result.passedTests++;
                    }
                }
            }
            catch (error) {
                result.failedTests++;
                // Continue with other test cases
            }
        }
        // Calculate failed tests
        result.failedTests = result.totalTests - result.passedTests;
        // Aggregate metrics
        for (const metric of this.metrics) {
            const measurements = result.metrics[metric.name];
            result.aggregatedMetrics[metric.name] = metric.aggregate(measurements);
        }
        // Calculate performance metrics
        if (latencies.length > 0) {
            result.avgLatencyMs = latencies.reduce((a, b) => a + b, 0) / latencies.length;
            // Calculate P95 latency
            const sortedLatencies = [...latencies].sort((a, b) => a - b);
            const p95Index = Math.floor(sortedLatencies.length * 0.95);
            result.p95LatencyMs = sortedLatencies[p95Index];
        }
        // Set convenience fields from aggregated metrics
        if (result.aggregatedMetrics['accuracy']) {
            result.accuracy = result.aggregatedMetrics['accuracy'].mean;
        }
        if (result.aggregatedMetrics['quality_score']) {
            result.qualityScore = result.aggregatedMetrics['quality_score'].mean;
        }
        return result;
    }
    /**
     * Evaluate agent on a single test case.
     *
     * @param inputMessage Input message
     * @param expectedOutput Expected output (optional)
     * @returns Map of metric names to scores
     */
    async evaluateSingle(inputMessage, expectedOutput) {
        const outputMessage = await this.agent.process(inputMessage);
        const scores = {};
        const context = {
            expected: expectedOutput,
            sessionId: this.sessionId,
        };
        for (const metric of this.metrics) {
            scores[metric.name] = await metric.measure(this.agent, inputMessage, outputMessage, context);
        }
        return scores;
    }
    /**
     * Check if a test case passed (simple validation).
     *
     * @param output Agent output message
     * @param testCase Test case with expected output
     * @returns True if test passed
     */
    checkTest(output, testCase) {
        if (!testCase.expected) {
            return true; // No expected output, consider passed
        }
        const actualLower = output.content.toLowerCase();
        const expectedLower = testCase.expected.toLowerCase();
        // Check if expected is contained in actual
        return actualLower.includes(expectedLower);
    }
    /**
     * Generate a unique evaluation ID.
     *
     * @returns Unique identifier string
     */
    generateEvaluationId() {
        return `eval-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    /**
     * Get the session ID.
     *
     * @returns Session identifier
     */
    getSessionId() {
        return this.sessionId;
    }
    /**
     * Get the agent being evaluated.
     *
     * @returns Agent instance
     */
    getAgent() {
        return this.agent;
    }
    /**
     * Get the metrics being collected.
     *
     * @returns Array of metrics
     */
    getMetrics() {
        return this.metrics;
    }
}
exports.Evaluator = Evaluator;
/**
 * Helper function to evaluate an agent on test cases.
 *
 * Convenience wrapper around Evaluator class.
 *
 * @param agent Agent to evaluate
 * @param testCases Test cases to run
 * @param metrics Metrics to collect (optional)
 * @returns Evaluation result
 */
async function evaluateAgent(agent, testCases, metrics) {
    const evaluator = new Evaluator(agent, metrics);
    return evaluator.evaluate(testCases);
}
