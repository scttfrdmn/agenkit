/**
 * @file regression.cpp
 * @brief Implementation of regression detection for agent performance monitoring
 */

#include "agenkit/evaluation/regression.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <iomanip>
#include <sstream>

namespace agenkit {
namespace evaluation {

// Helper functions (same as before)
static std::string time_point_to_rfc3339(std::chrono::system_clock::time_point tp) {
    auto time_t_value = std::chrono::system_clock::to_time_t(tp);
    std::tm tm_value = *std::gmtime(&time_t_value);

    std::ostringstream oss;
    oss << std::put_time(&tm_value, "%Y-%m-%dT%H:%M:%S");

    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        tp.time_since_epoch()
    ) % 1000;
    oss << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';

    return oss.str();
}

static std::chrono::system_clock::time_point rfc3339_to_time_point(const std::string& str) {
    std::tm tm_value = {};
    std::istringstream iss(str);
    iss >> std::get_time(&tm_value, "%Y-%m-%dT%H:%M:%S");

    auto tp = std::chrono::system_clock::from_time_t(std::mktime(&tm_value));

    size_t dot_pos = str.find('.');
    if (dot_pos != std::string::npos) {
        size_t end_pos = str.find('Z', dot_pos);
        if (end_pos != std::string::npos) {
            std::string ms_str = str.substr(dot_pos + 1, end_pos - dot_pos - 1);
            int ms = std::stoi(ms_str);
            tp += std::chrono::milliseconds(ms);
        }
    }

    return tp;
}

// Severity conversion functions

std::string severity_to_string(Severity severity) {
    switch (severity) {
        case Severity::None:
            return "none";
        case Severity::Minor:
            return "minor";
        case Severity::Moderate:
            return "moderate";
        case Severity::Major:
            return "major";
        case Severity::Critical:
            return "critical";
        default:
            return "none";
    }
}

Severity severity_from_string(const std::string& str) {
    if (str == "none") return Severity::None;
    if (str == "minor") return Severity::Minor;
    if (str == "moderate") return Severity::Moderate;
    if (str == "major") return Severity::Major;
    if (str == "critical") return Severity::Critical;
    return Severity::None;
}

// EvaluationResult implementation

nlohmann::json EvaluationResult::to_json() const {
    nlohmann::json j;
    j["evaluation_id"] = evaluation_id;
    j["agent_name"] = agent_name;
    j["timestamp"] = time_point_to_rfc3339(timestamp);

    if (accuracy.has_value()) {
        j["accuracy"] = *accuracy;
    }
    if (quality_score.has_value()) {
        j["quality_score"] = *quality_score;
    }
    if (avg_latency_ms.has_value()) {
        j["avg_latency_ms"] = *avg_latency_ms;
    }
    if (context_length.has_value()) {
        j["context_length"] = *context_length;
    }
    if (compression_ratio.has_value()) {
        j["compression_ratio"] = *compression_ratio;
    }

    j["metadata"] = metadata;

    return j;
}

EvaluationResult EvaluationResult::from_json(const nlohmann::json& j) {
    EvaluationResult result;
    result.evaluation_id = j["evaluation_id"].get<std::string>();
    result.agent_name = j["agent_name"].get<std::string>();
    result.timestamp = rfc3339_to_time_point(j["timestamp"].get<std::string>());

    if (j.contains("accuracy") && !j["accuracy"].is_null()) {
        result.accuracy = j["accuracy"].get<double>();
    }
    if (j.contains("quality_score") && !j["quality_score"].is_null()) {
        result.quality_score = j["quality_score"].get<double>();
    }
    if (j.contains("avg_latency_ms") && !j["avg_latency_ms"].is_null()) {
        result.avg_latency_ms = j["avg_latency_ms"].get<double>();
    }
    if (j.contains("context_length") && !j["context_length"].is_null()) {
        result.context_length = j["context_length"].get<int>();
    }
    if (j.contains("compression_ratio") && !j["compression_ratio"].is_null()) {
        result.compression_ratio = j["compression_ratio"].get<double>();
    }

    result.metadata = j.value("metadata", nlohmann::json::object());

    return result;
}

// Regression implementation

nlohmann::json Regression::to_json() const {
    nlohmann::json j;
    j["metric_name"] = metric_name;
    j["baseline_value"] = baseline_value;
    j["current_value"] = current_value;
    j["degradation_percent"] = degradation_percent;
    j["severity"] = severity_to_string(severity);
    j["timestamp"] = time_point_to_rfc3339(timestamp);
    j["context"] = context;
    return j;
}

// RegressionDetector implementation

RegressionDetector::RegressionDetector(
    std::unordered_map<std::string, double> thresholds,
    std::optional<EvaluationResult> baseline
)
    : baseline_(baseline)
{
    if (thresholds.empty()) {
        // Default thresholds
        thresholds_ = {
            {"accuracy", 0.10},       // 10% degradation threshold
            {"quality", 0.10},
            {"latency", 0.20},        // 20% slower acceptable
            {"context_length", 0.30}  // 30% larger context acceptable
        };
    } else {
        thresholds_ = std::move(thresholds);
    }
}

void RegressionDetector::set_baseline(const EvaluationResult& result) {
    baseline_ = result;
}

std::vector<Regression> RegressionDetector::detect(const EvaluationResult& result, bool store_history) {
    if (store_history) {
        history_.push_back(result);
    }

    if (!baseline_.has_value()) {
        // No baseline = no regressions
        return {};
    }

    std::vector<Regression> regressions;

    // Check accuracy
    if (result.accuracy.has_value() && baseline_->accuracy.has_value()) {
        auto reg = check_metric("accuracy", *baseline_->accuracy, *result.accuracy, true);
        if (reg.has_value()) {
            regressions.push_back(*reg);
        }
    }

    // Check quality_score
    if (result.quality_score.has_value() && baseline_->quality_score.has_value()) {
        auto reg = check_metric("quality", *baseline_->quality_score, *result.quality_score, true);
        if (reg.has_value()) {
            regressions.push_back(*reg);
        }
    }

    // Check latency (lower is better)
    if (result.avg_latency_ms.has_value() && baseline_->avg_latency_ms.has_value()) {
        auto reg = check_metric("latency", *baseline_->avg_latency_ms, *result.avg_latency_ms, false);
        if (reg.has_value()) {
            regressions.push_back(*reg);
        }
    }

    // Check context length (lower is better)
    if (result.context_length.has_value() && baseline_->context_length.has_value()) {
        auto reg = check_metric("context_length",
                               static_cast<double>(*baseline_->context_length),
                               static_cast<double>(*result.context_length),
                               false);
        if (reg.has_value()) {
            regressions.push_back(*reg);
        }
    }

    // Check compression ratio (higher is better)
    if (result.compression_ratio.has_value() && baseline_->compression_ratio.has_value()) {
        auto reg = check_metric("compression_ratio",
                               *baseline_->compression_ratio,
                               *result.compression_ratio,
                               true);
        if (reg.has_value()) {
            regressions.push_back(*reg);
        }
    }

    return regressions;
}

std::optional<Regression> RegressionDetector::check_metric(
    const std::string& name,
    double baseline,
    double current,
    bool higher_is_better
) const {
    double degradation;

    if (baseline == 0.0) {
        // Avoid division by zero
        if (current == 0.0) {
            return std::nullopt;
        }
        degradation = higher_is_better ? 1.0 : -1.0;
    } else {
        if (higher_is_better) {
            // For accuracy, quality: lower is worse
            degradation = (baseline - current) / baseline;
        } else {
            // For latency, context_length: higher is worse
            degradation = (current - baseline) / baseline;
        }
    }

    // Check if exceeds threshold
    double threshold = 0.10; // Default
    auto it = thresholds_.find(name);
    if (it != thresholds_.end()) {
        threshold = it->second;
    }

    if (degradation > threshold) {
        Severity severity = calculate_severity(degradation);

        Regression reg;
        reg.metric_name = name;
        reg.baseline_value = baseline;
        reg.current_value = current;
        reg.degradation_percent = degradation * 100.0;
        reg.severity = severity;
        reg.timestamp = std::chrono::system_clock::now();
        reg.context = {
            {"threshold_percent", threshold * 100.0},
            {"higher_is_better", higher_is_better}
        };

        return reg;
    }

    return std::nullopt;
}

Severity RegressionDetector::calculate_severity(double degradation) const {
    if (degradation < 0.10) {
        return Severity::None;
    } else if (degradation < 0.20) {
        return Severity::Minor;
    } else if (degradation < 0.50) {
        return Severity::Moderate;
    } else {
        return Severity::Critical;
    }
}

std::optional<nlohmann::json> RegressionDetector::get_trend(const std::string& metric_name, size_t window) const {
    if (history_.size() < 2) {
        return std::nullopt;
    }

    // Get recent results
    size_t start = history_.size() > window ? history_.size() - window : 0;
    std::vector<EvaluationResult> recent(history_.begin() + start, history_.end());

    // Extract metric values
    std::vector<double> values;
    for (const auto& result : recent) {
        if (metric_name == "accuracy" && result.accuracy.has_value()) {
            values.push_back(*result.accuracy);
        } else if (metric_name == "quality" && result.quality_score.has_value()) {
            values.push_back(*result.quality_score);
        } else if (metric_name == "latency" && result.avg_latency_ms.has_value()) {
            values.push_back(*result.avg_latency_ms);
        } else if (metric_name == "context_length" && result.context_length.has_value()) {
            values.push_back(static_cast<double>(*result.context_length));
        }
    }

    if (values.size() < 2) {
        return std::nullopt;
    }

    // Calculate trend using linear regression
    double n = static_cast<double>(values.size());

    std::vector<double> x(values.size());
    for (size_t i = 0; i < x.size(); ++i) {
        x[i] = static_cast<double>(i);
    }

    double x_mean = std::accumulate(x.begin(), x.end(), 0.0) / n;
    double y_mean = std::accumulate(values.begin(), values.end(), 0.0) / n;

    // Linear regression slope
    double numerator = 0.0;
    double denominator = 0.0;
    for (size_t i = 0; i < values.size(); ++i) {
        numerator += (x[i] - x_mean) * (values[i] - y_mean);
        denominator += (x[i] - x_mean) * (x[i] - x_mean);
    }

    double slope = 0.0;
    if (denominator != 0.0) {
        slope = numerator / denominator;
    }

    // Variance
    double variance = 0.0;
    for (double v : values) {
        variance += (v - y_mean) * (v - y_mean);
    }
    variance /= n;

    std::string direction = "stable";
    if (slope > 0) {
        direction = "improving";
    } else if (slope < 0) {
        direction = "degrading";
    }

    nlohmann::json trend;
    trend["metric"] = metric_name;
    trend["slope"] = slope;
    trend["direction"] = direction;
    trend["variance"] = variance;
    trend["current"] = values.back();
    trend["mean"] = y_mean;
    trend["window_size"] = values.size();

    return trend;
}

std::unordered_map<std::string, std::unordered_map<std::string, double>>
RegressionDetector::compare_results(const EvaluationResult& result_a, const EvaluationResult& result_b) const {
    std::unordered_map<std::string, std::unordered_map<std::string, double>> comparisons;

    // Compare accuracy
    if (result_a.accuracy.has_value() && result_b.accuracy.has_value()) {
        double change = *result_b.accuracy - *result_a.accuracy;
        double change_percent = 0.0;
        if (*result_a.accuracy != 0.0) {
            change_percent = change / *result_a.accuracy * 100.0;
        }
        comparisons["accuracy"] = {
            {"baseline", *result_a.accuracy},
            {"current", *result_b.accuracy},
            {"change", change},
            {"change_percent", change_percent}
        };
    }

    // Compare quality
    if (result_a.quality_score.has_value() && result_b.quality_score.has_value()) {
        double change = *result_b.quality_score - *result_a.quality_score;
        double change_percent = 0.0;
        if (*result_a.quality_score != 0.0) {
            change_percent = change / *result_a.quality_score * 100.0;
        }
        comparisons["quality"] = {
            {"baseline", *result_a.quality_score},
            {"current", *result_b.quality_score},
            {"change", change},
            {"change_percent", change_percent}
        };
    }

    // Compare latency
    if (result_a.avg_latency_ms.has_value() && result_b.avg_latency_ms.has_value()) {
        double change = *result_b.avg_latency_ms - *result_a.avg_latency_ms;
        double change_percent = 0.0;
        if (*result_a.avg_latency_ms != 0.0) {
            change_percent = change / *result_a.avg_latency_ms * 100.0;
        }
        comparisons["latency"] = {
            {"baseline", *result_a.avg_latency_ms},
            {"current", *result_b.avg_latency_ms},
            {"change", change},
            {"change_percent", change_percent}
        };
    }

    return comparisons;
}

void RegressionDetector::clear_history() {
    history_.clear();
}

nlohmann::json RegressionDetector::get_summary() const {
    nlohmann::json summary;

    summary["has_baseline"] = baseline_.has_value();
    if (baseline_.has_value()) {
        summary["baseline_id"] = baseline_->evaluation_id;
    } else {
        summary["baseline_id"] = nullptr;
    }

    summary["history_count"] = history_.size();

    nlohmann::json thresholds_json;
    for (const auto& pair : thresholds_) {
        thresholds_json[pair.first] = pair.second;
    }
    summary["thresholds"] = thresholds_json;

    return summary;
}

} // namespace evaluation
} // namespace agenkit
