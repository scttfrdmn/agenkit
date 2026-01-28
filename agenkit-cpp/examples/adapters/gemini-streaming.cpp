/**
 * @file gemini-streaming.cpp
 * @brief Example demonstrating Google Gemini streaming support
 *
 * This example shows how to stream responses from Gemini in real-time,
 * displaying text as it arrives from the API.
 *
 * Build:
 *   mkdir -p build && cd build
 *   cmake .. && make gemini-streaming
 *
 * Run:
 *   export GEMINI_API_KEY="your-key-here"
 *   ./gemini-streaming
 */

#include "agenkit/adapters/gemini_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::core;

int main() {
    // Load API key from environment
    const char* api_key_env = std::getenv("GEMINI_API_KEY");
    if (!api_key_env) {
        std::cerr << "Error: GEMINI_API_KEY environment variable not set\n";
        return 1;
    }

    // Configure Gemini
    GeminiConfig config;
    config.api_key = api_key_env;
    config.model = "gemini-2.0-flash-exp";
    config.temperature = 1.0;
    config.max_tokens = 1024;

    GeminiAgent gemini(config);

    std::cout << "=== Google Gemini Streaming Example ===\n\n";
    std::cout << "Asking Gemini to count to 10...\n\n";
    std::cout << "Response (streaming):\n";
    std::cout << std::string(60, '-') << "\n";

    // Create message
    auto message = Message::with_text("user", "Count to 10, one number per line.");

    // Stream response
    std::string full_response;
    auto result = gemini.stream(std::move(message), [&](const std::string& chunk) {
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
    std::cout << "Asking Gemini to write a short story...\n\n";
    std::cout << "Response (streaming):\n";
    std::cout << std::string(60, '-') << "\n";

    auto message2 = Message::with_text(
        "user",
        "Write a very short story (3 sentences) about a robot learning to paint."
    );

    full_response.clear();
    result = gemini.stream(std::move(message2), [&](const std::string& chunk) {
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
    result = gemini.stream(std::move(message3), [&](const std::string& chunk) {
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
