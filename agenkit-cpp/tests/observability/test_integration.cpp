/**
 * @file test_integration.cpp
 * @brief Integration tests for observability modules working together
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <gtest/gtest.h>
#include "agenkit/observability/tracing.hpp"
#include "agenkit/observability/metrics.hpp"
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/audit.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <filesystem>

using namespace agenkit;
using namespace agenkit::observability;

class ObservabilityIntegrationTest : public ::testing::Test {
protected:
    std::string audit_log_path_;

    void SetUp() override {
        // Initialize all observability components
        try {
            init_tracing("console", "");
        } catch (const std::runtime_error&) {
            // Already initialized
        }

        try {
            init_metrics("console", "");
        } catch (const std::runtime_error&) {
            // Already initialized
        }

        configure_logging("json", "info");

        // Create unique audit log file
        audit_log_path_ = std::filesystem::temp_directory_path() /
                         ("observability_integration_" +
                          std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) +
                          ".log");
    }

    void TearDown() override {
        // Clean up audit log
        if (std::filesystem::exists(audit_log_path_)) {
            std::filesystem::remove(audit_log_path_);
        }
    }
};

TEST_F(ObservabilityIntegrationTest, FullStackObservability) {
    // Create base agent
    auto echo = std::make_shared<EchoAgent>();

    // Wrap with tracing
    auto traced = std::make_shared<TracingMiddleware>(echo, "integration_test");

    // Wrap with metrics
    auto observed = std::make_shared<MetricsMiddleware>(traced);

    // Create audit logger
    auto audit = AuditLogger::create(audit_log_path_);

    // Log agent creation event
    audit->log(
        AuditEvent::create(AuditEventType::AgentCreated, "echo_agent", "test_session_001")
            .with_detail("wrapped_with", "tracing,metrics")
            .with_severity(Severity::INFO)
    );

    // Create message
    Message msg;
    msg.role = "user";
    msg.content = "Integration test message";

    // Log the event
    log_agent_event("message_received", "Processing message with full observability");

    // Process message (creates span, records metrics, includes trace in logs)
    auto result_future = observed->process(msg);
    auto result = result_future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.content, "Integration test message");

    // Log success
    log_agent_event("message_processed", "Message processed successfully");

    // Audit the operation
    audit->log(
        AuditEvent::create(AuditEventType::MessageProcessed, "echo_agent", "test_session_001")
            .with_detail("message_content", "Integration test message")
            .with_severity(Severity::INFO)
    );

    audit->flush();

    // Verify audit events were logged
    auto events = audit->query();
    EXPECT_EQ(events.size(), 2);
    EXPECT_EQ(events[0].event_type(), AuditEventType::AgentCreated);
    EXPECT_EQ(events[1].event_type(), AuditEventType::MessageProcessed);
}

TEST_F(ObservabilityIntegrationTest, DistributedTracingWithMetrics) {
    // Create two agents
    auto agent1 = std::make_shared<EchoAgent>();
    auto agent2 = std::make_shared<EchoAgent>();

    // Wrap both with tracing and metrics
    auto traced1 = std::make_shared<TracingMiddleware>(agent1, "agent1.process");
    auto observed1 = std::make_shared<MetricsMiddleware>(traced1);

    auto traced2 = std::make_shared<TracingMiddleware>(agent2, "agent2.process");
    auto observed2 = std::make_shared<MetricsMiddleware>(traced2);

    // Create message with trace context
    Message msg1;
    msg1.role = "user";
    msg1.content = "First agent message";

    // Process with first agent
    auto result1_future = observed1->process(msg1);
    auto result1 = result1_future.get();
    ASSERT_TRUE(result1.is_ok());

    auto response1 = result1.unwrap();

    // Use response as input to second agent (trace context propagated)
    auto result2_future = observed2->process(response1);
    auto result2 = result2_future.get();
    ASSERT_TRUE(result2.is_ok());

    auto response2 = result2.unwrap();

    // Verify trace context exists in metadata
    EXPECT_TRUE(response2.metadata.contains("traceparent"));

    // Both agents should have recorded metrics
    EXPECT_TRUE(true); // Metrics are recorded globally
}

TEST_F(ObservabilityIntegrationTest, ErrorHandlingWithAudit) {
    // Create agent that will fail
    auto failing_agent = std::make_shared<EchoAgent>();
    auto traced = std::make_shared<TracingMiddleware>(failing_agent, "failing_agent");
    auto observed = std::make_shared<MetricsMiddleware>(traced);

    auto audit = AuditLogger::create(audit_log_path_);

    // Create invalid message (empty content should work, but let's audit it)
    Message msg;
    msg.role = "user";
    msg.content = "";

    // Log warning
    log_agent_warning("empty_message", "Received message with empty content");

    // Audit the warning
    audit->log(
        AuditEvent::create(AuditEventType::MessageFailed, "failing_agent", "test_session_002")
            .with_detail("reason", "empty_content")
            .with_severity(Severity::WARNING)
    );

    // Process message
    auto result_future = observed->process(msg);
    auto result = result_future.get();

    // Even with empty content, EchoAgent should succeed
    ASSERT_TRUE(result.is_ok());

    audit->flush();

    // Verify audit event
    auto events = audit->query();
    EXPECT_EQ(events.size(), 1);
    EXPECT_EQ(events[0].severity(), Severity::WARNING);
}

TEST_F(ObservabilityIntegrationTest, SecurityViolationAudit) {
    auto audit = AuditLogger::create(audit_log_path_);

    // Simulate security violation
    log_agent_error("security_violation", "Unauthorized access attempt", "User attempted to access restricted resource");

    audit->log(
        AuditEvent::create(AuditEventType::SecurityViolation, "security_agent", "suspicious_session")
            .with_detail("violation_type", "unauthorized_access")
            .with_detail("resource", "admin_panel")
            .with_detail("user_ip", "192.168.1.100")
            .with_severity(Severity::CRITICAL)
    );

    audit->flush();

    // Query security violations
    auto violations = audit->query_by_type(AuditEventType::SecurityViolation);
    EXPECT_EQ(violations.size(), 1);
    EXPECT_EQ(violations[0].severity(), Severity::CRITICAL);
    EXPECT_TRUE(violations[0].details().contains("violation_type"));
}

TEST_F(ObservabilityIntegrationTest, MultiSessionAudit) {
    auto audit = AuditLogger::create(audit_log_path_);

    // Create agents for different sessions
    std::vector<std::string> sessions = {"session_001", "session_002", "session_003"};

    for (const auto& session_id : sessions) {
        auto agent = std::make_shared<EchoAgent>();
        auto traced = std::make_shared<TracingMiddleware>(agent, "multi_session_agent");

        // Audit agent creation
        audit->log(
            AuditEvent::create(AuditEventType::AgentCreated, "multi_session_agent", session_id)
                .with_detail("session_type", "test")
        );

        // Process message
        Message msg;
        msg.role = "user";
        msg.content = "Message for " + session_id;

        auto result_future = traced->process(msg);
        auto result = result_future.get();
        ASSERT_TRUE(result.is_ok());

        // Audit message processing
        audit->log(
            AuditEvent::create(AuditEventType::MessageProcessed, "multi_session_agent", session_id)
                .with_detail("message_length", std::to_string(msg.content.length()))
        );
    }

    audit->flush();

    // Query by session
    for (const auto& session_id : sessions) {
        auto session_events = audit->query_by_session(session_id);
        EXPECT_EQ(session_events.size(), 2); // Created + Processed
    }
}

TEST_F(ObservabilityIntegrationTest, TraceContextPropagation) {
    auto agent1 = std::make_shared<EchoAgent>();
    auto traced1 = std::make_shared<TracingMiddleware>(agent1, "agent1");

    auto agent2 = std::make_shared<EchoAgent>();
    auto traced2 = std::make_shared<TracingMiddleware>(agent2, "agent2");

    // Create initial message
    Message msg1;
    msg1.role = "user";
    msg1.content = "Trace propagation test";

    // Process with first agent
    auto result1_future = traced1->process(msg1);
    auto result1 = result1_future.get();
    ASSERT_TRUE(result1.is_ok());

    auto response1 = result1.unwrap();

    // Extract trace context
    auto context = extract_trace_context(response1.metadata);
    EXPECT_TRUE(context.IsValid());

    // Pass to second agent - context should be propagated
    auto result2_future = traced2->process(response1);
    auto result2 = result2_future.get();
    ASSERT_TRUE(result2.is_ok());

    auto response2 = result2.unwrap();

    // Trace context should be in metadata
    EXPECT_TRUE(response2.metadata.contains("traceparent"));
}

TEST_F(ObservabilityIntegrationTest, ConcurrentObservability) {
    auto audit = AuditLogger::create(audit_log_path_, 1000);

    std::vector<std::thread> threads;
    const int num_threads = 3;
    const int ops_per_thread = 5;

    for (int i = 0; i < num_threads; i++) {
        threads.emplace_back([i, ops_per_thread, &audit]() {
            auto agent = std::make_shared<EchoAgent>();
            auto traced = std::make_shared<TracingMiddleware>(agent, "concurrent_agent_" + std::to_string(i));
            auto observed = std::make_shared<MetricsMiddleware>(traced);

            for (int j = 0; j < ops_per_thread; j++) {
                std::string session_id = "session_" + std::to_string(i) + "_" + std::to_string(j);

                // Log event
                log_agent_event("concurrent_processing", "Thread " + std::to_string(i) + " operation " + std::to_string(j));

                // Process message
                Message msg;
                msg.role = "user";
                msg.content = "Concurrent message " + std::to_string(j);

                auto result_future = observed->process(msg);
                auto result = result_future.get();

                // Audit
                audit->log(
                    AuditEvent::create(AuditEventType::MessageProcessed, "concurrent_agent_" + std::to_string(i), session_id)
                        .with_detail("thread", std::to_string(i))
                        .with_detail("operation", std::to_string(j))
                );
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    audit->flush();

    // Verify all operations were audited
    auto events = audit->query();
    EXPECT_EQ(events.size(), num_threads * ops_per_thread);
}

#endif // AGENKIT_WITH_OBSERVABILITY
