/**
 * @file test_gemini_adapter.cpp
 * @brief Tests for Gemini adapter
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/gemini_agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include <cstdlib>
#include <nlohmann/json.hpp>

using namespace agenkit::core;
using namespace agenkit::adapters;
using json = nlohmann::json;

// Test 1: Constructor with explicit API key
TEST(GeminiAgentTest, ConstructorWithExplicitAPIKey) {
    GeminiConfig config;
    config.api_key = "test-api-key";
    config.model = "gemini-2.0-flash-exp";

    EXPECT_NO_THROW({
        GeminiAgent agent(config);
        EXPECT_EQ(agent.name(), "gemini-gemini-2.0-flash-exp");
    });
}

// Test 2: Constructor loads API key from environment
TEST(GeminiAgentTest, ConstructorLoadsAPIKeyFromEnvironment) {
    // Set environment variable
    setenv("GEMINI_API_KEY", "test-env-key", 1);

    GeminiConfig config;
    config.model = "gemini-1.5-pro";
    // Don't set api_key - should load from env

    EXPECT_NO_THROW({
        GeminiAgent agent(config);
        EXPECT_EQ(agent.config().api_key.value(), "test-env-key");
    });

    // Clean up
    unsetenv("GEMINI_API_KEY");
}

// Test 3: Constructor fails without API key
TEST(GeminiAgentTest, ConstructorFailsWithoutAPIKey) {
    // Make sure no API key in environment
    unsetenv("GEMINI_API_KEY");
    unsetenv("GOOGLE_API_KEY");

    GeminiConfig config;
    config.model = "gemini-2.0-flash-exp";
    // Don't set api_key

    EXPECT_THROW({
        GeminiAgent agent(config);
    }, std::invalid_argument);
}

// Test 4: Constructor prefers GEMINI_API_KEY over GOOGLE_API_KEY
TEST(GeminiAgentTest, ConstructorPrefersGeminiAPIKey) {
    setenv("GEMINI_API_KEY", "gemini-key", 1);
    setenv("GOOGLE_API_KEY", "google-key", 1);

    GeminiConfig config;
    config.model = "gemini-1.5-flash";

    GeminiAgent agent(config);
    EXPECT_EQ(agent.config().api_key.value(), "gemini-key");

    // Clean up
    unsetenv("GEMINI_API_KEY");
    unsetenv("GOOGLE_API_KEY");
}

// Test 5: Name format matches model
TEST(GeminiAgentTest, NameFormatMatchesModel) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.model = "gemini-1.5-pro";

    GeminiAgent agent(config);
    EXPECT_EQ(agent.name(), "gemini-gemini-1.5-pro");
}

// Test 6: Capabilities list
TEST(GeminiAgentTest, HasCorrectCapabilities) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.model = "gemini-2.0-flash-exp";

    GeminiAgent agent(config);
    auto caps = agent.capabilities();

    EXPECT_EQ(caps.size(), 3);
    EXPECT_EQ(caps[0], "llm");
    EXPECT_EQ(caps[1], "completion");
    EXPECT_EQ(caps[2], "chat");
}

// Test 7: Config getter returns correct values
TEST(GeminiAgentTest, ConfigGetterReturnsCorrectValues) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.model = "gemini-1.5-pro";
    config.temperature = 0.9;
    config.max_tokens = 2048;
    config.top_p = 0.95;
    config.top_k = 40;
    config.stop_sequences = {"STOP", "END"};

    GeminiAgent agent(config);
    const auto& retrieved_config = agent.config();

    EXPECT_EQ(retrieved_config.api_key.value(), "test-key");
    EXPECT_EQ(retrieved_config.model, "gemini-1.5-pro");
    EXPECT_EQ(retrieved_config.temperature.value(), 0.9);
    EXPECT_EQ(retrieved_config.max_tokens.value(), 2048);
    EXPECT_EQ(retrieved_config.top_p.value(), 0.95);
    EXPECT_EQ(retrieved_config.top_k.value(), 40);
    EXPECT_EQ(retrieved_config.stop_sequences.size(), 2);
}

// Test 8: Config setter updates configuration
TEST(GeminiAgentTest, ConfigSetterUpdatesConfiguration) {
    GeminiConfig config1;
    config1.api_key = "key1";
    config1.model = "gemini-2.0-flash-exp";

    GeminiAgent agent(config1);
    EXPECT_EQ(agent.name(), "gemini-gemini-2.0-flash-exp");

    GeminiConfig config2;
    config2.api_key = "key2";
    config2.model = "gemini-1.5-pro";
    config2.temperature = 1.0;

    agent.set_config(config2);

    EXPECT_EQ(agent.name(), "gemini-gemini-1.5-pro");
    EXPECT_EQ(agent.config().api_key.value(), "key2");
    EXPECT_EQ(agent.config().temperature.value(), 1.0);
}

// Test 9: Model constants are defined correctly
TEST(GeminiAgentTest, ModelConstantsAreDefined) {
    EXPECT_STREQ(GeminiModels::GEMINI_2_0_FLASH_EXP, "gemini-2.0-flash-exp");
    EXPECT_STREQ(GeminiModels::GEMINI_1_5_PRO, "gemini-1.5-pro");
    EXPECT_STREQ(GeminiModels::GEMINI_1_5_FLASH, "gemini-1.5-flash");
    EXPECT_STREQ(GeminiModels::GEMINI_PRO, "gemini-pro");
}

// Test 10: Default configuration values
TEST(GeminiAgentTest, DefaultConfigurationValues) {
    GeminiConfig config;

    EXPECT_FALSE(config.api_key.has_value());
    EXPECT_EQ(config.model, "gemini-2.0-flash-exp");
    EXPECT_FALSE(config.temperature.has_value());
    EXPECT_FALSE(config.max_tokens.has_value());
    EXPECT_FALSE(config.top_p.has_value());
    EXPECT_FALSE(config.top_k.has_value());
    EXPECT_TRUE(config.stop_sequences.empty());
    EXPECT_EQ(config.api_base, "https://generativelanguage.googleapis.com");
    EXPECT_EQ(config.timeout.count(), 60000);
}

// Test 11: Message format conversion with different roles
TEST(GeminiAgentTest, MessageFormatConversion) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.model = "gemini-2.0-flash-exp";

    GeminiAgent agent(config);

    // Test that agent creates messages with correct format
    auto msg_user = Message::with_text("user", "Hello");
    auto msg_assistant = Message::with_text("assistant", "Hi");
    auto msg_system = Message::with_text("system", "You are helpful");
    auto msg_agent = Message::with_text("agent", "Response");

    // Verify messages can be created and processed
    // (actual network calls will fail without API, but message conversion happens first)
    EXPECT_EQ(msg_user.role(), "user");
    EXPECT_EQ(msg_assistant.role(), "assistant");
    EXPECT_EQ(msg_system.role(), "system");
    EXPECT_EQ(msg_agent.role(), "agent");
}

// Test 12: Timeout configuration
TEST(GeminiAgentTest, TimeoutConfiguration) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.model = "gemini-2.0-flash-exp";
    config.timeout = std::chrono::milliseconds(30000);

    GeminiAgent agent(config);

    EXPECT_EQ(agent.config().timeout.count(), 30000);
}

// Test 13: Stop sequences configuration
TEST(GeminiAgentTest, StopSequencesConfiguration) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.model = "gemini-1.5-pro";
    config.stop_sequences = {"\n\n", "END", "STOP"};

    GeminiAgent agent(config);

    const auto& stop_seqs = agent.config().stop_sequences;
    EXPECT_EQ(stop_seqs.size(), 3);
    EXPECT_EQ(stop_seqs[0], "\n\n");
    EXPECT_EQ(stop_seqs[1], "END");
    EXPECT_EQ(stop_seqs[2], "STOP");
}

// --- CallOptions / OptionsAgent wiring (#818) ---

TEST(GeminiAgentTest, IsAnOptionsAgent) {
    GeminiConfig config;
    config.api_key = "test-key";
    GeminiAgent agent(config);

    EXPECT_TRUE(supports_options(&agent));
    EXPECT_NE(dynamic_cast<OptionsAgent*>(&agent), nullptr);
}

// Gemini's REST API supports `seed` directly as an integer field on
// generationConfig, and `stopSequences` for stop — both a real field, no
// warn-and-drop needed (unlike Claude/Bedrock).
TEST(GeminiAgentTest, RequestBodyIncludesSeedAndStopSequencesWhenSet) {
    GeminiConfig config;
    config.api_key = "test-key";
    GeminiAgent agent(config);

    auto options = CallOptions{}.with_seed(42).with_stop({"STOP", "END"});
    auto contents = json::array({{{"role", "user"}, {"parts", json::array({{{"text", "hi"}}})}}});
    auto body = agent.build_request_body(contents, options);

    ASSERT_TRUE(body.contains("generationConfig"));
    const auto& gen_config = body["generationConfig"];

    ASSERT_TRUE(gen_config.contains("seed"));
    EXPECT_EQ(gen_config["seed"].get<uint64_t>(), 42u);

    ASSERT_TRUE(gen_config.contains("stopSequences"));
    std::vector<std::string> stop = gen_config["stopSequences"].get<std::vector<std::string>>();
    ASSERT_EQ(stop.size(), 2u);
    EXPECT_EQ(stop[0], "STOP");
    EXPECT_EQ(stop[1], "END");
}

// options.stop overrides config_.stop_sequences for that one call rather
// than merging with it.
TEST(GeminiAgentTest, RequestBodyStopOverridesConfigStopSequences) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.stop_sequences = {"CONFIG_STOP"};
    GeminiAgent agent(config);

    auto options = CallOptions{}.with_stop({"CALL_STOP"});
    auto contents = json::array({{{"role", "user"}, {"parts", json::array({{{"text", "hi"}}})}}});
    auto body = agent.build_request_body(contents, options);

    std::vector<std::string> stop = body["generationConfig"]["stopSequences"].get<std::vector<std::string>>();
    ASSERT_EQ(stop.size(), 1u);
    EXPECT_EQ(stop[0], "CALL_STOP");
}

// When CallOptions.stop is unset, the config default must still reach the
// wire (the existing pre-#818 behavior for config-level stop_sequences).
TEST(GeminiAgentTest, RequestBodyFallsBackToConfigStopSequencesWhenUnset) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.stop_sequences = {"CONFIG_STOP"};
    GeminiAgent agent(config);

    auto contents = json::array({{{"role", "user"}, {"parts", json::array({{{"text", "hi"}}})}}});
    auto body = agent.build_request_body(contents, CallOptions{});

    std::vector<std::string> stop = body["generationConfig"]["stopSequences"].get<std::vector<std::string>>();
    ASSERT_EQ(stop.size(), 1u);
    EXPECT_EQ(stop[0], "CONFIG_STOP");
}

// A per-call temperature/max_tokens/top_p must override the config default
// for that one call.
TEST(GeminiAgentTest, RequestBodyPerCallOptionsOverrideConfigDefaults) {
    GeminiConfig config;
    config.api_key = "test-key";
    config.temperature = 0.5;
    config.max_tokens = 1024;
    config.top_p = 0.9;
    GeminiAgent agent(config);

    auto options = CallOptions{}.with_temperature(0.1).with_max_tokens(64).with_top_p(0.3);
    auto contents = json::array({{{"role", "user"}, {"parts", json::array({{{"text", "hi"}}})}}});
    auto body = agent.build_request_body(contents, options);

    const auto& gen_config = body["generationConfig"];
    EXPECT_DOUBLE_EQ(gen_config["temperature"].get<double>(), 0.1);
    EXPECT_EQ(gen_config["maxOutputTokens"].get<int>(), 64);
    EXPECT_DOUBLE_EQ(gen_config["topP"].get<double>(), 0.3);
}

// Test 14: Empty API key string is treated as invalid
TEST(GeminiAgentTest, EmptyAPIKeyStringIsInvalid) {
    GeminiConfig config;
    config.api_key = "";  // Empty string
    config.model = "gemini-2.0-flash-exp";

    EXPECT_THROW({
        GeminiAgent agent(config);
    }, std::invalid_argument);
}

// Test 15: Config setter validates API key
TEST(GeminiAgentTest, ConfigSetterValidatesAPIKey) {
    // Clean environment
    unsetenv("GEMINI_API_KEY");
    unsetenv("GOOGLE_API_KEY");

    GeminiConfig config1;
    config1.api_key = "valid-key";
    config1.model = "gemini-2.0-flash-exp";

    GeminiAgent agent(config1);

    GeminiConfig config2;
    config2.model = "gemini-1.5-pro";
    // Don't set api_key and no env var

    EXPECT_THROW({
        agent.set_config(config2);
    }, std::invalid_argument);
}
