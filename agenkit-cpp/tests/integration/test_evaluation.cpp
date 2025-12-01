/**
 * @file test_evaluation.cpp
 * @brief Integration tests for evaluation framework
 *
 * Tests session recording, regression detection, quality metrics,
 * and metrics collection with the current API.
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
 * Test: Session recording with new API
 * Tests SessionRecorder with wrap() method and storage backends
 */
TEST(EvaluationIntegrationTest, SessionRecordingWithWrap) {
    auto agent = std::make_shared<adapters::EchoAgent>();

    // Create in-memory storage for testing
    auto storage = std::make_shared<evaluation::InMemoryRecordingStorage>();
    evaluation::SessionRecorder recorder(storage);

    std::string session_id = "test-session-001";

    // Start session
    recorder.start_session(session_id, agent->name());

    // Wrap agent
    auto wrapped_agent = recorder.wrap(agent);
    EXPECT_NE(wrapped_agent, nullptr);

    // Process messages (with session_id in metadata for recording)
    auto msg1 = core::Message::with_text("user", "First message");
    msg1.with_metadata("session_id", session_id);
    auto future1 = wrapped_agent->process(std::move(msg1));
    auto result1 = future1.get();
    ASSERT_TRUE(result1.is_ok());

    auto msg2 = core::Message::with_text("user", "Second message");
    msg2.with_metadata("session_id", session_id);
    auto future2 = wrapped_agent->process(std::move(msg2));
    auto result2 = future2.get();
    ASSERT_TRUE(result2.is_ok());

    // Finalize session
    auto recording = recorder.finalize_session(session_id);

    EXPECT_EQ(recording.session_id(), session_id);
    EXPECT_EQ(recording.agent_name(), agent->name());
    EXPECT_GE(recording.interaction_count(), 2);

    // Verify recording was saved to storage
    auto loaded = storage->load_recording(session_id);
    ASSERT_TRUE(loaded.has_value());
    EXPECT_EQ(loaded->session_id(), session_id);
    EXPECT_GE(loaded->interaction_count(), 2);
}

/**
 * Test: File-based recording storage
 * Tests FileRecordingStorage saves and loads recordings
 */
TEST(EvaluationIntegrationTest, FileRecordingStorage) {
    auto agent = std::make_shared<adapters::EchoAgent>();

    std::filesystem::path record_dir = std::filesystem::temp_directory_path() / "agenkit_test_recordings";
    std::filesystem::create_directories(record_dir);

    auto storage = std::make_shared<evaluation::FileRecordingStorage>(record_dir.string());
    evaluation::SessionRecorder recorder(storage);

    std::string session_id = "file-test-001";

    // Start and record session
    recorder.start_session(session_id, agent->name());
    auto wrapped = recorder.wrap(agent);

    auto msg = core::Message::with_text("user", "Test message");
    msg.with_metadata("session_id", session_id);
    auto future = wrapped->process(std::move(msg));
    auto result = future.get();
    ASSERT_TRUE(result.is_ok());

    // Finalize
    recorder.finalize_session(session_id);

    // Verify file exists
    auto session_file = record_dir / (session_id + ".json");
    EXPECT_TRUE(std::filesystem::exists(session_file));

    // Load recording
    auto loaded = storage->load_recording(session_id);
    ASSERT_TRUE(loaded.has_value());
    EXPECT_EQ(loaded->session_id(), session_id);
    EXPECT_GE(loaded->interaction_count(), 1);

    // Cleanup
    std::filesystem::remove_all(record_dir);
}

/**
 * Test: Session replay
 * Tests replaying recorded sessions through agents
 */
TEST(EvaluationIntegrationTest, SessionReplay) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto storage = std::make_shared<evaluation::InMemoryRecordingStorage>();
    evaluation::SessionRecorder recorder(storage);

    std::string session_id = "replay-test-001";

    // Record a session
    recorder.start_session(session_id, agent->name());
    auto wrapped = recorder.wrap(agent);

    auto msg1 = core::Message::with_text("user", "Hello");
    msg1.with_metadata("session_id", session_id);
    auto msg2 = core::Message::with_text("user", "World");
    msg2.with_metadata("session_id", session_id);

    auto r1 = wrapped->process(std::move(msg1)).get();
    auto r2 = wrapped->process(std::move(msg2)).get();

    ASSERT_TRUE(r1.is_ok());
    ASSERT_TRUE(r2.is_ok());

    auto recording = recorder.finalize_session(session_id);

    // Replay through same agent
    evaluation::SessionReplay replay;
    auto replay_results = replay.replay(recording, agent);

    EXPECT_TRUE(replay_results.contains("session_id"));
    EXPECT_TRUE(replay_results.contains("interactions"));
    EXPECT_GE(replay_results["interactions"].size(), 2);
}

