/**
 * @file multiagent_example.cpp
 * @brief Example demonstrating Multiagent pattern
 */

#include <iostream>
#include "agenkit/patterns/multiagent.hpp"

using namespace agenkit;

// Specialist agents
class ResearcherAgent : public core::Agent {
public:
    std::string name() const override { return "researcher"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content = message.content_as_str();
        std::string research = "Research findings: AI patterns improve code quality by 40%.";

        auto msg = core::Message::with_text("assistant", research);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

class WriterAgent : public core::Agent {
public:
    std::string name() const override { return "writer"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string content = "Article: AI patterns provide structured approaches "
                            "to building intelligent systems.";

        auto msg = core::Message::with_text("assistant", content);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

class EditorAgent : public core::Agent {
public:
    std::string name() const override { return "editor"; }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        std::string feedback = "Editorial review: Clear structure, "
                              "well-supported claims, ready to publish.";

        auto msg = core::Message::with_text("assistant", feedback);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};

int main() {
    std::cout << "=== Agenkit C++ Multiagent Example ===\n\n";

    // Example 1: MultiAgent Orchestration
    std::cout << "=== Example 1: Multi-Agent Orchestration ===\n";
    {
        patterns::MultiAgentOrchestrator orchestrator;

        auto researcher = std::make_shared<ResearcherAgent>();
        auto writer = std::make_shared<WriterAgent>();
        auto editor = std::make_shared<EditorAgent>();

        orchestrator.register_agent("researcher", researcher);
        orchestrator.register_agent("writer", writer);
        orchestrator.register_agent("editor", editor);

        std::cout << "Registered agents: " << orchestrator.list_agents().size() << "\n";
        std::cout << "Strategy: Sequential\n\n";

        auto msg = core::Message::with_text("user", "Create research article");
        auto result = orchestrator.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Results ===\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";

            auto tasks = orchestrator.get_tasks();
            std::cout << "Tasks completed: " << tasks.size() << "\n";
        }
    }

    // Example 2: Consensus Agent
    std::cout << "\n=== Example 2: Consensus Among Agents ===\n";
    {
        patterns::ConsensusAgent consensus;

        consensus.add_agent(std::make_shared<ResearcherAgent>());
        consensus.add_agent(std::make_shared<WriterAgent>());
        consensus.add_agent(std::make_shared<EditorAgent>());

        std::cout << "Agents in consensus group: " << consensus.agent_count() << "\n\n";

        auto msg = core::Message::with_text("user", "What's the best approach?");
        auto result = consensus.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Consensus ===\n";
            std::cout << result.unwrap().content_as_str() << "\n";
        }
    }

    std::cout << "\n=== Key Insights ===\n";
    std::cout << "1. Orchestration: Multiple agents working sequentially\n";
    std::cout << "2. Consensus: Combining multiple perspectives\n";
    std::cout << "3. Task tracking: Monitor agent execution status\n";
    std::cout << "4. Specialist agents: Each with specific expertise\n";

    std::cout << "\n=== Example Complete ===\n";
    return 0;
}
