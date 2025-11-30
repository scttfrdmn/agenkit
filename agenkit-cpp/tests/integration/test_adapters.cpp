/**
 * @file test_adapters.cpp
 * @brief Integration tests for adapter implementations
 *
 * Tests real adapter functionality including OpenAI, Anthropic, Ollama,
 * and error handling. Some tests require API keys or services to be available.
 */

#include <gtest/gtest.h>
#include "agenkit/core/message.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/adapters/ollama_agent.hpp"
#include <cstdlib>
#include <string>

using namespace agenkit;

/**
 * Test: Echo adapter integration
 * Verifies echo adapter works correctly for basic message passing
 */
TEST(AdapterIntegrationTest, EchoAdapter) {
    adapters::EchoAgent agent;

    EXPECT_EQ(agent.name(), "echo");
    EXPECT_FALSE(agent.capabilities().empty());

    auto msg = core::Message::with_text("user", "Test message");
    msg.with_metadata("test_id", "echo_001");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_EQ(response.content_as_str(), "Test message");
    EXPECT_TRUE(response.metadata().contains("test_id"));
}

/**
 * Test: OpenAI adapter integration
 * Tests OpenAI adapter with real API (requires OPENAI_API_KEY)
 */
TEST(AdapterIntegrationTest, OpenAIAdapter) {
    const char* api_key = std::getenv("OPENAI_API_KEY");
    if (!api_key || std::string(api_key).empty()) {
        GTEST_SKIP() << "OPENAI_API_KEY not set, skipping OpenAI integration test";
    }

    adapters::OpenAIConfig config;
    config.api_key = api_key;
    config.model = "gpt-4o-mini";
    config.temperature = 1.0;
    config.max_tokens = 1024;
    config.timeout_seconds = 30;

    adapters::OpenAIAgent agent(config);

    EXPECT_EQ(agent.name(), "openai-gpt-4o-mini");
    EXPECT_FALSE(agent.capabilities().empty());

    auto msg = core::Message::with_text("user", "Say 'test passed' and nothing else");
    msg.with_metadata("test_type", "integration");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok()) << "OpenAI API call failed";
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Anthropic/Claude adapter integration
 * Tests Claude adapter with real API (requires ANTHROPIC_API_KEY)
 */
TEST(AdapterIntegrationTest, AnthropicAdapter) {
    const char* api_key = std::getenv("ANTHROPIC_API_KEY");
    if (!api_key || std::string(api_key).empty()) {
        GTEST_SKIP() << "ANTHROPIC_API_KEY not set, skipping Anthropic integration test";
    }

    adapters::ClaudeConfig config;
    config.api_key = api_key;
    config.model = "claude-3-5-sonnet-20241022";
    config.max_tokens = 1024;
    config.timeout_seconds = 30;

    adapters::ClaudeAgent agent(config);

    EXPECT_EQ(agent.name(), "claude-claude-3-5-sonnet-20241022");
    EXPECT_FALSE(agent.capabilities().empty());

    auto msg = core::Message::with_text("user", "Say 'test passed' and nothing else");
    msg.with_metadata("test_type", "integration")
       .with_metadata("model", "claude");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok()) << "Claude API call failed";
    auto response = result.unwrap();

    EXPECT_EQ(response.role(), "assistant");
    EXPECT_FALSE(response.content_as_str().empty());
    EXPECT_TRUE(response.metadata().contains("test_type"));
}

/**
 * Test: Ollama adapter integration
 * Tests Ollama adapter with local service (requires Ollama running)
 */
TEST(AdapterIntegrationTest, OllamaAdapter) {
    const char* skip_ollama = std::getenv("SKIP_OLLAMA_TESTS");
    if (skip_ollama && std::string(skip_ollama) == "1") {
        GTEST_SKIP() << "SKIP_OLLAMA_TESTS=1, skipping Ollama integration test";
    }

    adapters::OllamaConfig config;
    config.model = "llama3.2:1b";
    config.host = "http://localhost:11434";
    config.temperature = 1.0;
    config.timeout_seconds = 30;

    adapters::OllamaAgent agent(config);

    EXPECT_EQ(agent.name(), "ollama-llama3.2:1b");
    EXPECT_FALSE(agent.capabilities().empty());

    auto msg = core::Message::with_text("user", "Say 'test passed' and nothing else");
    msg.with_metadata("test_type", "integration")
       .with_metadata("service", "ollama");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    // Ollama might not be running, so we accept both success and transport error
    if (result.is_ok()) {
        auto response = result.unwrap();
        EXPECT_EQ(response.role(), "assistant");
        EXPECT_FALSE(response.content_as_str().empty());
    } else {
        auto error = result.unwrap_err();
        EXPECT_EQ(error.type(), core::AgentErrorType::Transport);
        GTEST_SKIP() << "Ollama service not available: " << error.message();
    }
}

