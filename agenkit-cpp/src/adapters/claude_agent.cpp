/**
 * @file claude_agent.cpp
 * @brief Implementation of Anthropic Claude API adapter
 */

#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/adapters/validation.hpp"
#include "agenkit/core/sse_parser.hpp"
#include <httplib.h>
#include <iostream>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <sstream>

namespace agenkit {
namespace adapters {

using json = nlohmann::json;

ClaudeAgent::ClaudeAgent(ClaudeConfig config)
    : config_(std::move(config))
{
    if (config_.api_key.empty()) {
        throw std::invalid_argument("Claude API key cannot be empty");
    }

    // Validate LLM parameters. temperature is deliberately not validated:
    // it is deprecated and never sent (#1071), so its value cannot fail.
    LLMParameterValidator::validate_max_tokens(config_.max_tokens);

    if (config_.temperature != 1.0) {
        warn_sampling_param_ignored("temperature");
    }
}

std::string ClaudeAgent::name() const {
    return "claude";
}

std::future<core::Result<core::Message, core::AgentError>>
ClaudeAgent::process(core::Message message) {
    return process_with(std::move(message), core::CallOptions{});
}

std::future<core::Result<core::Message, core::AgentError>>
ClaudeAgent::process_with(core::Message message, const core::CallOptions& options) {
    // seed has no Anthropic equivalent: the Messages API exposes no
    // sampling-seed parameter. Warn rather than silently drop it, so a caller
    // doesn't have to discover this empirically via non-reproducible output.
    if (options.seed.has_value()) {
        std::cerr << "ClaudeAgent: 'seed' is not supported by the Anthropic Messages API "
                  << "and was not sent to the provider." << std::endl;
    }

    // Sampling parameters are rejected by Anthropic API version 2026-10-21
    // (HTTP 400, even at their default values), so build_request_body()
    // never sends them (#1071). Warn once per instance instead of per call.
    if (options.temperature.has_value()) {
        warn_sampling_param_ignored("temperature");
    }
    if (options.top_p.has_value()) {
        warn_sampling_param_ignored("top_p");
    }

    // Convert message to Claude API format
    json messages = json::array();
    messages.push_back(message_to_json(message));

    // Make API call
    auto result = call_api(messages, options);

    if (result.is_err()) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(result.unwrap_err())
        );
    }

    // Convert response to message
    auto response_json = result.unwrap();
    auto response_msg = json_to_message(response_json);

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(std::move(response_msg))
    );
}

std::vector<std::string> ClaudeAgent::capabilities() const {
    return {"llm", "text-generation", "claude"};
}

const ClaudeConfig& ClaudeAgent::config() const {
    return config_;
}

void ClaudeAgent::set_config(const ClaudeConfig& config) {
    if (config.api_key.empty()) {
        throw std::invalid_argument("Claude API key cannot be empty");
    }

    // Validate LLM parameters (temperature is deprecated and not validated, #1071)
    LLMParameterValidator::validate_max_tokens(config.max_tokens);

    config_ = config;

    if (config_.temperature != 1.0) {
        warn_sampling_param_ignored("temperature");
    }
}

void ClaudeAgent::warn_sampling_param_ignored(const char* param) {
    if (!sampling_warning_.first()) {
        return;
    }
    std::cerr << "ClaudeAgent: '" << param << "' is deprecated and was not sent to the "
              << "Anthropic Messages API (API version 2026-10-21 rejects temperature, "
              << "top_p and top_k); the provider default applies. This warning is shown "
              << "once per ClaudeAgent instance. See #1071." << std::endl;
}

json ClaudeAgent::build_request_body(const json& messages, const core::CallOptions& options) const {
    // Build request body
    json request_body = {
        {"model", config_.model},
        {"max_tokens", options.max_tokens.value_or(config_.max_tokens)},
        {"messages", messages}
    };

    // temperature/top_p (config or per-call) are intentionally never added:
    // Anthropic API version 2026-10-21 rejects them with HTTP 400 even at
    // their defaults, and omitting them yields the same defaults under
    // 2023-06-01 (#1071). process_with() and the constructor warn instead.

    // stop -> stop_sequences: the Messages API has no field named `stop`.
    // seed is intentionally never added here: the Messages API has no
    // sampling-seed parameter at all, so there is no wire name to translate
    // it to. process_with() warns about this; this method only builds the
    // request that will actually be sent.
    if (options.stop.has_value()) {
        request_body["stop_sequences"] = options.stop.value();
    }

    return request_body;
}

