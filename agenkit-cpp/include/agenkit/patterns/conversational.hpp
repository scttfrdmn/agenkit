/**
 * @file conversational.hpp
 * @brief Conversational agent pattern for multi-turn dialogue
 *
 * This module implements the Conversational pattern, which maintains conversation
 * history across multiple turns to provide context-aware responses.
 */

#ifndef AGENKIT_PATTERNS_CONVERSATIONAL_HPP
#define AGENKIT_PATTERNS_CONVERSATIONAL_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <vector>
#include <string>
#include <optional>

namespace agenkit {
namespace patterns {

/**
 * @brief Configuration for conversational agents
 */
struct ConversationalConfig {
    /// Maximum number of messages to retain in history
    int max_history{10};

    /// Optional system prompt to prepend to conversations
    std::optional<std::string> system_prompt{std::nullopt};

    /// Whether to include system prompt in history count
    bool include_system_in_count{false};
};

/**
 * @brief Agent that maintains conversation history for context-aware responses
 *
 * The ConversationalAgent wraps another agent and manages conversation history,
 * automatically including previous messages for context when processing new messages.
 *
 * Features:
 * - Automatic history management
 * - Configurable history window
 * - System prompt support
 * - History pruning (oldest non-system messages removed first)
 * - History export/import for persistence
 *
 * @example
 * @code
 * auto llm = std::make_shared<MyLLMAgent>();
 * ConversationalConfig config;
 * config.max_history = 10;
 * config.system_prompt = "You are a helpful assistant.";
 *
 * ConversationalAgent agent(llm, config);
 *
 * // First turn
 * auto response1 = agent.process(
 *     Message::with_text("user", "My name is Alice")
 * ).get();
 *
 * // Second turn - agent remembers the name
 * auto response2 = agent.process(
 *     Message::with_text("user", "What's my name?")
 * ).get();
 * @endcode
 */
class ConversationalAgent : public core::Agent {
public:
    /**
     * @brief Construct a conversational agent
     * @param agent The underlying agent to wrap
     * @param config Configuration for conversation management
     * @throws std::invalid_argument if agent is nullptr
     */
    explicit ConversationalAgent(
        std::shared_ptr<core::Agent> agent,
        ConversationalConfig config = ConversationalConfig{}
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get a copy of the current conversation history
     * @return Vector of messages in conversation history
     */
    std::vector<core::Message> get_history() const;

    /**
     * @brief Get the current number of messages in history
     * @return Number of messages in history
     */
    size_t get_context_length() const;

    /**
     * @brief Clear conversation history
     * @param keep_system If true, preserves system prompt (default: true)
     */
    void clear_history(bool keep_system = true);

    /**
     * @brief Export history in serializable format
     * @return JSON array of message objects
     */
    nlohmann::json export_history() const;

    /**
     * @brief Import conversation history from serialized format
     * @param history JSON array of message objects
     * @throws std::invalid_argument if JSON format is invalid
     */
    void import_history(const nlohmann::json& history);

    /**
     * @brief Get the current configuration
     * @return Current configuration
     */
    ConversationalConfig get_config() const;

    /**
     * @brief Update configuration
     * @param config New configuration
     */
    void set_config(const ConversationalConfig& config);

private:
    std::shared_ptr<core::Agent> agent_;
    ConversationalConfig config_;
    std::vector<core::Message> history_;

    /**
     * @brief Prune history to stay within max_history limit
     *
     * System messages are preserved, oldest user/assistant messages removed first.
     */
    void prune_history();

    /**
     * @brief Create a message containing the conversation history
     * @param new_message The new message to process
     * @return Message with full conversation context
     */
    core::Message create_context_message(const core::Message& new_message);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_CONVERSATIONAL_HPP
