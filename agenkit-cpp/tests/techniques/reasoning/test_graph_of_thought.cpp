/**
 * @file test_graph_of_thought.cpp
 * @brief Tests for Graph-of-Thought reasoning technique
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/graph_of_thought.hpp"
#include "agenkit/techniques/reasoning/reasoning_graph.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <atomic>
#include <sstream>

using namespace agenkit::techniques::reasoning;
using namespace agenkit::core;

/**
 * @brief Mock agent for testing GraphOfThought
 */
class GraphMockAgent : public Agent {
public:
    GraphMockAgent() : call_count_(0) {}

    std::string name() const override {
        return "graph_mock_agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() mutable {
            int count = ++call_count_;

            std::string response;
            if (count == 1 || std::string(msg.content_as_str()).find("Premises") != std::string::npos) {
                response = "1. Premise one\n2. Premise two";
            } else if (count == 2 || std::string(msg.content_as_str()).find("thoughts") != std::string::npos) {
                response = "1. Intermediate thought\n2. Another thought";
            } else if (std::string(msg.content_as_str()).find("relationship") != std::string::npos) {
                response = "SUPPORT";
            } else if (std::string(msg.content_as_str()).find("conclusion") != std::string::npos) {
                response = "This is the final conclusion";
            } else {
                response = "Generic response " + std::to_string(count);
            }

            return Result<Message, AgentError>::ok(
                Message::with_text("assistant", response)
            );
        });
    }

    int call_count() const {
        return call_count_.load();
    }

private:
    std::atomic<int> call_count_;
};

// ============================================================================
// ReasoningGraph Tests
// ============================================================================

TEST(ReasoningGraphTest, GraphCreation) {
    ReasoningGraph graph;

    auto stats = graph.statistics();
    EXPECT_EQ(stats.num_nodes, 0);
    EXPECT_EQ(stats.num_edges, 0);
}

TEST(ReasoningGraphTest, AddNode) {
    ReasoningGraph graph;

    size_t node_id1 = graph.add_node("Premise 1", NodeType::PREMISE, 0.9);
    size_t node_id2 = graph.add_node("Thought 1", NodeType::INTERMEDIATE, 0.7);

    auto stats = graph.statistics();
    EXPECT_EQ(stats.num_nodes, 2);

    auto* node1 = graph.get_node(node_id1);
    ASSERT_NE(node1, nullptr);
    EXPECT_EQ(node1->content, "Premise 1");
    EXPECT_EQ(node1->node_type, NodeType::PREMISE);
    EXPECT_DOUBLE_EQ(node1->confidence, 0.9);

    auto* node2 = graph.get_node(node_id2);
    ASSERT_NE(node2, nullptr);
    EXPECT_EQ(node2->node_type, NodeType::INTERMEDIATE);
}

TEST(ReasoningGraphTest, AddEdge) {
    ReasoningGraph graph;

    size_t node1 = graph.add_node("A", NodeType::PREMISE);
    size_t node2 = graph.add_node("B", NodeType::INTERMEDIATE);

    bool success = graph.add_edge(node1, node2, EdgeType::SUPPORTS, 0.8);
    EXPECT_TRUE(success);

    auto stats = graph.statistics();
    EXPECT_EQ(stats.num_edges, 1);

    auto edges = graph.get_edges();
    EXPECT_EQ(edges.size(), 1);
    EXPECT_EQ(edges[0].from_node, node1);
    EXPECT_EQ(edges[0].to_node, node2);
    EXPECT_EQ(edges[0].edge_type, EdgeType::SUPPORTS);
    EXPECT_DOUBLE_EQ(edges[0].strength, 0.8);
}

TEST(ReasoningGraphTest, AddEdgeInvalidNodes) {
    ReasoningGraph graph;

    size_t node1 = graph.add_node("A", NodeType::PREMISE);

    // Try to add edge with invalid node
    bool success = graph.add_edge(node1, 999, EdgeType::SUPPORTS);
    EXPECT_FALSE(success);
}

TEST(ReasoningGraphTest, FindPaths) {
    ReasoningGraph graph;

    // Create chain: A -> B -> C
    size_t node_a = graph.add_node("A", NodeType::PREMISE);
    size_t node_b = graph.add_node("B", NodeType::INTERMEDIATE);
    size_t node_c = graph.add_node("C", NodeType::CONCLUSION);

    graph.add_edge(node_a, node_b, EdgeType::SUPPORTS);
    graph.add_edge(node_b, node_c, EdgeType::SUPPORTS);

    auto paths = graph.find_paths(node_a, node_c);

    EXPECT_EQ(paths.size(), 1);
    EXPECT_EQ(paths[0].size(), 3);
    EXPECT_EQ(paths[0][0], node_a);
    EXPECT_EQ(paths[0][1], node_b);
    EXPECT_EQ(paths[0][2], node_c);
}

