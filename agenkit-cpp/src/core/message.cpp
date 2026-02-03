/**
 * @file message.cpp
 * @brief Implementation of Message and ToolResult classes
 */

#include "agenkit/core/message.hpp"
#include <stdexcept>
#include <iomanip>
#include <sstream>

namespace agenkit {
namespace core {

// Message implementation

Message::Message(std::string role, nlohmann::json content)
    : role_(std::move(role))
    , content_(std::move(content))
    , metadata_(nlohmann::json::object())
    , timestamp_(std::chrono::system_clock::now())
{
    if (role_.empty()) {
        throw std::invalid_argument("message role must be a non-empty string");
    }
}

Message Message::with_text(std::string role, std::string text) {
    return Message(std::move(role), nlohmann::json(std::move(text)));
}

const std::string& Message::role() const {
    return role_;
}

const nlohmann::json& Message::content() const {
    return content_;
}

const nlohmann::json& Message::metadata() const {
    return metadata_;
}

std::chrono::system_clock::time_point Message::timestamp() const {
    return timestamp_;
}

Message& Message::with_metadata(const std::string& key, nlohmann::json value) {
    metadata_[key] = std::move(value);
    return *this;
}

std::string Message::content_as_str() const {
    if (content_.is_string()) {
        return content_.get<std::string>();
    }
    return "";
}

nlohmann::json Message::to_json() const {
    nlohmann::json j;
    j["role"] = role_;
    j["content"] = content_;
    j["metadata"] = metadata_;

    // Convert timestamp to ISO 8601 string
    auto time_t = std::chrono::system_clock::to_time_t(timestamp_);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%SZ");
    j["timestamp"] = ss.str();

    return j;
}

Message Message::from_json(const nlohmann::json& j) {
    if (!j.contains("role") || !j["role"].is_string()) {
        throw std::invalid_argument("invalid message format: missing or invalid 'role'");
    }
    if (!j.contains("content")) {
        throw std::invalid_argument("invalid message format: missing 'content'");
    }

    Message msg(j["role"].get<std::string>(), j["content"]);

    if (j.contains("metadata") && j["metadata"].is_object()) {
        msg.metadata_ = j["metadata"];
    }

    // Parse timestamp if present (simplified - uses current time if not present)
    if (j.contains("timestamp") && j["timestamp"].is_string()) {
        // For now, use current time - full ISO 8601 parsing would require additional library
        // In production, you'd want to parse the timestamp string properly
        msg.timestamp_ = std::chrono::system_clock::now();
    }

    return msg;
}

void Message::validate() const {
    // Role validation
    if (role_.empty()) {
        throw MessageValidationError("Message role cannot be empty");
    }

    if (role_.length() > 20) {
        throw MessageValidationError(
            "Message role exceeds maximum length of 20 characters (got " +
            std::to_string(role_.length()) + ")"
        );
    }

    // Validate role is one of the allowed values
    static const std::set<std::string> allowed_roles = {
        "user", "assistant", "system", "tool", "agent"
    };
    if (allowed_roles.find(role_) == allowed_roles.end()) {
        throw MessageValidationError(
            "Invalid message role: " + role_ +
            ". Must be one of: user, assistant, system, tool, agent"
        );
    }

    // Content size validation - max 16MB
    std::string content_str = content_.dump();
    size_t content_size = content_str.size();
    constexpr size_t max_content_size = 16 * 1024 * 1024; // 16MB

    if (content_size > max_content_size) {
        throw MessageValidationError(
            "Message content exceeds maximum size of " +
            std::to_string(max_content_size) + " bytes (got " +
            std::to_string(content_size) + " bytes)"
        );
    }

    // Metadata validation
    if (!metadata_.is_null() && metadata_.is_object()) {
        // Max 100 keys
        if (metadata_.size() > 100) {
            throw MessageValidationError(
                "Message metadata exceeds maximum of 100 keys (got " +
                std::to_string(metadata_.size()) + ")"
            );
        }

        // Validate each key and value
        constexpr size_t max_key_length = 50;
        constexpr size_t max_value_size = 16 * 1024 * 1024; // 16MB

        for (auto& [key, value] : metadata_.items()) {
            // Key length validation
            if (key.length() > max_key_length) {
                std::string short_key = key.substr(0, 20) + "...";
                throw MessageValidationError(
                    "Metadata key '" + short_key +
                    "' exceeds maximum length of " +
                    std::to_string(max_key_length) +
                    " characters (got " +
                    std::to_string(key.length()) + ")"
                );
            }

            // Value size validation
            std::string value_str = value.dump();
            size_t value_size = value_str.size();

            if (value_size > max_value_size) {
                throw MessageValidationError(
                    "Metadata value for key '" + key +
                    "' exceeds maximum size of " +
                    std::to_string(max_value_size) +
                    " bytes (got " + std::to_string(value_size) + " bytes)"
                );
            }
        }
    }
}

// ToolResult implementation

ToolResult::ToolResult(std::string tool_use_id, nlohmann::json result, bool is_error)
    : tool_use_id_(std::move(tool_use_id))
    , result_(std::move(result))
    , is_error_(is_error)
{
    if (tool_use_id_.empty()) {
        throw std::invalid_argument("tool_use_id must be a non-empty string");
    }
}

const std::string& ToolResult::tool_use_id() const {
    return tool_use_id_;
}

const nlohmann::json& ToolResult::result() const {
    return result_;
}

bool ToolResult::is_error() const {
    return is_error_;
}

nlohmann::json ToolResult::to_json() const {
    nlohmann::json j;
    j["tool_use_id"] = tool_use_id_;
    j["result"] = result_;
    j["is_error"] = is_error_;
    return j;
}

ToolResult ToolResult::from_json(const nlohmann::json& j) {
    if (!j.contains("tool_use_id") || !j["tool_use_id"].is_string()) {
        throw std::invalid_argument("invalid tool result format: missing or invalid 'tool_use_id'");
    }
    if (!j.contains("result")) {
        throw std::invalid_argument("invalid tool result format: missing 'result'");
    }

    bool is_error = false;
    if (j.contains("is_error") && j["is_error"].is_boolean()) {
        is_error = j["is_error"].get<bool>();
    }

    return ToolResult(
        j["tool_use_id"].get<std::string>(),
        j["result"],
        is_error
    );
}

} // namespace core
} // namespace agenkit
