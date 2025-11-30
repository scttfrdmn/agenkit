/**
 * @file react_tools_example.cpp
 * @brief Example: ReAct pattern with tool use and Ollama
 *
 * This example demonstrates:
 * - ReAct (Reasoning + Acting) pattern
 * - Tool selection and execution
 * - Multi-step reasoning
 * - Local LLM inference with Ollama
 * - Solving complex problems requiring multiple tools
 *
 * The agent has access to three tools:
 * - Calculator: Math operations
 * - Weather: City weather lookup
 * - Search: Web search simulation
 *
 * Setup:
 *   ollama serve               # Start Ollama (separate terminal)
 *   ollama pull llama3.3       # Pull model
 *   ./react_tools_example      # Run this example
 */

#include <iostream>
#include <memory>
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/patterns/react.hpp"
#include "agenkit/core/message.hpp"
#include "tools/calculator_tool.hpp"
#include "tools/weather_tool.hpp"
#include "tools/search_tool.hpp"

using namespace agenkit;

void print_header(const std::string& title) {
    std::cout << "\n";
    std::cout << "================================================================\n";
    std::cout << "  " << title << "\n";
    std::cout << "================================================================\n\n";
}

void print_separator() {
    std::cout << std::string(60, '-') << "\n";
}

int main() {
    print_header("AgentKit C++ - ReAct Pattern with Tools (Ollama)");

    // Configure Ollama
    adapters::OllamaConfig config;
    config.host = "http://localhost:11434";
    config.model = "llama3.3";  // or "mistral:7b", "qwen2.5:7b"
    config.temperature = 0.7;

    try {
        // Create Ollama agent
        auto agent = std::make_shared<adapters::OllamaAgent>(config);

        std::cout << "Configuration:\n";
        std::cout << "  Host:  " << config.host << "\n";
        std::cout << "  Model: " << config.model << "\n";
        std::cout << "  Max Steps: 5\n\n";

        // Check if Ollama is available
        if (!agent->is_available()) {
            std::cerr << "❌ Ollama server not available\n\n";
            std::cerr << "Please start Ollama:\n";
            std::cerr << "  1. Install: brew install ollama\n";
            std::cerr << "  2. Start:   ollama serve\n";
            std::cerr << "  3. Pull:    ollama pull " << config.model << "\n\n";
            return 1;
        }

        std::cout << "✓ Ollama server is running\n\n";

        // Create tools
        auto calc = std::make_shared<examples::CalculatorTool>();
        auto weather = std::make_shared<examples::WeatherTool>();
        auto search = std::make_shared<examples::SearchTool>();

        // Create ReAct agent with tools
        patterns::ReactAgent react(agent, 5);  // max 5 steps
        react.add_tool(calc);
        react.add_tool(weather);
        react.add_tool(search);

        std::cout << "Available Tools:\n";
        std::cout << "  • " << calc->name() << " - " << calc->description() << "\n";
        std::cout << "  • " << weather->name() << " - " << weather->description() << "\n";
        std::cout << "  • " << search->name() << " - " << search->description() << "\n\n";

        // Example 1: Simple calculation
        print_separator();
        std::cout << "Example 1: Simple Calculation\n";
        print_separator();

        std::string query1 = "What is 15% tip on a bill of $47.50?";
        std::cout << "\nQuery: " << query1 << "\n\n";

        auto msg1 = core::Message::with_text("user", query1);
        auto future1 = react.process(std::move(msg1));
        auto result1 = future1.get();

        if (result1.is_err()) {
            std::cerr << "Error: " << result1.unwrap_err().message() << "\n";
        } else {
            auto response1 = result1.unwrap();
            std::cout << "Result: " << response1.content_as_str() << "\n\n";
        }

        // Example 2: Weather + Calculation
        print_separator();
        std::cout << "Example 2: Multi-Tool Query\n";
        print_separator();

        std::string query2 = "What's the weather in Paris? Also, if I buy 3 items at $12.50 each, what's the total?";
        std::cout << "\nQuery: " << query2 << "\n\n";

        auto msg2 = core::Message::with_text("user", query2);
        auto future2 = react.process(std::move(msg2));
        auto result2 = future2.get();

        if (result2.is_ok()) {
            auto response2 = result2.unwrap();
            std::cout << "Result: " << response2.content_as_str() << "\n\n";
        }

        // Example 3: Search + Reasoning
        print_separator();
        std::cout << "Example 3: Search and Reasoning\n";
        print_separator();

        std::string query3 = "What is the ReAct pattern and why would I use it?";
        std::cout << "\nQuery: " << query3 << "\n\n";

        auto msg3 = core::Message::with_text("user", query3);
        auto future3 = react.process(std::move(msg3));
        auto result3 = future3.get();

        if (result3.is_ok()) {
            auto response3 = result3.unwrap();
            std::cout << "Result: " << response3.content_as_str() << "\n\n";
        }

        // Example 4: Complex multi-step
        print_separator();
        std::cout << "Example 4: Complex Multi-Step Problem\n";
        print_separator();

        std::string query4 = "I'm visiting Tokyo. What's the weather like there? "
                            "If I exchange 100 USD at 150 yen per dollar, how many yen do I get?";
        std::cout << "\nQuery: " << query4 << "\n\n";

        auto msg4 = core::Message::with_text("user", query4);
        auto future4 = react.process(std::move(msg4));
        auto result4 = future4.get();

        if (result4.is_ok()) {
            auto response4 = result4.unwrap();
            std::cout << "Result: " << response4.content_as_str() << "\n\n";
        }

        print_separator();
        std::cout << "\n✓ ReAct examples complete!\n";
        std::cout << "\nKey Observations:\n";
        std::cout << "  • Agent reasons about which tool to use\n";
        std::cout << "  • Can use multiple tools in sequence\n";
        std::cout << "  • Combines tool results into coherent answer\n";
        std::cout << "  • Handles complex, multi-step problems\n\n";

        std::cout << "Try your own queries:\n";
        std::cout << "  • Mix calculations with weather lookups\n";
        std::cout << "  • Ask questions requiring web search\n";
        std::cout << "  • Combine multiple tools in one query\n\n";

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