/**
 * Test: Adapter error handling - Invalid API key
 * Tests that adapters properly handle authentication errors
 */
TEST(AdapterIntegrationTest, InvalidAPIKeyHandling) {
    adapters::OpenAIConfig config;
    config.api_key = "invalid_key_12345";  // Invalid API key
    config.model = "gpt-4o-mini";
    config.temperature = 1.0;
    config.max_tokens = 1024;
    config.timeout_seconds = 5;  // Short timeout for faster test

    adapters::OpenAIAgent agent(config);

    auto msg = core::Message::with_text("user", "Test");
    auto future = agent.process(std::move(msg));
    auto result = future.get();

    // Should return error result, not throw
    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();

    // Should be either HTTP or transport error (no Authentication type in current impl)
    EXPECT_TRUE(
        error.type() == core::AgentErrorType::Http ||
        error.type() == core::AgentErrorType::Transport
    );
    EXPECT_FALSE(error.message().empty());
}

/**
 * Test: Adapter error handling - Network timeout
 * Tests that adapters handle timeout scenarios properly
 */
TEST(AdapterIntegrationTest, TimeoutHandling) {
    adapters::OpenAIConfig config;
    config.api_key = "sk-test";  // Will fail before reaching actual API
    config.model = "gpt-4o-mini";
    config.api_base = "http://192.0.2.1:9999";  // Non-routable address (TEST-NET-1)
    config.temperature = 1.0;
    config.max_tokens = 1024;
    config.timeout_seconds = 1;  // Very short timeout

    adapters::OpenAIAgent agent(config);

    auto msg = core::Message::with_text("user", "Test");
    auto future = agent.process(std::move(msg));
    auto result = future.get();

    // Should return transport error
    ASSERT_TRUE(result.is_err());
    auto error = result.unwrap_err();

    EXPECT_EQ(error.type(), core::AgentErrorType::Transport);
    EXPECT_FALSE(error.message().empty());
}

/**
 * Test: Adapter metadata preservation
 * Tests that all adapters preserve metadata through processing
 */
TEST(AdapterIntegrationTest, MetadataPreservation) {
    adapters::EchoAgent agent;

    auto msg = core::Message::with_text("user", "Test");
    msg.with_metadata("trace_id", "test-123")
       .with_metadata("session_id", "session-456")
       .with_metadata("priority", 5)
       .with_metadata("tags", nlohmann::json::array({"integration", "test"}));

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    // Verify all metadata was preserved
    EXPECT_TRUE(response.metadata().contains("trace_id"));
    EXPECT_EQ(response.metadata()["trace_id"].get<std::string>(), "test-123");
    EXPECT_TRUE(response.metadata().contains("session_id"));
    EXPECT_EQ(response.metadata()["session_id"].get<std::string>(), "session-456");
    EXPECT_TRUE(response.metadata().contains("priority"));
    EXPECT_EQ(response.metadata()["priority"].get<int>(), 5);
    EXPECT_TRUE(response.metadata().contains("tags"));
    EXPECT_TRUE(response.metadata()["tags"].is_array());
}

/**
 * Test: Adapter with complex message content
 * Tests adapters handle complex, multi-part messages
 */
TEST(AdapterIntegrationTest, ComplexMessageContent) {
    adapters::EchoAgent agent;

    // Create message with complex content
    std::string complex_content =
        "This is a test with:\n"
        "- Multiple lines\n"
        "- Special chars: !@#$%^&*()\n"
        "- Unicode: Hello 世界 🌍\n"
        "- Numbers: 123.456\n"
        "- JSON-like: {\"key\": \"value\"}";

    auto msg = core::Message::with_text("user", complex_content);
    msg.with_metadata("content_type", "complex");

    auto future = agent.process(std::move(msg));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();

    EXPECT_EQ(response.content_as_str(), complex_content);
    EXPECT_TRUE(response.metadata().contains("content_type"));
}

/**
 * Test: Adapter concurrent requests
 * Tests that adapters can handle multiple concurrent requests
 */
TEST(AdapterIntegrationTest, ConcurrentRequests) {
    adapters::EchoAgent agent;

    constexpr int num_requests = 10;
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;

    // Launch concurrent requests
    for (int i = 0; i < num_requests; ++i) {
        auto msg = core::Message::with_text("user", "Request " + std::to_string(i));
        msg.with_metadata("request_id", i);
        futures.push_back(agent.process(std::move(msg)));
    }

    // Collect results
    int success_count = 0;
    for (auto& future : futures) {
        auto result = future.get();
        if (result.is_ok()) {
            ++success_count;
            auto response = result.unwrap();
            EXPECT_TRUE(response.metadata().contains("request_id"));
        }
    }

    EXPECT_EQ(success_count, num_requests);
}
