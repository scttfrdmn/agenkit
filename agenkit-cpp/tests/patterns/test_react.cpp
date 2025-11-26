/**
 * @file test_react.cpp
 * @brief Tests for ReAct pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/react.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <memory>

using namespace agenkit;

// Mock tool that always succeeds
class MockCalculatorTool : public patterns::Tool {
public:
    std::string name() const override {
        return "calculator";
    }

    std::string description() const override {
        return "Performs mathematical calculations";
    }

    patterns::ToolResult execute(const std::string& input) override {
        // Simple mock: just echo the input with "= 42"
        return patterns::ToolResult::ok(input + " = 42");
    }
};

// Mock tool that always fails
class MockFailingTool : public patterns::Tool {
public:
    std::string name() const override {
        return "failing_tool";
    }

    std::string description() const override {
        return "A tool that always fails";
    }

    patterns::ToolResult execute(const std::string& /* input */) override {
        return patterns::ToolResult::error("Tool execution failed");
    }
};

// Mock agent that returns ReAct-formatted responses
class MockReActAgent : public core::Agent {
public:
    MockReActAgent(int steps_before_answer = 1)
        : steps_before_answer_(steps_before_answer)
        , call_count_(0)
    {}

    std::string name() const override {
        return "mock_react";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        call_count_++;

        std::string response;
        if (call_count_ >= steps_before_answer_) {
            // Return final answer
            response = "Final Answer: The answer is 42";
        } else {
            // Return thought + action
            response = "Thought: I need to use the calculator\n";
            response += "Action: calculator: 40 + 2";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    int get_call_count() const { return call_count_; }

private:
    int steps_before_answer_;
    int call_count_;
};

// Test: Basic ReAct loop with single step
TEST(ReactTest, SingleStepReAct) {
    auto agent = std::make_shared<MockReActAgent>(1);
    auto tool = std::make_shared<MockCalculatorTool>();

    patterns::ReactAgent react_agent(agent, 5);
    react_agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "What is 40 + 2?");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.content_as_str(), "The answer is 42");
    EXPECT_TRUE(response.metadata().contains("react_steps"));
}

// Test: Multi-step ReAct loop
TEST(ReactTest, MultiStepReAct) {
    auto agent = std::make_shared<MockReActAgent>(3);
    auto tool = std::make_shared<MockCalculatorTool>();

    patterns::ReactAgent react_agent(agent, 10);
    react_agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Complex calculation");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = react_agent.get_history();
    EXPECT_EQ(history.size(), 2); // 2 steps before final answer

    // Check metadata
    auto response = result.unwrap();
    EXPECT_EQ(response.metadata()["react_steps"], 2);
}

// Test: Max steps limit
TEST(ReactTest, MaxStepsLimit) {
    // Agent that never gives final answer
    auto agent = std::make_shared<MockReActAgent>(100);
    auto tool = std::make_shared<MockCalculatorTool>();

    patterns::ReactAgent react_agent(agent, 3);
    react_agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Question");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = react_agent.get_history();
    EXPECT_EQ(history.size(), 3); // Hit max steps

    auto response = result.unwrap();
    EXPECT_TRUE(response.content_as_str().find("maximum steps") != std::string::npos);
}

// Test: Tool execution failure
TEST(ReactTest, ToolExecutionFailure) {
    // Create mock agent that uses the failing tool
    class FailingToolAgent : public core::Agent {
    public:
        std::string name() const override { return "failing_tool_agent"; }
        std::future<core::Result<core::Message, core::AgentError>>
        process(core::Message /* message */) override {
            std::string response = "Thought: I need to use the failing tool\n";
            response += "Action: failing_tool: test input";
            auto msg = core::Message::with_text("assistant", response);
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(msg)
            );
        }
    };

    auto agent = std::make_shared<FailingToolAgent>();
    auto tool = std::make_shared<MockFailingTool>();

    patterns::ReactAgent react_agent(agent, 5);
    react_agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Test");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = react_agent.get_history();
    ASSERT_GT(history.size(), 0);

    // Check that tool execution was recorded as failed
    EXPECT_FALSE(history[0].success);
    EXPECT_TRUE(history[0].observation.find("failed") != std::string::npos);
}

// Test: No tools available
TEST(ReactTest, NoToolsError) {
    auto agent = std::make_shared<MockReActAgent>(1);

    patterns::ReactAgent react_agent(agent, 5);
    // Don't add any tools

    auto msg = core::Message::with_text("user", "Test");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), core::AgentErrorType::InvalidInput);
}

// Test: Error handling - null agent
TEST(ReactTest, NullAgentError) {
    EXPECT_THROW(
        patterns::ReactAgent(nullptr, 5),
        std::invalid_argument
    );
}

