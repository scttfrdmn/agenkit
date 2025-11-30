/**
 * @file react_example.cpp
 * @brief Example demonstrating the ReAct (Reasoning + Acting) pattern
 *
 * This example shows how to use the ReAct pattern to combine reasoning
 * with tool use through a Thought → Action → Observation loop.
 */

#include <iostream>
#include <sstream>
#include "agenkit/patterns/react.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit;

/**
 * @brief Simple calculator tool for basic arithmetic
 */
class CalculatorTool : public patterns::Tool {
public:
    std::string name() const override {
        return "calculator";
    }

    std::string description() const override {
        return "Performs basic arithmetic operations (+, -, *, /). "
               "Format: 'number operator number' (e.g., '15 * 20')";
    }

    patterns::ToolResult execute(const std::string& input) override {
        std::istringstream iss(input);
        double a, b;
        char op;

        if (!(iss >> a >> op >> b)) {
            return patterns::ToolResult::error("Invalid format. Use: number operator number");
        }

        double result;
        switch (op) {
            case '+':
                result = a + b;
                break;
            case '-':
                result = a - b;
                break;
            case '*':
                result = a * b;
                break;
            case '/':
                if (b == 0) {
                    return patterns::ToolResult::error("Division by zero");
                }
                result = a / b;
                break;
            default:
                return patterns::ToolResult::error("Unknown operator: " + std::string(1, op));
        }

        return patterns::ToolResult::ok(std::to_string(result));
    }
};

/**
 * @brief Mock search tool that returns canned results
 */
class SearchTool : public patterns::Tool {
public:
    std::string name() const override {
        return "search";
    }

    std::string description() const override {
        return "Searches for information. Provide a search query.";
    }

    patterns::ToolResult execute(const std::string& input) override {
        // Mock search results for demonstration
        if (input.find("population") != std::string::npos && input.find("France") != std::string::npos) {
            return patterns::ToolResult::ok("France has a population of approximately 67 million people.");
        } else if (input.find("capital") != std::string::npos && input.find("France") != std::string::npos) {
            return patterns::ToolResult::ok("The capital of France is Paris.");
        } else if (input.find("GDP") != std::string::npos) {
            return patterns::ToolResult::ok("France has a GDP of approximately $2.7 trillion USD.");
        } else {
            return patterns::ToolResult::ok("No specific information found for: " + input);
        }
    }
};

/**
 * @brief Mock agent that simulates LLM reasoning
 *
 * This agent demonstrates the ReAct loop by:
 * 1. Analyzing the question
 * 2. Deciding which tool to use
 * 3. Formulating the final answer from observations
 */
class MockReasoningAgent : public core::Agent {
private:
    int step_;

public:
    MockReasoningAgent() : step_(0) {}

