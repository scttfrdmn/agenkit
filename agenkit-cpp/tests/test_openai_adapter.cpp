/**
 * @file test_openai_adapter.cpp
 * @brief Tests for OpenAI adapter
 *
 * Tests constructor, configuration, capabilities, and config validation.
 * HTTP call tests require a running mock server (integration tests).
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit::core;
using namespace agenkit::adapters;

// Test default configuration values
TEST(OpenAIAgentTest, DefaultConfigModel) {
    OpenAIConfig config;
    EXPECT_EQ(config.model, "gpt-4o");
}

TEST(OpenAIAgentTest, DefaultConfigMaxTokens) {
    OpenAIConfig config;
    EXPECT_EQ(config.max_tokens, 4096);
}

TEST(OpenAIAgentTest, DefaultConfigTemperature) {
    OpenAIConfig config;
    EXPECT_DOUBLE_EQ(config.temperature, 0.7);
}

TEST(OpenAIAgentTest, DefaultConfigApiBase) {
    OpenAIConfig config;
    EXPECT_EQ(config.api_base, "https://api.openai.com");
}

TEST(OpenAIAgentTest, DefaultConfigPenalties) {
    OpenAIConfig config;
    EXPECT_DOUBLE_EQ(config.frequency_penalty, 0.0);
    EXPECT_DOUBLE_EQ(config.presence_penalty, 0.0);
}

// Test agent construction
TEST(OpenAIAgentTest, ConstructorBasic) {
    OpenAIConfig config;
    config.api_key = "test-key";
    EXPECT_NO_THROW({
        OpenAIAgent agent(config);
    });
}

// Test agent name
TEST(OpenAIAgentTest, AgentName) {
    OpenAIConfig config;
    config.api_key = "test-key";
    OpenAIAgent agent(config);
    EXPECT_EQ(agent.name(), "openai");
}

// Test agent capabilities
TEST(OpenAIAgentTest, AgentCapabilities) {
    OpenAIConfig config;
    config.api_key = "test-key";
    OpenAIAgent agent(config);
    auto caps = agent.capabilities();
    EXPECT_FALSE(caps.empty());

    bool has_llm = false;
    bool has_openai = false;
    for (const auto& cap : caps) {
        if (cap == "llm") has_llm = true;
        if (cap == "openai") has_openai = true;
    }
    EXPECT_TRUE(has_llm);
    EXPECT_TRUE(has_openai);
}

// Test config access
TEST(OpenAIAgentTest, ConfigAccess) {
    OpenAIConfig config;
    config.api_key = "test-key";
    config.model = "gpt-4o";
    config.max_tokens = 2048;
    OpenAIAgent agent(config);

    const auto& retrieved = agent.config();
    EXPECT_EQ(retrieved.model, "gpt-4o");
    EXPECT_EQ(retrieved.max_tokens, 2048);
}

// Test set_config updates configuration
TEST(OpenAIAgentTest, SetConfig) {
    OpenAIConfig config;
    config.api_key = "test-key";
    OpenAIAgent agent(config);

    OpenAIConfig new_config;
    new_config.api_key = "test-key";
    new_config.max_tokens = 8192;
    agent.set_config(new_config);

    EXPECT_EQ(agent.config().max_tokens, 8192);
}

// Test constructor throws on empty API key
TEST(OpenAIAgentTest, EmptyApiKeyThrows) {
    OpenAIConfig config;
    config.api_key = "";
    EXPECT_THROW(OpenAIAgent agent(config), std::invalid_argument);
}

// Test custom model string
TEST(OpenAIAgentTest, CustomModel) {
    OpenAIConfig config;
    config.api_key = "test-key";
    config.model = "gpt-4o-mini";
    EXPECT_NO_THROW({
        OpenAIAgent agent(config);
        EXPECT_EQ(agent.config().model, "gpt-4o-mini");
    });
}

// Test custom temperature
TEST(OpenAIAgentTest, CustomTemperature) {
    OpenAIConfig config;
    config.api_key = "test-key";
    config.temperature = 0.5;
    OpenAIAgent agent(config);
    EXPECT_DOUBLE_EQ(agent.config().temperature, 0.5);
}

// Test message content access
TEST(OpenAIAgentTest, MessageWithText) {
    auto msg = Message::with_text("user", "Hello, GPT!");
    EXPECT_EQ(msg.role, "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, GPT!");
}
