/**
 * @file test_cross_language.cpp
 * @brief Integration tests for cross-language compatibility
 *
 * Tests HTTP transport, JSON message format, gRPC (if available),
 * WebSocket (if available), and streaming compatibility with Python/Go/TypeScript.
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/transports/http_agent.hpp"
#include "agenkit/transports/http_server.hpp"
#include <thread>
#include <chrono>
#include <memory>

using namespace agenkit;

/**
 * Test: HTTP transport compatibility
 * Tests that C++ HTTP transport is compatible with other languages
 */
TEST(CrossLanguageTest, HTTPTransportCompatibility) {
    // Start HTTP server
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto server = std::make_unique<transports::HttpServer>(
        agent,
        "127.0.0.1:18090"
    );

    std::thread server_thread([&server]() {
        server->serve();
    });

    // Give server time to start
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // Create HTTP client
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18090",
        10,
        std::nullopt
    };

    transports::HttpAgent client("cpp-client", config);

    // Send message with metadata that other languages should understand
    auto msg = core::Message::with_text("user", "Cross-language test");
    msg.with_metadata("language", "cpp")
       .with_metadata("test_id", "cross-lang-001")
       .with_metadata("protocol", "http")
       .with_metadata("version", "1.0");

    auto future = client.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Verify response
    EXPECT_EQ(response.role(), "assistant");
    EXPECT_EQ(response.content_as_str(), "Cross-language test");

    // Verify metadata preserved
    EXPECT_TRUE(response.metadata().contains("language"));
    EXPECT_TRUE(response.metadata().contains("test_id"));
    EXPECT_TRUE(response.metadata().contains("protocol"));

    // Cleanup
    server->stop();
    if (server_thread.joinable()) {
        server_thread.join();
    }
}

/**
 * Test: JSON message format compatibility
 * Tests that JSON messages are compatible across languages
 */
TEST(CrossLanguageTest, JSONMessageFormatCompatibility) {
    // Create a message with all field types
    auto msg = core::Message::with_text("user", "JSON compatibility test");
    msg.with_metadata("string", "value")
       .with_metadata("integer", 42)
       .with_metadata("float", 3.14159)
       .with_metadata("boolean", true)
       .with_metadata("null_value", nullptr);

    // Add array
    nlohmann::json array = nlohmann::json::array({1, 2, 3});
    msg.with_metadata("array", array);

    // Add nested object
    nlohmann::json nested = {
        {"nested_key", "nested_value"},
        {"nested_num", 123}
    };
    msg.with_metadata("nested", nested);

    // Serialize to JSON
    auto json = msg.to_json();

    // Verify JSON structure matches expected format
    EXPECT_TRUE(json.contains("role"));
    EXPECT_TRUE(json.contains("content"));
    EXPECT_TRUE(json.contains("metadata"));
    EXPECT_TRUE(json.contains("timestamp"));

    // Verify role is string
    EXPECT_TRUE(json["role"].is_string());
    EXPECT_EQ(json["role"].get<std::string>(), "user");

    // Verify content is string or object
    EXPECT_TRUE(json["content"].is_string() || json["content"].is_object());

    // Verify metadata is object
    EXPECT_TRUE(json["metadata"].is_object());

    // Verify timestamp is string (ISO format) or number
    EXPECT_TRUE(json["timestamp"].is_string() || json["timestamp"].is_number());

    // Verify all metadata types
    EXPECT_EQ(json["metadata"]["string"].get<std::string>(), "value");
    EXPECT_EQ(json["metadata"]["integer"].get<int>(), 42);
    EXPECT_DOUBLE_EQ(json["metadata"]["float"].get<double>(), 3.14159);
    EXPECT_EQ(json["metadata"]["boolean"].get<bool>(), true);
    EXPECT_TRUE(json["metadata"]["null_value"].is_null());
    EXPECT_TRUE(json["metadata"]["array"].is_array());
    EXPECT_TRUE(json["metadata"]["nested"].is_object());

    // Test deserialization from JSON (simulating message from another language)
    nlohmann::json external_json = {
        {"role", "assistant"},
        {"content", "Response from Python/Go/TypeScript"},
        {"metadata", {
            {"language", "external"},
            {"timestamp_ms", 1234567890}
        }},
        {"timestamp", "2024-01-01T12:00:00Z"}
    };

    auto deserialized = core::Message::from_json(external_json);

    EXPECT_EQ(deserialized.role(), "assistant");
    EXPECT_EQ(deserialized.content_as_str(), "Response from Python/Go/TypeScript");
    EXPECT_TRUE(deserialized.metadata().contains("language"));
    EXPECT_EQ(deserialized.metadata()["language"].get<std::string>(), "external");
}

