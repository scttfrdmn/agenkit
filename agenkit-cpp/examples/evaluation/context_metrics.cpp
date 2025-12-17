/**
 * @file context_metrics.cpp
 * @brief Context-aware metrics for extreme-scale evaluation
 *
 * This example demonstrates how to use context metrics for evaluating agents
 * operating at extreme scale (1M-25M+ tokens):
 * - ContextMetrics: Track context length and growth over agent lifecycle
 * - CompressionMetrics: Measure compression quality and retrieval accuracy
 * - LatencyMetric: Track response times with percentile aggregation
 *
 * These metrics are essential for systems like Endless that operate at
 * massive context lengths where traditional evaluation approaches break down.
 *
 * Compile: See examples/CMakeLists.txt
 * Run: ./context_metrics
 */

#include "agenkit/evaluation/context_metrics.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <iomanip>
#include <vector>
#include <random>
#include <chrono>
#include <thread>

using namespace agenkit;
using namespace agenkit::evaluation;

// Simulate context growth over agent lifecycle
std::vector<double> simulate_context_growth() {
    std::vector<double> context_lengths;
    double current_length = 1000.0;  // Start with 1K tokens

    for (int i = 0; i < 10; ++i) {
        context_lengths.push_back(current_length);
        // Simulate growth: +500-1500 tokens per turn
        current_length += 500.0 + (rand() % 1000);
    }

    return context_lengths;
}

// Simulate compression ratios at different scales
std::vector<double> simulate_compression_ratios() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> ratio_dist(50.0, 150.0);

    std::vector<double> ratios;
    for (int i = 0; i < 10; ++i) {
        ratios.push_back(ratio_dist(gen));
    }

    return ratios;
}

// Simulate latency measurements with some outliers
std::vector<double> simulate_latencies() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> latency_dist(80.0, 150.0);

    std::vector<double> latencies;
    for (int i = 0; i < 100; ++i) {
        double latency = latency_dist(gen);

        // Add occasional outliers (5% of the time)
        if (i % 20 == 0) {
            latency *= 3.0;  // Spike
        }

        latencies.push_back(latency);
    }

    return latencies;
}

void print_separator() {
    std::cout << std::string(70, '-') << std::endl;
}

