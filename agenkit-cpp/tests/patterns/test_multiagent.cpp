/**
 * @file test_multiagent.cpp
 * @brief Tests for Multiagent pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/multiagent.hpp"
#include <memory>

using namespace agenkit;

// Mock agent for testing
class MockAgent : public core::Agent {
private:
    std::string name_;
    std::string response_;
    bool should_fail_;

public:
    MockAgent(
        const std::string& name,
        const std::string& response = "Response",
        bool should_fail = false
    ) : name_(name), response_(response), should_fail_(should_fail) {}

    std::string name() const override { return name_; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message /* message */) override {
        if (should_fail_) {
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(core::AgentErrorType::Internal, "Mock failure")
                )
            );
        }

        auto msg = core::Message::with_text("assistant", response_);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Test: Basic orchestration
TEST(MultiAgentTest, BasicOrchestration) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Response 1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Response 2");

    orchestrator.register_agent("agent1", agent1);
    orchestrator.register_agent("agent2", agent2);

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("agent1: Response 1") != std::string::npos);
    EXPECT_TRUE(response.content_as_str().find("agent2: Response 2") != std::string::npos);
}

// Test: Register and unregister agents
TEST(MultiAgentTest, RegisterUnregister) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent = std::make_shared<MockAgent>("test", "Response");

    orchestrator.register_agent("test", agent);
    EXPECT_EQ(orchestrator.list_agents().size(), 1);

    orchestrator.unregister_agent("test");
    EXPECT_EQ(orchestrator.list_agents().size(), 0);
}

// Test: List agents
TEST(MultiAgentTest, ListAgents) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1");
    auto agent2 = std::make_shared<MockAgent>("agent2");
    auto agent3 = std::make_shared<MockAgent>("agent3");

    orchestrator.register_agent("agent1", agent1);
    orchestrator.register_agent("agent2", agent2);
    orchestrator.register_agent("agent3", agent3);

    auto agents = orchestrator.list_agents();
    EXPECT_EQ(agents.size(), 3);
}

// Test: Task tracking
TEST(MultiAgentTest, TaskTracking) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Response 1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Response 2");

    orchestrator.register_agent("agent1", agent1);
    orchestrator.register_agent("agent2", agent2);

    auto msg = core::Message::with_text("user", "Test");
    orchestrator.process(std::move(msg)).get();

    auto tasks = orchestrator.get_tasks();
    EXPECT_EQ(tasks.size(), 2);

    EXPECT_EQ(tasks[0].agent_name, "agent1");
    EXPECT_EQ(tasks[0].status, patterns::TaskStatus::Completed);
    EXPECT_TRUE(tasks[0].result.has_value());

    EXPECT_EQ(tasks[1].agent_name, "agent2");
    EXPECT_EQ(tasks[1].status, patterns::TaskStatus::Completed);
}

// Test: Clear tasks
TEST(MultiAgentTest, ClearTasks) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent = std::make_shared<MockAgent>("agent", "Response");
    orchestrator.register_agent("agent", agent);

    auto msg = core::Message::with_text("user", "Test");
    orchestrator.process(std::move(msg)).get();

    EXPECT_GT(orchestrator.get_tasks().size(), 0);

    orchestrator.clear_tasks();
    EXPECT_EQ(orchestrator.get_tasks().size(), 0);
}

// Test: Agent failure handling
TEST(MultiAgentTest, AgentFailure) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Success");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Fail", true);

    orchestrator.register_agent("agent1", agent1);
    orchestrator.register_agent("agent2", agent2);

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    auto tasks = orchestrator.get_tasks();
    EXPECT_EQ(tasks[0].status, patterns::TaskStatus::Completed);
    EXPECT_EQ(tasks[1].status, patterns::TaskStatus::Failed);
    EXPECT_TRUE(tasks[1].error.has_value());
}

// Test: Set and get strategy
TEST(MultiAgentTest, SetGetStrategy) {
    patterns::MultiAgentOrchestrator orchestrator;

    EXPECT_EQ(orchestrator.get_strategy(), patterns::MultiAgentStrategy::Sequential);

    orchestrator.set_strategy(patterns::MultiAgentStrategy::Parallel);
    EXPECT_EQ(orchestrator.get_strategy(), patterns::MultiAgentStrategy::Parallel);
}

