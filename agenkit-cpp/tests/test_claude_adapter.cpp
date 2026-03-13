/**
 * @file test_claude_adapter.cpp
 * @brief Tests for Anthropic Claude adapter
 *
 * Tests constructor, configuration, capabilities, and config validation.
 * HTTP call tests require a running mock server (integration tests).
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit::core;
using namespace agenkit::adapters;

// Test default configuration values
TEST(ClaudeAgentTest, DefaultConfigModel) {
    ClaudeConfig config;
    config.api_key = "test-key";
    EXPECT_EQ(config.model, "claude-sonnet-4-6");
}

TEST(ClaudeAgentTest, DefaultConfigMaxTokens) {
    ClaudeConfig config;
    EXPECT_EQ(config.max_tokens, 4096);
}

TEST(ClaudeAgentTest, DefaultConfigTemperature) {
    ClaudeConfig config;
    EXPECT_DOUBLE_EQ(config.temperature, 1.0);
}

TEST(ClaudeAgentTest, DefaultConfigApiBase) {
    ClaudeConfig config;
    EXPECT_EQ(config.api_base, "https://api.anthropic.com");
}

TEST(ClaudeAgentTest, DefaultConfigApiVersion) {
    ClaudeConfig config;
    EXPECT_EQ(config.api_version, "2023-06-01");
}

// Test agent construction
TEST(ClaudeAgentTest, ConstructorBasic) {
    ClaudeConfig config;
    config.api_key = "test-key";
    EXPECT_NO_THROW({
        ClaudeAgent agent(config);
    });
}

// Test agent name
TEST(ClaudeAgentTest, AgentName) {
    ClaudeConfig config;
    config.api_key = "test-key";
    ClaudeAgent agent(config);
    EXPECT_EQ(agent.name(), "claude");
}

// Test agent capabilities
TEST(ClaudeAgentTest, AgentCapabilities) {
    ClaudeConfig config;
    config.api_key = "test-key";
    ClaudeAgent agent(config);
    auto caps = agent.capabilities();
    EXPECT_FALSE(caps.empty());

    bool has_llm = false;
    bool has_claude = false;
    for (const auto& cap : caps) {
        if (cap == "llm") has_llm = true;
        if (cap == "claude" || cap == "anthropic") has_claude = true;
    }
    EXPECT_TRUE(has_llm);
    EXPECT_TRUE(has_claude);
}

// Test config access
TEST(ClaudeAgentTest, ConfigAccess) {
    ClaudeConfig config;
    config.api_key = "test-key";
    config.model = "claude-sonnet-4-6";
    config.max_tokens = 2048;
    ClaudeAgent agent(config);

    const auto& retrieved = agent.config();
    EXPECT_EQ(retrieved.model, "claude-sonnet-4-6");
    EXPECT_EQ(retrieved.max_tokens, 2048);
}

// Test set_config updates configuration
TEST(ClaudeAgentTest, SetConfig) {
    ClaudeConfig config;
    config.api_key = "test-key";
    ClaudeAgent agent(config);

    ClaudeConfig new_config;
    new_config.api_key = "test-key";
    new_config.max_tokens = 8192;
    agent.set_config(new_config);

    EXPECT_EQ(agent.config().max_tokens, 8192);
}

// Test constructor throws on empty API key
TEST(ClaudeAgentTest, EmptyApiKeyThrows) {
    ClaudeConfig config;
    config.api_key = "";
    EXPECT_THROW(ClaudeAgent agent(config), std::invalid_argument);
}

// Test custom model string
TEST(ClaudeAgentTest, CustomModel) {
    ClaudeConfig config;
    config.api_key = "test-key";
    config.model = "claude-opus-4-6";
    EXPECT_NO_THROW({
        ClaudeAgent agent(config);
        EXPECT_EQ(agent.config().model, "claude-opus-4-6");
    });
}

// Test message content access
TEST(ClaudeAgentTest, MessageWithText) {
    auto msg = Message::with_text("user", "Hello, Claude!");
    EXPECT_EQ(msg.role, "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, Claude!");
}
