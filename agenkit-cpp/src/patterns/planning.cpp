/**
 * @file planning.cpp
 * @brief Implementation of Planning pattern
 */

#include "agenkit/patterns/planning.hpp"
#include <sstream>
#include <stdexcept>
#include <algorithm>

namespace agenkit {
namespace patterns {

// Plan implementation

bool Plan::is_complete() const {
    return std::all_of(steps.begin(), steps.end(), [](const PlanStep& step) {
        return step.status == StepStatus::Completed || step.status == StepStatus::Skipped;
    });
}

bool Plan::has_failures() const {
    return std::any_of(steps.begin(), steps.end(), [](const PlanStep& step) {
        return step.status == StepStatus::Failed;
    });
}

double Plan::get_progress() const {
    if (steps.empty()) return 0.0;

    int completed = std::count_if(steps.begin(), steps.end(), [](const PlanStep& step) {
        return step.status == StepStatus::Completed || step.status == StepStatus::Skipped;
    });

    return (static_cast<double>(completed) / steps.size()) * 100.0;
}

// PlanningAgent implementation

PlanningAgent::PlanningAgent(
    std::shared_ptr<core::Agent> planner,
    int max_steps
) : planner_(planner), max_steps_(max_steps) {
    if (!planner_) {
        throw std::invalid_argument("Planner cannot be null");
    }
}

std::string PlanningAgent::name() const {
    return "planning";
}

std::vector<std::string> PlanningAgent::capabilities() const {
    return {"planning", "multi-step", "task-decomposition", "execution"};
}

std::future<core::Result<core::Message, core::AgentError>>
PlanningAgent::process(core::Message message) {
    std::string task = message.content_as_str();

    // Create plan
    auto plan = create_plan(task);
    current_plan_ = plan;

    // Execute plan
    std::string result = execute_plan(plan);
    current_plan_ = plan; // Update with execution results

    // Create response
    std::ostringstream response;
    response << "Task completed.\n\n";
    response << "Goal: " << plan.goal << "\n\n";

    int completed = std::count_if(plan.steps.begin(), plan.steps.end(), [](const PlanStep& step) {
        return step.status == StepStatus::Completed;
    });

    response << "Steps completed: " << completed << "/" << plan.steps.size() << "\n\n";
    response << "Result:\n" << result;

    auto msg = core::Message::with_text("assistant", response.str());
    msg.with_metadata("pattern", "planning");
    msg.with_metadata("steps_total", static_cast<int>(plan.steps.size()));
    msg.with_metadata("steps_completed", completed);
    msg.with_metadata("progress", plan.get_progress());

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(msg)
    );
}

std::optional<Plan> PlanningAgent::get_plan() const {
    return current_plan_;
}

double PlanningAgent::get_progress() const {
    if (current_plan_.has_value()) {
        return current_plan_.value().get_progress();
    }
    return 0.0;
}

void PlanningAgent::clear_plan() {
    current_plan_.reset();
}

Plan PlanningAgent::create_plan(const std::string& task) {
    // Ask planner to create a plan
    std::string prompt = "Create a step-by-step plan for: " + task;
    auto msg = core::Message::with_text("user", prompt);

    auto future = planner_->process(std::move(msg));
    auto result = future.get();

    if (result.is_err()) {
        // Return empty plan on error
        return Plan{task, {}};
    }

    auto response = result.unwrap();
    return parse_plan(response.content_as_str(), task);
}

Plan PlanningAgent::parse_plan(const std::string& response, const std::string& goal) {
    Plan plan;
    plan.goal = goal;

    // Simple parsing: look for numbered steps
    std::istringstream stream(response);
    std::string line;
    int step_number = 0;

    while (std::getline(stream, line) && step_number < max_steps_) {
        // Trim whitespace
        size_t start = line.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) continue;

        line = line.substr(start);

        // Check if line starts with number
        if (!line.empty() && std::isdigit(line[0])) {
            // Remove leading number and punctuation
            size_t content_start = line.find_first_not_of("0123456789.)");
            if (content_start != std::string::npos) {
                std::string description = line.substr(content_start);

                // Trim again
                start = description.find_first_not_of(" \t");
                if (start != std::string::npos) {
                    description = description.substr(start);

                    if (!description.empty()) {
                        PlanStep step;
                        step.description = description;
                        step.step_number = step_number;
                        step.status = StepStatus::Pending;
                        plan.steps.push_back(step);
                        step_number++;
                    }
                }
            }
        }
    }

    return plan;
}

std::string PlanningAgent::execute_plan(Plan& plan) {
    std::ostringstream results;

    for (auto& step : plan.steps) {
        step.status = StepStatus::InProgress;

        // Execute step (mock implementation)
        try {
            std::string result = execute_step(step);
            step.result = result;
            step.status = StepStatus::Completed;

            results << "Step " << (step.step_number + 1) << ": "
                   << step.description << " ✓\n";
        } catch (const std::exception& e) {
            step.error = e.what();
            step.status = StepStatus::Failed;

            results << "Step " << (step.step_number + 1) << ": "
                   << step.description << " ✗ (" << e.what() << ")\n";
        }
    }

    // Add summary
    if (plan.is_complete()) {
        results << "\nPlan completed successfully ("
               << plan.get_progress() << "%)";
    } else if (plan.has_failures()) {
        results << "\nPlan failed ("
               << plan.get_progress() << "% complete)";
    } else {
        results << "\nPlan partially completed ("
               << plan.get_progress() << "%)";
    }

    return results.str();
}

std::string PlanningAgent::execute_step(PlanStep& step) {
    // Mock execution - in production, this would:
    // - Use tools/APIs
    // - Delegate to other agents
    // - Interact with external systems
    return "Completed: " + step.description;
}

} // namespace patterns
} // namespace agenkit
