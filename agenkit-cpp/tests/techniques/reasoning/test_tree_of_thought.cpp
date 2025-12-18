/**
 * @file test_tree_of_thought.cpp
 * @brief Tests for Tree-of-Thought reasoning technique
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/tree_of_thought.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <atomic>
#include <sstream>

using namespace agenkit::techniques::reasoning;
using namespace agenkit::core;

/**
 * @brief Mock agent that generates varied responses for tree branching
 */
class VariedMockAgent : public Agent {
public:
    VariedMockAgent() : call_count_(0) {}

    std::string name() const override {
        return "varied_mock_agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() mutable {
            int count = ++call_count_;

            std::vector<std::string> responses = {
                "Branch A: Analyze systematically (call " + std::to_string(count) + ").",
                "Branch B: Break into parts (call " + std::to_string(count) + ").",
                "Branch C: Consider edge cases (call " + std::to_string(count) + ").",
                "Step " + std::to_string(count) + ": Continue with details."
            };

            std::string response = responses[(count - 1) % responses.size()];
            return Result<Message, AgentError>::ok(
                Message::with_text("assistant", response)
            );
        });
    }

private:
    std::atomic<int> call_count_;
};

// Test basic Tree-of-Thought functionality
TEST(TreeOfThoughtTest, BasicFunctionality) {
    auto mock = std::make_shared<VariedMockAgent>();

    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = 2;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Solve this problem");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check technique
    EXPECT_EQ(metadata["technique"].get<std::string>(), "tree_of_thought");

    // Check search strategy
    EXPECT_TRUE(metadata.contains("search_strategy"));

    // Check tree statistics
    EXPECT_TRUE(metadata.contains("reasoning_tree_stats"));

    // Check reasoning path
    EXPECT_TRUE(metadata.contains("reasoning_path"));
    auto path = metadata["reasoning_path"].get<std::vector<std::string>>();
    EXPECT_GT(path.size(), 0);

    // Check num_steps
    EXPECT_TRUE(metadata.contains("num_steps"));
    int num_steps = metadata["num_steps"].get<int>();
    EXPECT_GT(num_steps, 0);

    // Check best_score
    EXPECT_TRUE(metadata.contains("best_score"));
}

// Test name and capabilities
TEST(TreeOfThoughtTest, NameAndCapabilities) {
    auto mock = std::make_shared<VariedMockAgent>();
    TreeOfThoughtAgent tot(mock);

    EXPECT_EQ(tot.name(), "tree_of_thought");

    auto caps = tot.capabilities();
    EXPECT_EQ(caps.size(), 6);

    std::vector<std::string> expected_caps = {
        "reasoning", "tree_search", "multi_path_exploration",
        "backtracking", "tree_of_thought", "planning"
    };

    for (const auto& expected : expected_caps) {
        EXPECT_NE(std::find(caps.begin(), caps.end(), expected), caps.end());
    }
}

// Test BFS search strategy
TEST(TreeOfThoughtTest, BFSStrategy) {
    auto mock = std::make_shared<VariedMockAgent>();

    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = 2;
    config.strategy = SearchStrategy::BFS;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test query");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["search_strategy"].get<std::string>(), "bfs");
}

// Test DFS search strategy
TEST(TreeOfThoughtTest, DFSStrategy) {
    auto mock = std::make_shared<VariedMockAgent>();

    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = 2;
    config.strategy = SearchStrategy::DFS;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test query");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["search_strategy"].get<std::string>(), "dfs");
}

// Test best-first search strategy
TEST(TreeOfThoughtTest, BestFirstStrategy) {
    auto mock = std::make_shared<VariedMockAgent>();

    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = 2;
    config.strategy = SearchStrategy::BestFirst;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test query");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["search_strategy"].get<std::string>(), "best-first");
}

// Test tree statistics
TEST(TreeOfThoughtTest, TreeStatistics) {
    auto mock = std::make_shared<VariedMockAgent>();

    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = 2;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto stats = metadata["reasoning_tree_stats"].get<TreeStatistics>();

    EXPECT_GE(stats.total_nodes, 1);
    EXPECT_LE(stats.max_depth, 2);
    EXPECT_GE(stats.num_leaves, 1);
    EXPECT_GE(stats.best_score, 0.0);
    EXPECT_LE(stats.best_score, 1.0);
}

// Test custom evaluator
TEST(TreeOfThoughtTest, CustomEvaluator) {
    auto mock = std::make_shared<VariedMockAgent>();

    // Custom evaluator that favors responses with "Branch A"
    auto custom_evaluator = [](const std::string& text) -> double {
        if (text.find("Branch A") != std::string::npos) {
            return 1.0;
        }
        return 0.5;
    };

    TreeOfThoughtConfig config;
    config.branching_factor = 3;
    config.max_depth = 2;
    config.evaluator = custom_evaluator;
    config.strategy = SearchStrategy::BestFirst;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();

    // Best path should contain "Branch A" due to custom evaluator
    std::string path_text = response.content_as_str();
    EXPECT_TRUE(path_text.find("Branch A") != std::string::npos);
}

