/**
 * @file test_reasoning_graph.cpp
 * @brief Unit tests for ReasoningGraph data structure
 *
 * Verifies graph construction, node/edge relationships, cycle detection,
 * and content preservation for the Graph-of-Thought data structure.
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/reasoning_graph.hpp"

using namespace agenkit::techniques::reasoning;

// 1. NodeType enum values are distinct from each other
TEST(ReasoningGraph, NodeTypes) {
    EXPECT_NE(static_cast<int>(NodeType::PREMISE),
              static_cast<int>(NodeType::INTERMEDIATE));
    EXPECT_NE(static_cast<int>(NodeType::INTERMEDIATE),
              static_cast<int>(NodeType::CONCLUSION));
    EXPECT_NE(static_cast<int>(NodeType::PREMISE),
              static_cast<int>(NodeType::CONCLUSION));
}

// 2. EdgeType enum values are all distinct
TEST(ReasoningGraph, EdgeTypes) {
    EXPECT_NE(static_cast<int>(EdgeType::SUPPORTS),
              static_cast<int>(EdgeType::DEPENDS_ON));
    EXPECT_NE(static_cast<int>(EdgeType::DEPENDS_ON),
              static_cast<int>(EdgeType::CONTRADICTS));
    EXPECT_NE(static_cast<int>(EdgeType::CONTRADICTS),
              static_cast<int>(EdgeType::REFINES));
    EXPECT_NE(static_cast<int>(EdgeType::SUPPORTS),
              static_cast<int>(EdgeType::REFINES));
}

// 3. Adding a node yields a valid, retrievable node
TEST(ReasoningGraph, AddNode) {
    ReasoningGraph graph;
    size_t node_id = graph.add_node("premise content", NodeType::PREMISE, 0.9);
    const ThoughtNode* node = graph.get_node(node_id);

    ASSERT_NE(node, nullptr);
    EXPECT_EQ(node->id, node_id);
    EXPECT_EQ(node->content, "premise content");
    EXPECT_EQ(node->node_type, NodeType::PREMISE);
    EXPECT_DOUBLE_EQ(node->confidence, 0.9);
}

// 4. Adding an edge between two nodes succeeds and is reflected in the graph
TEST(ReasoningGraph, AddEdge) {
    ReasoningGraph graph;
    size_t a = graph.add_node("premise", NodeType::PREMISE);
    size_t b = graph.add_node("conclusion", NodeType::CONCLUSION);

    bool ok = graph.add_edge(a, b, EdgeType::SUPPORTS, 0.8);
    EXPECT_TRUE(ok);

    // Edge should appear in the graph's edge list
    const auto& edges = graph.get_edges();
    ASSERT_EQ(edges.size(), 1u);
    EXPECT_EQ(edges[0].from_node, a);
    EXPECT_EQ(edges[0].to_node, b);
    EXPECT_EQ(edges[0].edge_type, EdgeType::SUPPORTS);
}

// 5. A graph with a back-edge cycle is detected as cyclic
TEST(ReasoningGraph, CycleDetection) {
    ReasoningGraph graph;
    size_t a = graph.add_node("A", NodeType::PREMISE);
    size_t b = graph.add_node("B", NodeType::INTERMEDIATE);

    graph.add_edge(a, b, EdgeType::SUPPORTS);
    graph.add_edge(b, a, EdgeType::SUPPORTS); // creates cycle A→B→A

    EXPECT_TRUE(graph.has_cycle());
}

// 6. A linear chain A→B→C has no cycle
TEST(ReasoningGraph, AcyclicNoCycle) {
    ReasoningGraph graph;
    size_t a = graph.add_node("A", NodeType::PREMISE);
    size_t b = graph.add_node("B", NodeType::INTERMEDIATE);
    size_t c = graph.add_node("C", NodeType::CONCLUSION);

    graph.add_edge(a, b, EdgeType::SUPPORTS);
    graph.add_edge(b, c, EdgeType::SUPPORTS);

    EXPECT_FALSE(graph.has_cycle());
}

// 7. A freshly created graph has 0 nodes and 0 edges
TEST(ReasoningGraph, EmptyGraph) {
    ReasoningGraph graph;
    auto stats = graph.statistics();

    EXPECT_EQ(stats.num_nodes, 0u);
    EXPECT_EQ(stats.num_edges, 0u);
    EXPECT_FALSE(stats.has_cycles);
}

// 8. Node content is preserved exactly after add_node
TEST(ReasoningGraph, NodeContentPreserved) {
    const std::string content = "The sky is blue because of Rayleigh scattering.";
    ReasoningGraph graph;
    size_t id = graph.add_node(content, NodeType::CONCLUSION, 0.95);
    const ThoughtNode* node = graph.get_node(id);

    ASSERT_NE(node, nullptr);
    EXPECT_EQ(node->content, content);
}
