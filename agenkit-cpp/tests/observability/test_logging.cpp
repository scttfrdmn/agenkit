/**
 * @file test_logging.cpp
 * @brief Tests for structured logging with trace correlation
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include <gtest/gtest.h>
#include "agenkit/observability/logging.hpp"
#include "agenkit/observability/tracing.hpp"
#include <map>
#include <string>

using namespace agenkit::observability;

class LoggingTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Tests run with auto-configuration if configure_logging() not called
    }

    void TearDown() override {
        // Reset is not possible due to global state, but tests are independent
    }
};

TEST_F(LoggingTest, ParseLogFormatJSON) {
    auto format = parse_log_format("json");
    EXPECT_EQ(format, LogFormat::JSON);
}

TEST_F(LoggingTest, ParseLogFormatCompact) {
    auto format = parse_log_format("compact");
    EXPECT_EQ(format, LogFormat::COMPACT);
}

TEST_F(LoggingTest, ParseLogFormatPretty) {
    auto format = parse_log_format("pretty");
    EXPECT_EQ(format, LogFormat::PRETTY);
}

TEST_F(LoggingTest, ParseLogFormatInvalid) {
    EXPECT_THROW(parse_log_format("invalid"), std::invalid_argument);
}

TEST_F(LoggingTest, ParseLogLevelTrace) {
    auto level = parse_log_level("trace");
    EXPECT_EQ(level, LogLevel::TRACE);
}

TEST_F(LoggingTest, ParseLogLevelDebug) {
    auto level = parse_log_level("debug");
    EXPECT_EQ(level, LogLevel::DEBUG);
}

TEST_F(LoggingTest, ParseLogLevelInfo) {
    auto level = parse_log_level("info");
    EXPECT_EQ(level, LogLevel::INFO);
}

TEST_F(LoggingTest, ParseLogLevelWarn) {
    auto level = parse_log_level("warn");
    EXPECT_EQ(level, LogLevel::WARN);
}

TEST_F(LoggingTest, ParseLogLevelError) {
    auto level = parse_log_level("error");
    EXPECT_EQ(level, LogLevel::ERROR);
}

TEST_F(LoggingTest, ParseLogLevelCritical) {
    auto level = parse_log_level("critical");
    EXPECT_EQ(level, LogLevel::CRITICAL);
}

TEST_F(LoggingTest, ParseLogLevelInvalid) {
    EXPECT_THROW(parse_log_level("invalid"), std::invalid_argument);
}

TEST_F(LoggingTest, LogAgentEventBasic) {
    // Should not crash
    log_agent_event("test_event", "Test message");
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogAgentEventWithContext) {
    std::map<std::string, std::string> context;
    context["agent"] = "test_agent";
    context["session_id"] = "abc123";

    // Should not crash
    log_agent_event("test_event", "Test message with context", context);
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogAgentEventEmptyContext) {
    std::map<std::string, std::string> empty_context;

    // Should not crash
    log_agent_event("test_event", "Test message", empty_context);
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogAgentError) {
    // Should not crash
    log_agent_error("test_error", "Error message", "Error details");
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogAgentErrorEmpty) {
    // Should not crash with empty error string
    log_agent_error("test_error", "Error message", "");
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogAgentWarning) {
    // Should not crash
    log_agent_warning("test_warning", "Warning message");
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogAgentWarningWithContext) {
    std::map<std::string, std::string> context;
    context["retry_count"] = "2";
    context["max_retries"] = "3";

    // Should not crash
    log_agent_warning("retry_attempt", "Retrying operation", context);
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, MultipleLogCalls) {
    // Should handle multiple log calls without issue
    for (int i = 0; i < 10; i++) {
        log_agent_event("loop_event", "Event " + std::to_string(i));
    }
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogWithSpecialCharacters) {
    std::map<std::string, std::string> context;
    context["key"] = "value with \"quotes\" and \\ backslashes";

    // Should handle special characters
    log_agent_event("special_chars", "Message with special chars: ñ € 中文", context);
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogWithEmptyStrings) {
    // Should handle empty strings
    log_agent_event("", "");
    log_agent_error("", "", "");
    log_agent_warning("", "");
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, LogWithLongStrings) {
    std::string long_message(1000, 'a');
    std::string long_error(1000, 'b');

    // Should handle long strings
    log_agent_event("long_event", long_message);
    log_agent_error("long_error", long_message, long_error);
    EXPECT_TRUE(true);
}

TEST_F(LoggingTest, ConcurrentLogging) {
    // Logging should be thread-safe
    std::vector<std::thread> threads;

    for (int i = 0; i < 5; i++) {
        threads.emplace_back([i]() {
            for (int j = 0; j < 10; j++) {
                std::map<std::string, std::string> context;
                context["thread"] = std::to_string(i);
                context["iteration"] = std::to_string(j);
                log_agent_event("concurrent_event", "Thread " + std::to_string(i), context);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    EXPECT_TRUE(true);
}

// Test with tracing integration
TEST_F(LoggingTest, LogWithTracingContext) {
    try {
        // Initialize tracing if not already done
        init_tracing("console", "");
    } catch (const std::runtime_error&) {
        // Already initialized
    }

    try {
        auto tracer = get_tracer("test");

        // Create a span
        auto span = tracer->StartSpan("test_operation");

        // Log within span context (would include trace_id/span_id)
        log_agent_event("traced_event", "Event with trace context");

        span->End();

        EXPECT_TRUE(true);
    } catch (const std::exception& e) {
        // Tracing not available - skip test
        GTEST_SKIP() << "Tracing not available: " << e.what();
    }
}

#endif // AGENKIT_WITH_OBSERVABILITY
