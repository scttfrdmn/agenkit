/**
 * @file litellm-basic.cpp
 * @brief Basic LiteLLM proxy usage example
 *
 * Demonstrates:
 * - LiteLLM adapter configuration
 * - Universal gateway access to multiple providers
 * - Single-turn completion
 * - Error handling
 * - Metadata extraction
 *
 * Setup:
 *   # Start LiteLLM proxy
 *   litellm --port 4000
 *
 *   # Or with specific providers
 *   export OPENAI_API_KEY=your-key
 *   litellm --model gpt-3.5-turbo --port 4000
 *
 *   # Build and run
 *   cmake -B build -S .
 *   cmake --build build
 *   ./build/examples/litellm-basic
 */

#include "agenkit/adapters/litellm_agent.hpp"
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
    print_separator("AgentKit C++ - LiteLLM Basic Example");

    std::cout << "LiteLLM is a universal LLM gateway supporting 100+ providers:\n";
    std::cout << "  • OpenAI (gpt-4, gpt-3.5-turbo)\n";
    std::cout << "  • Anthropic (claude-3-5-sonnet-20241022)\n";
    std::cout << "  • AWS Bedrock (bedrock/anthropic.claude-v2)\n";
    std::cout << "  • Google Gemini (gemini/gemini-pro)\n";
    std::cout << "  • Azure OpenAI (azure/gpt-4)\n";
    std::cout << "  • Cohere (command-r-plus)\n";
    std::cout << "  • Local models (ollama/llama2, ollama/mistral)\n";
    std::cout << "  • And 100+ more!\n\n";

    std::cout << "✓ Initialized LiteLLM adapter\n\n";

    // Example 1: Simple completion
    print_separator("Example 1: Simple Completion");

    try {
        LiteLLMConfig config;
        config.base_url = "http://localhost:4000";
        config.model = "gpt-3.5-turbo";
        config.temperature = 0.7;
        config.max_tokens = 1024;

        // Check for optional API key
        const char* api_key = std::getenv("LITELLM_API_KEY");
        if (api_key) {
            config.api_key = api_key;
            std::cout << "✓ Using API key from LITELLM_API_KEY\n";
        }

        LiteLLMAgent agent(config);

        std::cout << "Model: " << config.model << "\n";
        std::cout << "Base URL: " << config.base_url << "\n";
        std::cout << "User: Explain what LiteLLM is in two sentences.\n\n";

        auto msg = Message::with_text("user", "Explain what LiteLLM is in two sentences.");
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            const auto& response = result.unwrap();
            std::cout << "Assistant: " << response.content_as_str() << "\n\n";

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

    // Example 2: Multiple provider routing
    print_separator("Example 2: Multiple Provider Routing");

    try {
        std::string prompt = "What is the meaning of life?";

        // Each model can be routed to different providers by LiteLLM
        std::vector<std::string> models = {
            "gpt-3.5-turbo",           // OpenAI
            "claude-3-haiku-20240307", // Anthropic
            "gemini/gemini-pro"        // Google Gemini
        };

        for (const auto& model : models) {
            LiteLLMConfig config;
            config.base_url = "http://localhost:4000";
            config.model = model;
            config.max_tokens = 100;

            LiteLLMAgent agent(config);

            std::cout << "Model: " << model << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = agent.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response: " << result.unwrap().content_as_str() << "\n\n";
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
        std::string prompt = "Write a haiku about programming.";

        for (double temp : {0.3, 0.7, 1.2}) {
            LiteLLMConfig config;
            config.base_url = "http://localhost:4000";
            config.model = "gpt-3.5-turbo";
            config.temperature = temp;
            config.max_tokens = 50;

            LiteLLMAgent agent(config);

            std::cout << "Temperature: " << temp << "\n";
            std::cout << "User: " << prompt << "\n\n";

            auto msg = Message::with_text("user", prompt);
            auto future = agent.process(std::move(msg));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response:\n" << result.unwrap().content_as_str() << "\n\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 4: Using model constants
    print_separator("Example 4: Model Constants");

    try {
        std::cout << "Available model constants:\n\n";

        LiteLLMConfig config;
        config.base_url = "http://localhost:4000";
        config.model = LiteLLMModels::GPT_4O_MINI;
        config.max_tokens = 50;

        LiteLLMAgent agent(config);

        std::cout << "Using: " << LiteLLMModels::GPT_4O_MINI << "\n";
        std::cout << "User: Hello, how are you?\n\n";

        auto msg = Message::with_text("user", "Hello, how are you?");
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Response: " << result.unwrap().content_as_str() << "\n\n";
        }

        std::cout << "Other available constants:\n";
        std::cout << "  OpenAI: " << LiteLLMModels::GPT_4 << ", "
                  << LiteLLMModels::GPT_4_TURBO << "\n";
        std::cout << "  Anthropic: " << LiteLLMModels::CLAUDE_3_5_SONNET << "\n";
        std::cout << "  Bedrock: " << LiteLLMModels::BEDROCK_CLAUDE_V2 << "\n";
        std::cout << "  Gemini: " << LiteLLMModels::GEMINI_PRO << "\n";
        std::cout << "  Ollama: " << LiteLLMModels::OLLAMA_LLAMA2 << "\n";
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    // Example 5: Error handling
    print_separator("Example 5: Error Handling");

    try {
        // Test with unreachable server
        LiteLLMConfig config;
        config.base_url = "http://localhost:9999";  // Wrong port
        config.model = "gpt-3.5-turbo";
        config.timeout = std::chrono::milliseconds{2000};

        LiteLLMAgent agent(config);

        std::cout << "Testing with unreachable server (localhost:9999)...\n\n";

        auto msg = Message::with_text("user", "Hello");
        auto future = agent.process(std::move(msg));
        auto result = future.get();

        if (result.is_err()) {
            std::cout << "✓ Error caught as expected:\n";
            std::cout << "  Type: " << static_cast<int>(result.unwrap_err().type()) << "\n";
            std::cout << "  Message: " << result.unwrap_err().message() << "\n";
        } else {
            std::cout << "⚠️  Unexpected success with unreachable server\n";
        }
    } catch (const std::exception& e) {
        std::cout << "✓ Exception caught: " << e.what() << "\n";
    }

    print_separator("✓ All examples completed!");

    std::cout << "Key Features Demonstrated:\n";
    std::cout << "  • LiteLLM adapter configuration\n";
    std::cout << "  • Universal gateway for multiple providers\n";
    std::cout << "  • Single-turn completion\n";
    std::cout << "  • Temperature effects\n";
    std::cout << "  • Model constants\n";
    std::cout << "  • Error handling and metadata\n\n";

    std::cout << "Next Steps:\n";
    std::cout << "  • Try different models by changing config.model\n";
    std::cout << "  • Experiment with temperature and max_tokens\n";
    std::cout << "  • Use LiteLLM to route to AWS Bedrock, Azure, etc.\n";
    std::cout << "  • See https://docs.litellm.ai/ for more info\n\n";

    return 0;
}
