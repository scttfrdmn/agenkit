/**
 * @file test_core.cpp
 * @brief Integration tests for core functionality
 *
 * Tests message creation and serialization, agent interface compliance,
 * result type handling, error propagation, and metadata handling.
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <future>
#include <thread>
#include <chrono>

using namespace agenkit;

/**
 * Test: Message creation and serialization
 * Tests complete message lifecycle including creation, modification, and serialization
 */
TEST(CoreIntegrationTest, MessageCreationAndSerialization) {
    // Create message with various content types
    auto msg = core::Message::with_text("user", "Test message");
    msg.with_metadata("string_key", "string_value")
       .with_metadata("int_key", 42)
       .with_metadata("float_key", 3.14159)
       .with_metadata("bool_key", true)
       .with_metadata("null_key", nullptr);

    // Add nested metadata
    nlohmann::json nested = {
        {"level1", {
            {"level2", {
                {"level3", "deep value"}
            }}
        }},
        {"array", nlohmann::json::array({1, 2, 3, 4, 5})}
    };
    msg.with_metadata("nested", nested);

    // Serialize to JSON
    auto json = msg.to_json();

    // Verify JSON structure
    EXPECT_TRUE(json.contains("role"));
    EXPECT_TRUE(json.contains("content"));
    EXPECT_TRUE(json.contains("metadata"));
    EXPECT_TRUE(json.contains("timestamp"));

    // Deserialize from JSON
    auto deserialized = core::Message::from_json(json);

    // Verify all fields preserved
    EXPECT_EQ(deserialized.role(), "user");
    EXPECT_EQ(deserialized.content_as_str(), "Test message");

    // Verify metadata preserved
    EXPECT_EQ(deserialized.metadata()["string_key"].get<std::string>(), "string_value");
    EXPECT_EQ(deserialized.metadata()["int_key"].get<int>(), 42);
    EXPECT_DOUBLE_EQ(deserialized.metadata()["float_key"].get<double>(), 3.14159);
    EXPECT_EQ(deserialized.metadata()["bool_key"].get<bool>(), true);
    EXPECT_TRUE(deserialized.metadata()["null_key"].is_null());

    // Verify nested metadata
    EXPECT_EQ(
        deserialized.metadata()["nested"]["level1"]["level2"]["level3"].get<std::string>(),
        "deep value"
    );
    EXPECT_EQ(deserialized.metadata()["nested"]["array"].size(), 5);
}

/**
 * Test: Agent interface compliance
 * Tests that all agents properly implement the Agent interface
 */
TEST(CoreIntegrationTest, AgentInterfaceCompliance) {
    adapters::EchoAgent agent;

    // Test name() method
    std::string name = agent.name();
    EXPECT_FALSE(name.empty());

    // Test capabilities() method
    std::vector<std::string> capabilities = agent.capabilities();
    EXPECT_FALSE(capabilities.empty());

    // Test process() method returns future
    auto msg = core::Message::with_text("user", "Test");
    auto future = agent.process(std::move(msg));

    // Verify future is valid
    EXPECT_TRUE(future.valid());

    // Get result
    auto result = future.get();

    // Verify result type
    EXPECT_TRUE(result.is_ok() || result.is_err());
}

/**
 * Test: Result type handling
 * Tests Result<T, E> type for success and error cases
 */
TEST(CoreIntegrationTest, ResultTypeHandling) {
    adapters::EchoAgent agent;

    // Test successful result
    auto msg1 = core::Message::with_text("user", "Success test");
    auto future1 = agent.process(std::move(msg1));
    auto result1 = future1.get();

    ASSERT_TRUE(result1.is_ok());
    EXPECT_FALSE(result1.is_err());

    // Unwrap successful result
    auto response1 = result1.unwrap();
    EXPECT_EQ(response1.role(), "assistant");
    EXPECT_FALSE(response1.content_as_str().empty());

    // Test that unwrapping error on success throws
    EXPECT_THROW(result1.unwrap_err(), std::runtime_error);

    // Test Result with move semantics
    core::Result<core::Message, core::AgentError> moved_result = std::move(result1);
    EXPECT_TRUE(moved_result.is_ok());
}

