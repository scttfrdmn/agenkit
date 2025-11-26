/**
 * @file orchestration.hpp
 * @brief Orchestration pattern implementation
 *
 * The Orchestration pattern coordinates multiple agents to work together
 * on complex tasks. An orchestrator agent decides which agents to invoke,
 * in what order, and how to combine their results.
 *
 * @see https://microsoft.github.io/autogen/docs/topics/orchestration
 */

#ifndef AGENKIT_PATTERNS_ORCHESTRATION_HPP
#define AGENKIT_PATTERNS_ORCHESTRATION_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <future>

namespace agenkit {
namespace patterns {

/**
 * @brief Execution strategy for orchestration
 */
enum class OrchestrationStrategy {
    /// Orchestrator decides which agents to call and in what order
    Sequential,

    /// All agents are called in parallel and results are combined
    Parallel,

    /// Agents are called based on conditions/routing rules
    Conditional,

    /// Custom strategy defined by user function
    Custom
};

/**
 * @brief Record of a single agent invocation in orchestration
 */
struct OrchestrationStep {
    /// Step number (1-indexed)
    int step;

    /// Name of the agent that was invoked
    std::string agent_name;

    /// Input message sent to the agent
    core::Message input;

    /// Output message from the agent
    core::Message output;

    /// Whether the invocation was successful
    bool success;

    /// Error message if not successful
    std::string error_message;

    /// Metadata for this step
    nlohmann::json metadata;
};

/**
 * @brief Configuration for orchestration behavior
 */
struct OrchestrationConfig {
    /// Maximum number of orchestration steps
    int max_steps{10};

    /// Strategy to use
    OrchestrationStrategy strategy{OrchestrationStrategy::Sequential};

    /// Whether to include intermediate results in final message
    bool include_intermediate_results{false};

    /// Whether to stop on first agent error
    bool stop_on_error{false};

    /// Timeout for entire orchestration (0 = no timeout)
    std::chrono::milliseconds timeout{0};
};

/**
 * @brief Function type for custom routing logic
 *
 * Takes the current message and returns the name of the next agent to invoke
 * (or empty string to finish orchestration)
 */
using RoutingFunction = std::function<std::string(const core::Message&)>;

/**
 * @brief Function type for custom result combination
 *
 * Takes a vector of messages from different agents and combines them into one
 */
using CombinerFunction = std::function<core::Message(const std::vector<core::Message>&)>;

/**
 * @brief Orchestration agent that coordinates multiple agents
 *
 * The OrchestrationAgent manages a collection of agents and coordinates
 * their execution based on a strategy. It can:
 * - Route messages to appropriate agents sequentially
 * - Execute multiple agents in parallel
 * - Use conditional logic to determine execution flow
 * - Combine results from multiple agents
 *
 * @par Example
 * @code
 * // Create orchestrator
 * OrchestrationAgent orchestrator;
 * orchestrator.add_agent("research", research_agent);
 * orchestrator.add_agent("writer", writer_agent);
 * orchestrator.add_agent("reviewer", reviewer_agent);
 *
 * // Sequential execution
 * orchestrator.set_strategy(OrchestrationStrategy::Sequential);
 * orchestrator.set_routing([](const Message& msg) {
 *     // Custom routing logic
 *     return "research"; // Return agent name or "" to finish
 * });
 *
 * // Process request
 * auto result = orchestrator.process(message).get();
 * @endcode
 */
class OrchestrationAgent : public core::Agent {
public:
    /**
     * @brief Construct an orchestration agent
     *
     * @param config Optional configuration
     */
    explicit OrchestrationAgent(OrchestrationConfig config = OrchestrationConfig{});

    /**
     * @brief Add an agent to the orchestration
     *
     * @param name Name/identifier for the agent
     * @param agent The agent to add
     *
     * @throws std::invalid_argument if agent is null or name is empty
     */
    void add_agent(const std::string& name, std::shared_ptr<core::Agent> agent);

    /**
     * @brief Remove an agent from the orchestration
     *
     * @param name Name of the agent to remove
     * @return true if agent was removed, false if not found
     */
    bool remove_agent(const std::string& name);

    /**
     * @brief Get an agent by name
     *
     * @param name Name of the agent
     * @return Shared pointer to agent, or nullptr if not found
     */
    std::shared_ptr<core::Agent> get_agent(const std::string& name) const;

    /**
     * @brief Get all registered agents
     *
     * @return Map of agent names to agent pointers
     */
    const std::unordered_map<std::string, std::shared_ptr<core::Agent>>& get_agents() const;

    /**
     * @brief Set orchestration strategy
     *
     * @param strategy Strategy to use
     */
    void set_strategy(OrchestrationStrategy strategy);

    /**
     * @brief Get current strategy
     *
     * @return Current orchestration strategy
     */
    OrchestrationStrategy get_strategy() const;

    /**
     * @brief Set custom routing function (for Sequential/Conditional strategies)
     *
     * @param router Function that decides which agent to invoke next
     */
    void set_routing(RoutingFunction router);

    /**
     * @brief Set custom result combiner (for Parallel strategy)
     *
     * @param combiner Function that combines results from multiple agents
     */
    void set_combiner(CombinerFunction combiner);

    /**
     * @brief Get orchestration history
     *
     * @return Vector of orchestration steps
     */
    const std::vector<OrchestrationStep>& get_history() const;

    /**
     * @brief Clear orchestration history
     */
    void clear_history();

    /**
     * @brief Get configuration
     *
     * @return Current configuration
     */
    const OrchestrationConfig& get_config() const;

    /**
     * @brief Update configuration
     *
     * @param config New configuration
     */
    void set_config(const OrchestrationConfig& config);

    // Agent interface
    std::string name() const override;
    std::vector<std::string> capabilities() const override;
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    /// Configuration
    OrchestrationConfig config_;

    /// Registered agents
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents_;

    /// Routing function for sequential/conditional strategies
    RoutingFunction router_;

    /// Combiner function for parallel strategy
    CombinerFunction combiner_;

    /// Orchestration history
    std::vector<OrchestrationStep> history_;

    /**
     * @brief Execute sequential orchestration
     */
    core::Result<core::Message, core::AgentError>
    execute_sequential(core::Message message);

    /**
     * @brief Execute parallel orchestration
     */
    core::Result<core::Message, core::AgentError>
    execute_parallel(core::Message message);

    /**
     * @brief Execute conditional orchestration
     */
    core::Result<core::Message, core::AgentError>
    execute_conditional(core::Message message);

    /**
     * @brief Invoke a single agent
     */
    core::Result<core::Message, core::AgentError>
    invoke_agent(const std::string& agent_name, core::Message message, int step);

    /**
     * @brief Default combiner that concatenates results
     */
    static core::Message default_combiner(const std::vector<core::Message>& messages);

    /**
     * @brief Add orchestration metadata to final message
     */
    void add_orchestration_metadata(core::Message& message);
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_ORCHESTRATION_HPP
