/**
 * @file reasoning_with_tools_example.cpp
 * @brief Example demonstrating Reasoning with Tools pattern
 *
 * This example shows chain-of-thought reasoning combined with strategic tool use.
 */

#include <iostream>
#include "agenkit/patterns/reasoning_with_tools.hpp"

using namespace agenkit;

// Scientific calculator tool
class ScientificCalculator : public patterns::Tool {
public:
    std::string name() const override { return "calculator"; }
    std::string description() const override {
        return "Performs mathematical calculations (arithmetic, percentages, etc.)";
    }

    patterns::ToolResult execute(const std::string& input) override {
        // Mock calculation
        if (input.find("%") != std::string::npos) {
            return patterns::ToolResult::ok("15");
        }
        return patterns::ToolResult::ok("42");
    }
};

// Mock reasoning LLM that demonstrates multi-step reasoning
class ReasoningLLM : public core::Agent {
private:
    int step_;

public:
    ReasoningLLM() : step_(0) {}

    std::string name() const override { return "reasoning_llm"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        step_++;
        std::string content = message.content_as_str();
        std::string response;

        if (step_ == 1) {
            // Initial reasoning
            response = "Step 1: Breaking down the problem\n";
            response += "The question asks about percentage calculation.\n";
            response += "I need to calculate 15% of 200.\n";
            response += "This requires: (15/100) * 200\n";
            response += "USE TOOL: calculator: 15% of 200\n";
            response += "Conclusion: Need to use calculator for precision\n";
            response += "CONFIDENCE: 0.9";
        } else if (step_ == 2) {
            // After tool result
            response = "Step 2: Analyzing the result\n";
            response += "The calculator returned: 15\n";
            response += "This makes sense: 15% of 200 = (15/100) × 200 = 15 × 2 = 30\n";
            response += "Wait, let me verify: 10% of 200 = 20, so 15% = 20 + 10 = 30\n";
            response += "Conclusion: The answer is 30\n";
            response += "CONFIDENCE: 0.95\n";
            response += "FINAL ANSWER: 15% of 200 equals 30";
        } else {
            response = "FINAL ANSWER: 30";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    void reset() { step_ = 0; }
};

int main() {
    std::cout << "=== Agenkit C++ Reasoning with Tools Example ===\n\n";

    // Create reasoning agent
    auto llm = std::make_shared<ReasoningLLM>();
    patterns::ReasoningAgent agent(llm);

    // Add tools
    auto calculator = std::make_shared<ScientificCalculator>();
    agent.add_tool(calculator);

    // Configure reasoning
    patterns::ReasoningConfig config;
    config.max_reasoning_steps = 10;
    config.min_confidence = 0.8;
    config.use_chain_of_thought = true;
    agent.set_config(config);

    std::cout << "Reasoning Agent: " << agent.name() << "\n";
    std::cout << "Capabilities: ";
    for (const auto& cap : agent.capabilities()) {
        std::cout << cap << " ";
    }
    std::cout << "\n\nTools available: " << agent.get_tools().size() << "\n\n";

    // Process query
    std::string query = "What is 15% of 200?";
    std::cout << "=== Query ===\n" << query << "\n\n";

    auto msg = core::Message::with_text("user", query);
    auto result = agent.process(std::move(msg)).get();

    if (result.is_ok()) {
        auto response = result.unwrap();

        std::cout << "=== Final Answer ===\n";
        std::cout << response.content_as_str() << "\n\n";

        std::cout << "=== Reasoning Trace ===\n";
        const auto& history = agent.get_reasoning_history();

        for (const auto& step : history) {
            std::cout << "\n--- Step " << step.step << " ---\n";
            std::cout << step.reasoning << "\n";

            if (step.requires_tool) {
                std::cout << "\n[Tool Used: " << step.tool_name << "]\n";
                std::cout << "Input: " << step.tool_input << "\n";
                std::cout << "Result: " << step.tool_result << "\n";
            }

            if (!step.conclusion.empty()) {
                std::cout << "\nConclusion: " << step.conclusion << "\n";
            }

            std::cout << "Confidence: " << step.confidence << "\n";
        }

        std::cout << "\n=== Statistics ===\n";
        std::cout << "Total reasoning steps: " << response.metadata()["reasoning_steps"] << "\n";
        std::cout << "Average confidence: " << response.metadata()["average_confidence"] << "\n";
        std::cout << "Tool uses: " << response.metadata()["tool_uses"] << "\n";
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. Chain-of-thought: Explicit reasoning at each step\n";
    std::cout << "2. Strategic tool use: Tools invoked when needed\n";
    std::cout << "3. Confidence tracking: Self-assessment at each step\n";
    std::cout << "4. Verification: Agent can check its own work\n";
    std::cout << "5. Transparency: Complete reasoning trace preserved\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
