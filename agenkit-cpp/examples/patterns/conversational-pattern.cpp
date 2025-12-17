/**
 * @file conversational-pattern.cpp
 * @brief Conversational pattern with real LLM (Ollama)
 *
 * Demonstrates:
 * - Multi-turn conversation with context preservation
 * - Conversation history management and pruning
 * - Real LLM understanding of context
 * - History export/import for persistence
 *
 * Setup:
 *   brew install ollama
 *   ollama serve
 *   ollama pull llama3.3
 *   ./build/examples/patterns/conversational-pattern
 */

#include <iostream>
#include <memory>
#include "agenkit/patterns/conversational.hpp"
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

void print_separator(const std::string& title = "") {
    std::cout << "\n";
    std::cout << std::string(60, '=') << "\n";
    if (!title.empty()) {
        std::cout << title << "\n";
        std::cout << std::string(60, '=') << "\n";
    }
    std::cout << "\n";
}

int main() {
    print_separator("AgentKit C++ - Conversational Pattern with Real LLM");

    // Check Ollama availability
    std::cout << "Checking Ollama server...\n";
    adapters::OllamaConfig check_config;
    check_config.host = "http://localhost:11434";
    check_config.model = "llama3.3";

    adapters::OllamaAgent checker(check_config);
    if (!checker.is_available()) {
        std::cerr << "❌ Ollama server not available\n\n";
        std::cerr << "Please start Ollama:\n";
        std::cerr << "  1. Install: brew install ollama\n";
        std::cerr << "  2. Start:   ollama serve\n";
        std::cerr << "  3. Pull:    ollama pull llama3.3\n\n";
        return 1;
    }
    std::cout << "✓ Ollama server running\n";

    // Example 1: Personal Assistant Conversation
    print_separator("Example 1: Personal Assistant Conversation");
    {
        // Create Ollama agent with friendly system prompt
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.7;
        config.system = "You are a friendly personal assistant. Remember details "
                        "the user shares and use them in future responses. Be concise "
                        "and conversational.";

        auto llm = std::make_shared<adapters::OllamaAgent>(config);

        // Create conversational agent
        patterns::ConversationalConfig conv_config;
        conv_config.max_history = 10;
        conv_config.system_prompt = config.system;

        patterns::ConversationalAgent agent(llm, conv_config);

        std::cout << "Agent: " << agent.name() << "\n";
        std::cout << "Max history: " << conv_config.max_history << " messages\n\n";

        // Multi-turn conversation demonstrating context awareness
        std::vector<std::string> conversation = {
            "Hi! My name is Alex and I'm a software engineer.",
            "What's my name?",
            "I love working with C++ and building AI systems.",
            "What programming languages do I like?",
            "Can you summarize what you know about me?"
        };

        std::cout << "=== Multi-Turn Conversation ===\n\n";

        for (size_t i = 0; i < conversation.size(); i++) {
            std::cout << "Turn " << (i + 1) << ":\n";
            std::cout << "User: " << conversation[i] << "\n\n";

            auto msg = core::Message::with_text("user", conversation[i]);
            auto result = agent.process(std::move(msg)).get();

            if (result.is_ok()) {
                auto response = result.unwrap();
                std::cout << "Assistant: " << response.content_as_str() << "\n";
                std::cout << "History: " << agent.get_context_length() << " messages\n\n";
            } else {
                std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n\n";
            }
        }
    }

    // Example 2: Technical Support Conversation
    print_separator("Example 2: Technical Support Conversation");
    {
        // Create specialized technical support agent
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.5;  // Lower temperature for more consistent technical responses
        config.system = "You are a technical support specialist. Help users debug "
                        "issues by asking clarifying questions and providing step-by-step "
                        "solutions. Keep responses under 50 words.";

        auto llm = std::make_shared<adapters::OllamaAgent>(config);

        patterns::ConversationalConfig conv_config;
        conv_config.max_history = 8;
        conv_config.system_prompt = config.system;

        patterns::ConversationalAgent agent(llm, conv_config);

        std::cout << "Starting technical support session...\n\n";

        std::vector<std::string> support_conversation = {
            "My application is crashing when I try to start it",
            "It's a C++ application",
            "The error says 'segmentation fault'",
            "How can I debug this?"
        };

        for (size_t i = 0; i < support_conversation.size(); i++) {
            std::cout << "User: " << support_conversation[i] << "\n\n";

            auto msg = core::Message::with_text("user", support_conversation[i]);
            auto result = agent.process(std::move(msg)).get();

            if (result.is_ok()) {
                auto response = result.unwrap();
                std::cout << "Support: " << response.content_as_str() << "\n";
                std::cout << "(History: " << agent.get_context_length() << " messages)\n\n";
            }
        }
    }

    // Example 3: History Management
    print_separator("Example 3: History Export/Import");
    {
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.7;
        config.system = "You are a helpful assistant.";

        auto llm1 = std::make_shared<adapters::OllamaAgent>(config);

        patterns::ConversationalConfig conv_config;
        conv_config.max_history = 10;
        patterns::ConversationalAgent agent1(llm1, conv_config);

        std::cout << "Building conversation history in Agent 1...\n";

        // Build up some history
        auto msg1 = core::Message::with_text("user", "I'm working on a distributed system");
        agent1.process(std::move(msg1)).get();

        auto msg2 = core::Message::with_text("user", "It uses microservices architecture");
        agent1.process(std::move(msg2)).get();

        std::cout << "Agent 1 history: " << agent1.get_context_length() << " messages\n\n";

        // Export history
        auto exported = agent1.export_history();
        std::cout << "✓ Exported " << exported.size() << " messages\n\n";

        // Create new agent and import
        std::cout << "Creating Agent 2 and importing history...\n";
        auto llm2 = std::make_shared<adapters::OllamaAgent>(config);
        patterns::ConversationalAgent agent2(llm2, conv_config);
        agent2.import_history(exported);

        std::cout << "Agent 2 history after import: " << agent2.get_context_length() << " messages\n\n";

        // Test that Agent 2 has the context
        std::cout << "Testing context awareness in Agent 2:\n";
        std::cout << "User: What architecture am I using?\n\n";

        auto msg3 = core::Message::with_text("user", "What architecture am I using?");
        auto result = agent2.process(std::move(msg3)).get();

        if (result.is_ok()) {
            std::cout << "Agent 2: " << result.unwrap().content_as_str() << "\n";
            std::cout << "✓ Context successfully preserved across agents\n";
        }
    }

    // Example 4: History Pruning
    print_separator("Example 4: Automatic History Pruning");
    {
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";

        auto llm = std::make_shared<adapters::OllamaAgent>(config);

        patterns::ConversationalConfig conv_config;
        conv_config.max_history = 4;  // Small limit to demonstrate pruning

        patterns::ConversationalAgent agent(llm, conv_config);

        std::cout << "Agent with max_history = 4 messages\n";
        std::cout << "Sending 6 messages to demonstrate pruning...\n\n";

        for (int i = 1; i <= 6; i++) {
            auto msg = core::Message::with_text("user", "Message " + std::to_string(i));
            agent.process(std::move(msg)).get();

            std::cout << "After message " << i << ": "
                     << agent.get_context_length() << " messages in history";

            if (agent.get_context_length() == conv_config.max_history) {
                std::cout << " (limit reached, oldest pruned)";
            }
            std::cout << "\n";
        }

        std::cout << "\n✓ History automatically pruned to maintain limit\n";
    }

    // Summary
    print_separator("Key Insights");
    std::cout << "✓ Real LLM: Using Ollama for actual conversation understanding\n";
    std::cout << "✓ Context Preservation: Agent remembers previous turns\n";
    std::cout << "✓ System Prompts: Customize agent personality and behavior\n";
    std::cout << "✓ Automatic Pruning: Oldest messages removed when limit reached\n";
    std::cout << "✓ History Persistence: Export/import enables conversation saving\n";
    std::cout << "✓ Specialization: Different agents for different conversation types\n";

    print_separator("Example Complete");
    return 0;
}
