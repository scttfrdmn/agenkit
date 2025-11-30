/**
 * @file basic_metrics.cpp
 * @brief Basic metrics collection and aggregation example
 *
 * This example demonstrates how to use the evaluation framework to:
 * - Create SessionResult instances to track agent sessions
 * - Add metric measurements (quality, cost, duration)
 * - Collect multiple session results
 * - Compute aggregate statistics across sessions
 *
 * This is the foundation for monitoring agent performance over time,
 * tracking success rates, detecting issues, and measuring improvements.
 *
 * Compile: See examples/CMakeLists.txt
 * Run: ./basic_metrics
 */

#include "agenkit/evaluation/metrics.hpp"
#include <iostream>
#include <iomanip>
#include <random>
#include <string>
#include <thread>
#include <chrono>

using namespace agenkit::evaluation;

// Simulate running an agent session and collecting metrics
SessionResult simulate_agent_session(const std::string& session_id, const std::string& agent_name) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<> quality_dist(0.7, 1.0);
    static std::uniform_int_distribution<> token_dist(100, 500);
    static std::uniform_real_distribution<> duration_dist(0.5, 2.5);
    static std::uniform_real_distribution<> success_dist(0.0, 1.0);

    SessionResult result(session_id, agent_name);

    // Simulate some processing time
    std::this_thread::sleep_for(std::chrono::milliseconds(10 + (rand() % 50)));

    // Add quality metrics
    double quality_score = quality_dist(gen);
    result.add_metric_measurement(create_quality_metric(
        "response_quality",
        quality_score * 10,
        10.0,
        {{"evaluator", "rule_based"}}
    ));

    // Add cost metrics
    int tokens_used = token_dist(gen);
    double cost_per_token = 0.00001;
    double total_cost = tokens_used * cost_per_token;
    result.add_metric_measurement(create_cost_metric(
        total_cost,
        "USD",
        {{"tokens", tokens_used}}
    ));

    // Add duration metrics
    double duration_seconds = duration_dist(gen);
    result.add_metric_measurement(create_duration_metric(duration_seconds));

    // Add custom success rate metric
    bool success = success_dist(gen) > 0.2; // 80% success rate
    double success_value = success ? 1.0 : 0.0;

    if (success) {
        result.set_status(SessionStatus::Completed);
    } else {
        result.set_status(SessionStatus::Failed);
        result.add_error("processing_error", "Failed to complete task", {{"reason", "timeout"}});
    }

    result.add_metric_measurement(MetricMeasurement(
        "success",
        success_value,
        MetricType::SuccessRate
    ));

    return result;
}