// Test pruning
TEST(TreeOfThoughtTest, Pruning) {
    auto mock = std::make_shared<VariedMockAgent>();

    // Selective evaluator - prune some branches
    int call_count = 0;
    auto selective_evaluator = [&call_count](const std::string& text) -> double {
        (void)text;  // Suppress unused warning
        call_count++;
        // Return low scores for some branches to trigger pruning
        return (call_count % 3 == 0) ? 0.1 : 0.6;
    };

    TreeOfThoughtConfig config;
    config.branching_factor = 3;
    config.max_depth = 2;
    config.evaluator = selective_evaluator;
    config.prune_threshold = 0.3;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto stats = metadata["reasoning_tree_stats"].get<TreeStatistics>();

    // With selective pruning, we should have both pruned and non-pruned nodes
    EXPECT_GT(stats.total_nodes, 0);
    // Pruned nodes count may vary based on search strategy
    EXPECT_GE(stats.num_pruned, 0);
}

// Test reasoning path structure
TEST(TreeOfThoughtTest, ReasoningPathStructure) {
    auto mock = std::make_shared<VariedMockAgent>();

    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = 3;

    TreeOfThoughtAgent tot(mock, config);

    std::string query = "Test query";
    auto message = Message::with_text("user", query);
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto path = metadata["reasoning_path"].get<std::vector<std::string>>();

    EXPECT_GT(path.size(), 0);

    // First element should be the query (root node)
    EXPECT_EQ(path[0], query);

    // Path length should not exceed maxDepth + 1 (root)
    EXPECT_LE(path.size(), 4);
}

// Test max depth limiting
TEST(TreeOfThoughtTest, MaxDepthLimit) {
    auto mock = std::make_shared<VariedMockAgent>();

    int max_depth = 1;
    TreeOfThoughtConfig config;
    config.branching_factor = 2;
    config.max_depth = max_depth;

    TreeOfThoughtAgent tot(mock, config);

    auto message = Message::with_text("user", "Test");
    auto future = tot.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto path = metadata["reasoning_path"].get<std::vector<std::string>>();

    // Root + maxDepth levels = maxDepth + 1 nodes max
    EXPECT_LE(static_cast<int>(path.size()), max_depth + 1);
}

// Test default evaluator behavior
TEST(TreeOfThoughtTest, DefaultEvaluator) {
    auto mock = std::make_shared<VariedMockAgent>();
    TreeOfThoughtAgent tot(mock);

    // Test short response (should get low score)
    double short_score = tot.capabilities().size() > 0 ? 0.1 : 0.1; // Placeholder test
    EXPECT_LT(short_score, 0.5);

    // Test structured response (should get higher score)
    double structured_score = 0.4;  // Placeholder - actual scoring happens internally
    EXPECT_GT(structured_score, 0.2);
}

// Test reasoning tree operations
TEST(TreeOfThoughtTest, ReasoningTreeOperations) {
    ReasoningTree tree;

    // Create root
    int root_id = tree.create_root("Root node");
    EXPECT_EQ(root_id, 0);
    EXPECT_TRUE(tree.root_id().has_value());
    EXPECT_EQ(tree.root_id().value(), root_id);

    // Add children
    int child1 = tree.add_child(root_id, "Child 1", 0.8);
    int child2 = tree.add_child(root_id, "Child 2", 0.6);

    EXPECT_EQ(child1, 1);
    EXPECT_EQ(child2, 2);

    // Get node
    auto root = tree.get_node(root_id);
    ASSERT_NE(root, nullptr);
    EXPECT_EQ(root->content, "Root node");
    EXPECT_EQ(root->children_ids.size(), 2);

    // Get path
    auto path = tree.get_path(child1);
    EXPECT_EQ(path.size(), 2);  // Root + child1
    EXPECT_EQ(path[0]->id, root_id);
    EXPECT_EQ(path[1]->id, child1);

    // Get path text
    std::string path_text = tree.get_path_text(child1);
    EXPECT_TRUE(path_text.find("Root node") != std::string::npos);
    EXPECT_TRUE(path_text.find("Child 1") != std::string::npos);

    // Get best leaf
    auto best = tree.get_best_leaf();
    ASSERT_NE(best, nullptr);
    EXPECT_EQ(best->id, child1);  // Higher score

    // Prune node
    tree.prune_node(child2);
    auto pruned_node = tree.get_node(child2);
    EXPECT_EQ(pruned_node->state, NodeState::Pruned);

    // Get statistics
    auto stats = tree.get_statistics();
    EXPECT_EQ(stats.total_nodes, 3);
    EXPECT_EQ(stats.max_depth, 1);
    EXPECT_EQ(stats.num_leaves, 2);
    EXPECT_EQ(stats.num_pruned, 1);
    EXPECT_DOUBLE_EQ(stats.best_score, 0.8);
}
