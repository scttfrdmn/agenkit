/**
 * @file planning-pattern.cpp
 * @brief Planning pattern with real LLM (Ollama)
 *
 * Demonstrates:
 * - LLM-generated step-by-step plans
 * - Plan parsing and execution tracking
 * - Progress monitoring
 * - Real planning for complex tasks
 *
 * Setup:
 *   brew install ollama
 *   ollama serve
 *   ollama pull llama3.3
 *   ./build/examples/patterns/planning-pattern
 */

#include <iostream>
#include <memory>
#include "agenkit/patterns/planning.hpp"
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
    print_separator("AgentKit C++ - Planning Pattern with Real LLM");

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

    // Example 1: Project Planning
    print_separator("Example 1: Software Project Planning");
    {
        std::cout << "Creating planning agent with structured prompt...\n\n";

        // Create Ollama planner with system prompt for structured planning
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.5;  // Lower for more consistent planning
        config.system = "You are a project planning assistant. When given a task, "
                        "create a detailed step-by-step plan. Format your response as "
                        "a numbered list with one clear action per line. Each step should "
                        "start with a number followed by a period. Be specific and actionable.";

        auto planner = std::make_shared<adapters::OllamaAgent>(config);

        patterns::PlanningAgent agent(planner, 10);

        std::string task = "Implement a new user authentication system for our web application";
        std::cout << "Task: " << task << "\n\n";
        std::cout << "[Generating plan...]\n\n";

        auto msg = core::Message::with_text("user", task);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Generated Plan ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";

            auto plan = agent.get_plan();
            if (plan.has_value()) {
                std::cout << "Plan Details:\n";
                std::cout << "  Goal: " << plan->goal << "\n";
                std::cout << "  Total steps: " << plan->steps.size() << "\n";
                std::cout << "  Progress: " << plan->get_progress() << "%\n";
                std::cout << "  Status: Planning phase complete\n";
            }
        } else {
            std::cerr << "❌ Error: " << result.unwrap_err().message() << "\n";
        }
    }

    // Example 2: Research Project Planning
    print_separator("Example 2: Research Project Planning");
    {
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.5;
        config.system = "You are a research planning assistant. Create comprehensive "
                        "research plans with clear, actionable steps. Format as a numbered "
                        "list. Include phases like literature review, methodology, data "
                        "collection, analysis, and documentation.";

        auto planner = std::make_shared<adapters::OllamaAgent>(config);
        patterns::PlanningAgent agent(planner, 8);

        std::string task = "Investigate the impact of microservices architecture on system performance";
        std::cout << "Research Task: " << task << "\n\n";
        std::cout << "[Creating research plan...]\n\n";

        auto msg = core::Message::with_text("user", task);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Research Plan ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";

            auto plan = agent.get_plan();
            if (plan.has_value()) {
                std::cout << "✓ " << plan->steps.size() << " step research plan created\n";
            }
        }
    }

    // Example 3: Event Planning
    print_separator("Example 3: Event Planning");
    {
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.7;  // Slightly higher for creative event ideas
        config.system = "You are an event planning specialist. Create detailed plans "
                        "for organizing events. Include logistics, communication, "
                        "preparation, execution, and follow-up phases. Format as numbered "
                        "steps. Be practical and thorough.";

        auto planner = std::make_shared<adapters::OllamaAgent>(config);
        patterns::PlanningAgent agent(planner, 12);

        std::string task = "Organize a company-wide technical conference for 200 people";
        std::cout << "Event: " << task << "\n\n";
        std::cout << "[Planning logistics...]\n\n";

        auto msg = core::Message::with_text("user", task);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Event Plan ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n\n";
        }
    }

    // Example 4: Migration Planning
    print_separator("Example 4: System Migration Planning");
    {
        adapters::OllamaConfig config;
        config.host = "http://localhost:11434";
        config.model = "llama3.3";
        config.temperature = 0.3;  // Very low for risk-averse planning
        config.system = "You are a system migration specialist. Create safe, methodical "
                        "migration plans that minimize risk and downtime. Include preparation, "
                        "testing, rollback procedures, and verification steps. Format as "
                        "numbered list with clear phases.";

        auto planner = std::make_shared<adapters::OllamaAgent>(config);
        patterns::PlanningAgent agent(planner, 10);

        std::string task = "Migrate our monolithic application to a microservices architecture";
        std::cout << "Migration: " << task << "\n\n";
        std::cout << "[Analyzing migration strategy...]\n\n";

        auto msg = core::Message::with_text("user", task);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "=== Migration Plan ===\n\n";
            std::cout << result.unwrap().content_as_str() << "\n";
        }
    }

    // Summary
    print_separator("Key Insights");
    std::cout << "✓ Real LLM Planning: Ollama generates context-aware plans\n";
    std::cout << "✓ System Prompts: Specialize planner for different domains\n";
    std::cout << "✓ Temperature Control: Lower temps for consistent, safe plans\n";
    std::cout << "✓ Step Extraction: Patterns parse LLM output into structured steps\n";
    std::cout << "✓ Progress Tracking: Monitor plan execution status\n";
    std::cout << "✓ Domain Adaptation: Same pattern, different expertise\n";

    print_separator("Example Complete");
    return 0;
}
