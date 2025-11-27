/**
 * @file autonomous_example.cpp
 * @brief Demonstrates the Autonomous agent pattern
 *
 * This example shows how to create agents that operate independently,
 * setting their own goals and working toward objectives with minimal
 * human intervention.
 */

#include "agenkit/patterns/autonomous.hpp"
#include "agenkit/core/message.hpp"
#include <iostream>
#include <iomanip>

using namespace agenkit;
using namespace agenkit::patterns;

void print_separator() {
    std::cout << std::string(70, '=') << "\n";
}

void print_goals(const std::vector<Goal>& goals) {
    std::cout << "\nCurrent Goals:\n";
    for (size_t i = 0; i < goals.size(); ++i) {
        std::cout << "  " << (i + 1) << ". " << goals[i].description;
        std::cout << " (Priority: " << goals[i].priority;
        std::cout << ", Progress: " << std::fixed << std::setprecision(0)
                  << (goals[i].progress * 100) << "%";

        std::cout << ", Status: ";
        switch (goals[i].status) {
            case GoalStatus::Active:
                std::cout << "Active";
                break;
            case GoalStatus::Completed:
                std::cout << "Completed";
                break;
            case GoalStatus::Abandoned:
                std::cout << "Abandoned";
                break;
        }
        std::cout << ")\n";
    }
}

void print_result(const AutonomousResult& result) {
    std::cout << "\nExecution Summary:\n";
    std::cout << "  Objective: " << result.objective << "\n";
    std::cout << "  Iterations: " << result.iterations_completed << "\n";
    std::cout << "  Goals Completed: " << result.goals_completed << "\n";
    std::cout << "  Stopped Early: " << (result.stopped_early ? "Yes" : "No") << "\n";

    if (!result.iteration_results.empty()) {
        std::cout << "\nIteration Results:\n";
        for (const auto& iter_result : result.iteration_results) {
            std::cout << "  • " << iter_result << "\n";
        }
    }
}

/**
 * Example 1: Research Assistant
 * An autonomous agent that conducts research with multiple goals
 */
void example_research_assistant() {
    print_separator();
    std::cout << "Example 1: Autonomous Research Assistant\n";
    print_separator();

    // Configure autonomous operation
    AutonomousConfig config;
    config.max_iterations = 8;
    config.progress_per_iteration = 0.3;

    // Create agent with high-level objective
    AutonomousAgent agent("Research machine learning trends for 2024", config);

    // Add research goals with priorities
    agent.add_goal("Collect recent ML research papers", 3);
    agent.add_goal("Analyze breakthrough algorithms", 2);
    agent.add_goal("Identify emerging applications", 2);
    agent.add_goal("Summarize industry impact", 1);

    std::cout << "\nObjective: Research machine learning trends for 2024\n";
    print_goals(agent.get_goals());

    std::cout << "\nStarting autonomous research...\n";

    // Run autonomously
    auto result = agent.run();

    print_result(result);

    std::cout << "\nFinal Progress: " << std::fixed << std::setprecision(1)
              << agent.get_progress() << "%\n";
    print_goals(agent.get_goals());
}

/**
 * Example 2: Content Creator
 * An agent that autonomously generates content with stop condition
 */
void example_content_creator() {
    print_separator();
    std::cout << "\nExample 2: Autonomous Content Creator\n";
    print_separator();

    AutonomousConfig config;
    config.max_iterations = 20;
    config.progress_per_iteration = 0.25;

    // Stop when quality threshold is met
    int iterations = 0;
    config.stop_condition = [&iterations]() {
        // Simulate quality check after 5 iterations
        return ++iterations >= 5;
    };

    AutonomousAgent agent("Create blog post series", config);

    agent.add_goal("Draft introduction post", 3);
    agent.add_goal("Write technical deep dive", 2);
    agent.add_goal("Create tutorial examples", 2);
    agent.add_goal("Write conclusion post", 1);

    std::cout << "\nObjective: Create blog post series\n";
    std::cout << "Stop Condition: Quality threshold met\n";
    print_goals(agent.get_goals());

    std::cout << "\nStarting content creation...\n";

    auto result = agent.run();

    print_result(result);

    if (result.stopped_early) {
        std::cout << "\n✓ Stopped early due to quality threshold\n";
    }
}

/**
 * Example 3: Task Automation
 * An agent that automates multiple maintenance tasks
 */
