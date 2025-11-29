/**
 * @file ollama_agent.hpp
 * @brief Ollama local LLM adapter
 *
 * Adapter for calling local Ollama models via HTTP.
 * Supports all Ollama models: Llama, Mistral, Qwen, Phi, etc.
 *
 * @see https://github.com/ollama/ollama/blob/main/docs/api.md
 */

#ifndef AGENKIT_ADAPTERS_OLLAMA_AGENT_HPP
#define AGENKIT_ADAPTERS_OLLAMA_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <memory>

namespace agenkit {
namespace adapters {

/**
 * @brief Configuration for Ollama API calls
 */
struct OllamaConfig {
    /// Ollama host (default: http://localhost:11434)
    std::string host{"http://localhost:11434"};

    /// Model to use (e.g., "llama3.3", "mistral", "qwen2.5")
    std::string model{"llama3.3"};

    /// Temperature 0-1 (default: 0.8)
    double temperature{0.8};

    /// Request timeout in seconds (default: 120 for local)
    int timeout_seconds{120};

    /// Stream responses (default: false)
    bool stream{false};

    /// System prompt (optional)
    std::string system;
};

/**
 * @brief Agent adapter for Ollama local LLMs
 *
 * This adapter wraps the Ollama HTTP API, enabling use of local LLMs
 * without API costs or network latency.
 *
 * Features:
 * - Supports all Ollama models (Llama, Mistral, Qwen, Phi, etc.)
 * - Free and private (runs locally)
 * - Fast iteration (no network)
 * - Async message processing
 * - Error handling with typed errors
 *
 * @par Setup
 * @code
 * # Install Ollama
 * brew install ollama  # macOS
 * # or download from ollama.ai
 *
 * # Start Ollama server
 * ollama serve
 *
 * # Pull a model
 * ollama pull llama3.3
 * @endcode
 *
 * @par Example
 * @code
 * OllamaConfig config;
 * config.host = "http://localhost:11434";
 * config.model = "llama3.3";
 * config.temperature = 0.7;
 *
 * OllamaAgent ollama(config);
 * auto msg = Message::with_text("user", "What is AgentKit?");
 * auto future = ollama.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class OllamaAgent : public core::Agent {
public:
    /**
     * @brief Construct an Ollama agent with configuration
     *
     * @param config Configuration including host and model
     * @throws std::invalid_argument if model is empty
     */
    explicit OllamaAgent(OllamaConfig config);

    /**
     * @brief Get agent name
     * @return "ollama"
     */
    std::string name() const override;

    /**
     * @brief Process message through Ollama API
     *
     * Converts message to Ollama API format, makes HTTP request,
     * and converts response back to Agent message format.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["llm", "text-generation", "ollama", "local"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const OllamaConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const OllamaConfig& config);

    /**
     * @brief Check if Ollama server is running
     * @return true if server responds to health check
     */
    bool is_available() const;

    /**
     * @brief List available models
     * @return Vector of model names or empty if unavailable
     */
    std::vector<std::string> list_models() const;

private:
    OllamaConfig config_;

    /**
     * @brief Make HTTP request to Ollama API
     * @param messages JSON array of messages
     * @return JSON response or error
     */
    core::Result<nlohmann::json, core::AgentError>
    call_api(const nlohmann::json& messages);

    /**
     * @brief Convert Agent message to Ollama API format
     */
    nlohmann::json message_to_json(const core::Message& message);

    /**
     * @brief Convert Ollama API response to Agent message
     */
    core::Message json_to_message(const nlohmann::json& response);
};

/**
 * @brief Popular Ollama models (examples)
 */
namespace OllamaModels {
    /// Llama 3.3 70B - Meta's latest (November 2024)
    constexpr const char* LLAMA_3_3 = "llama3.3";

    /// Llama 3.2 3B - Smaller, faster
    constexpr const char* LLAMA_3_2_3B = "llama3.2:3b";

    /// Mistral 7B - Fast and capable
    constexpr const char* MISTRAL_7B = "mistral:7b";

    /// Qwen 2.5 7B - Alibaba's latest
    constexpr const char* QWEN_2_5_7B = "qwen2.5:7b";

    /// Phi-3 Mini - Microsoft's 3.8B
    constexpr const char* PHI_3_MINI = "phi3:mini";

    /// Gemma 2 9B - Google's open model
    constexpr const char* GEMMA_2_9B = "gemma2:9b";
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_OLLAMA_AGENT_HPP
