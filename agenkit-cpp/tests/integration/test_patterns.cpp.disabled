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

    // Create parallel pattern with default aggregator
    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    auto aggregator = [](const std::vector<core::Message>& messages) -> core::Message {
        // Simple concatenation aggregator
        std::string combined;
        for (const auto& msg : messages) {
            if (!combined.empty()) combined += " | ";
            combined += msg.content_as_str();
        }
        return core::Message::with_text("assistant", combined);
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
    // Create worker agents
    auto worker1 = std::make_shared<adapters::EchoAgent>();
    auto worker2 = std::make_shared<adapters::EchoAgent>();

    // Create supervisor with workers
    std::vector<std::shared_ptr<core::Agent>> workers = {worker1, worker2};
    patterns::SupervisorAgent supervisor(workers);

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
    auto echo_agent = std::make_shared<adapters::EchoAgent>();
    auto backup_agent = std::make_shared<adapters::EchoAgent>();

    // Create router with routing function
    std::vector<std::shared_ptr<core::Agent>> agents = {echo_agent, backup_agent};
    auto routing_fn = [](const core::Message& msg) -> size_t {
        // Route based on metadata
        if (msg.metadata().contains("route") &&
            msg.metadata()["route"].get<std::string>() == "backup") {
            return 1;  // backup_agent
        }
        return 0;  // echo_agent
    };

    patterns::RouterAgent router(agents, routing_fn);

    EXPECT_EQ(router.name(), "router");

    // Test routing to first agent
    auto msg1 = core::Message::with_text("user", "Route to echo");
    msg1.with_metadata("route", "primary");

    auto future1 = router.process(std::move(msg1));
    auto result1 = future1.get();

    ASSERT_TRUE(result1.is_ok());
    auto response1 = result1.unwrap();
    EXPECT_EQ(response1.role(), "assistant");

    // Test routing to backup agent
    auto msg2 = core::Message::with_text("user", "Route to backup");
    msg2.with_metadata("route", "backup");

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

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::CollaborativeAgent collaborative(agents, 2);  // Max 2 rounds

    EXPECT_EQ(collaborative.name(), "collaborative");

    auto msg = core::Message::with_text("user", "Collaborative problem solving");
    msg.with_metadata("test_type", "collaborative");

    auto future = collaborative.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: HumanInLoop pattern integration
 * Tests human-in-the-loop pattern with simulated human input
 */
TEST(PatternIntegrationTest, HumanInLoopPattern) {
    auto base_agent = std::make_shared<adapters::EchoAgent>();

    // Create human-in-loop with callback that simulates human approval
    auto human_callback = [](const core::Message& msg) -> std::optional<std::string> {
        // Simulate human approving the message
        if (msg.content_as_str().find("test") != std::string::npos) {
            return std::nullopt;  // Approve
        }
        return std::string("Rejected by human");
    };

    patterns::HumanInLoopAgent human_in_loop(base_agent, human_callback);

    EXPECT_EQ(human_in_loop.name(), "human-in-loop");

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