    std::string name() const override {
        return "reasoning_llm";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        step_++;
        std::string content = message.content_as_str();

        std::string response;

        // Detect if this is the initial query or a continuation
        if (content.find("Observation:") != std::string::npos) {
            // This is a continuation with observation
            if (content.find("67 million") != std::string::npos ||
                content.find("2.7 trillion") != std::string::npos) {
                // We have the information we need
                response = "Thought: I now have all the information needed to answer the question.\n";
                response += "Final Answer: France has a population of 67 million and a GDP of $2.7 trillion. ";
                response += "To calculate GDP per capita: 2,700,000,000,000 / 67,000,000 = approximately $40,300 per person.";
            } else if (content.find("population") != std::string::npos) {
                // Got population, now need GDP
                response = "Thought: I have the population. Now I need France's GDP to calculate per capita.\n";
                response += "Action: search: France GDP";
            } else {
                // Need to calculate
                response = "Thought: I have both numbers, now I need to calculate.\n";
                response += "Action: calculator: 2700000000000 / 67000000";
            }
        } else {
            // Initial query - analyze what we need
            if (content.find("GDP per capita") != std::string::npos) {
                response = "Thought: To calculate GDP per capita, I need France's total GDP and population. Let me start by finding the population.\n";
                response += "Action: search: France population";
            } else if (content.find("15% of 200") != std::string::npos) {
                response = "Thought: I need to calculate 15% of 200, which is 0.15 * 200.\n";
                response += "Action: calculator: 0.15 * 200";
            } else {
                // Default: provide final answer
                response = "Final Answer: I need more specific information to answer this question.";
            }
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    void reset() { step_ = 0; }
};

int main() {
    std::cout << "=== Agenkit C++ ReAct Pattern Example ===\n\n";

    // Create tools
    auto calculator = std::make_shared<CalculatorTool>();
    auto search = std::make_shared<SearchTool>();

    // Create ReAct agent
    auto llm = std::make_shared<MockReasoningAgent>();
    patterns::ReactAgent react_agent(llm, 10);

    react_agent.add_tool(calculator);
    react_agent.add_tool(search);

    std::cout << "Agent: " << react_agent.name() << "\n";
    std::cout << "Capabilities: ";
    for (const auto& cap : react_agent.capabilities()) {
        std::cout << cap << " ";
    }
    std::cout << "\n\n";

    std::cout << "Available Tools:\n";
    for (const auto& tool : react_agent.get_tools()) {
        std::cout << "  - " << tool->name() << ": " << tool->description() << "\n";
    }
    std::cout << "\n";

    // Example 1: Simple calculation
    std::cout << "=== Example 1: Simple Calculation ===\n";
    std::string query1 = "What is 15% of 200?";
    std::cout << "Query: \"" << query1 << "\"\n\n";

    auto msg1 = core::Message::with_text("user", query1);
    auto future1 = react_agent.process(std::move(msg1));
    auto result1 = future1.get();

    if (result1.is_ok()) {
        auto response = result1.unwrap();
        std::cout << "Final Answer: " << response.content_as_str() << "\n";
        std::cout << "Steps taken: " << response.metadata()["react_steps"] << "\n\n";

        // Show ReAct history
        std::cout << "ReAct History:\n";
        const auto& history1 = react_agent.get_history();
        for (const auto& step : history1) {
            std::cout << "\nStep " << step.step << ":\n";
            std::cout << "  Thought: " << step.thought << "\n";
            std::cout << "  Action: " << step.action << "\n";
            std::cout << "  Observation: " << step.observation << "\n";
            std::cout << "  Success: " << (step.success ? "Yes" : "No") << "\n";
        }
    }

    std::cout << "\n========================================\n\n";

    // Reset for next example
    llm->reset();
    react_agent.clear_history();

    // Example 2: Multi-step reasoning with multiple tools
    std::cout << "=== Example 2: Multi-Tool Reasoning ===\n";
    std::string query2 = "What is France's GDP per capita?";
    std::cout << "Query: \"" << query2 << "\"\n\n";

    auto msg2 = core::Message::with_text("user", query2);
    auto future2 = react_agent.process(std::move(msg2));
    auto result2 = future2.get();

    if (result2.is_ok()) {
        auto response = result2.unwrap();
        std::cout << "Final Answer: " << response.content_as_str() << "\n";
        std::cout << "Steps taken: " << response.metadata()["react_steps"] << "\n\n";

        // Show ReAct history
        std::cout << "ReAct History:\n";
        const auto& history2 = react_agent.get_history();
        for (const auto& step : history2) {
            std::cout << "\nStep " << step.step << ":\n";
            std::cout << "  Thought: " << step.thought.substr(0, 60) << "...\n";
            std::cout << "  Tool: " << step.tool_name << "\n";
            std::cout << "  Input: " << step.tool_input << "\n";
            std::cout << "  Observation: " << step.observation.substr(0, 60);
            if (step.observation.length() > 60) std::cout << "...";
            std::cout << "\n";
        }

        // Show tools used
        std::cout << "\nTools Used: ";
        const auto& tools_used = response.metadata()["tools_used"];
        for (const auto& tool_name : tools_used) {
            std::cout << tool_name << " ";
        }
        std::cout << "\n";
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. ReAct combines reasoning (thoughts) with actions (tool use)\n";
    std::cout << "2. The agent iteratively refines its approach based on observations\n";
    std::cout << "3. Multiple tools can be used in sequence to solve complex problems\n";
    std::cout << "4. Full trace history enables debugging and transparency\n";
    std::cout << "5. The pattern stops when a final answer is reached\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
