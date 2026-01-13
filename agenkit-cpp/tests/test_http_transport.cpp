/**
 * @file test_http_transport.cpp
 * @brief Tests for HTTP transport (client and server)
 */

#include <gtest/gtest.h>
#include "agenkit/transports/http_agent.hpp"
#include "agenkit/transports/http_server.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <thread>
#include <chrono>

using namespace agenkit;

class HttpTransportTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create echo agent for server
        agent_ = std::make_shared<adapters::EchoAgent>();

        // Start server in background thread
        server_ = std::make_unique<transports::HttpServer>(
            agent_,
            "127.0.0.1:18080"  // Use non-standard port for testing
        );

        server_thread_ = std::thread([this]() {
            server_->serve();
        });

        // Wait for server to start
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    void TearDown() override {
        // Stop server and wait for thread
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

TEST_F(HttpTransportTest, ServerStarts) {
    // Server should be running after SetUp
    EXPECT_TRUE(server_->is_running());
}

TEST_F(HttpTransportTest, ClientSendsMessage) {
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18080",
        5,
        std::nullopt
    };

    transports::HttpAgent client("test-client", config);

    auto msg = core::Message::with_text("user", "Hello from client!");
    auto future = client.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_EQ(response.content_as_str(), "Hello from client!");
}

TEST_F(HttpTransportTest, ClientHasName) {
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18080",
        5,
        std::nullopt
    };

    transports::HttpAgent client("remote-agent", config);
    EXPECT_EQ(client.name(), "remote-agent");
}

TEST_F(HttpTransportTest, ClientHasCapabilities) {
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18080",
        5,
        std::nullopt
    };

    transports::HttpAgent client("test", config);
    auto caps = client.capabilities();

    EXPECT_GE(caps.size(), 1);
    EXPECT_EQ(caps[0], "http");
}

TEST_F(HttpTransportTest, ServerProcessesMultipleRequests) {
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18080",
        5,
        std::nullopt
    };

    transports::HttpAgent client("test", config);

    // Send multiple messages
    for (int i = 0; i < 5; i++) {
        auto msg = core::Message::with_text("user", "Message " + std::to_string(i));
        auto future = client.process(std::move(msg));
        auto result = future.get();

        ASSERT_TRUE(result.is_ok());
        EXPECT_EQ(result.unwrap().content_as_str(), "Message " + std::to_string(i));
    }
}

TEST_F(HttpTransportTest, ServerStopsCleanly) {
    EXPECT_TRUE(server_->is_running());

    server_->stop();

    // Wait a bit for server to stop
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    EXPECT_FALSE(server_->is_running());
}

TEST(HttpTransportConfigTest, InvalidUrlThrows) {
    transports::HttpTransportConfig config{
        "invalid-url",
        5,
        std::nullopt
    };

    EXPECT_THROW(
        transports::HttpAgent("test", config),
        std::invalid_argument
    );
}

TEST(HttpServerTest, InvalidAddressThrows) {
    auto agent = std::make_shared<adapters::EchoAgent>();

    EXPECT_THROW(
        transports::HttpServer(agent, "invalid"),
        std::invalid_argument
    );
}

TEST(HttpServerTest, InvalidPortThrows) {
    auto agent = std::make_shared<adapters::EchoAgent>();

    EXPECT_THROW(
        transports::HttpServer(agent, "127.0.0.1:99999"),
        std::invalid_argument
    );
}

TEST(HttpServerTest, NullAgentThrows) {
    EXPECT_THROW(
        transports::HttpServer(nullptr, "127.0.0.1:8080"),
        std::invalid_argument
    );
}

TEST(HttpClientTimeoutTest, ConnectionTimeout) {
    // Test connection timeout to non-routable address
    // Using 192.0.2.1 (TEST-NET-1, RFC 5737) which is non-routable
    transports::HttpTransportConfig config{
        "http://192.0.2.1:8080",
        1,  // 1 second timeout
        std::nullopt
    };

    transports::HttpAgent client("timeout-test", config);

    auto msg = core::Message::with_text("user", "test");
    auto start = std::chrono::steady_clock::now();
    auto future = client.process(std::move(msg));
    auto result = future.get();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::steady_clock::now() - start
    ).count();

    // Should timeout and fail
    EXPECT_FALSE(result.is_ok());

    // Should timeout within reasonable time (allow 2x timeout for overhead)
    EXPECT_LE(elapsed, 3);
}
