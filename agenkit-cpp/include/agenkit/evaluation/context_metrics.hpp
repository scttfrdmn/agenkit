/**
 * @file context_metrics.hpp
 * @brief Context-aware metrics for extreme-scale evaluation
 *
 * This module provides metrics for evaluating agents operating at extreme scale
 * (1M-25M+ tokens), including:
 * - Context length tracking and growth analysis
 * - Compression quality evaluation (100x-1000x compression)
 * - Latency measurement with percentile aggregation
 * - "Needle in haystack" retrieval testing
 *
 * Key use cases:
 * - Evaluate extreme-scale systems like Endless (25M+ tokens)
 * - Track context growth over agent lifecycle
 * - Measure compression ratio and information retention
 * - Ensure acceptable response times at scale
 *
 * @example
 * @code
 * auto context_metric = ContextMetrics();
 * double length = context_metric.measure(agent, input_msg, output_msg, ctx);
 * std::cout << "Context: " << length << " tokens" << std::endl;
 *
 * auto latency_metric = LatencyMetric();
 * auto agg = latency_metric.aggregate({100.0, 150.0, 200.0, 120.0});
 * std::cout << "P95 latency: " << agg["p95"] << "ms" << std::endl;
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_CONTEXT_METRICS_HPP
#define AGENKIT_EVALUATION_CONTEXT_METRICS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "quality_metrics.hpp"
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <chrono>
#include <future>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Track context length and growth over agent lifecycle
 *
 * Essential for extreme-scale systems (Endless, etc.) that operate at
 * 1M-25M+ token contexts. Measures:
 * - Raw context token count
 * - Compressed context token count (if compression used)
 * - Compression ratio
 * - Context growth rate
 *
 * @details
 * Context length is measured by:
 * 1. Checking agent's get_context_stats() method if available
 * 2. Reading context_length from message metadata
 * 3. Estimating from conversation history (~4 chars = 1 token)
 *
 * @example
 * @code
 * auto metric = ContextMetrics();
 * auto ctx = nlohmann::json::object();
 * ctx["conversation_history"] = history_messages;
 *
 * double tokens = metric.measure(agent, input_msg, output_msg, ctx);
 * std::cout << "Context length: " << tokens << " tokens" << std::endl;
 *
 * auto agg = metric.aggregate({1000.0, 1500.0, 2000.0});
 * std::cout << "Growth rate: " << agg["growth_rate"] << " tokens/turn" << std::endl;
 * @endcode
 */
class ContextMetrics : public Metric {
public:
    /**
     * @brief Create a context metrics instance
     */
    ContextMetrics() = default;

    std::string name() const override { return "context_length"; }

    /**
     * @brief Measure context length for single interaction
     *
     * @param agent Agent being evaluated
     * @param input_message Input to agent
     * @param output_message Agent's response
     * @param ctx Context with session history or metadata
     * @return Current context length in tokens (or compressed tokens if available)
     */
    double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) override;

    /**
     * @brief Aggregate context length measurements
     *
     * @param measurements List of context lengths over time
     * @return Statistics: mean, min, max, final, growth_rate
     *
     * growth_rate = (final - initial) / num_measurements
     */
    nlohmann::json aggregate(const std::vector<double>& measurements) override;

private:
    /**
     * @brief Estimate token count from text
     * @param text Text to estimate
     * @return Estimated token count (~4 chars = 1 token)
     */
    size_t estimate_tokens(const std::string& text) const;
};

/**
 * @brief Statistics from compression evaluation
 *
 * Contains results from testing compression at a specific context length.
 */
struct CompressionStats {
    size_t raw_tokens;              ///< Raw uncompressed token count
    size_t compressed_tokens;       ///< Compressed token count
    double compression_ratio;       ///< Raw / compressed
    double retrieval_accuracy;      ///< Fraction of needles retrieved (0.0-1.0)
    size_t context_length_tested;   ///< Context length at which this was tested
    std::chrono::system_clock::time_point timestamp;  ///< When measurement was taken

    /**
     * @brief Default constructor
     */
    CompressionStats();

    /**
     * @brief Create compression stats
     * @param raw Raw token count
     * @param compressed Compressed token count
     * @param ratio Compression ratio
     * @param accuracy Retrieval accuracy
     * @param length Context length tested
     */
    CompressionStats(
        size_t raw,
        size_t compressed,
        double ratio,
        double accuracy,
        size_t length
    );

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return CompressionStats instance
     */
    static CompressionStats from_json(const nlohmann::json& j);
};

/**
 * @brief Measure compression quality at extreme scale
 *
 * Critical for Endless and similar systems that use 100x-1000x compression
 * at 25M+ tokens. Measures:
 * - Compression ratio achieved
 * - Information retention after compression
 * - Retrieval accuracy from compressed context
 * - Quality degradation as context grows
 *
 * Uses "needle in haystack" testing: embeds specific facts throughout a large
 * context, then tests if the agent can retrieve them after compression.
 *
 * @example
 * @code
 * std::vector<size_t> test_lengths = {1'000'000, 10'000'000, 25'000'000};
 * auto metric = CompressionMetrics(test_lengths, 10);
 *
 * std::string session_id = "test-session";
 * std::vector<std::string> needles = {"fact1", "fact2", "fact3"};
 *
 * auto stats_map = metric.evaluate_at_lengths(agent, session_id, needles).get();
 * for (const auto& [length, stats] : stats_map) {
 *     std::cout << length/1e6 << "M tokens: "
 *               << stats.compression_ratio << "x compression, "
 *               << stats.retrieval_accuracy * 100 << "% accuracy" << std::endl;
 * }
 * @endcode
 */
