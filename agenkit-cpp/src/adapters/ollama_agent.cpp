/**
 * @file ollama_agent.cpp
 * @brief Implementation of Ollama local LLM adapter
 */

#include "agenkit/adapters/ollama_agent.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <sstream>

namespace agenkit {
namespace adapters {

using json = nlohmann::json;

OllamaAgent::OllamaAgent(OllamaConfig config)
    : config_(std::move(config))
{
    if (config_.model.empty()) {
        throw std::invalid_argument("Ollama model cannot be empty");
    }
}

std::string OllamaAgent::name() const {
    return "ollama";
}

std::future<core::Result<core::Message, core::AgentError>>
OllamaAgent::process(core::Message message) {
    // Convert message to Ollama API format
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

std::vector<std::string> OllamaAgent::capabilities() const {
    return {"llm", "text-generation", "ollama", "local"};
}

const OllamaConfig& OllamaAgent::config() const {
    return config_;
}

void OllamaAgent::set_config(const OllamaConfig& config) {
    if (config.model.empty()) {
        throw std::invalid_argument("Ollama model cannot be empty");
    }
    config_ = config;
}

bool OllamaAgent::is_available() const {
    try {
        httplib::Client client(config_.host);
        client.set_read_timeout(5, 0);  // 5 second timeout

        auto response = client.Get("/api/tags");
        return response && response->status == 200;
    } catch (...) {
        return false;
    }
}

std::vector<std::string> OllamaAgent::list_models() const {
    std::vector<std::string> models;

    try {
        httplib::Client client(config_.host);
        client.set_read_timeout(5, 0);

        auto response = client.Get("/api/tags");
        if (!response || response->status != 200) {
            return models;
        }

        auto json_response = json::parse(response->body);
        if (json_response.contains("models") && json_response["models"].is_array()) {
            for (const auto& model : json_response["models"]) {
                if (model.contains("name")) {
                    models.push_back(model["name"].get<std::string>());
                }
            }
        }
    } catch (...) {
        // Return empty vector on any error
    }

    return models;
}

core::Result<nlohmann::json, core::AgentError>
OllamaAgent::call_api(const json& messages) {
    try {
        // Parse host URL
        httplib::Client client(config_.host);
        client.set_read_timeout(config_.timeout_seconds, 0);

        // Build request body
        json request_body = {
            {"model", config_.model},
            {"messages", messages},
            {"stream", config_.stream}
        };

        // Add optional parameters
        if (config_.temperature >= 0.0) {
            request_body["options"] = {
                {"temperature", config_.temperature}
            };
        }

        if (!config_.system.empty()) {
            request_body["system"] = config_.system;
        }

        // Set headers
        httplib::Headers headers = {
            {"Content-Type", "application/json"}
        };

        // Make request to /api/chat endpoint
        auto response = client.Post("/api/chat", headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to Ollama at " + config_.host
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "Ollama API error (" +
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

json OllamaAgent::message_to_json(const core::Message& message) {
    return {
        {"role", message.role()},
        {"content", message.content_as_str()}
    };
}

core::Message OllamaAgent::json_to_message(const json& response) {
    // Extract text from Ollama response
    // Response format: { "message": {"role": "assistant", "content": "..."}, ... }
    std::string text;

    if (response.contains("message") && response["message"].is_object()) {
        const auto& message = response["message"];
        if (message.contains("content")) {
            text = message["content"].get<std::string>();
        }
    }

    auto msg = core::Message::with_text("assistant", text);

    // Add metadata from response
    if (response.contains("model")) {
        msg.with_metadata("model", response["model"]);
    }
    if (response.contains("created_at")) {
        msg.with_metadata("created_at", response["created_at"]);
    }
    if (response.contains("done") && response["done"].is_boolean()) {
        msg.with_metadata("done", response["done"]);
    }

    // Add timing and token info if available
    if (response.contains("total_duration")) {
        msg.with_metadata("total_duration_ns", response["total_duration"]);
    }
    if (response.contains("prompt_eval_count")) {
        msg.with_metadata("prompt_tokens", response["prompt_eval_count"]);
    }
    if (response.contains("eval_count")) {
        msg.with_metadata("completion_tokens", response["eval_count"]);
    }

    return msg;
}

core::Result<void, core::AgentError>
OllamaAgent::stream(core::Message message, std::function<bool(const std::string&)> callback) {
    try {
        // Convert message to Ollama API format
        json messages = json::array();
        messages.push_back(message_to_json(message));

        // Parse host URL
        httplib::Client client(config_.host);
        client.set_read_timeout(config_.timeout_seconds, 0);

        // Build request body with stream=true
        json request_body = {
            {"model", config_.model},
            {"messages", messages},
            {"stream", true}
        };

        // Add optional parameters
        if (config_.temperature >= 0.0) {
            request_body["options"] = {
                {"temperature", config_.temperature}
            };
        }

        if (!config_.system.empty()) {
            request_body["system"] = config_.system;
        }

        // Set headers
        httplib::Headers headers = {
            {"Content-Type", "application/json"}
        };

        // Make streaming request
        std::string buffer;
        auto response = client.Post(
            "/api/chat",
            headers,
            request_body.dump(),
            "application/json",
            [&](const char* data, size_t data_length) {
                // Append to buffer
                buffer.append(data, data_length);

                // Process complete lines (Ollama uses newline-delimited JSON)
                size_t pos;
                while ((pos = buffer.find('\n')) != std::string::npos) {
                    std::string line = buffer.substr(0, pos);
                    buffer = buffer.substr(pos + 1);

                    // Skip empty lines
                    if (line.empty()) {
                        continue;
                    }

                    try {
                        json chunk_json = json::parse(line);

                        // Check if done
                        if (chunk_json.contains("done") &&
                            chunk_json["done"].is_boolean() &&
                            chunk_json["done"].get<bool>()) {
                            // Final chunk, no more content
                            continue;
                        }

                        // Extract text from message.content
                        if (chunk_json.contains("message") &&
                            chunk_json["message"].is_object()) {
                            const auto& msg = chunk_json["message"];
                            if (msg.contains("content") && msg["content"].is_string()) {
                                std::string text = msg["content"].get<std::string>();

                                // Invoke callback with text chunk
                                if (!text.empty() && !callback(text)) {
                                    return false;  // Stop streaming
                                }
                            }
                        }
                    } catch (const json::exception&) {
                        // Skip malformed JSON
                    }
                }
                return true;  // Continue receiving
            }
        );

        if (!response) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "Failed to connect to Ollama for streaming at " + config_.host
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "Ollama streaming error (" +
                                   std::to_string(response->status) + "): " +
                                   response->body;
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    error_msg
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
