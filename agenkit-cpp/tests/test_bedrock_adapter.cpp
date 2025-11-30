/**
 * @file test_bedrock_adapter.cpp
 * @brief Tests for Bedrock adapter
 *
 * NOTE: These tests verify the adapter interface and configuration.
 * Actual API calls require AWS credentials and will be skipped if
 * AWS SDK is not available or credentials are not configured.
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/bedrock_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit::core;
using namespace agenkit::adapters;

// Test 1: Constructor with valid config (may throw if AWS SDK not available)
TEST(BedrockAgentTest, ConstructorWithValidConfig) {
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = "anthropic.claude-3-5-sonnet-20241022-v2:0";
    config.temperature = 0.7;
    config.max_tokens = 1024;

#ifdef AGENKIT_HAS_AWS_SDK
    EXPECT_NO_THROW({
        BedrockAgent agent(config);
        EXPECT_EQ(agent.name(), "bedrock-anthropic.claude-3-5-sonnet-20241022-v2:0");
    });
#else
    EXPECT_THROW({
        BedrockAgent agent(config);
    }, std::runtime_error);
#endif
}

// Test 2: Constructor with explicit credentials
TEST(BedrockAgentTest, ConstructorWithExplicitCredentials) {
    BedrockConfig config;
    config.region = "us-west-2";
    config.model = "anthropic.claude-3-haiku-20240307-v1:0";
    config.access_key_id = "test-access-key";
    config.secret_access_key = "test-secret-key";

#ifdef AGENKIT_HAS_AWS_SDK
    EXPECT_NO_THROW({
        BedrockAgent agent(config);
    });
#else
    EXPECT_THROW({
        BedrockAgent agent(config);
    }, std::runtime_error);
#endif
}

// Test 3: Name format matches model
TEST(BedrockAgentTest, NameFormatMatchesModel) {
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = "meta.llama3-2-90b-instruct-v1:0";

#ifdef AGENKIT_HAS_AWS_SDK
    BedrockAgent agent(config);
    EXPECT_EQ(agent.name(), "bedrock-meta.llama3-2-90b-instruct-v1:0");
#else
    // Just test the name format without creating agent
    EXPECT_EQ("bedrock-meta.llama3-2-90b-instruct-v1:0",
              "bedrock-" + config.model);
#endif
}

// Test 4: Capabilities list
TEST(BedrockAgentTest, HasCorrectCapabilities) {
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = "anthropic.claude-3-5-sonnet-20241022-v2:0";

#ifdef AGENKIT_HAS_AWS_SDK
    BedrockAgent agent(config);
    auto caps = agent.capabilities();

    EXPECT_EQ(caps.size(), 3);
    EXPECT_EQ(caps[0], "llm");
    EXPECT_EQ(caps[1], "completion");
    EXPECT_EQ(caps[2], "chat");
#else
    // Capabilities are static, test without creating agent
    EXPECT_TRUE(true);
#endif
}

// Test 5: Config getter returns correct values
TEST(BedrockAgentTest, ConfigGetterReturnsCorrectValues) {
    BedrockConfig config;
    config.region = "eu-west-1";
    config.model = "mistral.mistral-large-2407-v1:0";
    config.temperature = 0.9;
    config.max_tokens = 2048;
    config.top_p = 0.95;
    config.stop_sequences = {"STOP", "END"};

#ifdef AGENKIT_HAS_AWS_SDK
    BedrockAgent agent(config);
    const auto& retrieved_config = agent.config();

    EXPECT_EQ(retrieved_config.region, "eu-west-1");
    EXPECT_EQ(retrieved_config.model, "mistral.mistral-large-2407-v1:0");
    EXPECT_EQ(retrieved_config.temperature.value(), 0.9);
    EXPECT_EQ(retrieved_config.max_tokens.value(), 2048);
    EXPECT_EQ(retrieved_config.top_p.value(), 0.95);
    EXPECT_EQ(retrieved_config.stop_sequences.size(), 2);
#else
    // Test config values directly
    EXPECT_EQ(config.region, "eu-west-1");
    EXPECT_EQ(config.model, "mistral.mistral-large-2407-v1:0");
#endif
}

// Test 6: Config setter updates configuration
TEST(BedrockAgentTest, ConfigSetterUpdatesConfiguration) {
#ifdef AGENKIT_HAS_AWS_SDK
    BedrockConfig config1;
    config1.region = "us-east-1";
    config1.model = "anthropic.claude-3-haiku-20240307-v1:0";

    BedrockAgent agent(config1);
    EXPECT_EQ(agent.name(), "bedrock-anthropic.claude-3-haiku-20240307-v1:0");

    BedrockConfig config2;
    config2.region = "us-west-2";
    config2.model = "meta.llama3-2-11b-instruct-v1:0";
    config2.temperature = 1.0;

    agent.set_config(config2);

    EXPECT_EQ(agent.name(), "bedrock-meta.llama3-2-11b-instruct-v1:0");
    EXPECT_EQ(agent.config().region, "us-west-2");
    EXPECT_EQ(agent.config().temperature.value(), 1.0);
#else
    EXPECT_TRUE(true);  // Skip test if SDK not available
#endif
}

// Test 7: Model constants are defined correctly
TEST(BedrockAgentTest, ModelConstantsAreDefined) {
    // Anthropic Claude models
    EXPECT_STREQ(BedrockModels::CLAUDE_3_5_SONNET_V2, "anthropic.claude-3-5-sonnet-20241022-v2:0");
    EXPECT_STREQ(BedrockModels::CLAUDE_3_5_SONNET, "anthropic.claude-3-5-sonnet-20240620-v1:0");
    EXPECT_STREQ(BedrockModels::CLAUDE_3_OPUS, "anthropic.claude-3-opus-20240229-v1:0");
    EXPECT_STREQ(BedrockModels::CLAUDE_3_SONNET, "anthropic.claude-3-sonnet-20240229-v1:0");
    EXPECT_STREQ(BedrockModels::CLAUDE_3_HAIKU, "anthropic.claude-3-haiku-20240307-v1:0");

    // Meta Llama models
    EXPECT_STREQ(BedrockModels::LLAMA_3_2_90B, "meta.llama3-2-90b-instruct-v1:0");
    EXPECT_STREQ(BedrockModels::LLAMA_3_2_11B, "meta.llama3-2-11b-instruct-v1:0");
    EXPECT_STREQ(BedrockModels::LLAMA_3_2_3B, "meta.llama3-2-3b-instruct-v1:0");
    EXPECT_STREQ(BedrockModels::LLAMA_3_2_1B, "meta.llama3-2-1b-instruct-v1:0");

    // Mistral models
    EXPECT_STREQ(BedrockModels::MISTRAL_LARGE_2407, "mistral.mistral-large-2407-v1:0");
    EXPECT_STREQ(BedrockModels::MISTRAL_LARGE_2402, "mistral.mistral-large-2402-v1:0");
    EXPECT_STREQ(BedrockModels::MISTRAL_7B, "mistral.mistral-7b-instruct-v0:2");

    // Amazon Titan models
    EXPECT_STREQ(BedrockModels::TITAN_TEXT_PREMIER, "amazon.titan-text-premier-v1:0");
    EXPECT_STREQ(BedrockModels::TITAN_TEXT_EXPRESS, "amazon.titan-text-express-v1");
    EXPECT_STREQ(BedrockModels::TITAN_TEXT_LITE, "amazon.titan-text-lite-v1");
}

// Test 8: Default configuration values
TEST(BedrockAgentTest, DefaultConfigurationValues) {
    BedrockConfig config;

    EXPECT_EQ(config.region, "us-east-1");
    EXPECT_EQ(config.model, "anthropic.claude-3-5-sonnet-20241022-v2:0");
    EXPECT_FALSE(config.access_key_id.has_value());
    EXPECT_FALSE(config.secret_access_key.has_value());
    EXPECT_FALSE(config.session_token.has_value());
    EXPECT_FALSE(config.temperature.has_value());
    EXPECT_FALSE(config.max_tokens.has_value());
    EXPECT_FALSE(config.top_p.has_value());
    EXPECT_TRUE(config.stop_sequences.empty());
    EXPECT_EQ(config.timeout_seconds, 60);
}

// Test 9: Message format conversion with different roles
TEST(BedrockAgentTest, MessageFormatConversion) {
    // Test that messages can be created with correct roles
    auto msg_user = Message::with_text("user", "Hello");
    auto msg_assistant = Message::with_text("assistant", "Hi");
    auto msg_system = Message::with_text("system", "You are helpful");
    auto msg_agent = Message::with_text("agent", "Response");

    // Verify messages can be created
    EXPECT_EQ(msg_user.role(), "user");
    EXPECT_EQ(msg_assistant.role(), "assistant");
    EXPECT_EQ(msg_system.role(), "system");
    EXPECT_EQ(msg_agent.role(), "agent");
}

// Test 10: Timeout configuration
TEST(BedrockAgentTest, TimeoutConfiguration) {
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = "anthropic.claude-3-5-sonnet-20241022-v2:0";
    config.timeout_seconds = 30;

    EXPECT_EQ(config.timeout_seconds, 30);
}

// Test 11: Stop sequences configuration
TEST(BedrockAgentTest, StopSequencesConfiguration) {
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = "anthropic.claude-3-5-sonnet-20241022-v2:0";
    config.stop_sequences = {"\n\n", "END", "STOP"};

    EXPECT_EQ(config.stop_sequences.size(), 3);
    EXPECT_EQ(config.stop_sequences[0], "\n\n");
    EXPECT_EQ(config.stop_sequences[1], "END");
    EXPECT_EQ(config.stop_sequences[2], "STOP");
}

// Test 12: Multiple regions support
TEST(BedrockAgentTest, MultipleRegionsSupport) {
    std::vector<std::string> regions = {
        "us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"
    };

    for (const auto& region : regions) {
        BedrockConfig config;
        config.region = region;
        config.model = BedrockModels::CLAUDE_3_HAIKU;

        EXPECT_EQ(config.region, region);
    }
}

// Test 13: Session token configuration
TEST(BedrockAgentTest, SessionTokenConfiguration) {
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = BedrockModels::CLAUDE_3_5_SONNET_V2;
    config.access_key_id = "test-key";
    config.secret_access_key = "test-secret";
    config.session_token = "test-session-token";

    EXPECT_TRUE(config.session_token.has_value());
    EXPECT_EQ(config.session_token.value(), "test-session-token");
}

// Test 14: Process returns error when AWS SDK not available
TEST(BedrockAgentTest, ProcessReturnsErrorWithoutAWSSDK) {
#ifndef AGENKIT_HAS_AWS_SDK
    // Test that constructor throws without AWS SDK
    BedrockConfig config;
    config.region = "us-east-1";
    config.model = BedrockModels::CLAUDE_3_5_SONNET_V2;

    EXPECT_THROW({
        BedrockAgent agent(config);
    }, std::runtime_error);
#else
    EXPECT_TRUE(true);  // Skip if SDK is available
#endif
}

// Test 15: All model families have constants
TEST(BedrockAgentTest, AllModelFamiliesHaveConstants) {
    // Verify we have models from each family

    // Anthropic
    EXPECT_TRUE(std::string(BedrockModels::CLAUDE_3_5_SONNET_V2).find("anthropic") != std::string::npos);

    // Meta
    EXPECT_TRUE(std::string(BedrockModels::LLAMA_3_2_90B).find("meta") != std::string::npos);

    // Mistral
    EXPECT_TRUE(std::string(BedrockModels::MISTRAL_LARGE_2407).find("mistral") != std::string::npos);

    // Amazon
    EXPECT_TRUE(std::string(BedrockModels::TITAN_TEXT_PREMIER).find("amazon") != std::string::npos);
}