// Test: Error handling - invalid max_steps
TEST(ReactTest, InvalidMaxSteps) {
    auto agent = std::make_shared<MockReActAgent>(1);

    EXPECT_THROW(
        patterns::ReactAgent(agent, 0),
        std::invalid_argument
    );

    EXPECT_THROW(
        patterns::ReactAgent(agent, -1),
        std::invalid_argument
    );
}

// Test: Error handling - null tool
TEST(ReactTest, NullToolError) {
    auto agent = std::make_shared<MockReActAgent>(1);
    patterns::ReactAgent react_agent(agent, 5);

    EXPECT_THROW(
        react_agent.add_tool(nullptr),
        std::invalid_argument
    );
}

// Test: Agent capabilities
TEST(ReactTest, Capabilities) {
    auto agent = std::make_shared<MockReActAgent>(1);
    patterns::ReactAgent react_agent(agent, 5);

    auto caps = react_agent.capabilities();
    EXPECT_EQ(caps.size(), 3);
    EXPECT_EQ(caps[0], "react");
    EXPECT_EQ(caps[1], "reasoning");
    EXPECT_EQ(caps[2], "tool-use");
}

// Test: Name
TEST(ReactTest, Name) {
    auto agent = std::make_shared<MockReActAgent>(1);
    patterns::ReactAgent react_agent(agent, 5);

    EXPECT_EQ(react_agent.name(), "react");
}

// Test: Get tools
TEST(ReactTest, GetTools) {
    auto agent = std::make_shared<MockReActAgent>(1);
    auto tool1 = std::make_shared<MockCalculatorTool>();
    auto tool2 = std::make_shared<MockFailingTool>();

    patterns::ReactAgent react_agent(agent, 5);
    react_agent.add_tool(tool1);
    react_agent.add_tool(tool2);

    const auto& tools = react_agent.get_tools();
    EXPECT_EQ(tools.size(), 2);
    EXPECT_EQ(tools[0]->name(), "calculator");
    EXPECT_EQ(tools[1]->name(), "failing_tool");
}

// Test: Clear history
TEST(ReactTest, ClearHistory) {
    auto agent = std::make_shared<MockReActAgent>(3);  // Takes 3 calls before answer
    auto tool = std::make_shared<MockCalculatorTool>();

    patterns::ReactAgent react_agent(agent, 5);
    react_agent.add_tool(tool);

    // First process - will have 2 steps (calls 1 and 2)
    auto msg1 = core::Message::with_text("user", "Test 1");
    auto future1 = react_agent.process(std::move(msg1));
    auto result1 = future1.get();

    size_t first_history_size = react_agent.get_history().size();
    EXPECT_GT(first_history_size, 0);

    // Clear history
    react_agent.clear_history();
    EXPECT_EQ(react_agent.get_history().size(), 0);

    // Second process should start fresh (call count resets, but agent doesn't reset)
    // So this will continue from call 3 and immediately return final answer
    // Therefore, we just need to verify history was cleared
    auto msg2 = core::Message::with_text("user", "Test 2");
    auto future2 = react_agent.process(std::move(msg2));
    auto result2 = future2.get();

    // History should be independent of first run
    // (it might be 0 if final answer on first call, or >0 if there were steps)
    EXPECT_TRUE(result2.is_ok());
}

// Test: Metadata preservation
TEST(ReactTest, MetadataPreservation) {
    auto agent = std::make_shared<MockReActAgent>(1);
    auto tool = std::make_shared<MockCalculatorTool>();

    patterns::ReactAgent react_agent(agent, 5);
    react_agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Test");
    msg.with_metadata("custom_key", "custom_value");

    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Check that original metadata is preserved
    EXPECT_TRUE(response.metadata().contains("custom_key"));
    EXPECT_EQ(response.metadata()["custom_key"], "custom_value");

    // Check that ReAct metadata was added
    EXPECT_TRUE(response.metadata().contains("react_steps"));
    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "react");
}

// Test: ReAct history structure
TEST(ReactTest, HistoryStructure) {
    auto agent = std::make_shared<MockReActAgent>(2);
    auto tool = std::make_shared<MockCalculatorTool>();

    patterns::ReactAgent react_agent(agent, 5);
    react_agent.add_tool(tool);

    auto msg = core::Message::with_text("user", "Calculate something");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = react_agent.get_history();
    ASSERT_EQ(history.size(), 1);

    const auto& step = history[0];
    EXPECT_EQ(step.step, 1);
    EXPECT_FALSE(step.thought.empty());
    EXPECT_FALSE(step.action.empty());
    EXPECT_EQ(step.tool_name, "calculator");
    EXPECT_FALSE(step.observation.empty());
    EXPECT_TRUE(step.success);
}
