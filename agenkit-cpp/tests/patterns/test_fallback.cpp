/**
 * @file test_fallback.cpp
 * @brief Comprehensive tests for Fallback pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/fallback.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>

using namespace agenkit;
using namespace agenkit::test;

// Test: Valid construction
TEST(FallbackAgentTest, Constructor) {
    auto agent1 = make_mock_agent("agent1", "result1");
    auto agent2 = make_mock_agent("agent2", "result2");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::FallbackAgent fallback(agents);

    EXPECT_EQ(fallback.name(), "fallback");
}

// Test: Constructor with empty agents list
TEST(FallbackAgentTest, ConstructorEmptyAgents) {
    std::vector<std::shared_ptr<core::Agent>> agents;

    EXPECT_THROW(
        {
            patterns::FallbackAgent fallback(agents);
        },
        std::invalid_argument
    );
}

// Test: First agent succeeds
TEST(FallbackAgentTest, FirstAgentSucceeds) {
    auto agent1 = make_mock_agent("agent1", "first success");
    auto agent2 = make_mock_agent("agent2", "should not execute");
    auto agent3 = make_mock_agent("agent3", "should not execute");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test input");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "first success");

    // Only first agent should have been called
    EXPECT_EQ(agent1->call_count(), 1);
    EXPECT_EQ(agent2->call_count(), 0);
    EXPECT_EQ(agent3->call_count(), 0);
}

// Test: First agent fails, second succeeds
TEST(FallbackAgentTest, FirstFailsSecondSucceeds) {
    auto agent1 = make_failing_mock_agent("agent1", "first failed");
    auto agent2 = make_mock_agent("agent2", "second success");
    auto agent3 = make_mock_agent("agent3", "should not execute");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "second success");

    // First two agents should have been called
    EXPECT_EQ(agent1->call_count(), 1);
    EXPECT_EQ(agent2->call_count(), 1);
    EXPECT_EQ(agent3->call_count(), 0);
}

// Test: All agents fail
TEST(FallbackAgentTest, AllAgentsFail) {
    auto agent1 = make_failing_mock_agent("agent1", "failure1");
    auto agent2 = make_failing_mock_agent("agent2", "failure2");
    auto agent3 = make_failing_mock_agent("agent3", "failure3");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();

    // Error should mention all agents failed
    EXPECT_TRUE(error.message().find("failed") != std::string::npos ||
                error.message().find("exhausted") != std::string::npos);

    // All agents should have been tried
    EXPECT_EQ(agent1->call_count(), 1);
    EXPECT_EQ(agent2->call_count(), 1);
    EXPECT_EQ(agent3->call_count(), 1);
}

// Test: Metadata tracking
TEST(FallbackAgentTest, Metadata) {
    auto agent1 = make_failing_mock_agent("agent1");
    auto agent2 = make_mock_agent("agent2", "success");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    expect_metadata_exists(response, "fallback_attempts");
    expect_metadata_value<int>(response, "fallback_attempts", 2);

    expect_metadata_exists(response, "fallback_success_agent");
    expect_metadata_value<std::string>(response, "fallback_success_agent", "agent2");

    expect_metadata_exists(response, "fallback_success_index");
    expect_metadata_value<int>(response, "fallback_success_index", 1);
}

// Test: Error metadata when all fail
TEST(FallbackAgentTest, ErrorMetadataAllFail) {
    auto agent1 = make_failing_mock_agent("agent1", "error1");
    auto agent2 = make_failing_mock_agent("agent2", "error2");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();

    // Error should contain information about all failures
    std::string error_msg = error.message();
    EXPECT_TRUE(error_msg.find("agent1") != std::string::npos ||
                error_msg.find("agent2") != std::string::npos);
}

// Test: Last agent succeeds
TEST(FallbackAgentTest, LastAgentSucceeds) {
    auto agent1 = make_failing_mock_agent("agent1");
    auto agent2 = make_failing_mock_agent("agent2");
    auto agent3 = make_mock_agent("agent3", "last resort");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "last resort");

    // All agents should have been tried
    EXPECT_EQ(agent1->call_count(), 1);
    EXPECT_EQ(agent2->call_count(), 1);
    EXPECT_EQ(agent3->call_count(), 1);

    expect_metadata_value<int>(response, "fallback_success_index", 2);
}

// Test: Capabilities aggregation
TEST(FallbackAgentTest, Capabilities) {
    auto agent1 = make_mock_agent("agent1");
    agent1->set_capabilities({"cap1", "cap2"});

    auto agent2 = make_mock_agent("agent2");
    agent2->set_capabilities({"cap2", "cap3"});

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::FallbackAgent fallback(agents);

    auto caps = fallback.capabilities();

    // Should have fallback capability plus unique agent capabilities
    bool has_fallback = false;
    for (const auto& cap : caps) {
        if (cap == "fallback") {
            has_fallback = true;
        }
    }

    EXPECT_TRUE(has_fallback);
}

// Test: Single agent fallback
TEST(FallbackAgentTest, SingleAgent) {
    auto agent = make_mock_agent("solo", "result");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "input");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "result");

    expect_metadata_value<int>(response, "fallback_attempts", 1);
    expect_metadata_value<int>(response, "fallback_success_index", 0);
}

// Test: Many fallback agents
TEST(FallbackAgentTest, ManyAgents) {
    std::vector<std::shared_ptr<core::Agent>> agents;
    const int num_agents = 10;

    // All fail except last
    for (int i = 0; i < num_agents - 1; ++i) {
        agents.push_back(make_failing_mock_agent("agent" + std::to_string(i)));
    }
    agents.push_back(make_mock_agent("final", "final success"));

    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "final success");

    expect_metadata_value<int>(response, "fallback_attempts", num_agents);
    expect_metadata_value<int>(response, "fallback_success_index", num_agents - 1);
}

// Test: Empty message handling
TEST(FallbackAgentTest, EmptyMessage) {
    auto agent = make_mock_agent("agent1", "response");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "");
    auto result = fallback.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: RecoveryAgent construction
TEST(RecoveryAgentTest, Constructor) {
    auto agent = make_mock_agent("agent", "response");

    auto recovery = [](const core::Message& /* msg */, const core::AgentError& /* err */) {
        return core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", "recovered")
        );
    };

    patterns::RecoveryAgent recovery_agent(agent, recovery);

    EXPECT_EQ(recovery_agent.name(), "agent+Recovery");
}

