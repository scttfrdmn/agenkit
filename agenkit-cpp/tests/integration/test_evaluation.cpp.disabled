/**
 * @file test_evaluation.cpp
 * @brief Integration tests for evaluation framework
 *
 * Tests metrics collection, session recording, regression detection,
 * quality metrics, A/B testing, and production monitoring.
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/evaluation/metrics.hpp"
#include "agenkit/evaluation/recorder.hpp"
#include "agenkit/evaluation/regression.hpp"
#include "agenkit/evaluation/quality_metrics.hpp"
#include <memory>
#include <filesystem>
#include <fstream>

using namespace agenkit;

/**
 * Test: Metrics collection integration
 * Tests that metrics are properly collected during agent execution
 */
TEST(EvaluationIntegrationTest, MetricsCollection) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto metrics_collector = std::make_shared<evaluation::MetricsCollector>();

    // Wrap agent with metrics collection
    evaluation::MetricsAgent metrics_agent(agent, metrics_collector);

    EXPECT_EQ(metrics_agent.name(), "metrics-echo");

    // Process multiple messages
    for (int i = 0; i < 5; ++i) {
        auto msg = core::Message::with_text("user", "Test " + std::to_string(i));
        msg.with_metadata("request_id", i);

        auto future = metrics_agent.process(std::move(msg));
        auto result = future.get();

        ASSERT_TRUE(result.is_ok());
    }

    // Get metrics
    auto metrics = metrics_collector->get_metrics();

    EXPECT_EQ(metrics["total_requests"], 5);
    EXPECT_EQ(metrics["successful_requests"], 5);
    EXPECT_EQ(metrics["failed_requests"], 0);
    EXPECT_TRUE(metrics.contains("total_duration_ms"));
    EXPECT_TRUE(metrics.contains("average_duration_ms"));
}

/**
 * Test: Session recording integration
 * Tests that sessions are properly recorded
 */
TEST(EvaluationIntegrationTest, SessionRecording) {
    auto agent = std::make_shared<adapters::EchoAgent>();

    std::string session_id = "test-session-001";
    std::filesystem::path record_dir = std::filesystem::temp_directory_path() / "agenkit_test_sessions";
    std::filesystem::create_directories(record_dir);

    auto recorder = std::make_shared<evaluation::SessionRecorder>(record_dir.string());
    evaluation::RecordingAgent recording_agent(agent, recorder, session_id);

    EXPECT_EQ(recording_agent.name(), "recording-echo");

    // Process messages
    auto msg1 = core::Message::with_text("user", "First message");
    msg1.with_metadata("step", 1);
    auto future1 = recording_agent.process(std::move(msg1));
    auto result1 = future1.get();
    ASSERT_TRUE(result1.is_ok());

    auto msg2 = core::Message::with_text("user", "Second message");
    msg2.with_metadata("step", 2);
    auto future2 = recording_agent.process(std::move(msg2));
    auto result2 = future2.get();
    ASSERT_TRUE(result2.is_ok());

    // Finalize recording
    recorder->finalize_session(session_id);

    // Verify session file was created
    auto session_file = record_dir / (session_id + ".jsonl");
    EXPECT_TRUE(std::filesystem::exists(session_file));

    // Read and verify content
    std::ifstream file(session_file);
    EXPECT_TRUE(file.is_open());

    std::string line;
    int line_count = 0;
    while (std::getline(file, line)) {
        if (!line.empty()) {
            auto json = nlohmann::json::parse(line);
            EXPECT_TRUE(json.contains("role"));
            EXPECT_TRUE(json.contains("content"));
            ++line_count;
        }
    }

    // Should have at least request and response records
    EXPECT_GE(line_count, 2);

    // Cleanup
    std::filesystem::remove_all(record_dir);
}

/**
 * Test: Regression detection integration
 * Tests that regressions are detected when quality degrades
 */
