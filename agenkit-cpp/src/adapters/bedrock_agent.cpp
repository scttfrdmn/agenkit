/**
 * @file bedrock_agent.cpp
 * @brief Implementation of Amazon Bedrock API adapter
 *
 * NOTE: This implementation requires the AWS SDK for C++ to be installed.
 * Specifically, the bedrock-runtime component is required.
 *
 * To build with Bedrock support:
 *   cmake -DAGENKIT_BUILD_BEDROCK=ON ..
 *
 * Without AWS SDK installed, this will compile but throw runtime errors.
 */

#include "agenkit/adapters/bedrock_agent.hpp"
#include "agenkit/adapters/validation.hpp"
#include <iostream>
#include <stdexcept>
#include <sstream>

// AWS SDK includes - these are conditionally compiled
#ifdef AGENKIT_HAS_AWS_SDK
#include <aws/core/Aws.h>
#include <aws/core/auth/AWSCredentialsProvider.h>
#include <aws/bedrock-runtime/BedrockRuntimeClient.h>
#include <aws/bedrock-runtime/model/ConverseRequest.h>
#include <aws/bedrock-runtime/model/ConverseResult.h>
#include <aws/bedrock-runtime/model/ConverseStreamRequest.h>
#include <aws/bedrock-runtime/model/ConverseStreamHandler.h>
#include <aws/bedrock-runtime/model/Message.h>
#include <aws/bedrock-runtime/model/ContentBlock.h>
#include <aws/bedrock-runtime/model/InferenceConfiguration.h>
#include <aws/bedrock-runtime/model/SystemContentBlock.h>
#include <functional>
#include <condition_variable>
#include <mutex>
#endif

namespace agenkit {
namespace adapters {

#ifdef AGENKIT_HAS_AWS_SDK

// AWS SDK is available - full implementation

BedrockAgent::BedrockAgent(BedrockConfig config)
    : config_(std::move(config))
{
    // Validate LLM parameters (if provided)
    if (config_.temperature.has_value()) {
        LLMParameterValidator::validate_temperature(config_.temperature.value());
    }
    if (config_.max_tokens.has_value()) {
        LLMParameterValidator::validate_max_tokens(config_.max_tokens.value());
    }

    initialize_client();
}

BedrockAgent::~BedrockAgent() = default;

std::string BedrockAgent::name() const {
    return "bedrock-" + config_.model;
}

std::future<core::Result<core::Message, core::AgentError>>
BedrockAgent::process(core::Message message) {
    return process_with(std::move(message), core::CallOptions{});
}

std::future<core::Result<core::Message, core::AgentError>>
BedrockAgent::process_with(core::Message message, const core::CallOptions& options) {
    // seed has no Bedrock equivalent: the Converse API's InferenceConfiguration
    // has no sampling-seed parameter. Warn rather than silently drop it, so a
    // caller doesn't have to discover this empirically via non-reproducible
    // output.
    if (options.seed.has_value()) {
        std::cerr << "BedrockAgent: 'seed' is not supported by the Bedrock Converse API "
                  << "and was not sent to the provider." << std::endl;
    }

    auto result = call_converse_api(message, options);

    if (result.is_err()) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(result.unwrap_err())
        );
    }

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(result.unwrap())
    );
}

std::vector<std::string> BedrockAgent::capabilities() const {
    return {"llm", "completion", "chat"};
}

const BedrockConfig& BedrockAgent::config() const {
    return config_;
}

void BedrockAgent::set_config(const BedrockConfig& config) {
    config_ = config;
    initialize_client();
}

void BedrockAgent::initialize_client() {
    Aws::Client::ClientConfiguration client_config;
    client_config.region = config_.region;

    if (config_.access_key_id.has_value() && config_.secret_access_key.has_value()) {
        // Use explicit credentials
        auto credentials = Aws::Auth::AWSCredentials(
            config_.access_key_id.value(),
            config_.secret_access_key.value(),
            config_.session_token.value_or("")
        );
        client_ = std::make_unique<Aws::BedrockRuntime::BedrockRuntimeClient>(
            credentials,
            client_config
        );
    } else {
        // Use default credential chain
        client_ = std::make_unique<Aws::BedrockRuntime::BedrockRuntimeClient>(
            client_config
        );
    }
}