// Test: RecoveryAgent null agent
TEST(RecoveryAgentTest, ConstructorNullAgent) {
    auto recovery = [](const core::Message& /* msg */, const core::AgentError& /* err */) {
        return core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", "recovered")
        );
    };

    EXPECT_THROW(
        {
            patterns::RecoveryAgent recovery_agent(nullptr, recovery);
        },
        std::invalid_argument
    );
}

// Test: RecoveryAgent null recovery function
TEST(RecoveryAgentTest, ConstructorNullRecovery) {
    auto agent = make_mock_agent("agent");

    EXPECT_THROW(
        {
            patterns::RecoveryAgent recovery_agent(agent, nullptr);
        },
        std::invalid_argument
    );
}

// Test: RecoveryAgent success path
TEST(RecoveryAgentTest, SuccessPath) {
    auto agent = make_mock_agent("agent", "success");

    bool recovery_called = false;
    auto recovery = [&recovery_called](const core::Message& /* msg */, const core::AgentError& /* err */) {
        recovery_called = true;
        return core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", "recovered")
        );
    };

    patterns::RecoveryAgent recovery_agent(agent, recovery);

    auto msg = core::Message::with_text("user", "test");
    auto result = recovery_agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "success");

    // Recovery should not have been called
    EXPECT_FALSE(recovery_called);
}

// Test: RecoveryAgent error recovery
TEST(RecoveryAgentTest, ErrorRecovery) {
    auto agent = make_failing_mock_agent("agent", "agent failed");

    bool recovery_called = false;
    auto recovery = [&recovery_called](const core::Message& /* msg */, const core::AgentError& /* err */) {
        recovery_called = true;
        return core::Result<core::Message, core::AgentError>::ok(
            core::Message::with_text("assistant", "recovered response")
        );
    };

    patterns::RecoveryAgent recovery_agent(agent, recovery);

    auto msg = core::Message::with_text("user", "test");
    auto result = recovery_agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "recovered response");

    // Recovery should have been called
    EXPECT_TRUE(recovery_called);
}

// Test: RecoveryAgent recovery also fails
TEST(RecoveryAgentTest, RecoveryAlsoFails) {
    auto agent = make_failing_mock_agent("agent", "agent failed");

    auto recovery = [](const core::Message& /* msg */, const core::AgentError& /* err */) {
        return core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::Internal, "recovery failed")
        );
    };

    patterns::RecoveryAgent recovery_agent(agent, recovery);

    auto msg = core::Message::with_text("user", "test");
    auto result = recovery_agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("recovery failed") != std::string::npos);
}

// Test: Default recovery - static message
TEST(DefaultRecoveryTest, StaticMessage) {
    auto agent = make_failing_mock_agent("agent");

    auto recovery = patterns::default_recovery::static_message("Fallback response");

    patterns::RecoveryAgent recovery_agent(agent, recovery);

    auto msg = core::Message::with_text("user", "test");
    auto result = recovery_agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "Fallback response");
}

// Test: Default recovery - empty response
TEST(DefaultRecoveryTest, EmptyResponse) {
    auto agent = make_failing_mock_agent("agent");

    auto recovery = patterns::default_recovery::empty_response();

    patterns::RecoveryAgent recovery_agent(agent, recovery);

    auto msg = core::Message::with_text("user", "test");
    auto result = recovery_agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "");
}

// Test: Fallback with different error types
TEST(FallbackAgentTest, DifferentErrorTypes) {
    auto agent1 = std::make_shared<MockAgent>(
        "agent1",
        core::AgentError(core::AgentErrorType::Transport, "network failed")
    );
    auto agent2 = std::make_shared<MockAgent>(
        "agent2",
        core::AgentError(core::AgentErrorType::Timeout, "timeout")
    );
    auto agent3 = make_mock_agent("agent3", "success");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "success");

    // Check that error details are tracked
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("fallback_failed_attempts"));
}

// Test: Message preservation through fallback
TEST(FallbackAgentTest, MessagePreservation) {
    auto agent1 = make_failing_mock_agent("agent1");

    // Agent that echoes the original message
    auto agent2 = std::make_shared<MockAgent>(
        "agent2",
        [](const core::Message& msg) -> core::Result<core::Message, core::AgentError> {
            std::string response = "received: " + msg.content_as_str();
            return core::Result<core::Message, core::AgentError>::ok(
                core::Message::with_text("assistant", response)
            );
        }
    );

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::FallbackAgent fallback(agents);

    auto msg = core::Message::with_text("user", "original message");
    auto result = fallback.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "received: original message");
}
