/**
 * @file tree_of_thought.cpp
 * @brief Tree-of-Thought Reasoning Technique Implementation
 */

#include "agenkit/techniques/reasoning/tree_of_thought.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"
#include <regex>
#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <queue>
#include <stack>
#include <vector>

namespace agenkit {
namespace techniques {
namespace reasoning {

TreeOfThoughtAgent::TreeOfThoughtAgent(
    std::shared_ptr<core::Agent> agent,
    const TreeOfThoughtConfig& config
) : agent_(std::move(agent)), config_(config) {
    // Set default evaluator if none provided
    if (!config_.evaluator) {
        config_.evaluator = [this](const std::string& text) {
            return this->default_evaluator(text);
        };
    }
}

std::string TreeOfThoughtAgent::name() const {
    return "tree_of_thought";
}

std::vector<std::string> TreeOfThoughtAgent::capabilities() const {
    return {
        "reasoning",
        "tree_search",
        "multi_path_exploration",
        "backtracking",
        "tree_of_thought",
        "planning"
    };
}

std::future<core::Result<core::Message, core::AgentError>>
TreeOfThoughtAgent::process(core::Message message) {
    return infrastructure::global_thread_pool().enqueue([this, msg = std::move(message)]() -> core::Result<core::Message, core::AgentError> {
        const std::string query = msg.content_as_str();

        // Create reasoning tree
        ReasoningTree tree;
        int root_id = tree.create_root(query);

        // Perform search based on strategy
        try {
            switch (config_.strategy) {
                case SearchStrategy::BFS:
                    search_bfs(tree, root_id, query);
                    break;
                case SearchStrategy::DFS:
                    search_dfs(tree, root_id, query);
                    break;
                case SearchStrategy::BestFirst:
                    search_best_first(tree, root_id, query);
                    break;
                default:
                    return core::Result<core::Message, core::AgentError>::err(
                        core::AgentError(
                            core::AgentErrorType::ProcessingError,
                            "Invalid search strategy"
                        )
                    );
            }
        } catch (const std::exception& e) {
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::ProcessingError,
                    std::string("Tree search failed: ") + e.what()
                )
            );
        }

        // Get best leaf node
        auto best_leaf = tree.get_best_leaf();
        if (!best_leaf) {
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::ProcessingError,
                    "No valid reasoning paths found"
                )
            );
        }

        // Build response with best path
        auto path = tree.get_path(best_leaf->id);
        std::vector<std::string> path_steps;
        path_steps.reserve(path.size());
        for (const auto& node : path) {
            path_steps.push_back(node->content);
        }

        std::string best_path_text = tree.get_path_text(best_leaf->id);
        auto stats = tree.get_statistics();

        // Create response message
        auto response = core::Message::with_text("assistant", best_path_text);
        response.with_metadata("technique", nlohmann::json("tree_of_thought"))
               .with_metadata("search_strategy", nlohmann::json(strategy_to_string(config_.strategy)))
               .with_metadata("reasoning_path", nlohmann::json(path_steps))
               .with_metadata("num_steps", nlohmann::json(static_cast<int>(path_steps.size())))
               .with_metadata("best_score", nlohmann::json(best_leaf->score))
               .with_metadata("reasoning_tree_stats", nlohmann::json(stats));

        return core::Result<core::Message, core::AgentError>::ok(std::move(response));
    });
}

double TreeOfThoughtAgent::default_evaluator(const std::string& text) const {
    if (text.empty()) {
        return 0.0;
    }

    // Base score on length (normalized)
    double length_score = std::min(1.0, static_cast<double>(text.length()) / 500.0);

    // Bonus for structured content (numbered steps, bullet points)
    double structure_bonus = 0.0;
    std::regex numbered_regex(R"(^\d+[\.)]\s*)", std::regex::multiline);
    std::regex bullet_regex(R"(^[•\-\*]\s*)", std::regex::multiline);

    auto numbered_begin = std::sregex_iterator(text.begin(), text.end(), numbered_regex);
    auto numbered_end = std::sregex_iterator();
    auto bullet_begin = std::sregex_iterator(text.begin(), text.end(), bullet_regex);
    auto bullet_end = std::sregex_iterator();

    int numbered_count = std::distance(numbered_begin, numbered_end);
    int bullet_count = std::distance(bullet_begin, bullet_end);

    if (numbered_count >= 2) {
        structure_bonus = 0.2;
    } else if (bullet_count >= 2) {
        structure_bonus = 0.15;
    }

    // Final score (capped at 1.0)
    return std::min(1.0, length_score + structure_bonus);
}

