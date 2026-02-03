/**
 * @file claude_agent.cpp
 * @brief Implementation of Anthropic Claude API adapter
 */

#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/adapters/validation.hpp"
#include <httplib.h>
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

    // Validate LLM parameters
    LLMParameterValidator::validate_temperature(config_.temperature);
    LLMParameterValidator::validate_max_tokens(config_.max_tokens);
    // Note: Claude uses temperature 0-1, but we validate 0-2 for consistency with other adapters
}

std::string ClaudeAgent::name() const {
    return "claude";
}

std::future<core::Result<core::Message, core::AgentError>>
ClaudeAgent::process(core::Message message) {
    // Convert message to Claude API format
    json messages = json::array();
    messages.push_back(message_to_json(message));

    // Make API call
    auto result = call_api(messages);

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

    // Validate LLM parameters
    LLMParameterValidator::validate_temperature(config.temperature);
    LLMParameterValidator::validate_max_tokens(config.max_tokens);

    config_ = config;
}

core::Result<nlohmann::json, core::AgentError>
ClaudeAgent::call_api(const json& messages) {
    try {
        // Parse API base URL
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        // Build request body
        json request_body = {
            {"model", config_.model},
            {"max_tokens", config_.max_tokens},
            {"messages", messages}
        };

        if (config_.temperature != 1.0) {
            request_body["temperature"] = config_.temperature;
        }

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

        if (config_.temperature != 1.0) {
            request_body["temperature"] = config_.temperature;
        }

        // Set headers
        httplib::Headers headers = {
            {"x-api-key", config_.api_key},
            {"anthropic-version", config_.api_version},
            {"content-type", "application/json"}
        };

        // TODO(Issue #XXX): Fix httplib streaming API - currently using fallback
        // The httplib Post() API changed and streaming callbacks need to be updated
        // For now, make a non-streaming request
        request_body["stream"] = false;  // Disable streaming
        auto response = client.Post("/v1/messages", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to Claude API for streaming"
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "Claude streaming error (" +
                                   std::to_string(response->status) + "): " +
                                   response->body;
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    error_msg
                )
            );
        }

        // TODO(Issue #XXX): Implement proper streaming
        // For now, return the full response body through the callback
        try {
            json response_json = json::parse(response->body);
            if (response_json.contains("content") && response_json["content"].is_array()) {
                for (const auto& content_block : response_json["content"]) {
                    if (content_block.contains("type") &&
                        content_block["type"] == "text" &&
                        content_block.contains("text")) {
                        callback(content_block["text"].get<std::string>());
                    }
                }
            }
        } catch (const json::exception&) {
            // Ignore parse errors
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
