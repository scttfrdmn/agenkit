/**
 * @file test_reasoning_tree.cpp
 * @brief Unit tests for ReasoningTree data structure
 *
 * Verifies tree construction, node relationships, state transitions,
 * depth tracking, pruning, and content preservation.
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/reasoning_tree.hpp"

using namespace agenkit::techniques::reasoning;

// 1. Creating the root node yields id=0, depth=0, and no parent
TEST(ReasoningTree, NodeCreation) {
    ReasoningTree tree;
    int root_id = tree.create_root("initial query");
    auto root = tree.get_node(root_id);

    ASSERT_NE(root, nullptr);
    EXPECT_EQ(root->id, 0);
    EXPECT_EQ(root->depth, 0);
    EXPECT_FALSE(root->parent_id.has_value());
    EXPECT_TRUE(root->children_ids.empty());
}

// 2. Adding a child updates parent's children_ids and sets child's parent_id
TEST(ReasoningTree, AddChild) {
    ReasoningTree tree;
    int root_id = tree.create_root("root content");
    int child_id = tree.add_child(root_id, "child content", 0.75);

    auto root = tree.get_node(root_id);
    auto child = tree.get_node(child_id);

    ASSERT_NE(root, nullptr);
    ASSERT_NE(child, nullptr);

    // Root knows about child
    ASSERT_EQ(root->children_ids.size(), 1u);
    EXPECT_EQ(root->children_ids[0], child_id);

    // Child knows about parent
    ASSERT_TRUE(child->parent_id.has_value());
    EXPECT_EQ(child->parent_id.value(), root_id);
}

// 3. Node state can be transitioned: Open → Active → Evaluated → Terminal
TEST(ReasoningTree, NodeStateTransitions) {
    ReasoningTree tree;
    int root_id = tree.create_root("query");
    auto node = tree.get_node(root_id);

    ASSERT_NE(node, nullptr);
    // Freshly created root starts as Open
    EXPECT_EQ(node->state, NodeState::Open);

    // Transition through states
    node->state = NodeState::Active;
    EXPECT_EQ(node->state, NodeState::Active);

    node->state = NodeState::Evaluated;
    EXPECT_EQ(node->state, NodeState::Evaluated);

    node->state = NodeState::Terminal;
    EXPECT_EQ(node->state, NodeState::Terminal);
}

// 4. Score assigned via add_child is retrievable from the node
TEST(ReasoningTree, ScoreAssignment) {
    ReasoningTree tree;
    int root_id = tree.create_root("root");
    int child_id = tree.add_child(root_id, "child", 0.85);
    auto child = tree.get_node(child_id);

    ASSERT_NE(child, nullptr);
    EXPECT_DOUBLE_EQ(child->score, 0.85);
}

// 5. A node with no children is a leaf; a node with children is not
TEST(ReasoningTree, IsLeaf) {
    ReasoningTree tree;
    int root_id = tree.create_root("root");

    auto root = tree.get_node(root_id);
    ASSERT_NE(root, nullptr);
    EXPECT_TRUE(root->is_leaf());

    int child_id = tree.add_child(root_id, "child", 0.5);
    (void)child_id;

    // Root now has a child, so it is no longer a leaf
    EXPECT_FALSE(root->is_leaf());

    // Child has no children, so it is a leaf
    auto child = tree.get_node(child_id);
    ASSERT_NE(child, nullptr);
    EXPECT_TRUE(child->is_leaf());
}

// 6. Depth is 0 for root, 1 for direct child, 2 for grandchild
TEST(ReasoningTree, Depth) {
    ReasoningTree tree;
    int root_id = tree.create_root("root");
    int child_id = tree.add_child(root_id, "child", 0.6);
    int grandchild_id = tree.add_child(child_id, "grandchild", 0.7);

    auto root = tree.get_node(root_id);
    auto child = tree.get_node(child_id);
    auto grandchild = tree.get_node(grandchild_id);

    ASSERT_NE(root, nullptr);
    ASSERT_NE(child, nullptr);
    ASSERT_NE(grandchild, nullptr);

    EXPECT_EQ(root->depth, 0);
    EXPECT_EQ(child->depth, 1);
    EXPECT_EQ(grandchild->depth, 2);
}

// 7. prune_node sets the node's state to Pruned
TEST(ReasoningTree, PrunedState) {
    ReasoningTree tree;
    int root_id = tree.create_root("root");
    int child_id = tree.add_child(root_id, "child to prune", 0.2);

    tree.prune_node(child_id);

    auto child = tree.get_node(child_id);
    ASSERT_NE(child, nullptr);
    EXPECT_EQ(child->state, NodeState::Pruned);
}

// 8. The content string passed to create_root / add_child is preserved exactly
TEST(ReasoningTree, ContentPreserved) {
    const std::string root_content = "This is the root reasoning step.";
    const std::string child_content = "This is a child reasoning step.";

    ReasoningTree tree;
    int root_id = tree.create_root(root_content);
    int child_id = tree.add_child(root_id, child_content, 0.9);

    auto root = tree.get_node(root_id);
    auto child = tree.get_node(child_id);

    ASSERT_NE(root, nullptr);
    ASSERT_NE(child, nullptr);
    EXPECT_EQ(root->content, root_content);
    EXPECT_EQ(child->content, child_content);
}
