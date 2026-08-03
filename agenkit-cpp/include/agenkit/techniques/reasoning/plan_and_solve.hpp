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
#include "agenkit/core/call_options.hpp"
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
class PlanAndSolveAgent : public core::Agent, public core::OptionsAgent {
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
    std::future<core::Result<core::Message, core::AgentError>> process(core::Message message) override;

    /**
     * @brief Process a message, forwarding per-call options to the wrapped agent
     *
     * Same as process(), except that `options` reaches the wrapped agent if it
     * honours them — on planning, validation, every step execution, and every
     * call in the replanning branch. process() is this method with an empty
     * option set.
     *
     * @param message Input message with problem content
     * @param options Per-call options to forward
     * @return Future with result containing response with metadata (see process())
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process_with(core::Message message, const core::CallOptions& options) override;

private:
    std::shared_ptr<core::Agent> agent_;
    std::optional<PlannerFunc> planner_;
    std::optional<SolverFunc> solver_;
    bool validate_plan_;
    bool allow_replanning_;

    std::future<core::Result<std::string, core::AgentError>> llm_call(
        const std::string& prompt,
        const core::CallOptions& options);
    std::future<core::Result<Plan, core::AgentError>> create_plan(
        const std::string& problem,
        const core::CallOptions& options);
    std::future<core::Result<void, core::AgentError>> validate(
        Plan& plan,
        const core::CallOptions& options);
    std::string format_plan(const Plan& plan);
    std::future<core::Result<std::string, core::AgentError>> execute_step(
        const PlanStep& step,
        const std::vector<std::string>& previous_results,
        const core::CallOptions& options);
    std::future<core::Result<std::vector<std::string>, core::AgentError>> execute_plan(
        Plan& plan,
        const core::CallOptions& options);
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_PLAN_AND_SOLVE_HPP
