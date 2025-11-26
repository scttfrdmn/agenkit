/**
 * @file test_reasoning_with_tools.cpp
 * @brief Tests for Reasoning with Tools pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/reasoning_with_tools.hpp"
#include <memory>

using namespace agenkit;

// Mock tool for testing
class MockCalculator : public patterns::Tool {
public:
    std::string name() const override { return "calculator"; }
    std::string description() const override { return "Performs calculations"; }

    patterns::ToolResult execute(const std::string& input) override {
        return patterns::ToolResult::ok("Result: 42");
    }
};

// Mock reasoning agent
class MockReasoningLLM : public core::Agent {
private:
    int call_count_;
    bool include_tool_use_;

public:
    MockReasoningLLM(bool include_tool_use = false)
        : call_count_(0), include_tool_use_(include_tool_use) {}

    std::string name() const override { return "mock_llm"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        call_count_++;
        std::string response;

        if (call_count_ == 1 && include_tool_use_) {
            response = "Step 1: I need to calculate.\n";
            response += "USE TOOL: calculator: 2 + 2\n";
            response += "Conclusion: Need calculation result\n";
            response += "CONFIDENCE: 0.9";
        } else {
            response = "Step " + std::to_string(call_count_) + ": Final reasoning\n";
            response += "Conclusion: The answer is 42\n";
            response += "CONFIDENCE: 0.95\n";
            response += "FINAL ANSWER: 42";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Test: Basic reasoning without tools
TEST(ReasoningWithToolsTest, BasicReasoning) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    auto msg = core::Message::with_text("user", "What is the answer?");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("42") != std::string::npos);
    EXPECT_TRUE(response.metadata().contains("reasoning_steps"));
}

// Test: Reasoning with tool use
TEST(ReasoningWithToolsTest, ReasoningWithTools) {
    auto llm = std::make_shared<MockReasoningLLM>(true);
    patterns::ReasoningAgent agent(llm);

    auto tool = std::make_shared<MockCalculator>();
    agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Calculate something");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = agent.get_reasoning_history();
    EXPECT_GT(history.size(), 0);

    // Check that tool was used
    bool tool_used = false;
    for (const auto& step : history) {
        if (step.requires_tool) {
            tool_used = true;
            EXPECT_FALSE(step.tool_result.empty());
        }
    }
    EXPECT_TRUE(tool_used);
}

// Test: Confidence tracking
TEST(ReasoningWithToolsTest, ConfidenceTracking) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    auto msg = core::Message::with_text("user", "Test");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("average_confidence"));
    double avg_conf = response.metadata()["average_confidence"];
    EXPECT_GT(avg_conf, 0.0);
    EXPECT_LE(avg_conf, 1.0);
}

// Test: Reasoning history
TEST(ReasoningWithToolsTest, ReasoningHistory) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    auto msg = core::Message::with_text("user", "Test");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = agent.get_reasoning_history();
    EXPECT_EQ(history.size(), 1);
    EXPECT_EQ(history[0].step, 1);
    EXPECT_FALSE(history[0].reasoning.empty());
    EXPECT_GT(history[0].confidence, 0.0);
}

// Test: Clear history
TEST(ReasoningWithToolsTest, ClearHistory) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    auto msg = core::Message::with_text("user", "Test");
    agent.process(std::move(msg)).get();

    EXPECT_GT(agent.get_reasoning_history().size(), 0);

    agent.clear_history();
    EXPECT_EQ(agent.get_reasoning_history().size(), 0);
}

// Test: Configuration
TEST(ReasoningWithToolsTest, Configuration) {
    auto llm = std::make_shared<MockReasoningLLM>();

    patterns::ReasoningConfig config;
    config.max_reasoning_steps = 20;
    config.min_confidence = 0.8;
    config.allow_backtracking = true;

    patterns::ReasoningAgent agent(llm, config);

    auto retrieved = agent.get_config();
    EXPECT_EQ(retrieved.max_reasoning_steps, 20);
    EXPECT_EQ(retrieved.min_confidence, 0.8);
    EXPECT_TRUE(retrieved.allow_backtracking);
}

// Test: Capabilities
TEST(ReasoningWithToolsTest, Capabilities) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    auto caps = agent.capabilities();
    EXPECT_EQ(caps.size(), 4);
    EXPECT_EQ(caps[0], "reasoning");
    EXPECT_EQ(caps[1], "chain-of-thought");
    EXPECT_EQ(caps[2], "tool-use");
    EXPECT_EQ(caps[3], "planning");
}

// Test: Name
TEST(ReasoningWithToolsTest, Name) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    EXPECT_EQ(agent.name(), "reasoning");
}

// Test: Metadata
TEST(ReasoningWithToolsTest, Metadata) {
    auto llm = std::make_shared<MockReasoningLLM>(true);
    patterns::ReasoningAgent agent(llm);

    auto tool = std::make_shared<MockCalculator>();
    agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Test");
    auto result = agent.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("reasoning_steps"));
    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "reasoning_with_tools");
    EXPECT_TRUE(response.metadata().contains("tool_uses"));
}

// Test: Null agent error
TEST(ReasoningWithToolsTest, NullAgentError) {
    EXPECT_THROW(
        patterns::ReasoningAgent(nullptr),
        std::invalid_argument
    );
}

// Test: Null tool error
TEST(ReasoningWithToolsTest, NullToolError) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    EXPECT_THROW(
        agent.add_tool(nullptr),
        std::invalid_argument
    );
}

// Test: Get tools
TEST(ReasoningWithToolsTest, GetTools) {
    auto llm = std::make_shared<MockReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    auto tool = std::make_shared<MockCalculator>();
    agent.add_tool(tool);

    const auto& tools = agent.get_tools();
    EXPECT_EQ(tools.size(), 1);
    EXPECT_EQ(tools[0]->name(), "calculator");
}
