/**
 * @file litellm_agent.cpp
 * @brief Implementation of LiteLLM proxy adapter
 */

#include "agenkit/adapters/litellm_agent.hpp"
#include "agenkit/adapters/validation.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <stdexcept>

namespace agenkit {
namespace adapters {

using json = nlohmann::json;

LiteLLMAgent::LiteLLMAgent(LiteLLMConfig config)
    : config_(std::move(config))
{
    // No API key validation - LiteLLM proxy may not require auth
    // Model is required for routing
    if (config_.model.empty()) {
        throw std::invalid_argument("LiteLLM model cannot be empty");
    }

    // Validate LLM parameters (if provided)
    if (config_.temperature.has_value()) {
        LLMParameterValidator::validate_temperature(config_.temperature.value());
    }
    if (config_.max_tokens.has_value()) {
        LLMParameterValidator::validate_max_tokens(config_.max_tokens.value());
    }
}

std::string LiteLLMAgent::name() const {
    return "litellm-" + config_.model;
}

std::future<core::Result<core::Message, core::AgentError>>
LiteLLMAgent::process(core::Message message) {
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

std::vector<std::string> LiteLLMAgent::capabilities() const {
    return {"llm", "completion", "streaming", "universal-gateway"};
}

const LiteLLMConfig& LiteLLMAgent::config() const {
    return config_;
}

void LiteLLMAgent::set_config(const LiteLLMConfig& config) {
    if (config.model.empty()) {
        throw std::invalid_argument("LiteLLM model cannot be empty");
    }

    // Validate LLM parameters (if provided)
    if (config.temperature.has_value()) {
        LLMParameterValidator::validate_temperature(config.temperature.value());
    }
    if (config.max_tokens.has_value()) {
        LLMParameterValidator::validate_max_tokens(config.max_tokens.value());
    }

    config_ = config;
}

core::Result<nlohmann::json, core::AgentError>
LiteLLMAgent::call_api(const json& messages) {
    try {
        // Parse base URL for http client
        httplib::Client client(config_.base_url);
        client.set_read_timeout(config_.timeout_seconds, 0);

        // Build request body
        json request_body = {
            {"model", config_.model},
            {"messages", messages}
        };

        // Add optional parameters if set
        if (config_.temperature.has_value()) {
            request_body["temperature"] = config_.temperature.value();
        }
        if (config_.max_tokens.has_value()) {
            request_body["max_tokens"] = config_.max_tokens.value();
        }
        if (config_.top_p.has_value()) {
            request_body["top_p"] = config_.top_p.value();
        }

        // Set headers
        httplib::Headers headers = {
            {"Content-Type", "application/json"}
        };

        // Add API key if provided
        if (config_.api_key.has_value()) {
            headers.insert({"Authorization", "Bearer " + config_.api_key.value()});
        }

        // Make request to /chat/completions endpoint (OpenAI-compatible)
        auto response = client.Post("/chat/completions", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "failed to connect to LiteLLM proxy"
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "LiteLLM API error (" +
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
                std::string("unexpected error: ") + e.what()
            )
        );
    }
}

json LiteLLMAgent::message_to_json(const core::Message& message) {
    // Convert role - map 'agent' to 'assistant'
    std::string role = message.role();
    if (role == "agent") {
        role = "assistant";
    }

    return {
        {"role", role},
        {"content", message.content_as_str()}
    };
}

core::Message LiteLLMAgent::json_to_message(const json& response) {
    // Extract text from OpenAI-compatible response
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
        msg.with_metadata("litellm_message_id", response["id"]);
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

} // namespace adapters
} // namespace agenkit
