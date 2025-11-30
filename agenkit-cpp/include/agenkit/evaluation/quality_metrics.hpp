/**
 * @file quality_metrics.hpp
 * @brief Quality metrics for agent evaluation
 *
 * This module provides comprehensive quality scoring for agent outputs:
 * - Accuracy measurement (exact/fuzzy matching)
 * - Multi-dimensional quality scoring (relevance, completeness, coherence)
 * - Precision/recall for classification tasks
 * - Extensible metric framework
 *
 * Key use cases:
 * - Benchmark agent accuracy on test sets
 * - Evaluate response quality holistically
 * - Track precision/recall for classification agents
 * - Custom domain-specific metrics
 *
 * @example
 * @code
 * auto metric = AccuracyMetric(false); // Case-insensitive
 * auto ctx = nlohmann::json::object();
 * ctx["expected"] = "Paris";
 *
 * double score = metric.measure(agent, input_msg, output_msg, ctx);
 * std::cout << "Accuracy: " << score << std::endl; // 0.0 or 1.0
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_QUALITY_METRICS_HPP
#define AGENKIT_EVALUATION_QUALITY_METRICS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <memory>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Validator function type for custom validation
 *
 * Takes expected and actual values, returns true if they match.
 */
using ValidatorFunc = std::function<bool(const std::string&, const std::string&)>;

/**
 * @brief Base interface for evaluation metrics
 *
 * All metrics implement this interface to provide:
 * - Single measurement on one interaction
 * - Aggregation across multiple measurements
 *
 * @details
 * This follows the same pattern as the Metric interface in Python/Go/TypeScript.
 */
class Metric {
public:
    virtual ~Metric() = default;

    /**
     * @brief Get metric name
     * @return Metric name
     */
    virtual std::string name() const = 0;

    /**
     * @brief Measure metric for a single agent interaction
     * @param agent Agent being evaluated
     * @param input_message Input to agent
     * @param output_message Agent's response
     * @param ctx Additional context (expected output, etc.)
     * @return Metric value (typically 0.0 to 1.0)
     */
    virtual double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) = 0;

    /**
     * @brief Aggregate multiple measurements
     * @param measurements List of individual measurements
     * @return Aggregated statistics (mean, std, min, max, etc.)
     */
    virtual nlohmann::json aggregate(const std::vector<double>& measurements) = 0;
};

/**
 * @brief Accuracy metric for task correctness
 *
 * Compares agent output to expected output to determine correctness.
 * Supports multiple validation methods:
 * - Exact string matching
 * - Substring matching (case-insensitive)
 * - Custom validator functions
 *
 * @example
 * @code
 * auto metric = AccuracyMetric(false); // Case-insensitive substring matching
 * auto ctx = nlohmann::json::object();
 * ctx["expected"] = "Paris";
 *
 * double score = metric.measure(agent, input_msg, output_msg, ctx);
 * // Returns 1.0 if output contains "paris" (any case), 0.0 otherwise
 * @endcode
 */
class AccuracyMetric : public Metric {
public:
    /**
     * @brief Create an accuracy metric
     * @param case_sensitive Whether string matching is case-sensitive
     * @param validator Optional custom validation function
     */
    explicit AccuracyMetric(
        bool case_sensitive = false,
        ValidatorFunc validator = nullptr
    );

    std::string name() const override { return "accuracy"; }

    /**
     * @brief Measure accuracy for single interaction
     * @param agent Agent being evaluated
     * @param input_message Input to agent
     * @param output_message Agent's response
     * @param ctx Must contain "expected" key with expected output
     * @return 1.0 if correct, 0.0 if incorrect
     */
    double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) override;

    /**
     * @brief Aggregate accuracy measurements
     * @param measurements List of 0.0/1.0 values
     * @return Accuracy statistics: accuracy, total, correct, incorrect
     */
    nlohmann::json aggregate(const std::vector<double>& measurements) override;

private:
    bool case_sensitive_;
    ValidatorFunc validator_;
};

/**
 * @brief Comprehensive quality scoring
 *
 * Evaluates multiple quality dimensions:
 * - Relevance: How relevant is response to query?
 * - Completeness: Does response answer all parts?
 * - Coherence: Is response logically structured?
 * - Accuracy: Is information factually correct?
 *
 * Uses rule-based scoring with configurable weights.
 *
 * @example
 * @code
 * std::unordered_map<std::string, double> weights = {
 *     {"relevance", 0.4},
 *     {"completeness", 0.3},
 *     {"coherence", 0.2},
 *     {"accuracy", 0.1}
 * };
 *
 * auto metric = QualityMetrics(false, "", weights);
 * double score = metric.measure(agent, input_msg, output_msg, ctx);
 * // Returns 0.0 to 1.0
 * @endcode
 */
