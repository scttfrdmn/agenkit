/**
 * @file claude_agent.hpp
 * @brief Anthropic Claude API adapter
 *
 * Adapter for calling Anthropic's Claude API via HTTP.
 * Supports Claude 3 Opus, Sonnet, and Haiku models.
 *
 * @see https://docs.anthropic.com/claude/reference/messages_post
 */

#ifndef AGENKIT_ADAPTERS_CLAUDE_AGENT_HPP
#define AGENKIT_ADAPTERS_CLAUDE_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <memory>
#include <functional>

namespace agenkit {
namespace adapters {

/**
 * @brief Configuration for Claude API calls
 */
struct ClaudeConfig {
    /// API key (required) - get from https://console.anthropic.com/
    std::string api_key;

    /// Model to use (default: claude-sonnet-4-6)
    std::string model{"claude-sonnet-4-6"};

    /// Maximum tokens to generate (default: 4096)
    int max_tokens{4096};

    /// Temperature 0-1 (default: 1.0)
    double temperature{1.0};

    /// API endpoint (default: Anthropic production)
    std::string api_base{"https://api.anthropic.com"};

    /// API version (default: 2023-06-01)
    std::string api_version{"2023-06-01"};

    /// Request timeout in milliseconds (default: 60000)
    std::chrono::milliseconds timeout{60000};
};

/**
 * @brief Agent adapter for Anthropic Claude API
 *
 * This adapter wraps the Anthropic Claude API, converting Agent messages
 * to Claude API calls and responses back to Agent messages.
 *
 * Features:
 * - Supports all Claude 3 models (Opus, Sonnet, Haiku)
 * - Async message processing
 * - Configurable temperature and max tokens
 * - Error handling with typed errors
 *
 * @par Example
 * @code
 * ClaudeConfig config;
 * config.api_key = std::getenv("ANTHROPIC_API_KEY");
 * config.model = "claude-3-5-sonnet-20241022";
 *
 * ClaudeAgent claude(config);
 * auto msg = Message::with_text("user", "What is the capital of France?");
 * auto future = claude.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class ClaudeAgent : public core::Agent {
public:
    /**
     * @brief Construct a Claude agent with configuration
     *
     * @param config Configuration including API key and model
     * @throws std::invalid_argument if api_key is empty
     */
    explicit ClaudeAgent(ClaudeConfig config);

    /**
     * @brief Get agent name
     * @return "claude"
     */
    std::string name() const override;

    /**
     * @brief Process message through Claude API
     *
     * Converts message to Claude API format, makes HTTP request,
     * and converts response back to Agent message format.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["llm", "text-generation", "claude"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const ClaudeConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const ClaudeConfig& config);

    /**
     * @brief Stream completion chunks from Claude API
     *
     * Streams response text as it arrives from the API using Server-Sent Events (SSE).
     * The callback function is invoked for each text chunk received.
     *
     * @param message Input message (role and content)
     * @param callback Function called for each chunk: (const std::string& text) -> void
     *                 Returns false to stop streaming early
     * @return Result indicating success or error
     *
     * @par Example
     * @code
     * auto msg = Message::with_text("user", "Count to 10");
     * auto result = claude.stream(std::move(msg), [](const std::string& chunk) {
     *     std::cout << chunk << std::flush;
     *     return true;  // Continue streaming
     * });
     * @endcode
     */
    core::Result<void, core::AgentError>
    stream(core::Message message, std::function<bool(const std::string&)> callback);

private:
    ClaudeConfig config_;

    /**
     * @brief Make HTTP request to Claude API
     * @param messages JSON array of messages
     * @return JSON response or error
     */
    core::Result<nlohmann::json, core::AgentError>
    call_api(const nlohmann::json& messages);

    /**
     * @brief Convert Agent message to Claude API format
     */
    nlohmann::json message_to_json(const core::Message& message);

    /**
     * @brief Convert Claude API response to Agent message
     */
    core::Message json_to_message(const nlohmann::json& response);
};

/**
 * @brief Available Claude models (November 2025)
 */
namespace ClaudeModels {
    /// Claude Sonnet 4 - Latest and most capable (November 2025)
    constexpr const char* SONNET_4 = "claude-sonnet-4-6";

    /// Claude 3.5 Sonnet v2 - Previous generation
    constexpr const char* SONNET_3_5_V2 = "claude-3-5-sonnet-20241022";

    /// Claude 3.5 Sonnet - Original 3.5
    constexpr const char* SONNET_3_5 = "claude-3-5-sonnet-20240620";

    /// Claude 3.5 Haiku - Fast and cost-effective
    constexpr const char* HAIKU_3_5 = "claude-3-5-haiku-20241022";
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_CLAUDE_AGENT_HPP
