/**
 * @file autonomous.cpp
 * @brief Implementation of Autonomous pattern
 */

#include "agenkit/patterns/autonomous.hpp"
#include <algorithm>
#include <sstream>

namespace agenkit {
namespace patterns {

AutonomousAgent::AutonomousAgent(
    const std::string& objective,
    AutonomousConfig config
) : objective_(objective), config_(config) {}

std::string AutonomousAgent::name() const {
    return "autonomous";
}

std::vector<std::string> AutonomousAgent::capabilities() const {
    return {"autonomous", "self-directed", "goal-oriented", "continuous"};
}

std::future<core::Result<core::Message, core::AgentError>>
AutonomousAgent::process(core::Message /* message */) {
    // Autonomous agents don't need messages - they operate independently
    std::string response = "Autonomous agent working on: " + objective_;

    auto msg = core::Message::with_text("assistant", response);
    msg.with_metadata("pattern", "autonomous");
    msg.with_metadata("objective", objective_);
    msg.with_metadata("goal_count", static_cast<int>(goals_.size()));

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(msg)
    );
}

Goal& AutonomousAgent::add_goal(const std::string& description, int priority) {
    goals_.emplace_back(description, priority);
    return goals_.back();
}

AutonomousResult AutonomousAgent::run() {
    AutonomousResult result;
    result.objective = objective_;
    is_running_ = true;

    while (iteration_count_ < config_.max_iterations && is_running_) {
        // Check stop condition
        if (config_.stop_condition && config_.stop_condition()) {
            result.stopped_early = true;
            break;
        }

        // Select next goal to work on
        Goal* goal = select_next_goal();
        if (!goal) {
            // No active goals remaining
            break;
        }

        // Increment counter only when we actually do work
        iteration_count_++;

        // Work on the goal
        std::string iteration_result = work_on_goal(*goal);
        result.iteration_results.push_back(iteration_result);

        // Update progress
        goal->progress += config_.progress_per_iteration;
        if (goal->progress >= 1.0) {
            goal->status = GoalStatus::Completed;
            result.goals_completed++;
        }
    }

    is_running_ = false;
    result.iterations_completed = iteration_count_;

    return result;
}

void AutonomousAgent::stop() {
    is_running_ = false;
}

double AutonomousAgent::get_progress() const {
    if (goals_.empty()) {
        return 0.0;
    }

    double total_progress = 0.0;
    for (const auto& goal : goals_) {
        total_progress += goal.progress;
    }

    return (total_progress / goals_.size()) * 100.0;
}

bool AutonomousAgent::is_running() const {
    return is_running_;
}

const std::vector<Goal>& AutonomousAgent::get_goals() const {
    return goals_;
}

int AutonomousAgent::get_iteration_count() const {
    return iteration_count_;
}

std::string AutonomousAgent::work_on_goal(Goal& goal) {
    // Mock implementation - in production, this would:
    // - Use tools/APIs to accomplish goal
    // - Make decisions about actions
    // - Monitor progress
    // - Adapt strategy based on results

    std::ostringstream result;
    result << "Iteration " << iteration_count_
           << ": Progress on goal '" << goal.description
           << "' (priority " << goal.priority
           << ", progress " << static_cast<int>(goal.progress * 100) << "%)";

    return result.str();
}

Goal* AutonomousAgent::select_next_goal() {
    // Select highest priority active goal
    Goal* selected = nullptr;
    int highest_priority = -1;

    for (auto& goal : goals_) {
        if (goal.status == GoalStatus::Active &&
            goal.priority > highest_priority) {
            selected = &goal;
            highest_priority = goal.priority;
        }
    }

    return selected;
}

} // namespace patterns
} // namespace agenkit
