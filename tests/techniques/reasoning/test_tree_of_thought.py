"""Tests for Tree-of-Thought reasoning technique."""

import pytest
from agenkit import Message
from agenkit.techniques.reasoning import TreeOfThought, ReasoningTree, ReasoningNode


class MockLLM:
    """Mock LLM for testing ToT."""

    def __init__(self, responses=None):
        """
        Initialize with optional predefined responses.

        Args:
            responses: List of responses to cycle through
        """
        self.responses = responses or [
            "First reasoning branch",
            "Second reasoning branch",
            "Third reasoning branch"
        ]
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock response based on call count."""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


def simple_evaluator(text: str) -> float:
    """Simple evaluator for testing - score based on length."""
    return min(len(text) / 100, 1.0)


@pytest.mark.asyncio
async def test_tot_basic():
    """Test basic ToT functionality."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=2,
        evaluator=simple_evaluator
    )

    response = await tot.process(Message(role="user", content="Test query"))

    # Check response
    assert response.content
    assert response.metadata["technique"] == "tree_of_thought"
    assert "reasoning_tree_stats" in response.metadata
    assert "best_score" in response.metadata


@pytest.mark.asyncio
async def test_tot_bfs_strategy():
    """Test breadth-first search strategy."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=3,
        strategy="bfs"
    )

    response = await tot.process(Message(role="user", content="Test query"))

    assert response.metadata["search_strategy"] == "bfs"
    stats = response.metadata["reasoning_tree_stats"]
    assert stats["total_nodes"] > 1  # Should have explored multiple nodes


@pytest.mark.asyncio
async def test_tot_dfs_strategy():
    """Test depth-first search strategy."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=3,
        strategy="dfs"
    )

    response = await tot.process(Message(role="user", content="Test query"))

    assert response.metadata["search_strategy"] == "dfs"
    stats = response.metadata["reasoning_tree_stats"]
    assert stats["total_nodes"] > 1


@pytest.mark.asyncio
async def test_tot_best_first_strategy():
    """Test best-first search strategy."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=3,
        strategy="best-first"
    )

    response = await tot.process(Message(role="user", content="Test query"))

    assert response.metadata["search_strategy"] == "best-first"
    stats = response.metadata["reasoning_tree_stats"]
    assert stats["total_nodes"] > 1


@pytest.mark.asyncio
async def test_tot_custom_evaluator():
    """Test with custom evaluator function."""

    def custom_evaluator(text: str) -> float:
        # Favor texts containing "reasoning"
        return 0.9 if "reasoning" in text.lower() else 0.3

    llm = MockLLM(responses=["Contains reasoning", "No special word"])
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=2,
        evaluator=custom_evaluator
    )

    response = await tot.process(Message(role="user", content="Test query"))

    # Should favor the path with "reasoning"
    assert "best_score" in response.metadata
    assert response.metadata["best_score"] > 0.5


@pytest.mark.asyncio
async def test_tot_pruning():
    """Test path pruning with low scores."""

    def strict_evaluator(text: str) -> float:
        # Most paths get low scores
        return 0.1

    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=3,
        max_depth=3,
        evaluator=strict_evaluator,
        prune_threshold=0.5  # High threshold -> prune most paths
    )

    response = await tot.process(Message(role="user", content="Test query"))

    stats = response.metadata["reasoning_tree_stats"]
    # Should have pruned some nodes
    assert stats["num_pruned"] > 0


@pytest.mark.asyncio
async def test_tot_max_depth():
    """Test max depth limiting."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=2  # Limit to 2 levels
    )

    response = await tot.process(Message(role="user", content="Test query"))

    stats = response.metadata["reasoning_tree_stats"]
    # Max depth should be respected
    assert stats["max_depth"] <= 2


