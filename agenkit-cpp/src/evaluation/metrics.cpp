/**
 * @file metrics.cpp
 * @brief Implementation of metrics tracking for agent evaluation
 */

#include "agenkit/evaluation/metrics.hpp"
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <limits>
#include <cmath>

namespace agenkit {
namespace evaluation {

// SessionStatus conversion functions

std::string session_status_to_string(SessionStatus status) {
    switch (status) {
        case SessionStatus::Running:
            return "running";
        case SessionStatus::Completed:
            return "completed";
        case SessionStatus::Failed:
            return "failed";
        case SessionStatus::Timeout:
            return "timeout";
        case SessionStatus::Cancelled:
            return "cancelled";
        default:
            return "unknown";
    }
}

SessionStatus session_status_from_string(const std::string& str) {
    if (str == "running") return SessionStatus::Running;
    if (str == "completed") return SessionStatus::Completed;
    if (str == "failed") return SessionStatus::Failed;
    if (str == "timeout") return SessionStatus::Timeout;
    if (str == "cancelled") return SessionStatus::Cancelled;
    return SessionStatus::Running; // Default
}

// MetricType conversion functions

std::string metric_type_to_string(MetricType type) {
    switch (type) {
        case MetricType::SuccessRate:
            return "success_rate";
        case MetricType::QualityScore:
            return "quality_score";
        case MetricType::Cost:
            return "cost";
        case MetricType::Duration:
            return "duration";
        case MetricType::ErrorRate:
            return "error_rate";
        case MetricType::TaskCompletion:
            return "task_completion";
        case MetricType::Custom:
            return "custom";
        default:
            return "custom";
    }
}

MetricType metric_type_from_string(const std::string& str) {
    if (str == "success_rate") return MetricType::SuccessRate;
    if (str == "quality_score") return MetricType::QualityScore;
    if (str == "cost") return MetricType::Cost;
    if (str == "duration") return MetricType::Duration;
    if (str == "error_rate") return MetricType::ErrorRate;
    if (str == "task_completion") return MetricType::TaskCompletion;
    return MetricType::Custom;
}

// Helper to convert time_point to RFC3339 string
static std::string time_point_to_rfc3339(std::chrono::system_clock::time_point tp) {
    auto time_t_value = std::chrono::system_clock::to_time_t(tp);
    std::tm tm_value = *std::gmtime(&time_t_value);

    std::ostringstream oss;
    oss << std::put_time(&tm_value, "%Y-%m-%dT%H:%M:%S");

    // Add milliseconds
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        tp.time_since_epoch()
    ) % 1000;
    oss << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';