TEST(ReasoningGraphTest, FindPathsMultiple) {
    ReasoningGraph graph;

    // Create diamond: A -> B -> D, A -> C -> D
    size_t node_a = graph.add_node("A", NodeType::PREMISE);
    size_t node_b = graph.add_node("B", NodeType::INTERMEDIATE);
    size_t node_c = graph.add_node("C", NodeType::INTERMEDIATE);
    size_t node_d = graph.add_node("D", NodeType::CONCLUSION);

    graph.add_edge(node_a, node_b, EdgeType::SUPPORTS);
    graph.add_edge(node_a, node_c, EdgeType::SUPPORTS);
    graph.add_edge(node_b, node_d, EdgeType::SUPPORTS);
    graph.add_edge(node_c, node_d, EdgeType::SUPPORTS);

    auto paths = graph.find_paths(node_a, node_d);

    EXPECT_EQ(paths.size(), 2);  // Two paths from A to D
}

TEST(ReasoningGraphTest, HasCycleFalse) {
    ReasoningGraph graph;

    size_t node_a = graph.add_node("A", NodeType::PREMISE);
    size_t node_b = graph.add_node("B", NodeType::INTERMEDIATE);
    size_t node_c = graph.add_node("C", NodeType::CONCLUSION);

    graph.add_edge(node_a, node_b, EdgeType::SUPPORTS);
    graph.add_edge(node_b, node_c, EdgeType::SUPPORTS);

    EXPECT_FALSE(graph.has_cycle());
}

TEST(ReasoningGraphTest, HasCycleTrue) {
    ReasoningGraph graph;

    size_t node_a = graph.add_node("A", NodeType::INTERMEDIATE);
    size_t node_b = graph.add_node("B", NodeType::INTERMEDIATE);
    size_t node_c = graph.add_node("C", NodeType::INTERMEDIATE);

    graph.add_edge(node_a, node_b, EdgeType::SUPPORTS);
    graph.add_edge(node_b, node_c, EdgeType::SUPPORTS);
    graph.add_edge(node_c, node_a, EdgeType::SUPPORTS);  // Creates cycle

    EXPECT_TRUE(graph.has_cycle());
}

TEST(ReasoningGraphTest, GetPremises) {
    ReasoningGraph graph;

    graph.add_node("Premise 1", NodeType::PREMISE);
    graph.add_node("Thought 1", NodeType::INTERMEDIATE);
    graph.add_node("Premise 2", NodeType::PREMISE);

    auto premises = graph.get_premises();
    EXPECT_EQ(premises.size(), 2);
}

TEST(ReasoningGraphTest, GetConclusions) {
    ReasoningGraph graph;

    graph.add_node("Premise 1", NodeType::PREMISE);
    graph.add_node("Conclusion 1", NodeType::CONCLUSION);
    graph.add_node("Conclusion 2", NodeType::CONCLUSION);

    auto conclusions = graph.get_conclusions();
    EXPECT_EQ(conclusions.size(), 2);
}

TEST(ReasoningGraphTest, GetPathScore) {
    ReasoningGraph graph;

    size_t node_a = graph.add_node("A", NodeType::PREMISE, 0.9);
    size_t node_b = graph.add_node("B", NodeType::INTERMEDIATE, 0.8);
    size_t node_c = graph.add_node("C", NodeType::CONCLUSION, 0.7);

    graph.add_edge(node_a, node_b, EdgeType::SUPPORTS, 0.9);
    graph.add_edge(node_b, node_c, EdgeType::SUPPORTS, 0.8);

    std::vector<size_t> path = {node_a, node_b, node_c};
    double score = graph.get_path_score(path);

    EXPECT_GE(score, 0.0);
    EXPECT_LE(score, 1.0);
    EXPECT_GT(score, 0.6);  // Should be reasonably high
}

TEST(ReasoningGraphTest, GraphStatistics) {
    ReasoningGraph graph;

    graph.add_node("Premise", NodeType::PREMISE, 0.9);
    graph.add_node("Thought", NodeType::INTERMEDIATE, 0.7);
    graph.add_node("Conclusion", NodeType::CONCLUSION, 0.8);

    auto nodes = graph.get_nodes();
    if (nodes.size() >= 2) {
        graph.add_edge(nodes[0]->id, nodes[1]->id, EdgeType::SUPPORTS);
    }

    auto stats = graph.statistics();

    EXPECT_EQ(stats.num_nodes, 3);
    EXPECT_EQ(stats.num_edges, 1);
    EXPECT_TRUE(stats.node_types.find("premise") != stats.node_types.end());
    EXPECT_TRUE(stats.edge_types.find("supports") != stats.edge_types.end());
}

// ============================================================================
// GraphOfThought Agent Tests
// ============================================================================

