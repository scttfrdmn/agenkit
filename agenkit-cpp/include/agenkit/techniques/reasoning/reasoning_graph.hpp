/**
 * @file reasoning_graph.hpp
 * @brief Reasoning Graph Data Structure for Graph-of-Thought
 *
 * Provides a directed graph structure for representing reasoning as nodes
 * (thoughts/conclusions) connected by edges (logical relationships).
 *
 * This is more flexible than tree-based approaches, allowing for:
 * - Multiple reasoning paths
 * - Complex dependencies
 * - Cycle detection for circular reasoning
 * - Path aggregation
 *
 * Reference: Graph-of-Thought paper: https://arxiv.org/abs/2308.09687
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_REASONING_GRAPH_HPP
#define AGENKIT_TECHNIQUES_REASONING_REASONING_GRAPH_HPP

#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <memory>
#include <optional>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief Type of thought node in the graph
 */
enum class NodeType {
    PREMISE,      ///< Starting assumption or fact
    INTERMEDIATE, ///< Intermediate conclusion
    CONCLUSION    ///< Final conclusion
};

/**
 * @brief Type of logical connection between nodes
 */
enum class EdgeType {
    SUPPORTS,     ///< Node supports another
    DEPENDS_ON,   ///< Node depends on another
    CONTRADICTS,  ///< Node contradicts another
    REFINES       ///< Node refines/improves another
};

/**
 * @brief A single thought or conclusion in the reasoning graph
 */
struct ThoughtNode {
    /** Unique node identifier */
    size_t id;

    /** Thought/conclusion text */
    std::string content;

    /** Type of node */
    NodeType node_type;

    /** Confidence score (0.0-1.0) */
    double confidence;

    /** Additional node-specific data */
    std::unordered_map<std::string, std::string> metadata;

    ThoughtNode(size_t id, const std::string& content, NodeType type, double conf)
        : id(id), content(content), node_type(type), confidence(conf) {}
};

/**
 * @brief A logical connection between two thoughts
 */
struct LogicalEdge {
    /** Source node ID */
    size_t from_node;

    /** Target node ID */
    size_t to_node;

    /** Type of logical connection */
    EdgeType edge_type;

    /** Connection strength (0.0-1.0) */
    double strength;

    /** Additional edge-specific data */
    std::unordered_map<std::string, std::string> metadata;

    LogicalEdge(size_t from, size_t to, EdgeType type, double str)
        : from_node(from), to_node(to), edge_type(type), strength(str) {}
};

/**
 * @brief Graph statistics for analysis
 */
struct GraphStatistics {
    /** Number of nodes in graph */
    size_t num_nodes;

    /** Number of edges in graph */
    size_t num_edges;

    /** Whether graph contains cycles */
    bool has_cycles;

    /** Count of each node type */
    std::unordered_map<std::string, size_t> node_types;

    /** Count of each edge type */
    std::unordered_map<std::string, size_t> edge_types;
};

/**
 * @brief Directed graph for representing reasoning structures
 *
 * Nodes represent thoughts, conclusions, or premises.
 * Edges represent logical connections and dependencies.
 *
 * Supports:
 * - Adding nodes and edges
 * - Path finding between nodes
 * - Cycle detection
 * - Graph statistics
 */
class ReasoningGraph {
public:
    ReasoningGraph();

    /**
     * @brief Add a thought node to the graph
     *
     * @param content The thought/conclusion content
     * @param node_type Type of node (premise, intermediate, conclusion)
     * @param confidence Confidence score 0.0 to 1.0
     * @return Node ID
     */
    size_t add_node(const std::string& content, NodeType node_type, double confidence = 1.0);

    /**
     * @brief Add a logical edge between two nodes
     *
     * @param from_node Source node ID
     * @param to_node Target node ID
     * @param edge_type Type of logical connection
     * @param strength Connection strength 0.0 to 1.0
     * @return true if successful, false if nodes don't exist
     */
    bool add_edge(size_t from_node, size_t to_node, EdgeType edge_type, double strength = 1.0);

    /**
     * @brief Get node by ID
     *
     * @param node_id Node ID
     * @return Pointer to node, or nullptr if not found
     */
    const ThoughtNode* get_node(size_t node_id) const;

    /**
     * @brief Get all premise nodes
     *
     * @return Vector of premise nodes
     */
    std::vector<const ThoughtNode*> get_premises() const;

    /**
     * @brief Get all conclusion nodes
     *
     * @return Vector of conclusion nodes
     */
    std::vector<const ThoughtNode*> get_conclusions() const;

    /**
     * @brief Find all paths from start to end node
     *
     * @param start Start node ID
     * @param end End node ID
     * @param max_length Maximum path length
     * @return Vector of paths (each path is vector of node IDs)
     */
    std::vector<std::vector<size_t>> find_paths(size_t start, size_t end, size_t max_length = 10) const;

    /**
     * @brief Check if graph contains cycles
     *
     * @return true if cycles detected
     */
    bool has_cycle() const;

    /**
     * @brief Calculate score for a reasoning path
     *
     * @param path Vector of node IDs
     * @return Path score (higher is better)
     */
    double get_path_score(const std::vector<size_t>& path) const;

    /**
     * @brief Get graph statistics for analysis
     *
     * @return Graph statistics
     */
    GraphStatistics statistics() const;

    /**
     * @brief Get all nodes in the graph
     *
     * @return Vector of all nodes
     */
    std::vector<const ThoughtNode*> get_nodes() const;

    /**
     * @brief Get all edges in the graph
     *
     * @return Vector of all edges
     */
    const std::vector<LogicalEdge>& get_edges() const;

private:
    std::unordered_map<size_t, std::unique_ptr<ThoughtNode>> nodes_;
    std::vector<LogicalEdge> edges_;
    size_t next_id_;

    // Adjacency lists for efficient traversal
    std::unordered_map<size_t, std::vector<size_t>> outgoing_;
    std::unordered_map<size_t, std::vector<size_t>> incoming_;

    // Helper methods
    void dfs_paths(size_t current, size_t end, size_t max_length,
                   std::unordered_set<size_t>& visited,
                   std::vector<size_t>& path,
                   std::vector<std::vector<size_t>>& paths) const;

    bool has_cycle_dfs(size_t node_id,
                       std::unordered_set<size_t>& visited,
                       std::unordered_set<size_t>& rec_stack) const;
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_REASONING_GRAPH_HPP
