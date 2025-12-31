/**
 * @file test_collaborative.cpp
 * @brief Comprehensive tests for Collaborative pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/collaborative.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>
#include <set>

using namespace agenkit;
using namespace agenkit::test;

// Test: Valid construction
TEST(CollaborativeAgentTest, Constructor) {
    auto agent1 = make_mock_agent("agent1", "r1");
    auto agent2 = make_mock_agent("agent2", "r2");

    auto merge = [](const std::vector<core::Message>& messages) {
        return messages[0];
    };

    patterns::CollaborativeConfig config{
        {agent1, agent2},  // agents
        3,                 // max_rounds
        nullptr,           // consensus_func
        merge              // merge_func
    };

    patterns::CollaborativeAgent collab(config);

    EXPECT_EQ(collab.name(), "collaborative");
}

// Test: Constructor with empty agents
TEST(CollaborativeAgentTest, ConstructorEmptyAgents) {
    auto merge = [](const std::vector<core::Message>& messages) {
        return messages[0];
    };

    patterns::CollaborativeConfig config{
        {},       // empty agents
        3,
        nullptr,
        merge
    };

    EXPECT_THROW(
        {
            patterns::CollaborativeAgent collab(config);
        },
        std::invalid_argument
    );
}

// Test: Constructor with null merge function
TEST(CollaborativeAgentTest, ConstructorNullMergeFunc) {
    auto agent = make_mock_agent("agent1");

    patterns::CollaborativeConfig config{
        {agent},
        3,
        nullptr,
        nullptr  // null merge function
    };

    EXPECT_THROW(
        {
            patterns::CollaborativeAgent collab(config);
        },
        std::invalid_argument
    );
}

// Test: Basic collaborative processing
TEST(CollaborativeAgentTest, BasicProcess) {
    auto agent1 = make_mock_agent("agent1", "response1");
    auto agent2 = make_mock_agent("agent2", "response2");
    auto agent3 = make_mock_agent("agent3", "response3");

    auto merge = patterns::default_merge::last;

    patterns::CollaborativeConfig config{
        {agent1, agent2, agent3},
        1,  // Single round
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test input");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should return last response
    std::string content = response.content_as_str();
    bool valid = (content == "response1" || content == "response2" || content == "response3");
    EXPECT_TRUE(valid);
}

// Test: Multi-round iteration
TEST(CollaborativeAgentTest, MultiRoundIteration) {
    auto agent1 = make_mock_agent("agent1", "r1");
    auto agent2 = make_mock_agent("agent2", "r2");

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        3,  // 3 rounds
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Both agents should have been called 3 times (one per round)
    EXPECT_EQ(agent1->call_count(), 3);
    EXPECT_EQ(agent2->call_count(), 3);

    // Check metadata
    auto metadata = response.metadata();
    expect_metadata_exists(response, "collaborative_rounds");
    expect_metadata_value<int>(response, "collaborative_rounds", 3);
}

// Test: Early consensus termination
TEST(CollaborativeAgentTest, EarlyConsensus) {
    auto agent1 = make_mock_agent("agent1", "agreed");
    auto agent2 = make_mock_agent("agent2", "agreed");

    auto consensus = patterns::default_consensus::exact_match;
    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        5,  // Max 5 rounds
        consensus,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should terminate early due to consensus
    EXPECT_LT(agent1->call_count(), 5);

    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("consensus"));
    EXPECT_TRUE(metadata["consensus"].get<bool>());
}

// Test: No consensus - max rounds reached
TEST(CollaborativeAgentTest, NoConsensusMaxRounds) {
    auto agent1 = make_mock_agent("agent1", "response1");
    auto agent2 = make_mock_agent("agent2", "response2");

    auto consensus = patterns::default_consensus::exact_match;
    auto merge = patterns::default_merge::vote;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        3,
        consensus,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should reach max rounds
    EXPECT_EQ(agent1->call_count(), 3);
    EXPECT_EQ(agent2->call_count(), 3);

    auto metadata = response.metadata();
    expect_metadata_value<int>(response, "collaborative_rounds", 3);
    EXPECT_FALSE(metadata["consensus"].get<bool>());
}

// Test: Metadata tracking
TEST(CollaborativeAgentTest, Metadata) {
    auto agent1 = make_mock_agent("agent1", "r1");
    auto agent2 = make_mock_agent("agent2", "r2");

    auto merge = patterns::default_merge::concatenate;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        2,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    expect_metadata_exists(response, "collaborative_agents");
    expect_metadata_value<int>(response, "collaborative_agents", 2);

    expect_metadata_exists(response, "collaborative_rounds");
    expect_metadata_value<int>(response, "collaborative_rounds", 2);

    expect_metadata_exists(response, "consensus");
}

// Test: Agent error handling
TEST(CollaborativeAgentTest, AgentError) {
    auto agent1 = make_mock_agent("agent1", "success");
    auto agent2 = make_failing_mock_agent("agent2", "agent2 failed");

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        2,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("agent2 failed") != std::string::npos);
}

// Test: Default merge - concatenate
TEST(CollaborativeAgentTest, DefaultMergeConcatenate) {
    auto agent1 = make_mock_agent("agent1", "A");
    auto agent2 = make_mock_agent("agent2", "B");
    auto agent3 = make_mock_agent("agent3", "C");

    patterns::CollaborativeConfig config{
        {agent1, agent2, agent3},
        1,
        nullptr,
        patterns::default_merge::concatenate
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    std::string content = response.content_as_str();

    // Should contain all responses
    EXPECT_TRUE(content.find("A") != std::string::npos);
    EXPECT_TRUE(content.find("B") != std::string::npos);
    EXPECT_TRUE(content.find("C") != std::string::npos);
}

// Test: Default merge - vote
TEST(CollaborativeAgentTest, DefaultMergeVote) {
    auto agent1 = make_mock_agent("agent1", "answer_A");
    auto agent2 = make_mock_agent("agent2", "answer_A");
    auto agent3 = make_mock_agent("agent3", "answer_B");

    patterns::CollaborativeConfig config{
        {agent1, agent2, agent3},
        1,
        nullptr,
        patterns::default_merge::vote
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Majority should win
    EXPECT_EQ(response.content_as_str(), "answer_A");

    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("votes"));
}

// Test: Default consensus - exact match
TEST(CollaborativeAgentTest, DefaultConsensusExactMatch) {
    auto agent1 = make_mock_agent("agent1", "same");
    auto agent2 = make_mock_agent("agent2", "same");
    auto agent3 = make_mock_agent("agent3", "same");

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2, agent3},
        5,
        patterns::default_consensus::exact_match,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should reach consensus quickly
    EXPECT_LT(agent1->call_count(), 5);

    auto metadata = response.metadata();
    EXPECT_TRUE(metadata["consensus"].get<bool>());
}

// Test: Default consensus - majority agreement
TEST(CollaborativeAgentTest, DefaultConsensusMajority) {
    auto agent1 = make_mock_agent("agent1", "agreed");
    auto agent2 = make_mock_agent("agent2", "agreed");
    auto agent3 = make_mock_agent("agent3", "different");

    auto merge = patterns::default_merge::vote;

    patterns::CollaborativeConfig config{
        {agent1, agent2, agent3},
        5,
        patterns::default_consensus::majority_agreement,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should reach majority consensus
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata["consensus"].get<bool>());
}

// Test: Capabilities aggregation
TEST(CollaborativeAgentTest, Capabilities) {
    auto agent1 = make_mock_agent("agent1");
    agent1->set_capabilities({"cap1", "cap2"});

    auto agent2 = make_mock_agent("agent2");
    agent2->set_capabilities({"cap2", "cap3"});

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        1,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto caps = collab.capabilities();

    // Should have collaborative capability plus unique agent capabilities
    bool has_collaborative = false;
    for (const auto& cap : caps) {
        if (cap == "collaborative") {
            has_collaborative = true;
        }
    }

    EXPECT_TRUE(has_collaborative);
}

// Test: Single agent collaboration
TEST(CollaborativeAgentTest, SingleAgent) {
    auto agent = make_mock_agent("solo", "result");

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent},
        3,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "input");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "result");

    // Should run for all rounds
    EXPECT_EQ(agent->call_count(), 3);
}

// Test: Many agents collaboration
TEST(CollaborativeAgentTest, ManyAgents) {
    std::vector<std::shared_ptr<core::Agent>> agents;
    const int num_agents = 10;

    for (int i = 0; i < num_agents; ++i) {
        agents.push_back(make_mock_agent("agent" + std::to_string(i), "r" + std::to_string(i)));
    }

    auto merge = patterns::default_merge::concatenate;

    patterns::CollaborativeConfig config{
        agents,
        2,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    expect_metadata_value<int>(response, "collaborative_agents", num_agents);
    expect_metadata_value<int>(response, "collaborative_rounds", 2);
}

// Test: Empty message handling
TEST(CollaborativeAgentTest, EmptyMessage) {
    auto agent = make_mock_agent("agent1", "response");

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent},
        1,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "");
    auto result = collab.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: Context building across rounds
TEST(CollaborativeAgentTest, ContextBuilding) {
    // Agent that accumulates context
    int call_count = 0;
    auto agent = std::make_shared<MockAgent>(
        "accumulator",
        [&call_count](const core::Message& msg) -> core::Result<core::Message, core::AgentError> {
            call_count++;
            std::string response = "round_" + std::to_string(call_count);
            return core::Result<core::Message, core::AgentError>::ok(
                core::Message::with_text("assistant", response)
            );
        }
    );

    auto merge = patterns::default_merge::last;

    patterns::CollaborativeConfig config{
        {agent},
        3,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should have gone through 3 rounds
    EXPECT_EQ(call_count, 3);
    EXPECT_EQ(response.content_as_str(), "round_3");
}

// Test: Custom merge function
TEST(CollaborativeAgentTest, CustomMergeFunction) {
    auto agent1 = make_mock_agent("agent1", "5");
    auto agent2 = make_mock_agent("agent2", "10");
    auto agent3 = make_mock_agent("agent3", "15");

    // Custom merge that sums numeric responses
    auto custom_merge = [](const std::vector<core::Message>& messages) {
        int sum = 0;
        for (const auto& msg : messages) {
            sum += std::stoi(msg.content_as_str());
        }
        return core::Message::with_text("assistant", std::to_string(sum));
    };

    patterns::CollaborativeConfig config{
        {agent1, agent2, agent3},
        1,
        nullptr,
        custom_merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "30");
}

// Test: Custom consensus function
TEST(CollaborativeAgentTest, CustomConsensusFunction) {
    auto agent1 = make_mock_agent("agent1", "good");
    auto agent2 = make_mock_agent("agent2", "great");

    // Custom consensus that checks for keywords
    auto custom_consensus = [](const std::vector<core::Message>& messages) {
        for (const auto& msg : messages) {
            if (msg.content_as_str().find("good") == std::string::npos &&
                msg.content_as_str().find("great") == std::string::npos) {
                return false;
            }
        }
        return true;
    };

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        5,
        custom_consensus,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should reach custom consensus quickly
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata["consensus"].get<bool>());
}

// Test: Round history in metadata
TEST(CollaborativeAgentTest, RoundHistory) {
    auto agent1 = make_mock_agent("agent1", "r1");
    auto agent2 = make_mock_agent("agent2", "r2");

    auto merge = patterns::default_merge::first;

    patterns::CollaborativeConfig config{
        {agent1, agent2},
        2,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check for round history
    EXPECT_TRUE(metadata.contains("round_history"));
    ASSERT_TRUE(metadata["round_history"].is_array());

    auto history = metadata["round_history"];
    EXPECT_EQ(history.size(), 2);
}

// Test: Different responses each round
TEST(CollaborativeAgentTest, EvolvingResponses) {
    int round = 0;
    auto agent = std::make_shared<MockAgent>(
        "evolving",
        [&round](const core::Message& /* msg */) -> core::Result<core::Message, core::AgentError> {
            round++;
            std::string response = "iteration_" + std::to_string(round);
            return core::Result<core::Message, core::AgentError>::ok(
                core::Message::with_text("assistant", response)
            );
        }
    );

    auto merge = patterns::default_merge::last;

    patterns::CollaborativeConfig config{
        {agent},
        3,
        nullptr,
        merge
    };

    patterns::CollaborativeAgent collab(config);

    auto msg = core::Message::with_text("user", "test");
    auto result = collab.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Final response should be from last round
    EXPECT_EQ(response.content_as_str(), "iteration_3");
}
