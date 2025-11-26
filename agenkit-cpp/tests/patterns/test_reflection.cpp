/**
 * @file test_reflection.cpp
 * @brief Tests for Reflection pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/reflection.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <memory>

using namespace agenkit;

// Mock agent that returns a response
class MockResponseAgent : public core::Agent {
public:
    MockResponseAgent(std::string response_text)
        : response_text_(std::move(response_text))
    {}

    std::string name() const override {
        return "mock_response";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto response = core::Message::with_text("assistant", response_text_);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }

private:
    std::string response_text_;
};

// Mock reflector that approves after N iterations
class MockApprovalReflector : public core::Agent {
public:
    MockApprovalReflector(int approve_after = 1)
        : approve_after_(approve_after)
        , call_count_(0)
    {}

    std::string name() const override {
        return "mock_approval";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        call_count_++;

        std::string feedback;
        if (call_count_ >= approve_after_) {
            feedback = "APPROVED - Response is good!";
        } else {
            feedback = "Needs improvement - iteration " + std::to_string(call_count_);
        }

        auto response = core::Message::with_text("assistant", feedback);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }

    int get_call_count() const { return call_count_; }

private:
    int approve_after_;
    int call_count_;
};

// Test: Basic reflection with immediate approval
TEST(ReflectionTest, ImmediateApproval) {
    auto agent = std::make_shared<MockResponseAgent>("Initial response");
    auto reflector = std::make_shared<MockApprovalReflector>(1);

    patterns::ReflectionAgent reflection_agent(agent, reflector, 3);

    auto msg = core::Message::with_text("user", "Test query");
    auto future = reflection_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should have 1 reflection iteration (immediate approval)
    EXPECT_TRUE(response.metadata().contains("reflection_iterations"));
    EXPECT_EQ(response.metadata()["reflection_iterations"], 1);

    // Check reflection history
    const auto& history = reflection_agent.get_reflection_history();
    EXPECT_EQ(history.size(), 1);
    EXPECT_EQ(history[0].iteration, 1);
    EXPECT_FALSE(history[0].should_continue);
}

// Test: Multiple reflections before approval
TEST(ReflectionTest, MultipleReflections) {
    auto agent = std::make_shared<MockResponseAgent>("Improving response");
    auto reflector = std::make_shared<MockApprovalReflector>(2);

    patterns::ReflectionAgent reflection_agent(agent, reflector, 5);

    auto msg = core::Message::with_text("user", "Test query");
    auto future = reflection_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should have 2 reflection iterations
    EXPECT_EQ(response.metadata()["reflection_iterations"], 2);

    const auto& history = reflection_agent.get_reflection_history();
    EXPECT_EQ(history.size(), 2);
    EXPECT_TRUE(history[0].should_continue);
    EXPECT_FALSE(history[1].should_continue);
}

// Test: Max reflections limit
TEST(ReflectionTest, MaxReflectionsLimit) {
    auto agent = std::make_shared<MockResponseAgent>("Response");
    auto reflector = std::make_shared<MockApprovalReflector>(10); // Never approves

    patterns::ReflectionAgent reflection_agent(agent, reflector, 3);

    auto msg = core::Message::with_text("user", "Test query");
    auto future = reflection_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should hit max reflections limit
    EXPECT_EQ(response.metadata()["reflection_iterations"], 3);

    const auto& history = reflection_agent.get_reflection_history();
    EXPECT_EQ(history.size(), 3);
    // All should indicate "should continue" since never approved
    for (const auto& step : history) {
        EXPECT_TRUE(step.should_continue);
    }
}

// Test: Reflection convergence (early stop)
TEST(ReflectionTest, ReflectionConvergence) {
    auto agent = std::make_shared<MockResponseAgent>("Good response");
    auto reflector = std::make_shared<MockApprovalReflector>(2);

    patterns::ReflectionAgent reflection_agent(agent, reflector, 5);

    auto msg = core::Message::with_text("user", "Test");
    auto future = reflection_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = reflection_agent.get_reflection_history();
    // Should stop at 2, not reach max of 5
    EXPECT_EQ(history.size(), 2);
    EXPECT_LT(history.size(), 5);
}

// Test: Error handling - null agent
TEST(ReflectionTest, NullAgentError) {
    auto reflector = std::make_shared<MockApprovalReflector>(1);

    EXPECT_THROW(
        patterns::ReflectionAgent(nullptr, reflector, 3),
        std::invalid_argument
    );
}

// Test: Error handling - null reflector
TEST(ReflectionTest, NullReflectorError) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    EXPECT_THROW(
        patterns::ReflectionAgent(agent, nullptr, 3),
        std::invalid_argument
    );
}

// Test: Error handling - invalid max_reflections
TEST(ReflectionTest, InvalidMaxReflections) {
    auto agent = std::make_shared<MockResponseAgent>("Response");
    auto reflector = std::make_shared<MockApprovalReflector>(1);

    EXPECT_THROW(
        patterns::ReflectionAgent(agent, reflector, 0),
        std::invalid_argument
    );

    EXPECT_THROW(
        patterns::ReflectionAgent(agent, reflector, -1),
        std::invalid_argument
    );
}

// Test: Agent capabilities
TEST(ReflectionTest, Capabilities) {
    auto agent = std::make_shared<MockResponseAgent>("Response");
    auto reflector = std::make_shared<MockApprovalReflector>(1);

    patterns::ReflectionAgent reflection_agent(agent, reflector, 3);

    auto caps = reflection_agent.capabilities();
    EXPECT_EQ(caps.size(), 2);
    EXPECT_EQ(caps[0], "reflection");
    EXPECT_EQ(caps[1], "self-improvement");
}

// Test: Name
TEST(ReflectionTest, Name) {
    auto agent = std::make_shared<MockResponseAgent>("Response");
    auto reflector = std::make_shared<MockApprovalReflector>(1);

    patterns::ReflectionAgent reflection_agent(agent, reflector, 3);

    EXPECT_EQ(reflection_agent.name(), "reflection");
}

// Test: Clear history
TEST(ReflectionTest, ClearHistory) {
    auto agent = std::make_shared<MockResponseAgent>("Response");
    auto reflector = std::make_shared<MockApprovalReflector>(2);

    patterns::ReflectionAgent reflection_agent(agent, reflector, 3);

    // First process
    auto msg1 = core::Message::with_text("user", "Test 1");
    auto future1 = reflection_agent.process(std::move(msg1));
    auto result1 = future1.get();

    EXPECT_EQ(reflection_agent.get_reflection_history().size(), 2);

    // Clear history
    reflection_agent.clear_history();
    EXPECT_EQ(reflection_agent.get_reflection_history().size(), 0);

    // Second process should start fresh
    auto msg2 = core::Message::with_text("user", "Test 2");
    auto future2 = reflection_agent.process(std::move(msg2));
    auto result2 = future2.get();

    EXPECT_EQ(reflection_agent.get_reflection_history().size(), 2);
}
