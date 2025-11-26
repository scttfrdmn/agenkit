/**
 * @file test_orchestration.cpp
 * @brief Tests for Orchestration pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/orchestration.hpp"
#include <memory>
#include <set>

using namespace agenkit;

// Mock agent that returns a specific response
class MockAgent : public core::Agent {
public:
    MockAgent(std::string agent_name, std::string response_prefix)
        : agent_name_(std::move(agent_name))
        , response_prefix_(std::move(response_prefix))
        , call_count_(0)
    {}

    std::string name() const override {
        return agent_name_;
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        call_count_++;
        std::string response = response_prefix_ + ": " + message.content_as_str();
        auto msg = core::Message::with_text("assistant", response);
        msg.with_metadata("agent_name", agent_name_);
        msg.with_metadata("call_count", call_count_);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    int get_call_count() const { return call_count_; }

private:
    std::string agent_name_;
    std::string response_prefix_;
    int call_count_;
};

// Mock agent that fails
class FailingAgent : public core::Agent {
public:
    FailingAgent(std::string agent_name)
        : agent_name_(std::move(agent_name))
    {}

    std::string name() const override {
        return agent_name_;
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        auto error = core::AgentError(
            core::AgentErrorType::ProcessingError,
            agent_name_ + " failed intentionally"
        );
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(error)
        );
    }

private:
    std::string agent_name_;
};

// Test: Basic agent registration
TEST(OrchestrationTest, AgentRegistration) {
    patterns::OrchestrationAgent orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Response1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Response2");

    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("agent2", agent2);

    EXPECT_EQ(orchestrator.get_agents().size(), 2);
    EXPECT_EQ(orchestrator.get_agent("agent1"), agent1);
    EXPECT_EQ(orchestrator.get_agent("agent2"), agent2);
}

// Test: Agent removal
TEST(OrchestrationTest, AgentRemoval) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");
    orchestrator.add_agent("agent1", agent);

    EXPECT_TRUE(orchestrator.remove_agent("agent1"));
    EXPECT_FALSE(orchestrator.remove_agent("agent1")); // Already removed
    EXPECT_EQ(orchestrator.get_agents().size(), 0);
}

// Test: Sequential orchestration
TEST(OrchestrationTest, SequentialOrchestration) {
    patterns::OrchestrationAgent orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Step1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Step2");
    auto agent3 = std::make_shared<MockAgent>("agent3", "Step3");

    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("agent2", agent2);
    orchestrator.add_agent("agent3", agent3);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);

    // Set up routing: agent1 -> agent2 -> agent3 -> done
    int call_count = 0;
    orchestrator.set_routing([&call_count](const core::Message& /* msg */) -> std::string {
        call_count++;
        if (call_count == 1) return "agent1";
        if (call_count == 2) return "agent2";
        if (call_count == 3) return "agent3";
        return ""; // Done
    });

    auto msg = core::Message::with_text("user", "Test input");
    auto future = orchestrator.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = orchestrator.get_history();
    EXPECT_EQ(history.size(), 3);
    EXPECT_EQ(history[0].agent_name, "agent1");
    EXPECT_EQ(history[1].agent_name, "agent2");
    EXPECT_EQ(history[2].agent_name, "agent3");

    // Verify response contains data from agent3
    auto response = result.unwrap();
    EXPECT_TRUE(response.content_as_str().find("Step3") != std::string::npos);
}

// Test: Parallel orchestration
TEST(OrchestrationTest, ParallelOrchestration) {
    patterns::OrchestrationAgent orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Response1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Response2");
    auto agent3 = std::make_shared<MockAgent>("agent3", "Response3");

    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("agent2", agent2);
    orchestrator.add_agent("agent3", agent3);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Parallel);

    auto msg = core::Message::with_text("user", "Test input");
    auto future = orchestrator.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = orchestrator.get_history();
    EXPECT_EQ(history.size(), 3);

    // All agents should have been called (order may vary)
    std::set<std::string> called_agents;
    for (const auto& step : history) {
        called_agents.insert(step.agent_name);
    }
    EXPECT_EQ(called_agents.size(), 3);
    EXPECT_TRUE(called_agents.count("agent1") > 0);
    EXPECT_TRUE(called_agents.count("agent2") > 0);
    EXPECT_TRUE(called_agents.count("agent3") > 0);

    // Response should contain all agent responses
    auto response = result.unwrap();
    std::string content = response.content_as_str();
    EXPECT_TRUE(content.find("Response1") != std::string::npos);
    EXPECT_TRUE(content.find("Response2") != std::string::npos);
    EXPECT_TRUE(content.find("Response3") != std::string::npos);
}

// Test: Custom combiner
TEST(OrchestrationTest, CustomCombiner) {
    patterns::OrchestrationAgent orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "A");
    auto agent2 = std::make_shared<MockAgent>("agent2", "B");

    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("agent2", agent2);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Parallel);

    // Custom combiner that concatenates with " | "
    orchestrator.set_combiner([](const std::vector<core::Message>& messages) {
        std::string combined;
        for (size_t i = 0; i < messages.size(); i++) {
            if (i > 0) combined += " | ";
            combined += messages[i].content_as_str();
        }
        return core::Message::with_text("assistant", combined);
    });

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_TRUE(response.content_as_str().find("|") != std::string::npos);
}

