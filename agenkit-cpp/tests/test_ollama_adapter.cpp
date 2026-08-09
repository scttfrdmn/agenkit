/**
 * @file test_ollama_adapter.cpp
 * @brief Tests for Ollama adapter
 *
 * Tests constructor, configuration, capabilities, and CallOptions/OptionsAgent
 * wiring (#818). HTTP call tests require a running Ollama server (integration
 * tests) and are out of scope here.
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include <nlohmann/json.hpp>

using namespace agenkit::core;
using namespace agenkit::adapters;
using json = nlohmann::json;

// Test default configuration values
TEST(OllamaAgentTest, DefaultConfigHost) {
    OllamaConfig config;
    EXPECT_EQ(config.host, "http://localhost:11434");
}

TEST(OllamaAgentTest, DefaultConfigModel) {
    OllamaConfig config;
    EXPECT_EQ(config.model, "llama3.3");
}

TEST(OllamaAgentTest, DefaultConfigTemperature) {
    OllamaConfig config;
    EXPECT_DOUBLE_EQ(config.temperature, 0.8);
}

// Test agent construction
TEST(OllamaAgentTest, ConstructorBasic) {
    OllamaConfig config;
    EXPECT_NO_THROW({
        OllamaAgent agent(config);
    });
}

TEST(OllamaAgentTest, ConstructorFailsWithEmptyModel) {
    OllamaConfig config;
    config.model = "";
    EXPECT_THROW(OllamaAgent agent(config), std::invalid_argument);
}

// Test agent name
TEST(OllamaAgentTest, AgentName) {
    OllamaConfig config;
    OllamaAgent agent(config);
    EXPECT_EQ(agent.name(), "ollama");
}

// Test agent capabilities
TEST(OllamaAgentTest, AgentCapabilities) {
    OllamaConfig config;
    OllamaAgent agent(config);
    auto caps = agent.capabilities();

    bool has_llm = false;
    bool has_local = false;
    for (const auto& cap : caps) {
        if (cap == "llm") has_llm = true;
        if (cap == "local") has_local = true;
    }
    EXPECT_TRUE(has_llm);
    EXPECT_TRUE(has_local);
}

// Test config access
TEST(OllamaAgentTest, ConfigAccess) {
    OllamaConfig config;
    config.model = "mistral:7b";
    OllamaAgent agent(config);

    EXPECT_EQ(agent.config().model, "mistral:7b");
}

// Test message content access
TEST(OllamaAgentTest, MessageWithText) {
    auto msg = Message::with_text("user", "Hello, Ollama!");
    EXPECT_EQ(msg.role(), "user");
    EXPECT_EQ(msg.content_as_str(), "Hello, Ollama!");
}

// --- CallOptions / OptionsAgent wiring (#818) ---

TEST(OllamaAgentTest, IsAnOptionsAgent) {
    OllamaConfig config;
    OllamaAgent agent(config);

    EXPECT_TRUE(supports_options(&agent));
    EXPECT_NE(dynamic_cast<OptionsAgent*>(&agent), nullptr);
}

// build_request_body must omit seed/stop from the options object entirely
// when CallOptions is empty.
TEST(OllamaAgentTest, RequestBodyOmitsSeedAndStopWhenUnset) {
    OllamaConfig config;
    OllamaAgent agent(config);

    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, CallOptions{});

    ASSERT_TRUE(body.contains("options"));
    EXPECT_FALSE(body["options"].contains("seed"));
    EXPECT_FALSE(body["options"].contains("stop"));
}

// Ollama's Options schema supports `seed` and `stop` natively under those
// exact keys, so both are a straight passthrough.
TEST(OllamaAgentTest, RequestBodyIncludesSeedAndStopWhenSet) {
    OllamaConfig config;
    OllamaAgent agent(config);

    auto options = CallOptions{}.with_seed(42).with_stop({"STOP", "END"});
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    ASSERT_TRUE(body.contains("options"));
    const auto& ollama_options = body["options"];

    ASSERT_TRUE(ollama_options.contains("seed"));
    EXPECT_EQ(ollama_options["seed"].get<uint64_t>(), 42u);

    ASSERT_TRUE(ollama_options.contains("stop"));
    std::vector<std::string> stop = ollama_options["stop"].get<std::vector<std::string>>();
    ASSERT_EQ(stop.size(), 2u);
    EXPECT_EQ(stop[0], "STOP");
    EXPECT_EQ(stop[1], "END");
}

// A per-call temperature must override the config default for that one call.
TEST(OllamaAgentTest, RequestBodyPerCallTemperatureOverridesConfigDefault) {
    OllamaConfig config;
    config.temperature = 0.8;
    OllamaAgent agent(config);

    auto options = CallOptions{}.with_temperature(0.1);
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    EXPECT_DOUBLE_EQ(body["options"]["temperature"].get<double>(), 0.1);
}
