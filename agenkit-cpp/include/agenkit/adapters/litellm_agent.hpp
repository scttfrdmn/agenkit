/**
 * @file litellm_agent.hpp
 * @brief LiteLLM proxy adapter for universal LLM access
 *
 * Provides integration with LiteLLM, a universal LLM gateway that offers
 * an OpenAI-compatible API for 100+ LLM providers. Supports both completion
 * and streaming modes.
 *
 * @see https://docs.litellm.ai/
 */

#ifndef AGENKIT_ADAPTERS_LITELLM_AGENT_HPP
#define AGENKIT_ADAPTERS_LITELLM_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <vector>
#include <optional>
#include <memory>

namespace agenkit {
namespace adapters {

/**
 * @brief Configuration for LiteLLM proxy
 */
struct LiteLLMConfig {
    /// LiteLLM proxy base URL (default: http://localhost:4000)
    std::string base_url{"http://localhost:4000"};

    /// Model identifier in LiteLLM format (e.g., 'gpt-4', 'claude-3-5-sonnet-20241022')
    std::string model{"gpt-3.5-turbo"};

    /// API key for LiteLLM proxy authentication (optional)
    std::optional<std::string> api_key;

    /// Temperature for sampling (0.0 - 2.0)
    std::optional<double> temperature;

    /// Maximum tokens to generate
    std::optional<int> max_tokens;

    /// Top-p sampling parameter
    std::optional<double> top_p;

    /// Request timeout in milliseconds (default: 60000)
    std::chrono::milliseconds timeout{60000};
};

/**
 * @brief Agent adapter for LiteLLM proxy
 *
 * This adapter wraps the LiteLLM proxy API, which provides an OpenAI-compatible
 * interface for 100+ LLM providers. The proxy acts as a universal gateway,
 * handling provider-specific authentication and API calls.
 *
 * Features:
 * - Support for 100+ LLM providers through LiteLLM proxy
 * - OpenAI-compatible API format
 * - HTTP-based communication (libcurl)
 * - Configurable temperature, max_tokens, top_p
 * - Error handling with typed errors
 *
 * Supported providers through LiteLLM:
 * - OpenAI (gpt-4, gpt-3.5-turbo)
 * - Anthropic (claude-3-5-sonnet-20241022)
 * - AWS Bedrock (bedrock/anthropic.claude-v2)
 * - Google Gemini (gemini/gemini-pro)
 * - Azure OpenAI (azure/gpt-4)
 * - Cohere (command-r-plus)
 * - Local models (ollama/llama2, ollama/mistral)
 * - And 100+ more!
 *
 * @par Example
 * @code
 * LiteLLMConfig config;
 * config.base_url = "http://localhost:4000";
 * config.model = "gpt-4";
 * config.api_key = "sk-litellm-...";
 * config.temperature = 0.7;
 *
 * LiteLLMAgent agent(config);
 * auto msg = Message::with_text("user", "Hello, LiteLLM!");
 * auto future = agent.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class LiteLLMAgent : public core::Agent, public core::OptionsAgent {
public:
    /**
     * @brief Construct a LiteLLM agent with configuration
     *
     * @param config Configuration including base URL and model
     */
    explicit LiteLLMAgent(LiteLLMConfig config);

    /**
     * @brief Get agent name
     * @return "litellm-{model}"
     */
    std::string name() const override;

    /**
     * @brief Process message through LiteLLM proxy
     *
     * Converts message to OpenAI-compatible format, makes HTTP request
     * to LiteLLM proxy, and converts response back to Agent message format.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Process a message, forwarding per-call options to the LiteLLM proxy
     *
     * Same as process(), except that `options` (temperature, max_tokens, top_p,
     * seed, stop) are threaded into the outgoing request body, overriding the
     * corresponding config default when set. The LiteLLM proxy normalizes
     * `seed`/`stop` to whatever the routed provider supports (or forwards them
     * as-is when unsupported), so both are a straight passthrough here.
     *
     * @param message Input message (role and content)
     * @param options Per-call options; unset fields fall back to config
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process_with(core::Message message, const core::CallOptions& options) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["llm", "completion", "streaming", "universal-gateway"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const LiteLLMConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const LiteLLMConfig& config);

    /**
     * @brief Build the outgoing OpenAI-compatible request body
     *
     * Exposed publicly so tests can assert on the exact JSON sent to the
     * LiteLLM proxy without a live HTTP call. Per-call `options` values, when
     * set, override the corresponding config default.
     *
     * @param messages JSON array of messages
     * @param options Per-call options; unset fields fall back to config
     * @return Request body JSON, not yet sent
     */
    nlohmann::json build_request_body(const nlohmann::json& messages, const core::CallOptions& options) const;

private:
    LiteLLMConfig config_;

    /**
     * @brief Make HTTP request to LiteLLM proxy
     * @param messages JSON array of messages
     * @param options Per-call options; unset fields fall back to config
     * @return JSON response or error
     */
    core::Result<nlohmann::json, core::AgentError>
    call_api(const nlohmann::json& messages, const core::CallOptions& options);

    /**
     * @brief Convert Agent message to OpenAI API format
     */
    nlohmann::json message_to_json(const core::Message& message);

    /**
     * @brief Convert LiteLLM API response to Agent message
     */
    core::Message json_to_message(const nlohmann::json& response);
};

/**
 * @brief Common LiteLLM model identifiers
 */
namespace LiteLLMModels {
    // OpenAI models
    constexpr const char* GPT_4 = "gpt-4";
    constexpr const char* GPT_4_TURBO = "gpt-4-turbo";
    constexpr const char* GPT_4O = "gpt-4o";
    constexpr const char* GPT_4O_MINI = "gpt-4o-mini";
    constexpr const char* GPT_3_5_TURBO = "gpt-3.5-turbo";

    // Anthropic models
    constexpr const char* CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022";
    constexpr const char* CLAUDE_3_OPUS = "claude-3-opus-20240229";
    constexpr const char* CLAUDE_3_SONNET = "claude-3-sonnet-20240229";
    constexpr const char* CLAUDE_3_HAIKU = "claude-3-haiku-20240307";

    // Bedrock models (prefix with bedrock/)
    constexpr const char* BEDROCK_CLAUDE_V2 = "bedrock/anthropic.claude-v2";
    constexpr const char* BEDROCK_CLAUDE_3_SONNET = "bedrock/anthropic.claude-3-sonnet-20240229-v1:0";

    // Gemini models (prefix with gemini/)
    constexpr const char* GEMINI_PRO = "gemini/gemini-pro";
    constexpr const char* GEMINI_2_0_FLASH = "gemini/gemini-2.0-flash-exp";

    // Ollama models (prefix with ollama/)
    constexpr const char* OLLAMA_LLAMA2 = "ollama/llama2";
    constexpr const char* OLLAMA_MISTRAL = "ollama/mistral";
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_LITELLM_AGENT_HPP