/**
 * Test: Regression detection
 * Tests that regressions are detected when metrics degrade
 */
TEST(EvaluationIntegrationTest, RegressionDetection) {
    evaluation::RegressionDetector detector;

    // Create baseline evaluation result
    evaluation::EvaluationResult baseline;
    baseline.evaluation_id = "baseline";
    baseline.agent_name = "test-agent";
    baseline.timestamp = std::chrono::system_clock::now();
    baseline.accuracy = 0.95;
    baseline.avg_latency_ms = 100.0;

    detector.set_baseline(baseline);

    // Create current evaluation result (with regression)
    evaluation::EvaluationResult current;
    current.evaluation_id = "current";
    current.agent_name = "test-agent";
    current.timestamp = std::chrono::system_clock::now();
    current.accuracy = 0.85;  // 10% drop
    current.avg_latency_ms = 150.0;  // 50% increase

    // Check for regressions
    auto regressions = detector.detect(current);

    // Should detect accuracy regression (10% drop exceeds default 5% threshold)
    EXPECT_FALSE(regressions.empty());

    bool found_accuracy_regression = false;
    for (const auto& regression : regressions) {
        if (regression.metric_name == "accuracy") {
            found_accuracy_regression = true;
            EXPECT_EQ(regression.baseline_value, 0.95);
            EXPECT_EQ(regression.current_value, 0.85);
        }
    }

    EXPECT_TRUE(found_accuracy_regression);
}

/**
 * Test: Quality metrics with AccuracyMetric
 * Tests accuracy metric for agent responses
 */
TEST(EvaluationIntegrationTest, AccuracyMetric) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    evaluation::AccuracyMetric metric(false);  // Case-insensitive

    EXPECT_EQ(metric.name(), "accuracy");

    // Test exact match
    auto input = core::Message::with_text("user", "What is the capital of France?");
    auto output = core::Message::with_text("assistant", "Paris");

    nlohmann::json ctx;
    ctx["expected"] = "Paris";

    double score = metric.measure(agent, input, output, ctx);
    EXPECT_EQ(score, 1.0);  // Exact match

    // Test mismatch
    auto wrong_output = core::Message::with_text("assistant", "London");
    double wrong_score = metric.measure(agent, input, wrong_output, ctx);
    EXPECT_EQ(wrong_score, 0.0);  // No match
}

/**
 * Test: MetricsCollector basic functionality
 * Tests SessionResult and MetricsCollector
 */
TEST(EvaluationIntegrationTest, MetricsCollectorBasic) {
    // Create session results
    evaluation::SessionResult result1("session-1", "test-agent");
    result1.add_metric_measurement(evaluation::MetricMeasurement(
        "accuracy", 0.95, evaluation::MetricType::SuccessRate
    ));
    result1.add_metric_measurement(evaluation::MetricMeasurement(
        "latency", 150.0, evaluation::MetricType::Duration
    ));
    result1.set_status(evaluation::SessionStatus::Completed);

    // Verify measurements
    EXPECT_EQ(result1.session_id(), "session-1");
    EXPECT_EQ(result1.agent_name(), "test-agent");
    EXPECT_EQ(result1.status(), evaluation::SessionStatus::Completed);
    EXPECT_EQ(result1.measurements().size(), 2);

    // Test metrics collector
    evaluation::MetricsCollector collector;
    collector.add_result(result1);

    auto stats = collector.get_statistics();
    EXPECT_EQ(stats["session_count"], 1);
    EXPECT_EQ(stats["completed_count"], 1);
    EXPECT_EQ(stats["failed_count"], 0);
}

/**
 * Test: MetricsCollector aggregation
 * Tests cross-session metric aggregation
 */
TEST(EvaluationIntegrationTest, MetricsCollectorAggregation) {
    evaluation::MetricsCollector collector;

    // Add multiple session results
    for (int i = 0; i < 5; ++i) {
        evaluation::SessionResult result("session-" + std::to_string(i), "agent");
        result.add_metric_measurement(evaluation::MetricMeasurement(
            "accuracy", 0.90 + (i * 0.01), evaluation::MetricType::SuccessRate
        ));
        result.set_status(evaluation::SessionStatus::Completed);
        collector.add_result(result);
    }

    // Add one failed session
    evaluation::SessionResult failed("session-failed", "agent");
    failed.set_status(evaluation::SessionStatus::Failed);
    failed.add_error("test_error", "Test error message");
    collector.add_result(failed);

    // Get statistics
    auto stats = collector.get_statistics();
    EXPECT_EQ(stats["session_count"], 6);
    EXPECT_EQ(stats["completed_count"], 5);
    EXPECT_EQ(stats["failed_count"], 1);

    // Get metric aggregates for accuracy
    auto accuracy_stats = collector.get_metric_aggregates("accuracy");
    EXPECT_EQ(accuracy_stats["count"], 5);
    EXPECT_GT(accuracy_stats["mean"].get<double>(), 0.90);
}

