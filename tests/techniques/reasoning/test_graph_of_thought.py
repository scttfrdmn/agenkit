"""Tests for Graph-of-Thought reasoning technique."""

import pytest
from agenkit import Message
from agenkit.techniques.reasoning import (
    GraphOfThought,
    ReasoningGraph,
    ThoughtNode,
    LogicalEdge,
    NodeType,
    EdgeType
)


# Test ReasoningGraph Data Structure

def test_graph_creation():
    """Test creating an empty reasoning graph."""
    graph = ReasoningGraph()
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_add_node():
    """Test adding nodes to graph."""
    graph = ReasoningGraph()

    node_id1 = graph.add_node("Premise 1", NodeType.PREMISE, confidence=0.9)
    node_id2 = graph.add_node("Thought 1", NodeType.INTERMEDIATE, confidence=0.7)

    assert len(graph.nodes) == 2
    assert graph.get_node(node_id1).content == "Premise 1"
    assert graph.get_node(node_id2).node_type == NodeType.INTERMEDIATE


def test_add_edge():
    """Test adding edges between nodes."""
    graph = ReasoningGraph()

    node1 = graph.add_node("A", NodeType.PREMISE)
    node2 = graph.add_node("B", NodeType.INTERMEDIATE)

    graph.add_edge(node1, node2, EdgeType.SUPPORTS, strength=0.8)

    assert len(graph.edges) == 1
    assert graph.edges[0].from_node == node1
    assert graph.edges[0].to_node == node2
    assert graph.edges[0].edge_type == EdgeType.SUPPORTS


def test_edge_invalid_nodes():
    """Test adding edge with invalid nodes raises error."""
    graph = ReasoningGraph()
    node1 = graph.add_node("A", NodeType.PREMISE)

    with pytest.raises(ValueError):
        graph.add_edge(node1, 999, EdgeType.SUPPORTS)  # Invalid node


def test_get_outgoing_edges():
    """Test getting outgoing edges from node."""
    graph = ReasoningGraph()

    node1 = graph.add_node("A", NodeType.PREMISE)
    node2 = graph.add_node("B", NodeType.INTERMEDIATE)
    node3 = graph.add_node("C", NodeType.INTERMEDIATE)

    graph.add_edge(node1, node2, EdgeType.SUPPORTS)
    graph.add_edge(node1, node3, EdgeType.SUPPORTS)

    outgoing = graph.get_outgoing_edges(node1)
    assert len(outgoing) == 2


def test_get_incoming_edges():
    """Test getting incoming edges to node."""
    graph = ReasoningGraph()

    node1 = graph.add_node("A", NodeType.PREMISE)
    node2 = graph.add_node("B", NodeType.PREMISE)
    node3 = graph.add_node("C", NodeType.INTERMEDIATE)

    graph.add_edge(node1, node3, EdgeType.SUPPORTS)
    graph.add_edge(node2, node3, EdgeType.SUPPORTS)

    incoming = graph.get_incoming_edges(node3)
    assert len(incoming) == 2


def test_find_paths():
    """Test finding paths between nodes."""
    graph = ReasoningGraph()

    # Create a chain: A -> B -> C
    node_a = graph.add_node("A", NodeType.PREMISE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)
    node_c = graph.add_node("C", NodeType.CONCLUSION)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_c, EdgeType.SUPPORTS)

    paths = graph.find_paths(node_a, node_c)

    assert len(paths) == 1
    assert paths[0] == [node_a, node_b, node_c]


def test_find_paths_multiple():
    """Test finding multiple paths between nodes."""
    graph = ReasoningGraph()

    # Create diamond: A -> B -> D, A -> C -> D
    node_a = graph.add_node("A", NodeType.PREMISE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)
    node_c = graph.add_node("C", NodeType.INTERMEDIATE)
    node_d = graph.add_node("D", NodeType.CONCLUSION)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_a, node_c, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_d, EdgeType.SUPPORTS)
    graph.add_edge(node_c, node_d, EdgeType.SUPPORTS)

    paths = graph.find_paths(node_a, node_d)

    assert len(paths) == 2  # Two paths


def test_has_cycle_false():
    """Test cycle detection on acyclic graph."""
    graph = ReasoningGraph()

    node_a = graph.add_node("A", NodeType.PREMISE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)
    node_c = graph.add_node("C", NodeType.CONCLUSION)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_c, EdgeType.SUPPORTS)

    assert not graph.has_cycle()


