/**
 * @file openai_basic.cpp
 * @brief Basic OpenAI GPT usage example
 *
 * Demonstrates:
 * - OpenAI adapter configuration
 * - Single-turn completion
 * - Multi-turn conversation
 * - Error handling
 * - Metadata extraction
 *
 * Setup:
 *   export OPENAI_API_KEY=your-key
 *   cmake -B build -S .
 *   cmake --build build
 *   ./build/examples/openai_basic
 */

#include "agenkit/adapters/openai_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>

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
    print_separator("AgentKit C++ - OpenAI Basic Example");

    // Check for API key
    const char* api_key = std::getenv("OPENAI_API_KEY");
    if (!api_key) {
        std::cerr << "❌ OPENAI_API_KEY environment variable not set\n";
        std::cerr << "Please set your API key: export OPENAI_API_KEY=your-key\n";
        return 1;
    }

    std::cout << "✓ Initialized OpenAI adapter\n\n";

    // Example 1: Simple completion
    print_separator("Example 1: Simple Completion");

    try {
        OpenAIConfig config;
        config.api_key = api_key;
        config.model = OpenAIModels::GPT_4_TURBO;
        config.temperature = 0.7;
        config.max_tokens = 1024;

        OpenAIAgent gpt(config);

        std::cout << "Model: " << config.model << "\n";
        std::cout << "User: Explain the concept of recursion in programming.\n\n";

        auto msg = Message::with_text("user", "Explain the concept of recursion in programming.");
        auto future = gpt.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "GPT: " << response.content_as_str() << "\n\n";

            // Show metadata
            std::cout << "Metadata:\n";
            const auto& meta = response.metadata();
            if (meta.contains("model")) {
                std::cout << "  Model: " << meta["model"].get<std::string>() << "\n";
            }
            if (meta.contains("finish_reason")) {
                std::cout << "  Finish reason: " << meta["finish_reason"].get<std::string>() << "\n";
            }
        } else {
            std::cerr << "Error: " << result.unwrap_err().message() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 2: Different models comparison
    print_separator("Example 2: Model Comparison (GPT-4o vs GPT-3.5)");

    try {
        std::string prompt = "What is machine learning in one sentence?";

        // GPT-4o
        {
            OpenAIConfig config;
            config.api_key = api_key;
            config.model = OpenAIModels::GPT_4O;
            config.max_tokens = 100;

            OpenAIAgent gpt(config);

            std::cout << "GPT-4o:\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = gpt.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response: " << result.unwrap().content_as_str() << "\n\n";
            }
        }

        // GPT-3.5 Turbo
        {
            OpenAIConfig config;
            config.api_key = api_key;
            config.model = OpenAIModels::GPT_3_5_TURBO;
            config.max_tokens = 100;

            OpenAIAgent gpt(config);

            std::cout << "GPT-3.5 Turbo:\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = gpt.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response: " << result.unwrap().content_as_str() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 3: Temperature variation
    print_separator("Example 3: Temperature Effects");

    try {
        std::string prompt = "Write a creative opening sentence for a story.";

        for (double temp : {0.2, 0.7, 1.5}) {
            OpenAIConfig config;
            config.api_key = api_key;
            config.model = OpenAIModels::GPT_4O_MINI;
            config.temperature = temp;
            config.max_tokens = 50;

            OpenAIAgent gpt(config);

            std::cout << "Temperature: " << temp << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = gpt.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "GPT: " << result.unwrap().content_as_str() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 4: Error handling
    print_separator("Example 4: Error Handling");

    try {
        // Test with invalid API key
        OpenAIConfig config;
        config.api_key = "invalid-key";
        config.model = OpenAIModels::GPT_4O_MINI;
        config.timeout = std::chrono::milliseconds{5000};

        OpenAIAgent gpt(config);

        std::cout << "Testing with invalid API key...\n\n";

        auto msg = Message::with_text("user", "Hello");
        auto future = gpt.process(std::move(msg));
        auto result = future.get();

        if (result.is_err()) {
            std::cout << "✓ Error caught as expected:\n";
            std::cout << "  Type: " << static_cast<int>(result.unwrap_err().type()) << "\n";
            std::cout << "  Message: " << result.unwrap_err().message() << "\n";
        } else {
            std::cout << "⚠️  Unexpected success with invalid key\n";
        }
    } catch (const std::exception& e) {
        std::cout << "✓ Exception caught: " << e.what() << "\n";
    }

    print_separator("✓ All examples completed!");

    std::cout << "Key Features Demonstrated:\n";
    std::cout << "  • OpenAI adapter configuration\n";
    std::cout << "  • Single-turn completion\n";
    std::cout << "  • Model comparison (GPT-4, GPT-3.5)\n";
    std::cout << "  • Temperature effects on creativity\n";
    std::cout << "  • Error handling and metadata\n\n";

    return 0;
}
