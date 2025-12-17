"use strict";
/**
 * Regression detection for agent quality monitoring.
 *
 * Detects performance degradation over time by comparing
 * current results to baseline and historical results.
 *
 * Example:
 * ```typescript
 * const detector = new RegressionDetector();
 * detector.setBaseline(baselineResult);
 *
 * // Later, after changes
 * const regressions = detector.detect(currentResult);
 * if (regressions.length > 0) {
 *   console.log(`Found ${regressions.length} regressions!`);
 *   for (const r of regressions) {
 *     console.log(`  ${r.metricName}: ${r.degradationPercent.toFixed(1)}% worse`);
 *   }
 * }
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.RegressionDetector = exports.Severity = void 0;
exports.isRegression = isRegression;
exports.regressionToDict = regressionToDict;
/**
 * Regression severity levels.
 */
var Severity;
(function (Severity) {
    /** No regression (or improvement) */
    Severity["NONE"] = "none";
    /** Minor regression (<10% degradation) */
    Severity["MINOR"] = "minor";
    /** Moderate regression (10-20% degradation) */
    Severity["MODERATE"] = "moderate";
    /** Major regression (20-50% degradation) */
    Severity["MAJOR"] = "major";
    /** Critical regression (>50% degradation) */
    Severity["CRITICAL"] = "critical";
})(Severity || (exports.Severity = Severity = {}));
/**
 * Check if a regression is a real degradation (not improvement).
 *
 * @param regression Regression to check
 * @returns True if degradation occurred
 */
function isRegression(regression) {
    return regression.degradationPercent > 0;
}
/**
 * Convert regression to plain object.
 *
 * @param regression Regression to convert
 * @returns Plain object representation
 */
function regressionToDict(regression) {
    return {
        metric_name: regression.metricName,
        baseline_value: regression.baselineValue,
        current_value: regression.currentValue,
        degradation_percent: regression.degradationPercent,
        severity: regression.severity,
        timestamp: regression.timestamp.toISOString(),
        context: regression.context,
    };
}
/**
 * Detect performance regressions by comparing results.
 *
 * Monitors agent quality over time and alerts when performance
 * degrades beyond acceptable thresholds.
 */
