/**
 * @file ollama-streaming.cpp
 * @brief Example demonstrating Ollama streaming support
 *
 * This example shows how to stream responses from local Ollama models in real-time,
 * displaying text as it arrives from the API.
 *
 * Prerequisites:
 *   - Install Ollama: https://ollama.ai
 *   - Pull a model: ollama pull llama3.3
 *   - Start Ollama server (usually runs automatically)
 *
 * Build:
 *   mkdir -p build && cd build
 *   cmake .. && make ollama-streaming
 *
 * Run:
 *   ./ollama-streaming
 */

#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::core;

int main() {
    // Configure Ollama
    OllamaConfig config;
    config.host = "http://localhost:11434";
    config.model = "llama3.3";
    config.temperature = 0.7;

    OllamaAgent ollama(config);

    // Check if Ollama is available
    if (!ollama.is_available()) {
        std::cerr << "Error: Ollama server not available at " << config.host << "\n";
        std::cerr << "Please start Ollama: ollama serve\n";
        return 1;
    }

    std::cout << "=== Ollama Streaming Example ===\n\n";
    std::cout << "Using model: " << config.model << "\n\n";
    std::cout << "Asking Ollama to count to 10...\n\n";
    std::cout << "Response (streaming):\n";
    std::cout << std::string(60, '-') << "\n";

    // Create message
    auto message = Message::with_text("user", "Count to 10, one number per line.");

    // Stream response
    std::string full_response;
    auto result = ollama.stream(std::move(message), [&](const std::string& chunk) {
        std::cout << chunk << std::flush;
        full_response += chunk;
        return true;  // Continue streaming
    });

    if (result.is_err()) {
        std::cerr << "\nError: " << result.unwrap_err().message() << "\n";
        return 1;
    }

    std::cout << "\n" << std::string(60, '-') << "\n";
    std::cout << "\nFull response length: " << full_response.length() << " characters\n";

    // Example 2: Story generation
    std::cout << "\n\n=== Story Generation Example ===\n\n";
    std::cout << "Asking Ollama to write a short story...\n\n";
    std::cout << "Response (streaming):\n";
    std::cout << std::string(60, '-') << "\n";

    auto message2 = Message::with_text(
        "user",
        "Write a very short story (3 sentences) about a robot learning to paint."
    );

    full_response.clear();
    result = ollama.stream(std::move(message2), [&](const std::string& chunk) {
        std::cout << chunk << std::flush;
        full_response += chunk;
        return true;  // Continue streaming
    });

    if (result.is_err()) {
        std::cerr << "\nError: " << result.unwrap_err().message() << "\n";
        return 1;
    }

    std::cout << "\n" << std::string(60, '-') << "\n";
    std::cout << "\nStreaming complete!\n";
    std::cout << "Total characters received: " << full_response.length() << "\n";

    // Example 3: Early termination
    std::cout << "\n\n=== Early Termination Example ===\n\n";
    std::cout << "Streaming with early stop after 50 characters...\n\n";
    std::cout << "Response (streaming):\n";
    std::cout << std::string(60, '-') << "\n";

    auto message3 = Message::with_text(
        "user",
        "Write a long essay about the history of computing."
    );

    full_response.clear();
    result = ollama.stream(std::move(message3), [&](const std::string& chunk) {
        std::cout << chunk << std::flush;
        full_response += chunk;

        // Stop after 50 characters
        if (full_response.length() >= 50) {
            std::cout << "\n[STOPPED EARLY]";
            return false;  // Stop streaming
        }
        return true;  // Continue streaming
    });

    std::cout << "\n" << std::string(60, '-') << "\n";
    std::cout << "\nStopped after " << full_response.length() << " characters\n";

    std::cout << "\nAll examples complete!\n";

    return 0;
}