    return oss.str();
}

// Helper to convert RFC3339 string to time_point
static std::chrono::system_clock::time_point rfc3339_to_time_point(const std::string& str) {
    std::tm tm_value = {};
    std::istringstream iss(str);
    iss >> std::get_time(&tm_value, "%Y-%m-%dT%H:%M:%S");

    auto tp = std::chrono::system_clock::from_time_t(std::mktime(&tm_value));

    // Try to parse milliseconds if present
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

// MetricMeasurement implementation

MetricMeasurement::MetricMeasurement(
    std::string name,
    double value,
    MetricType type,
    std::optional<std::chrono::system_clock::time_point> timestamp,
    nlohmann::json metadata
)
    : name_(std::move(name))
    , value_(value)
    , type_(type)
    , timestamp_(timestamp.value_or(std::chrono::system_clock::now()))
    , metadata_(std::move(metadata))
{
}

nlohmann::json MetricMeasurement::to_json() const {
    nlohmann::json j;
    j["name"] = name_;
    j["value"] = value_;
    j["type"] = metric_type_to_string(type_);
    j["timestamp"] = time_point_to_rfc3339(timestamp_);
    j["metadata"] = metadata_;
    return j;
}

MetricMeasurement MetricMeasurement::from_json(const nlohmann::json& j) {
    return MetricMeasurement(
        j["name"].get<std::string>(),
        j["value"].get<double>(),
        metric_type_from_string(j["type"].get<std::string>()),
        rfc3339_to_time_point(j["timestamp"].get<std::string>()),
        j.value("metadata", nlohmann::json::object())
    );
}

// ErrorRecord implementation

ErrorRecord::ErrorRecord(
    std::string type,
    std::string message,
    nlohmann::json details,
    std::optional<std::chrono::system_clock::time_point> timestamp
)
    : type_(std::move(type))
    , message_(std::move(message))
    , details_(std::move(details))
    , timestamp_(timestamp.value_or(std::chrono::system_clock::now()))
{
}

nlohmann::json ErrorRecord::to_json() const {
    nlohmann::json j;
    j["type"] = type_;
    j["message"] = message_;
    j["details"] = details_;
    j["timestamp"] = time_point_to_rfc3339(timestamp_);
    return j;
}

ErrorRecord ErrorRecord::from_json(const nlohmann::json& j) {
    return ErrorRecord(
        j["type"].get<std::string>(),
        j["message"].get<std::string>(),
        j.value("details", nlohmann::json::object()),
        rfc3339_to_time_point(j["timestamp"].get<std::string>())
    );
}

// SessionResult implementation

SessionResult::SessionResult(std::string session_id, std::string agent_name)
    : session_id_(std::move(session_id))
    , agent_name_(std::move(agent_name))
    , status_(SessionStatus::Running)
    , start_time_(std::chrono::system_clock::now())
    , end_time_(std::nullopt)
    , metadata_(nlohmann::json::object())
{
}

void SessionResult::add_metric_measurement(const MetricMeasurement& measurement) {
    measurements_.push_back(measurement);
}

void SessionResult::add_error(const std::string& type, const std::string& message,
                              const nlohmann::json& details) {
    errors_.emplace_back(type, message, details);
}

void SessionResult::set_status(SessionStatus status) {
    status_ = status;
    if (status != SessionStatus::Running && !end_time_.has_value()) {
        end_time_ = std::chrono::system_clock::now();
    }
}

const MetricMeasurement* SessionResult::get_metric(const std::string& name) const {
    for (const auto& m : measurements_) {
        if (m.name() == name) {
            return &m;
        }
    }
    return nullptr;
}

std::vector<MetricMeasurement> SessionResult::get_metrics_by_type(MetricType type) const {
    std::vector<MetricMeasurement> result;
    for (const auto& m : measurements_) {
        if (m.type() == type) {
            result.push_back(m);
        }
    }
    return result;
}

std::optional<double> SessionResult::duration_seconds() const {
    if (!end_time_.has_value()) {
        return std::nullopt;
    }

    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        *end_time_ - start_time_
    );
    return duration.count() / 1000000.0;
}

nlohmann::json SessionResult::to_json() const {
    nlohmann::json j;
    j["session_id"] = session_id_;
    j["agent_name"] = agent_name_;
    j["status"] = session_status_to_string(status_);
    j["start_time"] = time_point_to_rfc3339(start_time_);

    if (end_time_.has_value()) {
        j["end_time"] = time_point_to_rfc3339(*end_time_);
    } else {
        j["end_time"] = nullptr;
    }

    nlohmann::json measurements_json = nlohmann::json::array();
    for (const auto& m : measurements_) {
        measurements_json.push_back(m.to_json());
    }
    j["measurements"] = measurements_json;

    nlohmann::json errors_json = nlohmann::json::array();
    for (const auto& e : errors_) {
        errors_json.push_back(e.to_json());
    }
    j["errors"] = errors_json;

    j["metadata"] = metadata_;

    return j;
}

SessionResult SessionResult::from_json(const nlohmann::json& j) {
    SessionResult result(
        j["session_id"].get<std::string>(),
        j["agent_name"].get<std::string>()
    );

    result.status_ = session_status_from_string(j["status"].get<std::string>());
    result.start_time_ = rfc3339_to_time_point(j["start_time"].get<std::string>());

    if (!j["end_time"].is_null()) {
        result.end_time_ = rfc3339_to_time_point(j["end_time"].get<std::string>());
    }

    for (const auto& m_json : j["measurements"]) {
        result.measurements_.push_back(MetricMeasurement::from_json(m_json));
    }

    for (const auto& e_json : j["errors"]) {
        result.errors_.push_back(ErrorRecord::from_json(e_json));
    }

    result.metadata_ = j.value("metadata", nlohmann::json::object());

    return result;
}

// MetricsCollector implementation

MetricsCollector::MetricsCollector() = default;

void MetricsCollector::add_result(const SessionResult& result) {
    std::lock_guard<std::mutex> lock(mutex_);
    results_.push_back(result);
}

nlohmann::json MetricsCollector::get_statistics() const {
    std::lock_guard<std::mutex> lock(mutex_);

    nlohmann::json stats;

    size_t total_sessions = results_.size();
    stats["session_count"] = total_sessions;

    if (total_sessions == 0) {
        return stats;
    }

    size_t completed_count = 0;
    size_t failed_count = 0;
    double total_duration = 0.0;
    size_t duration_count = 0;
    size_t total_errors = 0;

    for (const auto& result : results_) {
        switch (result.status()) {
            case SessionStatus::Completed:
                completed_count++;
                break;
            case SessionStatus::Failed:
            case SessionStatus::Timeout:
            case SessionStatus::Cancelled:
                failed_count++;
                break;
            default:
                break;
        }

        auto duration = result.duration_seconds();
        if (duration.has_value()) {
            total_duration += *duration;
            duration_count++;
        }

        total_errors += result.errors().size();
    }

    stats["completed_count"] = completed_count;
    stats["failed_count"] = failed_count;
    stats["success_rate"] = static_cast<double>(completed_count) / static_cast<double>(total_sessions);

    if (duration_count > 0) {
        stats["avg_duration"] = total_duration / static_cast<double>(duration_count);
    }

    stats["total_errors"] = total_errors;
    stats["avg_errors_per_session"] = static_cast<double>(total_errors) / static_cast<double>(total_sessions);

    return stats;
}

nlohmann::json MetricsCollector::get_metric_aggregates(const std::string& metric_name) const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<double> values;

