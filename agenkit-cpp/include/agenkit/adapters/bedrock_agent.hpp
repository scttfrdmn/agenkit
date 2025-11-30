/**
 * @file bedrock_agent.hpp
 * @brief Amazon Bedrock API adapter
 *
 * Provides integration with Amazon Bedrock's foundation models including
 * Claude, Llama, Mistral, and Titan via the Converse API.
 *
 * NOTE: This implementation requires the AWS SDK for C++ (aws-sdk-cpp) which
 * must be installed separately. In particular, the bedrockruntime component
 * is required.
 *
 * Installation:
 *   # Install AWS SDK for C++
 *   git clone --recurse-submodules https://github.com/aws/aws-sdk-cpp
 *   cd aws-sdk-cpp
 *   mkdir build && cd build
 *   cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_ONLY="bedrock-runtime"
 *   make && sudo make install
 *
 * @see https://docs.aws.amazon.com/bedrock/latest/userguide/
 */

#ifndef AGENKIT_ADAPTERS_BEDROCK_AGENT_HPP
#define AGENKIT_ADAPTERS_BEDROCK_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <vector>
#include <optional>
#include <memory>

// Forward declarations for AWS SDK types
namespace Aws {
namespace BedrockRuntime {
    class BedrockRuntimeClient;
}
}

namespace agenkit {
namespace adapters {

/**
 * @brief Configuration for Bedrock API
 */
struct BedrockConfig {
    /// AWS region (default: us-east-1)
    std::string region{"us-east-1"};

    /// Bedrock model identifier (e.g., 'anthropic.claude-3-5-sonnet-20241022-v2:0')
    std::string model{"anthropic.claude-3-5-sonnet-20241022-v2:0"};

    /// AWS access key ID (optional - uses default credential chain if not provided)
    std::optional<std::string> access_key_id;

    /// AWS secret access key (optional - uses default credential chain if not provided)
    std::optional<std::string> secret_access_key;

    /// AWS session token (optional)
    std::optional<std::string> session_token;

    /// Temperature for sampling (0.0 - 1.0)
    std::optional<double> temperature;

    /// Maximum tokens to generate
    std::optional<int> max_tokens;

    /// Top-p sampling parameter
    std::optional<double> top_p;

    /// Stop sequences
    std::vector<std::string> stop_sequences;

    /// Request timeout in seconds (default: 60)
    int timeout_seconds{60};
};

/**
 * @brief Agent adapter for Amazon Bedrock API
 *
 * This adapter wraps the AWS Bedrock Converse API, converting Agent messages
 * to Bedrock API calls and responses back to Agent messages.
 *
 * Features:
 * - Support for Claude, Llama, Mistral, Titan, and other Bedrock models
 * - Converse API for unified interface across models
 * - Configurable temperature, top_p, max_tokens
 * - Stop sequences support
 * - Error handling with typed errors
 * - AWS credential chain support (IAM roles, env vars, profiles)
 * - System message support
 *
 * Popular model IDs:
 * - anthropic.claude-3-5-sonnet-20241022-v2:0 - Claude 3.5 Sonnet
 * - anthropic.claude-3-haiku-20240307-v1:0 - Claude 3 Haiku
 * - meta.llama3-2-90b-instruct-v1:0 - Llama 3.2 90B
 * - mistral.mistral-large-2407-v1:0 - Mistral Large
 * - amazon.titan-text-premier-v1:0 - Amazon Titan Premier
 *
 * @par Example
 * @code
 * BedrockConfig config;
 * config.region = "us-east-1";
 * config.model = "anthropic.claude-3-5-sonnet-20241022-v2:0";
 * config.temperature = 0.7;
 * config.max_tokens = 4096;
 *
 * BedrockAgent bedrock(config);
 * auto msg = Message::with_text("user", "Explain machine learning");
 * auto future = bedrock.process(std::move(msg));
 * auto result = future.get();
 *
 * if (result.is_ok()) {
 *     std::cout << result.unwrap().content_as_str() << std::endl;
 * }
 * @endcode
 */
class BedrockAgent : public core::Agent {
public:
    /**
     * @brief Construct a Bedrock agent with configuration
     *
     * @param config Configuration including region and model
     * @throws std::runtime_error if AWS SDK initialization fails
     */
    explicit BedrockAgent(BedrockConfig config);

    /**
     * @brief Destructor
     */
    ~BedrockAgent() override;

    /**
     * @brief Get agent name
     * @return "bedrock-{model}"
     */
    std::string name() const override;

    /**
     * @brief Process message through Bedrock API
     *
     * Converts message to Bedrock Converse API format, makes API request,
     * and converts response back to Agent message format.
     *
     * @param message Input message (role and content)
     * @return Future with Result containing response or error
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get agent capabilities
     * @return List of capabilities: ["llm", "completion", "chat"]
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Get current configuration
     * @return Reference to config
     */
    const BedrockConfig& config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const BedrockConfig& config);

private:
    BedrockConfig config_;
#ifdef AGENKIT_HAS_AWS_SDK
    std::unique_ptr<Aws::BedrockRuntime::BedrockRuntimeClient> client_;
#else
    void* client_{nullptr};  // Placeholder when AWS SDK not available
#endif

    /**
     * @brief Initialize AWS SDK and create client
     */
    void initialize_client();

    /**
     * @brief Make API request to Bedrock Converse API
     * @param message Agent message
     * @return Agent message response or error
     */
    core::Result<core::Message, core::AgentError>
    call_converse_api(const core::Message& message);
};

/**
 * @brief Available Bedrock models
 */
namespace BedrockModels {
    // Anthropic Claude models
    constexpr const char* CLAUDE_3_5_SONNET_V2 = "anthropic.claude-3-5-sonnet-20241022-v2:0";
    constexpr const char* CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20240620-v1:0";
    constexpr const char* CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0";
    constexpr const char* CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0";
    constexpr const char* CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0";

    // Meta Llama models
    constexpr const char* LLAMA_3_2_90B = "meta.llama3-2-90b-instruct-v1:0";
    constexpr const char* LLAMA_3_2_11B = "meta.llama3-2-11b-instruct-v1:0";
    constexpr const char* LLAMA_3_2_3B = "meta.llama3-2-3b-instruct-v1:0";
    constexpr const char* LLAMA_3_2_1B = "meta.llama3-2-1b-instruct-v1:0";

    // Mistral models
    constexpr const char* MISTRAL_LARGE_2407 = "mistral.mistral-large-2407-v1:0";
    constexpr const char* MISTRAL_LARGE_2402 = "mistral.mistral-large-2402-v1:0";
    constexpr const char* MISTRAL_7B = "mistral.mistral-7b-instruct-v0:2";

    // Amazon Titan models
    constexpr const char* TITAN_TEXT_PREMIER = "amazon.titan-text-premier-v1:0";
    constexpr const char* TITAN_TEXT_EXPRESS = "amazon.titan-text-express-v1";
    constexpr const char* TITAN_TEXT_LITE = "amazon.titan-text-lite-v1";
}

} // namespace adapters
} // namespace agenkit

#endif // AGENKIT_ADAPTERS_BEDROCK_AGENT_HPP
