/**
 * @file test_context_metrics.cpp
 * @brief Tests for context-aware metrics (ContextMetrics, CompressionMetrics, LatencyMetric)
 *
 * Tests context length tracking, compression quality evaluation, and latency measurement
 * for extreme-scale agent evaluation.
 */

#include <gtest/gtest.h>
#include "agenkit/evaluation/context_metrics.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <memory>
#include <vector>
#include <nlohmann/json.hpp>

using namespace agenkit;
using namespace agenkit::evaluation;

/**
 * Test: ContextMetrics basic measurement
 * Tests that context length can be measured from message metadata
 */
TEST(ContextMetricsTest, MeasureFromMessageMetadata) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    ContextMetrics metric;

    EXPECT_EQ(metric.name(), "context_length");

    // Create message with context_length in metadata
    auto input_msg = core::Message::with_text("user", "Test message");
    input_msg.with_metadata("context_length", 1000.0);

    auto output_msg = core::Message::with_text("assistant", "Response");

    auto ctx = nlohmann::json::object();

    double length = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(length, 1000.0);
}

/**
 * Test: ContextMetrics measurement from context dictionary
 * Tests that context length can be measured from context parameter
 */
TEST(ContextMetricsTest, MeasureFromContext) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    ContextMetrics metric;

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");

    auto ctx = nlohmann::json::object();
    ctx["context_length"] = 5000;

    double length = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(length, 5000.0);
}

/**
 * Test: ContextMetrics estimation from conversation history
 * Tests token estimation from conversation messages
 */
TEST(ContextMetricsTest, EstimateFromConversationHistory) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    ContextMetrics metric;

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");

    // Create conversation history
    auto ctx = nlohmann::json::object();
    ctx["conversation_history"] = nlohmann::json::array();

    // Add messages (each ~20 chars = ~5 tokens)
    ctx["conversation_history"].push_back({
        {"role", "user"},
        {"content", "Hello, how are you?"}  // ~20 chars
    });
    ctx["conversation_history"].push_back({
        {"role", "assistant"},
        {"content", "I'm doing well!"}  // ~16 chars
    });
    ctx["conversation_history"].push_back({
        {"role", "user"},
        {"content", "That's great to hear"}  // ~21 chars
    });

    double length = metric.measure(agent, input_msg, output_msg, ctx);
    // Total ~57 chars / 4 = ~14 tokens
    EXPECT_GT(length, 10.0);
    EXPECT_LT(length, 20.0);
}

/**
 * Test: ContextMetrics aggregation with growth rate
 * Tests that aggregate calculates mean, min, max, final, and growth rate
 */
TEST(ContextMetricsTest, AggregateWithGrowthRate) {
    ContextMetrics metric;

    std::vector<double> measurements = {1000.0, 1500.0, 2000.0, 2500.0, 3000.0};
    auto agg = metric.aggregate(measurements);

    EXPECT_TRUE(agg.contains("mean"));
    EXPECT_TRUE(agg.contains("min"));
    EXPECT_TRUE(agg.contains("max"));
    EXPECT_TRUE(agg.contains("final"));
    EXPECT_TRUE(agg.contains("growth_rate"));

    EXPECT_EQ(agg["mean"], 2000.0);  // (1000+1500+2000+2500+3000)/5
    EXPECT_EQ(agg["min"], 1000.0);
    EXPECT_EQ(agg["max"], 3000.0);
    EXPECT_EQ(agg["final"], 3000.0);
    EXPECT_EQ(agg["growth_rate"], 400.0);  // (3000-1000)/5
}

/**
 * Test: ContextMetrics empty measurements
 * Tests that aggregate handles empty input gracefully
 */
TEST(ContextMetricsTest, AggregateEmpty) {
    ContextMetrics metric;

    std::vector<double> measurements;
    auto agg = metric.aggregate(measurements);

    EXPECT_EQ(agg["mean"], 0.0);
    EXPECT_EQ(agg["min"], 0.0);
    EXPECT_EQ(agg["max"], 0.0);
    EXPECT_EQ(agg["final"], 0.0);
    EXPECT_EQ(agg["growth_rate"], 0.0);
}

/**
 * Test: CompressionStats serialization
 * Tests JSON serialization and deserialization
 */
