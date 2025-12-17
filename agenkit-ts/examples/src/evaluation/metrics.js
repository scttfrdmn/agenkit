"use strict";
/**
 * Enhanced Metrics Tracking for Agent Evaluation
 *
 * This module extends core evaluation with enhanced metric tracking including:
 * - Session status tracking (running, completed, failed, etc.)
 * - Error collection and analysis
 * - Metric type categorization
 * - Cross-session aggregation
 *
 * Key use case: "How do you know a long-running agent succeeded?"
 *
 * Example:
 * ```typescript
 * const result = new SessionResult('session-123', 'my-agent');
 * result.addMetricMeasurement(
 *   createMetricMeasurement('accuracy', 0.95, MetricType.SuccessRate)
 * );
 * result.setStatus(SessionStatus.Completed);
 *
 * const collector = new MetricsCollector();
 * collector.addSession(result);
 * const aggregate = collector.getAggregatedMetrics();
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MetricsCollector = exports.SessionResult = exports.MetricType = exports.SessionStatus = void 0;
exports.createMetricMeasurement = createMetricMeasurement;
exports.createErrorRecord = createErrorRecord;
/**
 * Session status types.
 */
var SessionStatus;
(function (SessionStatus) {
    /** Session is currently running */
    SessionStatus["Running"] = "running";
    /** Session completed successfully */
    SessionStatus["Completed"] = "completed";
    /** Session failed */
    SessionStatus["Failed"] = "failed";
    /** Session timed out */
    SessionStatus["Timeout"] = "timeout";
    /** Session was cancelled */
    SessionStatus["Cancelled"] = "cancelled";
})(SessionStatus || (exports.SessionStatus = SessionStatus = {}));
/**
 * Metric type categories.
 */
var MetricType;
(function (MetricType) {
    /** Success/failure rates */
    MetricType["SuccessRate"] = "success_rate";
    /** Output quality scores */
    MetricType["QualityScore"] = "quality_score";
    /** Token/API costs */
    MetricType["Cost"] = "cost";
    /** Time taken */
    MetricType["Duration"] = "duration";
    /** Error frequency */
    MetricType["ErrorRate"] = "error_rate";
    /** Task completion */
    MetricType["TaskCompletion"] = "task_completion";
    /** Custom metrics */
    MetricType["Custom"] = "custom";
})(MetricType || (exports.MetricType = MetricType = {}));
/**
 * Create a new metric measurement with current timestamp.
 *
 * @param name Metric name
 * @param value Metric value
 * @param type Metric type
 * @param metadata Optional metadata
 * @returns Metric measurement
 */
function createMetricMeasurement(name, value, type, metadata) {
    return {
        name,
        value,
        type,
        timestamp: new Date(),
        metadata: metadata || {},
    };
}
/**
 * Create a new error record with current timestamp.
 *
 * @param errorType Error type
 * @param message Error message
 * @param details Optional details
 * @returns Error record
 */
function createErrorRecord(errorType, message, details) {
    return {
        type: errorType,
        message,
        details: details || {},
        timestamp: new Date(),
    };
}
/**
 * Session result with enhanced tracking.
 *
 * This extends the core EvaluationResult with session status, error tracking,
 * and richer metadata for long-running agent evaluations.
 */
class SessionResult {
    /**
     * Create session result.
     *
     * @param sessionId Session identifier
     * @param agentName Agent name
     */
    constructor(sessionId, agentName) {
        this.endTime = null;
        this.measurements = [];
        this.errors = [];
        this.metadata = {};
        this.sessionId = sessionId;
        this.agentName = agentName;
        this.status = SessionStatus.Running;
        this.startTime = new Date();
    }
    /**
     * Set session status.
     *
     * @param status New status
     */
    setStatus(status) {
        this.status = status;
        if (status !== SessionStatus.Running &&
            status !== SessionStatus.Cancelled &&
            this.endTime === null) {
            this.endTime = new Date();
        }
    }
    /**
     * Add metric measurement.
     *
     * @param measurement Metric measurement
     */
    addMetricMeasurement(measurement) {
        this.measurements.push(measurement);
    }
    /**
     * Add error record.
     *
     * @param error Error record
     */
    addError(error) {
        this.errors.push(error);
    }
    /**
     * Get duration in seconds.
     *
     * @returns Duration in seconds (0 if not ended)
     */
    getDurationSeconds() {
        if (!this.endTime) {
            return 0;
        }
        return (this.endTime.getTime() - this.startTime.getTime()) / 1000;
    }
    /**
     * Get measurements by metric name.
     *
     * @param name Metric name
     * @returns Measurements for this metric
     */
    getMeasurementsByName(name) {
        return this.measurements.filter(m => m.name === name);
    }
    /**
     * Get measurements by metric type.
     *
     * @param type Metric type
     * @returns Measurements of this type
     */
    getMeasurementsByType(type) {
        return this.measurements.filter(m => m.type === type);
    }
    /**
     * Get errors by type.
     *
     * @param type Error type
     * @returns Errors of this type
     */
    getErrorsByType(type) {
        return this.errors.filter(e => e.type === type);
    }
    /**
     * Check if session has errors.
     *
     * @returns True if errors occurred
     */
    hasErrors() {
        return this.errors.length > 0;
    }
    /**
     * Get error count.
     *
     * @returns Number of errors
     */
    getErrorCount() {
        return this.errors.length;
    }
    /**
     * Convert to plain object.
     *
     * @returns Plain object representation
     */
    toDict() {
        return {
            session_id: this.sessionId,
            agent_name: this.agentName,
            status: this.status,
            start_time: this.startTime.toISOString(),
            end_time: this.endTime ? this.endTime.toISOString() : null,
            duration_seconds: this.getDurationSeconds(),
            measurements: this.measurements.map(m => ({
                name: m.name,
                value: m.value,
                type: m.type,
                timestamp: m.timestamp.toISOString(),
                metadata: m.metadata,
            })),
            errors: this.errors.map(e => ({
                type: e.type,
                message: e.message,
                details: e.details,
                timestamp: e.timestamp.toISOString(),
            })),
            metadata: this.metadata,
        };
    }
}
exports.SessionResult = SessionResult;
/**
 * Cross-session metrics collector.
 *
 * Aggregates metrics across multiple evaluation sessions for analysis.
 */
