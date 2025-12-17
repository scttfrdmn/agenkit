/**
 * @file multiagent-pattern.cpp
 * @brief Multiagent pattern with real LLMs (Ollama)
 *
 * Demonstrates:
 * - Multiple specialized LLM agents collaborating
 * - Sequential orchestration with real LLMs
 * - Consensus building across agents
 * - System prompts for agent specialization
 *
 * Setup:
 *   brew install ollama
 *   ollama serve
 *   ollama pull llama3.3
 *   ./build/examples/patterns/multiagent-pattern
 */

#include <iostream>
#include <memory>
#include "agenkit/patterns/multiagent.hpp"
#include "agenkit/adapters/ollama_agent.hpp"
#include "agenkit/core/message.hpp"

using namespace agenkit;

/**
 * Create a specialized Ollama agent with custom system prompt
 */
std::shared_ptr<adapters::OllamaAgent> create_specialist(
    const std::string& role,
    const std::string& system_prompt
) {
    adapters::OllamaConfig config;
    config.host = "http://localhost:11434";
    config.model = "llama3.3";
    config.temperature = 0.7;
    config.system = system_prompt;

    return std::make_shared<adapters::OllamaAgent>(config);
}

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
    print_separator("AgentKit C++ - Multiagent Pattern with Real LLMs");

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

    // Example 1: Collaborative Research Team
    print_separator("Example 1: Collaborative Research Team");
    {
        std::cout << "Creating specialist agents with custom system prompts...\n\n";

        // Create specialized agents
        auto researcher = create_specialist(
            "researcher",
            "You are a research specialist. When given a topic, provide "
            "3-4 key research findings with data and statistics. Be concise "
            "and factual. Focus on recent developments."
        );

        auto writer = create_specialist(
            "writer",
            "You are a technical writer. Take research findings and write "
            "a clear, engaging article summary. Use professional tone. "
            "Keep it under 100 words."
        );

        auto editor = create_specialist(
            "editor",
            "You are an editor. Review the content and provide brief "
            "feedback on clarity, structure, and impact. Give 2-3 specific "
            "suggestions for improvement."
        );

        // Create orchestrator
        patterns::MultiAgentOrchestrator orchestrator;
        orchestrator.register_agent("researcher", researcher);
        orchestrator.register_agent("writer", writer);
        orchestrator.register_agent("editor", editor);

        std::cout << "Registered " << orchestrator.list_agents().size()
                  << " specialist agents\n";
        std::cout << "Strategy: Sequential execution\n\n";

        // Execute collaborative task
        std::string topic = "AI agent patterns in software engineering";
        std::cout << "Topic: " << topic << "\n\n";
        std::cout << "Processing through pipeline: Researcher → Writer → Editor\n\n";

        auto msg = core::Message::with_text("user",
            "Research and write about: " + topic);

        std::cout << "[Running orchestration...]\n\n";
        auto result = orchestrator.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Final Output ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";

            auto tasks = orchestrator.get_tasks();
            std::cout << "✓ Tasks completed: " << tasks.size() << "\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
        }
    }

    // Example 2: Consensus Decision Making
    print_separator("Example 2: Consensus Decision Making");
    {
        std::cout << "Creating agents with different perspectives...\n\n";

        auto pragmatist = create_specialist(
            "pragmatist",
            "You are a pragmatic engineer. When asked for opinions, focus "
            "on practical concerns: implementation complexity, maintenance, "
            "and real-world feasibility. Be skeptical but constructive."
        );

        auto innovator = create_specialist(
            "innovator",
            "You are an innovation advocate. When asked for opinions, focus "
            "on new technologies, cutting-edge approaches, and future "
            "potential. Be optimistic and forward-thinking."
        );

        auto realist = create_specialist(
            "realist",
            "You are a balanced realist. When asked for opinions, weigh "
            "both pros and cons. Consider team skills, timeline, and "
            "business value. Aim for the middle ground."
        );

        patterns::ConsensusAgent consensus;
        consensus.add_agent(pragmatist);
        consensus.add_agent(innovator);
        consensus.add_agent(realist);

        std::cout << "Agents in consensus group: " << consensus.agent_count() << "\n\n";

        std::string question = "Should we use microservices or monolith for a new startup project?";
        std::cout << "Question: " << question << "\n\n";
        std::cout << "[Gathering perspectives from all agents...]\n\n";

        auto msg = core::Message::with_text("user", question + " Answer in 2-3 sentences.");
        auto result = consensus.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Consensus View ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n";
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
        }
    }

    // Summary
    print_separator("Key Insights");
    std::cout << "✓ Orchestration: Agents work sequentially in a pipeline\n";
    std::cout << "✓ Specialization: Each agent has unique expertise via system prompts\n";
    std::cout << "✓ Consensus: Multiple perspectives combined into unified view\n";
    std::cout << "✓ Real LLMs: Using Ollama for actual intelligence (not mocks)\n";
    std::cout << "✓ Collaboration: Complex tasks decomposed across specialists\n";

    print_separator("Example Complete");
    return 0;
}
