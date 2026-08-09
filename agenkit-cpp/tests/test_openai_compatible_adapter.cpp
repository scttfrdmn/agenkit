/**
 * @file test_openai_compatible_adapter.cpp
 * @brief Tests for OpenAI-Compatible adapter
 */

#include <gtest/gtest.h>
#include "agenkit/adapters/openai_compatible_agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include <nlohmann/json.hpp>

using namespace agenkit::core;
using namespace agenkit::adapters;
using json = nlohmann::json;

// Test 1: Constructor with all parameters
TEST(OpenAICompatibleAgentTest, ConstructorWithAllParameters) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.provider = "vllm";
    config.api_key = "test-key";
    config.temperature = 0.5;
    config.max_tokens = 2048;

    EXPECT_NO_THROW({
        OpenAICompatibleAgent agent(config);
        EXPECT_EQ(agent.name(), "vllm");
    });
}

// Test 2: Constructor without provider
TEST(OpenAICompatibleAgentTest, ConstructorWithoutProvider) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";

    EXPECT_NO_THROW({
        OpenAICompatibleAgent agent(config);
        EXPECT_EQ(agent.name(), "openai_compatible");
    });
}

// Test 3: Constructor without API key (optional for local services)
TEST(OpenAICompatibleAgentTest, ConstructorWithoutAPIKey) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.provider = "vllm";

    // API key is optional for local services
    EXPECT_NO_THROW({
        OpenAICompatibleAgent agent(config);
    });
}

// Test 4: Name format matches provider
TEST(OpenAICompatibleAgentTest, NameFormatMatchesProvider) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.provider = "vllm";

    OpenAICompatibleAgent agent(config);
    EXPECT_EQ(agent.name(), "vllm");
}

// Test 5: Name defaults when no provider
TEST(OpenAICompatibleAgentTest, NameDefaultsWithoutProvider) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";

    OpenAICompatibleAgent agent(config);
    EXPECT_EQ(agent.name(), "openai_compatible");
}

// Test 6: Capabilities list with provider
TEST(OpenAICompatibleAgentTest, CapabilitiesWithProvider) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.provider = "vllm";

    OpenAICompatibleAgent agent(config);
    auto caps = agent.capabilities();

    ASSERT_GE(caps.size(), 4);
    EXPECT_EQ(caps[0], "llm");
    EXPECT_EQ(caps[1], "text-generation");
    EXPECT_EQ(caps[2], "openai-compatible");
    EXPECT_EQ(caps[3], "vllm");
}

// Test 7: Capabilities list without provider
TEST(OpenAICompatibleAgentTest, CapabilitiesWithoutProvider) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";

    OpenAICompatibleAgent agent(config);
    auto caps = agent.capabilities();

    ASSERT_EQ(caps.size(), 3);
    EXPECT_EQ(caps[0], "llm");
    EXPECT_EQ(caps[1], "text-generation");
    EXPECT_EQ(caps[2], "openai-compatible");
}

// Test 8: Config getter returns correct values
TEST(OpenAICompatibleAgentTest, ConfigGetterReturnsCorrectValues) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.provider = "vllm";
    config.temperature = 0.8;
    config.max_tokens = 512;

    OpenAICompatibleAgent agent(config);
    const auto& retrieved_config = agent.config();

    EXPECT_EQ(retrieved_config.base_url, "http://localhost:8000/v1");
    EXPECT_EQ(retrieved_config.model, "llama-2-7b");
    EXPECT_EQ(retrieved_config.provider.value(), "vllm");
    EXPECT_DOUBLE_EQ(retrieved_config.temperature, 0.8);
    EXPECT_EQ(retrieved_config.max_tokens, 512);
}