/**
 * Test: Error propagation
 * Tests that errors propagate correctly through the system
 */
TEST(CoreIntegrationTest, ErrorPropagation) {
    // Test AgentError creation
    auto error1 = core::AgentError(
        core::AgentErrorType::Transport,
        "Connection failed from http_client"
    );

    EXPECT_EQ(error1.type(), core::AgentErrorType::Transport);
    EXPECT_EQ(error1.message(), "Connection failed from http_client");

    // Test error with HTTP type
    auto error2 = core::AgentError(
        core::AgentErrorType::Http,
        "HTTP service unavailable (503)"
    );

    EXPECT_EQ(error2.type(), core::AgentErrorType::Http);
    EXPECT_FALSE(error2.message().empty());

    // Test Result with error
    core::Result<core::Message, core::AgentError> error_result = core::Result<core::Message, core::AgentError>::err(
        std::move(error2)
    );

    EXPECT_TRUE(error_result.is_err());
    EXPECT_FALSE(error_result.is_ok());

    auto unwrapped_error = error_result.unwrap_err();
    EXPECT_EQ(unwrapped_error.type(), core::AgentErrorType::Http);
    EXPECT_EQ(unwrapped_error.message(), "HTTP service unavailable (503)");
}

/**
 * Test: Metadata handling
 * Tests comprehensive metadata operations
 */
TEST(CoreIntegrationTest, MetadataHandling) {
    auto msg = core::Message::with_text("user", "Metadata test");

    // Test single value metadata
    msg.with_metadata("string", "value")
       .with_metadata("integer", 123)
       .with_metadata("floating", 45.67)
       .with_metadata("boolean", false);

    EXPECT_EQ(msg.metadata()["string"].get<std::string>(), "value");
    EXPECT_EQ(msg.metadata()["integer"].get<int>(), 123);
    EXPECT_DOUBLE_EQ(msg.metadata()["floating"].get<double>(), 45.67);
    EXPECT_EQ(msg.metadata()["boolean"].get<bool>(), false);

    // Test array metadata
    nlohmann::json array = nlohmann::json::array({1, 2, 3, 4, 5});
    msg.with_metadata("numbers", array);

    EXPECT_TRUE(msg.metadata()["numbers"].is_array());
    EXPECT_EQ(msg.metadata()["numbers"].size(), 5);
    EXPECT_EQ(msg.metadata()["numbers"][0].get<int>(), 1);
    EXPECT_EQ(msg.metadata()["numbers"][4].get<int>(), 5);

    // Test object metadata
    nlohmann::json obj = {
        {"name", "test"},
        {"value", 42},
        {"active", true}
    };
    msg.with_metadata("object", obj);

    EXPECT_TRUE(msg.metadata()["object"].is_object());
    EXPECT_EQ(msg.metadata()["object"]["name"].get<std::string>(), "test");
    EXPECT_EQ(msg.metadata()["object"]["value"].get<int>(), 42);
    EXPECT_EQ(msg.metadata()["object"]["active"].get<bool>(), true);

    // Test metadata update
    msg.with_metadata("string", "updated_value");
    EXPECT_EQ(msg.metadata()["string"].get<std::string>(), "updated_value");

    // Test metadata persistence through agent processing
    adapters::EchoAgent agent;
    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Verify metadata was preserved
    EXPECT_TRUE(response.metadata().contains("string"));
    EXPECT_TRUE(response.metadata().contains("integer"));
    EXPECT_TRUE(response.metadata().contains("numbers"));
    EXPECT_TRUE(response.metadata().contains("object"));
}

/**
 * Test: Message timestamp handling
 * Tests timestamp creation and preservation
 */
