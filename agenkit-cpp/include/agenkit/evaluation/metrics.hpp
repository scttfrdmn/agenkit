/**
 * @file metrics.hpp
 * @brief Enhanced metrics tracking for agent evaluation
 *
 * This module extends core evaluation with detailed metric tracking including:
 * - Session status tracking (running, completed, failed, etc.)
 * - Error collection and analysis
 * - Metric type categorization
 * - Cross-session aggregation
 *
 * Key use case: "How do you know a long-running agent succeeded?"
 *
 * @example
 * @code
 * auto result = SessionResult("session-123", "my-agent");
 * result.add_metric_measurement(MetricMeasurement(
 *     "accuracy", 0.95, MetricType::SuccessRate
 * ));
 * result.set_status(SessionStatus::Completed);
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_METRICS_HPP
#define AGENKIT_EVALUATION_METRICS_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <mutex>
#include <optional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Session status enumeration
 *
 * Represents the current state of an evaluation session.
 */
enum class SessionStatus {
    Running,    ///< Session is currently running
    Completed,  ///< Session completed successfully
    Failed,     ///< Session failed
    Timeout,    ///< Session timed out
    Cancelled   ///< Session was cancelled
};

/**
 * @brief Convert SessionStatus to string
 * @param status Status to convert
 * @return String representation
 */
std::string session_status_to_string(SessionStatus status);

/**
 * @brief Convert string to SessionStatus
 * @param str String to convert
 * @return SessionStatus enum value
 */
SessionStatus session_status_from_string(const std::string& str);

/**
 * @brief Metric type categorization
 *
 * Categorizes different types of metrics for easier analysis.
 */
enum class MetricType {
    SuccessRate,     ///< Success/failure rates
    QualityScore,    ///< Output quality scores
    Cost,            ///< Token/API costs
    Duration,        ///< Time measurements
    ErrorRate,       ///< Error frequency
    TaskCompletion,  ///< Task completion metrics
    Custom           ///< Custom domain-specific metrics
};

/**
 * @brief Convert MetricType to string
 * @param type Type to convert
 * @return String representation
 */
std::string metric_type_to_string(MetricType type);

/**
 * @brief Convert string to MetricType
 * @param str String to convert
 * @return MetricType enum value
 */
MetricType metric_type_from_string(const std::string& str);

/**
 * @brief Single metric measurement
 *
 * Note: This is distinct from the Metric interface in core evaluation.
 * Metric interface defines how to measure, MetricMeasurement stores the measurement.
 *
 * @details
 * Represents a single measurement taken at a specific time, with optional metadata
 * for additional context.
 */
class MetricMeasurement {
public:
    /**
     * @brief Create a metric measurement
     * @param name Metric name
     * @param value Measurement value
     * @param type Metric type categorization
     * @param timestamp Optional timestamp (defaults to now)
     * @param metadata Optional metadata
     */
    MetricMeasurement(
        std::string name,
        double value,
        MetricType type,
        std::optional<std::chrono::system_clock::time_point> timestamp = std::nullopt,
        nlohmann::json metadata = nlohmann::json::object()
    );

    /// Get metric name
    const std::string& name() const { return name_; }

    /// Get measurement value
    double value() const { return value_; }

    /// Get metric type
    MetricType type() const { return type_; }

    /// Get timestamp
    std::chrono::system_clock::time_point timestamp() const { return timestamp_; }

    /// Get metadata
    const nlohmann::json& metadata() const { return metadata_; }

    /// Get mutable metadata reference
    nlohmann::json& metadata() { return metadata_; }

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return MetricMeasurement instance
     */
    static MetricMeasurement from_json(const nlohmann::json& j);

private:
    std::string name_;
    double value_;
    MetricType type_;
    std::chrono::system_clock::time_point timestamp_;
    nlohmann::json metadata_;
};

/**
 * @brief Error record for tracking failures
 *
 * Records errors that occurred during evaluation with details and timestamp.
 */