int main() {
    std::cout << "Context Metrics for Extreme-Scale Evaluation" << std::endl;
    std::cout << "=============================================" << std::endl << std::endl;

    // Part 1: ContextMetrics
    // ======================
    std::cout << "Part 1: Context Length Tracking" << std::endl;
    print_separator();
    std::cout << "Track context growth over agent lifecycle (1K -> 10K+ tokens)"
              << std::endl << std::endl;

    ContextMetrics context_metric;
    auto agent = std::make_shared<adapters::EchoAgent>();

    // Simulate 10 turns of conversation
    std::cout << "Simulating conversation with growing context:" << std::endl;
    std::vector<double> context_measurements;

    for (int turn = 0; turn < 10; ++turn) {
        // Create message with context_length in metadata
        auto input_msg = core::Message::with_text("user", "Query " + std::to_string(turn));
        double context_length = 1000.0 + (turn * 1000.0);  // Growth: 1K, 2K, 3K...
        input_msg.with_metadata("context_length", context_length);

        auto output_msg = core::Message::with_text("assistant", "Response");

        auto ctx = nlohmann::json::object();

        // Measure context length
        double measured_length = context_metric.measure(agent, input_msg, output_msg, ctx);
        context_measurements.push_back(measured_length);

        std::cout << "  Turn " << std::setw(2) << turn + 1 << ": "
                  << std::setw(6) << std::fixed << std::setprecision(0)
                  << measured_length << " tokens" << std::endl;
    }

    // Aggregate statistics
    auto context_agg = context_metric.aggregate(context_measurements);

    std::cout << std::endl << "Context Statistics:" << std::endl;
    std::cout << "  Mean:        " << std::fixed << std::setprecision(0)
              << context_agg["mean"].get<double>() << " tokens" << std::endl;
    std::cout << "  Min:         " << context_agg["min"].get<double>() << " tokens" << std::endl;
    std::cout << "  Max:         " << context_agg["max"].get<double>() << " tokens" << std::endl;
    std::cout << "  Final:       " << context_agg["final"].get<double>() << " tokens" << std::endl;
    std::cout << "  Growth Rate: " << std::setprecision(1)
              << context_agg["growth_rate"].get<double>() << " tokens/turn" << std::endl;

    std::cout << std::endl;

    // Part 2: CompressionMetrics
    // ==========================
    std::cout << "Part 2: Compression Quality Evaluation" << std::endl;
    print_separator();
    std::cout << "Evaluate compression at extreme scale (1M, 10M, 25M tokens)"
              << std::endl << std::endl;

    CompressionMetrics compression_metric;

    std::cout << "Testing compression at different scales:" << std::endl;

    // Simulate compression at three scale levels
    struct ScaleTest {
        size_t context_length;
        double compression_ratio;
        double retrieval_accuracy;
    };

    std::vector<ScaleTest> scale_tests = {
        {1'000'000,   100.0, 0.98},   // 1M tokens: 100x compression, 98% accuracy
        {10'000'000,  150.0, 0.95},   // 10M tokens: 150x compression, 95% accuracy
        {25'000'000,  200.0, 0.90}    // 25M tokens: 200x compression, 90% accuracy
    };

    std::vector<double> compression_measurements;

    for (const auto& test : scale_tests) {
        compression_measurements.push_back(test.compression_ratio);

        std::cout << "  " << std::setw(2) << test.context_length / 1'000'000 << "M tokens: "
                  << std::setw(5) << std::fixed << std::setprecision(1)
                  << test.compression_ratio << "x compression, "
                  << std::setw(5) << std::setprecision(1)
                  << test.retrieval_accuracy * 100 << "% retrieval accuracy" << std::endl;
    }

    // Aggregate compression statistics
    auto compression_agg = compression_metric.aggregate(compression_measurements);

    std::cout << std::endl << "Compression Statistics:" << std::endl;
    std::cout << "  Mean Ratio: " << std::fixed << std::setprecision(1)
              << compression_agg["mean"].get<double>() << "x" << std::endl;
    std::cout << "  Min Ratio:  " << compression_agg["min"].get<double>() << "x" << std::endl;
    std::cout << "  Max Ratio:  " << compression_agg["max"].get<double>() << "x" << std::endl;
    std::cout << "  Std Dev:    " << compression_agg["std"].get<double>() << "x" << std::endl;

    std::cout << std::endl;

    // Part 3: LatencyMetric
    // =====================
    std::cout << "Part 3: Latency Measurement with Percentiles" << std::endl;
    print_separator();
    std::cout << "Track response times with p50, p95, p99 percentiles"
              << std::endl << std::endl;

    LatencyMetric latency_metric;

    std::cout << "Collecting 100 latency measurements..." << std::endl;

    // Simulate latencies
    auto latencies = simulate_latencies();

    // Show a few samples
    std::cout << "Sample measurements (ms): ";
    for (size_t i = 0; i < 10 && i < latencies.size(); ++i) {
        std::cout << std::fixed << std::setprecision(1) << latencies[i];
        if (i < 9 && i < latencies.size() - 1) std::cout << ", ";
    }
    std::cout << "..." << std::endl << std::endl;

    // Aggregate with percentiles
    auto latency_agg = latency_metric.aggregate(latencies);

    std::cout << "Latency Statistics:" << std::endl;
    std::cout << "  Mean:  " << std::setw(6) << std::fixed << std::setprecision(1)
              << latency_agg["mean"].get<double>() << " ms" << std::endl;
    std::cout << "  P50:   " << std::setw(6) << latency_agg["p50"].get<double>() << " ms" << std::endl;
    std::cout << "  P95:   " << std::setw(6) << latency_agg["p95"].get<double>() << " ms" << std::endl;
    std::cout << "  P99:   " << std::setw(6) << latency_agg["p99"].get<double>() << " ms" << std::endl;
    std::cout << "  Min:   " << std::setw(6) << latency_agg["min"].get<double>() << " ms" << std::endl;
    std::cout << "  Max:   " << std::setw(6) << latency_agg["max"].get<double>() << " ms" << std::endl;

    std::cout << std::endl;
    std::cout << "Note: P95 and P99 show tail latencies (outliers)" << std::endl;
    std::cout << "      Critical for understanding worst-case performance" << std::endl;

    std::cout << std::endl;

    // Summary
    // =======
    std::cout << std::endl;
    std::cout << "Summary: Context Metrics for Extreme-Scale Agents" << std::endl;
    print_separator();
    std::cout << std::endl;

    std::cout << "✓ ContextMetrics: Track context growth from 1K to 10K+ tokens" << std::endl;
    std::cout << "  - Measured growth rate: "
              << std::fixed << std::setprecision(0)
              << context_agg["growth_rate"].get<double>() << " tokens/turn" << std::endl;
    std::cout << std::endl;

    std::cout << "✓ CompressionMetrics: Evaluate 100x-200x compression" << std::endl;
    std::cout << "  - Mean compression: "
              << std::fixed << std::setprecision(1)
              << compression_agg["mean"].get<double>() << "x at extreme scale" << std::endl;
    std::cout << std::endl;

    std::cout << "✓ LatencyMetric: Track response times with percentiles" << std::endl;
    std::cout << "  - P95 latency: "
              << std::fixed << std::setprecision(1)
              << latency_agg["p95"].get<double>() << " ms (95% under this)" << std::endl;
    std::cout << std::endl;

    std::cout << "These metrics are essential for evaluating systems operating at" << std::endl;
    std::cout << "1M-25M+ token contexts where traditional metrics break down." << std::endl;
    std::cout << std::endl;

    std::cout << "Use Cases:" << std::endl;
    std::cout << "  • Monitor context growth in long-running conversations" << std::endl;
    std::cout << "  • Verify compression doesn't degrade retrieval accuracy" << std::endl;
    std::cout << "  • Ensure acceptable latencies at extreme scale" << std::endl;
    std::cout << "  • Detect performance regressions in production" << std::endl;

    return 0;
}
