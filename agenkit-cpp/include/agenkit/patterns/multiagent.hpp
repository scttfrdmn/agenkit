/**
 * @file multiagent.hpp
 * @brief Multi-agent collaboration pattern
 *
 * This module provides patterns for multiple agents working together through
 * coordination, delegation, and consensus mechanisms.
 */

#ifndef AGENKIT_PATTERNS_MULTIAGENT_HPP
#define AGENKIT_PATTERNS_MULTIAGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <map>
#include <vector>
#include <string>
#include <memory>
#include <optional>

namespace agenkit {
namespace patterns {

/**
 * @brief Execution strategy for multi-agent orchestration
 */
enum class MultiAgentStrategy {
    Sequential,  ///< Execute agents one after another
    Parallel,    ///< Execute agents concurrently (future enhancement)
    Delegate     ///< Delegate to specialist agents based on task
};

/**
 * @brief Status of an agent task
 */
enum class TaskStatus {
    Pending,     ///< Task not yet started
    InProgress,  ///< Task currently executing
    Completed,   ///< Task completed successfully
    Failed       ///< Task failed with error
};

/**
 * @brief A task assigned to an agent
 */
struct AgentTask {
    std::string agent_name;
    std::string description;
    std::optional<std::string> result;
    TaskStatus status{TaskStatus::Pending};
    std::optional<std::string> error;
};

/**
 * @brief Orchestrates multiple agents working together
 *
 * The MultiAgentOrchestrator coordinates multiple agents to work on tasks,
 * either sequentially or in parallel, combining their results.
 *
 * Features:
 * - Agent registration and management
 * - Sequential and parallel execution strategies
 * - Task tracking and status monitoring
 * - Result aggregation
 *
 * @example
 * @code
 * MultiAgentOrchestrator orchestrator(MultiAgentStrategy::Sequential);
 * orchestrator.register_agent("researcher", research_agent);
 * orchestrator.register_agent("writer", writing_agent);
 *
 * auto msg = Message::with_text("user", "Write a research report");
 * auto result = orchestrator.process(std::move(msg)).get();
 * @endcode
 */
class MultiAgentOrchestrator : public core::Agent {
public:
    /**
     * @brief Construct a multi-agent orchestrator
     * @param strategy Execution strategy (default: Sequential)
     */
    explicit MultiAgentOrchestrator(
        MultiAgentStrategy strategy = MultiAgentStrategy::Sequential
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Register an agent
     * @param name Agent name
     * @param agent Agent instance
     */
    void register_agent(const std::string& name, std::shared_ptr<core::Agent> agent);

    /**
     * @brief Unregister an agent
     * @param name Agent name
     */
    void unregister_agent(const std::string& name);

    /**
     * @brief Get list of registered agents
     * @return Vector of agent names
     */
    std::vector<std::string> list_agents() const;

    /**
     * @brief Get all tasks executed
     * @return Vector of agent tasks
     */
    std::vector<AgentTask> get_tasks() const;

    /**
     * @brief Clear task history
     */
    void clear_tasks();

    /**
     * @brief Set execution strategy
     * @param strategy New strategy
     */
    void set_strategy(MultiAgentStrategy strategy);

    /**
     * @brief Get current strategy
     * @return Current execution strategy
     */
    MultiAgentStrategy get_strategy() const;

private:
    std::map<std::string, std::shared_ptr<core::Agent>> agents_;
    MultiAgentStrategy strategy_;
    std::vector<AgentTask> tasks_;

    /**
     * @brief Execute agents sequentially
     * @param message Input message
     * @return Combined result
     */
    core::Result<core::Message, core::AgentError>
    execute_sequential(const core::Message& message);

    /**
     * @brief Execute agents in parallel
     * @param message Input message
     * @return Combined result
     */
    core::Result<core::Message, core::AgentError>
    execute_parallel(const core::Message& message);
};

/**
 * @brief Reaches consensus among multiple agents
 *
 * The ConsensusAgent collects responses from multiple agents and combines
 * them to form a consensus or aggregate view.
 *
 * Features:
 * - Multiple agent consultation
 * - Response aggregation
 * - Consensus formation
 *
 * @example
 * @code
 * ConsensusAgent consensus;
 * consensus.add_agent(agent1);
 * consensus.add_agent(agent2);
 * consensus.add_agent(agent3);
 *
 * auto msg = Message::with_text("user", "What's the best approach?");
 * auto result = consensus.process(std::move(msg)).get();
 * @endcode
 */
class ConsensusAgent : public core::Agent {
public:
    /**
     * @brief Construct a consensus agent
     */
    ConsensusAgent();

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Add an agent to the consensus group
     * @param agent Agent to add
     */
    void add_agent(std::shared_ptr<core::Agent> agent);

    /**
     * @brief Remove all agents
     */
    void clear_agents();

    /**
     * @brief Get number of agents in consensus group
     * @return Agent count
     */
    size_t agent_count() const;

private:
    std::vector<std::shared_ptr<core::Agent>> agents_;
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_MULTIAGENT_HPP