// Test 9: Config setter updates values
TEST(OpenAICompatibleAgentTest, ConfigSetterUpdatesValues) {
    OpenAICompatibleConfig config1;
    config1.base_url = "http://localhost:8000/v1";
    config1.model = "llama-2-7b";
    config1.provider = "vllm";

    OpenAICompatibleAgent agent(config1);

    OpenAICompatibleConfig config2;
    config2.base_url = "http://localhost:8080/v1";
    config2.model = "llama-2-13b";
    config2.provider = "llamacpp";

    agent.set_config(config2);
    const auto& retrieved_config = agent.config();

    EXPECT_EQ(retrieved_config.base_url, "http://localhost:8080/v1");
    EXPECT_EQ(retrieved_config.model, "llama-2-13b");
    EXPECT_EQ(retrieved_config.provider.value(), "llamacpp");
}

// Test 10: Default configuration values
TEST(OpenAICompatibleAgentTest, DefaultConfigurationValues) {
    OpenAICompatibleConfig config;

    EXPECT_EQ(config.base_url, "http://localhost:8000/v1");
    EXPECT_EQ(config.model, "llama-2-7b");
    EXPECT_FALSE(config.provider.has_value());
    EXPECT_FALSE(config.api_key.has_value());
    EXPECT_EQ(config.max_tokens, 1024);
    EXPECT_DOUBLE_EQ(config.temperature, 0.7);
    EXPECT_DOUBLE_EQ(config.top_p, 1.0);
    EXPECT_EQ(config.timeout.count(), 60000);
}

// Test 11: Provider helper - vLLM
TEST(OpenAICompatibleAgentTest, ProviderHelperVLLM) {
    auto config = OpenAICompatibleProviders::vllm("meta-llama/Llama-2-7b-chat-hf");

    EXPECT_EQ(config.base_url, "http://localhost:8000/v1");
    EXPECT_EQ(config.model, "meta-llama/Llama-2-7b-chat-hf");
    EXPECT_EQ(config.provider.value(), "vllm");
}

// Test 12: Provider helper - llama.cpp
TEST(OpenAICompatibleAgentTest, ProviderHelperLlamaCpp) {
    auto config = OpenAICompatibleProviders::llamacpp("llama-2-7b-chat");

    EXPECT_EQ(config.base_url, "http://localhost:8080/v1");
    EXPECT_EQ(config.model, "llama-2-7b-chat");
    EXPECT_EQ(config.provider.value(), "llamacpp");
}

// Test 13: Provider helper - SGLang
TEST(OpenAICompatibleAgentTest, ProviderHelperSGLang) {
    auto config = OpenAICompatibleProviders::sglang("meta-llama/Llama-2-13b-chat-hf");

    EXPECT_EQ(config.base_url, "http://localhost:30000/v1");
    EXPECT_EQ(config.model, "meta-llama/Llama-2-13b-chat-hf");
    EXPECT_EQ(config.provider.value(), "sglang");
}

// Test 14: Provider helper - TensorRT
TEST(OpenAICompatibleAgentTest, ProviderHelperTensorRT) {
    auto config = OpenAICompatibleProviders::tensorrt("llama-2-70b");

    EXPECT_EQ(config.base_url, "http://localhost:8001/v1");
    EXPECT_EQ(config.model, "llama-2-70b");
    EXPECT_EQ(config.provider.value(), "tensorrt");
}

// Test 15: Configuration with custom timeout
TEST(OpenAICompatibleAgentTest, CustomTimeoutConfiguration) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.timeout = std::chrono::milliseconds(120000);

    OpenAICompatibleAgent agent(config);
    EXPECT_EQ(agent.config().timeout.count(), 120000);
}

// Test 16: Configuration with custom temperature
TEST(OpenAICompatibleAgentTest, CustomTemperatureConfiguration) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.temperature = 0.9;

    OpenAICompatibleAgent agent(config);
    EXPECT_DOUBLE_EQ(agent.config().temperature, 0.9);
}

// Test 17: Configuration with custom max_tokens
TEST(OpenAICompatibleAgentTest, CustomMaxTokensConfiguration) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.max_tokens = 4096;

    OpenAICompatibleAgent agent(config);
    EXPECT_EQ(agent.config().max_tokens, 4096);
}

