/**
 * @file test_claude_adapter.cpp
 * @brief Tests for Anthropic Claude adapter
 *
 * Tests constructor, configuration, capabilities, and config validation.
 * HTTP call tests require a running mock server (integration tests).
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <nlohmann/json.hpp>
#include <sstream>

using namespace agenkit::core;
using namespace agenkit::adapters;
using json = nlohmann::json;

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
    EXPECT_EQ(msg.role(), "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, Claude!");
}

// --- CallOptions / OptionsAgent wiring (#818) ---

TEST(ClaudeAgentTest, IsAnOptionsAgent) {
    ClaudeConfig config;
    config.api_key = "test-key";
    ClaudeAgent agent(config);

    EXPECT_TRUE(supports_options(&agent));
    EXPECT_NE(dynamic_cast<OptionsAgent*>(&agent), nullptr);
}

// stop -> stop_sequences: the Messages API has no field named `stop`, so this
// is a real translation, not a passthrough.
TEST(ClaudeAgentTest, RequestBodyTranslatesStopToStopSequences) {
    ClaudeConfig config;
    config.api_key = "test-key";
    ClaudeAgent agent(config);

    auto options = CallOptions{}.with_stop({"STOP", "END"});
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    EXPECT_FALSE(body.contains("stop"));
    ASSERT_TRUE(body.contains("stop_sequences"));
    std::vector<std::string> stop = body["stop_sequences"].get<std::vector<std::string>>();
    ASSERT_EQ(stop.size(), 2u);
    EXPECT_EQ(stop[0], "STOP");
    EXPECT_EQ(stop[1], "END");
}

// The Anthropic Messages API has no sampling-seed parameter at all: proving
// the drop (not just the absence of a crash) is the point of this test.
// Even with CallOptions.seed set, "seed" must never appear on the wire.
TEST(ClaudeAgentTest, RequestBodyNeverIncludesSeed) {
    ClaudeConfig config;
    config.api_key = "test-key";
    ClaudeAgent agent(config);

    auto options = CallOptions{}.with_seed(42);
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    EXPECT_FALSE(body.contains("seed"));
}

// A per-call temperature/max_tokens must override the config default for
// that one call.
TEST(ClaudeAgentTest, RequestBodyPerCallOptionsOverrideConfigDefaults) {
    ClaudeConfig config;
    config.api_key = "test-key";
    config.temperature = 1.0;
    config.max_tokens = 4096;
    ClaudeAgent agent(config);

    auto options = CallOptions{}.with_temperature(0.3).with_max_tokens(256);
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    EXPECT_DOUBLE_EQ(body["temperature"].get<double>(), 0.3);
    EXPECT_EQ(body["max_tokens"].get<int>(), 256);
}

// process_with() must warn (not silently drop) when the caller sets a seed
// that Claude cannot honour. Captured via stderr redirection since this
// codebase's convention for "unsupported option" warnings is std::cerr
// (no Logger abstraction exists in agenkit-cpp).
TEST(ClaudeAgentTest, ProcessWithWarnsOnUnsupportedSeed) {
    ClaudeConfig config;
    config.api_key = "test-key";
    config.api_base = "http://127.0.0.1:1";  // unroutable: fails fast, no network
    ClaudeAgent agent(config);

    std::ostringstream captured;
    std::streambuf* old_cerr = std::cerr.rdbuf(captured.rdbuf());

    auto options = CallOptions{}.with_seed(7);
    auto future = agent.process_with(Message::with_text("user", "hi"), options);
    future.get();

    std::cerr.rdbuf(old_cerr);

    EXPECT_NE(captured.str().find("seed"), std::string::npos);
}
