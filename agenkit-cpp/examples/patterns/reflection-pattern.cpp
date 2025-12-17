/**
 * @file reflection-pattern.cpp
 * @brief Reflection pattern with real LLMs (Ollama)
 *
 * Demonstrates:
 * - Iterative self-critique with real LLMs
 * - Writer and critic roles using system prompts
 * - Quality improvement through reflection loops
 * - Convergence detection
 *
 * Setup:
 *   brew install ollama
 *   ollama serve
 *   ollama pull llama3.3
 *   ./build/examples/patterns/reflection-pattern
 */

#include <iostream>
#include <memory>
#include "agenkit/patterns/reflection.hpp"
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

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
    print_separator("AgentKit C++ - Reflection Pattern with Real LLMs");

    // Check Ollama availability
    std::cout << "Checking Ollama server...\n";
    adapters::OllamaConfig check_config;
    check_config.host = "http://localhost:11434";
    check_config.model = "llama3.3";

    adapters::OllamaAgent checker(check_config);
    if (!checker.is_available()) {
        std::cerr << "❌ Ollama server not available\n\n";
        std::cerr << "Please start Ollama:\n";
        std::cerr << "  1. Install: brew install ollama\n";
        std::cerr << "  2. Start:   ollama serve\n";
        std::cerr << "  3. Pull:    ollama pull llama3.3\n\n";
        return 1;
    }
    std::cout << "✓ Ollama server running\n";

    // Example 1: Technical Writing Improvement
    print_separator("Example 1: Technical Writing Improvement");
    {
        std::cout << "Creating writer and critic agents...\n\n";

        // Writer agent: generates content
        adapters::OllamaConfig writer_config;
        writer_config.host = "http://localhost:11434";
        writer_config.model = "llama3.3";
        writer_config.temperature = 0.7;
        writer_config.system = "You are a technical writer. When given a topic, write "
                                "a clear explanation. If you receive critique, improve "
                                "your response by addressing the specific feedback points. "
                                "Be concise but thorough.";

        auto writer = std::make_shared<adapters::OllamaAgent>(writer_config);

        // Critic agent: provides feedback
        adapters::OllamaConfig critic_config;
        critic_config.host = "http://localhost:11434";
        critic_config.model = "llama3.3";
        critic_config.temperature = 0.5;
        critic_config.system = "You are a technical editor. Review responses and provide "
                                "constructive criticism. If the response is comprehensive, "
                                "accurate, and well-structured, start with 'APPROVED'. "
                                "Otherwise, give specific suggestions for improvement in "
                                "2-3 bullet points.";

        auto critic = std::make_shared<adapters::OllamaAgent>(critic_config);

        // Create reflection agent
        patterns::ReflectionAgent agent(writer, critic, 3);

        std::string topic = "Explain how database indexing improves query performance";
        std::cout << "Topic: " << topic << "\n\n";
        std::cout << "[Starting reflection loop...]\n\n";

        auto msg = core::Message::with_text("user", topic);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Final Response (After Reflection) ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";

            auto history = agent.get_reflection_history();
            std::cout << "Reflection cycles: " << history.size() << "\n";
            std::cout << "✓ Quality improved through iterative critique\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
        }
    }

    // Example 2: Code Review
    print_separator("Example 2: Code Review and Improvement");
    {
        // Writer: generates code
        adapters::OllamaConfig writer_config;
        writer_config.host = "http://localhost:11434";
        writer_config.model = "llama3.3";
        writer_config.temperature = 0.6;
        writer_config.system = "You are a C++ programmer. Write clean, efficient code. "
                                "If you receive code review feedback, rewrite the code "
                                "addressing all points. Keep code concise.";

        auto writer = std::make_shared<adapters::OllamaAgent>(writer_config);

        // Critic: reviews code
        adapters::OllamaConfig critic_config;
        critic_config.host = "http://localhost:11434";
        critic_config.model = "llama3.3";
        critic_config.temperature = 0.3;
        critic_config.system = "You are a senior C++ code reviewer. Review code for:\n"
                                "1. Correctness and edge cases\n"
                                "2. Modern C++ best practices\n"
                                "3. Error handling\n"
                                "4. Memory safety\n"
                                "Start with 'APPROVED' if code meets all standards, "
                                "otherwise list specific issues to fix.";

        auto critic = std::make_shared<adapters::OllamaAgent>(critic_config);

        patterns::ReflectionAgent agent(writer, critic, 2);

        std::string task = "Write a C++ function to reverse a string in-place";
        std::cout << "Task: " << task << "\n\n";
        std::cout << "[Code generation with review...]\n\n";

        auto msg = core::Message::with_text("user", task);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Final Code (After Review) ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n";
        }
    }

    // Example 3: Essay Refinement
    print_separator("Example 3: Essay Refinement");
    {
        // Writer: drafts essay
        adapters::OllamaConfig writer_config;
        writer_config.host = "http://localhost:11434";
        writer_config.model = "llama3.3";
        writer_config.temperature = 0.8;
        writer_config.system = "You are an essay writer. Write clear, persuasive essays. "
                                "If critiqued, revise to address feedback while maintaining "
                                "your argument. Keep essays under 100 words.";

        auto writer = std::make_shared<adapters::OllamaAgent>(writer_config);

        // Critic: reviews essay
        adapters::OllamaConfig critic_config;
        critic_config.host = "http://localhost:11434";
        critic_config.model = "llama3.3";
        critic_config.temperature = 0.4;
        critic_config.system = "You are an English teacher. Evaluate essays for:\n"
                                "- Clear thesis statement\n"
                                "- Supporting evidence\n"
                                "- Logical structure\n"
                                "- Grammar and style\n"
                                "Start with 'APPROVED' if excellent, otherwise give "
                                "2-3 specific improvements needed.";

        auto critic = std::make_shared<adapters::OllamaAgent>(critic_config);

        patterns::ReflectionAgent agent(writer, critic, 3);

        std::string prompt = "Write an essay: Why software testing is crucial for quality";
        std::cout << "Prompt: " << prompt << "\n\n";
        std::cout << "[Writing and revising...]\n\n";

        auto msg = core::Message::with_text("user", prompt);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Polished Essay ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";

            auto history = agent.get_reflection_history();
            std::cout << "✓ Refined through " << history.size() << " revision cycles\n";
        }
    }

    // Summary
    print_separator("Key Insights");
    std::cout << "✓ Dual LLMs: Separate writer and critic roles\n";
    std::cout << "✓ System Prompts: Define role-specific behavior\n";
    std::cout << "✓ Iterative Improvement: Multiple critique-revision cycles\n";
    std::cout << "✓ Convergence Detection: 'APPROVED' keyword stops iteration\n";
    std::cout << "✓ Temperature Tuning: Higher for creativity, lower for critique\n";
    std::cout << "✓ Domain Flexibility: Works for code, writing, technical docs\n";

    print_separator("Example Complete");
    return 0;
}
