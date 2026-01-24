/**
 * @file openai_compatible_agent.hpp
 * @brief OpenAI-Compatible API adapter
 *
 * Generic adapter for OpenAI-compatible inference services like vLLM,
 * llama.cpp, SGLang, TensorRT-LLM, and others.
 *
 * This adapter enables Agenkit to work with any service implementing the
 * OpenAI Chat Completions API by configuring the HTTP client with a custom
 * base URL. This provides a consistent interface across different local and
 * self-hosted inference engines.
 *
 * Supported services:
 * - vLLM: High-throughput batch inference
 * - llama.cpp: Lightweight C++ implementation (CPU-friendly)
 * - SGLang: Optimized for complex prompts
 * - TensorRT-LLM: NVIDIA GPU optimized
 * - OpenLLM: Multi-model serving platform
 * - MLC LLM: Mobile and edge deployment
 * - Text Generation Inference (TGI): HuggingFace inference server
 * - Inferflow: High-performance inference
 *
 * @par Example - vLLM
 * @code
 * OpenAICompatibleConfig config;
 * config.base_url = "http://localhost:8000/v1";
 * config.model = "meta-llama/Llama-2-7b-chat-hf";
 * config.provider = "vllm";
 *
 * OpenAICompatibleAgent agent(config);
 * auto msg = Message::with_text("user", "What is machine learning?");
 * auto future = agent.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 *
 * @par Example - llama.cpp
 * @code
 * OpenAICompatibleConfig config;
 * config.base_url = "http://localhost:8080/v1";
 * config.model = "llama-2-7b-chat";
 * config.provider = "llamacpp";
 *
 * OpenAICompatibleAgent agent(config);
 * @endcode
 */

#ifndef AGENKIT_ADAPTERS_OPENAI_COMPATIBLE_AGENT_HPP
#define AGENKIT_ADAPTERS_OPENAI_COMPATIBLE_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <memory>
#include <optional>

namespace agenkit {
namespace adapters {

/**
 * @brief Configuration for OpenAI-Compatible API calls
 *
 * This configuration works with any service implementing the OpenAI
 * Chat Completions API.
 */
struct OpenAICompatibleConfig {
    /// Base URL of the inference service (e.g., "http://localhost:8000/v1")
    /// Must include the /v1 suffix for most services
    std::string base_url{"http://localhost:8000/v1"};

    /// Model name/identifier used by the inference service
    /// Format varies by service:
    /// - vLLM: "meta-llama/Llama-2-7b-chat-hf"
    /// - llama.cpp: "llama-2-7b-chat"
    /// - SGLang: "meta-llama/Llama-2-13b-chat-hf"
    std::string model{"llama-2-7b"};

    /// Optional provider name for metadata and debugging
    /// Examples: "vllm", "llamacpp", "sglang", "tensorrt"
    std::optional<std::string> provider{std::nullopt};

    /// Optional API key. Most local services don't require authentication
    /// Defaults to "not-needed" if not provided
    std::optional<std::string> api_key{std::nullopt};

    /// Maximum tokens to generate (default: 1024)
    int max_tokens{1024};

    /// Temperature 0-2 (default: 0.7)
    double temperature{0.7};

    /// Top P sampling (default: 1.0)
    double top_p{1.0};

    /// Request timeout in seconds (default: 60)
    int timeout_seconds{60};
};

/**
 * @brief Agent adapter for OpenAI-compatible services
 *
 * This adapter wraps OpenAI-compatible Chat Completions APIs, converting Agent
 * messages to API calls and responses back to Agent messages.
 *
 * Features:
 * - Supports 8+ OpenAI-compatible inference services
 * - Async message processing
 * - Configurable temperature, top_p, and max_tokens
 * - Provider metadata for debugging and monitoring
 * - Error handling with typed errors
 *
 * @par Example
 * @code
 * // vLLM local deployment
 * OpenAICompatibleConfig config;
 * config.base_url = "http://localhost:8000/v1";
 * config.model = "meta-llama/Llama-2-7b-chat-hf";
 * config.provider = "vllm";
 *
 * OpenAICompatibleAgent agent(config);
 * auto msg = Message::with_text("user", "What is machine learning?");
 * auto future = agent.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class OpenAICompatibleAgent : public core::Agent {
public:
    /**
     * @brief Construct an OpenAI-compatible agent with configuration
     *
     * @param config Configuration including base URL, model, and optional provider name
     *
     * @par Example
     * @code
     * OpenAICompatibleConfig config;
     * config.base_url = "http://localhost:8000/v1";
     * config.model = "llama-2-7b";
     * config.provider = "vllm";
     *
     * OpenAICompatibleAgent agent(config);
     * @endcode
     */
    explicit OpenAICompatibleAgent(OpenAICompatibleConfig config);

    /**
     * @brief Get agent name
     * @return Provider name if set, otherwise "openai_compatible"
     */
    std::string name() const override;

    /**
     * @brief Process message through OpenAI-compatible API
     *
     * Converts message to OpenAI API format, makes HTTP request,
     * and converts response back to Agent message format with
     * provider metadata for debugging and monitoring.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities including provider name
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const OpenAICompatibleConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const OpenAICompatibleConfig& config);

private:
    OpenAICompatibleConfig config_;

    /**
     * @brief Make HTTP request to OpenAI-compatible API
     * @param messages JSON array of messages
     * @return JSON response or error
     */
    core::Result<nlohmann::json, core::AgentError>
    call_api(const nlohmann::json& messages);

    /**
     * @brief Convert Agent message to OpenAI API format
     *
     * Maps agent role to assistant for OpenAI compatibility.
     */
    nlohmann::json message_to_json(const core::Message& message);

    /**
     * @brief Convert OpenAI API response to Agent message
     *
     * Includes provider metadata for debugging and monitoring.
     */
    core::Message json_to_message(const nlohmann::json& response);
};

/**
 * @brief Provider configuration helpers
 *
 * Convenience functions for creating configurations for common services.
 */
namespace OpenAICompatibleProviders {
    /**
     * @brief vLLM configuration (default port 8000)
     * @param model Model name/path
     * @return Configured OpenAICompatibleConfig
     */
    inline OpenAICompatibleConfig vllm(const std::string& model) {
        OpenAICompatibleConfig config;
        config.base_url = "http://localhost:8000/v1";
        config.model = model;
        config.provider = "vllm";
        return config;
    }

    /**
     * @brief llama.cpp configuration (default port 8080)
     * @param model Model name/path
     * @return Configured OpenAICompatibleConfig
     */
    inline OpenAICompatibleConfig llamacpp(const std::string& model) {
        OpenAICompatibleConfig config;
        config.base_url = "http://localhost:8080/v1";
        config.model = model;
        config.provider = "llamacpp";
        return config;
    }

    /**
     * @brief SGLang configuration (default port 30000)
     * @param model Model name/path
     * @return Configured OpenAICompatibleConfig
     */
    inline OpenAICompatibleConfig sglang(const std::string& model) {
        OpenAICompatibleConfig config;
        config.base_url = "http://localhost:30000/v1";
        config.model = model;
        config.provider = "sglang";
        return config;
    }

    /**
     * @brief TensorRT-LLM configuration (default port 8001)
     * @param model Model name/path
     * @return Configured OpenAICompatibleConfig
     */
    inline OpenAICompatibleConfig tensorrt(const std::string& model) {
        OpenAICompatibleConfig config;
        config.base_url = "http://localhost:8001/v1";
        config.model = model;
        config.provider = "tensorrt";
        return config;
    }
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_OPENAI_COMPATIBLE_AGENT_HPP