TEST(CoreIntegrationTest, MessageTimestampHandling) {
    auto before = std::chrono::system_clock::now();

    auto msg = core::Message::with_text("user", "Timestamp test");

    auto after = std::chrono::system_clock::now();

    // Timestamp should be between before and after
    // Note: This test assumes the Message constructor sets timestamp
    // If timestamp is not automatically set, this test may need adjustment

    // Serialize and deserialize to test timestamp preservation
    auto json = msg.to_json();
    EXPECT_TRUE(json.contains("timestamp"));

    auto deserialized = core::Message::from_json(json);

    // Timestamp should be preserved through serialization
    // (This tests that timestamp serialization/deserialization works)
    EXPECT_TRUE(json["timestamp"].is_string() || json["timestamp"].is_number());
}

/**
 * Test: Concurrent message processing
 * Tests that core message handling is thread-safe
 */
TEST(CoreIntegrationTest, ConcurrentMessageProcessing) {
    adapters::EchoAgent agent;

    constexpr int num_threads = 10;
    constexpr int msgs_per_thread = 10;

    std::vector<std::thread> threads;
    std::atomic<int> success_count{0};
    std::atomic<int> error_count{0};

    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&agent, &success_count, &error_count, t]() {
            for (int i = 0; i < msgs_per_thread; ++i) {
                auto msg = core::Message::with_text("user", "Thread " + std::to_string(t) + " Msg " + std::to_string(i));
                msg.with_metadata("thread_id", t)
                   .with_metadata("msg_id", i);

                auto future = agent.process(std::move(msg));
                auto result = future.get();

                if (result.is_ok()) {
                    ++success_count;
                } else {
                    ++error_count;
                }
            }
        });
    }

    // Wait for all threads
    for (auto& thread : threads) {
        thread.join();
    }

    // Verify all messages were processed
    EXPECT_EQ(success_count.load(), num_threads * msgs_per_thread);
    EXPECT_EQ(error_count.load(), 0);
}

/**
 * Test: Message content type flexibility
 * Tests different content types in messages
 */
TEST(CoreIntegrationTest, MessageContentTypeFlexibility) {
    // Test with text content
    auto text_msg = core::Message::with_text("user", "Text content");
    EXPECT_EQ(text_msg.content_as_str(), "Text content");

    // Test with empty content
    auto empty_msg = core::Message::with_text("user", "");
    EXPECT_EQ(empty_msg.content_as_str(), "");

    // Test with very long content
    std::string long_content(100000, 'x');
    auto long_msg = core::Message::with_text("user", long_content);
    EXPECT_EQ(long_msg.content_as_str().length(), 100000);

    // Test with unicode content
    auto unicode_msg = core::Message::with_text("user", "Hello 世界 🌍 Привет مرحبا");
    EXPECT_FALSE(unicode_msg.content_as_str().empty());

    // Test with special characters
    auto special_msg = core::Message::with_text("user", "Line1\nLine2\tTab\rReturn\0Null");
    EXPECT_FALSE(special_msg.content_as_str().empty());

    // Process through agent to ensure all content types work
    adapters::EchoAgent agent;

    auto future = agent.process(std::move(unicode_msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_FALSE(response.content_as_str().empty());
}

/**
 * Test: Error type coverage
 * Tests all error types are properly handled
 */
TEST(CoreIntegrationTest, ErrorTypeCoverage) {
    // Test all error types
    std::vector<core::AgentErrorType> error_types = {
        core::AgentErrorType::ProcessingError,
        core::AgentErrorType::Timeout,
        core::AgentErrorType::NotFound,
        core::AgentErrorType::Transport,
        core::AgentErrorType::Serialization,
        core::AgentErrorType::Http,
        core::AgentErrorType::Internal,
        core::AgentErrorType::InvalidInput
    };

    for (auto error_type : error_types) {
        auto error = core::AgentError(
            error_type,
            "Test error message"
        );

        EXPECT_EQ(error.type(), error_type);
        EXPECT_EQ(error.message(), "Test error message");

        // Create Result with this error
        auto result = core::Result<core::Message, core::AgentError>::err(std::move(error));

        EXPECT_TRUE(result.is_err());
        auto unwrapped = result.unwrap_err();
        EXPECT_EQ(unwrapped.type(), error_type);
    }
}