def test_has_cycle_true():
    """Test cycle detection on cyclic graph."""
    graph = ReasoningGraph()

    node_a = graph.add_node("A", NodeType.INTERMEDIATE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)
    node_c = graph.add_node("C", NodeType.INTERMEDIATE)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_c, EdgeType.SUPPORTS)
    graph.add_edge(node_c, node_a, EdgeType.SUPPORTS)  # Creates cycle

    assert graph.has_cycle()


def test_find_cycles():
    """Test finding all cycles in graph."""
    graph = ReasoningGraph()

    node_a = graph.add_node("A", NodeType.INTERMEDIATE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_a, EdgeType.SUPPORTS)  # Create cycle

    cycles = graph.find_cycles()
    assert len(cycles) >= 1


def test_topological_sort():
    """Test topological sorting of acyclic graph."""
    graph = ReasoningGraph()

    node_a = graph.add_node("A", NodeType.PREMISE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)
    node_c = graph.add_node("C", NodeType.CONCLUSION)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_c, EdgeType.SUPPORTS)

    topo_order = graph.topological_sort()

    assert topo_order is not None
    assert topo_order.index(node_a) < topo_order.index(node_b)
    assert topo_order.index(node_b) < topo_order.index(node_c)


def test_topological_sort_with_cycle():
    """Test topological sort returns None for cyclic graph."""
    graph = ReasoningGraph()

    node_a = graph.add_node("A", NodeType.INTERMEDIATE)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)
    graph.add_edge(node_b, node_a, EdgeType.SUPPORTS)

    topo_order = graph.topological_sort()
    assert topo_order is None


def test_get_premises():
    """Test getting all premise nodes."""
    graph = ReasoningGraph()

    graph.add_node("Premise 1", NodeType.PREMISE)
    graph.add_node("Thought 1", NodeType.INTERMEDIATE)
    graph.add_node("Premise 2", NodeType.PREMISE)

    premises = graph.get_premises()
    assert len(premises) == 2


def test_get_conclusions():
    """Test getting all conclusion nodes."""
    graph = ReasoningGraph()

    graph.add_node("Premise 1", NodeType.PREMISE)
    graph.add_node("Conclusion 1", NodeType.CONCLUSION)
    graph.add_node("Conclusion 2", NodeType.CONCLUSION)

    conclusions = graph.get_conclusions()
    assert len(conclusions) == 2


def test_get_path_score():
    """Test calculating path score."""
    graph = ReasoningGraph()

    node_a = graph.add_node("A", NodeType.PREMISE, confidence=0.9)
    node_b = graph.add_node("B", NodeType.INTERMEDIATE, confidence=0.8)
    node_c = graph.add_node("C", NodeType.CONCLUSION, confidence=0.7)

    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS, strength=0.9)
    graph.add_edge(node_b, node_c, EdgeType.SUPPORTS, strength=0.8)

    path = [node_a, node_b, node_c]
    score = graph.get_path_score(path)

    assert 0.0 <= score <= 1.0
    assert score > 0.6  # Should be reasonably high


def test_graph_statistics():
    """Test graph statistics."""
    graph = ReasoningGraph()

    graph.add_node("Premise", NodeType.PREMISE, confidence=0.9)
    graph.add_node("Thought", NodeType.INTERMEDIATE, confidence=0.7)
    graph.add_node("Conclusion", NodeType.CONCLUSION, confidence=0.8)

    node_a = list(graph.nodes.keys())[0]
    node_b = list(graph.nodes.keys())[1]
    graph.add_edge(node_a, node_b, EdgeType.SUPPORTS)

    stats = graph.statistics()

    assert stats["num_nodes"] == 3
    assert stats["num_edges"] == 1
    assert "premise" in stats["node_types"]
    assert "supports" in stats["edge_types"]
    assert isinstance(stats["has_cycles"], bool)
    assert 0.0 <= stats["avg_confidence"] <= 1.0


# Test GraphOfThought Agent

