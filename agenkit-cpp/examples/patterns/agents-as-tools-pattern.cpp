/**
 * @file agents_as_tools_example.cpp
 * @brief Example demonstrating the Agents-as-Tools pattern
 *
 * This example shows how to wrap specialized agents as tools
 * and use them in a ReAct agent for complex problem-solving.
 */

#include <iostream>
#include <set>
#include "agenkit/patterns/agents_as_tools.hpp"
#include "agenkit/patterns/react.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit;

/**
 * @brief Specialized agent for mathematical operations
 */
class MathAgent : public core::Agent {
public:
    std::string name() const override {
        return "math_agent";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string query = message.content_as_str();
        std::string response;

        // Simple math evaluation (mock)
        if (query.find("factorial") != std::string::npos) {
            response = "Factorial calculation: 5! = 120";
        } else if (query.find("square root") != std::string::npos) {
            response = "Square root of 144 = 12";
        } else if (query.find("*") != std::string::npos || query.find("+") != std::string::npos) {
            // Mock calculation result
            response = "Calculation result: 42";
        } else {
            response = "Result: " + query + " = 10";
        }

        auto msg = core::Message::with_text("assistant", response);
        msg.with_metadata("computation_type", "mathematical");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

/**
 * @brief Specialized agent for text analysis
 */
class TextAnalysisAgent : public core::Agent {
public:
    std::string name() const override {
        return "text_analysis_agent";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string text = message.content_as_str();
        std::string analysis;

        // Mock text analysis
        size_t word_count = 1;
        for (char c : text) {
            if (c == ' ') word_count++;
        }

        analysis = "Text Analysis:\n";
        analysis += "- Word count: " + std::to_string(word_count) + "\n";
        analysis += "- Character count: " + std::to_string(text.length()) + "\n";
        analysis += "- Contains numbers: " + std::string(
            text.find_first_of("0123456789") != std::string::npos ? "Yes" : "No"
        );

        auto msg = core::Message::with_text("assistant", analysis);
        msg.with_metadata("analysis_type", "text");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

/**
 * @brief Specialized agent for data lookup
 */
class DatabaseAgent : public core::Agent {
public:
    std::string name() const override {
        return "database_agent";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string query = message.content_as_str();
        std::string result;

        // Mock database lookup
        if (query.find("user") != std::string::npos) {
            result = "User record: {id: 123, name: 'Alice', role: 'admin'}";
        } else if (query.find("product") != std::string::npos) {
            result = "Product: {id: 456, name: 'Widget', price: $29.99}";
        } else {
            result = "Query executed: " + std::to_string(rand() % 100) + " records found";
        }

        auto msg = core::Message::with_text("assistant", result);
        msg.with_metadata("query_type", "database");
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

/**
 * @brief Mock orchestrator agent that decides which tools to use
 */
class OrchestratorAgent : public core::Agent {
private:
    int call_count_ = 0;

public:
    std::string name() const override {
        return "orchestrator";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        call_count_++;
        std::string content = message.content_as_str();

        std::string response;

        // Analyze the query and determine tool usage
        if (content.find("Observation:") != std::string::npos) {
            // We have results, provide final answer
            response = "Final Answer: Based on the tool results, I have gathered all necessary information. ";
            response += "The specialized agents (math, text analysis, and database) have successfully completed their tasks.";
        } else if (call_count_ == 1) {
            // First call - use math agent
            response = "Thought: This query requires mathematical computation. I'll use the math agent.\n";
            response += "Action: math_calculator: Calculate 6 * 7";
        } else if (call_count_ == 2) {
            // Second call - use text analysis
            response = "Thought: Now I'll analyze the text content.\n";
            response += "Action: text_analyzer: The quick brown fox jumps over the lazy dog";
        } else {
            // Third call - use database
            response = "Thought: Finally, let me look up some data.\n";
            response += "Action: data_lookup: Find user with id 123";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }

    void reset() { call_count_ = 0; }
};

int main() {
    std::cout << "=== Agenkit C++ Agents-as-Tools Pattern Example ===\n\n";

    // Create specialized agents
    auto math_agent = std::make_shared<MathAgent>();
    auto text_agent = std::make_shared<TextAnalysisAgent>();
    auto db_agent = std::make_shared<DatabaseAgent>();

    std::cout << "Created specialized agents:\n";
    std::cout << "  - " << math_agent->name() << " (mathematical computations)\n";
    std::cout << "  - " << text_agent->name() << " (text analysis)\n";
    std::cout << "  - " << db_agent->name() << " (data lookup)\n\n";

    // Wrap agents as tools using builder pattern
    auto math_tool = patterns::AgentToolBuilder(
        math_agent,
        "math_calculator",
        "Performs mathematical calculations like addition, multiplication, factorials"
    )
        .with_timing(true)
        .with_metadata_propagation(true)
        .build();

    auto text_tool = patterns::AgentToolBuilder(
        text_agent,
        "text_analyzer",
        "Analyzes text for word count, character count, and content patterns"
    )
        .with_timing(true)
        .build();

    auto db_tool = patterns::AgentToolBuilder(
        db_agent,
        "data_lookup",
        "Queries database for user records, products, and other data"
    )
        .with_timeout(std::chrono::seconds(5))
        .with_timing(true)
        .build();

    std::cout << "Wrapped agents as tools:\n";
    std::cout << "  - " << math_tool->name() << ": " << math_tool->description() << "\n";
    std::cout << "  - " << text_tool->name() << ": " << text_tool->description() << "\n";
    std::cout << "  - " << db_tool->name() << ": " << db_tool->description() << "\n\n";

    // Create ReAct agent with agent tools
    auto orchestrator = std::make_shared<OrchestratorAgent>();
    patterns::ReactAgent react_agent(orchestrator, 10);

    react_agent.add_tool(math_tool);
    react_agent.add_tool(text_tool);
    react_agent.add_tool(db_tool);

    std::cout << "=== Running Multi-Agent Task ===\n\n";

    std::string query = "I need to: 1) Calculate 6*7, 2) Analyze a sentence, 3) Look up user data";
    std::cout << "Query: \"" << query << "\"\n\n";

    auto msg = core::Message::with_text("user", query);
    auto future = react_agent.process(std::move(msg));
    auto result = future.get();

    if (result.is_ok()) {
        auto response = result.unwrap();

        std::cout << "=== Final Answer ===\n";
        std::cout << response.content_as_str() << "\n\n";

        std::cout << "=== Execution Trace ===\n";
        const auto& history = react_agent.get_history();

        for (size_t i = 0; i < history.size(); i++) {
            const auto& step = history[i];
            std::cout << "\n--- Step " << step.step << " ---\n";
            std::cout << "Thought: " << step.thought << "\n";
            std::cout << "Action: " << step.action << "\n";
            std::cout << "Tool Used: " << step.tool_name << "\n";
            std::cout << "Tool Input: " << step.tool_input << "\n";
            std::cout << "Observation: " << step.observation << "\n";
            std::cout << "Success: " << (step.success ? "Yes" : "No") << "\n";
        }

        std::cout << "\n=== Execution Statistics ===\n";
        std::cout << "Total steps: " << history.size() << "\n";

        // Count unique tools used
        std::set<std::string> unique_tools;
        for (const auto& step : history) {
            if (!step.tool_name.empty()) {
                unique_tools.insert(step.tool_name);
            }
        }
        std::cout << "Unique tools used: " << unique_tools.size() << "\n";
        std::cout << "Tools: ";
        for (const auto& tool : unique_tools) {
            std::cout << tool << " ";
        }
        std::cout << "\n";
    } else {
        std::cerr << "Error: " << result.unwrap_err().message() << "\n";
        return 1;
    }

    std::cout << "\n=== Direct Tool Usage Example ===\n\n";

    // Demonstrate direct tool usage (without ReAct)
    std::cout << "Using math_calculator directly:\n";
    auto math_result = math_tool->execute("What is the factorial of 5?");
    std::cout << "Input: \"What is the factorial of 5?\"\n";
    std::cout << "Output: " << math_result.content << "\n";
    std::cout << "Execution time: " << math_result.metadata["execution_time_ms"] << "ms\n";
    if (math_result.metadata.contains("computation_type")) {
        std::cout << "Metadata: computation_type = " << math_result.metadata["computation_type"] << "\n";
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. Any agent can be wrapped as a tool using AgentTool\n";
    std::cout << "2. Agent tools integrate seamlessly with ReAct pattern\n";
    std::cout << "3. Specialized agents can be composed into complex systems\n";
    std::cout << "4. Builder pattern provides clean configuration\n";
    std::cout << "5. Metadata flows through the entire execution chain\n";
    std::cout << "6. Timeout and error handling work transparently\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
