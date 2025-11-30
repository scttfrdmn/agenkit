/**
 * @file conversation_memory.cpp
 * @brief Conversational agent with memory
 *
 * Demonstrates:
 * - Conversational pattern with context preservation
 * - Memory across multiple turns
 * - Natural multi-turn dialogue
 * - Context building over time
 *
 * Setup:
 *   export OPENAI_API_KEY=your-key
 *   cmake -B build -S .
 *   cmake --build build
 *   ./build/examples/conversation_memory
 */

#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/patterns/conversational.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>
#include <memory>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::patterns;
using namespace agenkit::core;

void print_separator(const std::string& title = "") {
    std::cout << "\n" << std::string(60, '-') << "\n";
    if (!title.empty()) {
        std::cout << title << "\n" << std::string(60, '-') << "\n";
    }
    std::cout << "\n";
}

int main() {
    std::cout << std::string(60, '=') << "\n";
    std::cout << "AgentKit C++ - Memory & Conversation Example\n";
    std::cout << std::string(60, '=') << "\n\n";

    const char* api_key = std::getenv("OPENAI_API_KEY");
    if (!api_key) {
        std::cerr << "❌ OPENAI_API_KEY environment variable not set\n";
        return 1;
    }

    std::cout << "✓ Initialized LLM adapter\n\n";

    // Example 1: Personal assistant with memory
    print_separator("Example 1: Personal Assistant Conversation");

    try {
        OpenAIConfig config;
        config.api_key = api_key;
        config.model = OpenAIModels::GPT_4O;
        config.temperature = 0.7;
        config.max_tokens = 200;

        auto llm = std::make_shared<OpenAIAgent>(config);

        ConversationalConfig conv_config;
        conv_config.system_prompt = "You are a helpful personal assistant. "
                                   "Remember details about the user and reference them in future responses.";
        conv_config.max_history = 10;

        ConversationalAgent assistant(llm, conv_config);

        std::cout << "System: You are a helpful personal assistant.\n";
        std::cout << "Max history: 10 messages\n\n";

        // Turn 1
        std::cout << "User: My name is Alex and I'm a software engineer.\n";
        auto msg1 = Message::with_text("user", "My name is Alex and I'm a software engineer.");
        auto future1 = assistant.process(std::move(msg1));
        auto result1 = future1.get();
        if (result1.is_ok()) {
            std::cout << "Assistant: " << result1.unwrap().content_as_str() << "\n\n";
        }

        // Turn 2
        std::cout << "User: I'm working on a C++ project using AgentKit.\n";
        auto msg2 = Message::with_text("user", "I'm working on a C++ project using AgentKit.");
        auto future2 = assistant.process(std::move(msg2));
        auto result2 = future2.get();
        if (result2.is_ok()) {
            std::cout << "Assistant: " << result2.unwrap().content_as_str() << "\n\n";
        }

        // Turn 3 - Test memory
        std::cout << "User: What was my name again?\n";
        auto msg3 = Message::with_text("user", "What was my name again?");
        auto future3 = assistant.process(std::move(msg3));
        auto result3 = future3.get();
        if (result3.is_ok()) {
            std::cout << "Assistant: " << result3.unwrap().content_as_str() << "\n\n";
        }

        // Turn 4 - Test memory
        std::cout << "User: What am I working on?\n";
        auto msg4 = Message::with_text("user", "What am I working on?");
        auto future4 = assistant.process(std::move(msg4));
        auto result4 = future4.get();
        if (result4.is_ok()) {
            std::cout << "Assistant: " << result4.unwrap().content_as_str() << "\n\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 2: Technical advisor conversation
    print_separator("Example 2: Technical Advisor Conversation");

    try {
        OpenAIConfig config;
        config.api_key = api_key;
        config.model = OpenAIModels::GPT_4_TURBO;
        config.temperature = 0.7;
        config.max_tokens = 250;

        auto llm = std::make_shared<OpenAIAgent>(config);

        ConversationalConfig conv_config;
        conv_config.system_prompt = "You are a technical advisor specializing in system design. "
                                   "Build on previous context in your responses.";
        conv_config.max_history = 15;

        ConversationalAgent advisor(llm, conv_config);

        std::cout << "System: Technical advisor specializing in system design.\n\n";

        // Turn 1
        std::cout << "User: I need to design a microservices architecture.\n";
        auto msg1 = Message::with_text("user", "I need to design a microservices architecture.");
        auto future1 = advisor.process(std::move(msg1));
        auto result1 = future1.get();
        if (result1.is_ok()) {
            std::cout << "Advisor: " << result1.unwrap().content_as_str() << "\n\n";
        }

        // Turn 2
        std::cout << "User: The system needs to handle 10,000 requests per second.\n";
        auto msg2 = Message::with_text("user", "The system needs to handle 10,000 requests per second.");
        auto future2 = advisor.process(std::move(msg2));
        auto result2 = future2.get();
        if (result2.is_ok()) {
            std::cout << "Advisor: " << result2.unwrap().content_as_str() << "\n\n";
        }

        // Turn 3
        std::cout << "User: What database would you recommend?\n";
        auto msg3 = Message::with_text("user", "What database would you recommend?");
        auto future3 = advisor.process(std::move(msg3));
        auto result3 = future3.get();
        if (result3.is_ok()) {
            std::cout << "Advisor: " << result3.unwrap().content_as_str() << "\n\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    std::cout << std::string(60, '-') << "\n";
    std::cout << "✓ All memory/conversation examples completed!\n\n";

    std::cout << "Key Features Demonstrated:\n";
    std::cout << "  • Context preservation across turns\n";
    std::cout << "  • Memory of previous interactions\n";
    std::cout << "  • Natural multi-turn dialogue\n";
    std::cout << "  • Progressive context building\n\n";

    std::cout << "Use Cases:\n";
    std::cout << "  • Personal assistants\n";
    std::cout << "  • Customer support chatbots\n";
    std::cout << "  • Technical advisors\n";
    std::cout << "  • Educational tutors\n";
    std::cout << "  • Interactive troubleshooting\n";
    std::cout << std::string(60, '-') << "\n";

    return 0;
}
