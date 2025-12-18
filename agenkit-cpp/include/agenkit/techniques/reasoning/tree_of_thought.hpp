/**
 * @file tree_of_thought.hpp
 * @brief Tree-of-Thought Reasoning Technique
 *
 * Tree-of-Thought explores multiple reasoning paths simultaneously through
 * tree search with branching, evaluation, pruning, and backtracking.
 *
 * Reference: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
 * Yao et al., 2023 - https://arxiv.org/abs/2305.10601
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_TREE_OF_THOUGHT_HPP
#define AGENKIT_TECHNIQUES_REASONING_TREE_OF_THOUGHT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/techniques/reasoning/reasoning_tree.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>
#include <functional>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief Search strategy for tree exploration
 */
enum class SearchStrategy {
    BFS,        ///< Breadth-first search (level by level)
    DFS,        ///< Depth-first search (explore deeply first)
    BestFirst   ///< Best-first search (greedy, highest score first)
};

/**
 * @brief Function type for evaluating reasoning quality
 *
 * Takes a text string and returns a score between 0.0 and 1.0.
 */
using EvaluatorFunc = std::function<double(const std::string&)>;

/**
 * @brief Configuration for Tree-of-Thought
 */
struct TreeOfThoughtConfig {
    /** Number of branches to generate at each step (default: 3) */
    int branching_factor = 3;

    /** Maximum tree depth to explore (default: 5) */
    int max_depth = 5;

    /** Evaluator function for scoring reasoning paths (default: length-based) */
    EvaluatorFunc evaluator = nullptr;

    /** Search strategy to use (default: BestFirst) */
    SearchStrategy strategy = SearchStrategy::BestFirst;

    /** Score threshold below which nodes are pruned (default: 0.3) */
    double prune_threshold = 0.3;
};

/**
 * @brief Tree-of-Thought agent that wraps a base agent
 *
 * This technique explores multiple reasoning paths by building a tree of
 * possibilities, evaluating each path, and selecting the best solution.
 *
 * Particularly effective for:
 * - Complex planning and decision-making
 * - Multi-step reasoning with backtracking
 * - Exploring alternative approaches
 * - Creative problem-solving
 *
 * @example
 * @code
 * auto base_agent = std::make_shared<MyAgent>();
 * TreeOfThoughtConfig config;
 * config.branching_factor = 3;
 * config.max_depth = 4;
 * config.strategy = SearchStrategy::BestFirst;
 *
 * auto tot = std::make_shared<TreeOfThoughtAgent>(base_agent, config);
 * auto future = tot->process(Message::with_text("user", "Design a system architecture"));
 * auto result = future.get();
 * if (result.is_ok()) {
 *     auto response = result.unwrap();
 *     std::cout << "Best solution: " << response.content_as_str() << std::endl;
 *     // Access reasoning_tree_stats and reasoning_path from metadata
 * }
 * @endcode
 */
class TreeOfThoughtAgent : public core::Agent {
public:
    /**
     * @brief Create a new Tree-of-Thought agent
     * @param agent Base agent to wrap
     * @param config Configuration options
     */
    TreeOfThoughtAgent(
        std::shared_ptr<core::Agent> agent,
        const TreeOfThoughtConfig& config = TreeOfThoughtConfig{}
    );

    /**
     * @brief Agent identifier
     * @return "tree_of_thought"
     */
    std::string name() const override;

    /**
     * @brief Agent capabilities
     * @return List of capabilities
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Process a message with Tree-of-Thought reasoning
     *
     * Builds a reasoning tree by:
     * 1. Creating root node with the query
     * 2. Expanding nodes by generating N branches
     * 3. Scoring each branch with the evaluator
     * 4. Pruning low-quality branches
     * 5. Continuing search until max depth or no valid paths
     * 6. Returning best leaf path as the solution
     *
     * @param message Input message with query content
     * @return Future with result containing response with metadata:
     *         - technique: "tree_of_thought"
     *         - search_strategy: "bfs" | "dfs" | "best-first"
     *         - reasoning_tree_stats: TreeStatistics object
     *         - reasoning_path: std::vector<std::string> (best path steps)
     *         - num_steps: int (path length)
     *         - best_score: double (score of best path)
     *
     * @throws std::runtime_error if strategy is invalid or search fails
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    TreeOfThoughtConfig config_;

    /**
     * @brief Default evaluator based on text length and structure
     *
     * Scores text based on:
     * - Length (longer is better, up to a point)
     * - Structure (numbered steps, bullet points get bonus)
     * - Normalized to 0.0-1.0 range
     *
     * @param text Text to evaluate
     * @return Score between 0.0 and 1.0
     */
    double default_evaluator(const std::string& text) const;

    /**
     * @brief Generate N varied reasoning branches for a prompt
     *
     * Uses parallel execution (std::async) to generate multiple branches
     * simultaneously by calling the wrapped agent with varied prompts.
     *
     * @param prompt Base prompt to branch from
     * @param n Number of branches to generate
     * @return Vector of generated branch texts
     */
    std::vector<std::string> generate_branches(const std::string& prompt, int n);

    /**
     * @brief Expand a tree node by generating and adding children
     *
     * Generates N branches, scores them, and adds viable children to the tree.
     * Prunes branches below the threshold.
     *
     * @param tree Reasoning tree to expand
     * @param node_id ID of node to expand
     * @param query Original query for context
     * @return Vector of child node IDs that were added
     */
    std::vector<int> expand_node(
        ReasoningTree& tree,
        int node_id,
        const std::string& query
    );

    /**
     * @brief Perform breadth-first search on the tree
     *
     * Explores all nodes at depth D before moving to depth D+1.
     *
     * @param tree Reasoning tree to search
     * @param root_id ID of root node
     * @param query Original query for context
     */
    void search_bfs(
        ReasoningTree& tree,
        int root_id,
        const std::string& query
    );

    /**
     * @brief Perform depth-first search on the tree
     *
     * Explores as deeply as possible before backtracking.
     *
     * @param tree Reasoning tree to search
     * @param root_id ID of root node
     * @param query Original query for context
     */
    void search_dfs(
        ReasoningTree& tree,
        int root_id,
        const std::string& query
    );

    /**
     * @brief Perform best-first search on the tree
     *
     * Always expands the highest-scoring node next (greedy).
     *
     * @param tree Reasoning tree to search
     * @param root_id ID of root node
     * @param query Original query for context
     */
    void search_best_first(
        ReasoningTree& tree,
        int root_id,
        const std::string& query
    );

    /**
     * @brief Convert SearchStrategy enum to string
     * @param strategy Strategy enum value
     * @return String representation
     */
    std::string strategy_to_string(SearchStrategy strategy) const;
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_TREE_OF_THOUGHT_HPP