core::Result<core::Message, core::AgentError>
BedrockAgent::call_converse_api(const core::Message& message, const core::CallOptions& options) {
    try {
        // Create request
        Aws::BedrockRuntime::Model::ConverseRequest request;
        request.SetModelId(config_.model);

        // Convert message to Bedrock format
        Aws::BedrockRuntime::Model::Message bedrock_message;

        // Map role
        std::string role = message.role();
        if (role == "user") {
            bedrock_message.SetRole(Aws::BedrockRuntime::Model::ConversationRole::user);
        } else if (role == "assistant" || role == "agent") {
            bedrock_message.SetRole(Aws::BedrockRuntime::Model::ConversationRole::assistant);
        } else {
            // Default to user for system messages
            bedrock_message.SetRole(Aws::BedrockRuntime::Model::ConversationRole::user);
        }

        // Add content
        Aws::BedrockRuntime::Model::ContentBlock content_block;
        content_block.SetText(message.content_as_str());
        bedrock_message.AddContent(content_block);

        // Add message to request
        request.AddMessages(bedrock_message);

        // Set inference configuration. A per-call option overrides the config
        // default for that one call rather than merging with it.
        Aws::BedrockRuntime::Model::InferenceConfiguration inference_config;

        std::optional<double> temperature = options.temperature.has_value() ? options.temperature : config_.temperature;
        if (temperature.has_value()) {
            inference_config.SetTemperature(static_cast<float>(temperature.value()));
        }
        std::optional<int> max_tokens = options.max_tokens.has_value() ? options.max_tokens : config_.max_tokens;
        if (max_tokens.has_value()) {
            inference_config.SetMaxTokens(max_tokens.value());
        }
        std::optional<double> top_p = options.top_p.has_value() ? options.top_p : config_.top_p;
        if (top_p.has_value()) {
            inference_config.SetTopP(static_cast<float>(top_p.value()));
        }

        // stop -> stopSequences: the Converse API has no field named `stop`.
        // options.stop overrides config_.stop_sequences for this call when
        // set, rather than merging with it. seed is intentionally never set
        // here: the Converse API has no sampling-seed parameter at all, so
        // there is no wire name to translate it to. process_with() warns
        // about this; this method only builds the request that will
        // actually be sent.
        const std::vector<std::string>& stop_sequences =
            options.stop.has_value() ? options.stop.value() : config_.stop_sequences;
        for (const auto& seq : stop_sequences) {
            inference_config.AddStopSequences(seq);
        }

        request.SetInferenceConfig(inference_config);

        // Make API call
        auto outcome = client_->Converse(request);

        if (!outcome.IsSuccess()) {
            const auto& error = outcome.GetError();
            std::string error_msg = "Bedrock API error: " + error.GetMessage();
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    error_msg
                )
            );
        }

        // Extract response
        const auto& result = outcome.GetResult();
        std::string response_text;

        if (result.GetOutput().GetMessage().GetContent().size() > 0) {
            const auto& output_message = result.GetOutput().GetMessage();
            for (const auto& content_block : output_message.GetContent()) {
                response_text += content_block.GetText();
            }
        }

        // Create response message
        auto response_msg = core::Message::with_text("assistant", response_text);

        // Add metadata
        response_msg.with_metadata("model", config_.model);

        // Add usage metadata
        if (result.GetUsage().InputTokensHasBeenSet() ||
            result.GetUsage().OutputTokensHasBeenSet() ||
            result.GetUsage().TotalTokensHasBeenSet()) {
            nlohmann::json usage_metadata;
            usage_metadata["prompt_tokens"] = result.GetUsage().GetInputTokens();
            usage_metadata["completion_tokens"] = result.GetUsage().GetOutputTokens();
            usage_metadata["total_tokens"] = result.GetUsage().GetTotalTokens();
            // Prompt-cache token counts (Anthropic-on-Bedrock), billed at a
            // reduced rate. Only present when prompt caching is active.
            if (result.GetUsage().CacheReadInputTokensHasBeenSet()) {
                usage_metadata["cache_read_tokens"] = result.GetUsage().GetCacheReadInputTokens();
            }
            if (result.GetUsage().CacheWriteInputTokensHasBeenSet()) {
                usage_metadata["cache_creation_tokens"] =
                    result.GetUsage().GetCacheWriteInputTokens();
            }
            response_msg.with_metadata("usage", usage_metadata);
        }

        // Add stop reason
        if (result.GetStopReason() != Aws::BedrockRuntime::Model::StopReason::NOT_SET) {
            std::string stop_reason;
            switch (result.GetStopReason()) {
                case Aws::BedrockRuntime::Model::StopReason::end_turn:
                    stop_reason = "end_turn";
                    break;
                case Aws::BedrockRuntime::Model::StopReason::stop_sequence:
                    stop_reason = "stop_sequence";
                    break;
                case Aws::BedrockRuntime::Model::StopReason::max_tokens:
                    stop_reason = "max_tokens";
                    break;
                case Aws::BedrockRuntime::Model::StopReason::content_filtered:
                    stop_reason = "content_filtered";
                    break;
                default:
                    stop_reason = "unknown";
                    break;
            }
            response_msg.with_metadata("finish_reason", stop_reason);
        }

        return core::Result<core::Message, core::AgentError>::ok(response_msg);

    } catch (const std::exception& e) {
        return core::Result<core::Message, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Internal,
                std::string("unexpected error: ") + e.what()
            )
        );
    }
}