TEST(EvaluationIntegrationTest, RegressionDetection) {
    // Create baseline metrics
    nlohmann::json baseline_metrics = {
        {"accuracy", 0.95},
        {"latency_ms", 100.0},
        {"error_rate", 0.01}
    };

    // Create current metrics (with regression)
    nlohmann::json current_metrics = {
        {"accuracy", 0.85},      // 10% drop
        {"latency_ms", 150.0},   // 50% increase
        {"error_rate", 0.05}     // 5x increase
    };

    // Configure thresholds
    evaluation::RegressionConfig config{
        0.05,  // 5% accuracy drop threshold
        0.20,  // 20% latency increase threshold
        2.0    // 2x error rate increase threshold
    };

    evaluation::RegressionDetector detector(config);

    // Check for regressions
    auto regressions = detector.detect(baseline_metrics, current_metrics);

    // Should detect accuracy and error_rate regressions
    EXPECT_FALSE(regressions.empty());

    bool found_accuracy_regression = false;
    bool found_error_rate_regression = false;

    for (const auto& regression : regressions) {
        if (regression.metric_name == "accuracy") {
            found_accuracy_regression = true;
            EXPECT_EQ(regression.baseline_value, 0.95);
            EXPECT_EQ(regression.current_value, 0.85);
        }
        if (regression.metric_name == "error_rate") {
            found_error_rate_regression = true;
            EXPECT_EQ(regression.baseline_value, 0.01);
            EXPECT_EQ(regression.current_value, 0.05);
        }
    }

    EXPECT_TRUE(found_accuracy_regression);
    EXPECT_TRUE(found_error_rate_regression);
}

/**
 * Test: Quality metrics integration
 * Tests quality metrics calculation for agent responses
 */
TEST(EvaluationIntegrationTest, QualityMetrics) {
    evaluation::QualityMetricsCalculator calculator;

    // Create test messages
    auto request = core::Message::with_text("user", "What is 2+2?");
    auto response = core::Message::with_text("assistant", "The answer is 4.");

    // Calculate quality metrics
    auto metrics = calculator.calculate(request, response);

    EXPECT_TRUE(metrics.contains("response_length"));
    EXPECT_GT(metrics["response_length"].get<int>(), 0);

    EXPECT_TRUE(metrics.contains("response_time_ms"));
    EXPECT_GE(metrics["response_time_ms"].get<double>(), 0.0);

    // Test with empty response
    auto empty_response = core::Message::with_text("assistant", "");
    auto empty_metrics = calculator.calculate(request, empty_response);

    EXPECT_EQ(empty_metrics["response_length"].get<int>(), 0);
}

/**
 * Test: A/B testing workflow
 * Tests A/B testing framework for comparing agent variants
 */
TEST(EvaluationIntegrationTest, ABTestingWorkflow) {
    // Create two agent variants
    auto variant_a = std::make_shared<adapters::EchoAgent>();
    auto variant_b = std::make_shared<adapters::EchoAgent>();

    // Create metrics collectors for each variant
    auto metrics_a = std::make_shared<evaluation::MetricsCollector>();
    auto metrics_b = std::make_shared<evaluation::MetricsCollector>();

    evaluation::MetricsAgent agent_a(variant_a, metrics_a);
    evaluation::MetricsAgent agent_b(variant_b, metrics_b);

    // Run test messages through both variants
    constexpr int num_tests = 10;

    for (int i = 0; i < num_tests; ++i) {
        auto msg_a = core::Message::with_text("user", "Test " + std::to_string(i));
        auto msg_b = core::Message::with_text("user", "Test " + std::to_string(i));

        auto future_a = agent_a.process(std::move(msg_a));
        auto future_b = agent_b.process(std::move(msg_b));

        auto result_a = future_a.get();
        auto result_b = future_b.get();

        ASSERT_TRUE(result_a.is_ok());
        ASSERT_TRUE(result_b.is_ok());
    }

    // Compare metrics
    auto metrics_a_data = metrics_a->get_metrics();
    auto metrics_b_data = metrics_b->get_metrics();

    EXPECT_EQ(metrics_a_data["total_requests"], num_tests);
    EXPECT_EQ(metrics_b_data["total_requests"], num_tests);

    EXPECT_EQ(metrics_a_data["successful_requests"], num_tests);
    EXPECT_EQ(metrics_b_data["successful_requests"], num_tests);

    // Both should have timing metrics
    EXPECT_TRUE(metrics_a_data.contains("total_duration_ms"));
    EXPECT_TRUE(metrics_b_data.contains("total_duration_ms"));
}

