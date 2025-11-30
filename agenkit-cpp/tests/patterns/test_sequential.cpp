/**
 * @file test_sequential.cpp
 * @brief Comprehensive tests for Sequential pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/sequential.hpp"
#include "test_pattern_helpers.hpp"
#include <memory>
#include <string>
#include <stdexcept>

using namespace agenkit;
using namespace agenkit::test;

// Test: Valid construction
TEST(SequentialAgentTest, Constructor) {
    auto agent1 = make_mock_agent("agent1", "result1");
    auto agent2 = make_mock_agent("agent2", "result2");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::SequentialAgent seq(agents);

    EXPECT_EQ(seq.name(), "SequentialAgent");
}

// Test: Constructor with empty agents list
TEST(SequentialAgentTest, ConstructorEmptyAgents) {
    std::vector<std::shared_ptr<core::Agent>> agents;

    EXPECT_THROW(
        {
            patterns::SequentialAgent seq(agents);
        },
        std::invalid_argument
    );
}

// Test: Basic sequential processing
TEST(SequentialAgentTest, BasicProcess) {
    auto agent1 = make_mock_agent("agent1", "step1");
    auto agent2 = make_mock_agent("agent2", "step2");
    auto agent3 = make_mock_agent("agent3", "final");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "test input");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "final");
}

// Test: Pipeline transformation through stages
TEST(SequentialAgentTest, PipelineTransformation) {
    auto agent1 = make_appending_mock_agent("agent1", " -> stage1");
    auto agent2 = make_appending_mock_agent("agent2", " -> stage2");
    auto agent3 = make_appending_mock_agent("agent3", " -> stage3");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "input");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "input -> stage1 -> stage2 -> stage3");
}

// Test: Metadata preservation across pipeline stages
TEST(SequentialAgentTest, MetadataPreservation) {
    nlohmann::json meta1 = {{"stage1_key", "stage1_value"}};
    nlohmann::json meta2 = {{"stage2_key", "stage2_value"}};

    auto agent1 = make_metadata_mock_agent("agent1", "stage1", meta1);
    auto agent2 = make_metadata_mock_agent("agent2", "stage2", meta2);

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check pipeline metadata
    expect_metadata_exists(response, "pipeline_length");
    expect_metadata_value<int>(response, "pipeline_length", 2);

    expect_metadata_exists(response, "pipeline_stages");
}

// Test: Error handling - propagation from agent
TEST(SequentialAgentTest, ErrorHandling) {
    auto agent1 = make_mock_agent("agent1", "success");
    auto agent2 = make_failing_mock_agent("agent2", "agent2 failed");
    auto agent3 = make_mock_agent("agent3", "should not reach");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("agent2") != std::string::npos ||
                error.message().find("stage 1") != std::string::npos);
}

// Test: First agent failure
TEST(SequentialAgentTest, FirstAgentFailure) {
    auto agent1 = make_failing_mock_agent("agent1", "first agent error");
    auto agent2 = make_mock_agent("agent2", "should not execute");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();
    EXPECT_TRUE(error.message().find("agent1") != std::string::npos ||
                error.message().find("stage 0") != std::string::npos);
}

// Test: Single agent pipeline
TEST(SequentialAgentTest, SingleAgent) {
    auto agent = make_mock_agent("solo", "result");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "input");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "result");

    // Check metadata
    expect_metadata_value<int>(response, "pipeline_length", 1);
}

// Test: Stage metadata tracking
TEST(SequentialAgentTest, StageMetadata) {
    auto agent1 = make_mock_agent("extractor", "extracted");
    auto agent2 = make_mock_agent("transformer", "transformed");
    auto agent3 = make_mock_agent("validator", "validated");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "input");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    auto metadata = response.metadata();

    ASSERT_TRUE(metadata.contains("pipeline_stages"));
    ASSERT_TRUE(metadata["pipeline_stages"].is_array());

    auto stages = metadata["pipeline_stages"];
    EXPECT_EQ(stages.size(), 3);

    std::vector<std::string> expected_agents = {"extractor", "transformer", "validator"};
    for (size_t i = 0; i < stages.size(); ++i) {
        ASSERT_TRUE(stages[i].contains("agent"));
        EXPECT_EQ(stages[i]["agent"].get<std::string>(), expected_agents[i]);

        ASSERT_TRUE(stages[i].contains("stage"));
        EXPECT_EQ(stages[i]["stage"].get<int>(), static_cast<int>(i));
    }
}

// Test: Capabilities aggregation
TEST(SequentialAgentTest, Capabilities) {
    auto agent1 = make_mock_agent("agent1");
    agent1->set_capabilities({"cap1", "cap2"});

    auto agent2 = make_mock_agent("agent2");
    agent2->set_capabilities({"cap2", "cap3"});

    auto agent3 = make_mock_agent("agent3");
    agent3->set_capabilities({"cap4"});

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent seq(agents);

    auto caps = seq.capabilities();

    // Should have sequential/pipeline capabilities plus unique agent capabilities
    bool has_sequential = false;
    bool has_pipeline = false;
    for (const auto& cap : caps) {
        if (cap == "sequential") {
            has_sequential = true;
        }
        if (cap == "pipeline") {
            has_pipeline = true;
        }
    }

    EXPECT_TRUE(has_sequential);
    EXPECT_TRUE(has_pipeline);
}

// Test: Long pipeline with many stages
TEST(SequentialAgentTest, LongPipeline) {
    std::vector<std::shared_ptr<core::Agent>> agents;
    const int num_agents = 10;

    for (int i = 0; i < num_agents; ++i) {
        agents.push_back(
            make_appending_mock_agent("agent" + std::to_string(i), " -> s" + std::to_string(i))
        );
    }

    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "start");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Should have all stages appended
    std::string expected = "start";
    for (int i = 0; i < num_agents; ++i) {
        expected += " -> s" + std::to_string(i);
    }
    EXPECT_EQ(response.content_as_str(), expected);

    expect_metadata_value<int>(response, "pipeline_length", num_agents);
}

// Test: Error at middle stage
TEST(SequentialAgentTest, ErrorAtMiddleStage) {
    auto agent1 = make_mock_agent("agent1", "step1");
    auto agent2 = make_failing_mock_agent("agent2", "middle failure");
    auto agent3 = make_mock_agent("agent3", "step3");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2, agent3};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    // Error should reference stage 1 (0-indexed) or agent2
    auto error = result.unwrap_err();
    std::string error_msg = error.message();
    bool has_stage_info = (error_msg.find("stage 1") != std::string::npos) ||
                          (error_msg.find("agent2") != std::string::npos);
    EXPECT_TRUE(has_stage_info);
}

// Test: Empty message handling
TEST(SequentialAgentTest, EmptyMessage) {
    auto agent = make_mock_agent("agent1", "response");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "");
    auto result = seq.process(std::move(msg)).get();

    // Should still process successfully
    ASSERT_TRUE(result.is_ok());
}

// Test: Message role preservation
TEST(SequentialAgentTest, MessageRolePreservation) {
    auto agent1 = make_mock_agent("agent1", "response1");
    auto agent2 = make_mock_agent("agent2", "response2");

    std::vector<std::shared_ptr<core::Agent>> agents = {agent1, agent2};
    patterns::SequentialAgent seq(agents);

    auto msg = core::Message::with_text("user", "test");
    auto result = seq.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Response should be from assistant role
    EXPECT_EQ(response.role(), "assistant");
}
