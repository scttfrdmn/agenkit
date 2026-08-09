/**
 * @file test_openai_adapter.cpp
 * @brief Tests for OpenAI adapter
 *
 * Tests constructor, configuration, capabilities, and config validation.
 * HTTP call tests require a running mock server (integration tests).
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include <nlohmann/json.hpp>

using namespace agenkit::core;
using namespace agenkit::adapters;
using json = nlohmann::json;

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
    EXPECT_EQ(msg.role(), "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, GPT!");
}

// --- CallOptions / OptionsAgent wiring (#818) ---

// OpenAIAgent must be detectable as an OptionsAgent via dynamic_cast, the
// same mechanism supports_options() and process_with_options() rely on.
TEST(OpenAIAgentTest, IsAnOptionsAgent) {
    OpenAIConfig config;
    config.api_key = "test-key";
    OpenAIAgent agent(config);

    EXPECT_TRUE(supports_options(&agent));
    EXPECT_NE(dynamic_cast<OptionsAgent*>(&agent), nullptr);
}

// build_request_body must omit seed/stop entirely when CallOptions is empty,
// so an agent that never opts in never sees a "seed": null on the wire.
TEST(OpenAIAgentTest, RequestBodyOmitsSeedAndStopWhenUnset) {
    OpenAIConfig config;
    config.api_key = "test-key";
    OpenAIAgent agent(config);

    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, CallOptions{});

    EXPECT_FALSE(body.contains("seed"));
    EXPECT_FALSE(body.contains("stop"));
}

// The defect in #818: seed/stop were accepted by CallOptions but never
// reached the request body. This is the positive check that they now do,
// under OpenAI's own field names (straight passthrough, no translation).
TEST(OpenAIAgentTest, RequestBodyIncludesSeedAndStopWhenSet) {
    OpenAIConfig config;
    config.api_key = "test-key";
    OpenAIAgent agent(config);

    auto options = CallOptions{}.with_seed(42).with_stop({"STOP", "END"});
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    ASSERT_TRUE(body.contains("seed"));
    EXPECT_EQ(body["seed"].get<uint64_t>(), 42u);

    ASSERT_TRUE(body.contains("stop"));
    std::vector<std::string> stop = body["stop"].get<std::vector<std::string>>();
    ASSERT_EQ(stop.size(), 2u);
    EXPECT_EQ(stop[0], "STOP");
    EXPECT_EQ(stop[1], "END");
}

// A per-call temperature/max_tokens/top_p must override the config default
// for that one call, matching CallOptions::merge's override semantics.
TEST(OpenAIAgentTest, RequestBodyPerCallOptionsOverrideConfigDefaults) {
    OpenAIConfig config;
    config.api_key = "test-key";
    config.temperature = 0.7;
    config.max_tokens = 4096;
    config.top_p = 1.0;
    OpenAIAgent agent(config);

    auto options = CallOptions{}.with_temperature(0.2).with_max_tokens(128).with_top_p(0.5);
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    EXPECT_DOUBLE_EQ(body["temperature"].get<double>(), 0.2);
    EXPECT_EQ(body["max_tokens"].get<int>(), 128);
    EXPECT_DOUBLE_EQ(body["top_p"].get<double>(), 0.5);
}

// process_with() must be reachable through the OptionsAgent interface, not
// just as a concrete OpenAIAgent method — this is what process_with_options()
// dispatches through.
TEST(OpenAIAgentTest, ProcessWithReachableViaOptionsAgentInterface) {
    OpenAIConfig config;
    config.api_key = "test-key";
    config.api_base = "http://127.0.0.1:1";  // unroutable: fails fast, no network
    OpenAIAgent agent(config);

    OptionsAgent* options_agent = dynamic_cast<OptionsAgent*>(&agent);
    ASSERT_NE(options_agent, nullptr);

    auto options = CallOptions{}.with_seed(7);
    auto future = options_agent->process_with(Message::with_text("user", "hi"), options);
    auto result = future.get();

    // No live server at this address: the call fails, but it must fail at
    // the transport layer, not because process_with() is unreachable/unimplemented.
    EXPECT_TRUE(result.is_err());
}
