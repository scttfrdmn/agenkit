/**
 * @file test_errors.cpp
 * @brief Tests for error types
 */

#include <gtest/gtest.h>
#include "agenkit/core/errors.hpp"

using namespace agenkit::core;

TEST(AgentErrorTest, CreateError) {
    AgentError error(AgentErrorType::ProcessingError, "test error");

    EXPECT_EQ(error.type(), AgentErrorType::ProcessingError);
    EXPECT_EQ(error.message(), "test error");
}

TEST(AgentErrorTest, InheritsFromStdException) {
    AgentError error(AgentErrorType::Timeout, "timeout occurred");

    // Should be catchable as std::exception
    try {
        throw error;
    } catch (const std::exception& e) {
        EXPECT_STREQ(e.what(), "timeout occurred");
    }
}

TEST(AgentErrorTest, AllErrorTypes) {
    auto types = {
        AgentErrorType::ProcessingError,
        AgentErrorType::Timeout,
        AgentErrorType::NotFound,
        AgentErrorType::Transport,
        AgentErrorType::Serialization,
        AgentErrorType::Http,
        AgentErrorType::Internal,
        AgentErrorType::InvalidInput
    };

    for (auto type : types) {
        AgentError error(type, "test");
        EXPECT_EQ(error.type(), type);
    }
}

TEST(ErrorTypeTest, ToStringConversion) {
    EXPECT_EQ(to_string(AgentErrorType::ProcessingError), "ProcessingError");
    EXPECT_EQ(to_string(AgentErrorType::Timeout), "Timeout");
    EXPECT_EQ(to_string(AgentErrorType::NotFound), "NotFound");
    EXPECT_EQ(to_string(AgentErrorType::Transport), "Transport");
    EXPECT_EQ(to_string(AgentErrorType::Serialization), "Serialization");
    EXPECT_EQ(to_string(AgentErrorType::Http), "Http");
    EXPECT_EQ(to_string(AgentErrorType::Internal), "Internal");
    EXPECT_EQ(to_string(AgentErrorType::InvalidInput), "InvalidInput");
}