class CompressionMetrics : public Metric {
public:
    /**
     * @brief Create a compression metrics instance
     * @param test_lengths Context lengths to test (defaults to 1M, 10M, 25M)
     * @param needle_count Number of "needle" facts to test retrieval
     */
    explicit CompressionMetrics(
        std::vector<size_t> test_lengths = {1'000'000, 10'000'000, 25'000'000},
        size_t needle_count = 10
    );

    std::string name() const override { return "compression_quality"; }

    /**
     * @brief Measure compression quality for single interaction
     *
     * @param agent Agent being evaluated
     * @param input_message Input to agent
     * @param output_message Agent's response
     * @param ctx Context with session_id and compression stats
     * @return Compression ratio (raw_tokens / compressed_tokens)
     */
    double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) override;

    /**
     * @brief Aggregate compression ratios
     *
     * @param measurements List of compression ratios
     * @return Statistics: mean, min, max, std
     */
    nlohmann::json aggregate(const std::vector<double>& measurements) override;

    /**
     * @brief Evaluate compression quality at multiple context lengths
     *
     * Tests compression and retrieval at 1M, 10M, 25M tokens to detect
     * quality degradation as context grows.
     *
     * @param agent Agent with compression capability
     * @param session_id Session to evaluate
     * @param needle_content Specific facts to test retrieval (optional)
     * @return Future with map: context_length -> CompressionStats
     */
    std::future<std::map<size_t, CompressionStats>> evaluate_at_lengths(
        std::shared_ptr<core::Agent> agent,
        const std::string& session_id,
        const std::vector<std::string>& needle_content = {}
    );

private:
    /**
     * @brief Generate test context with embedded needles
     * @param target_tokens Target context length
     * @param needles Facts to embed for retrieval testing
     * @return List of messages totaling ~target_tokens
     */
    std::vector<std::string> generate_test_context(
        size_t target_tokens,
        const std::vector<std::string>& needles
    );

    /**
     * @brief Test retrieval accuracy of needles from context
     * @param agent Agent to test
     * @param session_id Session with context
     * @param needles Facts that should be retrievable
     * @return Future with accuracy (0.0 to 1.0)
     */
    std::future<double> test_retrieval(
        std::shared_ptr<core::Agent> agent,
        const std::string& session_id,
        const std::vector<std::string>& needles
    );

    /**
     * @brief Generate default needle facts for testing
     * @return Vector of needle strings
     */
    std::vector<std::string> default_needles() const;

    std::vector<size_t> test_lengths_;
    size_t needle_count_;
};

/**
 * @brief Measure agent response latency
 *
 * Tracks processing time per interaction. Critical for production systems
 * where response time matters. Aggregates with percentile statistics
 * (p50, p95, p99) for understanding tail latencies.
 *
 * @details
 * Latency is measured in milliseconds and should be provided in the context
 * dictionary under the key "latency_ms". The metric aggregates measurements
 * using percentile statistics to understand both typical and worst-case
 * performance.
 *
 * @example
 * @code
 * auto metric = LatencyMetric();
 *
 * // During evaluation
 * auto ctx = nlohmann::json::object();
 * ctx["latency_ms"] = 125.5;
 * double latency = metric.measure(agent, input_msg, output_msg, ctx);
 *
 * // After collecting measurements
 * std::vector<double> measurements = {100.0, 150.0, 200.0, 120.0, 500.0};
 * auto stats = metric.aggregate(measurements);
 * std::cout << "Mean: " << stats["mean"] << "ms" << std::endl;
 * std::cout << "P95: " << stats["p95"] << "ms" << std::endl;
 * std::cout << "P99: " << stats["p99"] << "ms" << std::endl;
 * @endcode
 */
class LatencyMetric : public Metric {
public:
    /**
     * @brief Create a latency metric instance
     */
    LatencyMetric() = default;

    std::string name() const override { return "latency"; }

    /**
     * @brief Get latency for this interaction
     *
     * @param agent Agent being evaluated
     * @param input_message Input to agent
     * @param output_message Agent's response
     * @param ctx Context with latency_ms measurement
     * @return Latency in milliseconds
     */
    double measure(
        std::shared_ptr<core::Agent> agent,
        const core::Message& input_message,
        const core::Message& output_message,
        const nlohmann::json& ctx
    ) override;

    /**
     * @brief Aggregate latency measurements with percentiles
     *
     * @param measurements List of latency measurements in milliseconds
     * @return Statistics: mean, p50, p95, p99, min, max
     *
     * Returns empty statistics if measurements is empty.
     */
    nlohmann::json aggregate(const std::vector<double>& measurements) override;

private:
    /**
     * @brief Calculate percentile from sorted values
     * @param sorted_values Sorted measurements
     * @param percentile Percentile to calculate (0.0 to 1.0)
     * @return Value at percentile
     */
    double calculate_percentile(
        const std::vector<double>& sorted_values,
        double percentile
    ) const;
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_CONTEXT_METRICS_HPP
