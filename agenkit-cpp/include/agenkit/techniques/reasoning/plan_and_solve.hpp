/**
 * @file plan_and_solve.hpp
 * @brief Plan-and-Solve Prompting Technique
 *
 * Explicitly separates planning (devising a solution strategy) from solving
 * (executing the strategy). Creates more structured reasoning than pure CoT
 * by forcing an upfront planning phase.
 *
 * Reference: "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning"
 * Lei Wang et al., 2023 - https://arxiv.org/abs/2305.04091
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_PLAN_AND_SOLVE_HPP
#define AGENKIT_TECHNIQUES_REASONING_PLAN_AND_SOLVE_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <functional>
#include <future>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief A single step in a solution plan
 */
struct PlanStep {
    std::string description;
    int order;
    std::vector<int> dependencies;
    int estimated_complexity;
    std::optional<std::string> result;
    bool executed;

    PlanStep(const std::string& desc, int ord)
        : description(desc)
        , order(ord)
        , estimated_complexity(1)
        , executed(false) {}
};

/**
 * @brief A complete solution plan with steps
 */
struct Plan {
    std::vector<PlanStep> steps;
    std::string problem;
    std::optional<std::string> strategy;
    bool validated;
    std::optional<std::string> validation_notes;

    Plan(const std::string& prob)
        : problem(prob)
        , validated(false) {}
};

// Function types for custom planner and solver
using PlannerFunc = std::function<Plan(const std::string&)>;
using SolverFunc = std::function<std::string(const PlanStep&, const std::vector<std::string>&)>;

/**
 * @brief Configuration options for PlanAndSolve agent
 */
struct PlanAndSolveConfig {
    std::optional<PlannerFunc> planner;
    std::optional<SolverFunc> solver;
    bool validate_plan = true;
    bool allow_replanning = false;
};

/**
 * @brief Plan-and-Solve reasoning technique
 *
 * Implements two-phase reasoning: planning (decomposing problem into steps)
 * then execution (solving each step sequentially).
 *
 * @example
 * @code
 * auto base_agent = std::make_shared<MyAgent>();
 * PlanAndSolveConfig config;
 * config.validate_plan = true;
 *
 * auto pas = std::make_unique<PlanAndSolveAgent>(base_agent, config);
 * auto result = pas->process(message).get();
 * @endcode
 */
class PlanAndSolveAgent : public core::Agent {
public:
    /**
     * @brief Constructor
     *
     * @param agent Base agent for generating responses
     * @param config Configuration options
     */
    PlanAndSolveAgent(
        std::shared_ptr<core::Agent> agent,
        const PlanAndSolveConfig& config = PlanAndSolveConfig());

    std::string name() const override;
    std::vector<std::string> capabilities() const override;
    std::future<core::Result<core::Message>> process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    std::optional<PlannerFunc> planner_;
    std::optional<SolverFunc> solver_;
    bool validate_plan_;
    bool allow_replanning_;

    std::future<core::Result<std::string>> llm_call(const std::string& prompt);
    std::future<core::Result<Plan>> create_plan(const std::string& problem);
    std::future<core::Result<void>> validate(Plan& plan);
    std::string format_plan(const Plan& plan);
    std::future<core::Result<std::string>> execute_step(
        const PlanStep& step,
        const std::vector<std::string>& previous_results);
    std::future<core::Result<std::vector<std::string>>> execute_plan(Plan& plan);
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_PLAN_AND_SOLVE_HPP