@pytest.mark.asyncio
async def test_tot_branching_factor():
    """Test branching factor configuration."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=4,  # Create 4 branches per node
        max_depth=2
    )

    response = await tot.process(Message(role="user", content="Test query"))

    stats = response.metadata["reasoning_tree_stats"]
    # Should have multiple nodes due to branching
    assert stats["total_nodes"] >= 5  # Root + at least 4 children


@pytest.mark.asyncio
async def test_tot_reasoning_path():
    """Test reasoning path extraction."""
    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=3
    )

    response = await tot.process(Message(role="user", content="Test query"))

    # Check reasoning path
    assert "reasoning_path" in response.metadata
    path = response.metadata["reasoning_path"]
    assert isinstance(path, list)
    assert len(path) > 0
    assert response.metadata["num_steps"] == len(path)


@pytest.mark.asyncio
async def test_tot_capabilities():
    """Test agent capabilities reporting."""
    llm = MockLLM()
    tot = TreeOfThought(llm=llm)

    caps = tot.capabilities

    assert "reasoning" in caps
    assert "tree_search" in caps
    assert "tree_of_thought" in caps
    assert "backtracking" in caps


@pytest.mark.asyncio
async def test_tot_name():
    """Test agent name."""
    llm = MockLLM()
    tot = TreeOfThought(llm=llm)

    assert tot.name == "tree_of_thought"


@pytest.mark.asyncio
async def test_tot_invalid_strategy():
    """Test error handling for invalid strategy."""
    llm = MockLLM()
    tot = TreeOfThought(llm=llm, strategy="invalid")

    with pytest.raises(ValueError, match="Invalid strategy"):
        await tot.process(Message(role="user", content="Test query"))


@pytest.mark.asyncio
async def test_tot_with_agent_interface():
    """Test ToT with LLM that uses Agent.process() interface."""

    class MockLLMAgent:
        async def process(self, message: Message) -> Message:
            return Message(
                role="assistant",
                content="Response from agent interface"
            )

    llm = MockLLMAgent()
    tot = TreeOfThought(llm=llm, branching_factor=2, max_depth=2)

    response = await tot.process(Message(role="user", content="Test query"))

    assert response.content
    assert "reasoning_tree_stats" in response.metadata


@pytest.mark.asyncio
async def test_tot_default_evaluator():
    """Test default evaluator behavior."""
    llm = MockLLM(responses=[
        "Very short",  # Low score
        "This is a much longer response with more detail and structure",  # Higher score
    ])

    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=2
        # No evaluator provided - uses default
    )

    response = await tot.process(Message(role="user", content="Test query"))

    # Default evaluator should favor longer responses
    assert "best_score" in response.metadata


# Tests for ReasoningTree data structure


def test_reasoning_tree_creation():
    """Test creating reasoning tree."""
    tree = ReasoningTree()

    root_id = tree.create_root("Root node")

    assert tree.root_id == root_id
    assert root_id in tree.nodes
    assert tree.nodes[root_id].content == "Root node"
    assert tree.nodes[root_id].depth == 0


def test_reasoning_tree_add_children():
    """Test adding children to tree."""
    tree = ReasoningTree()

    root_id = tree.create_root("Root")
    child1_id = tree.add_child(root_id, "Child 1", score=0.8)
    child2_id = tree.add_child(root_id, "Child 2", score=0.6)

    # Check children exist
    assert child1_id in tree.nodes
    assert child2_id in tree.nodes

    # Check parent-child relationships
    root = tree.nodes[root_id]
    assert child1_id in root.children_ids
    assert child2_id in root.children_ids

    # Check depths
    assert tree.nodes[child1_id].depth == 1
    assert tree.nodes[child2_id].depth == 1


def test_reasoning_tree_get_path():
    """Test getting path from root to node."""
    tree = ReasoningTree()

    root_id = tree.create_root("Root")
    child_id = tree.add_child(root_id, "Child")
    grandchild_id = tree.add_child(child_id, "Grandchild")

    path = tree.get_path(grandchild_id)

    assert len(path) == 3
    assert path[0].content == "Root"
    assert path[1].content == "Child"
    assert path[2].content == "Grandchild"


def test_reasoning_tree_get_leaves():
    """Test getting leaf nodes."""
    tree = ReasoningTree()

    root_id = tree.create_root("Root")
    child1_id = tree.add_child(root_id, "Child 1")
    child2_id = tree.add_child(root_id, "Child 2")
    _ = tree.add_child(child1_id, "Grandchild")  # Child 1 is no longer a leaf

    leaves = tree.get_leaves()

    # Only Child 2 and Grandchild are leaves
    assert len(leaves) == 2
    leaf_contents = [leaf.content for leaf in leaves]
    assert "Child 2" in leaf_contents
    assert "Grandchild" in leaf_contents


def test_reasoning_tree_get_best_leaf():
    """Test getting best scoring leaf."""
    tree = ReasoningTree()

    root_id = tree.create_root("Root")
    tree.add_child(root_id, "Low score", score=0.3)
    best_id = tree.add_child(root_id, "High score", score=0.9)
    tree.add_child(root_id, "Medium score", score=0.6)

    best_leaf = tree.get_best_leaf()

    assert best_leaf is not None
    assert best_leaf.id == best_id
    assert best_leaf.score == 0.9


def test_reasoning_tree_statistics():
    """Test tree statistics."""
    tree = ReasoningTree()

    root_id = tree.create_root("Root")
    child1_id = tree.add_child(root_id, "Child 1", score=0.8)
    child2_id = tree.add_child(root_id, "Child 2", score=0.6)
    tree.add_child(child1_id, "Grandchild", score=0.7)

    # Prune one node
    tree.prune_node(child2_id)

    stats = tree.get_statistics()

    assert stats["total_nodes"] == 4
    assert stats["max_depth"] == 2
    assert stats["num_leaves"] == 2
    assert stats["num_pruned"] == 1
    assert 0 <= stats["avg_score"] <= 1
    assert 0 <= stats["best_score"] <= 1
