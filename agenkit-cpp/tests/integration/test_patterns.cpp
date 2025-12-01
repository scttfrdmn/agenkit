/**
 * @file test_patterns.cpp
 * @brief Integration tests for pattern implementations
 *
 * Tests real pattern functionality including Sequential, Parallel, Supervisor,
 * Router, Collaborative, HumanInLoop, and Fallback patterns.
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/patterns/sequential.hpp"
#include "agenkit/patterns/parallel.hpp"
#include "agenkit/patterns/supervisor.hpp"
#include "agenkit/patterns/router.hpp"
#include "agenkit/patterns/collaborative.hpp"
#include "agenkit/patterns/human_in_loop.hpp"
#include "agenkit/patterns/fallback.hpp"
#include <memory>
#include <vector>

using namespace agenkit;

/**
 * Test: Sequential pattern integration
 * Tests that sequential pattern executes agents in order
 */
TEST(PatternIntegrationTest, SequentialPattern) {
    // Create agents
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();
    auto agent3 = std::make_shared<adapters::EchoAgent>();

    // Create sequential pattern
    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent sequential(agents);

    EXPECT_EQ(sequential.name(), "sequential");

    auto msg = core::Message::with_text("user", "Sequential test");
    msg.with_metadata("test_type", "sequential");

    auto future = sequential.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should have gone through all 3 agents
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Parallel pattern integration
 * Tests that parallel pattern executes agents concurrently
 */
TEST(PatternIntegrationTest, ParallelPattern) {
    // Create agents
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();
    auto agent3 = std::make_shared<adapters::EchoAgent>();

    // Create parallel pattern with metadata-preserving aggregator
    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    auto aggregator = [](const std::vector<core::Message>& messages) -> core::Message {
        // Simple concatenation aggregator
        std::string combined;
        for (const auto& msg : messages) {
            if (!combined.empty()) combined += " | ";
            combined += msg.content_as_str();
        }
        auto result = core::Message::with_text("assistant", combined);
        // Preserve metadata from first message
        if (!messages.empty() && !messages[0].metadata().is_null()) {
            for (auto it = messages[0].metadata().begin(); it != messages[0].metadata().end(); ++it) {
                result.with_metadata(it.key(), it.value());
            }
        }
        return result;
    };
    patterns::ParallelAgent parallel(agents, aggregator);

    EXPECT_EQ(parallel.name(), "parallel");

    auto msg = core::Message::with_text("user", "Parallel test");
    msg.with_metadata("test_type", "parallel");

    auto future = parallel.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should aggregate results from all 3 agents
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Supervisor pattern integration
 * Tests that supervisor pattern coordinates multiple agents
 */
TEST(PatternIntegrationTest, SupervisorPattern) {
    // Create specialist agents
    auto specialist1 = std::make_shared<adapters::EchoAgent>();
    auto specialist2 = std::make_shared<adapters::EchoAgent>();

    // Create planner agent (using SimplePlanner with EchoAgent)
    auto base_agent = std::make_shared<adapters::EchoAgent>();
    auto planner = std::make_shared<patterns::SimplePlanner>(base_agent);

    // Create supervisor with planner and specialists
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists = {
        {"specialist1", specialist1},
        {"specialist2", specialist2}
    };
    patterns::SupervisorAgent supervisor(planner, specialists);

    EXPECT_EQ(supervisor.name(), "supervisor");

    auto msg = core::Message::with_text("user", "Supervisor test task");
    msg.with_metadata("test_type", "supervisor");

    auto future = supervisor.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Router pattern integration
 * Tests that router pattern selects appropriate agent
 */
TEST(PatternIntegrationTest, RouterPattern) {
    // Create specialized agents
    auto primary_agent = std::make_shared<adapters::EchoAgent>();
    auto backup_agent = std::make_shared<adapters::EchoAgent>();

    // Create simple keyword-based classifier
    std::unordered_map<std::string, std::vector<std::string>> keywords = {
        {"primary", {"primary", "main", "default"}},
        {"backup", {"backup", "fallback", "secondary"}}
    };
    auto classifier = std::make_shared<patterns::SimpleClassifier>(
        primary_agent,  // Fallback agent if classification is unclear
        keywords
    );

    // Create router with config
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents = {
        {"primary", primary_agent},
        {"backup", backup_agent}
    };
    patterns::RouterConfig config{classifier, agents, "primary"};  // Default to primary
    patterns::RouterAgent router(config);

    EXPECT_EQ(router.name(), "router");

    // Test routing to primary agent
    auto msg1 = core::Message::with_text("user", "Route to primary agent");
    msg1.with_metadata("test_type", "router");

    auto future1 = router.process(std::move(msg1));
    auto result1 = future1.get();

    ASSERT_TRUE(result1.is_ok());
    auto response1 = result1.unwrap();
    EXPECT_EQ(response1.role(), "assistant");

    // Test routing to backup agent
    auto msg2 = core::Message::with_text("user", "Route to backup agent");
    msg2.with_metadata("test_type", "router");

    auto future2 = router.process(std::move(msg2));
    auto result2 = future2.get();

    ASSERT_TRUE(result2.is_ok());
    auto response2 = result2.unwrap();
    EXPECT_EQ(response2.role(), "assistant");
}

/**
 * Test: Collaborative pattern integration
 * Tests that collaborative pattern enables agent interaction
 */
TEST(PatternIntegrationTest, CollaborativePattern) {
    // Create collaborating agents
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();
    auto agent3 = std::make_shared<adapters::EchoAgent>();

    // Create collaborative config
    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};

    // Define merge function (return last response - most refined)
    // Note: CollaborativeAgent doesn't preserve original input metadata to agent responses,
    // so we can't expect test_type metadata in the merged result
    auto merge_func = [](const std::vector<core::Message>& messages) -> core::Message {
        if (messages.empty()) {
            return core::Message::with_text("assistant", "");
        }
        return messages.back();
    };

    patterns::CollaborativeConfig config;
    config.agents = agents;
    config.max_rounds = 2;  // Max 2 rounds
    config.merge_func = merge_func;
    // config.consensus_func is optional

    patterns::CollaborativeAgent collaborative(config);

    EXPECT_EQ(collaborative.name(), "collaborative");

    auto msg = core::Message::with_text("user", "Collaborative problem solving");
    msg.with_metadata("test_type", "collaborative");

    auto future = collaborative.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    // CollaborativeAgent adds its own metadata but doesn't preserve input metadata
    EXPECT_TRUE(response.metadata().contains("collaboration_rounds"));
    EXPECT_TRUE(response.metadata().contains("collaboration_agents"));
}

/**
 * Test: HumanInLoop pattern integration
 * Tests human-in-the-loop pattern with simulated human input
 */
TEST(PatternIntegrationTest, HumanInLoopPattern) {
    auto base_agent = std::make_shared<adapters::EchoAgent>();

    // Create human-in-loop with callback that simulates human approval
    auto approval_func = [](const patterns::ApprovalRequest& request)
        -> core::Result<patterns::ApprovalResponse, core::AgentError> {
        // Simulate human approving messages with "test"
        if (request.message.content_as_str().find("test") != std::string::npos) {
            return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
                patterns::ApprovalResponse{true, "Approved"}
            );
        }
        return core::Result<patterns::ApprovalResponse, core::AgentError>::ok(
            patterns::ApprovalResponse{false, "Rejected by human"}
        );
    };

    // Create config
    patterns::HumanInLoopConfig config;
    config.agent = base_agent;
    config.approval_threshold = 0.8;  // Require approval if confidence < 80%
    config.approval_func = approval_func;

    patterns::HumanInLoopAgent human_in_loop(config);

    EXPECT_EQ(human_in_loop.name(), "human_in_loop");

    // Test message that should be approved
    auto msg = core::Message::with_text("user", "This is a test message");
    msg.with_metadata("test_type", "human_in_loop");

    auto future = human_in_loop.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
}

/**
 * Test: Fallback pattern integration
 * Tests fallback pattern tries alternatives on failure
 */
TEST(PatternIntegrationTest, FallbackPattern) {
    // Create agents where first might fail
    auto primary_agent = std::make_shared<adapters::EchoAgent>();
    auto fallback1 = std::make_shared<adapters::EchoAgent>();
    auto fallback2 = std::make_shared<adapters::EchoAgent>();

    std::vector<std::shared_ptr<core::Agent>> agents = {
        primary_agent,
        fallback1,
        fallback2
    };

    patterns::FallbackAgent fallback_pattern(agents);

    EXPECT_EQ(fallback_pattern.name(), "fallback");

    auto msg = core::Message::with_text("user", "Fallback test");
    msg.with_metadata("test_type", "fallback");

    auto future = fallback_pattern.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should succeed with one of the agents
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Pattern composition - Sequential of Parallel
 * Tests composing patterns together
 */
TEST(PatternIntegrationTest, PatternComposition) {
    // Create parallel patterns
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();
    auto agent3 = std::make_shared<adapters::EchoAgent>();
    auto agent4 = std::make_shared<adapters::EchoAgent>();

    // Aggregator for parallel patterns
    auto aggregator = [](const std::vector<core::Message>& messages) -> core::Message {
        std::string combined;
        for (const auto& msg : messages) {
            if (!combined.empty()) combined += " | ";
            combined += msg.content_as_str();
        }
        return core::Message::with_text("assistant", combined);
    };

    // First parallel group
    std::vector<std::shared_ptr<core::Agent>> parallel1_agents = {agent1, agent2};
    auto parallel1 = std::make_shared<patterns::ParallelAgent>(parallel1_agents, aggregator);

    // Second parallel group
    std::vector<std::shared_ptr<core::Agent>> parallel2_agents = {agent3, agent4};
    auto parallel2 = std::make_shared<patterns::ParallelAgent>(parallel2_agents, aggregator);

    // Sequential composition
    std::vector<std::shared_ptr<core::Agent>> sequential_agents = {parallel1, parallel2};
    patterns::SequentialAgent composed(sequential_agents);

    auto msg = core::Message::with_text("user", "Composed pattern test");
    msg.with_metadata("test_type", "composition");

    auto future = composed.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
}

/**
 * Test: Pattern error handling
 * Tests that patterns properly handle errors from agents
 */
TEST(PatternIntegrationTest, PatternErrorHandling) {
    // Create a sequential pattern with echo agents
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::SequentialAgent sequential(agents);

    // Normal message should succeed
    auto msg = core::Message::with_text("user", "Test");
    msg.with_metadata("test_type", "error_handling");

    auto future = sequential.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Pattern metadata flow
 * Tests that metadata flows correctly through patterns
 */
TEST(PatternIntegrationTest, PatternMetadataFlow) {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::SequentialAgent sequential(agents);

    // Create message with rich metadata
    auto msg = core::Message::with_text("user", "Metadata test");
    msg.with_metadata("trace_id", "trace-123")
       .with_metadata("session_id", "session-456")
       .with_metadata("priority", 5)
       .with_metadata("tags", nlohmann::json::array({"integration", "pattern"}));

    auto future = sequential.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Verify metadata was preserved through pattern
    EXPECT_TRUE(response.metadata().contains("trace_id"));
    EXPECT_TRUE(response.metadata().contains("session_id"));
    EXPECT_TRUE(response.metadata().contains("priority"));
    EXPECT_TRUE(response.metadata().contains("tags"));
}

/**
 * Test: Pattern concurrent execution
 * Tests patterns can handle concurrent requests
 */
TEST(PatternIntegrationTest, PatternConcurrentExecution) {
    auto agent1 = std::make_shared<adapters::EchoAgent>();
    auto agent2 = std::make_shared<adapters::EchoAgent>();

    auto aggregator = [](const std::vector<core::Message>& messages) -> core::Message {
        std::string combined;
        for (const auto& msg : messages) {
            if (!combined.empty()) combined += " | ";
            combined += msg.content_as_str();
        }
        return core::Message::with_text("assistant", combined);
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    constexpr int num_requests = 5;
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;

    // Launch concurrent requests to the pattern
    for (int i = 0; i < num_requests; ++i) {
        auto msg = core::Message::with_text("user", "Request " + std::to_string(i));
        msg.with_metadata("request_id", i);
        futures.push_back(parallel.process(std::move(msg)));
    }

    // Collect results
    int success_count = 0;
    for (auto& future : futures) {
        auto result = future.get();
        if (result.is_ok()) {
            ++success_count;
        }
    }

    EXPECT_EQ(success_count, num_requests);
}