class MetricsCollector {
    constructor() {
        this.sessions = new Map();
    }
    /**
     * Add session result.
     *
     * @param session Session result
     */
    addSession(session) {
        this.sessions.set(session.sessionId, session);
    }
    /**
     * Get session by ID.
     *
     * @param sessionId Session identifier
     * @returns Session result if found
     */
    getSession(sessionId) {
        return this.sessions.get(sessionId);
    }
    /**
     * Get all sessions.
     *
     * @returns All session results
     */
    getAllSessions() {
        return Array.from(this.sessions.values());
    }
    /**
     * Get sessions by status.
     *
     * @param status Session status
     * @returns Sessions with this status
     */
    getSessionsByStatus(status) {
        return this.getAllSessions().filter(s => s.status === status);
    }
    /**
     * Get sessions by agent name.
     *
     * @param agentName Agent name
     * @returns Sessions for this agent
     */
    getSessionsByAgent(agentName) {
        return this.getAllSessions().filter(s => s.agentName === agentName);
    }
    /**
     * Get aggregated metrics across all sessions.
     *
     * @returns Map of metric name to aggregated statistics
     */
    getAggregatedMetrics() {
        const metricsByName = new Map();
        // Collect all measurements by metric name
        for (const session of this.sessions.values()) {
            for (const measurement of session.measurements) {
                if (!metricsByName.has(measurement.name)) {
                    metricsByName.set(measurement.name, []);
                }
                metricsByName.get(measurement.name).push(measurement);
            }
        }
        // Aggregate each metric
        const aggregated = new Map();
        for (const [name, measurements] of metricsByName.entries()) {
            aggregated.set(name, this.aggregateMeasurements(name, measurements));
        }
        return aggregated;
    }
    /**
     * Aggregate measurements for a single metric.
     *
     * @param name Metric name
     * @param measurements Measurements to aggregate
     * @returns Aggregated statistics
     */
    aggregateMeasurements(name, measurements) {
        if (measurements.length === 0) {
            return {
                name,
                type: MetricType.Custom,
                mean: 0,
                min: 0,
                max: 0,
                std: 0,
                count: 0,
            };
        }
        const values = measurements.map(m => m.value);
        const sum = values.reduce((a, b) => a + b, 0);
        const mean = sum / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        // Calculate standard deviation
        const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / values.length;
        const std = Math.sqrt(variance);
        return {
            name,
            type: measurements[0].type,
            mean,
            min,
            max,
            std,
            count: values.length,
        };
    }
    /**
     * Get success rate across all sessions.
     *
     * @returns Success rate (completed / total)
     */
    getSuccessRate() {
        const total = this.sessions.size;
        if (total === 0) {
            return 0;
        }
        const completed = this.getSessionsByStatus(SessionStatus.Completed).length;
        return completed / total;
    }
    /**
     * Get error rate across all sessions.
     *
     * @returns Error rate (sessions with errors / total)
     */
    getErrorRate() {
        const total = this.sessions.size;
        if (total === 0) {
            return 0;
        }
        const withErrors = this.getAllSessions().filter(s => s.hasErrors()).length;
        return withErrors / total;
    }
    /**
     * Get total error count.
     *
     * @returns Total number of errors
     */
    getTotalErrorCount() {
        return this.getAllSessions().reduce((sum, s) => sum + s.getErrorCount(), 0);
    }
    /**
     * Get average duration across completed sessions.
     *
     * @returns Average duration in seconds
     */
    getAverageDuration() {
        const completed = this.getSessionsByStatus(SessionStatus.Completed);
        if (completed.length === 0) {
            return 0;
        }
        const totalDuration = completed.reduce((sum, s) => sum + s.getDurationSeconds(), 0);
        return totalDuration / completed.length;
    }
    /**
     * Clear all sessions.
     */
    clear() {
        this.sessions.clear();
    }
    /**
     * Get session count.
     *
     * @returns Number of sessions
     */
    getSessionCount() {
        return this.sessions.size;
    }
}
exports.MetricsCollector = MetricsCollector;