// Note (#818): stream() intentionally does not take a CallOptions, same
// rationale as OpenAIAgent::stream — #818 scopes per-call options to
// process()/process_with().
core::Result<void, core::AgentError>
BedrockAgent::stream(core::Message message, std::function<bool(const std::string&)> callback) {
    try {
        // Create streaming request
        Aws::BedrockRuntime::Model::ConverseStreamRequest request;
        request.SetModelId(config_.model);

        // Convert message to Bedrock format
        Aws::BedrockRuntime::Model::Message bedrock_message;

        // Map role
        std::string role = message.role();
        if (role == "user") {
            bedrock_message.SetRole(Aws::BedrockRuntime::Model::ConversationRole::user);
        } else if (role == "assistant" || role == "agent") {
            bedrock_message.SetRole(Aws::BedrockRuntime::Model::ConversationRole::assistant);
        } else {
            // Default to user for system messages
            bedrock_message.SetRole(Aws::BedrockRuntime::Model::ConversationRole::user);
        }

        // Add content
        Aws::BedrockRuntime::Model::ContentBlock content_block;
        content_block.SetText(message.content_as_str());
        bedrock_message.AddContent(content_block);

        // Add message to request
        request.AddMessages(bedrock_message);

        // Set inference configuration
        Aws::BedrockRuntime::Model::InferenceConfiguration inference_config;

        if (config_.temperature.has_value()) {
            inference_config.SetTemperature(static_cast<float>(config_.temperature.value()));
        }
        if (config_.max_tokens.has_value()) {
            inference_config.SetMaxTokens(config_.max_tokens.value());
        }
        if (config_.top_p.has_value()) {
            inference_config.SetTopP(static_cast<float>(config_.top_p.value()));
        }
        if (!config_.stop_sequences.empty()) {
            for (const auto& seq : config_.stop_sequences) {
                inference_config.AddStopSequences(seq);
            }
        }

        request.SetInferenceConfig(inference_config);

        // Set up stream handler
        bool should_stop = false;
        bool has_error = false;
        std::string error_message;
        std::mutex mtx;
        std::condition_variable cv;
        bool stream_complete = false;

        Aws::BedrockRuntime::Model::ConverseStreamHandler handler;

        // Handle content block delta events
        handler.SetContentBlockDeltaEventCallback(
            [&](const Aws::BedrockRuntime::Model::ContentBlockDeltaEvent& event) {
                if (should_stop) return;

                if (event.GetDelta().GetText().size() > 0) {
                    std::string text = event.GetDelta().GetText();

                    // Invoke callback with text chunk
                    if (!callback(text)) {
                        std::lock_guard<std::mutex> lock(mtx);
                        should_stop = true;
                    }
                }
            }
        );

        // Handle errors
        handler.SetOnErrorCallback(
            [&](const Aws::Client::AWSError<Aws::BedrockRuntime::BedrockRuntimeErrors>& error) {
                std::lock_guard<std::mutex> lock(mtx);
                has_error = true;
                error_message = error.GetMessage();
                stream_complete = true;
                cv.notify_one();
            }
        );

        // Handle completion
        handler.SetMessageStopEventCallback(
            [&](const Aws::BedrockRuntime::Model::MessageStopEvent&) {
                std::lock_guard<std::mutex> lock(mtx);
                stream_complete = true;
                cv.notify_one();
            }
        );

        // Make streaming API call
        request.SetEventStreamHandler(handler);
        auto outcome = client_->ConverseStream(request);

        if (!outcome.IsSuccess()) {
            const auto& error = outcome.GetError();
            std::string error_msg = "Bedrock streaming error: " + error.GetMessage();
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    error_msg
                )
            );
        }

        // Wait for stream to complete
        std::unique_lock<std::mutex> lock(mtx);
        cv.wait(lock, [&] { return stream_complete; });

        if (has_error) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    "Bedrock streaming error: " + error_message
                )
            );
        }

        return core::Result<void, core::AgentError>::ok();

    } catch (const std::exception& e) {
        return core::Result<void, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Internal,
                std::string("streaming error: ") + e.what()
            )
        );
    }
}