std::vector<std::string> TreeOfThoughtAgent::generate_branches(
    const std::string& prompt,
    int n
) {
    // Launch parallel futures for branch generation
    std::vector<std::future<std::string>> futures;
    futures.reserve(n);

    for (int i = 0; i < n; ++i) {
        futures.push_back(infrastructure::global_thread_pool().enqueue([this, prompt, i]() -> std::string {
            std::string varied_prompt = prompt + "\n\nAlternative approach #" +
                                       std::to_string(i + 1) + ":";

            auto msg_future = agent_->process(core::Message::with_text("user", varied_prompt));
            auto result = msg_future.get();

            if (!result.is_ok()) {
                throw std::runtime_error("Branch generation failed: " + result.unwrap_err().message());
            }

            return result.unwrap().content_as_str();
        }));
    }

    // Collect results
    std::vector<std::string> branches;
    branches.reserve(n);

    for (auto& future : futures) {
        try {
            branches.push_back(future.get());
        } catch (const std::exception& e) {
            // Continue with other branches if one fails
            continue;
        }
    }

    return branches;
}

std::vector<int> TreeOfThoughtAgent::expand_node(
    ReasoningTree& tree,
    int node_id,
    const std::string& query
) {
    (void)query;  // Suppress unused parameter warning

    auto node = tree.get_node(node_id);
    if (!node) {
        return {};
    }

    // Don't expand pruned nodes
    if (node->state == NodeState::Pruned) {
        return {};
    }

    // Mark as active
    node->state = NodeState::Active;

    // Generate branches
    std::string prompt = tree.get_path_text(node_id);
    auto branches = generate_branches(prompt, config_.branching_factor);

    std::vector<int> child_ids;
    child_ids.reserve(branches.size());

    for (const auto& branch : branches) {
        // Score the branch
        double score = config_.evaluator(branch);

        // Prune if below threshold
        if (score < config_.prune_threshold) {
            continue;
        }

        // Add child to tree
        int child_id = tree.add_child(node_id, branch, score);
        child_ids.push_back(child_id);

        auto child = tree.get_node(child_id);
        if (child) {
            child->state = NodeState::Evaluated;
        }
    }

    // Mark node as evaluated
    node->state = NodeState::Evaluated;

    return child_ids;
}

void TreeOfThoughtAgent::search_bfs(
    ReasoningTree& tree,
    int root_id,
    const std::string& query
) {
    std::queue<int> queue;
    queue.push(root_id);

    while (!queue.empty()) {
        int node_id = queue.front();
        queue.pop();

        auto node = tree.get_node(node_id);
        if (!node) {
            continue;
        }

        // Stop at max depth
        if (node->depth >= config_.max_depth) {
            node->state = NodeState::Terminal;
            continue;
        }

        // Expand node
        auto children = expand_node(tree, node_id, query);

        // Add children to queue
        for (int child_id : children) {
            queue.push(child_id);
        }
    }
}

void TreeOfThoughtAgent::search_dfs(
    ReasoningTree& tree,
    int root_id,
    const std::string& query
) {
    std::stack<int> stack;
    stack.push(root_id);

    while (!stack.empty()) {
        int node_id = stack.top();
        stack.pop();

        auto node = tree.get_node(node_id);
        if (!node) {
            continue;
        }

        // Stop at max depth
        if (node->depth >= config_.max_depth) {
            node->state = NodeState::Terminal;
            continue;
        }

        // Expand node
        auto children = expand_node(tree, node_id, query);

        // Add children to stack (reverse order for left-to-right DFS)
        for (auto it = children.rbegin(); it != children.rend(); ++it) {
            stack.push(*it);
        }
    }
}

void TreeOfThoughtAgent::search_best_first(
    ReasoningTree& tree,
    int root_id,
    const std::string& query
) {
    // Priority queue ordered by score (highest first)
    auto comparator = [&tree](int a, int b) {
        auto node_a = tree.get_node(a);
        auto node_b = tree.get_node(b);
        if (!node_a || !node_b) {
            return false;
        }
        return node_a->score < node_b->score;  // Min-heap, so invert for max-heap behavior
    };

    std::priority_queue<int, std::vector<int>, decltype(comparator)> pq(comparator);
    pq.push(root_id);

    while (!pq.empty()) {
        int node_id = pq.top();
        pq.pop();

        auto node = tree.get_node(node_id);
        if (!node) {
            continue;
        }

        // Stop at max depth
        if (node->depth >= config_.max_depth) {
            node->state = NodeState::Terminal;
            continue;
        }

        // Expand node
        auto children = expand_node(tree, node_id, query);

        // Add children to priority queue
        for (int child_id : children) {
            pq.push(child_id);
        }
    }
}

std::string TreeOfThoughtAgent::strategy_to_string(SearchStrategy strategy) const {
    switch (strategy) {
        case SearchStrategy::BFS:
            return "bfs";
        case SearchStrategy::DFS:
            return "dfs";
        case SearchStrategy::BestFirst:
            return "best-first";
        default:
            return "unknown";
    }
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