core::Result<nlohmann::json, core::AgentError>
ClaudeAgent::call_api(const json& messages, const core::CallOptions& options) {
    try {
        // Parse API base URL
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        json request_body = build_request_body(messages, options);

        // Set headers
        httplib::Headers headers = {
            {"x-api-key", config_.api_key},
            {"anthropic-version", config_.api_version},
            {"content-type", "application/json"}
        };

        // Make request
        auto response = client.Post("/v1/messages", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to Claude API"
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "Claude API error (" +
                                   std::to_string(response->status) + "): " +
                                   response->body;
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    error_msg
                )
            );
        }

        // Parse response
        json response_json = json::parse(response->body);
        return core::Result<json, core::AgentError>::ok(response_json);

    } catch (const json::exception& e) {
        return core::Result<json, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Serialization,
                std::string("JSON error: ") + e.what()
            )
        );
    } catch (const std::exception& e) {
        return core::Result<json, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Internal,
                std::string("Unexpected error: ") + e.what()
            )
        );
    }
}

json ClaudeAgent::message_to_json(const core::Message& message) {
    return {
        {"role", message.role()},
        {"content", message.content_as_str()}
    };
}

core::Message ClaudeAgent::json_to_message(const json& response) {
    // Extract text from Claude response
    // Response format: { "content": [{"type": "text", "text": "..."}], ... }
    std::string text;

    if (response.contains("content") && response["content"].is_array()) {
        for (const auto& content_block : response["content"]) {
            if (content_block.contains("type") &&
                content_block["type"] == "text" &&
                content_block.contains("text")) {
                text = content_block["text"].get<std::string>();
                break;
            }
        }
    }

    auto msg = core::Message::with_text("assistant", text);

    // Add metadata from response
    if (response.contains("id")) {
        msg.with_metadata("claude_message_id", response["id"]);
    }
    if (response.contains("model")) {
        msg.with_metadata("model", response["model"]);
    }
    if (response.contains("usage")) {
        msg.with_metadata("usage", response["usage"]);
    }

    return msg;
}

// Note (#818): stream() intentionally does not take a CallOptions, same
// rationale as OpenAIAgent::stream — #818 scopes per-call options to
// process()/process_with().
core::Result<void, core::AgentError>
ClaudeAgent::stream(core::Message message, std::function<bool(const std::string&)> callback) {
    try {
        // Convert message to Claude API format
        json messages = json::array();
        messages.push_back(message_to_json(message));

        // Parse API base URL
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        // Build request body with stream=true
        json request_body = {
            {"model", config_.model},
            {"max_tokens", config_.max_tokens},
            {"messages", messages},
            {"stream", true}
        };
        // temperature is never sent (#1071); see build_request_body().

        // Set headers
        httplib::Headers headers = {
            {"x-api-key", config_.api_key},
            {"anthropic-version", config_.api_version},
            {"content-type", "application/json"}
        };

        // Use httplib Request with content_receiver for true SSE streaming
        httplib::Request req;
        req.method = "POST";
        req.path = "/v1/messages";
        req.headers = headers;
        req.body = request_body.dump();
        req.set_header("Content-Type", "application/json");

        std::string stream_error;
        core::SseParser parser;

        req.content_receiver = [&](const char* data, size_t data_length,
                                   uint64_t /*offset*/, uint64_t /*total*/) -> bool {
            return parser.feed(data, data_length, core::SseParser::Mode::SSE,
                [&](const std::string& json_str) -> bool {
                    try {
                        auto chunk = json::parse(json_str);
                        // content_block_delta events carry the streamed text
                        if (chunk.contains("type") &&
                            chunk["type"] == "content_block_delta" &&
                            chunk.contains("delta") &&
                            chunk["delta"].contains("text")) {
                            callback(chunk["delta"]["text"].get<std::string>());
                        }
                    } catch (const json::exception&) {
                        // skip malformed chunks
                    }
                    return true;
                });
        };

        httplib::Response res;
        httplib::Error err = httplib::Error::Success;
        if (!client.send(req, res, err)) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "failed to connect to Claude API for streaming: " +
                    httplib::to_string(err)
                )
            );
        }

        if (res.status != 200) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    "Claude streaming error (" + std::to_string(res.status) + "): " + res.body
                )
            );
        }

        return core::Result<void, core::AgentError>::ok();

    } catch (const std::exception& e) {
        return core::Result<void, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::Internal,
                std::string("Streaming error: ") + e.what()
            )
        );
    }
}

} // namespace adapters
} // namespace agenkit
