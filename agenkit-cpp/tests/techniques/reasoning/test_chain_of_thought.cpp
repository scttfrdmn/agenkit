/**
 * @file test_chain_of_thought.cpp
 * @brief Tests for Chain-of-Thought reasoning technique
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/chain_of_thought.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <vector>
#include <string>

using namespace agenkit::techniques::reasoning;
using namespace agenkit::core;

/**
 * @brief Mock agent for testing
 */
class MockAgent : public Agent {
public:
    MockAgent(const std::vector<std::string>& responses)
        : responses_(responses), call_count_(0) {}

    std::string name() const override {
        return "mock_agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() mutable {
            size_t idx = call_count_ % responses_.size();
            call_count_++;
            return Result<Message, AgentError>::ok(
                Message::with_text("assistant", responses_[idx])
            );
        });
    }

private:
    std::vector<std::string> responses_;
    size_t call_count_;
};

// Test basic Chain-of-Thought functionality
TEST(ChainOfThoughtTest, BasicFunctionality) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First, analyze the problem.\n2. Then, calculate.\n3. The answer is 42."
    });

    ChainOfThoughtAgent cot(mock);

    auto message = Message::with_text("user", "What is the answer?");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_TRUE(response.content_as_str().find("42") != std::string::npos);

    // Check metadata
    auto metadata = response.metadata();
    EXPECT_EQ(metadata["technique"].get<std::string>(), "chain_of_thought");

    // Check reasoning steps
    EXPECT_TRUE(metadata.contains("reasoning_steps"));
    auto steps = metadata["reasoning_steps"].get<std::vector<std::string>>();
    EXPECT_EQ(steps.size(), 3);

    EXPECT_TRUE(metadata.contains("num_steps"));
    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 3);
}

// Test name and capabilities
TEST(ChainOfThoughtTest, NameAndCapabilities) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"response"});
    ChainOfThoughtAgent cot(mock);

    EXPECT_EQ(cot.name(), "chain_of_thought");

    auto caps = cot.capabilities();
    EXPECT_EQ(caps.size(), 4);
    EXPECT_NE(std::find(caps.begin(), caps.end(), "reasoning"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "step_by_step"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "chain_of_thought"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "explainable_ai"), caps.end());
}

// Test numbered step parsing
TEST(ChainOfThoughtTest, NumberedSteps) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First step\n2. Second step\n3. Third step\n4. Fourth step"
    });

    ChainOfThoughtAgent cot(mock);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto steps = metadata["reasoning_steps"].get<std::vector<std::string>>();

    EXPECT_EQ(steps.size(), 4);
    EXPECT_EQ(steps[0], "First step");
    EXPECT_EQ(steps[1], "Second step");
}

// Test numbered steps with parentheses
TEST(ChainOfThoughtTest, NumberedStepsParentheses) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1) First step\n2) Second step\n3) Third step"
    });

    ChainOfThoughtAgent cot(mock);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto steps = metadata["reasoning_steps"].get<std::vector<std::string>>();

    EXPECT_EQ(steps.size(), 3);
}

// Test bullet point parsing
TEST(ChainOfThoughtTest, BulletPoints) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "- First step\n- Second step\n- Third step"
    });

    ChainOfThoughtAgent cot(mock);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto steps = metadata["reasoning_steps"].get<std::vector<std::string>>();

    EXPECT_EQ(steps.size(), 3);
    EXPECT_EQ(steps[0], "First step");
}

// Test custom prompt template
TEST(ChainOfThoughtTest, CustomTemplate) {
    std::string captured_prompt;

    class CustomAgent : public Agent {
    public:
        std::string* captured;

        CustomAgent(std::string* cap) : captured(cap) {}

        std::string name() const override { return "custom"; }
        std::vector<std::string> capabilities() const override { return {"testing"}; }

        std::future<Result<Message, AgentError>> process(Message message) override {
            return std::async(std::launch::async, [this, msg = std::move(message)]() mutable {
                *captured = msg.content_as_str();
                return Result<Message, AgentError>::ok(
                    Message::with_text("assistant", "1. Answer")
                );
            });
        }
    };

    auto custom = std::make_shared<CustomAgent>(&captured_prompt);

    ChainOfThoughtConfig config;
    config.prompt_template = "Solve carefully:\n{query}";

    ChainOfThoughtAgent cot(custom, config);

    auto message = Message::with_text("user", "Test query");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(captured_prompt, "Solve carefully:\nTest query");
}

// Test max steps limiting
TEST(ChainOfThoughtTest, MaxSteps) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First\n2. Second\n3. Third\n4. Fourth\n5. Fifth\n6. Sixth"
    });

    ChainOfThoughtConfig config;
    config.max_steps = 3;

    ChainOfThoughtAgent cot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto steps = metadata["reasoning_steps"].get<std::vector<std::string>>();

    EXPECT_EQ(steps.size(), 3);
    EXPECT_EQ(metadata["num_steps"].get<size_t>(), 3);
}

// Test parse steps disabled
TEST(ChainOfThoughtTest, ParseStepsDisabled) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First\n2. Second\n3. Third"
    });

    ChainOfThoughtConfig config;
    config.parse_steps = false;

    ChainOfThoughtAgent cot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_FALSE(metadata.contains("reasoning_steps"));
    EXPECT_FALSE(metadata.contains("num_steps"));
    EXPECT_EQ(metadata["technique"].get<std::string>(), "chain_of_thought");
}

// Test error on missing {query} placeholder
TEST(ChainOfThoughtTest, MissingPlaceholder) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"response"});

    ChainOfThoughtConfig config;
    config.prompt_template = "This template has no placeholder";

    ChainOfThoughtAgent cot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_err());
    EXPECT_TRUE(result.unwrap_err().message().find("placeholder") != std::string::npos);
}

// Test empty response
TEST(ChainOfThoughtTest, EmptyResponse) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{""});

    ChainOfThoughtAgent cot(mock);

    auto message = Message::with_text("user", "Test");
    auto future = cot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto steps = metadata["reasoning_steps"].get<std::vector<std::string>>();

    EXPECT_EQ(steps.size(), 0);
}
