/**
 * @file gemini_agent.cpp
 * @brief Implementation of Google Gemini API adapter
 */

#include "agenkit/adapters/gemini_agent.hpp"
#include "agenkit/adapters/validation.hpp"
#include "agenkit/core/sse_parser.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <cstdlib>
#include <sstream>

namespace agenkit {
namespace adapters {

using json = nlohmann::json;

GeminiAgent::GeminiAgent(GeminiConfig config)
    : config_(std::move(config))
{
    // Load API key from environment if not provided
    if (!config_.api_key.has_value()) {
        load_api_key_from_env();
    }

    // Validate API key is set
    if (!config_.api_key.has_value() || config_.api_key.value().empty()) {
        throw std::invalid_argument(
            "Gemini API key required: provide api_key parameter or set "
            "GEMINI_API_KEY or GOOGLE_API_KEY environment variable"
        );
    }

    // Validate LLM parameters (if provided)
    if (config_.temperature.has_value()) {
        LLMParameterValidator::validate_temperature(config_.temperature.value());
    }
    if (config_.max_tokens.has_value()) {
        LLMParameterValidator::validate_max_tokens(config_.max_tokens.value());
    }
}

std::string GeminiAgent::name() const {
    return "gemini-" + config_.model;
}

std::future<core::Result<core::Message, core::AgentError>>
GeminiAgent::process(core::Message message) {
    return process_with(std::move(message), core::CallOptions{});
}

std::future<core::Result<core::Message, core::AgentError>>
GeminiAgent::process_with(core::Message message, const core::CallOptions& options) {
    // Convert message to Gemini API format
    json contents = json::array();
    contents.push_back(message_to_json(message));

    // Make API call
    auto result = call_api(contents, options);

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

std::vector<std::string> GeminiAgent::capabilities() const {
    return {"llm", "completion", "chat"};
}

const GeminiConfig& GeminiAgent::config() const {
    return config_;
}

void GeminiAgent::set_config(const GeminiConfig& config) {
    config_ = config;

    // Load API key from environment if not provided
    if (!config_.api_key.has_value()) {
        load_api_key_from_env();
    }

    // Validate API key is set
    if (!config_.api_key.has_value() || config_.api_key.value().empty()) {
        throw std::invalid_argument(
            "Gemini API key required: provide api_key parameter or set "
            "GEMINI_API_KEY or GOOGLE_API_KEY environment variable"
        );
    }

    // Validate LLM parameters (if provided)
    if (config_.temperature.has_value()) {
        LLMParameterValidator::validate_temperature(config_.temperature.value());
    }
    if (config_.max_tokens.has_value()) {
        LLMParameterValidator::validate_max_tokens(config_.max_tokens.value());
    }
}

void GeminiAgent::load_api_key_from_env() {
    // Try GEMINI_API_KEY first
    const char* key = std::getenv("GEMINI_API_KEY");
    if (key && key[0] != '\0') {
        config_.api_key = key;
        return;
    }

    // Try GOOGLE_API_KEY
    key = std::getenv("GOOGLE_API_KEY");
    if (key && key[0] != '\0') {
        config_.api_key = key;
        return;
    }
}

json GeminiAgent::build_request_body(const json& contents, const core::CallOptions& options) const {
    // Build request body
    json request_body = {
        {"contents", contents}
    };

    // Add generation config if any parameters are set. A per-call option
    // overrides the config default for that one call rather than merging
    // with it (e.g. options.stop replaces config_.stop_sequences wholesale).
    json generation_config;
    bool has_config = false;

    std::optional<double> temperature = options.temperature.has_value() ? options.temperature : config_.temperature;
    if (temperature.has_value()) {
        generation_config["temperature"] = temperature.value();
        has_config = true;
    }
    std::optional<int> max_tokens = options.max_tokens.has_value() ? options.max_tokens : config_.max_tokens;
    if (max_tokens.has_value()) {
        generation_config["maxOutputTokens"] = max_tokens.value();
        has_config = true;
    }
    std::optional<double> top_p = options.top_p.has_value() ? options.top_p : config_.top_p;
    if (top_p.has_value()) {
        generation_config["topP"] = top_p.value();
        has_config = true;
    }
    if (config_.top_k.has_value()) {
        generation_config["topK"] = config_.top_k.value();
        has_config = true;
    }

    // seed: Gemini's REST API supports it directly as an integer field on
    // generationConfig, no translation needed.
    if (options.seed.has_value()) {
        generation_config["seed"] = options.seed.value();
        has_config = true;
    }

    // stop -> stopSequences: options.stop overrides config_.stop_sequences
    // for this call when set, rather than merging with it.
    if (options.stop.has_value()) {
        generation_config["stopSequences"] = options.stop.value();
        has_config = true;
    } else if (!config_.stop_sequences.empty()) {
        generation_config["stopSequences"] = config_.stop_sequences;
        has_config = true;
    }

    if (has_config) {
        request_body["generationConfig"] = generation_config;
    }

    return request_body;
}

core::Result<nlohmann::json, core::AgentError>
GeminiAgent::call_api(const json& contents, const core::CallOptions& options) {
    try {
        // Build API endpoint URL
        // Format: /v1beta/models/{model}:generateContent?key={api_key}
        std::string path = "/v1beta/models/" + config_.model + ":generateContent";
        std::string query = "?key=" + config_.api_key.value();
        std::string endpoint = path + query;

        // Parse base URL for http client
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        json request_body = build_request_body(contents, options);

        // Set headers
        httplib::Headers headers = {
            {"Content-Type", "application/json"}
        };

        // Make request
        auto response = client.Post(endpoint.c_str(), headers,
                                   request_body.dump(),
                                   "application/json");

        if (!response) {
            return core::Result<json, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "failed to connect to Gemini API"
                )
            );
        }

        if (response->status != 200) {
            std::string error_msg = "Gemini API error (" +
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

json GeminiAgent::message_to_json(const core::Message& message) {
    // Map role to Gemini format
    std::string role = message.role();
    if (role == "assistant" || role == "agent") {
        role = "model";
    } else if (role == "system") {
        role = "user";  // Gemini treats system messages as user messages
    }
    // else keep "user" as is

    // Gemini format: { "role": "user|model", "parts": [{"text": "..."}] }
    return {
        {"role", role},
        {"parts", json::array({
            {{"text", message.content_as_str()}}
        })}
    };
}

core::Message GeminiAgent::json_to_message(const json& response) {
    // Extract text from Gemini response
    // Response format: { "candidates": [{"content": {"parts": [{"text": "..."}]}}], ... }
    std::string text;
    std::string role = "assistant";

    if (response.contains("candidates") && response["candidates"].is_array() &&
        !response["candidates"].empty()) {
        const auto& candidate = response["candidates"][0];
        if (candidate.contains("content")) {
            const auto& content = candidate["content"];
            if (content.contains("parts") && content["parts"].is_array()) {
                // Concatenate all text parts
                for (const auto& part : content["parts"]) {
                    if (part.contains("text")) {
                        text += part["text"].get<std::string>();
                    }
                }
            }
        }
    }

    auto msg = core::Message::with_text(role, text);

    // Add metadata from response
    msg.with_metadata("model", config_.model);

    // Add usage metadata if available
    if (response.contains("usageMetadata")) {
        const auto& usage = response["usageMetadata"];
        json usage_metadata;

        if (usage.contains("promptTokenCount")) {
            usage_metadata["prompt_tokens"] = usage["promptTokenCount"];
        }
        if (usage.contains("candidatesTokenCount")) {
            usage_metadata["completion_tokens"] = usage["candidatesTokenCount"];
        }
        if (usage.contains("totalTokenCount")) {
            usage_metadata["total_tokens"] = usage["totalTokenCount"];
        }

        if (!usage_metadata.empty()) {
            msg.with_metadata("usage", usage_metadata);
        }
    }

    // Add finish reason if available
    if (response.contains("candidates") && response["candidates"].is_array() &&
        !response["candidates"].empty()) {
        const auto& candidate = response["candidates"][0];
        if (candidate.contains("finishReason")) {
            msg.with_metadata("finish_reason", candidate["finishReason"]);
        }
    }

    return msg;
}

// Note (#818): stream() intentionally does not take a CallOptions, same
// rationale as OpenAIAgent::stream — #818 scopes per-call options to
// process()/process_with().
core::Result<void, core::AgentError>
GeminiAgent::stream(core::Message message, std::function<bool(const std::string&)> callback) {
    try {
        // Convert message to Gemini API format
        json contents = json::array();
        contents.push_back(message_to_json(message));

        // Build streaming API endpoint URL
        // Format: /v1beta/models/{model}:streamGenerateContent?key={api_key}
        std::string path = "/v1beta/models/" + config_.model + ":streamGenerateContent";
        std::string query = "?key=" + config_.api_key.value();
        std::string endpoint = path + query;

        // Parse base URL for http client
        httplib::Client client(config_.api_base);
        client.set_read_timeout(std::chrono::duration_cast<std::chrono::seconds>(config_.timeout).count(), 0);

        // Build request body
        json request_body = {
            {"contents", contents}
        };

        // Add generation config if any parameters are set
        json generation_config;
        bool has_config = false;

        if (config_.temperature.has_value()) {
            generation_config["temperature"] = config_.temperature.value();
            has_config = true;
        }
        if (config_.max_tokens.has_value()) {
            generation_config["maxOutputTokens"] = config_.max_tokens.value();
            has_config = true;
        }
        if (config_.top_p.has_value()) {
            generation_config["topP"] = config_.top_p.value();
            has_config = true;
        }
        if (config_.top_k.has_value()) {
            generation_config["topK"] = config_.top_k.value();
            has_config = true;
        }
        if (!config_.stop_sequences.empty()) {
            generation_config["stopSequences"] = config_.stop_sequences;
            has_config = true;
        }

        if (has_config) {
            request_body["generationConfig"] = generation_config;
        }

        // Set headers
        httplib::Headers headers = {
            {"Content-Type", "application/json"}
        };

        // Use httplib Request with content_receiver for true NDJSON streaming.
        // The :streamGenerateContent endpoint returns NDJSON (one JSON object per line).
        httplib::Request req;
        req.method = "POST";
        req.path = endpoint;
        req.headers = headers;
        req.body = request_body.dump();
        req.set_header("Content-Type", "application/json");

        core::SseParser parser;

        req.content_receiver = [&](const char* data, size_t data_length,
                                   uint64_t /*offset*/, uint64_t /*total*/) -> bool {
            return parser.feed(data, data_length, core::SseParser::Mode::NDJSON,
                [&](const std::string& json_str) -> bool {
                    try {
                        auto chunk = json::parse(json_str);
                        if (chunk.contains("candidates") && !chunk["candidates"].empty()) {
                            const auto& candidate = chunk["candidates"][0];
                            if (candidate.contains("content") &&
                                candidate["content"].contains("parts") &&
                                !candidate["content"]["parts"].empty()) {
                                const auto& part = candidate["content"]["parts"][0];
                                if (part.contains("text") && part["text"].is_string()) {
                                    callback(part["text"].get<std::string>());
                                }
                            }
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
                    "failed to connect to Gemini API for streaming: " +
                    httplib::to_string(err)
                )
            );
        }

        if (res.status != 200) {
            return core::Result<void, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    "Gemini streaming error (" + std::to_string(res.status) + "): " + res.body
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

} // namespace adapters
} // namespace agenkit