/**
 * Test: HTTP error handling compatibility
 * Tests that HTTP errors are handled consistently across languages
 */
TEST(CrossLanguageTest, HTTPErrorHandlingCompatibility) {
    // Test connection to non-existent server
    transports::HttpTransportConfig config{
        "http://127.0.0.1:19999",  // Port with no server
        2,  // Short timeout
        std::nullopt
    };

    transports::HttpAgent client("test-client", config);

    auto msg = core::Message::with_text("user", "Test");
    auto future = client.process(std::move(msg));
    auto result = future.get();

    // Should return error, not throw
    EXPECT_TRUE(result.is_err());

    if (result.is_err()) {
        auto error = result.unwrap_err();
        EXPECT_EQ(error.type(), core::AgentErrorType::Transport);
        EXPECT_FALSE(error.message().empty());
    }
}

/**
 * Test: Message size handling compatibility
 * Tests that large messages are handled consistently
 */
TEST(CrossLanguageTest, MessageSizeHandlingCompatibility) {
    // Start HTTP server
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto server = std::make_unique<transports::HttpServer>(
        agent,
        "127.0.0.1:18091"
    );

    std::thread server_thread([&server]() {
        server->serve();
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // Create HTTP client
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18091",
        30,  // Longer timeout for large message
        std::nullopt
    };

    transports::HttpAgent client("cpp-client", config);

    // Send large message (1MB of text)
    std::string large_content(1024 * 1024, 'x');  // 1MB
    auto msg = core::Message::with_text("user", large_content);
    msg.with_metadata("size_bytes", large_content.size())
       .with_metadata("test_type", "large_message");

    auto future = client.process(std::move(msg));
    auto result = future.get();

    // Should handle large message successfully
    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.content_as_str().size(), large_content.size());
    EXPECT_TRUE(response.metadata().contains("size_bytes"));

    // Cleanup
    server->stop();
    if (server_thread.joinable()) {
        server_thread.join();
    }
}

/**
 * Test: Streaming compatibility (if implemented)
 * Tests that streaming is compatible across languages
 */
