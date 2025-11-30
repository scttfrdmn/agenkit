/**
 * @file anthropic-basic.cpp
 * @brief Basic Anthropic Claude usage example
 *
 * Demonstrates:
 * - Claude adapter configuration
 * - Single-turn completion
 * - Multi-turn conversation
 * - Error handling
 * - Metadata extraction
 * - Model comparison (Opus vs Sonnet vs Haiku)
 *
 * Setup:
 *   export ANTHROPIC_API_KEY=your-key
 *   cmake -B build -S .
 *   cmake --build build
 *   ./build/examples/anthropic-basic
 */

#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>
#include <vector>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::core;

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
    print_separator("AgentKit C++ - Anthropic Claude Basic Example");

    // Check for API key
    const char* api_key = std::getenv("ANTHROPIC_API_KEY");
    if (!api_key) {
        std::cerr << "❌ ANTHROPIC_API_KEY environment variable not set\n";
        std::cerr << "Please set your API key: export ANTHROPIC_API_KEY=your-key\n";
        std::cerr << "Get your key at: https://console.anthropic.com/\n";
        return 1;
    }

    std::cout << "✓ Initialized Claude adapter\n\n";

    // Example 1: Simple completion
    print_separator("Example 1: Simple Completion");

    try {
        ClaudeConfig config;
        config.api_key = api_key;
        config.model = "claude-3-5-sonnet-20241022";
        config.temperature = 0.7;
        config.max_tokens = 1024;

        ClaudeAgent claude(config);

        std::cout << "Model: " << config.model << "\n";
        std::cout << "User: Explain the concept of recursion in programming.\n\n";

        auto msg = Message::with_text("user", "Explain the concept of recursion in programming.");
        auto future = claude.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "Claude: " << response.content_as_str() << "\n\n";

            // Show metadata
            std::cout << "Metadata:\n";
            const auto& meta = response.metadata();
            if (meta.contains("model")) {
                std::cout << "  Model: " << meta["model"].get<std::string>() << "\n";
            }
            if (meta.contains("stop_reason")) {
                std::cout << "  Stop reason: " << meta["stop_reason"].get<std::string>() << "\n";
            }
            if (meta.contains("usage")) {
                const auto& usage = meta["usage"];
                if (usage.contains("input_tokens")) {
                    std::cout << "  Input tokens: " << usage["input_tokens"].get<int>() << "\n";
                }
                if (usage.contains("output_tokens")) {
                    std::cout << "  Output tokens: " << usage["output_tokens"].get<int>() << "\n";
                }
            }
        } else {
            std::cerr << "Error: " << result.unwrap_err().message() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 2: Model comparison (Opus vs Sonnet vs Haiku)
    print_separator("Example 2: Model Comparison (Opus vs Sonnet vs Haiku)");

    try {
        std::string prompt = "What is machine learning in one sentence?";
        std::cout << "Prompt: " << prompt << "\n\n";

        struct ModelTest {
            std::string name;
            std::string model_id;
            std::string description;
        };

        std::vector<ModelTest> models = {
            {"Opus", "claude-3-opus-20240229", "Most capable, best for complex tasks"},
            {"Sonnet", "claude-3-5-sonnet-20241022", "Balanced performance and speed"},
            {"Haiku", "claude-3-haiku-20240307", "Fastest, best for simple tasks"}
        };

        for (const auto& model : models) {
            std::cout << "Model: " << model.name << "\n";
            std::cout << "  " << model.description << "\n";

            ClaudeConfig config;
            config.api_key = api_key;
            config.model = model.model_id;
            config.max_tokens = 100;

            ClaudeAgent claude(config);

            auto msg = Message::with_text("user", prompt);
            auto future = claude.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                const auto& response = result.unwrap();
                std::cout << "  Response: " << response.content_as_str() << "\n\n";
            } else {
                std::cerr << "  Error: " << result.unwrap_err().message() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 3: Multi-turn conversation
    print_separator("Example 3: Multi-turn Conversation");

    try {
        ClaudeConfig config;
        config.api_key = api_key;
        config.model = "claude-3-5-sonnet-20241022";
        config.max_tokens = 1024;

        ClaudeAgent claude(config);

        // First turn
        std::cout << "Turn 1:\n";
        std::cout << "User: What is an agent pattern in software?\n\n";

        auto msg1 = Message::with_text("user", "What is an agent pattern in software?");
        auto future1 = claude.process(std::move(msg1));
        auto result1 = future1.get();

        if (result1.is_ok()) {
            const auto& response1 = result1.unwrap();
            std::cout << "Claude: " << response1.content_as_str() << "\n\n";

            // Second turn (in production, maintain conversation history)
            std::cout << "Turn 2:\n";
            std::cout << "User: Can you give me a code example?\n\n";

            auto msg2 = Message::with_text("user", "Can you give me a code example of an agent pattern?");
            auto future2 = claude.process(std::move(msg2));
            auto result2 = future2.get();

            if (result2.is_ok()) {
                const auto& response2 = result2.unwrap();
                std::cout << "Claude: " << response2.content_as_str() << "\n\n";

                std::cout << "✓ Multi-turn conversation completed\n";
                std::cout << "Note: This example sends independent requests.\n";
                std::cout << "      For true conversation history, maintain message array.\n";
            } else {
                std::cerr << "Error on turn 2: " << result2.unwrap_err().message() << "\n";
            }
        } else {
            std::cerr << "Error on turn 1: " << result1.unwrap_err().message() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 4: Temperature comparison
    print_separator("Example 4: Temperature Comparison");

    try {
        std::string prompt = "Write a creative tagline for an AI agent framework.";
        std::cout << "Prompt: " << prompt << "\n\n";

        std::vector<double> temperatures = {0.0, 0.5, 1.0};

        for (double temp : temperatures) {
            std::cout << "Temperature: " << temp << "\n";
            std::cout << "  (";
            if (temp == 0.0) {
                std::cout << "deterministic, focused";
            } else if (temp == 0.5) {
                std::cout << "balanced";
            } else {
                std::cout << "creative, varied";
            }
            std::cout << ")\n";

            ClaudeConfig config;
            config.api_key = api_key;
            config.model = "claude-3-5-sonnet-20241022";
            config.temperature = temp;
            config.max_tokens = 50;

            ClaudeAgent claude(config);

            auto msg = Message::with_text("user", prompt);
            auto future = claude.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                const auto& response = result.unwrap();
                std::cout << "  Response: " << response.content_as_str() << "\n\n";
            } else {
                std::cerr << "  Error: " << result.unwrap_err().message() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 5: Error handling
    print_separator("Example 5: Error Handling");

    try {
        std::cout << "Testing with invalid API key...\n";

        ClaudeConfig config;
        config.api_key = "invalid-key-12345";
        config.model = "claude-3-5-sonnet-20241022";
        config.max_tokens = 100;

        ClaudeAgent claude(config);

        auto msg = Message::with_text("user", "Test message");
        auto future = claude.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Unexpected success!\n";
        } else {
            std::cout << "✓ Error handled correctly:\n";
            std::cout << "  " << result.unwrap_err().message() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception caught: " << e.what() << "\n";
    }

    // Summary
    print_separator("✅ ALL EXAMPLES COMPLETED");

    std::cout << "💡 Key Advantages of Claude:\n\n";
    std::cout << "  • Strong reasoning and analysis\n";
    std::cout << "  • Long context window (200K tokens)\n";
    std::cout << "  • Three models for different use cases:\n";
    std::cout << "    - Opus: Most capable, complex tasks\n";
    std::cout << "    - Sonnet: Balanced, most tasks\n";
    std::cout << "    - Haiku: Fast, simple tasks\n";
    std::cout << "  • Constitutional AI for safety\n\n";

    std::cout << "Available Models:\n\n";
    std::cout << "  • claude-3-opus-20240229\n";
    std::cout << "  • claude-3-5-sonnet-20241022 (recommended)\n";
    std::cout << "  • claude-3-haiku-20240307\n";
    std::cout << "  • claude-sonnet-4-20250514 (latest)\n\n";

    std::cout << "Documentation:\n";
    std::cout << "  https://docs.anthropic.com/claude/reference/messages_post\n\n";

    return 0;
}
