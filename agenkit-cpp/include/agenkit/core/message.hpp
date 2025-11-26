/**
 * @file message.hpp
 * @brief Universal message format for agent communication
 *
 * This module provides the core Message type for agent communication,
 * following the same design as Python, Go, TypeScript, and Rust implementations.
 */

#ifndef AGENKIT_CORE_MESSAGE_HPP
#define AGENKIT_CORE_MESSAGE_HPP

#include <string>
#include <chrono>
#include <memory>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace core {

/**
 * @brief Universal message format for agent communication
 *
 * Design decisions:
 * - role: Identifies message source ("user", "assistant", "system", "tool")
 * - content: Flexible JSON value for any serializable data
 * - metadata: Extension point for framework-specific data
 * - timestamp: UTC timestamp for ordering and debugging
 *
 * @example
 * @code
 * auto msg = Message::with_text("user", "Hello, agent!");
 * msg.with_metadata("session_id", "abc123");
 * @endcode
 */
class Message {
public:
    /**
     * @brief Create a new message with role and JSON content
     * @param role Message role (e.g., "user", "assistant", "system", "tool")
     * @param content Message content as JSON value
     */
    Message(std::string role, nlohmann::json content);

    /**
     * @brief Create a message with text content (convenience method)
     * @param role Message role
     * @param text Text content
     * @return Message with text content
     */
    static Message with_text(std::string role, std::string text);

    /**
     * @brief Get message role
     * @return Message role
     */
    const std::string& role() const;

    /**
     * @brief Get message content
     * @return Message content as JSON
     */
    const nlohmann::json& content() const;

    /**
     * @brief Get message metadata
     * @return Message metadata as JSON object
     */
    const nlohmann::json& metadata() const;

    /**
     * @brief Get message timestamp
     * @return UTC timestamp
     */
    std::chrono::system_clock::time_point timestamp() const;

    /**
     * @brief Add metadata to message (fluent interface)
     * @param key Metadata key
     * @param value Metadata value as JSON
     * @return Reference to this message for chaining
     */
    Message& with_metadata(const std::string& key, nlohmann::json value);

    /**
     * @brief Get content as string (if it's a string)
     * @return Content string, or empty string if not a string
     */
    std::string content_as_str() const;

    /**
     * @brief Serialize message to JSON
     * @return JSON representation of message
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize message from JSON
     * @param j JSON object
     * @return Message instance
     * @throws std::invalid_argument if JSON is invalid
     */
    static Message from_json(const nlohmann::json& j);

private:
    std::string role_;
    nlohmann::json content_;
    nlohmann::json metadata_;
    std::chrono::system_clock::time_point timestamp_;
};

/**
 * @brief Tool result from tool execution
 *
 * Represents the result of executing a tool, including success/error status.
 */
class ToolResult {
public:
    /**
     * @brief Create a tool result
     * @param tool_use_id ID of the tool use that generated this result
     * @param result Result data as JSON
     * @param is_error Whether this represents an error (default: false)
     */
    ToolResult(std::string tool_use_id, nlohmann::json result, bool is_error = false);

    /**
     * @brief Get tool use ID
     * @return Tool use ID
     */
    const std::string& tool_use_id() const;

    /**
     * @brief Get result data
     * @return Result as JSON
     */
    const nlohmann::json& result() const;

    /**
     * @brief Check if this is an error result
     * @return true if error, false if success
     */
    bool is_error() const;

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return ToolResult instance
     */
    static ToolResult from_json(const nlohmann::json& j);

private:
    std::string tool_use_id_;
    nlohmann::json result_;
    bool is_error_;
};

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_MESSAGE_HPP
