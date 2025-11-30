/**
 * @file quality_metrics.cpp
 * @brief Implementation of quality metrics for agent evaluation
 */

#include "agenkit/evaluation/quality_metrics.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <cctype>
#include <sstream>
#include <unordered_set>

namespace agenkit {
namespace evaluation {

// Helper functions

static std::string to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

static std::vector<std::string> split_words(const std::string& str) {
    std::vector<std::string> words;
    std::istringstream iss(str);
    std::string word;
    while (iss >> word) {
        words.push_back(word);
    }
    return words;
}

static bool to_bool(const nlohmann::json& value) {
    if (value.is_boolean()) {
        return value.get<bool>();
    } else if (value.is_number_integer()) {
        return value.get<int>() != 0;
    } else if (value.is_number_float()) {
        return value.get<double>() != 0.0;
    } else if (value.is_string()) {
        std::string str = value.get<std::string>();
        return str == "true" || str == "True" || str == "1";
    }
    return false;
}

// AccuracyMetric implementation

AccuracyMetric::AccuracyMetric(bool case_sensitive, ValidatorFunc validator)
    : case_sensitive_(case_sensitive)
    , validator_(std::move(validator))
{
}

double AccuracyMetric::measure(
    std::shared_ptr<core::Agent> agent,
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    // Unused parameter
    (void)agent;
    (void)input_message;

    if (!ctx.contains("expected")) {
        return 1.0; // No expected output = always correct
    }

    std::string actual = output_message.content_as_str();

    // Custom validator
    if (validator_) {
        std::string expected = ctx["expected"].is_string() ?
            ctx["expected"].get<std::string>() :
            ctx["expected"].dump();
        return validator_(expected, actual) ? 1.0 : 0.0;
    }

    // String matching
    std::string expected = ctx["expected"].is_string() ?
        ctx["expected"].get<std::string>() :
        ctx["expected"].dump();

    if (!case_sensitive_) {
        expected = to_lower(expected);
        actual = to_lower(actual);
    }

    // Substring matching
    return actual.find(expected) != std::string::npos ? 1.0 : 0.0;
}

nlohmann::json AccuracyMetric::aggregate(const std::vector<double>& measurements) {
    nlohmann::json result;

    if (measurements.empty()) {
        result["accuracy"] = 0.0;
        result["total"] = 0.0;
        result["correct"] = 0.0;
        result["incorrect"] = 0.0;
        return result;
    }

    double total = static_cast<double>(measurements.size());
    double correct = std::accumulate(measurements.begin(), measurements.end(), 0.0);

    result["accuracy"] = correct / total;
    result["total"] = total;
    result["correct"] = correct;
    result["incorrect"] = total - correct;

    return result;
}

// QualityMetrics implementation

QualityMetrics::QualityMetrics(
    bool use_llm_judge,
    const std::string& judge_model,
    std::unordered_map<std::string, double> weights
)
    : use_llm_judge_(use_llm_judge)
    , judge_model_(judge_model)
{
    if (weights.empty()) {
        weights_ = {
            {"relevance", 0.3},
            {"completeness", 0.3},
            {"coherence", 0.2},
            {"accuracy", 0.2}
        };
    } else {
        weights_ = std::move(weights);
    }
}

double QualityMetrics::measure(
    std::shared_ptr<core::Agent> agent,
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    // Unused parameters
    (void)agent;
    (void)use_llm_judge_;  // Reserved for future LLM-based judging
    (void)judge_model_;

    return rule_based_quality(input_message, output_message, ctx);
}

double QualityMetrics::rule_based_quality(
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    std::string input_text = to_lower(input_message.content_as_str());
    std::string output_text = to_lower(output_message.content_as_str());

    std::unordered_map<std::string, double> scores;

    // Relevance: Does response mention query terms?
    std::vector<std::string> query_terms = split_words(input_text);
    std::vector<std::string> output_terms = split_words(output_text);

    std::unordered_set<std::string> query_set(query_terms.begin(), query_terms.end());
    std::unordered_set<std::string> output_set(output_terms.begin(), output_terms.end());

    size_t overlap = 0;
    for (const auto& term : query_set) {
        if (output_set.count(term) > 0) {
            overlap++;
        }
    }

    double relevance = query_set.empty() ? 0.0 :
        static_cast<double>(overlap) / static_cast<double>(query_set.size());
    if (relevance > 1.0) {
        relevance = 1.0;
    }
    scores["relevance"] = relevance;

    // Completeness: Is response substantial?
    double expected_length = std::max(input_text.length() * 2, size_t(100)); // At least 2x input
    double completeness = output_text.length() / expected_length;
    if (completeness > 1.0) {
        completeness = 1.0;
    }
    scores["completeness"] = completeness;

    // Coherence: Basic checks
    bool has_structure = output_text.length() > 20; // Non-trivial response
    bool no_repetition = !has_repetition(output_text);

    double coherence = 0.0;
    if (has_structure) {
        coherence += 0.5;
    }
    if (no_repetition) {
        coherence += 0.5;
    }
    scores["coherence"] = coherence;

    // Accuracy: Compare to expected if available
    double accuracy = 0.5; // Neutral if no expected output
    if (ctx.contains("expected") && !ctx["expected"].is_null()) {
        std::string expected = ctx["expected"].is_string() ?
            to_lower(ctx["expected"].get<std::string>()) :
            to_lower(ctx["expected"].dump());

        if (output_text.find(expected) != std::string::npos) {
            accuracy = 1.0;
        } else {
            accuracy = 0.0;
        }
    }
    scores["accuracy"] = accuracy;

    // Weighted average
    double total_score = 0.0;
    for (const auto& pair : scores) {
        auto it = weights_.find(pair.first);
        if (it != weights_.end()) {
            total_score += pair.second * it->second;
        }
    }

    return total_score;
}

bool QualityMetrics::has_repetition(const std::string& text) {
    std::vector<std::string> words = split_words(text);

    if (words.size() < 10) {
        return false;
    }

    // Check for repeated phrases (3+ word sequences)
    std::unordered_set<std::string> seen_phrases;
    for (size_t i = 0; i < words.size() - 2; ++i) {
        std::string phrase = words[i] + " " + words[i+1] + " " + words[i+2];
        if (seen_phrases.count(phrase) > 0) {
            return true;
        }
        seen_phrases.insert(phrase);
    }

    return false;
}

nlohmann::json QualityMetrics::aggregate(const std::vector<double>& measurements) {
    nlohmann::json result;

    if (measurements.empty()) {
        result["mean"] = 0.0;
        result["min"] = 0.0;
        result["max"] = 0.0;
        result["std"] = 0.0;
        return result;
    }

    double mean = std::accumulate(measurements.begin(), measurements.end(), 0.0) /
                  static_cast<double>(measurements.size());

    double variance = 0.0;
    for (double x : measurements) {
        variance += (x - mean) * (x - mean);
    }
    variance /= static_cast<double>(measurements.size());
    double std_dev = std::sqrt(variance);

    double min_val = *std::min_element(measurements.begin(), measurements.end());
    double max_val = *std::max_element(measurements.begin(), measurements.end());

    result["mean"] = mean;
    result["min"] = min_val;
    result["max"] = max_val;
    result["std"] = std_dev;

    return result;
}

// PrecisionRecallStats implementation

double PrecisionRecallStats::precision() const {
    if (true_positives + false_positives == 0) {
        return 0.0;
    }
    return static_cast<double>(true_positives) /
           static_cast<double>(true_positives + false_positives);
}

double PrecisionRecallStats::recall() const {
    if (true_positives + false_negatives == 0) {
        return 0.0;
    }
    return static_cast<double>(true_positives) /
           static_cast<double>(true_positives + false_negatives);
}

double PrecisionRecallStats::f1_score() const {
    double p = precision();
    double r = recall();
    if (p + r == 0.0) {
        return 0.0;
    }
    return 2.0 * (p * r) / (p + r);
}

nlohmann::json PrecisionRecallStats::to_json() const {
    nlohmann::json j;
    j["true_positives"] = true_positives;
    j["false_positives"] = false_positives;
    j["false_negatives"] = false_negatives;
    j["true_negatives"] = true_negatives;
    j["precision"] = precision();
    j["recall"] = recall();
    j["f1_score"] = f1_score();
    return j;
}

// PrecisionRecallMetric implementation

double PrecisionRecallMetric::measure(
    std::shared_ptr<core::Agent> agent,
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    // Unused parameters
    (void)agent;
    (void)input_message;
    (void)output_message;

    if (ctx.is_null() || ctx.empty()) {
        return 1.0;
    }

    if (!ctx.contains("true_label") || !ctx.contains("predicted_label")) {
        return 1.0; // No labels = always correct
    }

    bool true_label = to_bool(ctx["true_label"]);
    bool predicted_label = to_bool(ctx["predicted_label"]);

    // Update confusion matrix
    if (true_label && predicted_label) {
        stats_.true_positives++;
        return 1.0;
    } else if (!true_label && predicted_label) {
        stats_.false_positives++;
        return 0.0;
    } else if (true_label && !predicted_label) {
        stats_.false_negatives++;
        return 0.0;
    } else { // !true_label && !predicted_label
        stats_.true_negatives++;
        return 1.0;
    }
}

nlohmann::json PrecisionRecallMetric::aggregate(const std::vector<double>& measurements) {
    // Measurements not used - we maintain confusion matrix internally
    (void)measurements;
    return stats_.to_json();
}

void PrecisionRecallMetric::reset() {
    stats_ = PrecisionRecallStats();
}

} // namespace evaluation
} // namespace agenkit
