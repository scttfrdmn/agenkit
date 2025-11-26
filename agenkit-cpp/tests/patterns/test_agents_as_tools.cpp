/**
 * @file test_agents_as_tools.cpp
 * @brief Tests for Agents-as-Tools pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/agents_as_tools.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <memory>
#include <thread>
#include <chrono>

using namespace agenkit;

// Mock agent that returns a specific response
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
        response.with_metadata("test_key", "test_value");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(response)
        );
    }

private:
    std::string response_text_;
};

// Mock agent that sleeps for a duration
class SlowAgent : public core::Agent {
public:
    SlowAgent(std::chrono::milliseconds delay)
        : delay_(delay)
    {}

    std::string name() const override {
        return "slow_agent";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        return std::async(std::launch::async, [this]() {
            std::this_thread::sleep_for(delay_);
            auto response = core::Message::with_text("assistant", "Slow response");
            return core::Result<core::Message, core::AgentError>::ok(response);
        });
    }

private:
    std::chrono::milliseconds delay_;
};

// Mock agent that returns an error
class FailingAgent : public core::Agent {
public:
    std::string name() const override {
        return "failing_agent";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto error = core::AgentError(
            core::AgentErrorType::ProcessingError,
            "Intentional test failure"
        );
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(error)
        );
    }
};

// Test: Basic agent tool creation and execution
TEST(AgentsAsToolsTest, BasicExecution) {
    auto agent = std::make_shared<MockResponseAgent>("Test response");
    patterns::AgentTool tool(agent, "test_tool", "A test tool");

    EXPECT_EQ(tool.name(), "test_tool");
    EXPECT_EQ(tool.description(), "A test tool");

    auto result = tool.execute("Test input");

    EXPECT_TRUE(result.success);
    EXPECT_EQ(result.content, "Test response");
}

// Test: Metadata propagation
TEST(AgentsAsToolsTest, MetadataPropagation) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    patterns::AgentToolConfig config;
    config.propagate_metadata = true;

    patterns::AgentTool tool(agent, "test", "Test", config);

    auto result = tool.execute("Input");

    EXPECT_TRUE(result.success);
    EXPECT_TRUE(result.metadata.contains("test_key"));
    EXPECT_EQ(result.metadata["test_key"], "test_value");
}

// Test: Metadata propagation disabled
TEST(AgentsAsToolsTest, MetadataPropagationDisabled) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    patterns::AgentToolConfig config;
    config.propagate_metadata = false;

    patterns::AgentTool tool(agent, "test", "Test", config);

    auto result = tool.execute("Input");

    EXPECT_TRUE(result.success);
    EXPECT_FALSE(result.metadata.contains("test_key"));
    EXPECT_TRUE(result.metadata.contains("agent_name"));  // Always included
}

// Test: Execution timing
TEST(AgentsAsToolsTest, ExecutionTiming) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    patterns::AgentToolConfig config;
    config.include_timing = true;

    patterns::AgentTool tool(agent, "test", "Test", config);

    auto result = tool.execute("Input");

    EXPECT_TRUE(result.success);
    EXPECT_TRUE(result.metadata.contains("execution_time_ms"));
    EXPECT_TRUE(result.metadata.contains("timed_out"));
    EXPECT_FALSE(result.metadata["timed_out"]);
}

// Test: Timeout handling
TEST(AgentsAsToolsTest, TimeoutHandling) {
    auto agent = std::make_shared<SlowAgent>(std::chrono::milliseconds(200));

    patterns::AgentToolConfig config;
    config.timeout = std::chrono::milliseconds(50);
    config.include_timing = true;

    patterns::AgentTool tool(agent, "slow", "Slow tool", config);

    auto result = tool.execute("Input");

    EXPECT_FALSE(result.success);
    EXPECT_TRUE(result.content.find("timed out") != std::string::npos);
    EXPECT_TRUE(result.metadata.contains("timed_out"));
    EXPECT_TRUE(result.metadata["timed_out"]);
}

// Test: Error handling
TEST(AgentsAsToolsTest, ErrorHandling) {
    auto agent = std::make_shared<FailingAgent>();

    patterns::AgentTool tool(agent, "failing", "Failing tool");

    auto result = tool.execute("Input");

    EXPECT_FALSE(result.success);
    EXPECT_TRUE(result.content.find("Agent error") != std::string::npos);
    EXPECT_TRUE(result.content.find("Intentional test failure") != std::string::npos);
    EXPECT_TRUE(result.metadata.contains("error_type"));
    EXPECT_TRUE(result.metadata.contains("error_message"));
}

// Test: Get agent
TEST(AgentsAsToolsTest, GetAgent) {
    auto agent = std::make_shared<MockResponseAgent>("Response");
    patterns::AgentTool tool(agent, "test", "Test");

    auto retrieved_agent = tool.get_agent();
    EXPECT_EQ(retrieved_agent, agent);
    EXPECT_EQ(retrieved_agent->name(), "mock_response");
}

// Test: Get/set config
TEST(AgentsAsToolsTest, GetSetConfig) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    patterns::AgentToolConfig initial_config;
    initial_config.timeout = std::chrono::milliseconds(100);

    patterns::AgentTool tool(agent, "test", "Test", initial_config);

    auto config = tool.get_config();
    EXPECT_EQ(config.timeout.count(), 100);

    patterns::AgentToolConfig new_config;
    new_config.timeout = std::chrono::milliseconds(200);
    new_config.include_timing = true;

    tool.set_config(new_config);

    auto updated_config = tool.get_config();
    EXPECT_EQ(updated_config.timeout.count(), 200);
    EXPECT_TRUE(updated_config.include_timing);
}

// Test: Custom message role
TEST(AgentsAsToolsTest, CustomMessageRole) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    patterns::AgentToolConfig config;
    config.message_role = "system";

    patterns::AgentTool tool(agent, "test", "Test", config);

    auto result = tool.execute("Input");
    EXPECT_TRUE(result.success);
}

// Test: Error handling - null agent
TEST(AgentsAsToolsTest, NullAgentError) {
    EXPECT_THROW(
        patterns::AgentTool(nullptr, "test", "Test"),
        std::invalid_argument
    );
}

// Test: Error handling - empty tool name
TEST(AgentsAsToolsTest, EmptyToolNameError) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    EXPECT_THROW(
        patterns::AgentTool(agent, "", "Test"),
        std::invalid_argument
    );
}

// Test: Error handling - empty description
TEST(AgentsAsToolsTest, EmptyDescriptionError) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    EXPECT_THROW(
        patterns::AgentTool(agent, "test", ""),
        std::invalid_argument
    );
}

// Test: Builder pattern - basic
TEST(AgentsAsToolsTest, BuilderBasic) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    auto tool = patterns::AgentToolBuilder(agent, "test", "Test tool")
        .build();

    EXPECT_EQ(tool->name(), "test");
    EXPECT_EQ(tool->description(), "Test tool");

    auto result = tool->execute("Input");
    EXPECT_TRUE(result.success);
}

// Test: Builder pattern - with timeout
TEST(AgentsAsToolsTest, BuilderWithTimeout) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    auto tool = patterns::AgentToolBuilder(agent, "test", "Test")
        .with_timeout(std::chrono::milliseconds(100))
        .build();

    EXPECT_EQ(tool->get_config().timeout.count(), 100);
}

// Test: Builder pattern - with timing
TEST(AgentsAsToolsTest, BuilderWithTiming) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    auto tool = patterns::AgentToolBuilder(agent, "test", "Test")
        .with_timing()
        .build();

    EXPECT_TRUE(tool->get_config().include_timing);

    auto result = tool->execute("Input");
    EXPECT_TRUE(result.metadata.contains("execution_time_ms"));
}

// Test: Builder pattern - full configuration
TEST(AgentsAsToolsTest, BuilderFullConfig) {
    auto agent = std::make_shared<MockResponseAgent>("Response");

    auto tool = patterns::AgentToolBuilder(agent, "test", "Test tool")
        .with_timeout(std::chrono::seconds(5))
        .with_metadata_propagation(false)
        .with_timing(true)
        .with_message_role("system")
        .build();

    auto config = tool->get_config();
    EXPECT_EQ(config.timeout.count(), 5000);
    EXPECT_FALSE(config.propagate_metadata);
    EXPECT_TRUE(config.include_timing);
    EXPECT_EQ(config.message_role, "system");
}

// Test: Integration with ReAct pattern
TEST(AgentsAsToolsTest, ReactIntegration) {
    // Create a simple agent to wrap
    auto calculator_agent = std::make_shared<MockResponseAgent>("42");

    // Wrap as tool
    auto calculator_tool = std::make_shared<patterns::AgentTool>(
        calculator_agent,
        "calculator",
        "Performs calculations"
    );

    // Create a mock ReAct agent that returns final answer after first observation
    class SimpleReActAgent : public core::Agent {
    public:
        std::string name() const override { return "simple_react"; }
        std::future<core::Result<core::Message, core::AgentError>>
        process(core::Message message) override {
            std::string content = message.content_as_str();
            std::string response;

            if (content.find("Observation:") != std::string::npos) {
                // We got an observation, provide final answer
                response = "Final Answer: The calculator returned 42";
            } else {
                // First call, request calculation
                response = "Thought: I need to calculate\n";
                response += "Action: calculator: 2 + 2";
            }

            auto msg = core::Message::with_text("assistant", response);
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::ok(msg)
            );
        }
    };

    auto react_llm = std::make_shared<SimpleReActAgent>();
    patterns::ReactAgent react_agent(react_llm, 5);
    react_agent.add_tool(calculator_tool);

    auto msg = core::Message::with_text("user", "What is 2 + 2?");
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    // Verify the calculator agent was called via tool
    const auto& history = react_agent.get_history();
    ASSERT_EQ(history.size(), 1);
    EXPECT_EQ(history[0].tool_name, "calculator");
    EXPECT_EQ(history[0].observation, "42");
}