/**
 * Test: Session status transitions
 * Tests different session status states
 */
TEST(EvaluationIntegrationTest, SessionStatusTransitions) {
    evaluation::SessionResult result("session-status-test", "agent");

    // Initial state
    EXPECT_EQ(result.status(), evaluation::SessionStatus::Running);

    // Complete successfully
    result.set_status(evaluation::SessionStatus::Completed);
    EXPECT_EQ(result.status(), evaluation::SessionStatus::Completed);

    // Test status string conversion
    EXPECT_EQ(evaluation::session_status_to_string(evaluation::SessionStatus::Completed), "completed");
    EXPECT_EQ(evaluation::session_status_to_string(evaluation::SessionStatus::Failed), "failed");
    EXPECT_EQ(evaluation::session_status_to_string(evaluation::SessionStatus::Timeout), "timeout");

    // Test status from string
    EXPECT_EQ(evaluation::session_status_from_string("running"), evaluation::SessionStatus::Running);
    EXPECT_EQ(evaluation::session_status_from_string("cancelled"), evaluation::SessionStatus::Cancelled);
}

/**
 * Test: Error recording
 * Tests error collection in SessionResult
 */
TEST(EvaluationIntegrationTest, ErrorRecording) {
    evaluation::SessionResult result("error-test", "agent");

    // Add errors
    result.add_error("connection_error", "Failed to connect to API");
    result.add_error("timeout_error", "Request timed out");

    result.set_status(evaluation::SessionStatus::Failed);

    // Verify errors recorded
    const auto& errors = result.errors();
    EXPECT_EQ(errors.size(), 2);
    EXPECT_EQ(errors[0].type(), "connection_error");
    EXPECT_EQ(errors[1].type(), "timeout_error");
}

/**
 * Test: Quality metrics aggregation
 * Tests using quality metrics with multiple evaluations
 */
TEST(EvaluationIntegrationTest, QualityMetricsAggregation) {
    auto agent = std::make_shared<adapters::EchoAgent>();
    evaluation::AccuracyMetric metric(false);

    std::vector<double> scores;

    // Run multiple evaluations
    for (int i = 0; i < 10; ++i) {
        auto input = core::Message::with_text("user", "Test " + std::to_string(i));
        auto output = core::Message::with_text("assistant", "Test " + std::to_string(i));

        nlohmann::json ctx;
        ctx["expected"] = "Test " + std::to_string(i);

        double score = metric.measure(agent, input, output, ctx);
        scores.push_back(score);
    }

    // All should be accurate
    double total = 0.0;
    for (double score : scores) {
        total += score;
    }
    double avg = total / scores.size();

    EXPECT_EQ(avg, 1.0);  // 100% accuracy
}

/**
 * Test: Recording storage list and delete
 * Tests storage list/delete operations
 */
TEST(EvaluationIntegrationTest, RecordingStorageOperations) {
    auto storage = std::make_shared<evaluation::InMemoryRecordingStorage>();
    evaluation::SessionRecorder recorder(storage);

    // Create multiple recordings
    for (int i = 0; i < 5; ++i) {
        std::string session_id = "session-" + std::to_string(i);
        auto agent = std::make_shared<adapters::EchoAgent>();

        recorder.start_session(session_id, agent->name());
        auto wrapped = recorder.wrap(agent);

        auto msg = core::Message::with_text("user", "Test");
        msg.with_metadata("session_id", session_id);
        auto result = wrapped->process(std::move(msg)).get();
        ASSERT_TRUE(result.is_ok());

        recorder.finalize_session(session_id);
    }

    // List recordings
    auto recordings = storage->list_recordings(10, 0);
    EXPECT_EQ(recordings.size(), 5);

    // Delete one recording
    storage->delete_recording("session-2");

    // Verify deleted
    auto loaded = storage->load_recording("session-2");
    EXPECT_FALSE(loaded.has_value());

    // List again
    auto remaining = storage->list_recordings(10, 0);
    EXPECT_EQ(remaining.size(), 4);
}
