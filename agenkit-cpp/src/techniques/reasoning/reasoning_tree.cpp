/**
 * @file reasoning_tree.cpp
 * @brief Reasoning Tree Implementation
 */

#include "agenkit/techniques/reasoning/reasoning_tree.hpp"
#include <stdexcept>
#include <algorithm>
#include <numeric>
#include <sstream>

namespace agenkit {
namespace techniques {
namespace reasoning {

ReasoningTree::ReasoningTree()
    : nodes_()
    , root_id_(std::nullopt)
    , next_id_(0)
    , max_depth_(0)
{
}

int ReasoningTree::create_root(
    const std::string& content,
    const std::unordered_map<std::string, std::any>& metadata
) {
    if (root_id_.has_value()) {
        throw std::runtime_error("Root node already exists");
    }

    int node_id = next_id_;
    next_id_++;

    auto node = std::make_shared<ReasoningNode>();
    node->id = node_id;
    node->content = content;
    node->parent_id = std::nullopt;
    node->children_ids = {};
    node->depth = 0;
    node->score = 0.0;
    node->state = NodeState::Open;
    node->metadata = metadata;

    nodes_[node_id] = node;
    root_id_ = node_id;
    max_depth_ = 0;

    return node_id;
}

int ReasoningTree::add_child(
    int parent_id,
    const std::string& content,
    double score,
    const std::unordered_map<std::string, std::any>& metadata
) {
    auto parent_it = nodes_.find(parent_id);
    if (parent_it == nodes_.end()) {
        throw std::runtime_error("Parent node " + std::to_string(parent_id) + " not found");
    }

    auto parent = parent_it->second;

    int child_id = next_id_;
    next_id_++;

    auto child = std::make_shared<ReasoningNode>();
    child->id = child_id;
    child->content = content;
    child->parent_id = parent_id;
    child->children_ids = {};
    child->depth = parent->depth + 1;
    child->score = score;
    child->state = NodeState::Open;
    child->metadata = metadata;

    nodes_[child_id] = child;
    parent->add_child(child_id);

    if (child->depth > max_depth_) {
        max_depth_ = child->depth;
    }

    return child_id;
}

std::shared_ptr<ReasoningNode> ReasoningTree::get_node(int node_id) const {
    auto it = nodes_.find(node_id);
    if (it == nodes_.end()) {
        return nullptr;
    }
    return it->second;
}

std::vector<std::shared_ptr<ReasoningNode>> ReasoningTree::get_path(int node_id) const {
    std::vector<std::shared_ptr<ReasoningNode>> path;

    auto current = get_node(node_id);
    if (!current) {
        return path;
    }

    // Build path from leaf to root
    while (current) {
        path.push_back(current);
        if (!current->parent_id.has_value()) {
            break;
        }
        current = get_node(current->parent_id.value());
    }

    // Reverse to get root to leaf order
    std::reverse(path.begin(), path.end());
    return path;
}

std::string ReasoningTree::get_path_text(int node_id, const std::string& delimiter) const {
    auto path = get_path(node_id);
    if (path.empty()) {
        return "";
    }

    std::ostringstream oss;
    for (size_t i = 0; i < path.size(); ++i) {
        if (i > 0) {
            oss << delimiter;
        }
        oss << path[i]->content;
    }

    return oss.str();
}

std::shared_ptr<ReasoningNode> ReasoningTree::get_best_leaf() const {
    std::shared_ptr<ReasoningNode> best_leaf = nullptr;
    double best_score = -1.0;

    for (const auto& [node_id, node] : nodes_) {
        if (node->is_leaf() && node->state != NodeState::Pruned) {
            if (node->score > best_score) {
                best_score = node->score;
                best_leaf = node;
            }
        }
    }

    return best_leaf;
}

void ReasoningTree::prune_node(int node_id) {
    prune_recursive(node_id);
}

void ReasoningTree::prune_recursive(int node_id) {
    auto node = get_node(node_id);
    if (!node) {
        return;
    }

    // Mark this node as pruned
    node->state = NodeState::Pruned;

    // Recursively prune all children
    for (int child_id : node->children_ids) {
        prune_recursive(child_id);
    }
}

TreeStatistics ReasoningTree::get_statistics() const {
    TreeStatistics stats;
    stats.total_nodes = static_cast<int>(nodes_.size());
    stats.max_depth = max_depth_;
    stats.num_leaves = 0;
    stats.num_pruned = 0;
    stats.best_score = 0.0;
    stats.avg_score = 0.0;

    if (nodes_.empty()) {
        return stats;
    }

    double sum_scores = 0.0;
    int scored_nodes = 0;

    for (const auto& [node_id, node] : nodes_) {
        // Count leaves
        if (node->is_leaf()) {
            stats.num_leaves++;
        }

        // Count pruned nodes
        if (node->state == NodeState::Pruned) {
            stats.num_pruned++;
        }

        // Track scores (exclude root which has score 0.0)
        if (!node->is_root()) {
            sum_scores += node->score;
            scored_nodes++;
            if (node->score > stats.best_score) {
                stats.best_score = node->score;
            }
        }
    }

    // Calculate average score
    if (scored_nodes > 0) {
        stats.avg_score = sum_scores / static_cast<double>(scored_nodes);
    }

    return stats;
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
