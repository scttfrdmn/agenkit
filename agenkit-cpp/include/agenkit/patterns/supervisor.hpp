/**
 * @file supervisor.hpp
 * @brief Supervisor hierarchical coordination pattern
 *
 * This module provides the Supervisor pattern for hierarchical coordination where a central
 * supervisor agent plans task decomposition, delegates to specialist agents,
 * and synthesizes their results into a final response.
 */

#ifndef AGENKIT_PATTERNS_SUPERVISOR_HPP
#define AGENKIT_PATTERNS_SUPERVISOR_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <vector>
#include <string>
#include <map>
#include <unordered_map>

namespace agenkit {
namespace patterns {

/**
 * @brief Represents a decomposed task for a specialist agent
 */
struct Subtask {
    /// Type identifies which specialist should handle this subtask
    std::string type;
    /// Message is the input for the specialist
    core::Message message;
    /// Metadata contains additional task information
    nlohmann::json metadata;

    Subtask(std::string t, core::Message msg)
        : type(std::move(t))
        , message(std::move(msg))
        , metadata(nlohmann::json::object())
    {}
};

/**
 * @brief Planner agent interface for task decomposition and synthesis
 *
 * The planner receives the initial message and breaks it down into subtasks
 * for specialist agents. After specialists complete their work, the planner
 * synthesizes their results into a final response.
 */
class PlannerAgent : public core::Agent {
public:
    /**
     * @brief Plan decomposes a message into subtasks for specialists
     * @param message Input message to decompose
     * @return Result containing vector of subtasks or error
     */
    virtual core::Result<std::vector<Subtask>, core::AgentError>
    plan(const core::Message& message) = 0;

    /**
     * @brief Synthesize combines specialist results into final response
     * @param original Original input message
     * @param results Map of specialist results keyed by specialist type
     * @return Result containing synthesized message or error
     */
    virtual core::Result<core::Message, core::AgentError>
    synthesize(
        const core::Message& original,
        const std::unordered_map<std::string, core::Message>& results
    ) = 0;
};

/**
 * @brief Supervisor agent for hierarchical planning and coordination
 *
 * The SupervisorAgent coordinates specialist agents through hierarchical planning.
 * The supervisor uses a planner agent to decompose complex tasks into subtasks,
 * delegates each subtask to an appropriate specialist, and synthesizes the
 * specialist results into a coherent final response.
 *
 * Key concepts:
 * - Central planner/supervisor for coordination
 * - Specialist agents for domain-specific tasks
 * - Task decomposition and delegation
 * - Result synthesis from specialist outputs
 *
 * Performance characteristics:
 * - Time: O(planning + max(specialist) + synthesis)
 * - Memory: O(n specialists * message size)
 * - Hierarchical execution model
 *
 * Example use cases:
 * - Software development: planner coordinates coder, tester, reviewer
 * - Research: planner coordinates searcher, analyzer, writer
 * - Data processing: planner coordinates extractor, transformer, validator
 * - Customer service: planner coordinates billing, technical, account specialists
 *
 * The supervisor pattern is ideal when tasks have clear domain boundaries
 * and benefit from specialized expertise.
 *
 * @example
 * @code
 * auto planner = std::make_shared<MyPlannerAgent>();
 * std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists = {
 *     {"coder", std::make_shared<CoderAgent>()},
 *     {"tester", std::make_shared<TesterAgent>()},
 *     {"reviewer", std::make_shared<ReviewerAgent>()}
 * };
 *
 * SupervisorAgent supervisor(planner, specialists);
 * auto msg = core::Message::with_text("user", "Build a new feature");
 * auto result = supervisor.process(std::move(msg)).get();
 * @endcode
 */
class SupervisorAgent : public core::Agent {
public:
    /**
     * @brief Construct a supervisor agent
     * @param planner Agent responsible for planning and synthesis
     * @param specialists Map of specialist agents keyed by their domain/type
     * @throws std::invalid_argument if planner is null or specialists is empty
     */
    SupervisorAgent(
        std::shared_ptr<PlannerAgent> planner,
        std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<PlannerAgent> planner_;
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> specialists_;
};

/**
 * @brief Simple planner implementation for basic use cases
 *
 * This planner uses an LLM agent to handle both planning and synthesis.
 * For planning, it prompts the LLM to decompose the task. For synthesis,
 * it prompts the LLM to combine results.
 *
 * For production use, consider implementing a custom PlannerAgent with
 * domain-specific planning and synthesis logic.
 */
class SimplePlanner : public PlannerAgent {
public:
    /**
     * @brief Create a basic planner using an LLM agent
     * @param agent Underlying agent for planning and synthesis
     */
    explicit SimplePlanner(std::shared_ptr<core::Agent> agent);

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    core::Result<std::vector<Subtask>, core::AgentError>
    plan(const core::Message& message) override;

    core::Result<core::Message, core::AgentError>
    synthesize(
        const core::Message& original,
        const std::unordered_map<std::string, core::Message>& results
    ) override;

private:
    std::shared_ptr<core::Agent> agent_;
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_SUPERVISOR_HPP
