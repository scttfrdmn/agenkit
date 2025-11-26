/**
 * @file orchestration_example.cpp
 * @brief Example demonstrating the Orchestration pattern
 *
 * This example shows how to coordinate multiple specialized agents
 * using different orchestration strategies.
 */

#include <iostream>
#include "agenkit/patterns/orchestration.hpp"

using namespace agenkit;

// Research agent
class ResearchAgent : public core::Agent {
public:
    std::string name() const override { return "research_agent"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string query = message.content_as_str();
        std::string research = "Research findings for '" + query + "':\n";
        research += "- Key fact 1: Relevant information about the topic\n";
        research += "- Key fact 2: Important data points\n";
        research += "- Key fact 3: Historical context";

        auto msg = core::Message::with_text("assistant", research);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Writer agent
class WriterAgent : public core::Agent {
public:
    std::string name() const override { return "writer_agent"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string input = message.content_as_str();
        std::string draft = "Draft article based on research:\n\n";
        draft += "The topic presents interesting insights. ";
        draft += "Based on the available information, we can conclude that... ";
        draft += "[Content elaborated from: " + input.substr(0, 50) + "...]";

        auto msg = core::Message::with_text("assistant", draft);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

// Reviewer agent
class ReviewerAgent : public core::Agent {
public:
    std::string name() const override { return "reviewer_agent"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content = message.content_as_str();
        std::string review = "Editorial review:\n";
        review += "✓ Structure is clear and logical\n";
        review += "✓ Content is well-researched\n";
        review += "✓ Ready for publication\n";
        review += "\nFinal approved content:\n" + content;

        auto msg = core::Message::with_text("assistant", review);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

int main() {
    std::cout << "=== Agenkit C++ Orchestration Pattern Example ===\n\n";

    // Create specialized agents
    auto research = std::make_shared<ResearchAgent>();
    auto writer = std::make_shared<WriterAgent>();
    auto reviewer = std::make_shared<ReviewerAgent>();

    std::cout << "Created specialized agents:\n";
    std::cout << "  - " << research->name() << "\n";
    std::cout << "  - " << writer->name() << "\n";
    std::cout << "  - " << reviewer->name() << "\n\n";

    // Example 1: Sequential Orchestration
    std::cout << "=== Example 1: Sequential Orchestration ===\n\n";

    patterns::OrchestrationAgent seq_orchestrator;
    seq_orchestrator.add_agent("research", research);
    seq_orchestrator.add_agent("writer", writer);
    seq_orchestrator.add_agent("reviewer", reviewer);

    seq_orchestrator.set_strategy(patterns::OrchestrationStrategy::Sequential);

    // Define routing: research -> writer -> reviewer -> done
    seq_orchestrator.set_routing([](const core::Message& msg) -> std::string {
        std::string content = msg.content_as_str();

        if (content.find("Research findings") != std::string::npos) {
            return "writer";
        } else if (content.find("Draft article") != std::string::npos) {
            return "reviewer";
        } else if (content.find("Editorial review") != std::string::npos) {
            return ""; // Done
        }
        return "research"; // Start with research
    });

    auto query = core::Message::with_text("user", "AI ethics in healthcare");
    std::cout << "Query: \"AI ethics in healthcare\"\n\n";

    auto result1 = seq_orchestrator.process(std::move(query)).get();

    if (result1.is_ok()) {
        auto response = result1.unwrap();
        std::cout << "=== Sequential Result ===\n";
        std::cout << response.content_as_str() << "\n\n";

        std::cout << "=== Execution Trace ===\n";
        const auto& history = seq_orchestrator.get_history();
        for (const auto& step : history) {
            std::cout << "Step " << step.step << ": " << step.agent_name;
            std::cout << " [" << (step.success ? "✓" : "✗") << "]\n";
        }
        std::cout << "\nTotal steps: " << history.size() << "\n\n";
    }

    // Example 2: Parallel Orchestration
    std::cout << "=== Example 2: Parallel Orchestration ===\n\n";

    patterns::OrchestrationAgent par_orchestrator;
    par_orchestrator.add_agent("research", research);
    par_orchestrator.add_agent("writer", writer);
    par_orchestrator.add_agent("reviewer", reviewer);

    par_orchestrator.set_strategy(patterns::OrchestrationStrategy::Parallel);

    auto query2 = core::Message::with_text("user", "Climate change solutions");
    std::cout << "Query: \"Climate change solutions\"\n\n";

    auto result2 = par_orchestrator.process(std::move(query2)).get();

    if (result2.is_ok()) {
        auto response = result2.unwrap();
        std::cout << "=== Parallel Results (Combined) ===\n";
        std::cout << response.content_as_str() << "\n\n";

        std::cout << "=== Agents Called in Parallel ===\n";
        const auto& history = par_orchestrator.get_history();
        for (const auto& step : history) {
            std::cout << "  - " << step.agent_name << "\n";
        }
        std::cout << "\n";
    }

    // Example 3: Custom Combiner
    std::cout << "=== Example 3: Custom Combiner ===\n\n";

    patterns::OrchestrationAgent custom_orchestrator;
    custom_orchestrator.add_agent("research", research);
    custom_orchestrator.add_agent("writer", writer);

    custom_orchestrator.set_strategy(patterns::OrchestrationStrategy::Parallel);

    // Custom combiner that creates a structured report
    custom_orchestrator.set_combiner([](const std::vector<core::Message>& messages) {
        std::string report = "=== Structured Report ===\n\n";

        for (const auto& msg : messages) {
            std::string content = msg.content_as_str();
            if (content.find("Research") != std::string::npos) {
                report += "## Research Section\n" + content + "\n\n";
            } else if (content.find("Draft") != std::string::npos) {
                report += "## Content Section\n" + content + "\n\n";
            }
        }

        return core::Message::with_text("assistant", report);
    });

    auto query3 = core::Message::with_text("user", "Future of work");
    std::cout << "Query: \"Future of work\"\n\n";

    auto result3 = custom_orchestrator.process(std::move(query3)).get();

    if (result3.is_ok()) {
        auto response = result3.unwrap();
        std::cout << response.content_as_str() << "\n";
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. Sequential: Agents process in a defined order (pipeline)\n";
    std::cout << "2. Parallel: All agents run concurrently for speed\n";
    std::cout << "3. Custom combiner: Flexible result aggregation\n";
    std::cout << "4. Routing function: Dynamic flow control\n";
    std::cout << "5. History tracking: Complete execution audit trail\n";

    std::cout << "\n=== Example Complete ===\n";

    return 0;
}