TEST(CompressionStatsTest, JsonSerialization) {
    CompressionStats stats(
        10'000'000,  // raw_tokens
        100'000,     // compressed_tokens
        100.0,       // compression_ratio
        0.95,        // retrieval_accuracy
        10'000'000   // context_length_tested
    );

    // Serialize
    auto json = stats.to_json();

    EXPECT_EQ(json["raw_tokens"], 10'000'000);
    EXPECT_EQ(json["compressed_tokens"], 100'000);
    EXPECT_EQ(json["compression_ratio"], 100.0);
    EXPECT_EQ(json["retrieval_accuracy"], 0.95);
    EXPECT_EQ(json["context_length_tested"], 10'000'000);
    EXPECT_TRUE(json.contains("timestamp"));

    // Deserialize
    auto stats2 = CompressionStats::from_json(json);

    EXPECT_EQ(stats2.raw_tokens, stats.raw_tokens);
    EXPECT_EQ(stats2.compressed_tokens, stats.compressed_tokens);
    EXPECT_DOUBLE_EQ(stats2.compression_ratio, stats.compression_ratio);
    EXPECT_DOUBLE_EQ(stats2.retrieval_accuracy, stats.retrieval_accuracy);
    EXPECT_EQ(stats2.context_length_tested, stats.context_length_tested);
}

/**
 * Test: CompressionMetrics basic measurement
 * Tests measuring compression ratio from metadata
 */
TEST(CompressionMetricsTest, MeasureFromMetadata) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    CompressionMetrics metric;

    EXPECT_EQ(metric.name(), "compression_quality");

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");
    output_msg.with_metadata("compression_ratio", 50.0);

    auto ctx = nlohmann::json::object();

    double ratio = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(ratio, 50.0);
}

/**
 * Test: CompressionMetrics from context stats
 * Tests measuring compression from context dictionary
 */
TEST(CompressionMetricsTest, MeasureFromContextStats) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    CompressionMetrics metric;

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");

    auto ctx = nlohmann::json::object();
    ctx["compression_stats"] = {
        {"raw_tokens", 1'000'000},
        {"compressed_tokens", 10'000}
    };

    double ratio = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(ratio, 100.0);  // 1M / 10K = 100x
}

/**
 * Test: CompressionMetrics no compression
 * Tests default behavior when no compression info available
 */
TEST(CompressionMetricsTest, NoCompression) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    CompressionMetrics metric;

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");
    auto ctx = nlohmann::json::object();

    double ratio = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(ratio, 1.0);  // No compression
}

/**
 * Test: CompressionMetrics aggregation
 * Tests statistical aggregation of compression ratios
 */
TEST(CompressionMetricsTest, AggregateCompressionRatios) {
    CompressionMetrics metric;

    std::vector<double> measurements = {50.0, 75.0, 100.0, 125.0, 150.0};
    auto agg = metric.aggregate(measurements);

    EXPECT_TRUE(agg.contains("mean"));
    EXPECT_TRUE(agg.contains("min"));
    EXPECT_TRUE(agg.contains("max"));
    EXPECT_TRUE(agg.contains("std"));

    EXPECT_EQ(agg["mean"], 100.0);
    EXPECT_EQ(agg["min"], 50.0);
    EXPECT_EQ(agg["max"], 150.0);
    EXPECT_GT(agg["std"], 0.0);  // Should have non-zero variance
}

/**
 * Test: CompressionMetrics default needles generation
 * Tests that default needle facts are generated correctly
 */
TEST(CompressionMetricsTest, DefaultNeedles) {
    CompressionMetrics metric({1'000'000}, 5);  // 5 needles at 1M tokens

    // Access through measure to trigger internal logic
    // The default_needles() method will be called during evaluate_at_lengths
    // For now, just verify construction succeeds
    EXPECT_EQ(metric.name(), "compression_quality");
}

/**
 * Test: LatencyMetric basic measurement
 * Tests measuring latency from context
 */
TEST(LatencyMetricTest, MeasureFromContext) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    LatencyMetric metric;

    EXPECT_EQ(metric.name(), "latency");

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");

    auto ctx = nlohmann::json::object();
    ctx["latency_ms"] = 125.5;

    double latency = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(latency, 125.5);
}