// Test: Capabilities
TEST(MultiAgentTest, Capabilities) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto caps = orchestrator.capabilities();
    EXPECT_EQ(caps.size(), 4);
    EXPECT_EQ(caps[0], "orchestration");
    EXPECT_EQ(caps[1], "multi-agent");
    EXPECT_EQ(caps[2], "coordination");
    EXPECT_EQ(caps[3], "delegation");
}

// Test: Name
TEST(MultiAgentTest, Name) {
    patterns::MultiAgentOrchestrator orchestrator;
    EXPECT_EQ(orchestrator.name(), "multiagent_orchestrator");
}

// Test: Metadata
TEST(MultiAgentTest, Metadata) {
    patterns::MultiAgentOrchestrator orchestrator;

    auto agent = std::make_shared<MockAgent>("agent", "Response");
    orchestrator.register_agent("agent", agent);

    auto msg = core::Message::with_text("user", "Test");
    auto result = orchestrator.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "multiagent");
    EXPECT_TRUE(response.metadata().contains("agent_count"));
    EXPECT_TRUE(response.metadata().contains("tasks_completed"));
}

// ConsensusAgent Tests

// Test: Basic consensus
TEST(ConsensusAgentTest, BasicConsensus) {
    patterns::ConsensusAgent consensus;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Opinion 1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Opinion 2");
    auto agent3 = std::make_shared<MockAgent>("agent3", "Opinion 3");

    consensus.add_agent(agent1);
    consensus.add_agent(agent2);
    consensus.add_agent(agent3);

    auto msg = core::Message::with_text("user", "What do you think?");
    auto result = consensus.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("Opinion 1") != std::string::npos);
    EXPECT_TRUE(response.content_as_str().find("Opinion 2") != std::string::npos);
    EXPECT_TRUE(response.content_as_str().find("Opinion 3") != std::string::npos);
    EXPECT_TRUE(response.content_as_str().find("Consensus from 3 agents") != std::string::npos);
}

// Test: Agent count
TEST(ConsensusAgentTest, AgentCount) {
    patterns::ConsensusAgent consensus;

    EXPECT_EQ(consensus.agent_count(), 0);

    auto agent1 = std::make_shared<MockAgent>("agent1");
    auto agent2 = std::make_shared<MockAgent>("agent2");

    consensus.add_agent(agent1);
    EXPECT_EQ(consensus.agent_count(), 1);

    consensus.add_agent(agent2);
    EXPECT_EQ(consensus.agent_count(), 2);
}

// Test: Clear agents
TEST(ConsensusAgentTest, ClearAgents) {
    patterns::ConsensusAgent consensus;

    auto agent = std::make_shared<MockAgent>("agent");
    consensus.add_agent(agent);

    EXPECT_EQ(consensus.agent_count(), 1);

    consensus.clear_agents();
    EXPECT_EQ(consensus.agent_count(), 0);
}

// Test: Consensus with failures
TEST(ConsensusAgentTest, ConsensusWithFailures) {
    patterns::ConsensusAgent consensus;

    auto agent1 = std::make_shared<MockAgent>("agent1", "Opinion 1");
    auto agent2 = std::make_shared<MockAgent>("agent2", "Fail", true);

    consensus.add_agent(agent1);
    consensus.add_agent(agent2);

    auto msg = core::Message::with_text("user", "Test");
    auto result = consensus.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.content_as_str().find("Opinion 1") != std::string::npos);
    EXPECT_TRUE(response.content_as_str().find("Error:") != std::string::npos);
}

// Test: Consensus capabilities
TEST(ConsensusAgentTest, Capabilities) {
    patterns::ConsensusAgent consensus;

    auto caps = consensus.capabilities();
    EXPECT_EQ(caps.size(), 3);
    EXPECT_EQ(caps[0], "consensus");
    EXPECT_EQ(caps[1], "multi-perspective");
    EXPECT_EQ(caps[2], "aggregation");
}

// Test: Consensus name
TEST(ConsensusAgentTest, Name) {
    patterns::ConsensusAgent consensus;
    EXPECT_EQ(consensus.name(), "consensus");
}

// Test: Consensus metadata
TEST(ConsensusAgentTest, Metadata) {
    patterns::ConsensusAgent consensus;

    auto agent = std::make_shared<MockAgent>("agent", "Opinion");
    consensus.add_agent(agent);

    auto msg = core::Message::with_text("user", "Test");
    auto result = consensus.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_TRUE(response.metadata().contains("pattern"));
    EXPECT_EQ(response.metadata()["pattern"], "consensus");
    EXPECT_TRUE(response.metadata().contains("agent_count"));
}