void example_task_automation() {
    print_separator();
    std::cout << "\nExample 3: Autonomous Task Automation\n";
    print_separator();

    AutonomousConfig config;
    config.max_iterations = 10;
    config.progress_per_iteration = 0.5;  // Fast progress for automation

    AutonomousAgent agent("Daily system maintenance", config);

    agent.add_goal("Check system health", 3);
    agent.add_goal("Update dependencies", 2);
    agent.add_goal("Clean temporary files", 2);
    agent.add_goal("Generate status report", 1);

    std::cout << "\nObjective: Daily system maintenance\n";
    print_goals(agent.get_goals());

    std::cout << "\nStarting automated maintenance...\n";

    auto result = agent.run();

    print_result(result);

    std::cout << "\nMaintenance Status:\n";
    for (const auto& goal : agent.get_goals()) {
        std::cout << "  ";
        if (goal.status == GoalStatus::Completed) {
            std::cout << "✓ ";
        } else {
            std::cout << "⧗ ";
        }
        std::cout << goal.description << "\n";
    }
}

/**
 * Example 4: Continuous Monitoring
 * Shows autonomous agent pattern for continuous operations
 */
void example_continuous_monitoring() {
    print_separator();
    std::cout << "\nExample 4: Continuous Monitoring Agent\n";
    print_separator();

    AutonomousConfig config;
    config.max_iterations = 15;
    config.progress_per_iteration = 0.15;

    AutonomousAgent agent("Monitor application health", config);

    agent.add_goal("Check API endpoints", 3);
    agent.add_goal("Verify database connectivity", 3);
    agent.add_goal("Monitor resource usage", 2);
    agent.add_goal("Analyze error logs", 2);
    agent.add_goal("Generate health report", 1);

    std::cout << "\nObjective: Monitor application health\n";
    std::cout << "Mode: Continuous monitoring with priority-based checks\n";
    print_goals(agent.get_goals());

    std::cout << "\nStarting monitoring...\n";

    auto result = agent.run();

    print_result(result);

    std::cout << "\nMonitoring Complete:\n";
    std::cout << "  Total Checks: " << result.iterations_completed << "\n";
    std::cout << "  Components Verified: " << result.goals_completed << "\n";
}

/**
 * Example 5: Using process() method
 * Shows how to use the Agent interface
 */
void example_agent_interface() {
    print_separator();
    std::cout << "\nExample 5: Agent Interface Usage\n";
    print_separator();

    AutonomousAgent agent("Complete project deliverables");

    agent.add_goal("Design architecture", 3);
    agent.add_goal("Implement core features", 2);
    agent.add_goal("Write tests", 2);
    agent.add_goal("Create documentation", 1);

    std::cout << "\nUsing Agent interface:\n";
    std::cout << "  Name: " << agent.name() << "\n";

    std::cout << "  Capabilities:\n";
    for (const auto& cap : agent.capabilities()) {
        std::cout << "    - " << cap << "\n";
    }

    // Process a message
    auto msg = core::Message::with_text("user", "What is your current status?");
    auto future = agent.process(msg);
    auto result = future.get();

    if (result.is_ok()) {
        auto response = result.unwrap();
        std::cout << "\n  Status Response:\n    " << response.content_as_str() << "\n";

        std::cout << "\n  Metadata:\n";
        std::cout << "    Pattern: " << response.metadata()["pattern"] << "\n";
        std::cout << "    Objective: " << response.metadata()["objective"] << "\n";
        std::cout << "    Goals: " << response.metadata()["goal_count"] << "\n";
    }
}

int main() {
    std::cout << "\n";
    std::cout << "╔═══════════════════════════════════════════════════════════════════╗\n";
    std::cout << "║         Autonomous Agent Pattern - Comprehensive Examples        ║\n";
    std::cout << "╚═══════════════════════════════════════════════════════════════════╝\n";

    example_research_assistant();
    example_content_creator();
    example_task_automation();
    example_continuous_monitoring();
    example_agent_interface();

    print_separator();
    std::cout << "\nKey Takeaways:\n";
    std::cout << "  • Autonomous agents operate independently toward objectives\n";
    std::cout << "  • Goals are prioritized and worked on systematically\n";
    std::cout << "  • Progress is tracked automatically for each goal\n";
    std::cout << "  • Stop conditions provide fine-grained control\n";
    std::cout << "  • Ideal for background tasks, monitoring, and automation\n";
    print_separator();

    return 0;
}
