/**
 * @file bedrock-streaming.cpp
 * @brief Example demonstrating Amazon Bedrock streaming support
 *
 * This example shows how to stream responses from Bedrock foundation models
 * in real-time, displaying text as it arrives from the API.
 *
 * Build:
 *   mkdir -p build && cd build
 *   cmake -DAGENKIT_BUILD_BEDROCK=ON .. && make bedrock-streaming
 *
 * Run:
 *   export AWS_REGION="us-east-1"
 *   export AWS_ACCESS_KEY_ID="your-key-id"
 *   export AWS_SECRET_ACCESS_KEY="your-secret-key"
 *   ./bedrock-streaming
 */

#include "agenkit/adapters/bedrock_agent.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <cstdlib>

using namespace agenkit;
using namespace agenkit::adapters;
using namespace agenkit::core;

int main() {
    // Configure Bedrock (uses AWS credential chain by default)
    BedrockConfig config;

    // Get region from environment or use default
    const char* region_env = std::getenv("AWS_REGION");
    if (region_env) {
        config.region = region_env;
    }

    config.model = "anthropic.claude-3-5-sonnet-20241022-v2:0";
    config.temperature = 1.0;
    config.max_tokens = 1024;

    try {
        BedrockAgent bedrock(config);

        std::cout << "=== Amazon Bedrock Streaming Example ===\n\n";
        std::cout << "Using Claude 3.5 Sonnet on Bedrock...\n\n";
        std::cout << "Response (streaming):\n";
        std::cout << std::string(60, '-') << "\n";

        // Create message
        auto message = Message::with_text("user", "Count to 10, one number per line.");

        // Stream response
        std::string full_response;
        auto result = bedrock.stream(std::move(message), [&](const std::string& chunk) {
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
        std::cout << "Asking Claude to write a short story...\n\n";
        std::cout << "Response (streaming):\n";
        std::cout << std::string(60, '-') << "\n";

        auto message2 = Message::with_text(
            "user",
            "Write a very short story (3 sentences) about a robot learning to paint."
        );

        full_response.clear();
        result = bedrock.stream(std::move(message2), [&](const std::string& chunk) {
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
        result = bedrock.stream(std::move(message3), [&](const std::string& chunk) {
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

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        std::cerr << "\nNote: This example requires the AWS SDK for C++.\n";
        std::cerr << "Build with: cmake -DAGENKIT_BUILD_BEDROCK=ON ..\n";
        return 1;
    }

    return 0;
}