TEST(GraphOfThoughtTest, BasicFunctionality) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.max_nodes = 10;
    config.max_edges = 20;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check technique
    EXPECT_EQ(metadata["technique"].get<std::string>(), "graph_of_thought");

    // Check metadata fields
    EXPECT_TRUE(metadata.contains("num_nodes"));
    EXPECT_TRUE(metadata.contains("num_edges"));

    // Check content is non-empty
    std::string content = response.content_as_str();
    EXPECT_GT(content.length(), 0);
}

TEST(GraphOfThoughtTest, NameAndCapabilities) {
    auto mock = std::make_shared<GraphMockAgent>();
    GraphOfThoughtAgent agent(mock, GraphOfThoughtConfig{});

    EXPECT_EQ(agent.name(), "graph_of_thought");

    auto caps = agent.capabilities();
    EXPECT_GE(caps.size(), 3);

    std::vector<std::string> expected_caps = {
        "reasoning", "graph_of_thought", "multi_hop_reasoning"
    };

    for (const auto& expected : expected_caps) {
        EXPECT_NE(std::find(caps.begin(), caps.end(), expected), caps.end());
    }
}

TEST(GraphOfThoughtTest, MaxNodesLimit) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.max_nodes = 5;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    int num_nodes = metadata["num_nodes"].get<int>();
    EXPECT_LE(num_nodes, 5);
}

TEST(GraphOfThoughtTest, MaxEdgesLimit) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.max_nodes = 10;
    config.max_edges = 5;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    int num_edges = metadata["num_edges"].get<int>();
    EXPECT_LE(num_edges, 5);
}

TEST(GraphOfThoughtTest, PathBasedAggregation) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.aggregator = AggregatorType::PATH_BASED;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["aggregator"].get<std::string>(), "path_based");
    EXPECT_GT(response.content_as_str().length(), 0);
}

TEST(GraphOfThoughtTest, NodeBasedAggregation) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.aggregator = AggregatorType::NODE_BASED;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["aggregator"].get<std::string>(), "node_based");
    EXPECT_GT(response.content_as_str().length(), 0);
}

TEST(GraphOfThoughtTest, MetadataCompleteness) {
    auto mock = std::make_shared<GraphMockAgent>();
    GraphOfThoughtAgent agent(mock, GraphOfThoughtConfig{});

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check all required fields
    EXPECT_TRUE(metadata.contains("technique"));
    EXPECT_TRUE(metadata.contains("num_nodes"));
    EXPECT_TRUE(metadata.contains("num_edges"));
    EXPECT_TRUE(metadata.contains("has_cycles"));
    EXPECT_TRUE(metadata.contains("aggregator"));
    EXPECT_TRUE(metadata.contains("allow_cycles"));

    // Verify technique name
    EXPECT_EQ(metadata["technique"].get<std::string>(), "graph_of_thought");
}

TEST(GraphOfThoughtTest, AllowCycles) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.allow_cycles = true;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_TRUE(metadata["allow_cycles"].get<bool>());
}

TEST(GraphOfThoughtTest, DisallowCycles) {
    auto mock = std::make_shared<GraphMockAgent>();

    GraphOfThoughtConfig config;
    config.allow_cycles = false;

    GraphOfThoughtAgent agent(mock, config);

    auto message = Message::with_text("user", "Test problem");
    auto future = agent.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_FALSE(metadata["allow_cycles"].get<bool>());
}

// ============================================================================
// Edge and Node Type Tests
// ============================================================================

TEST(EdgeTypeTest, EdgeTypeValues) {
    // Test that edge types are distinct
    EXPECT_NE(EdgeType::SUPPORTS, EdgeType::DEPENDS_ON);
    EXPECT_NE(EdgeType::SUPPORTS, EdgeType::CONTRADICTS);
    EXPECT_NE(EdgeType::SUPPORTS, EdgeType::REFINES);
}

TEST(NodeTypeTest, NodeTypeValues) {
    // Test that node types are distinct
    EXPECT_NE(NodeType::PREMISE, NodeType::INTERMEDIATE);
    EXPECT_NE(NodeType::PREMISE, NodeType::CONCLUSION);
    EXPECT_NE(NodeType::INTERMEDIATE, NodeType::CONCLUSION);
}

TEST(ThoughtNodeTest, NodeConstruction) {
    ThoughtNode node(1, "Test content", NodeType::PREMISE, 0.9);

    EXPECT_EQ(node.id, 1);
    EXPECT_EQ(node.content, "Test content");
    EXPECT_EQ(node.node_type, NodeType::PREMISE);
    EXPECT_DOUBLE_EQ(node.confidence, 0.9);
}

TEST(LogicalEdgeTest, EdgeConstruction) {
    LogicalEdge edge(1, 2, EdgeType::SUPPORTS, 0.8);

    EXPECT_EQ(edge.from_node, 1);
    EXPECT_EQ(edge.to_node, 2);
    EXPECT_EQ(edge.edge_type, EdgeType::SUPPORTS);
    EXPECT_DOUBLE_EQ(edge.strength, 0.8);
}
