/**
 * @file openai_compatible_agent.cpp
 * @brief Implementation of OpenAI-Compatible API adapter
 */

#include "agenkit/adapters/openai_compatible_agent.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <stdexcept>

namespace agenkit {
namespace adapters {

using json = nlohmann::json;

OpenAICompatibleAgent::OpenAICompatibleAgent(OpenAICompatibleConfig config)
    : config_(std::move(config))
{
    // No validation needed - local services may not have auth
}

std::string OpenAICompatibleAgent::name() const {
    if (config_.provider.has_value()) {
        return config_.provider.value();
    }
    return "openai_compatible";
}

std::future<core::Result<core::Message, core::AgentError>>
OpenAICompatibleAgent::process(core::Message message) {
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

std::vector<std::string> OpenAICompatibleAgent::capabilities() const {
    std::vector<std::string> caps = {
        "llm",
        "text-generation",
        "openai-compatible"
    };

    if (config_.provider.has_value()) {
        caps.push_back(config_.provider.value());
    }

    return caps;
}

const OpenAICompatibleConfig& OpenAICompatibleAgent::config() const {
    return config_;
}

void OpenAICompatibleAgent::set_config(const OpenAICompatibleConfig& config) {
    config_ = config;
}

core::Result<nlohmann::json, core::AgentError>
OpenAICompatibleAgent::call_api(const json& messages) {
    try {
        // Parse base URL
        httplib::Client client(config_.base_url);
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

        // Set headers
        std::string api_key = config_.api_key.value_or("not-needed");
        httplib::Headers headers = {
            {"Authorization", "Bearer " + api_key},
            {"Content-Type", "application/json"}
        };

        // Make request to /chat/completions endpoint
        auto response = client.Post("/chat/completions", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to OpenAI-compatible service at " + config_.base_url
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "OpenAI-compatible API error (" +
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

json OpenAICompatibleAgent::message_to_json(const core::Message& message) {
    // Map agent role to assistant for OpenAI compatibility
    std::string role = message.role();
    if (role == "agent") {
        role = "assistant";
    } else if (role != "system" && role != "user" && role != "tool") {
        role = "assistant";
    }

    return {
        {"role", role},
        {"content", message.content_as_str()}
    };
}

core::Message OpenAICompatibleAgent::json_to_message(const json& response) {
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

    // Add metadata with provider information
    if (response.contains("id")) {
        msg.with_metadata("id", response["id"]);
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

    // Add provider metadata for debugging
    std::string provider = config_.provider.value_or("openai_compatible");
    msg.with_metadata("provider", provider);
    msg.with_metadata("base_url", config_.base_url);

    return msg;
}

} // namespace adapters
} // namespace agenkit