class MockLLM:
    """Mock LLM for testing GraphOfThought."""

    def __init__(self):
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock responses based on prompt type."""
        self.call_count += 1

        if "Identify the key facts" in prompt or "Premises" in prompt:
            return "1. Premise one\n2. Premise two"

        if "generate" in prompt.lower() and "thoughts" in prompt.lower():
            return "1. Intermediate thought\n2. Another thought"

        if "relationship" in prompt.lower():
            return "SUPPORT"

        if "final conclusion" in prompt:
            return "This is the final conclusion"

        return "Generic response"


@pytest.mark.asyncio
async def test_got_basic():
    """Test basic Graph-of-Thought functionality."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=10, max_edges=20)

    response = await agent.process(Message(role="user", content="Test problem"))

    assert response.content
    assert response.metadata["technique"] == "graph_of_thought"
    assert "graph" in response.metadata
    assert "num_nodes" in response.metadata


@pytest.mark.asyncio
async def test_got_graph_building():
    """Test graph building process."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=10)

    response = await agent.process(Message(role="user", content="Problem"))

    graph = response.metadata["graph"]
    assert len(graph.nodes) > 0
    assert isinstance(graph, ReasoningGraph)


@pytest.mark.asyncio
async def test_got_max_nodes():
    """Test max_nodes limit."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=5)

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.metadata["num_nodes"] <= 5


@pytest.mark.asyncio
async def test_got_max_edges():
    """Test max_edges limit."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=10, max_edges=5)

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.metadata["num_edges"] <= 5


@pytest.mark.asyncio
async def test_got_path_based_aggregation():
    """Test path-based aggregation strategy."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, aggregator="path_based")

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.metadata["aggregator"] == "path_based"
    assert response.content


@pytest.mark.asyncio
async def test_got_node_based_aggregation():
    """Test node-based aggregation strategy."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, aggregator="node_based")

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.metadata["aggregator"] == "node_based"
    assert response.content


@pytest.mark.asyncio
async def test_got_reasoning_paths():
    """Test that reasoning paths are found."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm)

    response = await agent.process(Message(role="user", content="Problem"))

    assert "reasoning_paths" in response.metadata
    assert isinstance(response.metadata["reasoning_paths"], list)


@pytest.mark.asyncio
async def test_got_metadata():
    """Test metadata completeness."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm)

    response = await agent.process(Message(role="user", content="Problem"))

    metadata = response.metadata

    # Check all required fields
    assert "technique" in metadata
    assert "graph" in metadata
    assert "reasoning_paths" in metadata
    assert "num_nodes" in metadata
    assert "num_edges" in metadata
    assert "has_cycles" in metadata
    assert "node_types" in metadata
    assert "edge_types" in metadata
    assert "aggregator" in metadata
    assert "allow_cycles" in metadata


@pytest.mark.asyncio
async def test_got_capabilities():
    """Test agent capabilities."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm)

    caps = agent.capabilities

    assert "reasoning" in caps
    assert "graph_of_thought" in caps
    assert "multi_hop_reasoning" in caps


@pytest.mark.asyncio
async def test_got_name():
    """Test agent name."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm)

    assert agent.name == "graph_of_thought"


@pytest.mark.asyncio
async def test_got_with_agent_interface():
    """Test with LLM that uses Agent.process() interface."""

    class MockLLMAgent:
        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="1. Thought one\n2. Thought two")

    llm = MockLLMAgent()
    agent = GraphOfThought(llm=llm, max_nodes=5)

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.content
    assert response.metadata["num_nodes"] > 0


@pytest.mark.asyncio
async def test_got_allow_cycles():
    """Test allow_cycles configuration."""
    llm = MockLLM()
    agent = GraphOfThought(llm=llm, allow_cycles=True)

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.metadata["allow_cycles"]


def test_node_type_enum():
    """Test NodeType enum."""
    assert NodeType.PREMISE.value == "premise"
    assert NodeType.INTERMEDIATE.value == "intermediate"
    assert NodeType.CONCLUSION.value == "conclusion"


def test_edge_type_enum():
    """Test EdgeType enum."""
    assert EdgeType.SUPPORTS.value == "supports"
    assert EdgeType.DEPENDS_ON.value == "depends_on"
    assert EdgeType.CONTRADICTS.value == "contradicts"
    assert EdgeType.REFINES.value == "refines"


def test_thought_node_hash():
    """Test ThoughtNode hashing."""
    node1 = ThoughtNode(id=1, content="Test", node_type=NodeType.PREMISE)
    node2 = ThoughtNode(id=1, content="Different", node_type=NodeType.PREMISE)
    node3 = ThoughtNode(id=2, content="Test", node_type=NodeType.PREMISE)

    assert node1 == node2  # Same ID
    assert node1 != node3  # Different ID
    assert hash(node1) == hash(node2)
