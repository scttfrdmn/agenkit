/**
 * @file reasoning_tree.hpp
 * @brief Reasoning Tree Data Structure for Tree-of-Thought
 *
 * Provides a tree structure for exploring multiple reasoning paths with
 * branching, evaluation, pruning, and backtracking capabilities.
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_REASONING_TREE_HPP
#define AGENKIT_TECHNIQUES_REASONING_REASONING_TREE_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <memory>
#include <any>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief State of a reasoning node in the tree
 */
enum class NodeState {
    Open,       ///< Node created but not yet explored
    Active,     ///< Node currently being explored
    Evaluated,  ///< Node has been scored but not yet pruned/terminated
    Pruned,     ///< Node pruned due to low score
    Terminal    ///< Node is a leaf/endpoint
};

/**
 * @brief Individual node in the reasoning tree
 */
struct ReasoningNode {
    int id;                                     ///< Unique node identifier
    std::string content;                        ///< Reasoning step content
    std::optional<int> parent_id;               ///< Parent node ID (nullopt for root)
    std::vector<int> children_ids;              ///< Child node IDs
    int depth;                                  ///< Depth in tree (root = 0)
    double score;                               ///< Quality score (0.0-1.0)
    NodeState state;                            ///< Current node state
    std::unordered_map<std::string, std::any> metadata;  ///< Additional metadata

    /**
     * @brief Check if this is a leaf node
     * @return true if node has no children
     */
    bool is_leaf() const { return children_ids.empty(); }

    /**
     * @brief Check if this is the root node
     * @return true if node has no parent
     */
    bool is_root() const { return !parent_id.has_value(); }

    /**
     * @brief Add a child to this node
     * @param child_id ID of child node
     */
    void add_child(int child_id) {
        children_ids.push_back(child_id);
    }
};

/**
 * @brief Statistics about the reasoning tree
 */
struct TreeStatistics {
    int total_nodes;        ///< Total number of nodes
    int max_depth;          ///< Maximum depth reached
    int num_leaves;         ///< Number of leaf nodes
    int num_pruned;         ///< Number of pruned nodes
    double best_score;      ///< Best score achieved
    double avg_score;       ///< Average score across all nodes
};

/**
 * @brief Convert TreeStatistics to JSON (for nlohmann::json)
 */
inline void to_json(nlohmann::json& j, const TreeStatistics& stats) {
    j = nlohmann::json{
        {"total_nodes", stats.total_nodes},
        {"max_depth", stats.max_depth},
        {"num_leaves", stats.num_leaves},
        {"num_pruned", stats.num_pruned},
        {"best_score", stats.best_score},
        {"avg_score", stats.avg_score}
    };
}

/**
 * @brief Convert JSON to TreeStatistics (for nlohmann::json)
 */
inline void from_json(const nlohmann::json& j, TreeStatistics& stats) {
    j.at("total_nodes").get_to(stats.total_nodes);
    j.at("max_depth").get_to(stats.max_depth);
    j.at("num_leaves").get_to(stats.num_leaves);
    j.at("num_pruned").get_to(stats.num_pruned);
    j.at("best_score").get_to(stats.best_score);
    j.at("avg_score").get_to(stats.avg_score);
}

/**
 * @brief Tree structure for multi-path reasoning exploration
 *
 * ReasoningTree manages a tree of reasoning nodes with support for:
 * - Creating root and adding children
 * - Path retrieval and text generation
 * - Finding best leaf nodes
 * - Pruning low-quality branches
 * - Collecting tree statistics
 *
 * @example
 * @code
 * ReasoningTree tree;
 * int root_id = tree.create_root("Initial query");
 * int child1 = tree.add_child(root_id, "Approach 1", 0.8);
 * int child2 = tree.add_child(root_id, "Approach 2", 0.6);
 *
 * auto best = tree.get_best_leaf();
 * if (best) {
 *     auto path = tree.get_path_text(best->id);
 *     std::cout << "Best path: " << path << std::endl;
 * }
 * @endcode
 */
class ReasoningTree {
public:
    /**
     * @brief Create a new empty reasoning tree
     */
    ReasoningTree();

    /**
     * @brief Create the root node of the tree
     * @param content Content for the root node
     * @param metadata Optional metadata for the root node
     * @return ID of the created root node
     * @throws std::runtime_error if root already exists
     */
    int create_root(
        const std::string& content,
        const std::unordered_map<std::string, std::any>& metadata = {}
    );

    /**
     * @brief Add a child node to a parent
     * @param parent_id ID of the parent node
     * @param content Content for the child node
     * @param score Quality score for the child (0.0-1.0)
     * @param metadata Optional metadata for the child node
     * @return ID of the created child node
     * @throws std::runtime_error if parent doesn't exist
     */
    int add_child(
        int parent_id,
        const std::string& content,
        double score,
        const std::unordered_map<std::string, std::any>& metadata = {}
    );

    /**
     * @brief Get a node by ID
     * @param node_id ID of the node to retrieve
     * @return Pointer to the node, or nullptr if not found
     */
    std::shared_ptr<ReasoningNode> get_node(int node_id) const;

    /**
     * @brief Get the path from root to a specific node
     * @param node_id ID of the target node
     * @return Vector of nodes from root to target (inclusive)
     */
    std::vector<std::shared_ptr<ReasoningNode>> get_path(int node_id) const;

    /**
     * @brief Get path content as concatenated text
     * @param node_id ID of the target node
     * @param delimiter Delimiter between path steps (default: newline)
     * @return Concatenated text of all nodes in path
     */
    std::string get_path_text(int node_id, const std::string& delimiter = "\n") const;

    /**
     * @brief Find the best leaf node (highest score)
     * @return Pointer to best leaf node, or nullptr if no leaves exist
     */
    std::shared_ptr<ReasoningNode> get_best_leaf() const;

    /**
     * @brief Prune a node and all its descendants
     * @param node_id ID of the node to prune
     *
     * Sets the node state to Pruned and recursively prunes all children.
     */
    void prune_node(int node_id);

    /**
     * @brief Get statistics about the tree
     * @return TreeStatistics struct with tree metrics
     */
    TreeStatistics get_statistics() const;

    /**
     * @brief Get the maximum depth of the tree
     * @return Maximum depth (root = 0)
     */
    int max_depth() const { return max_depth_; }

    /**
     * @brief Get the root node ID
     * @return Root ID, or nullopt if no root exists
     */
    std::optional<int> root_id() const { return root_id_; }

private:
    std::unordered_map<int, std::shared_ptr<ReasoningNode>> nodes_;
    std::optional<int> root_id_;
    int next_id_;
    int max_depth_;

    /**
     * @brief Recursively prune a node and its descendants
     * @param node_id ID of the node to prune
     */
    void prune_recursive(int node_id);
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_REASONING_TREE_HPP
