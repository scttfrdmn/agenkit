/**
 * @file reflection_example.cpp
 * @brief Example demonstrating the Reflection pattern
 *
 * This example shows how to use the Reflection pattern to improve
 * agent responses through iterative self-critique.
 */

#include <iostream>
#include "agenkit/patterns/reflection.hpp"
#include "agenkit/adapters/echo_agent.hpp"

using namespace agenkit;

/**
 * @brief Mock agent that generates responses (simulates an LLM)
 */
class WriterAgent : public core::Agent {
public:
    std::string name() const override {
        return "writer";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content_str = message.content_as_str();

        std::string response;
        if (content_str.find("improvement") != std::string::npos) {
            // If asked to improve, generate a better response
            response = "Quantum computing uses quantum mechanical phenomena like "
                      "superposition and entanglement to perform computations. "
                      "Unlike classical bits (0 or 1), quantum bits (qubits) can exist "
                      "in superposition states, enabling parallel processing of information. "
                      "This provides exponential speedup for certain algorithms like "
                      "Shor's algorithm for factoring and Grover's search algorithm.";
        } else {
            // Initial response (intentionally simple)
            response = "Quantum computing is computing using quantum mechanics.";
        }

        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

/**
 * @brief Mock critic agent that provides feedback
 */
class CriticAgent : public core::Agent {
private:
    int call_count_ = 0;

public:
    std::string name() const override {
        return "critic";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        call_count_++;

        // Parse the response being critiqued
        std::string content_str = message.content_as_str();

        std::string feedback;
        if (call_count_ == 1) {
            // First critique: provide constructive feedback
            feedback = "The response is too brief and lacks specific details. "
                      "Please elaborate on:\n"
                      "1. What quantum mechanics principles are used\n"
                      "2. How quantum computing differs from classical computing\n"
                      "3. Practical applications or algorithms\n"
                      "Please provide a more comprehensive answer.";
        } else {
            // Second critique: approve the improved response
            feedback = "APPROVED - This response is much better! It includes:\n"
                      "- Clear explanation of superposition and entanglement\n"
                      "- Comparison with classical computing\n"
                      "- Specific algorithm examples\n"
                      "- Technical accuracy\n"
                      "The response is comprehensive and informative.";
        }

        auto msg = core::Message::with_text("assistant", feedback);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

int main() {
    std::cout << "=== Agenkit C++ Reflection Pattern Example ===\n\n";

    // Create agents
    auto writer = std::make_shared<WriterAgent>();
    auto critic = std::make_shared<CriticAgent>();

    // Create reflection agent with max 3 reflections
    patterns::ReflectionAgent reflection_agent(writer, critic, 3);

    std::cout << "Agent: " << reflection_agent.name() << "\n";
    std::cout << "Capabilities: ";
    for (const auto& cap : reflection_agent.capabilities()) {
        std::cout << cap << " ";
    }
    std::cout << "\n\n";

    // User query
    std::string query = "Explain quantum computing in simple terms";
    std::cout << "User Query: \"" << query << "\"\n\n";

    // Process with reflection
    auto msg = core::Message::with_text("user", query);
    msg.with_metadata("example", "reflection");

    std::cout << "Processing with reflection loop...\n\n";

    auto future = reflection_agent.process(std::move(msg));
    auto result = future.get();

    if (result.is_err()) {
        std::cerr << "Error: " << result.unwrap_err().message() << "\n";
        return 1;
    }

    auto response = result.unwrap();

    // Display results
    std::cout << "=== Final Response ===\n";
    std::cout << response.content_as_str() << "\n\n";

    // Display reflection metadata
    std::cout << "=== Reflection Metadata ===\n";
    std::cout << "Total iterations: "
              << response.metadata()["reflection_iterations"] << "\n";
    std::cout << "Final iteration: "
              << response.metadata()["final_iteration"] << "\n\n";

    // Display reflection history
    std::cout << "=== Reflection History ===\n";
    const auto& history = reflection_agent.get_reflection_history();
    for (const auto& step : history) {
        std::cout << "\nIteration " << step.iteration << ":\n";
        std::cout << "  Response preview: "
                  << step.response.content_as_str().substr(0, 60) << "...\n";
        std::cout << "  Feedback preview: "
                  << step.feedback.content_as_str().substr(0, 60) << "...\n";
        std::cout << "  Should continue: "
                  << (step.should_continue ? "Yes" : "No") << "\n";
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. The reflection pattern improved the response quality\n";
    std::cout << "2. The critic provided specific, actionable feedback\n";
    std::cout << "3. The pattern stopped when the response was approved\n";
    std::cout << "4. Full reflection history is preserved for analysis\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
