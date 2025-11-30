/**
 * @file conversational_example.cpp
 * @brief Example demonstrating Conversational pattern
 *
 * This example shows how to maintain conversation history across multiple turns.
 */

#include <iostream>
#include "agenkit/patterns/conversational.hpp"

using namespace agenkit;

// Mock LLM that demonstrates context awareness
class ContextAwareLLM : public core::Agent {
private:
    std::map<std::string, std::string> memory_;

public:
    std::string name() const override { return "context_aware_llm"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content = message.content_as_str();
        std::string response;

        // Check if we have conversation history
        if (message.metadata().contains("conversation_history")) {
            auto history = message.metadata()["conversation_history"];

            // Analyze history for context
            for (const auto& msg : history) {
                std::string role = msg["role"];
                std::string msg_content = msg["content"];

                // Extract name from previous conversation
                if (msg_content.find("My name is ") != std::string::npos) {
                    size_t pos = msg_content.find("My name is ") + 11;
                    size_t end = msg_content.find_first_of(".,!", pos);
                    if (end == std::string::npos) end = msg_content.length();
                    memory_["user_name"] = msg_content.substr(pos, end - pos);
                }

                // Extract favorite color
                if (msg_content.find("favorite color is ") != std::string::npos) {
                    size_t pos = msg_content.find("favorite color is ") + 18;
                    size_t end = msg_content.find_first_of(".,!", pos);
                    if (end == std::string::npos) end = msg_content.length();
                    memory_["favorite_color"] = msg_content.substr(pos, end - pos);
                }
            }
        }

        // Generate context-aware response
        if (content.find("name") != std::string::npos && content.find("?") != std::string::npos) {
            if (memory_.count("user_name")) {
                response = "Your name is " + memory_["user_name"] + "!";
            } else {
                response = "I don't know your name yet. Could you tell me?";
            }
        } else if (content.find("favorite color") != std::string::npos && content.find("?") != std::string::npos) {
            if (memory_.count("favorite_color")) {
                response = "Your favorite color is " + memory_["favorite_color"] + "!";
            } else {
                response = "I don't know your favorite color yet.";
            }
        } else if (content.find("My name is ") != std::string::npos) {
            size_t pos = content.find("My name is ") + 11;
            size_t end = content.find_first_of(".,!", pos);
            if (end == std::string::npos) end = content.length();
            std::string name = content.substr(pos, end - pos);
            response = "Nice to meet you, " + name + "! I'll remember that.";
        } else if (content.find("favorite color is ") != std::string::npos) {
            size_t pos = content.find("favorite color is ") + 18;
            size_t end = content.find_first_of(".,!", pos);
            if (end == std::string::npos) end = content.length();
            std::string color = content.substr(pos, end - pos);
            response = color + " is a great color! I'll remember that.";
        } else if (content.find("tell me about me") != std::string::npos) {
            if (memory_.count("user_name") && memory_.count("favorite_color")) {
                response = "You're " + memory_["user_name"] + " and your favorite color is "
                          + memory_["favorite_color"] + "!";
            } else if (memory_.count("user_name")) {
                response = "I know your name is " + memory_["user_name"] + ".";
            } else {
                response = "I don't know much about you yet. Tell me more!";
            }
        } else {
            response = "I'm listening! Tell me more about yourself.";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

int main() {
    std::cout << "=== Agenkit C++ Conversational Example ===\n\n";

    // Create conversational agent with system prompt
    auto llm = std::make_shared<ContextAwareLLM>();

    patterns::ConversationalConfig config;
    config.max_history = 10;
    config.system_prompt = "You are a friendly assistant that remembers user information.";

    patterns::ConversationalAgent agent(llm, config);

    std::cout << "Agent: " << agent.name() << "\n";
    std::cout << "Capabilities: ";
    for (const auto& cap : agent.capabilities()) {
        std::cout << cap << " ";
    }
    std::cout << "\n";
    std::cout << "Max history: " << config.max_history << "\n";
    std::cout << "System prompt: " << config.system_prompt.value() << "\n\n";

    // Conversation turns
    std::vector<std::string> conversation = {
        "My name is Alice.",
        "What's my name?",
        "My favorite color is blue.",
        "What's my favorite color?",
        "Can you tell me about me?"
    };

    std::cout << "=== Multi-turn Conversation ===\n\n";

    for (size_t i = 0; i < conversation.size(); i++) {
        std::cout << "Turn " << (i + 1) << ":\n";
        std::cout << "User: " << conversation[i] << "\n";

        auto msg = core::Message::with_text("user", conversation[i]);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "Assistant: " << response.content_as_str() << "\n";
            std::cout << "History length: " << agent.get_context_length() << "\n";
        }

        std::cout << "\n";
    }

    // Export history
    std::cout << "=== Conversation History ===\n";
    auto history = agent.get_history();

    for (size_t i = 0; i < history.size(); i++) {
        std::cout << "\n[" << i << "] " << history[i].role() << ": ";
        std::cout << history[i].content_as_str() << "\n";
    }

    // Export and import demo
    std::cout << "\n=== Export/Import Demo ===\n";
    auto exported = agent.export_history();
    std::cout << "Exported " << exported.size() << " messages\n";

    // Create new agent and import
    auto llm2 = std::make_shared<ContextAwareLLM>();
    patterns::ConversationalAgent agent2(llm2, config);
    agent2.import_history(exported);

    std::cout << "Imported into new agent\n";
    std::cout << "New agent history length: " << agent2.get_context_length() << "\n";

    // Continue conversation with new agent
    auto msg = core::Message::with_text("user", "What's my name again?");
    auto result = agent2.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << "New agent response: " << result.unwrap().content_as_str() << "\n";
    }

    // History pruning demo
    std::cout << "\n=== History Pruning Demo ===\n";
    auto llm3 = std::make_shared<ContextAwareLLM>();
    patterns::ConversationalConfig small_config;
    small_config.max_history = 4;

    patterns::ConversationalAgent agent3(llm3, small_config);

    std::cout << "Creating agent with max_history = 4\n";

    for (int i = 0; i < 6; i++) {
        auto msg = core::Message::with_text("user", "Message " + std::to_string(i));
        agent3.process(std::move(msg)).get();
        std::cout << "After message " << i << ": " << agent3.get_context_length()
                  << " messages in history\n";
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. Context preservation: Agent remembers previous turns\n";
    std::cout << "2. Automatic pruning: Oldest messages removed when limit reached\n";
    std::cout << "3. System prompt: Preserved during pruning\n";
    std::cout << "4. History export/import: Enable conversation persistence\n";
    std::cout << "5. Turn tracking: Metadata tracks conversation progress\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
