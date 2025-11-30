/**
 * @file regression.hpp
 * @brief Regression detection for agent performance monitoring
 *
 * This module provides regression detection by comparing agent evaluation results:
 * - Compare current performance against baselines
 * - Detect statistically significant degradations
 * - Categorize severity (minor, moderate, major, critical)
 * - Track performance trends over time
 *
 * Key use cases:
 * - CI/CD regression testing
 * - Production monitoring
 * - A/B testing analysis
 * - Performance trend analysis
 *
 * @example
 * @code
 * auto detector = RegressionDetector();
 * detector.set_baseline(baseline_result);
 *
 * // Later, after changes
 * auto regressions = detector.detect(current_result, true);
 * if (!regressions.empty()) {
 *     std::cout << "Found " << regressions.size() << " regressions!" << std::endl;
 *     for (const auto& r : regressions) {
 *         std::cout << "  " << r.metric_name << ": "
 *                   << r.degradation_percent << "% worse" << std::endl;
 *     }
 * }
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_REGRESSION_HPP
#define AGENKIT_EVALUATION_REGRESSION_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Regression severity levels
 *
 * Categorizes the severity of performance degradation.
 */
enum class Severity {
    None,       ///< No regression detected
    Minor,      ///< < 10% degradation
    Moderate,   ///< 10-20% degradation
    Major,      ///< 20-50% degradation
    Critical    ///< > 50% degradation
};

/**
 * @brief Convert Severity to string
 * @param severity Severity to convert
 * @return String representation
 */
std::string severity_to_string(Severity severity);

/**
 * @brief Convert string to Severity
 * @param str String to convert
 * @return Severity enum value
 */
Severity severity_from_string(const std::string& str);

/**
 * @brief Evaluation result for regression detection
 *
 * Simplified structure containing key metrics for comparison.
 * Maps to the full EvaluationResult from core evaluation.
 */
struct EvaluationResult {
    std::string evaluation_id;
    std::string agent_name;
    std::chrono::system_clock::time_point timestamp;

    std::optional<double> accuracy;
    std::optional<double> quality_score;
    std::optional<double> avg_latency_ms;
    std::optional<int> context_length;
    std::optional<double> compression_ratio;

    nlohmann::json metadata;

    /**
     * @brief Convert to JSON representation
     * @return JSON object
     */
    nlohmann::json to_json() const;

    /**
     * @brief Create from JSON representation
     * @param j JSON object
     * @return EvaluationResult instance
     */
    static EvaluationResult from_json(const nlohmann::json& j);
};

/**
 * @brief Detected regression in agent performance
 *
 * Contains information about what degraded and by how much.
 */
struct Regression {
    std::string metric_name;          ///< Name of the metric that regressed
    double baseline_value;            ///< Baseline (expected) value
    double current_value;             ///< Current (actual) value
    double degradation_percent;       ///< Degradation as percentage
    Severity severity;                ///< Severity level
    std::chrono::system_clock::time_point timestamp; ///< When detected
    nlohmann::json context;           ///< Additional context

    /**
     * @brief Check if this is a real regression (not improvement)
     * @return true if degradation_percent > 0
     */
    bool is_regression() const { return degradation_percent > 0; }

    /**
     * @brief Convert to JSON representation
     * @return JSON object
     */
    nlohmann::json to_json() const;
};

/**
 * @brief Detects performance regressions by comparing results
 *
 * Monitors agent quality over time and alerts when performance
 * degrades beyond acceptable thresholds.
 *
 * @details
 * RegressionDetector maintains a baseline and optionally a history
 * of evaluation results. It compares new results against the baseline
 * to detect degradations in key metrics.
 *
 * @example
 * @code
 * std::unordered_map<std::string, double> thresholds = {
 *     {"accuracy", 0.10},  // 10% degradation acceptable
 *     {"latency", 0.20}    // 20% slower acceptable
 * };
 *
 * auto detector = RegressionDetector(thresholds);
 * detector.set_baseline(baseline_result);
 *
 * // Later
 * auto regressions = detector.detect(current_result, true);
 * if (!regressions.empty()) {
 *     // Handle regressions
 * }
 * @endcode
 */
class RegressionDetector {
public:
    /**
     * @brief Create a regression detector
     * @param thresholds Acceptable degradation per metric (default: 10% for most)
     * @param baseline Optional baseline evaluation result
     *
     * Default thresholds:
     * - accuracy: 0.10 (10%)
     * - quality: 0.10 (10%)
     * - latency: 0.20 (20%)
     * - context_length: 0.30 (30%)
     */
    explicit RegressionDetector(
        std::unordered_map<std::string, double> thresholds = {},
        std::optional<EvaluationResult> baseline = std::nullopt
    );

    /**
     * @brief Set baseline for comparison
     * @param result Evaluation result to use as baseline
     */
    void set_baseline(const EvaluationResult& result);

    /**
     * @brief Detect regressions in evaluation result
     *
     * Compares current result to baseline and identifies metrics
     * that have degraded beyond acceptable thresholds.
     *
     * @param result Current evaluation result
     * @param store_history Whether to store result in history
     * @return List of detected regressions (empty if no regressions)
     */
    std::vector<Regression> detect(const EvaluationResult& result, bool store_history = false);

    /**
     * @brief Get trend for metric over recent history
     * @param metric_name Metric to analyze
     * @param window Number of recent results to analyze
     * @return Trend statistics (slope, direction, variance), or empty if insufficient data
     *
     * Returns a JSON object with:
     * - metric: Metric name
     * - slope: Linear regression slope
     * - direction: "improving", "degrading", or "stable"
     * - variance: Variance of values
     * - current: Most recent value
     * - mean: Mean value
     * - window_size: Number of data points used
     */
    std::optional<nlohmann::json> get_trend(const std::string& metric_name, size_t window) const;

    /**
     * @brief Compare two evaluation results
     * @param result_a First result (baseline)
     * @param result_b Second result (comparison)
     * @return Map of metric comparisons
     *
     * Returns a map where each key is a metric name and the value is a map with:
     * - baseline: Value from result_a
     * - current: Value from result_b
     * - change: Absolute change
     * - change_percent: Percentage change
     */
    std::unordered_map<std::string, std::unordered_map<std::string, double>>
    compare_results(const EvaluationResult& result_a, const EvaluationResult& result_b) const;

    /**
     * @brief Clear evaluation history
     */
    void clear_history();

    /**
     * @brief Get summary of detector state
     * @return Summary with baseline info and history count
     *
     * Returns a JSON object with:
     * - has_baseline: Whether a baseline is set
     * - baseline_id: Baseline evaluation ID (if set)
     * - history_count: Number of results in history
     * - thresholds: Configured thresholds
     */
    nlohmann::json get_summary() const;

private:
    /**
     * @brief Check a single metric for regression
     * @param name Metric name
     * @param baseline Baseline value
     * @param current Current value
     * @param higher_is_better Whether higher values indicate better performance
     * @return Regression if detected, nullopt otherwise
     */
    std::optional<Regression> check_metric(
        const std::string& name,
        double baseline,
        double current,
        bool higher_is_better
    ) const;

    /**
     * @brief Calculate severity based on degradation amount
     * @param degradation Degradation as fraction (0.1 = 10%)
     * @return Severity level
     */
    Severity calculate_severity(double degradation) const;

    std::unordered_map<std::string, double> thresholds_;
    std::optional<EvaluationResult> baseline_;
    std::vector<EvaluationResult> history_;
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_REGRESSION_HPP
