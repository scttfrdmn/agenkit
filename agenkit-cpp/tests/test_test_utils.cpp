/**
 * @file test_test_utils.cpp
 * @brief Tests for test utilities
 */

#include <gtest/gtest.h>
#include "test_utils.hpp"
#include <memory>

using namespace agenkit::test;
using namespace agenkit::core;

// Test MockAgent basic functionality
TEST(TestUtilsTest, MockAgentBasicFunctionality) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "Response 1",
        "Response 2"
    });

    EXPECT_EQ(mock->name(), "mock_agent");

    // Test first response
    auto msg1 = Message::with_text("user", "Test 1");
    auto result1 = mock->process(std::move(msg1)).get();

    ASSERT_TRUE(result1.is_ok());
    EXPECT_EQ(result1.unwrap().content_as_str(), "Response 1");
    EXPECT_EQ(mock->get_call_count(), 1);

    // Test second response
    auto msg2 = Message::with_text("user", "Test 2");
    auto result2 = mock->process(std::move(msg2)).get();

    ASSERT_TRUE(result2.is_ok());
    EXPECT_EQ(result2.unwrap().content_as_str(), "Response 2");
    EXPECT_EQ(mock->get_call_count(), 2);

    // Test cycling back to first response
    auto msg3 = Message::with_text("user", "Test 3");
    auto result3 = mock->process(std::move(msg3)).get();

    ASSERT_TRUE(result3.is_ok());
    EXPECT_EQ(result3.unwrap().content_as_str(), "Response 1");
    EXPECT_EQ(mock->get_call_count(), 3);
}

// Test MockAgent capabilities
TEST(TestUtilsTest, MockAgentCapabilities) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"Response"});

    auto caps = mock->capabilities();
    EXPECT_EQ(caps.size(), 2);
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "mock") != caps.end());
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "testing") != caps.end());
}

// Test MockAgent reset call count
TEST(TestUtilsTest, MockAgentResetCallCount) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"Response"});

    // Make some calls
    auto msg1 = Message::with_text("user", "Test 1");
    auto result1 = mock->process(std::move(msg1)).get();
    ASSERT_TRUE(result1.is_ok());

    EXPECT_EQ(mock->get_call_count(), 1);

    // Reset
    mock->reset_call_count();
    EXPECT_EQ(mock->get_call_count(), 0);
}

// Test MockAgent with empty responses (should add default)
TEST(TestUtilsTest, MockAgentEmptyResponses) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{});

    auto msg = Message::with_text("user", "Test");
    auto result = mock->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap().content_as_str(), "default_response");
}

// Test MockAgent with custom name
TEST(TestUtilsTest, MockAgentCustomName) {
    auto mock = std::make_shared<MockAgent>(
        std::vector<std::string>{"Response"},
        "custom_mock"
    );

    EXPECT_EQ(mock->name(), "custom_mock");
}

// Test FailingMockAgent returns error
TEST(TestUtilsTest, FailingMockAgentReturnsError) {
    auto failing = std::make_shared<FailingMockAgent>(
        AgentErrorType::ProcessingError,
        "Simulated failure"
    );

    EXPECT_EQ(failing->name(), "failing_mock_agent");

    auto msg = Message::with_text("user", "Test");
    auto result = failing->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), AgentErrorType::ProcessingError);
    EXPECT_EQ(result.unwrap_err().message(), "Simulated failure");
}

// Test FailingMockAgent with different error types
TEST(TestUtilsTest, FailingMockAgentDifferentErrorTypes) {
    auto timeout = std::make_shared<FailingMockAgent>(
        AgentErrorType::Timeout,
        "Operation timed out"
    );

    auto msg = Message::with_text("user", "Test");
    auto result = timeout->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err().type(), AgentErrorType::Timeout);
    EXPECT_EQ(result.unwrap_err().message(), "Operation timed out");
}

// Test FailingMockAgent capabilities
TEST(TestUtilsTest, FailingMockAgentCapabilities) {
    auto failing = std::make_shared<FailingMockAgent>(
        AgentErrorType::ProcessingError,
        "Error"
    );

    auto caps = failing->capabilities();
    EXPECT_EQ(caps.size(), 2);
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "failing") != caps.end());
    EXPECT_TRUE(std::find(caps.begin(), caps.end(), "testing") != caps.end());
}

// Test MockAgent introspection
TEST(TestUtilsTest, MockAgentIntrospection) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"R1", "R2"});

    std::string info = mock->introspect();
    EXPECT_TRUE(info.find("MockAgent") != std::string::npos);
    EXPECT_TRUE(info.find("responses=2") != std::string::npos);
}

// Test FailingMockAgent introspection
TEST(TestUtilsTest, FailingMockAgentIntrospection) {
    auto failing = std::make_shared<FailingMockAgent>(
        AgentErrorType::ProcessingError,
        "Test error"
    );

    std::string info = failing->introspect();
    EXPECT_TRUE(info.find("FailingMockAgent") != std::string::npos);
    EXPECT_TRUE(info.find("ProcessingError") != std::string::npos);
}