class ErrorRecord {
public:
    /**
     * @brief Create an error record
     * @param type Error type/category
     * @param message Error message
     * @param details Additional error details
     * @param timestamp Optional timestamp (defaults to now)
     */
    ErrorRecord(
        std::string type,
        std::string message,
        nlohmann::json details = nlohmann::json::object(),
        std::optional<std::chrono::system_clock::time_point> timestamp = std::nullopt
    );

    /// Get error type
    const std::string& type() const { return type_; }

    /// Get error message
    const std::string& message() const { return message_; }

    /// Get error details
    const nlohmann::json& details() const { return details_; }

    /// Get timestamp
    std::chrono::system_clock::time_point timestamp() const { return timestamp_; }

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return ErrorRecord instance
     */
    static ErrorRecord from_json(const nlohmann::json& j);

private:
    std::string type_;
    std::string message_;
    nlohmann::json details_;
    std::chrono::system_clock::time_point timestamp_;
};

/**
 * @brief Session evaluation result with enhanced tracking
 *
 * This extends core EvaluationResult with session status, error tracking,
 * and richer metadata for long-running agent evaluations.
 *
 * Thread-safety: Individual SessionResult instances are NOT thread-safe.
 * Use external synchronization if accessing from multiple threads.
 *
 * @example
 * @code
 * auto result = SessionResult("session-1", "my-agent");
 * result.add_metric_measurement(MetricMeasurement("accuracy", 0.95, MetricType::SuccessRate));
 * result.add_error("timeout", "Request timed out", {{"duration", 30.0}});
 * result.set_status(SessionStatus::Failed);
 * std::cout << result.to_json().dump(2) << std::endl;
 * @endcode
 */
class SessionResult {
public:
    /**
     * @brief Create a new session result
     * @param session_id Unique session identifier
     * @param agent_name Name of agent being evaluated
     */
    SessionResult(std::string session_id, std::string agent_name);

    /// Get session ID
    const std::string& session_id() const { return session_id_; }

    /// Get agent name
    const std::string& agent_name() const { return agent_name_; }

    /// Get session status
    SessionStatus status() const { return status_; }

    /// Get start time
    std::chrono::system_clock::time_point start_time() const { return start_time_; }

    /// Get end time (if session has ended)
    std::optional<std::chrono::system_clock::time_point> end_time() const { return end_time_; }

    /// Get measurements
    const std::vector<MetricMeasurement>& measurements() const { return measurements_; }

    /// Get errors
    const std::vector<ErrorRecord>& errors() const { return errors_; }

    /// Get metadata
    const nlohmann::json& metadata() const { return metadata_; }

    /// Get mutable metadata reference
    nlohmann::json& metadata() { return metadata_; }

    /**
     * @brief Add a metric measurement
     * @param measurement Measurement to add
     */
    void add_metric_measurement(const MetricMeasurement& measurement);

    /**
     * @brief Add an error record
     * @param type Error type
     * @param message Error message
     * @param details Optional error details
     */
    void add_error(const std::string& type, const std::string& message,
                   const nlohmann::json& details = nlohmann::json::object());

    /**
     * @brief Set session status
     * @param status New status
     *
     * If status is not Running and end_time is not set, sets end_time to now.
     */
    void set_status(SessionStatus status);

    /**
     * @brief Get a specific metric by name (returns first match)
     * @param name Metric name to search for
     * @return Pointer to measurement if found, nullptr otherwise
     */
    const MetricMeasurement* get_metric(const std::string& name) const;

    /**
     * @brief Get all measurements of a specific type
     * @param type Metric type to filter by
     * @return Vector of measurements matching the type
     */
    std::vector<MetricMeasurement> get_metrics_by_type(MetricType type) const;

    /**
     * @brief Calculate session duration in seconds
     * @return Duration in seconds, or nullopt if session hasn't ended
     */
    std::optional<double> duration_seconds() const;

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return SessionResult instance
     */
    static SessionResult from_json(const nlohmann::json& j);

private:
    std::string session_id_;
    std::string agent_name_;
    SessionStatus status_;
    std::chrono::system_clock::time_point start_time_;
    std::optional<std::chrono::system_clock::time_point> end_time_;
    std::vector<MetricMeasurement> measurements_;
    std::vector<ErrorRecord> errors_;
    nlohmann::json metadata_;
};

