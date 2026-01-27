/**
 * @file reasoning_graph.cpp
 * @brief Implementation of Reasoning Graph Data Structure
 */

#include "agenkit/techniques/reasoning/reasoning_graph.hpp"
#include <algorithm>
#include <stdexcept>

namespace agenkit {
namespace techniques {
namespace reasoning {

ReasoningGraph::ReasoningGraph() : next_id_(0) {}

size_t ReasoningGraph::add_node(const std::string& content, NodeType node_type, double confidence) {
    size_t node_id = next_id_++;

    auto node = std::make_unique<ThoughtNode>(node_id, content, node_type, confidence);
    nodes_[node_id] = std::move(node);
    outgoing_[node_id] = std::vector<size_t>();
    incoming_[node_id] = std::vector<size_t>();

    return node_id;
}

bool ReasoningGraph::add_edge(size_t from_node, size_t to_node, EdgeType edge_type, double strength) {
    if (nodes_.find(from_node) == nodes_.end() || nodes_.find(to_node) == nodes_.end()) {
        return false;
    }

    edges_.emplace_back(from_node, to_node, edge_type, strength);
    outgoing_[from_node].push_back(to_node);
    incoming_[to_node].push_back(from_node);

    return true;
}

const ThoughtNode* ReasoningGraph::get_node(size_t node_id) const {
    auto it = nodes_.find(node_id);
    if (it != nodes_.end()) {
        return it->second.get();
    }
    return nullptr;
}

std::vector<const ThoughtNode*> ReasoningGraph::get_premises() const {
    std::vector<const ThoughtNode*> premises;
    for (const auto& pair : nodes_) {
        if (pair.second->node_type == NodeType::PREMISE) {
            premises.push_back(pair.second.get());
        }
    }
    return premises;
}

std::vector<const ThoughtNode*> ReasoningGraph::get_conclusions() const {
    std::vector<const ThoughtNode*> conclusions;
    for (const auto& pair : nodes_) {
        if (pair.second->node_type == NodeType::CONCLUSION) {
            conclusions.push_back(pair.second.get());
        }
    }
    return conclusions;
}

std::vector<std::vector<size_t>> ReasoningGraph::find_paths(size_t start, size_t end, size_t max_length) const {
    std::vector<std::vector<size_t>> paths;
    std::unordered_set<size_t> visited;
    std::vector<size_t> path;

    dfs_paths(start, end, max_length, visited, path, paths);

    return paths;
}

void ReasoningGraph::dfs_paths(size_t current, size_t end, size_t max_length,
                                std::unordered_set<size_t>& visited,
                                std::vector<size_t>& path,
                                std::vector<std::vector<size_t>>& paths) const {
    if (path.size() > max_length) {
        return;
    }

    if (current == end) {
        auto complete_path = path;
        complete_path.push_back(current);
        paths.push_back(complete_path);
        return;
    }

    if (visited.find(current) != visited.end()) {
        return;
    }

    visited.insert(current);
    path.push_back(current);

    auto it = outgoing_.find(current);
    if (it != outgoing_.end()) {
        for (size_t neighbor : it->second) {
            dfs_paths(neighbor, end, max_length, visited, path, paths);
        }
    }

    path.pop_back();
    visited.erase(current);
}

bool ReasoningGraph::has_cycle() const {
    std::unordered_set<size_t> visited;
    std::unordered_set<size_t> rec_stack;

    for (const auto& pair : nodes_) {
        if (visited.find(pair.first) == visited.end()) {
            if (has_cycle_dfs(pair.first, visited, rec_stack)) {
                return true;
            }
        }
    }

    return false;
}

bool ReasoningGraph::has_cycle_dfs(size_t node_id,
                                    std::unordered_set<size_t>& visited,
                                    std::unordered_set<size_t>& rec_stack) const {
    visited.insert(node_id);
    rec_stack.insert(node_id);

    auto it = outgoing_.find(node_id);
    if (it != outgoing_.end()) {
        for (size_t neighbor : it->second) {
            if (visited.find(neighbor) == visited.end()) {
                if (has_cycle_dfs(neighbor, visited, rec_stack)) {
                    return true;
                }
            } else if (rec_stack.find(neighbor) != rec_stack.end()) {
                return true;
            }
        }
    }

    rec_stack.erase(node_id);
    return false;
}

double ReasoningGraph::get_path_score(const std::vector<size_t>& path) const {
    double score = 0.0;

    // Add confidence scores
    for (size_t node_id : path) {
        auto node = get_node(node_id);
        if (node) {
            score += node->confidence;
        }
    }

    // Add edge strengths
    for (size_t i = 0; i < path.size() - 1; ++i) {
        size_t from_node = path[i];
        size_t to_node = path[i + 1];

        auto edge_it = std::find_if(edges_.begin(), edges_.end(),
                                     [from_node, to_node](const LogicalEdge& e) {
                                         return e.from_node == from_node && e.to_node == to_node;
                                     });

        if (edge_it != edges_.end()) {
            score += edge_it->strength;
        }
    }

    return score;
}

GraphStatistics ReasoningGraph::statistics() const {
    GraphStatistics stats;

    stats.num_nodes = nodes_.size();
    stats.num_edges = edges_.size();
    stats.has_cycles = has_cycle();

    // Count node types
    stats.node_types["premise"] = 0;
    stats.node_types["intermediate"] = 0;
    stats.node_types["conclusion"] = 0;

    for (const auto& pair : nodes_) {
        switch (pair.second->node_type) {
            case NodeType::PREMISE:
                stats.node_types["premise"]++;
                break;
            case NodeType::INTERMEDIATE:
                stats.node_types["intermediate"]++;
                break;
            case NodeType::CONCLUSION:
                stats.node_types["conclusion"]++;
                break;
        }
    }

    // Count edge types
    stats.edge_types["supports"] = 0;
    stats.edge_types["depends_on"] = 0;
    stats.edge_types["contradicts"] = 0;
    stats.edge_types["refines"] = 0;

    for (const auto& edge : edges_) {
        switch (edge.edge_type) {
            case EdgeType::SUPPORTS:
                stats.edge_types["supports"]++;
                break;
            case EdgeType::DEPENDS_ON:
                stats.edge_types["depends_on"]++;
                break;
            case EdgeType::CONTRADICTS:
                stats.edge_types["contradicts"]++;
                break;
            case EdgeType::REFINES:
                stats.edge_types["refines"]++;
                break;
        }
    }

    return stats;
}

std::vector<const ThoughtNode*> ReasoningGraph::get_nodes() const {
    std::vector<const ThoughtNode*> result;
    for (const auto& pair : nodes_) {
        result.push_back(pair.second.get());
    }
    return result;
}

const std::vector<LogicalEdge>& ReasoningGraph::get_edges() const {
    return edges_;
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