// Test 18: Configuration with custom top_p
TEST(OpenAICompatibleAgentTest, CustomTopPConfiguration) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.top_p = 0.95;

    OpenAICompatibleAgent agent(config);
    EXPECT_DOUBLE_EQ(agent.config().top_p, 0.95);
}

// Test 19: Multiple providers configuration
TEST(OpenAICompatibleAgentTest, MultipleProvidersConfiguration) {
    std::vector<std::string> providers = {
        "vllm", "llamacpp", "sglang", "tensorrt",
        "openllm", "mlc", "tgi", "inferflow"
    };

    for (const auto& provider : providers) {
        OpenAICompatibleConfig config;
        config.base_url = "http://localhost:8000/v1";
        config.model = "test-model";
        config.provider = provider;

        OpenAICompatibleAgent agent(config);
        EXPECT_EQ(agent.name(), provider);

        auto caps = agent.capabilities();
        EXPECT_TRUE(std::find(caps.begin(), caps.end(), provider) != caps.end());
    }
}

// Test 20: Agent creation from helper configs
TEST(OpenAICompatibleAgentTest, AgentCreationFromHelpers) {
    auto vllm_config = OpenAICompatibleProviders::vllm("model1");
    OpenAICompatibleAgent vllm_agent(vllm_config);
    EXPECT_EQ(vllm_agent.name(), "vllm");

    auto llamacpp_config = OpenAICompatibleProviders::llamacpp("model2");
    OpenAICompatibleAgent llamacpp_agent(llamacpp_config);
    EXPECT_EQ(llamacpp_agent.name(), "llamacpp");

    auto sglang_config = OpenAICompatibleProviders::sglang("model3");
    OpenAICompatibleAgent sglang_agent(sglang_config);
    EXPECT_EQ(sglang_agent.name(), "sglang");

    auto tensorrt_config = OpenAICompatibleProviders::tensorrt("model4");
    OpenAICompatibleAgent tensorrt_agent(tensorrt_config);
    EXPECT_EQ(tensorrt_agent.name(), "tensorrt");
}

// --- CallOptions / OptionsAgent wiring (#818) ---

TEST(OpenAICompatibleAgentTest, IsAnOptionsAgent) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    OpenAICompatibleAgent agent(config);

    EXPECT_TRUE(supports_options(&agent));
    EXPECT_NE(dynamic_cast<OptionsAgent*>(&agent), nullptr);
}

// build_request_body must omit seed/stop entirely when CallOptions is empty.
TEST(OpenAICompatibleAgentTest, RequestBodyOmitsSeedAndStopWhenUnset) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    OpenAICompatibleAgent agent(config);

    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, CallOptions{});

    EXPECT_FALSE(body.contains("seed"));
    EXPECT_FALSE(body.contains("stop"));
}

// This adapter shares OpenAI's Chat Completions request shape, so seed/stop
// are a straight passthrough, same as OpenAIAgent.
TEST(OpenAICompatibleAgentTest, RequestBodyIncludesSeedAndStopWhenSet) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    OpenAICompatibleAgent agent(config);

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

// A per-call temperature/max_tokens/top_p must override the config default.
TEST(OpenAICompatibleAgentTest, RequestBodyPerCallOptionsOverrideConfigDefaults) {
    OpenAICompatibleConfig config;
    config.base_url = "http://localhost:8000/v1";
    config.model = "llama-2-7b";
    config.temperature = 0.7;
    config.max_tokens = 1024;
    config.top_p = 1.0;
    OpenAICompatibleAgent agent(config);

    auto options = CallOptions{}.with_temperature(0.2).with_max_tokens(128).with_top_p(0.5);
    auto messages = json::array({{{"role", "user"}, {"content", "hi"}}});
    auto body = agent.build_request_body(messages, options);

    EXPECT_DOUBLE_EQ(body["temperature"].get<double>(), 0.2);
    EXPECT_EQ(body["max_tokens"].get<int>(), 128);
    EXPECT_DOUBLE_EQ(body["top_p"].get<double>(), 0.5);
}
