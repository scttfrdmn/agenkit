/**
 * @file test_parallel.cpp
 * @brief Comprehensive tests for Parallel pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/parallel.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>
#include <atomic>
#include <chrono>

using namespace agenkit;
using namespace agenkit::test;

// Test: Valid construction
TEST(ParallelAgentTest, Constructor) {
    auto agent1 = make_mock_agent("agent1", "result1");
    auto agent2 = make_mock_agent("agent2", "result2");

    auto aggregator = [](const std::vector<core::Message>& messages) {
        return messages[0];
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    EXPECT_EQ(parallel.name(), "ParallelAgent");
}

// Test: Constructor with empty agents list
TEST(ParallelAgentTest, ConstructorEmptyAgents) {
    auto aggregator = [](const std::vector<core::Message>& messages) {
        return messages[0];
    };

    std::vector<std::shared_ptr<core::Agent>> agents;

    EXPECT_THROW(
        {
            patterns::ParallelAgent parallel(agents, aggregator);
        },
        std::invalid_argument
    );
}

// Test: Constructor with null aggregator
TEST(ParallelAgentTest, ConstructorNullAggregator) {
    auto agent = make_mock_agent("agent1", "result1");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::AggregatorFunc aggregator = nullptr;

    EXPECT_THROW(
        {
            patterns::ParallelAgent parallel(agents, aggregator);
        },
        std::invalid_argument
    );
}

// Test: Basic parallel processing
TEST(ParallelAgentTest, BasicProcess) {
    auto agent1 = make_mock_agent("agent1", "response1");
    auto agent2 = make_mock_agent("agent2", "response2");
    auto agent3 = make_mock_agent("agent3", "response3");

    auto aggregator = [](const std::vector<core::Message>& messages) {
        std::string combined = "aggregated " + std::to_string(messages.size()) + " responses";
        return core::Message::with_text("assistant", combined);
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test input");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "aggregated 3 responses");
}

// Test: Concurrent execution verification
TEST(ParallelAgentTest, ConcurrentExecution) {
    std::atomic<int> active_counter(0);
    std::atomic<int> max_counter(0);

    auto delay = std::chrono::milliseconds(50);

    auto agent1 = std::make_shared<ConcurrencyTrackingAgent>(
        "agent1", "r1", delay, &active_counter, &max_counter);
    auto agent2 = std::make_shared<ConcurrencyTrackingAgent>(
        "agent2", "r2", delay, &active_counter, &max_counter);
    auto agent3 = std::make_shared<ConcurrencyTrackingAgent>(
        "agent3", "r3", delay, &active_counter, &max_counter);

    auto aggregator = patterns::default_aggregators::first;

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());

    // If truly concurrent, max should be > 1
    EXPECT_GT(max_counter.load(), 1) << "Expected concurrent execution";
}

// Test: Metadata tracking
TEST(ParallelAgentTest, Metadata) {
    auto agent1 = make_mock_agent("agent1", "r1");
    auto agent2 = make_mock_agent("agent2", "r2");

    auto aggregator = patterns::default_aggregators::first;

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Check metadata
    expect_metadata_exists(response, "parallel_agents");
    expect_metadata_value<int>(response, "parallel_agents", 2);

    expect_metadata_exists(response, "successful_agents");
    expect_metadata_value<int>(response, "successful_agents", 2);
}

// Test: Partial failure - some agents succeed
TEST(ParallelAgentTest, PartialFailure) {
    auto agent1 = make_mock_agent("agent1", "success");
    auto agent2 = make_failing_mock_agent("agent2", "agent2 failed");
    auto agent3 = make_mock_agent("agent3", "success");

    auto aggregator = [](const std::vector<core::Message>& messages) {
        std::string combined = "got " + std::to_string(messages.size()) + " successes";
        return core::Message::with_text("assistant", combined);
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should have 2 successes
    EXPECT_EQ(response.content_as_str(), "got 2 successes");

    // Check error metadata
    auto metadata = response.metadata();
    ASSERT_TRUE(metadata.contains("errors"));
    ASSERT_TRUE(metadata["errors"].is_array());

    auto errors = metadata["errors"];
    EXPECT_EQ(errors.size(), 1);
    EXPECT_EQ(errors[0]["agent"].get<std::string>(), "agent2");
}

// Test: All agents fail
TEST(ParallelAgentTest, AllAgentsFail) {
    auto agent1 = make_failing_mock_agent("agent1", "failure1");
    auto agent2 = make_failing_mock_agent("agent2", "failure2");

    auto aggregator = [](const std::vector<core::Message>& messages) {
        return messages[0];
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("all agents failed") != std::string::npos);
}

// Test: Default aggregator - first
TEST(ParallelAgentTest, DefaultAggregatorFirst) {
    auto agent1 = make_mock_agent("agent1", "first");
    auto agent2 = make_mock_agent("agent2", "second");
    auto agent3 = make_mock_agent("agent3", "third");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, patterns::default_aggregators::first);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should be one of the responses (order not guaranteed due to concurrency)
    std::string content = response.content_as_str();
    bool valid = (content == "first" || content == "second" || content == "third");
    EXPECT_TRUE(valid);
}

// Test: Default aggregator - concatenate
TEST(ParallelAgentTest, DefaultAggregatorConcatenate) {
    auto agent1 = make_mock_agent("agent1", "A");
    auto agent2 = make_mock_agent("agent2", "B");
    auto agent3 = make_mock_agent("agent3", "C");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, patterns::default_aggregators::concatenate);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should contain all responses (order may vary)
    std::string content = response.content_as_str();
    EXPECT_TRUE(content.find("A") != std::string::npos);
    EXPECT_TRUE(content.find("B") != std::string::npos);
    EXPECT_TRUE(content.find("C") != std::string::npos);
}

// Test: Default aggregator - majority vote
TEST(ParallelAgentTest, DefaultAggregatorMajorityVote) {
    auto agent1 = make_mock_agent("agent1", "answer_A");
    auto agent2 = make_mock_agent("agent2", "answer_A");
    auto agent3 = make_mock_agent("agent3", "answer_B");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::ParallelAgent parallel(agents, patterns::default_aggregators::majority_vote);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Majority should win (answer_A)
    EXPECT_EQ(response.content_as_str(), "answer_A");

    // Should have vote metadata
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("vote_count"));
}

// Test: Single agent parallel
TEST(ParallelAgentTest, SingleAgent) {
    auto agent = make_mock_agent("solo", "result");

    auto aggregator = patterns::default_aggregators::first;

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "input");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "result");
}

// Test: Large number of parallel agents
TEST(ParallelAgentTest, ManyAgents) {
    std::vector<std::shared_ptr<core::Agent>> agents;
    const int num_agents = 20;

    for (int i = 0; i < num_agents; ++i) {
        agents.push_back(make_mock_agent("agent" + std::to_string(i), "r" + std::to_string(i)));
    }

    auto aggregator = [num_agents](const std::vector<core::Message>& messages) {
        std::string combined = "collected " + std::to_string(messages.size()) + " responses";
        return core::Message::with_text("assistant", combined);
    };

    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "collected " + std::to_string(num_agents) + " responses");
}

// Test: Capabilities aggregation
TEST(ParallelAgentTest, Capabilities) {
    auto agent1 = make_mock_agent("agent1");
    agent1->set_capabilities({"cap1", "cap2"});

    auto agent2 = make_mock_agent("agent2");
    agent2->set_capabilities({"cap2", "cap3"});

    auto aggregator = patterns::default_aggregators::first;

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto caps = parallel.capabilities();

    // Should have parallel capability plus unique agent capabilities
    bool has_parallel = false;
    for (const auto& cap : caps) {
        if (cap == "parallel") {
            has_parallel = true;
        }
    }

    EXPECT_TRUE(has_parallel);
}

// Test: Custom aggregator with metadata
TEST(ParallelAgentTest, CustomAggregatorWithMetadata) {
    auto agent1 = make_mock_agent("agent1", "response1");
    auto agent2 = make_mock_agent("agent2", "response2");

    auto aggregator = [](const std::vector<core::Message>& messages) {
        std::string combined;
        for (const auto& msg : messages) {
            if (!combined.empty()) {
                combined += " | ";
            }
            combined += msg.content_as_str();
        }

        auto result = core::Message::with_text("assistant", combined);
        nlohmann::json custom_meta = {{"custom_key", "custom_value"}};
        for (auto it = custom_meta.begin(); it != custom_meta.end(); ++it) {
            result.with_metadata(it.key(), it.value());
        }
        return result;
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Check custom metadata from aggregator
    auto metadata = response.metadata();
    EXPECT_TRUE(metadata.contains("custom_key"));
    EXPECT_EQ(metadata["custom_key"].get<std::string>(), "custom_value");
}

// Test: Partial failure with metadata tracking
TEST(ParallelAgentTest, PartialFailureMetadata) {
    auto agent1 = make_mock_agent("agent1", "success1");
    auto agent2 = make_failing_mock_agent("agent2", "error2");
    auto agent3 = make_mock_agent("agent3", "success3");
    auto agent4 = make_failing_mock_agent("agent4", "error4");

    auto aggregator = patterns::default_aggregators::first;

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3, agent4};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Should track successful and failed agents
    expect_metadata_value<int>(response, "parallel_agents", 4);
    expect_metadata_value<int>(response, "successful_agents", 2);

    ASSERT_TRUE(metadata.contains("errors"));
    auto errors = metadata["errors"];
    EXPECT_EQ(errors.size(), 2);
}

// Test: Empty message handling
TEST(ParallelAgentTest, EmptyMessage) {
    auto agent = make_mock_agent("agent1", "response");

    auto aggregator = patterns::default_aggregators::first;

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "");
    auto result = parallel.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: Agent response order independence
TEST(ParallelAgentTest, OrderIndependence) {
    // Run multiple times to test for race conditions
    for (int run = 0; run < 5; ++run) {
        auto agent1 = make_mock_agent("agent1", "A");
        auto agent2 = make_mock_agent("agent2", "B");
        auto agent3 = make_mock_agent("agent3", "C");

        auto aggregator = [](const std::vector<core::Message>& messages) {
            // Count unique responses
            std::set<std::string> unique_responses;
            for (const auto& msg : messages) {
                unique_responses.insert(msg.content_as_str());
            }
            std::string result = std::to_string(unique_responses.size()) + " unique";
            return core::Message::with_text("assistant", result);
        };

        std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
        patterns::ParallelAgent parallel(agents, aggregator);

        auto msg = core::Message::with_text("user", "test");
        auto result = parallel.process(std::move(msg)).get();

        ASSERT_TRUE(result.is_ok());
        auto response = result.unwrap();
        EXPECT_EQ(response.content_as_str(), "3 unique");
    }
}

// Test: Aggregator with empty results (all failed scenario)
TEST(ParallelAgentTest, AggregatorEmptyResults) {
    auto agent1 = make_failing_mock_agent("agent1");
    auto agent2 = make_failing_mock_agent("agent2");

    bool aggregator_called = false;
    auto aggregator = [&aggregator_called](const std::vector<core::Message>& messages) {
        aggregator_called = true;
        return messages[0];
    };

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::ParallelAgent parallel(agents, aggregator);

    auto msg = core::Message::with_text("user", "test");
    auto result = parallel.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    // Aggregator should not be called if all agents fail
    EXPECT_FALSE(aggregator_called);
}
