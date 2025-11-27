/**
 * @file planning.hpp
 * @brief Planning agent pattern for multi-step task execution
 *
 * Implements agents that create and execute plans by breaking down complex
 * tasks into smaller, manageable steps.
 */

#ifndef AGENKIT_PATTERNS_PLANNING_HPP
#define AGENKIT_PATTERNS_PLANNING_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <vector>
#include <string>
#include <memory>
#include <optional>

namespace agenkit {
namespace patterns {

/**
 * @brief Status of a plan step
 */
enum class StepStatus {
    Pending,     ///< Step not yet started
    InProgress,  ///< Step currently executing
    Completed,   ///< Step completed successfully
    Failed,      ///< Step failed
    Skipped      ///< Step skipped
};

/**
 * @brief A single step in a plan
 */
struct PlanStep {
    std::string description;
    int step_number{0};
    StepStatus status{StepStatus::Pending};
    std::optional<std::string> result;
    std::optional<std::string> error;
};

/**
 * @brief A plan consisting of multiple steps
 */
struct Plan {
    std::string goal;
    std::vector<PlanStep> steps;

    /**
     * @brief Check if all steps are completed or skipped
     * @return True if plan is complete
     */
    bool is_complete() const;

    /**
     * @brief Check if any steps failed
     * @return True if any step failed
     */
    bool has_failures() const;

    /**
     * @brief Get completion progress as percentage
     * @return Progress (0.0 to 100.0)
     */
    double get_progress() const;
};

/**
 * @brief Agent that creates and executes plans for complex tasks
 *
 * The PlanningAgent uses an underlying agent to create a plan, then
 * executes each step sequentially, tracking progress and handling failures.
 *
 * Features:
 * - Plan creation from task description
 * - Step-by-step execution
 * - Progress tracking
 * - Failure handling
 *
 * @example
 * @code
 * auto planner = std::make_shared<MyPlannerLLM>();
 * PlanningAgent agent(planner);
 *
 * auto msg = Message::with_text("user", "Organize a team event");
 * auto result = agent.process(std::move(msg)).get();
 * // Agent creates plan with steps and executes them
 *
 * auto plan = agent.get_plan();
 * std::cout << "Progress: " << plan->get_progress() << "%\n";
 * @endcode
 */
class PlanningAgent : public core::Agent {
public:
    /**
     * @brief Construct a planning agent
     * @param planner Agent that creates plans
     * @param max_steps Maximum steps in a plan (default: 10)
     */
    explicit PlanningAgent(
        std::shared_ptr<core::Agent> planner,
        int max_steps = 10
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get the current plan
     * @return Optional Plan if one exists
     */
    std::optional<Plan> get_plan() const;

    /**
     * @brief Get current plan progress as percentage
     * @return Progress (0.0 to 100.0)
     */
    double get_progress() const;

    /**
     * @brief Clear current plan
     */
    void clear_plan();

private:
    std::shared_ptr<core::Agent> planner_;
    int max_steps_;
    std::optional<Plan> current_plan_;

    /**
     * @brief Create a plan from task description
     * @param task Task description
     * @return Plan with steps
     */
    Plan create_plan(const std::string& task);

    /**
     * @brief Parse plan from LLM response
     * @param response LLM response text
     * @param goal Original goal
     * @return Parsed plan
     */
    Plan parse_plan(const std::string& response, const std::string& goal);

    /**
     * @brief Execute all steps in the plan
     * @param plan Plan to execute
     * @return Execution summary
     */
    std::string execute_plan(Plan& plan);

    /**
     * @brief Execute a single step (mock implementation)
     * @param step Step to execute
     * @return Result string
     */
    std::string execute_step(PlanStep& step);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_PLANNING_HPP