/**
 * Test: LatencyMetric missing data
 * Tests default behavior when no latency data available
 */
TEST(LatencyMetricTest, MissingLatencyData) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    LatencyMetric metric;

    auto input_msg = core::Message::with_text("user", "Test");
    auto output_msg = core::Message::with_text("assistant", "Response");
    auto ctx = nlohmann::json::object();

    double latency = metric.measure(agent, input_msg, output_msg, ctx);
    EXPECT_EQ(latency, 0.0);
}

/**
 * Test: LatencyMetric aggregation with percentiles
 * Tests percentile calculation (p50, p95, p99)
 */
TEST(LatencyMetricTest, AggregateWithPercentiles) {
    LatencyMetric metric;

    std::vector<double> measurements = {
        100.0, 110.0, 120.0, 130.0, 140.0,
        150.0, 160.0, 170.0, 180.0, 190.0,
        200.0, 300.0, 400.0, 500.0, 1000.0  // Including outliers
    };

    auto agg = metric.aggregate(measurements);

    EXPECT_TRUE(agg.contains("mean"));
    EXPECT_TRUE(agg.contains("p50"));
    EXPECT_TRUE(agg.contains("p95"));
    EXPECT_TRUE(agg.contains("p99"));
    EXPECT_TRUE(agg.contains("min"));
    EXPECT_TRUE(agg.contains("max"));

    EXPECT_EQ(agg["min"], 100.0);
    EXPECT_EQ(agg["max"], 1000.0);

    // P50 should be around median (170.0)
    EXPECT_GT(agg["p50"], 150.0);
    EXPECT_LT(agg["p50"], 200.0);

    // P95 should be high (near 500.0)
    EXPECT_GT(agg["p95"], 400.0);

    // P99 should be very high (near 1000.0)
    EXPECT_GT(agg["p99"], 500.0);

    // Mean should be affected by outlier
    EXPECT_GT(agg["mean"], 200.0);
}

/**
 * Test: LatencyMetric empty measurements
 * Tests that aggregate handles empty input gracefully
 */
TEST(LatencyMetricTest, AggregateEmpty) {
    LatencyMetric metric;

    std::vector<double> measurements;
    auto agg = metric.aggregate(measurements);

    EXPECT_EQ(agg["mean"], 0.0);
    EXPECT_EQ(agg["p50"], 0.0);
    EXPECT_EQ(agg["p95"], 0.0);
    EXPECT_EQ(agg["p99"], 0.0);
    EXPECT_EQ(agg["min"], 0.0);
    EXPECT_EQ(agg["max"], 0.0);
}

/**
 * Test: LatencyMetric single measurement
 * Tests percentile calculation with single value
 */
TEST(LatencyMetricTest, AggregateSingleMeasurement) {
    LatencyMetric metric;

    std::vector<double> measurements = {100.0};
    auto agg = metric.aggregate(measurements);

    EXPECT_EQ(agg["mean"], 100.0);
    EXPECT_EQ(agg["p50"], 100.0);
    EXPECT_EQ(agg["p95"], 100.0);
    EXPECT_EQ(agg["p99"], 100.0);
    EXPECT_EQ(agg["min"], 100.0);
    EXPECT_EQ(agg["max"], 100.0);
}

/**
 * Test: LatencyMetric percentile edge cases
 * Tests percentile calculation at boundaries
 */
TEST(LatencyMetricTest, PercentileEdgeCases) {
    LatencyMetric metric;

    // 100 measurements from 1 to 100
    std::vector<double> measurements;
    for (int i = 1; i <= 100; ++i) {
        measurements.push_back(static_cast<double>(i));
    }

    auto agg = metric.aggregate(measurements);

    // P50 should be around 50
    EXPECT_GE(agg["p50"], 49.0);
    EXPECT_LE(agg["p50"], 51.0);

    // P95 should be around 95
    EXPECT_GE(agg["p95"], 94.0);
    EXPECT_LE(agg["p95"], 96.0);

    // P99 should be around 99
    EXPECT_GE(agg["p99"], 98.0);
    EXPECT_LE(agg["p99"], 100.0);
}