#else

// AWS SDK is NOT available - stub implementation that throws errors

BedrockAgent::BedrockAgent(BedrockConfig config)
    : config_(std::move(config))
    , client_(nullptr)
{
    // Validate LLM parameters even in stub (fail fast)
    if (config_.temperature.has_value()) {
        LLMParameterValidator::validate_temperature(config_.temperature.value());
    }
    if (config_.max_tokens.has_value()) {
        LLMParameterValidator::validate_max_tokens(config_.max_tokens.value());
    }

    throw std::runtime_error(
        "Bedrock adapter requires AWS SDK for C++ to be installed. "
        "Please install aws-sdk-cpp with bedrock-runtime component and rebuild with -DAGENKIT_HAS_AWS_SDK=ON"
    );
}

BedrockAgent::~BedrockAgent() = default;

std::string BedrockAgent::name() const {
    return "bedrock-" + config_.model;
}

std::future<core::Result<core::Message, core::AgentError>>
BedrockAgent::process(core::Message /* message */) {
    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Internal,
                "Bedrock adapter not available - AWS SDK not compiled in"
            )
        )
    );
}

std::future<core::Result<core::Message, core::AgentError>>
BedrockAgent::process_with(core::Message /* message */, const core::CallOptions& /* options */) {
    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Internal,
                "Bedrock adapter not available - AWS SDK not compiled in"
            )
        )
    );
}

std::vector<std::string> BedrockAgent::capabilities() const {
    return {"llm", "completion", "chat"};
}

const BedrockConfig& BedrockAgent::config() const {
    return config_;
}

void BedrockAgent::set_config(const BedrockConfig& config) {
    config_ = config;
}

#endif // AGENKIT_HAS_AWS_SDK

} // namespace adapters
} // namespace agenkit
