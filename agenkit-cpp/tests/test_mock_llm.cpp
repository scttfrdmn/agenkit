/**
 * @file test_mock_llm.cpp
 * @brief Tests for MockLLM test utility
 */

#include <gtest/gtest.h>
#include "test_utils.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;
using namespace agenkit::test;
using namespace agenkit::core;

TEST(MockLLMTest, BasicFunctionality) {
    auto mock_llm = std::make_shared<MockLLM>(
        std::vector<std::string>{"Response 1", "Response 2"},
        "mock-gpt-4"
    );

    EXPECT_EQ("mock-gpt-4", mock_llm->name());
    EXPECT_EQ(0, mock_llm->get_call_count());

    // First call
    auto msg1 = Message::with_text("user", "What is AI?");
    auto future1 = mock_llm->process(std::move(msg1));
    auto result1 = future1.get();

    EXPECT_TRUE(result1.is_ok());
    EXPECT_EQ("Response 1", result1.unwrap().content_as_str());
    EXPECT_EQ(1, mock_llm->get_call_count());

    // Second call
    auto msg2 = Message::with_text("user", "Tell me more");
    auto future2 = mock_llm->process(std::move(msg2));
    auto result2 = future2.get();

    EXPECT_TRUE(result2.is_ok());
    EXPECT_EQ("Response 2", result2.unwrap().content_as_str());
    EXPECT_EQ(2, mock_llm->get_call_count());

    // Third call (cycles back)
    auto msg3 = Message::with_text("user", "And again");
    auto future3 = mock_llm->process(std::move(msg3));
    auto result3 = future3.get();

    EXPECT_TRUE(result3.is_ok());
    EXPECT_EQ("Response 1", result3.unwrap().content_as_str());
    EXPECT_EQ(3, mock_llm->get_call_count());
}

TEST(MockLLMTest, SingleResponse) {
    auto mock_llm = std::make_shared<MockLLM>("Single response");

    auto msg = Message::with_text("user", "Test");
    auto future = mock_llm->process(std::move(msg));
    auto result = future.get();

    EXPECT_TRUE(result.is_ok());
    EXPECT_EQ("Single response", result.unwrap().content_as_str());
}

TEST(MockLLMTest, LLMParameters) {
    auto mock_llm = std::make_shared<MockLLM>("Response");

    // Test temperature
    mock_llm->set_temperature(0.7);
    EXPECT_DOUBLE_EQ(0.7, mock_llm->get_temperature());

    // Test max_tokens
    mock_llm->set_max_tokens(100);
    EXPECT_EQ(100, mock_llm->get_max_tokens().value());

    // Test top_p
    mock_llm->set_top_p(0.9);
    EXPECT_DOUBLE_EQ(0.9, mock_llm->get_top_p().value());
}

TEST(MockLLMTest, Metadata) {
    auto mock_llm = std::make_shared<MockLLM>("Response", "gpt-4-turbo");
    mock_llm->set_temperature(0.8);
    mock_llm->set_max_tokens(150);

    auto msg = Message::with_text("user", "Test");
    auto future = mock_llm->process(std::move(msg));
    auto result = future.get();

    EXPECT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Check LLM metadata was added
    auto llm_metadata = response.get_metadata("llm");
    EXPECT_TRUE(llm_metadata.has_value());

    auto metadata_json = llm_metadata.value();
    EXPECT_EQ("gpt-4-turbo", metadata_json["model"].get<std::string>());
    EXPECT_DOUBLE_EQ(0.8, metadata_json["temperature"].get<double>());
    EXPECT_EQ(150, metadata_json["max_tokens"].get<int>());
    EXPECT_TRUE(metadata_json["mock"].get<bool>());
}

TEST(MockLLMTest, FailureMode) {
    auto mock_llm = std::make_shared<MockLLM>("Response");
    mock_llm->set_failure_mode(true, "Simulated failure");

    auto msg = Message::with_text("user", "Test");
    auto future = mock_llm->process(std::move(msg));
    auto result = future.get();

    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(AgentErrorType::ProcessingError, result.unwrap_err().type());
    EXPECT_EQ("Simulated failure", result.unwrap_err().message());
}

TEST(MockLLMTest, DelaySimulation) {
    auto mock_llm = std::make_shared<MockLLM>("Response");
    mock_llm->set_delay(100); // 100ms delay

    auto start = std::chrono::steady_clock::now();

    auto msg = Message::with_text("user", "Test");
    auto future = mock_llm->process(std::move(msg));
    auto result = future.get();

    auto end = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    EXPECT_TRUE(result.is_ok());
    EXPECT_GE(duration.count(), 100); // Should take at least 100ms
}

TEST(MockLLMTest, ResetCallCount) {
    auto mock_llm = std::make_shared<MockLLM>("Response");

    // Make some calls
    auto msg1 = Message::with_text("user", "Test 1");
    auto future1 = mock_llm->process(std::move(msg1));
    future1.get();

    EXPECT_EQ(1, mock_llm->get_call_count());

    // Reset
    mock_llm->reset_call_count();
    EXPECT_EQ(0, mock_llm->get_call_count());
}

TEST(MockLLMTest, DebugInfo) {
    auto mock_llm = std::make_shared<MockLLM>(
        std::vector<std::string>{"R1", "R2"},
        "gpt-4"
    );
    mock_llm->set_temperature(0.7);
    mock_llm->set_max_tokens(100);

    std::string info = mock_llm->debug_info();

    EXPECT_NE(std::string::npos, info.find("MockLLM"));
    EXPECT_NE(std::string::npos, info.find("gpt-4"));
    EXPECT_NE(std::string::npos, info.find("responses=2"));
    EXPECT_NE(std::string::npos, info.find("temperature=0.7"));
    EXPECT_NE(std::string::npos, info.find("max_tokens=100"));
}

// Test MockLLM::introspect() -- the real Agent interface method (#850)
TEST(MockLLMTest, Introspect) {
    auto mock_llm = std::make_shared<MockLLM>(
        std::vector<std::string>{"R1", "R2"},
        "gpt-4"
    );

    nlohmann::json result = mock_llm->introspect();

    EXPECT_EQ(result["agent_name"], "gpt-4");
    ASSERT_TRUE(result["capabilities"].is_array());
    EXPECT_FALSE(result["capabilities"].empty());
    EXPECT_TRUE(result["memory_state"].is_null());
    EXPECT_TRUE(result["internal_state"].is_object());
    EXPECT_TRUE(result.contains("timestamp"));
}

TEST(MockLLMTest, Capabilities) {
    auto mock_llm = std::make_shared<MockLLM>("Response");
    auto caps = mock_llm->capabilities();

    EXPECT_EQ(4, caps.size());
    EXPECT_EQ("text-generation", caps[0]);
    EXPECT_EQ("chat", caps[1]);
    EXPECT_EQ("mock", caps[2]);
    EXPECT_EQ("testing", caps[3]);
}
