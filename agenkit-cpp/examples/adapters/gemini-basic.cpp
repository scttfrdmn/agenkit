/**
 * @file gemini-basic.cpp
 * @brief Basic Google Gemini usage example
 *
 * Demonstrates:
 * - Gemini adapter configuration
 * - Single-turn completion
 * - Multiple model comparison
 * - Error handling
 * - Metadata extraction
 *
 * Setup:
 *   export GEMINI_API_KEY=your-key
 *   # OR
 *   export GOOGLE_API_KEY=your-key
 *
 *   cmake -B build -S .
 *   cmake --build build
 *   ./build/examples/gemini-basic
 */

#include "agenkit/adapters/gemini_agent.hpp"
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
    print_separator("AgentKit C++ - Google Gemini Basic Example");

    // Check for API key
    const char* api_key = std::getenv("GEMINI_API_KEY");
    if (!api_key) {
        api_key = std::getenv("GOOGLE_API_KEY");
    }
    if (!api_key) {
        std::cerr << "❌ GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set\n";
        std::cerr << "Please set your API key: export GEMINI_API_KEY=your-key\n";
        return 1;
    }

    std::cout << "✓ Initialized Gemini adapter\n\n";

    // Example 1: Simple completion
    print_separator("Example 1: Simple Completion");

    try {
        GeminiConfig config;
        config.api_key = api_key;
        config.model = GeminiModels::GEMINI_2_0_FLASH_EXP;
        config.temperature = 0.7;
        config.max_tokens = 1024;

        GeminiAgent gemini(config);

        std::cout << "Model: " << config.model << "\n";
        std::cout << "User: Explain quantum computing in simple terms.\n\n";

        auto msg = Message::with_text("user", "Explain quantum computing in simple terms.");
        auto future = gemini.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "Gemini: " << response.content_as_str() << "\n\n";

            // Show metadata
            std::cout << "Metadata:\n";
            const auto& meta = response.metadata();
            if (meta.contains("model")) {
                std::cout << "  Model: " << meta["model"].get<std::string>() << "\n";
            }
            if (meta.contains("finish_reason")) {
                std::cout << "  Finish reason: " << meta["finish_reason"].get<std::string>() << "\n";
            }
            if (meta.contains("usage")) {
                const auto& usage = meta["usage"];
                if (usage.contains("total_tokens")) {
                    std::cout << "  Total tokens: " << usage["total_tokens"].get<int>() << "\n";
                }
            }
        } else {
            std::cerr << "Error: " << result.unwrap_err().message() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 2: Model comparison
    print_separator("Example 2: Model Comparison");

    try {
        std::string prompt = "Write a haiku about programming.";

        std::vector<std::string> models = {
            GeminiModels::GEMINI_2_0_FLASH_EXP,
            GeminiModels::GEMINI_1_5_FLASH,
            GeminiModels::GEMINI_1_5_PRO
        };

        for (const auto& model : models) {
            GeminiConfig config;
            config.api_key = api_key;
            config.model = model;
            config.max_tokens = 100;

            GeminiAgent gemini(config);

            std::cout << "Model: " << model << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = gemini.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response:\n" << result.unwrap().content_as_str() << "\n\n";
            } else {
                std::cout << "Error: " << result.unwrap_err().message() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 3: Temperature variation
    print_separator("Example 3: Temperature Effects");

    try {
        std::string prompt = "Generate a creative name for a coffee shop.";

        for (double temp : {0.2, 0.7, 1.5}) {
            GeminiConfig config;
            config.api_key = api_key;
            config.model = GeminiModels::GEMINI_2_0_FLASH_EXP;
            config.temperature = temp;
            config.max_tokens = 50;

            GeminiAgent gemini(config);

            std::cout << "Temperature: " << temp << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = gemini.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Gemini: " << result.unwrap().content_as_str() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 4: Using generation config parameters
    print_separator("Example 4: Advanced Configuration");

    try {
        GeminiConfig config;
        config.api_key = api_key;
        config.model = GeminiModels::GEMINI_1_5_PRO;
        config.temperature = 0.9;
        config.max_tokens = 150;
        config.top_p = 0.95;
        config.top_k = 40;
        config.stop_sequences = {"\n\n", "END"};

        GeminiAgent gemini(config);

        std::cout << "Configuration:\n";
        std::cout << "  Model: " << config.model << "\n";
        std::cout << "  Temperature: " << config.temperature.value() << "\n";
        std::cout << "  Max tokens: " << config.max_tokens.value() << "\n";
        std::cout << "  Top P: " << config.top_p.value() << "\n";
        std::cout << "  Top K: " << config.top_k.value() << "\n";
        std::cout << "  Stop sequences: ";
        for (const auto& seq : config.stop_sequences) {
            std::cout << "\"" << seq << "\" ";
        }
        std::cout << "\n\n";

        std::cout << "User: Tell me a short story about a robot.\n\n";

        auto msg = Message::with_text("user", "Tell me a short story about a robot.");
        auto future = gemini.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Gemini: " << result.unwrap().content_as_str() << "\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 5: System instruction (via user message)
    print_separator("Example 5: System Instructions");

    try {
        GeminiConfig config;
        config.api_key = api_key;
        config.model = GeminiModels::GEMINI_2_0_FLASH_EXP;
        config.max_tokens = 100;

        GeminiAgent gemini(config);

        std::cout << "Note: Gemini treats system messages as user messages\n\n";

        auto system_msg = Message::with_text(
            "system",
            "You are a helpful assistant that speaks like a pirate."
        );
        auto future = gemini.process(std::move(system_msg));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "System message processed\n\n";
        }

        auto user_msg = Message::with_text("user", "Tell me about the weather.");
        future = gemini.process(std::move(user_msg));
        result = future.get();

        if (result.is_ok()) {
            std::cout << "User: Tell me about the weather.\n\n";
            std::cout << "Gemini: " << result.unwrap().content_as_str() << "\n\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 6: Error handling
    print_separator("Example 6: Error Handling");

    try {
        // Test with invalid API key
        GeminiConfig config;
        config.api_key = "invalid-key";
        config.model = GeminiModels::GEMINI_2_0_FLASH_EXP;
        config.timeout_seconds = 5;

        GeminiAgent gemini(config);

        std::cout << "Testing with invalid API key...\n\n";

        auto msg = Message::with_text("user", "Hello");
        auto future = gemini.process(std::move(msg));
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
    std::cout << "  • Gemini adapter configuration\n";
    std::cout << "  • Single-turn completion\n";
    std::cout << "  • Model comparison (2.0 Flash, 1.5 Pro, 1.5 Flash)\n";
    std::cout << "  • Temperature effects on creativity\n";
    std::cout << "  • Advanced configuration (top_p, top_k, stop sequences)\n";
    std::cout << "  • System instructions\n";
    std::cout << "  • Error handling and metadata\n\n";

    std::cout << "Next Steps:\n";
    std::cout << "  • Try different models by changing config.model\n";
    std::cout << "  • Experiment with temperature, top_p, and top_k\n";
    std::cout << "  • Use stop sequences for structured output\n";
    std::cout << "  • See https://ai.google.dev/docs for more info\n\n";

    return 0;
}