// Test: Error handling - no agents
TEST(OrchestrationTest, NoAgentsError) {
    patterns::OrchestrationAgent orchestrator;

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), core::AgentErrorType::InvalidInput);
}

// Test: Error handling - no routing function
TEST(OrchestrationTest, NoRoutingFunctionError) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");
    orchestrator.add_agent("agent1", agent);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);
    // Don't set routing function

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
}

// Test: Error handling - agent not found
TEST(OrchestrationTest, AgentNotFoundError) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");
    orchestrator.add_agent("agent1", agent);

    // Enable stop_on_error to propagate NotFound errors
    patterns::OrchestrationConfig config;
    config.stop_on_error = true;
    orchestrator.set_config(config);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);
    orchestrator.set_routing([](const core::Message& /* msg */) {
        return "nonexistent_agent";
    });

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), core::AgentErrorType::NotFound);
}

// Test: Stop on error
TEST(OrchestrationTest, StopOnError) {
    patterns::OrchestrationAgent orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Response1");
    auto failing = std::make_shared<FailingAgent>("failing");
    auto agent3 = std::make_shared<MockAgent>("agent3", "Response3");

    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("failing", failing);
    orchestrator.add_agent("agent3", agent3);

    patterns::OrchestrationConfig config;
    config.stop_on_error = true;
    orchestrator.set_config(config);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Parallel);

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
}

// Test: Continue on error
TEST(OrchestrationTest, ContinueOnError) {
    patterns::OrchestrationAgent orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Response1");
    auto failing = std::make_shared<FailingAgent>("failing");

    orchestrator.add_agent("agent1", agent1);
    orchestrator.add_agent("failing", failing);

    patterns::OrchestrationConfig config;
    config.stop_on_error = false;
    orchestrator.set_config(config);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Parallel);

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    // Check that both were called
    const auto& history = orchestrator.get_history();
    EXPECT_EQ(history.size(), 2);

    // One should have failed
    int failures = 0;
    for (const auto& step : history) {
        if (!step.success) failures++;
    }
    EXPECT_EQ(failures, 1);
}

// Test: Max steps limit
TEST(OrchestrationTest, MaxStepsLimit) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");
    orchestrator.add_agent("agent1", agent);

    patterns::OrchestrationConfig config;
    config.max_steps = 3;
    orchestrator.set_config(config);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);

    // Router that never returns empty (would loop forever)
    orchestrator.set_routing([](const core::Message& /* msg */) {
        return "agent1";
    });

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    const auto& history = orchestrator.get_history();
    EXPECT_EQ(history.size(), 3); // Limited by max_steps
}

// Test: Get/set configuration
TEST(OrchestrationTest, GetSetConfig) {
    patterns::OrchestrationAgent orchestrator;

    patterns::OrchestrationConfig config;
    config.max_steps = 20;
    config.stop_on_error = true;

    orchestrator.set_config(config);

    auto retrieved = orchestrator.get_config();
    EXPECT_EQ(retrieved.max_steps, 20);
    EXPECT_TRUE(retrieved.stop_on_error);
}

// Test: Clear history
TEST(OrchestrationTest, ClearHistory) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");
    orchestrator.add_agent("agent1", agent);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);
    orchestrator.set_routing([](const core::Message& /* msg */) {
        static int count = 0;
        return (++count == 1) ? "agent1" : "";
    });

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    EXPECT_GT(orchestrator.get_history().size(), 0);

    orchestrator.clear_history();
    EXPECT_EQ(orchestrator.get_history().size(), 0);
}

// Test: Capabilities
TEST(OrchestrationTest, Capabilities) {
    patterns::OrchestrationAgent orchestrator;

    auto caps = orchestrator.capabilities();
    EXPECT_EQ(caps.size(), 3);
    EXPECT_EQ(caps[0], "orchestration");
    EXPECT_EQ(caps[1], "coordination");
    EXPECT_EQ(caps[2], "multi-agent");
}

// Test: Name
TEST(OrchestrationTest, Name) {
    patterns::OrchestrationAgent orchestrator;
    EXPECT_EQ(orchestrator.name(), "orchestration");
}

// Test: Metadata in response
TEST(OrchestrationTest, ResponseMetadata) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");
    orchestrator.add_agent("agent1", agent);

    orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);
    orchestrator.set_routing([](const core::Message& /* msg */) {
        static int count = 0;
        return (++count == 1) ? "agent1" : "";
    });

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("orchestration_steps"));
    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "orchestration");
    EXPECT_TRUE(response.metadata().contains("invoked_agents"));
}

// Test: Validation - null agent
TEST(OrchestrationTest, NullAgentValidation) {
    patterns::OrchestrationAgent orchestrator;

    EXPECT_THROW(
        orchestrator.add_agent("agent1", nullptr),
        std::invalid_argument
    );
}

// Test: Validation - empty name
TEST(OrchestrationTest, EmptyNameValidation) {
    patterns::OrchestrationAgent orchestrator;

    auto agent = std::make_shared<MockAgent>("agent1", "Response");

    EXPECT_THROW(
        orchestrator.add_agent("", agent),
        std::invalid_argument
    );
}
