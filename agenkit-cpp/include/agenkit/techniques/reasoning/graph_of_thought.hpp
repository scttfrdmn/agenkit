/**
 * @file graph_of_thought.hpp
 * @brief Graph-of-Thought Reasoning Technique
 *
 * Represents reasoning as a directed graph where nodes are thoughts/conclusions
 * and edges represent logical connections. More flexible than tree-based
 * approaches, allows for complex multi-hop reasoning and thought combination.
 *
 * This technique is particularly effective for:
 * - Multi-hop reasoning problems
 * - Problems with multiple interconnected concepts
 * - Situations requiring synthesis of multiple reasoning chains
 *
 * Reference:
 * - Paper: https://arxiv.org/abs/2308.09687
 * - "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_GRAPH_OF_THOUGHT_HPP
#define AGENKIT_TECHNIQUES_REASONING_GRAPH_OF_THOUGHT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/techniques/reasoning/reasoning_graph.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief Aggregation strategy for combining reasoning paths
 */
enum class AggregatorType {
    PATH_BASED, ///< Evaluate complete paths, choose best path
    NODE_BASED  ///< Aggregate individual nodes across paths
};

/**
 * @brief Configuration options for GraphOfThought agent
 */
struct GraphOfThoughtConfig {
    /** Maximum number of nodes in reasoning graph */
    size_t max_nodes = 20;

    /** Maximum number of edges in reasoning graph */
    size_t max_edges = 40;

    /** Aggregation strategy for combining paths */
    AggregatorType aggregator = AggregatorType::PATH_BASED;

    /** Whether to allow cycles in reasoning graph */
    bool allow_cycles = false;
};

/**
 * @brief Graph-of-Thought reasoning technique
 *
 * Builds a directed graph of reasoning steps, explores connections,
 * and aggregates multiple reasoning paths to reach conclusions.
 *
 * This technique is particularly effective for:
 * - Multi-hop reasoning with complex dependencies
 * - Problems requiring synthesis of multiple chains of thought
 * - Situations where thoughts may support, contradict, or refine each other
 * - Complex knowledge integration tasks
 *
 * @example
 * @code
 * auto base_agent = std::make_shared<MyAgent>();
 * GraphOfThoughtConfig config;
 * config.max_nodes = 20;
 * config.aggregator = AggregatorType::PATH_BASED;
 *
 * auto got = std::make_unique<GraphOfThoughtAgent>(base_agent, config);
 * auto result = got->process(message).get();
 * // Access reasoning graph and paths from metadata
 * @endcode
 */
class GraphOfThoughtAgent : public core::Agent {
public:
    /**
     * @brief Constructor
     *
     * @param agent Base agent for generating responses
     * @param config Configuration options
     */
    GraphOfThoughtAgent(std::shared_ptr<core::Agent> agent, const GraphOfThoughtConfig& config);

    std::string name() const override;
    std::vector<std::string> capabilities() const override;
    std::future<core::Result<core::Message, core::AgentError>> process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    size_t max_nodes_;
    size_t max_edges_;
    AggregatorType aggregator_;
    bool allow_cycles_;

    // Helper methods
    std::future<core::Result<std::string, core::AgentError>> llm_call(const std::string& prompt);

    std::future<core::Result<std::vector<std::string>, core::AgentError>> generate_premises(const std::string& problem);

    std::future<core::Result<std::vector<std::string>, core::AgentError>> generate_thoughts(
        const std::string& problem,
        const std::vector<std::string>& existing_thoughts,
        size_t max_new);

    std::future<core::Result<std::optional<EdgeType>, core::AgentError>> identify_connection(
        const std::string& thought1,
        const std::string& thought2);

    std::future<core::Result<ReasoningGraph, core::AgentError>> build_graph(const std::string& problem);

    std::vector<std::vector<size_t>> find_reasoning_paths(const ReasoningGraph& graph);

    std::string aggregate_paths(const ReasoningGraph& graph,
                                const std::vector<std::vector<size_t>>& paths);
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_GRAPH_OF_THOUGHT_HPP
