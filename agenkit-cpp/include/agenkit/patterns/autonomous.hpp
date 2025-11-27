/**
 * @file autonomous.hpp
 * @brief Autonomous agent pattern for self-directed operation
 *
 * Implements agents that operate independently with minimal human intervention,
 * setting their own goals and making decisions about actions to take.
 */

#ifndef AGENKIT_PATTERNS_AUTONOMOUS_HPP
#define AGENKIT_PATTERNS_AUTONOMOUS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <vector>
#include <string>
#include <memory>
#include <functional>
#include <optional>
#include <chrono>

namespace agenkit {
namespace patterns {

/**
 * @brief Status of a goal
 */
enum class GoalStatus {
    Active,      ///< Goal is being pursued
    Completed,   ///< Goal has been achieved
    Abandoned    ///< Goal was abandoned
};

/**
 * @brief A goal the autonomous agent is pursuing
 */
struct Goal {
    std::string description;
    int priority{1};
    GoalStatus status{GoalStatus::Active};
    double progress{0.0};  ///< Progress from 0.0 to 1.0
    std::chrono::system_clock::time_point created_at;

    Goal(const std::string& desc, int prio = 1)
        : description(desc), priority(prio),
          created_at(std::chrono::system_clock::now()) {}
};

/**
 * @brief Stop condition function type
 *
 * Returns true if the agent should stop
 */
using StopCondition = std::function<bool()>;

/**
 * @brief Configuration for autonomous agents
 */
struct AutonomousConfig {
    /// Maximum iterations before stopping
    int max_iterations{10};

    /// Optional stop condition callback
    StopCondition stop_condition{nullptr};

    /// Progress increment per iteration (0.0 to 1.0)
    double progress_per_iteration{0.2};
};

/**
 * @brief Result from autonomous agent execution
 */
struct AutonomousResult {
    std::string objective;
    int iterations_completed{0};
    int goals_completed{0};
    std::vector<std::string> iteration_results;
    bool stopped_early{false};
};

/**
 * @brief Agent that operates autonomously toward objectives
 *
 * The AutonomousAgent runs independently, setting its own goals based on
 * high-level objectives, making decisions about actions, and monitoring
 * progress until the objective is met or stopped.
 *
 * Features:
 * - Self-directed goal setting
 * - Autonomous decision making
 * - Progress monitoring
 * - Stop conditions
 * - Multiple goals with priorities
 *
 * @example
 * @code
 * AutonomousConfig config;
 * config.max_iterations = 10;
 * config.stop_condition = []() { return should_stop(); };
 *
 * AutonomousAgent agent("Research AI trends", config);
 * agent.add_goal("Collect recent papers", 2);
 * agent.add_goal("Analyze trends", 1);
 *
 * auto result = agent.run();
 * std::cout << "Completed " << result.goals_completed << " goals\n";
 * @endcode
 */
class AutonomousAgent : public core::Agent {
public:
    /**
     * @brief Construct an autonomous agent
     * @param objective High-level objective
     * @param config Configuration for autonomous operation
     */
    explicit AutonomousAgent(
        const std::string& objective,
        AutonomousConfig config = AutonomousConfig{}
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Add a goal for the agent to pursue
     * @param description Goal description
     * @param priority Priority level (higher = more important)
     * @return Reference to the created goal
     */
    Goal& add_goal(const std::string& description, int priority = 1);

    /**
     * @brief Run the autonomous agent
     * @return Result of autonomous execution
     */
    AutonomousResult run();

    /**
     * @brief Stop the autonomous agent
     */
    void stop();

    /**
     * @brief Get overall progress (0.0 to 100.0)
     * @return Progress percentage
     */
    double get_progress() const;

    /**
     * @brief Check if agent is currently running
     * @return True if running
     */
    bool is_running() const;

    /**
     * @brief Get all goals
     * @return Vector of goals
     */
    const std::vector<Goal>& get_goals() const;

    /**
     * @brief Get number of iterations completed
     * @return Iteration count
     */
    int get_iteration_count() const;

private:
    std::string objective_;
    AutonomousConfig config_;
    std::vector<Goal> goals_;
    int iteration_count_{0};
    bool is_running_{false};

    /**
     * @brief Work on a specific goal
     * @param goal Goal to work on
     * @return Result string
     */
    std::string work_on_goal(Goal& goal);

    /**
     * @brief Select next goal to work on
     * @return Pointer to goal, or nullptr if none available
     */
    Goal* select_next_goal();
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_AUTONOMOUS_HPP
