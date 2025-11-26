/**
 * @file test_integration.cpp
 * @brief Integration tests for end-to-end scenarios
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/transports/http_agent.hpp"
#include "agenkit/transports/http_server.hpp"
#include <thread>
#include <chrono>

using namespace agenkit;

/**
 * Integration test: Full message roundtrip
 * Tests serialization, deserialization, and agent processing
 */
TEST(IntegrationTest, MessageRoundtrip) {
    // Create message with metadata
    auto original = core::Message::with_text("user", "Test message");
    original.with_metadata("key1", "value1")
           .with_metadata("key2", 42)
           .with_metadata("key3", nlohmann::json::array({"a", "b", "c"}));

    // Serialize to JSON
    auto json = original.to_json();

    // Deserialize from JSON
    auto deserialized = core::Message::from_json(json);

    // Verify content preserved
    EXPECT_EQ(deserialized.role(), "user");
    EXPECT_EQ(deserialized.content_as_str(), "Test message");
    EXPECT_EQ(deserialized.metadata()["key1"], "value1");
    EXPECT_EQ(deserialized.metadata()["key2"], 42);
    EXPECT_EQ(deserialized.metadata()["key3"][0], "a");
}

/**
 * Integration test: Agent chain
 * Tests composing multiple agents together
 */
TEST(IntegrationTest, AgentChain) {
    adapters::EchoAgent agent1;
    adapters::EchoAgent agent2;

    // Process through first agent
    auto msg1 = core::Message::with_text("user", "Hello");
    auto future1 = agent1.process(std::move(msg1));
    auto result1 = future1.get();

    ASSERT_TRUE(result1.is_ok());
    auto response1 = result1.unwrap();

    // Process response through second agent
    auto future2 = agent2.process(std::move(response1));
    auto result2 = future2.get();

    ASSERT_TRUE(result2.is_ok());
    auto response2 = result2.unwrap();

    // Verify final response
    EXPECT_EQ(response2.role(), "assistant");
    EXPECT_EQ(response2.content_as_str(), "Hello");
}

/**
 * Integration test: HTTP transport with metadata
 * Tests HTTP roundtrip preserves metadata
 */
class HttpMetadataTest : public ::testing::Test {
protected:
    void SetUp() override {
        agent_ = std::make_shared<adapters::EchoAgent>();
        server_ = std::make_unique<transports::HttpServer>(
            agent_,
            "127.0.0.1:18081"
        );

        server_thread_ = std::thread([this]() {
            server_->serve();
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    void TearDown() override {
        if (server_) {
            server_->stop();
        }
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

    std::shared_ptr<adapters::EchoAgent> agent_;
    std::unique_ptr<transports::HttpServer> server_;
    std::thread server_thread_;
};

TEST_F(HttpMetadataTest, MetadataPreserved) {
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18081",
        5,
        std::nullopt
    };

    transports::HttpAgent client("test", config);

    // Create message with rich metadata
    auto msg = core::Message::with_text("user", "Test");
    msg.with_metadata("session_id", "abc123")
       .with_metadata("priority", 5)
       .with_metadata("tags", nlohmann::json::array({"important", "test"}));

    auto future = client.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Verify metadata was preserved
    EXPECT_EQ(response.metadata()["session_id"], "abc123");
    EXPECT_EQ(response.metadata()["priority"], 5);
    EXPECT_EQ(response.metadata()["tags"][0], "important");
}

/**
 * Integration test: Concurrent requests
 * Tests HTTP server handles multiple simultaneous requests
 */
class HttpConcurrencyTest : public ::testing::Test {
protected:
    void SetUp() override {
        agent_ = std::make_shared<adapters::EchoAgent>();
        server_ = std::make_unique<transports::HttpServer>(
            agent_,
            "127.0.0.1:18082"
        );

        server_thread_ = std::thread([this]() {
            server_->serve();
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    void TearDown() override {
        if (server_) {
            server_->stop();
        }
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

    std::shared_ptr<adapters::EchoAgent> agent_;
    std::unique_ptr<transports::HttpServer> server_;
    std::thread server_thread_;
};

TEST_F(HttpConcurrencyTest, ConcurrentRequests) {
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18082",
        10,
        std::nullopt
    };

    // Launch 5 concurrent client requests
    std::vector<std::thread> threads;
    std::vector<bool> results(5, false);

    for (int i = 0; i < 5; i++) {
        threads.emplace_back([i, &config, &results]() {
            transports::HttpAgent client("client-" + std::to_string(i), config);
            auto msg = core::Message::with_text("user", "Request " + std::to_string(i));
            auto future = client.process(std::move(msg));
            auto result = future.get();
            results[i] = result.is_ok();
        });
    }

    // Wait for all threads
    for (auto& t : threads) {
        t.join();
    }

    // Verify all requests succeeded
    for (bool success : results) {
        EXPECT_TRUE(success);
    }
}

/**
 * Integration test: Error handling across layers
 * Tests errors propagate correctly through stack
 */
TEST(IntegrationTest, ErrorPropagation) {
    // Test invalid HTTP URL
    transports::HttpTransportConfig bad_config{
        "http://localhost:99999",  // Invalid port
        1,  // Short timeout
        std::nullopt
    };

    EXPECT_THROW(
        transports::HttpAgent("test", bad_config),
        std::invalid_argument
    );

    // Test connection error
    transports::HttpTransportConfig unreachable_config{
        "http://localhost:19999",  // Nothing listening
        1,
        std::nullopt
    };

    transports::HttpAgent client("test", unreachable_config);
    auto msg = core::Message::with_text("user", "Test");
    auto future = client.process(std::move(msg));
    auto result = future.get();

    // Should return error result (not throw)
    EXPECT_TRUE(result.is_err());
    if (result.is_err()) {
        auto error = result.unwrap_err();
        EXPECT_EQ(error.type(), core::AgentErrorType::Transport);
    }
}