/**
 * @brief Aggregates metrics across multiple evaluation sessions
 *
 * Useful for analyzing agent performance over time and across different scenarios.
 * Thread-safe for concurrent access.
 *
 * @details
 * MetricsCollector maintains a collection of SessionResults and provides
 * statistical analysis across all sessions. All methods are thread-safe
 * using internal mutex synchronization.
 *
 * @example
 * @code
 * auto collector = MetricsCollector();
 * collector.add_result(result1);
 * collector.add_result(result2);
 *
 * auto stats = collector.get_statistics();
 * std::cout << "Success rate: " << stats["success_rate"] * 100 << "%" << std::endl;
 * @endcode
 */
class MetricsCollector {
public:
    /**
     * @brief Create a new metrics collector
     */
    MetricsCollector();

    /**
     * @brief Add a session result to the collector
     * @param result Session result to add
     *
     * Thread-safe for concurrent access.
     */
    void add_result(const SessionResult& result);

    /**
     * @brief Get aggregated statistics across all sessions
     * @return Map of statistics
     *
     * Returns a map with the following keys:
     * - session_count: Total number of sessions
     * - completed_count: Number of completed sessions
     * - failed_count: Number of failed sessions
     * - success_rate: Ratio of completed to total sessions
     * - avg_duration: Average session duration in seconds
     * - total_errors: Total number of errors across all sessions
     * - avg_errors_per_session: Average errors per session
     *
     * Thread-safe for concurrent access.
     */
    nlohmann::json get_statistics() const;

    /**
     * @brief Get aggregated statistics for a specific metric
     * @param metric_name Name of the metric to aggregate
     * @return Map with count, sum, mean, min, max
     *
     * Thread-safe for concurrent access.
     */
    nlohmann::json get_metric_aggregates(const std::string& metric_name) const;

    /**
     * @brief Get all collected session results
     * @return Vector of session results (copy)
     *
     * Returns a copy to prevent external mutation.
     * Thread-safe for concurrent access.
     */
    std::vector<SessionResult> get_results() const;

    /**
     * @brief Clear all collected results
     *
     * Thread-safe for concurrent access.
     */
    void clear();

private:
    mutable std::mutex mutex_;
    std::vector<SessionResult> results_;
};

/**
 * @brief Helper function to create a quality score metric measurement
 *
 * Creates a quality score metric with normalized score (0.0-1.0).
 *
 * @param name Metric name
 * @param score Raw score value
 * @param max_score Maximum possible score (default: 10.0)
 * @param metadata Optional additional metadata
 * @return MetricMeasurement with normalized score
 *
 * @example
 * @code
 * auto metric = create_quality_metric("response_quality", 8.5, 10.0);
 * // metric.value() will be 0.85
 * @endcode
 */
MetricMeasurement create_quality_metric(
    const std::string& name,
    double score,
    double max_score = 10.0,
    nlohmann::json metadata = nlohmann::json::object()
);

/**
 * @brief Helper function to create a cost metric measurement
 *
 * Creates a cost metric with currency information.
 *
 * @param cost Cost amount
 * @param currency Currency code (default: "USD")
 * @param metadata Optional additional metadata
 * @return Cost metric measurement
 *
 * @example
 * @code
 * auto metric = create_cost_metric(0.0042, "USD", {{"tokens", 1000}});
 * @endcode
 */
MetricMeasurement create_cost_metric(
    double cost,
    const std::string& currency = "USD",
    nlohmann::json metadata = nlohmann::json::object()
);

/**
 * @brief Helper function to create a duration metric measurement
 *
 * Creates a duration metric with hours conversion in metadata.
 *
 * @param duration_seconds Duration in seconds
 * @param metadata Optional additional metadata
 * @return Duration metric measurement
 *
 * @example
 * @code
 * auto metric = create_duration_metric(125.5);
 * // metadata will include duration_hours: 0.0348611
 * @endcode
 */
MetricMeasurement create_duration_metric(
    double duration_seconds,
    nlohmann::json metadata = nlohmann::json::object()
);

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_METRICS_HPP
