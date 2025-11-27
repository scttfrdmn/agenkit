/**
 * @file claude_reflection.cpp
 * @brief Example: Using Claude with Reflection pattern for self-improvement
 *
 * This example demonstrates:
 * - Anthropic Claude API integration
 * - Reflection pattern for iterative refinement
 * - Real-world LLM usage with agenkit
 *
 * The Reflection pattern has an agent generate a response, then a "reflector"
 * agent critiques it. The process repeats until the reflector approves or
 * max iterations is reached.
 *
 * Usage:
 *   export ANTHROPIC_API_KEY=your-key-here
 *   ./claude_reflection
 */

#include <iostream>
#include <memory>
#include <cstdlib>
#include "agenkit/adapters/claude_agent.hpp"
#include "agenkit/patterns/reflection.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

int main() {
    std::cout << "\n";
    std::cout << "╔════════════════════════════════════════════════════════════╗\n";
    std::cout << "║  AgentKit C++ - Claude Reflection Pattern Example         ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════╝\n\n";

    // Get API key from environment
    const char* api_key_env = std::getenv("ANTHROPIC_API_KEY");
    if (!api_key_env) {
        std::cerr << "Error: ANTHROPIC_API_KEY environment variable not set\n";
        std::cerr << "Please set it with: export ANTHROPIC_API_KEY=your-key-here\n";
        return 1;
    }

    std::string api_key(api_key_env);

    // Configure primary agent (Claude Sonnet 4)
    adapters::ClaudeConfig agent_config;
    agent_config.api_key = api_key;
    agent_config.model = adapters::ClaudeModels::SONNET_4;
    agent_config.max_tokens = 500;
    agent_config.temperature = 1.0;

    // Configure reflector agent (Claude 3.5 Haiku - faster for critique)
    adapters::ClaudeConfig reflector_config;
    reflector_config.api_key = api_key;
    reflector_config.model = adapters::ClaudeModels::HAIKU_3_5;
    reflector_config.max_tokens = 300;
    reflector_config.temperature = 0.7;

    try {
        // Create agents
        auto agent = std::make_shared<adapters::ClaudeAgent>(agent_config);
        auto reflector = std::make_shared<adapters::ClaudeAgent>(reflector_config);

        // Create reflection agent (max 3 iterations)
        patterns::ReflectionAgent reflection(agent, reflector, 3);

        std::cout << "Configuration:\n";
        std::cout << "  Primary Model:   " << agent_config.model << "\n";
        std::cout << "  Reflector Model: " << reflector_config.model << "\n";
        std::cout << "  Max Iterations:  3\n\n";

        // Example task: Write a haiku about AI
        std::string task = "Write a haiku about artificial intelligence. "
                          "Make it thoughtful and poetic.";

        std::cout << "Task:\n";
        std::cout << "  " << task << "\n\n";

        std::cout << "Processing with reflection...\n";
        std::cout << std::string(60, '-') << "\n\n";

        // Create message and process
        auto msg = core::Message::with_text("user", task);
        auto future = reflection.process(std::move(msg));
        auto result = future.get();

        if (result.is_err()) {
            auto error = result.unwrap_err();
            std::cerr << "Error: " << error.message() << "\n";
            return 1;
        }

        // Get final result
        auto response = result.unwrap();

        // Show reflection history
        const auto& history = reflection.get_reflection_history();
        std::cout << "Reflection Process:\n\n";

        for (size_t i = 0; i < history.size(); ++i) {
            const auto& step = history[i];
            std::cout << "Iteration " << step.iteration << ":\n";
            std::cout << "  Response:\n    " << step.response.content_as_str() << "\n";
            std::cout << "  Feedback:\n    " << step.feedback.content_as_str() << "\n";
            std::cout << "  Approved: " << (step.should_continue ? "No" : "Yes") << "\n\n";
        }

        std::cout << std::string(60, '=') << "\n\n";
        std::cout << "Final Result:\n";
        std::cout << response.content_as_str() << "\n\n";

        // Show metadata
        if (response.metadata().contains("reflection_iterations")) {
            std::cout << "Iterations: " << response.metadata()["reflection_iterations"] << "\n";
        }

        if (response.metadata().contains("usage")) {
            const auto& usage = response.metadata()["usage"];
            if (usage.contains("input_tokens") && usage.contains("output_tokens")) {
                int input = usage["input_tokens"].get<int>();
                int output = usage["output_tokens"].get<int>();
                std::cout << "Token Usage: " << input << " in, " << output << " out, "
                         << (input + output) << " total\n";
            }
        }

        std::cout << "\n✓ Reflection complete!\n\n";

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
