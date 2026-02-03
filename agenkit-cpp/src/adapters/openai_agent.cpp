/**
 * @file openai_agent.cpp
 * @brief Implementation of OpenAI API adapter
 */

#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/adapters/validation.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <sstream>

namespace agenkit {
namespace adapters {

using json = nlohmann::json;

OpenAIAgent::OpenAIAgent(OpenAIConfig config)
    : config_(std::move(config))
{
    if (config_.api_key.empty()) {
        throw std::invalid_argument("OpenAI API key cannot be empty");
    }

    // Validate LLM parameters using shared utility
    LLMParameterValidator::validate_all(
        config_.temperature,
        config_.max_tokens,
        config_.top_p,
        config_.frequency_penalty,
        config_.presence_penalty
    );
}

std::string OpenAIAgent::name() const {
    return "openai";
}

std::future<core::Result<core::Message, core::AgentError>>
OpenAIAgent::process(core::Message message) {
    // Convert message to OpenAI API format
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

std::vector<std::string> OpenAIAgent::capabilities() const {
    return {"llm", "text-generation", "openai"};
}

const OpenAIConfig& OpenAIAgent::config() const {
    return config_;
}

void OpenAIAgent::set_config(const OpenAIConfig& config) {
    if (config.api_key.empty()) {
        throw std::invalid_argument("OpenAI API key cannot be empty");
    }

    // Validate temperature (0-2)
    if (config.temperature < 0.0 || config.temperature > 2.0) {
        throw std::invalid_argument(
            "temperature must be between 0 and 2, got " +
            std::to_string(config.temperature)
        );
    }

    // Validate max_tokens (must be positive)
    if (config.max_tokens <= 0) {
        throw std::invalid_argument(
            "max_tokens must be positive, got " +
            std::to_string(config.max_tokens)
        );
    }

    // Validate top_p (0-1)
    if (config.top_p < 0.0 || config.top_p > 1.0) {
        throw std::invalid_argument(
            "top_p must be between 0 and 1, got " +
            std::to_string(config.top_p)
        );
    }

    // Validate frequency_penalty (-2 to 2)
    if (config.frequency_penalty < -2.0 || config.frequency_penalty > 2.0) {
        throw std::invalid_argument(
            "frequency_penalty must be between -2 and 2, got " +
            std::to_string(config.frequency_penalty)
        );
    }

    // Validate presence_penalty (-2 to 2)
    if (config.presence_penalty < -2.0 || config.presence_penalty > 2.0) {
        throw std::invalid_argument(
            "presence_penalty must be between -2 and 2, got " +
            std::to_string(config.presence_penalty)
        );
    }

    config_ = config;
}

core::Result<nlohmann::json, core::AgentError>
OpenAIAgent::call_api(const json& messages) {
    try {
        // Parse API base URL
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        // Build request body
        json request_body = {
            {"model", config_.model},
            {"messages", messages},
            {"max_tokens", config_.max_tokens}
        };

        // Add optional parameters if not default
        if (config_.temperature != 0.7) {
            request_body["temperature"] = config_.temperature;
        }
        if (config_.top_p != 1.0) {
            request_body["top_p"] = config_.top_p;
        }
        if (config_.frequency_penalty != 0.0) {
            request_body["frequency_penalty"] = config_.frequency_penalty;
        }
        if (config_.presence_penalty != 0.0) {
            request_body["presence_penalty"] = config_.presence_penalty;
        }

        // Set headers
        httplib::Headers headers = {
            {"Authorization", "Bearer " + config_.api_key},
            {"Content-Type", "application/json"}
        };

        // Make request
        auto response = client.Post("/v1/chat/completions", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to OpenAI API"
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "OpenAI API error (" +
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

json OpenAIAgent::message_to_json(const core::Message& message) {
    return {
        {"role", message.role()},
        {"content", message.content_as_str()}
    };
}

core::Message OpenAIAgent::json_to_message(const json& response) {
    // Extract text from OpenAI response
    // Response format: { "choices": [{"message": {"role": "assistant", "content": "..."}}], ... }
    std::string text;
    std::string role = "assistant";

    if (response.contains("choices") && response["choices"].is_array() &&
        !response["choices"].empty()) {
        const auto& choice = response["choices"][0];
        if (choice.contains("message")) {
            const auto& message = choice["message"];
            if (message.contains("content")) {
                text = message["content"].get<std::string>();
            }
            if (message.contains("role")) {
                role = message["role"].get<std::string>();
            }
        }
    }

    auto msg = core::Message::with_text(role, text);

    // Add metadata from response
    if (response.contains("id")) {
        msg.with_metadata("openai_message_id", response["id"]);
    }
    if (response.contains("model")) {
        msg.with_metadata("model", response["model"]);
    }
    if (response.contains("usage")) {
        msg.with_metadata("usage", response["usage"]);
    }
    if (response.contains("choices") && response["choices"].is_array() &&
        !response["choices"].empty()) {
        const auto& choice = response["choices"][0];
        if (choice.contains("finish_reason")) {
            msg.with_metadata("finish_reason", choice["finish_reason"]);
        }
    }

    return msg;
}

core::Result<void, core::AgentError>
OpenAIAgent::stream(core::Message message, std::function<bool(const std::string&)> callback) {
    try {
        // Convert message to OpenAI API format
        json messages = json::array();
        messages.push_back(message_to_json(message));

        // Parse API base URL
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        // Build request body with stream=true
        json request_body = {
            {"model", config_.model},
            {"messages", messages},
            {"max_tokens", config_.max_tokens},
            {"stream", true}
        };

        // Add optional parameters if not default
        if (config_.temperature != 0.7) {
            request_body["temperature"] = config_.temperature;
        }
        if (config_.top_p != 1.0) {
            request_body["top_p"] = config_.top_p;
        }
        if (config_.frequency_penalty != 0.0) {
            request_body["frequency_penalty"] = config_.frequency_penalty;
        }
        if (config_.presence_penalty != 0.0) {
            request_body["presence_penalty"] = config_.presence_penalty;
        }

        // Set headers
        httplib::Headers headers = {
            {"Authorization", "Bearer " + config_.api_key},
            {"Content-Type", "application/json"}
        };

        // TODO(Issue #XXX): Fix httplib streaming API - currently using fallback
        // The httplib Post() API changed and streaming callbacks need to be updated
        // For now, make a non-streaming request and simulate streaming by chunking
        auto response = client.Post("/v1/chat/completions", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to OpenAI API for streaming"
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "OpenAI streaming error (" +
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
            if (response_json.contains("choices") && !response_json["choices"].empty()) {
                const auto& choice = response_json["choices"][0];
                if (choice.contains("message") && choice["message"].contains("content")) {
                    std::string content = choice["message"]["content"].get<std::string>();
                    callback(content);
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
