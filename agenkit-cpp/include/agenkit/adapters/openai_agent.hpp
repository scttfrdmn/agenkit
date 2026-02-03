/**
 * @file openai_agent.hpp
 * @brief OpenAI API adapter
 *
 * Adapter for calling OpenAI's GPT API via HTTP.
 * Supports GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and other OpenAI models.
 *
 * @see https://platform.openai.com/docs/api-reference/chat
 */

#ifndef AGENKIT_ADAPTERS_OPENAI_AGENT_HPP
#define AGENKIT_ADAPTERS_OPENAI_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <memory>
#include <functional>

namespace agenkit {
namespace adapters {

/**
 * @brief Configuration for OpenAI API calls
 */
struct OpenAIConfig {
    /// API key (required) - get from https://platform.openai.com/api-keys
    std::string api_key;

    /// Model to use (default: gpt-4-turbo)
    std::string model{"gpt-4-turbo"};

    /// Maximum tokens to generate (default: 1024)
    int max_tokens{1024};

    /// Temperature 0-2 (default: 0.7)
    double temperature{0.7};

    /// Top P sampling (default: 1.0)
    double top_p{1.0};

    /// Frequency penalty -2.0 to 2.0 (default: 0.0)
    double frequency_penalty{0.0};

    /// Presence penalty -2.0 to 2.0 (default: 0.0)
    double presence_penalty{0.0};

    /// API endpoint (default: OpenAI production)
    std::string api_base{"https://api.openai.com"};

    /// Request timeout in milliseconds (default: 60000)
    std::chrono::milliseconds timeout{60000};
};

/**
 * @brief Agent adapter for OpenAI API
 *
 * This adapter wraps the OpenAI Chat Completions API, converting Agent messages
 * to OpenAI API calls and responses back to Agent messages.
 *
 * Features:
 * - Supports all OpenAI chat models (GPT-4, GPT-3.5, etc.)
 * - Async message processing
 * - Configurable temperature, top_p, and penalties
 * - Error handling with typed errors
 *
 * @par Example
 * @code
 * OpenAIConfig config;
 * config.api_key = std::getenv("OPENAI_API_KEY");
 * config.model = "gpt-4-turbo";
 *
 * OpenAIAgent gpt(config);
 * auto msg = Message::with_text("user", "What is the capital of France?");
 * auto future = gpt.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class OpenAIAgent : public core::Agent {
public:
    /**
     * @brief Construct an OpenAI agent with configuration
     *
     * @param config Configuration including API key and model
     * @throws std::invalid_argument if api_key is empty
     */
    explicit OpenAIAgent(OpenAIConfig config);

    /**
     * @brief Get agent name
     * @return "openai"
     */
    std::string name() const override;

    /**
     * @brief Process message through OpenAI API
     *
     * Converts message to OpenAI API format, makes HTTP request,
     * and converts response back to Agent message format.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Stream response from OpenAI API
     *
     * Makes a streaming request to OpenAI and invokes callback for each text chunk.
     * Callback can return false to stop streaming early.
     *
     * @param message Input message (role and content)
     * @param callback Function called with each text chunk (return false to stop)
     * @return Result indicating success or error
     */
    core::Result<void, core::AgentError>
    stream(core::Message message, std::function<bool(const std::string&)> callback);

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["llm", "text-generation", "openai"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const OpenAIConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const OpenAIConfig& config);

private:
    OpenAIConfig config_;

    /**
     * @brief Make HTTP request to OpenAI API
     * @param messages JSON array of messages
     * @return JSON response or error
     */
    core::Result<nlohmann::json, core::AgentError>
    call_api(const nlohmann::json& messages);

    /**
     * @brief Convert Agent message to OpenAI API format
     */
    nlohmann::json message_to_json(const core::Message& message);

    /**
     * @brief Convert OpenAI API response to Agent message
     */
    core::Message json_to_message(const nlohmann::json& response);
};

/**
 * @brief Available OpenAI models (November 2025)
 */
namespace OpenAIModels {
    /// GPT-4 Turbo - Most capable, 128k context
    constexpr const char* GPT_4_TURBO = "gpt-4-turbo";

    /// GPT-4 - High capability, 8k context
    constexpr const char* GPT_4 = "gpt-4";

    /// GPT-4o - Multimodal flagship
    constexpr const char* GPT_4O = "gpt-4o";

    /// GPT-4o Mini - Fast and affordable
    constexpr const char* GPT_4O_MINI = "gpt-4o-mini";

    /// GPT-3.5 Turbo - Fast and cost-effective
    constexpr const char* GPT_3_5_TURBO = "gpt-3.5-turbo";
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_OPENAI_AGENT_HPP