class QualityMetrics : public Metric {
public:
    /**
     * @brief Create a quality metrics instance
     * @param use_llm_judge Use LLM to judge quality (not yet implemented)
     * @param judge_model Model to use for judging (e.g., "claude-sonnet-4")
     * @param weights Weights for each dimension (relevance, completeness, etc.)
     *
     * Default weights:
     * - relevance: 0.3
     * - completeness: 0.3
     * - coherence: 0.2
     * - accuracy: 0.2
     */
    explicit QualityMetrics(
        bool use_llm_judge = false,
        const std::string& judge_model = "",
        std::unordered_map<std::string, double> weights = {}
    );

    std::string name() const override { return "quality"; }

    /**
     * @brief Measure response quality
     * @param agent Agent being evaluated
     * @param input_message Input query
     * @param output_message Agent response
     * @param ctx Optional context (expected output for accuracy scoring)
     * @return Quality score (0.0 to 1.0)
     */
    double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) override;

    /**
     * @brief Aggregate quality measurements
     * @param measurements List of quality scores
     * @return Statistics: mean, min, max, std
     */
    nlohmann::json aggregate(const std::vector<double>& measurements) override;

private:
    /**
     * @brief Perform rule-based quality scoring
     *
     * Uses heuristics to evaluate quality:
     * - Relevance: Response mentions query terms
     * - Completeness: Response length vs query complexity
     * - Coherence: Proper structure, no repetition
     * - Accuracy: Matches expected output if provided
     *
     * @param input_message Input query
     * @param output_message Agent response
     * @param ctx Context (expected output, etc.)
     * @return Quality score (0.0 to 1.0)
     */
    double rule_based_quality(
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    );

    /**
     * @brief Check for excessive repetition in text
     * @param text Text to check
     * @return true if repetition detected
     */
    bool has_repetition(const std::string& text);

    bool use_llm_judge_;
    std::string judge_model_;  // Not yet used but reserved for future LLM-based judging
    std::unordered_map<std::string, double> weights_;
};

/**
 * @brief Precision and recall statistics
 *
 * Container for confusion matrix and derived metrics.
 */
struct PrecisionRecallStats {
    int true_positives = 0;
    int false_positives = 0;
    int false_negatives = 0;
    int true_negatives = 0;

    /**
     * @brief Calculate precision
     * @return Precision (TP / (TP + FP))
     */
    double precision() const;

    /**
     * @brief Calculate recall
     * @return Recall (TP / (TP + FN))
     */
    double recall() const;

    /**
     * @brief Calculate F1 score
     * @return F1 score (2 * (precision * recall) / (precision + recall))
     */
    double f1_score() const;

    /**
     * @brief Convert to JSON representation
     * @return JSON object with all metrics
     */
    nlohmann::json to_json() const;
};

/**
 * @brief Precision/recall metric for classification tasks
 *
 * Useful for agents that categorize, filter, or make binary decisions.
 * Maintains confusion matrix across all measurements.
 *
 * @example
 * @code
 * auto metric = PrecisionRecallMetric();
 *
 * // For each test case
 * auto ctx = nlohmann::json::object();
 * ctx["true_label"] = true;
 * ctx["predicted_label"] = agent_predicted_label;
 *
 * metric.measure(agent, input_msg, output_msg, ctx);
 *
 * // Get final metrics
 * auto stats = metric.aggregate({});
 * std::cout << "Precision: " << stats["precision"] << std::endl;
 * std::cout << "Recall: " << stats["recall"] << std::endl;
 * std::cout << "F1: " << stats["f1_score"] << std::endl;
 * @endcode
 */
class PrecisionRecallMetric : public Metric {
public:
    PrecisionRecallMetric() = default;

    std::string name() const override { return "precision_recall"; }

    /**
     * @brief Measure precision/recall for single classification
     *
     * Context must contain:
     * - "true_label": Ground truth (true/false or 1/0)
     * - "predicted_label": Agent's prediction (true/false or 1/0)
     *
     * @param agent Agent being evaluated
     * @param input_message Input to agent
     * @param output_message Agent's response
     * @param ctx Must contain true_label and predicted_label
     * @return 1.0 if correct classification, 0.0 if incorrect
     */
    double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) override;

    /**
     * @brief Aggregate precision/recall metrics
     * @param measurements Not used (confusion matrix maintained internally)
     * @return Precision, recall, F1 score, and confusion matrix counts
     */
    nlohmann::json aggregate(const std::vector<double>& measurements) override;

    /**
     * @brief Reset confusion matrix counts
     */
    void reset();

    /**
     * @brief Get current statistics
     * @return Current precision/recall stats
     */
    PrecisionRecallStats get_stats() const { return stats_; }

private:
    PrecisionRecallStats stats_;
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_QUALITY_METRICS_HPP
