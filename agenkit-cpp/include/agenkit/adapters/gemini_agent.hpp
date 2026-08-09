/**
 * @file gemini_agent.hpp
 * @brief Google Gemini API adapter
 *
 * Provides integration with Google's Gemini models via REST API.
 * Supports Gemini 2.0 Flash, Gemini 1.5 Pro, and other Gemini models.
 *
 * @see https://ai.google.dev/docs
 */

#ifndef AGENKIT_ADAPTERS_GEMINI_AGENT_HPP
#define AGENKIT_ADAPTERS_GEMINI_AGENT_HPP

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
 * @brief Configuration for Gemini API
 */
struct GeminiConfig {
    /// Google API key (optional - reads from GEMINI_API_KEY or GOOGLE_API_KEY if not set)
    std::optional<std::string> api_key;

    /// Model to use (default: gemini-2.0-flash-exp)
    std::string model{"gemini-2.0-flash-exp"};

    /// Temperature for sampling (0.0 - 2.0)
    std::optional<double> temperature;

    /// Maximum tokens to generate
    std::optional<int> max_tokens;

    /// Top-p sampling parameter
    std::optional<double> top_p;

    /// Top-k sampling parameter
    std::optional<int> top_k;

    /// Stop sequences
    std::vector<std::string> stop_sequences;

    /// API endpoint (default: Google AI production)
    std::string api_base{"https://generativelanguage.googleapis.com"};

    /// Request timeout in milliseconds (default: 60000)
    std::chrono::milliseconds timeout{60000};
};

/**
 * @brief Agent adapter for Google Gemini API
 *
 * This adapter wraps the Google Gemini REST API, converting Agent messages
 * to Gemini API calls and responses back to Agent messages.
 *
 * Features:
 * - Support for Gemini 2.0, Gemini 1.5 Pro, and other Gemini models
 * - REST API client (libcurl)
 * - Configurable temperature, top_p, top_k, max_tokens
 * - Stop sequences support
 * - Error handling with typed errors
 * - Automatic API key loading from environment variables
 *
 * Supported models:
 * - gemini-2.0-flash-exp (fastest, experimental)
 * - gemini-1.5-pro (most capable)
 * - gemini-1.5-flash (fast and efficient)
 *
 * @par Example
 * @code
 * GeminiConfig config;
 * config.api_key = std::getenv("GEMINI_API_KEY");
 * config.model = "gemini-2.0-flash-exp";
 * config.temperature = 0.7;
 * config.max_tokens = 1024;
 *
 * GeminiAgent gemini(config);
 * auto msg = Message::with_text("user", "Explain quantum computing");
 * auto future = gemini.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class GeminiAgent : public core::Agent, public core::OptionsAgent {
public:
    /**
     * @brief Construct a Gemini agent with configuration
     *
     * @param config Configuration including API key and model
     * @throws std::invalid_argument if API key cannot be found
     */
    explicit GeminiAgent(GeminiConfig config);

    /**
     * @brief Get agent name
     * @return "gemini-{model}"
     */
    std::string name() const override;

    /**
     * @brief Process message through Gemini API
     *
     * Converts message to Gemini API format, makes HTTP request,
     * and converts response back to Agent message format.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Process a message, forwarding per-call options to the Gemini API
     *
     * Same as process(), except that `options` (temperature, max_tokens, top_p,
     * seed, stop) are threaded into `generationConfig`, overriding the
     * corresponding config default for that one call. Gemini's REST API
     * supports `seed` directly (an integer field on `generationConfig`) and
     * `stopSequences` (`options.stop` overrides `config_.stop_sequences`
     * rather than merging with it, for that one call).
     *
     * @param message Input message (role and content)
     * @param options Per-call options; unset fields fall back to config
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process_with(core::Message message, const core::CallOptions& options) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["llm", "completion", "chat"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const GeminiConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const GeminiConfig& config);

    /**
     * @brief Build the outgoing generateContent request body
     *
     * Exposed publicly so tests can assert on the exact JSON sent to Gemini
     * without a live HTTP call. Per-call `options` values, when set, override
     * the corresponding config default in `generationConfig`.
     *
     * @param contents JSON array of content
     * @param options Per-call options; unset fields fall back to config
     * @return Request body JSON, not yet sent
     */
    nlohmann::json build_request_body(const nlohmann::json& contents, const core::CallOptions& options) const;

    /**
     * @brief Stream completion chunks from Gemini API
     *
     * Streams response text as it arrives from the API using newline-delimited JSON.
     * The callback function is invoked for each text chunk received.
     *
     * @param message Input message (role and content)
     * @param callback Function called for each chunk: (const std::string& text) -> bool
     *                 Returns false to stop streaming early, true to continue
     * @return Result indicating success or error
     *
     * @par Example
     * @code
     * auto msg = Message::with_text("user", "Count to 10");
     * auto result = gemini.stream(std::move(msg), [](const std::string& chunk) {
     *     std::cout << chunk << std::flush;
     *     return true;  // Continue streaming
     * });
     * @endcode
     */
    core::Result<void, core::AgentError>
    stream(core::Message message, std::function<bool(const std::string&)> callback);

private:
    GeminiConfig config_;

    /**
     * @brief Make HTTP request to Gemini API
     * @param contents JSON array of content
     * @param options Per-call options; unset fields fall back to config
     * @return JSON response or error
     */
    core::Result<nlohmann::json, core::AgentError>
    call_api(const nlohmann::json& contents, const core::CallOptions& options);

    /**
     * @brief Convert Agent message to Gemini API format
     * @param message Agent message
     * @return JSON content object
     */
    nlohmann::json message_to_json(const core::Message& message);

    /**
     * @brief Convert Gemini API response to Agent message
     * @param response API response JSON
     * @return Agent message
     */
    core::Message json_to_message(const nlohmann::json& response);

    /**
     * @brief Load API key from environment if not set
     * @throws std::invalid_argument if API key cannot be found
     */
    void load_api_key_from_env();
};

/**
 * @brief Available Gemini models
 */
namespace GeminiModels {
    /// Gemini 2.0 Flash - Experimental, fastest
    constexpr const char* GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp";

    /// Gemini 1.5 Pro - Most capable, balanced
    constexpr const char* GEMINI_1_5_PRO = "gemini-1.5-pro";

    /// Gemini 1.5 Flash - Fast and efficient
    constexpr const char* GEMINI_1_5_FLASH = "gemini-1.5-flash";

    /// Gemini Pro (legacy)
    constexpr const char* GEMINI_PRO = "gemini-pro";
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_GEMINI_AGENT_HPP