/**
 * Test: Production monitoring workflow
 * Tests production monitoring with metrics and alerting
 */
TEST(EvaluationIntegrationTest, ProductionMonitoringWorkflow) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto metrics_collector = std::make_shared<evaluation::MetricsCollector>();

    evaluation::MetricsAgent monitored_agent(agent, metrics_collector);

    // Simulate production traffic
    constexpr int num_requests = 20;
    int successful = 0;
    int failed = 0;

    for (int i = 0; i < num_requests; ++i) {
        auto msg = core::Message::with_text("user", "Production request " + std::to_string(i));
        msg.with_metadata("request_id", "prod-" + std::to_string(i))
           .with_metadata("priority", i % 3);  // Vary priority

        auto future = monitored_agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            ++successful;
        } else {
            ++failed;
        }
    }

    // Get production metrics
    auto metrics = metrics_collector->get_metrics();

    EXPECT_EQ(metrics["total_requests"], num_requests);
    EXPECT_EQ(metrics["successful_requests"], successful);
    EXPECT_EQ(metrics["failed_requests"], failed);

    // Calculate success rate
    double success_rate = static_cast<double>(successful) / num_requests;
    EXPECT_GT(success_rate, 0.95);  // Expect >95% success rate

    // Verify latency metrics
    EXPECT_TRUE(metrics.contains("average_duration_ms"));
    EXPECT_TRUE(metrics.contains("total_duration_ms"));

    // Check for performance SLA (e.g., average latency < 1000ms)
    double avg_latency = metrics["average_duration_ms"].get<double>();
    EXPECT_LT(avg_latency, 1000.0);
}

/**
 * Test: Metrics reset and lifecycle
 * Tests that metrics can be properly reset and managed
 */
TEST(EvaluationIntegrationTest, MetricsLifecycle) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto metrics_collector = std::make_shared<evaluation::MetricsCollector>();

    evaluation::MetricsAgent metrics_agent(agent, metrics_collector);

    // Process some messages
    for (int i = 0; i < 3; ++i) {
        auto msg = core::Message::with_text("user", "Test " + std::to_string(i));
        auto future = metrics_agent.process(std::move(msg));
        auto result = future.get();
        ASSERT_TRUE(result.is_ok());
    }

    auto metrics1 = metrics_collector->get_metrics();
    EXPECT_EQ(metrics1["total_requests"], 3);

    // Reset metrics
    metrics_collector->reset();

    auto metrics2 = metrics_collector->get_metrics();
    EXPECT_EQ(metrics2["total_requests"], 0);
    EXPECT_EQ(metrics2["successful_requests"], 0);

    // Process more messages
    for (int i = 0; i < 2; ++i) {
        auto msg = core::Message::with_text("user", "New test " + std::to_string(i));
        auto future = metrics_agent.process(std::move(msg));
        auto result = future.get();
        ASSERT_TRUE(result.is_ok());
    }

    auto metrics3 = metrics_collector->get_metrics();
    EXPECT_EQ(metrics3["total_requests"], 2);
}

/**
 * Test: Quality metrics with edge cases
 * Tests quality metrics calculation with edge cases
 */
TEST(EvaluationIntegrationTest, QualityMetricsEdgeCases) {
    evaluation::QualityMetricsCalculator calculator;

    // Test with very long response
    std::string long_content(10000, 'x');
    auto request1 = core::Message::with_text("user", "Generate text");
    auto response1 = core::Message::with_text("assistant", long_content);
    auto metrics1 = calculator.calculate(request1, response1);

    EXPECT_EQ(metrics1["response_length"].get<int>(), 10000);

    // Test with unicode content
    auto request2 = core::Message::with_text("user", "Hello 世界");
    auto response2 = core::Message::with_text("assistant", "你好 world 🌍");
    auto metrics2 = calculator.calculate(request2, response2);

    EXPECT_GT(metrics2["response_length"].get<int>(), 0);

    // Test with special characters
    auto request3 = core::Message::with_text("user", "Test");
    auto response3 = core::Message::with_text("assistant", "Line1\nLine2\tTab\r\n");
    auto metrics3 = calculator.calculate(request3, response3);

    EXPECT_GT(metrics3["response_length"].get<int>(), 0);
}
