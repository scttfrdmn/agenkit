/**
 * @file ollama_example.cpp
 * @brief Example: Using Ollama for local LLM inference
 *
 * This example demonstrates:
 * - Ollama adapter for local LLMs (free, fast, private)
 * - Multiple model options (Llama, Mistral, Qwen)
 * - Server availability checking
 * - Token usage tracking
 *
 * Setup:
 *   brew install ollama        # Install Ollama
 *   ollama serve               # Start server (in separate terminal)
 *   ollama pull llama3.3       # Pull a model
 *   ./ollama_example           # Run this example
 */

#include <iostream>
#include <memory>
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

int main() {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  AgentKit C++ - Ollama Local LLM Example\n";
    std::cout << "================================================================\n\n";

    // Configure Ollama
    adapters::OllamaConfig config;
    config.host = "http://localhost:11434";
    config.model = "llama3.3";  // or "mistral:7b", "qwen2.5:7b", etc.
    config.temperature = 0.7;

    try {
        // Create Ollama agent
        adapters::OllamaAgent ollama(config);

        std::cout << "Configuration:\n";
        std::cout << "  Host:  " << config.host << "\n";
        std::cout << "  Model: " << config.model << "\n";
        std::cout << "  Temp:  " << config.temperature << "\n\n";

        // Check if Ollama is available
        std::cout << "Checking Ollama server...\n";
        if (!ollama.is_available()) {
            std::cerr << "❌ Ollama server not available at " << config.host << "\n";
            std::cerr << "\nPlease start Ollama:\n";
            std::cerr << "  1. Install: brew install ollama\n";
            std::cerr << "  2. Start:   ollama serve\n";
            std::cerr << "  3. Pull:    ollama pull " << config.model << "\n\n";
            return 1;
        }

        std::cout << "✓ Ollama server is running\n\n";

        // List available models
        std::cout << "Available models:\n";
        auto models = ollama.list_models();
        if (models.empty()) {
            std::cout << "  (none - run 'ollama pull <model>' to download one)\n";
        } else {
            for (const auto& model : models) {
                std::cout << "  • " << model << "\n";
            }
        }
        std::cout << "\n";

        // Example 1: Simple question
        std::cout << "Example 1: Simple Question\n";
        std::cout << std::string(60, '-') << "\n";

        std::string question = "What is AgentKit? Answer in one sentence.";
        std::cout << "Q: " << question << "\n\n";

        auto msg1 = core::Message::with_text("user", question);
        auto future1 = ollama.process(std::move(msg1));
        auto result1 = future1.get();

        if (result1.is_err()) {
            std::cerr << "Error: " << result1.unwrap_err().message() << "\n";
            return 1;
        }

        auto response1 = result1.unwrap();
        std::cout << "A: " << response1.content_as_str() << "\n\n";

        // Show metadata
        if (response1.metadata().contains("prompt_tokens")) {
            int prompt_tokens = response1.metadata()["prompt_tokens"].get<int>();
            int completion_tokens = response1.metadata()["completion_tokens"].get<int>();
            std::cout << "Tokens: " << prompt_tokens << " prompt, "
                     << completion_tokens << " completion\n";
        }

        std::cout << "\n";

        // Example 2: Code generation
        std::cout << "Example 2: Code Generation\n";
        std::cout << std::string(60, '-') << "\n";

        std::string code_request = "Write a C++ function to calculate fibonacci numbers. Just the code, no explanation.";
        std::cout << "Q: " << code_request << "\n\n";

        auto msg2 = core::Message::with_text("user", code_request);
        auto future2 = ollama.process(std::move(msg2));
        auto result2 = future2.get();

        if (result2.is_ok()) {
            auto response2 = result2.unwrap();
            std::cout << response2.content_as_str() << "\n\n";
        }

        std::cout << "================================================================\n";
        std::cout << "\n✓ Ollama examples complete!\n";
        std::cout << "\nTry other models:\n";
        std::cout << "  • llama3.2:3b  - Smaller, faster\n";
        std::cout << "  • mistral:7b   - Fast and capable\n";
        std::cout << "  • qwen2.5:7b   - Good at code\n";
        std::cout << "  • phi3:mini    - Microsoft's 3.8B\n\n";

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