TEST(CrossLanguageTest, StreamingCompatibility) {
    // Note: This test is a placeholder for when streaming is implemented
    // For now, we test that the system can handle sequential messages

    auto agent = std::make_shared<adapters::EchoAgent>();
    auto server = std::make_unique<transports::HttpServer>(
        agent,
        "127.0.0.1:18092"
    );

    std::thread server_thread([&server]() {
        server->serve();
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    transports::HttpTransportConfig config{
        "http://127.0.0.1:18092",
        10,
        std::nullopt
    };

    transports::HttpAgent client("streaming-client", config);

    // Send multiple messages in sequence (simulating stream)
    constexpr int num_messages = 10;
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;

    for (int i = 0; i < num_messages; ++i) {
        auto msg = core::Message::with_text("user", "Stream message " + std::to_string(i));
        msg.with_metadata("sequence", i)
           .with_metadata("stream_id", "test-stream-001");

        futures.push_back(client.process(std::move(msg)));
    }

    // Collect all responses
    int success_count = 0;
    for (auto& future : futures) {
        auto result = future.get();
        if (result.is_ok()) {
            ++success_count;
            auto response = result.unwrap();
            EXPECT_TRUE(response.metadata().contains("stream_id"));
        }
    }

    EXPECT_EQ(success_count, num_messages);

    // Cleanup
    server->stop();
    if (server_thread.joinable()) {
        server_thread.join();
    }
}

/**
 * Test: Unicode and special character compatibility
 * Tests that unicode and special characters work across languages
 */
TEST(CrossLanguageTest, UnicodeCompatibility) {
    // Start HTTP server
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto server = std::make_unique<transports::HttpServer>(
        agent,
        "127.0.0.1:18093"
    );

    std::thread server_thread([&server]() {
        server->serve();
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // Create HTTP client
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18093",
        10,
        std::nullopt
    };

    transports::HttpAgent client("unicode-client", config);

    // Test various unicode characters
    std::vector<std::string> unicode_tests = {
        "Hello 世界",           // Chinese
        "Привет мир",          // Russian
        "مرحبا بالعالم",       // Arabic
        "こんにちは世界",        // Japanese
        "🌍🌎🌏",              // Emojis
        "Ñoño España",         // Spanish
        "Ümlaut Grüß",         // German
        "café résumé",         // French
    };

    for (const auto& unicode_text : unicode_tests) {
        auto msg = core::Message::with_text("user", unicode_text);
        msg.with_metadata("original", unicode_text)
           .with_metadata("test_type", "unicode");

        auto future = client.process(std::move(msg));
        auto result = future.get();

        ASSERT_TRUE(result.is_ok()) << "Failed for: " << unicode_text;
        auto response = result.unwrap();

        EXPECT_EQ(response.content_as_str(), unicode_text);
        EXPECT_TRUE(response.metadata().contains("original"));
    }

    // Cleanup
    server->stop();
    if (server_thread.joinable()) {
        server_thread.join();
    }
}

/**
 * Test: Metadata type consistency
 * Tests that metadata types are preserved across language boundaries
 */
TEST(CrossLanguageTest, MetadataTypeConsistency) {
    // Create message with various metadata types
    auto msg = core::Message::with_text("user", "Type test");

    // Add all JSON types
    msg.with_metadata("string", "text")
       .with_metadata("integer", 42)
       .with_metadata("negative", -123)
       .with_metadata("float", 3.14159)
       .with_metadata("boolean_true", true)
       .with_metadata("boolean_false", false)
       .with_metadata("null", nullptr);

    // Add array with mixed types
    nlohmann::json mixed_array = nlohmann::json::array({
        1, "two", 3.0, true, nullptr
    });
    msg.with_metadata("mixed_array", mixed_array);

    // Add nested object
    nlohmann::json nested = {
        {"level1", {
            {"level2", {
                {"string", "value"},
                {"number", 42}
            }}
        }}
    };
    msg.with_metadata("nested", nested);

    // Serialize and deserialize (simulating cross-language transfer)
    auto json = msg.to_json();
    auto deserialized = core::Message::from_json(json);

    // Verify all types preserved
    EXPECT_EQ(deserialized.metadata()["string"].get<std::string>(), "text");
    EXPECT_EQ(deserialized.metadata()["integer"].get<int>(), 42);
    EXPECT_EQ(deserialized.metadata()["negative"].get<int>(), -123);
    EXPECT_DOUBLE_EQ(deserialized.metadata()["float"].get<double>(), 3.14159);
    EXPECT_EQ(deserialized.metadata()["boolean_true"].get<bool>(), true);
    EXPECT_EQ(deserialized.metadata()["boolean_false"].get<bool>(), false);
    EXPECT_TRUE(deserialized.metadata()["null"].is_null());
    EXPECT_TRUE(deserialized.metadata()["mixed_array"].is_array());
    EXPECT_TRUE(deserialized.metadata()["nested"].is_object());

    // Verify nested structure
    EXPECT_EQ(
        deserialized.metadata()["nested"]["level1"]["level2"]["string"].get<std::string>(),
        "value"
    );
}

/**
 * Test: Concurrent cross-language requests
 * Tests that concurrent requests work correctly over HTTP
 */
TEST(CrossLanguageTest, ConcurrentCrossLanguageRequests) {
    // Start HTTP server
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto server = std::make_unique<transports::HttpServer>(
        agent,
        "127.0.0.1:18094"
    );

    std::thread server_thread([&server]() {
        server->serve();
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    // Create HTTP client config
    transports::HttpTransportConfig config{
        "http://127.0.0.1:18094",
        10,
        std::nullopt
    };

    // Launch multiple concurrent clients
    constexpr int num_clients = 5;
    std::vector<std::thread> client_threads;
    std::atomic<int> success_count{0};
    std::atomic<int> error_count{0};

    for (int i = 0; i < num_clients; ++i) {
        client_threads.emplace_back([i, &config, &success_count, &error_count]() {
            transports::HttpAgent client("client-" + std::to_string(i), config);

            for (int j = 0; j < 5; ++j) {
                auto msg = core::Message::with_text("user", "Client " + std::to_string(i) + " Msg " + std::to_string(j));
                msg.with_metadata("client_id", i)
                   .with_metadata("msg_id", j);

                auto future = client.process(std::move(msg));
                auto result = future.get();

                if (result.is_ok()) {
                    ++success_count;
                } else {
                    ++error_count;
                }
            }
        });
    }

    // Wait for all clients
    for (auto& thread : client_threads) {
        thread.join();
    }

    // Verify all requests succeeded
    EXPECT_EQ(success_count.load(), num_clients * 5);
    EXPECT_EQ(error_count.load(), 0);

    // Cleanup
    server->stop();
    if (server_thread.joinable()) {
        server_thread.join();
    }
}
