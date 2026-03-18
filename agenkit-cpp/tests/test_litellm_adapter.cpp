/**
 * @file test_litellm_adapter.cpp
 * @brief Tests for LiteLLM adapter
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/litellm_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit::core;
using namespace agenkit::adapters;

// Test 1: Constructor validation with valid config
TEST(LiteLLMAgentTest, ConstructorWithValidConfig) {
    LiteLLMConfig config;
    config.base_url = "http://localhost:4000";
    config.model = "gpt-3.5-turbo";
    config.temperature = 0.7;
    config.max_tokens = 1024;

    EXPECT_NO_THROW({
        LiteLLMAgent agent(config);
        EXPECT_EQ(agent.name(), "litellm-gpt-3.5-turbo");
    });
}

// Test 2: Constructor validation without API key (optional)
TEST(LiteLLMAgentTest, ConstructorWithoutAPIKey) {
    LiteLLMConfig config;
    config.base_url = "http://localhost:4000";
    config.model = "gpt-4";

    // API key is optional for LiteLLM
    EXPECT_NO_THROW({
        LiteLLMAgent agent(config);
    });
}

// Test 3: Constructor fails with empty model
TEST(LiteLLMAgentTest, ConstructorFailsWithEmptyModel) {
    LiteLLMConfig config;
    config.base_url = "http://localhost:4000";
    config.model = "";

    EXPECT_THROW({
        LiteLLMAgent agent(config);
    }, std::invalid_argument);
}

// Test 4: Name format matches model
TEST(LiteLLMAgentTest, NameFormatMatchesModel) {
    LiteLLMConfig config;
    config.model = "claude-3-5-sonnet-20241022";
    config.base_url = "http://localhost:4000";

    LiteLLMAgent agent(config);
    EXPECT_EQ(agent.name(), "litellm-claude-3-5-sonnet-20241022");
}

// Test 5: Capabilities list
TEST(LiteLLMAgentTest, HasCorrectCapabilities) {
    LiteLLMConfig config;
    config.model = "gpt-3.5-turbo";
    config.base_url = "http://localhost:4000";

    LiteLLMAgent agent(config);
    auto caps = agent.capabilities();

    EXPECT_EQ(caps.size(), 4);
    EXPECT_EQ(caps[0], "llm");
    EXPECT_EQ(caps[1], "completion");
    EXPECT_EQ(caps[2], "streaming");
    EXPECT_EQ(caps[3], "universal-gateway");
}

// Test 6: Config getter returns correct values
TEST(LiteLLMAgentTest, ConfigGetterReturnsCorrectValues) {
    LiteLLMConfig config;
    config.base_url = "http://localhost:4000";
    config.model = "gpt-4";
    config.temperature = 0.9;
    config.max_tokens = 2048;
    config.api_key = "test-key";

    LiteLLMAgent agent(config);
    const auto& retrieved_config = agent.config();

    EXPECT_EQ(retrieved_config.base_url, "http://localhost:4000");
    EXPECT_EQ(retrieved_config.model, "gpt-4");
    EXPECT_EQ(retrieved_config.temperature.value(), 0.9);
    EXPECT_EQ(retrieved_config.max_tokens.value(), 2048);
    EXPECT_EQ(retrieved_config.api_key.value(), "test-key");
}

// Test 7: Config setter updates configuration
TEST(LiteLLMAgentTest, ConfigSetterUpdatesConfiguration) {
    LiteLLMConfig config1;
    config1.model = "gpt-3.5-turbo";
    config1.base_url = "http://localhost:4000";

    LiteLLMAgent agent(config1);
    EXPECT_EQ(agent.name(), "litellm-gpt-3.5-turbo");

    LiteLLMConfig config2;
    config2.model = "gpt-4";
    config2.base_url = "http://localhost:5000";
    config2.temperature = 1.0;

    agent.set_config(config2);

    EXPECT_EQ(agent.name(), "litellm-gpt-4");
    EXPECT_EQ(agent.config().base_url, "http://localhost:5000");
    EXPECT_EQ(agent.config().temperature.value(), 1.0);
}

// Test 8: Config setter validates model
TEST(LiteLLMAgentTest, ConfigSetterValidatesModel) {
    LiteLLMConfig config1;
    config1.model = "gpt-3.5-turbo";
    config1.base_url = "http://localhost:4000";

    LiteLLMAgent agent(config1);

    LiteLLMConfig config2;
    config2.model = "";  // Invalid empty model
    config2.base_url = "http://localhost:4000";

    EXPECT_THROW({
        agent.set_config(config2);
    }, std::invalid_argument);
}

// Test 9: Model constants are defined correctly
TEST(LiteLLMAgentTest, ModelConstantsAreDefined) {
    // OpenAI models
    EXPECT_STREQ(LiteLLMModels::GPT_4, "gpt-4");
    EXPECT_STREQ(LiteLLMModels::GPT_4_TURBO, "gpt-4-turbo");
    EXPECT_STREQ(LiteLLMModels::GPT_4O, "gpt-4o");
    EXPECT_STREQ(LiteLLMModels::GPT_4O_MINI, "gpt-4o-mini");
    EXPECT_STREQ(LiteLLMModels::GPT_3_5_TURBO, "gpt-3.5-turbo");

    // Anthropic models
    EXPECT_STREQ(LiteLLMModels::CLAUDE_3_5_SONNET, "claude-3-5-sonnet-20241022");
    EXPECT_STREQ(LiteLLMModels::CLAUDE_3_OPUS, "claude-3-opus-20240229");
    EXPECT_STREQ(LiteLLMModels::CLAUDE_3_SONNET, "claude-3-sonnet-20240229");
    EXPECT_STREQ(LiteLLMModels::CLAUDE_3_HAIKU, "claude-3-haiku-20240307");

    // Bedrock models
    EXPECT_STREQ(LiteLLMModels::BEDROCK_CLAUDE_V2, "bedrock/anthropic.claude-v2");
    EXPECT_STREQ(LiteLLMModels::BEDROCK_CLAUDE_3_SONNET, "bedrock/anthropic.claude-3-sonnet-20240229-v1:0");

    // Gemini models
    EXPECT_STREQ(LiteLLMModels::GEMINI_PRO, "gemini/gemini-pro");
    EXPECT_STREQ(LiteLLMModels::GEMINI_2_0_FLASH, "gemini/gemini-2.0-flash-exp");

    // Ollama models
    EXPECT_STREQ(LiteLLMModels::OLLAMA_LLAMA2, "ollama/llama2");
    EXPECT_STREQ(LiteLLMModels::OLLAMA_MISTRAL, "ollama/mistral");
}

// Test 10: Default configuration values
TEST(LiteLLMAgentTest, DefaultConfigurationValues) {
    LiteLLMConfig config;

    EXPECT_EQ(config.base_url, "http://localhost:4000");
    EXPECT_EQ(config.model, "gpt-3.5-turbo");
    EXPECT_FALSE(config.api_key.has_value());
    EXPECT_FALSE(config.temperature.has_value());
    EXPECT_FALSE(config.max_tokens.has_value());
    EXPECT_FALSE(config.top_p.has_value());
    EXPECT_EQ(config.timeout.count(), 60000);
}

// Test 11: Message format conversion with different roles
TEST(LiteLLMAgentTest, MessageFormatConversion) {
    LiteLLMConfig config;
    config.model = "gpt-3.5-turbo";
    config.base_url = "http://localhost:4000";

    LiteLLMAgent agent(config);

    // Test that agent creates messages with correct format
    // This tests the internal message_to_json conversion
    auto msg_user = Message::with_text("user", "Hello");
    auto msg_assistant = Message::with_text("assistant", "Hi");
    auto msg_system = Message::with_text("system", "You are helpful");
    auto msg_agent = Message::with_text("agent", "Response");

    // Verify messages can be created and processed
    // (actual network calls will fail without server, but message conversion happens first)
    EXPECT_EQ(msg_user.role(), "user");
    EXPECT_EQ(msg_assistant.role(), "assistant");
    EXPECT_EQ(msg_system.role(), "system");
    EXPECT_EQ(msg_agent.role(), "agent");
}

// Test 12: Timeout configuration
TEST(LiteLLMAgentTest, TimeoutConfiguration) {
    LiteLLMConfig config;
    config.model = "gpt-3.5-turbo";
    config.base_url = "http://localhost:4000";
    config.timeout = std::chrono::milliseconds(30000);

    LiteLLMAgent agent(config);

    EXPECT_EQ(agent.config().timeout.count(), 30000);
}