class RegressionDetector {
    /**
     * Create regression detector.
     *
     * @param config Detector configuration
     */
    constructor(config) {
        this.baseline = null;
        this.history = [];
        this.thresholds = config?.thresholds || {
            accuracy: 0.1, // 10% degradation threshold
            quality: 0.1,
            latency: 0.2, // 20% slower acceptable
            context_length: 0.3, // 30% larger context acceptable
        };
        if (config?.baseline) {
            this.baseline = config.baseline;
        }
    }
    /**
     * Set baseline for comparison.
     *
     * @param result Evaluation result to use as baseline
     */
    setBaseline(result) {
        this.baseline = result;
    }
    /**
     * Detect regressions in evaluation result.
     *
     * Compares current result to baseline and identifies metrics
     * that have degraded beyond acceptable thresholds.
     *
     * @param result Current evaluation result
     * @param storeHistory Whether to store result in history
     * @returns List of detected regressions (empty if no regressions)
     */
    detect(result, storeHistory = true) {
        if (storeHistory) {
            this.history.push(result);
        }
        if (!this.baseline) {
            // No baseline = no regressions
            return [];
        }
        const regressions = [];
        // Check accuracy
        if (result.accuracy !== undefined && this.baseline.accuracy !== undefined) {
            const reg = this.checkMetric('accuracy', this.baseline.accuracy, result.accuracy, true);
            if (reg) {
                regressions.push(reg);
            }
        }
        // Check quality_score
        if (result.qualityScore !== undefined && this.baseline.qualityScore !== undefined) {
            const reg = this.checkMetric('quality', this.baseline.qualityScore, result.qualityScore, true);
            if (reg) {
                regressions.push(reg);
            }
        }
        // Check latency (lower is better)
        if (result.avgLatencyMs !== undefined && this.baseline.avgLatencyMs !== undefined) {
            const reg = this.checkMetric('latency', this.baseline.avgLatencyMs, result.avgLatencyMs, false);
            if (reg) {
                regressions.push(reg);
            }
        }
        // Check context length
        if (result.contextLength !== undefined && this.baseline.contextLength !== undefined) {
            const reg = this.checkMetric('context_length', this.baseline.contextLength, result.contextLength, false);
            if (reg) {
                regressions.push(reg);
            }
        }
        // Check compression ratio (higher is better)
        if (result.compressionRatio !== undefined && this.baseline.compressionRatio !== undefined) {
            const reg = this.checkMetric('compression_ratio', this.baseline.compressionRatio, result.compressionRatio, true);
            if (reg) {
                regressions.push(reg);
            }
        }
        return regressions;
    }
    /**
     * Check single metric for regression.
     *
     * @param name Metric name
     * @param baseline Baseline value
     * @param current Current value
     * @param higherIsBetter Whether higher values are better
     * @returns Regression if detected, null otherwise
     */
    checkMetric(name, baseline, current, higherIsBetter) {
        let degradation;
        if (baseline === 0) {
            // Avoid division by zero
            if (current === 0) {
                return null;
            }
            degradation = higherIsBetter ? 1.0 : -1.0;
        }
        else if (higherIsBetter) {
            // For accuracy, quality: lower is worse
            degradation = (baseline - current) / baseline;
        }
        else {
            // For latency, context_length: higher is worse
            degradation = (current - baseline) / baseline;
        }
        // Check if exceeds threshold
        const threshold = this.thresholds[name] ?? 0.1;
        if (degradation > threshold) {
            const severity = this.calculateSeverity(degradation);
            return {
                metricName: name,
                baselineValue: baseline,
                currentValue: current,
                degradationPercent: degradation * 100,
                severity,
                timestamp: new Date(),
                context: {
                    thresholdPercent: threshold * 100,
                    higherIsBetter,
                },
            };
        }
        return null;
    }
    /**
     * Calculate severity based on degradation amount.
     *
     * @param degradation Degradation as fraction (0.1 = 10%)
     * @returns Severity level
     */
    calculateSeverity(degradation) {
        if (degradation < 0.1) {
            return Severity.NONE;
        }
        else if (degradation < 0.2) {
            return Severity.MINOR;
        }
        else if (degradation < 0.5) {
            return Severity.MODERATE;
        }
        else {
            return Severity.CRITICAL;
        }
    }
    /**
     * Get trend for metric over recent history.
     *
     * @param metricName Metric to analyze
     * @param window Number of recent results to analyze
     * @returns Trend statistics (null if insufficient data)
     */
    getTrend(metricName, window = 10) {
        if (this.history.length < 2) {
            return null;
        }
        // Get recent results
        const recent = this.history.slice(-window);
        // Extract metric values
        const values = [];
        for (const result of recent) {
            if (metricName === 'accuracy' && result.accuracy !== undefined) {
                values.push(result.accuracy);
            }
            else if (metricName === 'quality' && result.qualityScore !== undefined) {
                values.push(result.qualityScore);
            }
            else if (metricName === 'latency' && result.avgLatencyMs !== undefined) {
                values.push(result.avgLatencyMs);
            }
            else if (metricName === 'context_length' && result.contextLength !== undefined) {
                values.push(result.contextLength);
            }
        }
        if (values.length < 2) {
            return null;
        }
        // Calculate trend
        const n = values.length;
        const x = Array.from({ length: n }, (_, i) => i);
        const xMean = x.reduce((sum, val) => sum + val, 0) / n;
        const yMean = values.reduce((sum, val) => sum + val, 0) / n;
        // Linear regression slope
        const numerator = x.reduce((sum, xi, i) => sum + (xi - xMean) * (values[i] - yMean), 0);
        const denominator = x.reduce((sum, xi) => sum + Math.pow(xi - xMean, 2), 0);
        const slope = denominator !== 0 ? numerator / denominator : 0;
        // Variance
        const variance = values.reduce((sum, v) => sum + Math.pow(v - yMean, 2), 0) / n;
        return {
            metric: metricName,
            slope,
            direction: slope > 0 ? 'improving' : slope < 0 ? 'degrading' : 'stable',
            variance,
            current: values[values.length - 1],
            mean: yMean,
            windowSize: n,
        };
    }
    /**
     * Compare two evaluation results.
     *
     * @param resultA First result (baseline)
     * @param resultB Second result (comparison)
     * @returns Dictionary of metric comparisons
     */
    compareResults(resultA, resultB) {
        const comparisons = {};
        // Compare accuracy
        if (resultA.accuracy !== undefined && resultB.accuracy !== undefined) {
            comparisons.accuracy = {
                baseline: resultA.accuracy,
                current: resultB.accuracy,
                change: resultB.accuracy - resultA.accuracy,
                changePercent: resultA.accuracy !== 0
                    ? ((resultB.accuracy - resultA.accuracy) / resultA.accuracy) * 100
                    : 0,
            };
        }
        // Compare quality
        if (resultA.qualityScore !== undefined && resultB.qualityScore !== undefined) {
            comparisons.quality = {
                baseline: resultA.qualityScore,
                current: resultB.qualityScore,
                change: resultB.qualityScore - resultA.qualityScore,
                changePercent: resultA.qualityScore !== 0
                    ? ((resultB.qualityScore - resultA.qualityScore) / resultA.qualityScore) * 100
                    : 0,
            };
        }
        // Compare latency
        if (resultA.avgLatencyMs !== undefined && resultB.avgLatencyMs !== undefined) {
            comparisons.latency = {
                baseline: resultA.avgLatencyMs,
                current: resultB.avgLatencyMs,
                change: resultB.avgLatencyMs - resultA.avgLatencyMs,
                changePercent: resultA.avgLatencyMs !== 0
                    ? ((resultB.avgLatencyMs - resultA.avgLatencyMs) / resultA.avgLatencyMs) * 100
                    : 0,
            };
        }
        return comparisons;
    }
    /**
     * Clear evaluation history.
     */
    clearHistory() {
        this.history = [];
    }
    /**
     * Get summary of detector state.
     *
     * @returns Summary with baseline info and history count
     */
    getSummary() {
        return {
            hasBaseline: this.baseline !== null,
            baselineId: this.baseline?.evaluationId || null,
            historyCount: this.history.length,
            thresholds: this.thresholds,
        };
    }
    /**
     * Get evaluation history.
     *
     * @returns List of historical evaluation results
     */
    getHistory() {
        return [...this.history];
    }
    /**
     * Get baseline evaluation result.
     *
     * @returns Baseline result if set, null otherwise
     */
    getBaseline() {
        return this.baseline;
    }
}
exports.RegressionDetector = RegressionDetector;