    for (const auto& result : results_) {
        for (const auto& measurement : result.measurements()) {
            if (measurement.name() == metric_name) {
                values.push_back(measurement.value());
            }
        }
    }

    if (values.empty()) {
        nlohmann::json j;
        j["count"] = 0;
        return j;
    }

    double sum = 0.0;
    double min_val = std::numeric_limits<double>::max();
    double max_val = std::numeric_limits<double>::lowest();

    for (double v : values) {
        sum += v;
        min_val = std::min(min_val, v);
        max_val = std::max(max_val, v);
    }

    nlohmann::json j;
    j["count"] = values.size();
    j["sum"] = sum;
    j["mean"] = sum / static_cast<double>(values.size());
    j["min"] = min_val;
    j["max"] = max_val;

    return j;
}

std::vector<SessionResult> MetricsCollector::get_results() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return results_; // Returns a copy
}

void MetricsCollector::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    results_.clear();
}

// Helper functions

MetricMeasurement create_quality_metric(
    const std::string& name,
    double score,
    double max_score,
    nlohmann::json metadata
) {
    double normalized_score = score / max_score;
    if (normalized_score > 1.0) {
        normalized_score = 1.0;
    }

    metadata["raw_score"] = score;
    metadata["max_score"] = max_score;

    return MetricMeasurement(name, normalized_score, MetricType::QualityScore, std::nullopt, metadata);
}

MetricMeasurement create_cost_metric(
    double cost,
    const std::string& currency,
    nlohmann::json metadata
) {
    metadata["currency"] = currency;
    return MetricMeasurement("total_cost", cost, MetricType::Cost, std::nullopt, metadata);
}

MetricMeasurement create_duration_metric(
    double duration_seconds,
    nlohmann::json metadata
) {
    metadata["duration_hours"] = duration_seconds / 3600.0;
    return MetricMeasurement("duration", duration_seconds, MetricType::Duration, std::nullopt, metadata);
}

} // namespace evaluation
} // namespace agenkit
