/**
 * @file conversational.cpp
 * @brief Implementation of Conversational pattern
 */

#include "agenkit/patterns/conversational.hpp"
#include <algorithm>
#include <stdexcept>

namespace agenkit {
namespace patterns {

ConversationalAgent::ConversationalAgent(
    std::shared_ptr<core::Agent> agent,
    ConversationalConfig config
) : agent_(agent), config_(config) {
    if (!agent_) {
        throw std::invalid_argument("Agent cannot be null");
    }

    // Add system prompt to history if provided
    if (config_.system_prompt.has_value()) {
        auto system_msg = core::Message::with_text("system", config_.system_prompt.value());
        history_.push_back(std::move(system_msg));
    }
}

std::string ConversationalAgent::name() const {
    return "conversational";
}

std::vector<std::string> ConversationalAgent::capabilities() const {
    return {"conversation", "history", "context", "multi-turn"};
}

std::future<core::Result<core::Message, core::AgentError>>
ConversationalAgent::process(core::Message message) {
    // Add user message to history
    history_.push_back(core::Message(message));

    // Prune history if needed
    prune_history();

    // Create context message with full history
    auto context_msg = create_context_message(message);

    // Process with underlying agent
    auto result = agent_->process(std::move(context_msg)).get();

    if (result.is_err()) {
        return core::make_ready_future(result);
    }

    auto response = result.unwrap();

    // Add response to history
    history_.push_back(core::Message(response));

    // Prune again after adding response
    prune_history();

    // Add metadata about conversation state
    response.with_metadata("pattern", "conversational");
    response.with_metadata("history_length", static_cast<int>(history_.size()));
    response.with_metadata("turn", static_cast<int>(history_.size() / 2));

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(response)
    );
}

std::vector<core::Message> ConversationalAgent::get_history() const {
    return history_;
}

size_t ConversationalAgent::get_context_length() const {
    return history_.size();
}

void ConversationalAgent::clear_history(bool keep_system) {
    if (keep_system && config_.system_prompt.has_value()) {
        auto system_msg = core::Message::with_text("system", config_.system_prompt.value());
        history_.clear();
        history_.push_back(std::move(system_msg));
    } else {
        history_.clear();
    }
}

nlohmann::json ConversationalAgent::export_history() const {
    nlohmann::json history_json = nlohmann::json::array();

    for (const auto& msg : history_) {
        history_json.push_back(msg.to_json());
    }

    return history_json;
}

void ConversationalAgent::import_history(const nlohmann::json& history) {
    if (!history.is_array()) {
        throw std::invalid_argument("History must be a JSON array");
    }

    history_.clear();

    for (const auto& msg_json : history) {
        history_.push_back(core::Message::from_json(msg_json));
    }
}

ConversationalConfig ConversationalAgent::get_config() const {
    return config_;
}

void ConversationalAgent::set_config(const ConversationalConfig& config) {
    config_ = config;
    prune_history();
}

void ConversationalAgent::prune_history() {
    if (static_cast<int>(history_.size()) <= config_.max_history) {
        return;
    }

    // Separate system messages from conversation
    std::vector<core::Message> system_messages;
    std::vector<core::Message> conversation_messages;

    for (auto& msg : history_) {
        if (msg.role() == "system") {
            system_messages.push_back(std::move(msg));
        } else {
            conversation_messages.push_back(std::move(msg));
        }
    }

    // Calculate how many conversation messages to keep
    int system_count = static_cast<int>(system_messages.size());
    int available_slots = config_.max_history;

    if (!config_.include_system_in_count) {
        // System messages don't count toward limit
        available_slots = config_.max_history;
    } else {
        // System messages count toward limit
        available_slots = config_.max_history - system_count;
    }

    // Keep only the most recent conversation messages
    if (available_slots > 0 &&
        static_cast<int>(conversation_messages.size()) > available_slots) {
        auto keep_from = conversation_messages.end() - available_slots;
        conversation_messages.erase(conversation_messages.begin(), keep_from);
    } else if (available_slots <= 0) {
        conversation_messages.clear();
    }

    // Rebuild history with system messages first
    history_.clear();
    history_.reserve(system_messages.size() + conversation_messages.size());

    for (auto& msg : system_messages) {
        history_.push_back(std::move(msg));
    }
    for (auto& msg : conversation_messages) {
        history_.push_back(std::move(msg));
    }
}

core::Message ConversationalAgent::create_context_message(
    const core::Message& new_message
) {
    // For conversational agents, we pass the history context through metadata
    // The underlying agent can access the full conversation context
    nlohmann::json history_json = nlohmann::json::array();

    for (const auto& msg : history_) {
        history_json.push_back(msg.to_json());
    }

    auto context_msg = core::Message(new_message);
    context_msg.with_metadata("conversation_history", history_json);
    context_msg.with_metadata("turn", static_cast<int>(history_.size() / 2 + 1));

    return context_msg;
}

} // namespace patterns
} // namespace agenkit
