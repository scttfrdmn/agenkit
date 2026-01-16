/**
 * @file test_audit.cpp
 * @brief Tests for audit logging for compliance and security
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <gtest/gtest.h>
#include "agenkit/observability/audit.hpp"
#include <filesystem>
#include <fstream>
#include <thread>
#include <vector>

using namespace agenkit::observability;

class AuditTest : public ::testing::Test {
protected:
    std::string test_log_path_;

    void SetUp() override {
        // Create unique test log file
        test_log_path_ = std::filesystem::temp_directory_path() /
                        ("audit_test_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count()) + ".log");
    }

    void TearDown() override {
        // Clean up test file
        if (std::filesystem::exists(test_log_path_)) {
            std::filesystem::remove(test_log_path_);
        }
    }
};

TEST_F(AuditTest, CreateAuditEvent) {
    auto event = AuditEvent::create(
        AuditEventType::MessageProcessed,
        "test_agent",
        "session_123"
    );

    EXPECT_EQ(event.event_type(), AuditEventType::MessageProcessed);
    EXPECT_EQ(event.agent_name(), "test_agent");
    EXPECT_EQ(event.session_id(), "session_123");
    EXPECT_FALSE(event.event_id().empty());
    EXPECT_EQ(event.severity(), Severity::INFO);
}

TEST_F(AuditTest, EventIDIsUnique) {
    auto event1 = AuditEvent::create(AuditEventType::MessageProcessed, "agent1");
    auto event2 = AuditEvent::create(AuditEventType::MessageProcessed, "agent2");

    EXPECT_NE(event1.event_id(), event2.event_id());
}

TEST_F(AuditTest, FluentAPI) {
    auto event = AuditEvent::create(
        AuditEventType::SecurityViolation,
        "test_agent",
        "session_456"
    )
    .with_detail("violation_type", "unauthorized_access")
    .with_detail("resource", "secret_data")
    .with_severity(Severity::CRITICAL);

    EXPECT_EQ(event.severity(), Severity::CRITICAL);

    auto details = event.details();
    EXPECT_TRUE(details.contains("violation_type"));
    EXPECT_EQ(details["violation_type"], "unauthorized_access");
    EXPECT_TRUE(details.contains("resource"));
    EXPECT_EQ(details["resource"], "secret_data");
}

TEST_F(AuditTest, EventToJSON) {
    auto event = AuditEvent::create(
        AuditEventType::MessageProcessed,
        "test_agent",
        "session_789"
    )
    .with_detail("message_id", "msg_123")
    .with_severity(Severity::INFO);

    auto json = event.to_json();

    EXPECT_TRUE(json.contains("event_id"));
    EXPECT_TRUE(json.contains("timestamp"));
    EXPECT_TRUE(json.contains("event_type"));
    EXPECT_EQ(json["event_type"], "MessageProcessed");
    EXPECT_EQ(json["agent_name"], "test_agent");
    EXPECT_EQ(json["session_id"], "session_789");
    EXPECT_EQ(json["severity"], "INFO");
    EXPECT_TRUE(json["details"].contains("message_id"));
}

TEST_F(AuditTest, EventFromJSON) {
    auto original = AuditEvent::create(
        AuditEventType::ErrorOccurred,
        "test_agent",
        "session_abc"
    )
    .with_detail("error_code", "ERR_001")
    .with_severity(Severity::ERROR);

    auto json = original.to_json();
    auto restored = AuditEvent::from_json(json);

    EXPECT_EQ(restored.event_id(), original.event_id());
    EXPECT_EQ(restored.event_type(), original.event_type());
    EXPECT_EQ(restored.agent_name(), original.agent_name());
    EXPECT_EQ(restored.session_id(), original.session_id());
    EXPECT_EQ(restored.severity(), original.severity());
    EXPECT_EQ(restored.details()["error_code"], original.details()["error_code"]);
}

TEST_F(AuditTest, AuditLoggerCreation) {
    auto logger = AuditLogger::create(test_log_path_);
    EXPECT_TRUE(logger != nullptr);
    EXPECT_TRUE(std::filesystem::exists(test_log_path_));
}

TEST_F(AuditTest, LogAuditEvent) {
    auto logger = AuditLogger::create(test_log_path_);

    auto event = AuditEvent::create(
        AuditEventType::AgentCreated,
        "new_agent",
        "session_001"
    );

    EXPECT_NO_THROW(logger->log(event));
}

TEST_F(AuditTest, BufferAutoFlush) {
    const size_t buffer_size = 5;
    auto logger = AuditLogger::create(test_log_path_, buffer_size);

    // Log exactly buffer_size events to trigger auto-flush
    for (size_t i = 0; i < buffer_size; i++) {
        auto event = AuditEvent::create(
            AuditEventType::MessageProcessed,
            "test_agent",
            "session_" + std::to_string(i)
        );
        logger->log(event);
    }

    // Events should be flushed to file
    auto events = logger->query();
    EXPECT_EQ(events.size(), buffer_size);
}

TEST_F(AuditTest, ManualFlush) {
    auto logger = AuditLogger::create(test_log_path_, 100);

    // Log a few events
    for (int i = 0; i < 3; i++) {
        auto event = AuditEvent::create(
            AuditEventType::MessageProcessed,
            "test_agent",
            "session_" + std::to_string(i)
        );
        logger->log(event);
    }

    // Manually flush
    logger->flush();

    // Events should be in file
    auto events = logger->query();
    EXPECT_EQ(events.size(), 3);
}

TEST_F(AuditTest, QueryBySessionID) {
    auto logger = AuditLogger::create(test_log_path_, 100);

    // Log events with different session IDs
    for (int i = 0; i < 5; i++) {
        auto event = AuditEvent::create(
            AuditEventType::MessageProcessed,
            "agent_" + std::to_string(i),
            i % 2 == 0 ? "session_even" : "session_odd"
        );
        logger->log(event);
    }

    logger->flush();

    auto even_events = logger->query_by_session("session_even");
    EXPECT_EQ(even_events.size(), 3);

    auto odd_events = logger->query_by_session("session_odd");
    EXPECT_EQ(odd_events.size(), 2);
}

TEST_F(AuditTest, QueryByAgentName) {
    auto logger = AuditLogger::create(test_log_path_, 100);

    // Log events from different agents
    for (int i = 0; i < 4; i++) {
        auto event = AuditEvent::create(
            AuditEventType::MessageProcessed,
            i < 2 ? "agent_a" : "agent_b",
            "session_123"
        );
        logger->log(event);
    }

    logger->flush();

    auto agent_a_events = logger->query_by_agent("agent_a");
    EXPECT_EQ(agent_a_events.size(), 2);

    auto agent_b_events = logger->query_by_agent("agent_b");
    EXPECT_EQ(agent_b_events.size(), 2);
}

TEST_F(AuditTest, QueryByEventType) {
    auto logger = AuditLogger::create(test_log_path_, 100);

    // Log events of different types
    logger->log(AuditEvent::create(AuditEventType::AgentCreated, "agent1"));
    logger->log(AuditEvent::create(AuditEventType::AgentCreated, "agent2"));
    logger->log(AuditEvent::create(AuditEventType::MessageProcessed, "agent1"));
    logger->log(AuditEvent::create(AuditEventType::SecurityViolation, "agent1"));

    logger->flush();

    auto created_events = logger->query_by_type(AuditEventType::AgentCreated);
    EXPECT_EQ(created_events.size(), 2);

    auto processed_events = logger->query_by_type(AuditEventType::MessageProcessed);
    EXPECT_EQ(processed_events.size(), 1);

    auto violation_events = logger->query_by_type(AuditEventType::SecurityViolation);
    EXPECT_EQ(violation_events.size(), 1);
}

TEST_F(AuditTest, QueryWithCustomFilter) {
    auto logger = AuditLogger::create(test_log_path_, 100);

    // Log events with different severities
    logger->log(AuditEvent::create(AuditEventType::MessageProcessed, "agent1")
                    .with_severity(Severity::INFO));
    logger->log(AuditEvent::create(AuditEventType::MessageFailed, "agent1")
                    .with_severity(Severity::WARNING));
    logger->log(AuditEvent::create(AuditEventType::ErrorOccurred, "agent1")
                    .with_severity(Severity::ERROR));
    logger->log(AuditEvent::create(AuditEventType::SecurityViolation, "agent1")
                    .with_severity(Severity::CRITICAL));

    logger->flush();

    // Query for critical and error events only
    auto critical_and_error = logger->query_with_filter([](const AuditEvent& event) {
        return event.severity() == Severity::CRITICAL || event.severity() == Severity::ERROR;
    });

    EXPECT_EQ(critical_and_error.size(), 2);
}

TEST_F(AuditTest, ConcurrentLogging) {
    auto logger = AuditLogger::create(test_log_path_, 1000);

    const int num_threads = 5;
    const int events_per_thread = 10;
    std::vector<std::thread> threads;

    // Log from multiple threads
    for (int i = 0; i < num_threads; i++) {
        threads.emplace_back([&logger, i, events_per_thread]() {
            for (int j = 0; j < events_per_thread; j++) {
                auto event = AuditEvent::create(
                    AuditEventType::MessageProcessed,
                    "agent_" + std::to_string(i),
                    "session_" + std::to_string(j)
                )
                .with_detail("thread", std::to_string(i))
                .with_detail("iteration", std::to_string(j));

                logger->log(event);
            }
        });
    }

    // Wait for all threads
    for (auto& thread : threads) {
        thread.join();
    }

    logger->flush();

    // All events should be logged
    auto all_events = logger->query();
    EXPECT_EQ(all_events.size(), num_threads * events_per_thread);
}

TEST_F(AuditTest, EventTypeToString) {
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::AgentCreated), "AgentCreated");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::AgentDestroyed), "AgentDestroyed");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::MessageProcessed), "MessageProcessed");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::MessageFailed), "MessageFailed");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::SecurityViolation), "SecurityViolation");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::ConfigurationChanged), "ConfigurationChanged");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::ErrorOccurred), "ErrorOccurred");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::UserAction), "UserAction");
    EXPECT_EQ(audit_event_type_to_string(AuditEventType::SystemEvent), "SystemEvent");
}

TEST_F(AuditTest, SeverityToString) {
    EXPECT_EQ(severity_to_string(Severity::INFO), "INFO");
    EXPECT_EQ(severity_to_string(Severity::WARNING), "WARNING");
    EXPECT_EQ(severity_to_string(Severity::ERROR), "ERROR");
    EXPECT_EQ(severity_to_string(Severity::CRITICAL), "CRITICAL");
}

TEST_F(AuditTest, SetBufferSize) {
    auto logger = AuditLogger::create(test_log_path_, 100);

    // Change buffer size
    logger->set_buffer_size(10);

    // Log 10 events to trigger auto-flush
    for (int i = 0; i < 10; i++) {
        auto event = AuditEvent::create(
            AuditEventType::MessageProcessed,
            "test_agent",
            "session_" + std::to_string(i)
        );
        logger->log(event);
    }

    // Events should be flushed
    auto events = logger->query();
    EXPECT_EQ(events.size(), 10);
}

#endif // AGENKIT_WITH_OBSERVABILITY