int main() {
    std::cout << "Basic Metrics Collection Example" << std::endl;
    std::cout << "=================================" << std::endl << std::endl;

    // Step 1: Create metrics collector
    std::cout << "Step 1: Creating Metrics Collector" << std::endl;
    std::cout << "-----------------------------------" << std::endl;
    MetricsCollector collector;
    std::cout << "✓ Metrics collector created" << std::endl << std::endl;

    // Step 2: Simulate multiple agent sessions
    std::cout << "Step 2: Simulating Agent Sessions" << std::endl;
    std::cout << "----------------------------------" << std::endl;
    int num_sessions = 20;
    std::cout << "Running " << num_sessions << " simulated agent sessions..." << std::endl << std::endl;

    for (int i = 0; i < num_sessions; ++i) {
        std::string session_id = "session-" + std::string(3 - std::to_string(i+1).length(), '0') + std::to_string(i+1);
        std::string agent_name = "example-agent";

        SessionResult result = simulate_agent_session(session_id, agent_name);
        collector.add_result(result);

        // Print progress
        std::string status = result.status() == SessionStatus::Completed ? "✓" : "✗";
        std::cout << "  " << status << " Session " << (i+1) << ": "
                  << session_status_to_string(result.status()) << std::endl;
    }
    std::cout << std::endl;

    // Step 3: Compute aggregate statistics
    std::cout << "Step 3: Computing Aggregate Statistics" << std::endl;
    std::cout << "---------------------------------------" << std::endl;
    auto stats = collector.get_statistics();

    std::cout << "Total Sessions: " << stats["session_count"] << std::endl;
    std::cout << "Completed: " << stats["completed_count"] << std::endl;
    std::cout << "Failed: " << stats["failed_count"] << std::endl;
    std::cout << std::fixed << std::setprecision(1);
    std::cout << "Success Rate: " << stats["success_rate"].get<double>() * 100 << "%" << std::endl;
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Average Duration: " << stats["avg_duration"] << "s" << std::endl;
    std::cout << "Total Errors: " << stats["total_errors"] << std::endl;
    std::cout << "Avg Errors/Session: " << stats["avg_errors_per_session"] << std::endl << std::endl;

    // Step 4: Analyze specific metrics
    std::cout << "Step 4: Analyzing Specific Metrics" << std::endl;
    std::cout << "-----------------------------------" << std::endl;

    // Quality metrics
    auto quality_stats = collector.get_metric_aggregates("response_quality");
    if (quality_stats["count"].get<int>() > 0) {
        std::cout << "\nQuality Metrics:" << std::endl;
        std::cout << "  Count: " << quality_stats["count"] << std::endl;
        std::cout << std::fixed << std::setprecision(3);
        std::cout << "  Mean: " << quality_stats["mean"] << std::endl;
        std::cout << "  Min: " << quality_stats["min"] << std::endl;
        std::cout << "  Max: " << quality_stats["max"] << std::endl;
    }

    // Cost metrics
    auto cost_stats = collector.get_metric_aggregates("total_cost");
    if (cost_stats["count"].get<int>() > 0) {
        std::cout << "\nCost Metrics:" << std::endl;
        std::cout << "  Count: " << cost_stats["count"] << std::endl;
        std::cout << std::fixed << std::setprecision(4);
        std::cout << "  Total Cost: $" << cost_stats["sum"] << std::endl;
        std::cout << "  Average Cost/Session: $" << cost_stats["mean"] << std::endl;
        std::cout << "  Min Cost: $" << cost_stats["min"] << std::endl;
        std::cout << "  Max Cost: $" << cost_stats["max"] << std::endl;
    }

    // Duration metrics
    auto duration_stats = collector.get_metric_aggregates("duration");
    if (duration_stats["count"].get<int>() > 0) {
        std::cout << "\nDuration Metrics:" << std::endl;
        std::cout << "  Count: " << duration_stats["count"] << std::endl;
        std::cout << std::fixed << std::setprecision(2);
        std::cout << "  Total Duration: " << duration_stats["sum"] << "s" << std::endl;
        std::cout << "  Average Duration: " << duration_stats["mean"] << "s" << std::endl;
        std::cout << "  Min Duration: " << duration_stats["min"] << "s" << std::endl;
        std::cout << "  Max Duration: " << duration_stats["max"] << "s" << std::endl;
    }

    // Success rate metrics
    auto success_stats = collector.get_metric_aggregates("success");
    if (success_stats["count"].get<int>() > 0) {
        std::cout << "\nSuccess Rate Metrics:" << std::endl;
        std::cout << "  Count: " << success_stats["count"] << std::endl;
        std::cout << std::fixed << std::setprecision(1);
        std::cout << "  Success Rate: " << success_stats["mean"].get<double>() * 100 << "%" << std::endl;
    }

    // Step 5: Summary and best practices
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "Summary: Basic Metrics Collection" << std::endl;
    std::cout << std::string(70, '=') << std::endl;

    std::cout << "\nKey Capabilities:" << std::endl;
    std::cout << "1. SessionResult: Track individual agent session metrics" << std::endl;
    std::cout << "2. MetricsCollector: Aggregate metrics across multiple sessions" << std::endl;
    std::cout << "3. Metric Types: Quality, cost, duration, success rate, custom" << std::endl;
    std::cout << "4. Statistics: Success rate, averages, min/max, error rates" << std::endl;

    std::cout << "\nMetric Types Available:" << std::endl;
    std::cout << "- SuccessRate: Binary success/failure tracking" << std::endl;
    std::cout << "- QualityScore: Normalized quality scores (0.0-1.0)" << std::endl;
    std::cout << "- Cost: Token costs and API expenses" << std::endl;
    std::cout << "- Duration: Execution time tracking" << std::endl;
    std::cout << "- ErrorRate: Error frequency analysis" << std::endl;
    std::cout << "- TaskCompletion: Task completion tracking" << std::endl;
    std::cout << "- Custom: Domain-specific metrics" << std::endl;

    std::cout << "\nThread Safety:" << std::endl;
    std::cout << "MetricsCollector is thread-safe and can be used concurrently" << std::endl;
    std::cout << "from multiple threads without additional synchronization." << std::endl;

    std::cout << "\nBest Practices:" << std::endl;
    std::cout << "1. Create one SessionResult per agent invocation" << std::endl;
    std::cout << "2. Add measurements as they occur (streaming metrics)" << std::endl;
    std::cout << "3. Set final status (completed/failed) when session ends" << std::endl;
    std::cout << "4. Use helper functions (create_quality_metric, create_cost_metric)" << std::endl;
    std::cout << "5. Collect across many sessions for statistical significance" << std::endl;
    std::cout << "6. Export to JSON for long-term storage and analysis" << std::endl;

    return 0;
}
