/**
 * @file context_metrics.cpp
 * @brief Implementation of context-aware metrics for extreme-scale evaluation
 */

#include "agenkit/evaluation/context_metrics.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <sstream>
#include <future>
#include <iomanip>

namespace agenkit {
namespace evaluation {

// Helper functions

static std::string to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

static double calculate_variance(const std::vector<double>& values, double mean) {
    if (values.empty()) {
        return 0.0;
    }
    double variance = 0.0;
    for (double val : values) {
        double diff = val - mean;
        variance += diff * diff;
    }
    return variance / static_cast<double>(values.size());
}

static std::string time_point_to_iso(std::chrono::system_clock::time_point tp) {
    auto time_t = std::chrono::system_clock::to_time_t(tp);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S") << "Z";
    return ss.str();
}

static std::chrono::system_clock::time_point time_point_from_iso(const std::string& iso) {
    // Simplified: just return current time if parsing fails
    // In production, use a proper ISO 8601 parser
    std::tm tm = {};
    std::istringstream ss(iso);
    ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%S");
    if (ss.fail()) {
        return std::chrono::system_clock::now();
    }
    auto time_t = std::mktime(&tm);
    return std::chrono::system_clock::from_time_t(time_t);
}

// ContextMetrics implementation

double ContextMetrics::measure(
    std::shared_ptr<core::Agent> agent,
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    // Unused parameters
    (void)agent;
    (void)output_message;

    // Check message metadata first
    if (input_message.metadata().contains("context_length")) {
        const auto& cl = input_message.metadata()["context_length"];
        if (cl.is_number()) {
            return cl.get<double>();
        } else if (cl.is_string()) {
            return std::stod(cl.get<std::string>());
        }
    }

    // Check context for conversation history
    if (ctx.contains("conversation_history") && ctx["conversation_history"].is_array()) {
        size_t total_tokens = 0;
        for (const auto& msg_json : ctx["conversation_history"]) {
            if (msg_json.contains("content")) {
                std::string content = msg_json["content"].is_string() ?
                    msg_json["content"].get<std::string>() :
                    msg_json["content"].dump();
                total_tokens += estimate_tokens(content);
            }
        }
        return static_cast<double>(total_tokens);
    }

    // Check context for direct context_length
    if (ctx.contains("context_length")) {
        const auto& cl = ctx["context_length"];
        if (cl.is_number()) {
            return cl.get<double>();
        } else if (cl.is_string()) {
            return std::stod(cl.get<std::string>());
        }
    }

    return 0.0;
}

nlohmann::json ContextMetrics::aggregate(const std::vector<double>& measurements) {
    nlohmann::json result;

    if (measurements.empty()) {
        result["mean"] = 0.0;
        result["min"] = 0.0;
        result["max"] = 0.0;
        result["final"] = 0.0;
        result["growth_rate"] = 0.0;
        return result;
    }

    double sum = std::accumulate(measurements.begin(), measurements.end(), 0.0);
    double mean = sum / static_cast<double>(measurements.size());

    result["mean"] = mean;
    result["min"] = *std::min_element(measurements.begin(), measurements.end());
    result["max"] = *std::max_element(measurements.begin(), measurements.end());
    result["final"] = measurements.back();

    // Calculate growth rate: (final - initial) / num_measurements
    if (measurements.size() > 1) {
        result["growth_rate"] = (measurements.back() - measurements.front()) /
                                static_cast<double>(measurements.size());
    } else {
        result["growth_rate"] = 0.0;
    }

    return result;
}

size_t ContextMetrics::estimate_tokens(const std::string& text) const {
    // Rough estimation: ~4 characters per token
    return text.length() / 4;
}

// CompressionStats implementation

CompressionStats::CompressionStats()
    : raw_tokens(0)
    , compressed_tokens(0)
    , compression_ratio(1.0)
    , retrieval_accuracy(0.0)
    , context_length_tested(0)
    , timestamp(std::chrono::system_clock::now())
{
}

CompressionStats::CompressionStats(
    size_t raw,
    size_t compressed,
    double ratio,
    double accuracy,
    size_t length
)
    : raw_tokens(raw)
    , compressed_tokens(compressed)
    , compression_ratio(ratio)
    , retrieval_accuracy(accuracy)
    , context_length_tested(length)
    , timestamp(std::chrono::system_clock::now())
{
}

nlohmann::json CompressionStats::to_json() const {
    nlohmann::json j;
    j["raw_tokens"] = raw_tokens;
    j["compressed_tokens"] = compressed_tokens;
    j["compression_ratio"] = compression_ratio;
    j["retrieval_accuracy"] = retrieval_accuracy;
    j["context_length_tested"] = context_length_tested;
    j["timestamp"] = time_point_to_iso(timestamp);
    return j;
}

CompressionStats CompressionStats::from_json(const nlohmann::json& j) {
    CompressionStats stats(
        j.value("raw_tokens", 0),
        j.value("compressed_tokens", 0),
        j.value("compression_ratio", 0.0),
        j.value("retrieval_accuracy", 0.0),
        j.value("context_length_tested", 0)
    );

    if (j.contains("timestamp") && j["timestamp"].is_string()) {
        stats.timestamp = time_point_from_iso(j["timestamp"].get<std::string>());
    }

    return stats;
}

// CompressionMetrics implementation

CompressionMetrics::CompressionMetrics(
    std::vector<size_t> test_lengths,
    size_t needle_count
)
    : test_lengths_(std::move(test_lengths))
    , needle_count_(needle_count)
{
}

double CompressionMetrics::measure(
    std::shared_ptr<core::Agent> agent,
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    // Unused parameters
    (void)agent;
    (void)input_message;

    // Check output metadata for compression_ratio
    if (output_message.metadata().contains("compression_ratio")) {
        const auto& cr = output_message.metadata()["compression_ratio"];
        if (cr.is_number()) {
            return cr.get<double>();
        } else if (cr.is_string()) {
            return std::stod(cr.get<std::string>());
        }
    }

    // Check context for compression stats
    if (ctx.contains("compression_stats")) {
        const auto& stats = ctx["compression_stats"];
        if (stats.contains("raw_tokens") && stats.contains("compressed_tokens")) {
            double raw = stats["raw_tokens"].get<double>();
            double compressed = stats["compressed_tokens"].get<double>();
            if (compressed > 0) {
                return raw / compressed;
            }
        }
    }

    // No compression
    return 1.0;
}

nlohmann::json CompressionMetrics::aggregate(const std::vector<double>& measurements) {
    nlohmann::json result;

    if (measurements.empty()) {
        result["mean"] = 1.0;
        result["min"] = 1.0;
        result["max"] = 1.0;
        result["std"] = 0.0;
        return result;
    }

    double sum = std::accumulate(measurements.begin(), measurements.end(), 0.0);
    double mean = sum / static_cast<double>(measurements.size());

    double variance = calculate_variance(measurements, mean);
    double std_dev = std::sqrt(variance);

    result["mean"] = mean;
    result["min"] = *std::min_element(measurements.begin(), measurements.end());
    result["max"] = *std::max_element(measurements.begin(), measurements.end());
    result["std"] = std_dev;

    return result;
}

std::future<std::map<size_t, CompressionStats>> CompressionMetrics::evaluate_at_lengths(
    std::shared_ptr<core::Agent> agent,
    const std::string& session_id,
    const std::vector<std::string>& needle_content
) {
    return std::async(std::launch::async, [this, agent, session_id, needle_content]() {
        std::map<size_t, CompressionStats> results;

        std::vector<std::string> needles = needle_content.empty() ?
            default_needles() : needle_content;

        for (size_t length : test_lengths_) {
            // Generate test context with needles
            auto test_messages = generate_test_context(length, needles);

            // Process messages through agent to build context
            for (const auto& msg_content : test_messages) {
                core::Message msg("user", msg_content);
                msg.with_metadata("session_id", session_id);
                auto response_future = agent->process(msg);
                // Wait for response (blocking on future)
                try {
                    auto response_result = response_future.get();
                    // Just building context, don't need to check response
                    (void)response_result;
                } catch (...) {
                    // Continue even if individual messages fail
                }
            }

            // Get compression stats from agent metadata if available
            size_t raw_tokens = length;
            size_t compressed_tokens = length;  // Default: no compression
            double compression_ratio = 1.0;

            // Note: In real implementation, agent would provide get_compression_stats()
            // For now, we check message metadata from last response

            // Test retrieval accuracy
            double accuracy_future = test_retrieval(agent, session_id, needles).get();

            results[length] = CompressionStats(
                raw_tokens,
                compressed_tokens,
                compression_ratio,
                accuracy_future,
                length
            );
        }

        return results;
    });
}

std::vector<std::string> CompressionMetrics::generate_test_context(
    size_t target_tokens,
    const std::vector<std::string>& needles
) {
    std::vector<std::string> messages;
    size_t current_tokens = 0;

    // Calculate needle insertion intervals
    size_t needle_interval = needles.empty() ? target_tokens :
        target_tokens / (needles.size() + 1);
    size_t next_needle_at = needle_interval;
    size_t needle_idx = 0;

    // Generate filler content (~80 tokens per filler block)
    std::string filler = "This is filler content for context expansion. "
                         "It helps us reach extreme scale for testing. ";
    for (int i = 0; i < 18; ++i) {  // ~20 words * 4 = 80 tokens
        filler += filler;
    }
    size_t filler_tokens = filler.length() / 4;

    while (current_tokens < target_tokens) {
        // Insert needle if at interval
        if (current_tokens >= next_needle_at && needle_idx < needles.size()) {
            messages.push_back(needles[needle_idx]);
            current_tokens += needles[needle_idx].length() / 4;
            needle_idx++;
            next_needle_at += needle_interval;
        } else {
            // Add filler
            messages.push_back(filler);
            current_tokens += filler_tokens;
        }
    }

    return messages;
}

std::future<double> CompressionMetrics::test_retrieval(
    std::shared_ptr<core::Agent> agent,
    const std::string& session_id,
    const std::vector<std::string>& needles
) {
    return std::async(std::launch::async, [agent, session_id, needles]() {
        if (needles.empty()) {
            return 0.0;
        }

        size_t correct = 0;

        for (const auto& needle : needles) {
            // Ask agent to retrieve the fact
            std::string needle_prefix = needle.substr(0, std::min(size_t(50), needle.length()));
            std::string query = "Recall: What was mentioned about " + needle_prefix + "?";

            core::Message query_msg("user", query);
            query_msg.with_metadata("session_id", session_id);
            auto response_future = agent->process(query_msg);

            try {
                auto response_result = response_future.get();
                if (response_result.is_ok()) {
                    std::string response_content = response_result.unwrap().content_as_str();
                    std::string needle_lower = to_lower(needle);
                    std::string response_lower = to_lower(response_content);

                    // Check if response contains needle content
                    if (response_lower.find(needle_lower) != std::string::npos) {
                        correct++;
                    }
                }
            } catch (...) {
                // Failed to retrieve - count as incorrect
            }
        }

        return static_cast<double>(correct) / static_cast<double>(needles.size());
    });
}

std::vector<std::string> CompressionMetrics::default_needles() const {
    std::vector<std::string> needles;
    for (size_t i = 0; i < needle_count_; ++i) {
        std::ostringstream oss;
        oss << "NEEDLE FACT " << i << ": The secret code is ALPHA-"
            << std::setw(4) << std::setfill('0') << i << "-OMEGA.";
        needles.push_back(oss.str());
    }
    return needles;
}

// LatencyMetric implementation

double LatencyMetric::measure(
    std::shared_ptr<core::Agent> agent,
    const core::Message& input_message,
    const core::Message& output_message,
    const nlohmann::json& ctx
) {
    // Unused parameters
    (void)agent;
    (void)input_message;
    (void)output_message;

    if (ctx.contains("latency_ms")) {
        const auto& latency = ctx["latency_ms"];
        if (latency.is_number()) {
            return latency.get<double>();
        } else if (latency.is_string()) {
            return std::stod(latency.get<std::string>());
        }
    }

    return 0.0;
}

nlohmann::json LatencyMetric::aggregate(const std::vector<double>& measurements) {
    nlohmann::json result;

    if (measurements.empty()) {
        result["mean"] = 0.0;
        result["p50"] = 0.0;
        result["p95"] = 0.0;
        result["p99"] = 0.0;
        result["min"] = 0.0;
        result["max"] = 0.0;
        return result;
    }

    // Sort measurements for percentile calculation
    std::vector<double> sorted = measurements;
    std::sort(sorted.begin(), sorted.end());

    double sum = std::accumulate(measurements.begin(), measurements.end(), 0.0);
    double mean = sum / static_cast<double>(measurements.size());

    result["mean"] = mean;
    result["p50"] = calculate_percentile(sorted, 0.50);
    result["p95"] = calculate_percentile(sorted, 0.95);
    result["p99"] = calculate_percentile(sorted, 0.99);
    result["min"] = sorted.front();
    result["max"] = sorted.back();

    return result;
}

double LatencyMetric::calculate_percentile(
    const std::vector<double>& sorted_values,
    double percentile
) const {
    if (sorted_values.empty()) {
        return 0.0;
    }

    size_t n = sorted_values.size();
    double index = percentile * static_cast<double>(n);

    // Handle edge cases
    if (index <= 0) {
        return sorted_values.front();
    }
    if (index >= static_cast<double>(n) - 1) {
        return sorted_values.back();
    }

    // Linear interpolation between values
    size_t lower_index = static_cast<size_t>(std::floor(index));
    size_t upper_index = static_cast<size_t>(std::ceil(index));

    if (lower_index == upper_index) {
        return sorted_values[lower_index];
    }

    double lower_value = sorted_values[lower_index];
    double upper_value = sorted_values[upper_index];
    double fraction = index - static_cast<double>(lower_index);

    return lower_value + fraction * (upper_value - lower_value);
}

} // namespace evaluation
} // namespace agenkit
