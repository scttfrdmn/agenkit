"""
Reasoning Tree Data Structure

Provides tree structures for representing branching reasoning paths
used by Tree-of-Thought and related techniques.

This module defines:
- ReasoningNode: Individual node in reasoning tree
- ReasoningTree: Complete tree structure with search/traversal methods
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from enum import Enum


class NodeState(Enum):
    """State of a reasoning node during search."""

    OPEN = "open"           # Not yet explored
    ACTIVE = "active"       # Currently being explored
    EVALUATED = "evaluated" # Evaluated, may have children
    PRUNED = "pruned"       # Pruned from search
    TERMINAL = "terminal"   # Leaf node (complete reasoning path)


@dataclass
class ReasoningNode:
    """
    Node in a reasoning tree.

    Represents a single reasoning step in a multi-step reasoning path.
    Nodes can branch into multiple child nodes, forming a tree structure.

    Attributes:
        id: Unique node identifier
        content: Reasoning text for this step
        parent_id: ID of parent node (None for root)
        children_ids: List of child node IDs
        depth: Depth in tree (0 for root)
        score: Evaluation score (0.0-1.0, higher is better)
        state: Current state in search process
        metadata: Additional node-specific data
    """

    id: int
    content: str
    parent_id: Optional[int] = None
    children_ids: List[int] = field(default_factory=list)
    depth: int = 0
    score: float = 0.0
    state: NodeState = NodeState.OPEN
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children)."""
        return len(self.children_ids) == 0

    def is_root(self) -> bool:
        """Check if this is the root node (no parent)."""
        return self.parent_id is None

    def add_child(self, child_id: int) -> None:
        """Add a child node ID."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)


@dataclass
class ReasoningTree:
    """
    Tree structure for branching reasoning paths.

    Manages a tree of reasoning nodes with methods for building,
    searching, and analyzing reasoning paths.

    Attributes:
        nodes: Dictionary mapping node ID to ReasoningNode
        root_id: ID of root node
        next_id: Next available node ID
        max_depth: Maximum tree depth reached
    """

    nodes: dict[int, ReasoningNode] = field(default_factory=dict)
    root_id: Optional[int] = None
    next_id: int = 0
    max_depth: int = 0

    def create_root(self, content: str, metadata: Optional[dict] = None) -> int:
        """
        Create root node and return its ID.

        Args:
            content: Content for root node
            metadata: Optional metadata dict

        Returns:
            Root node ID
        """
        node_id = self.next_id
        self.next_id += 1

        node = ReasoningNode(
            id=node_id,
            content=content,
            depth=0,
            metadata=metadata or {}
        )

        self.nodes[node_id] = node
        self.root_id = node_id
        return node_id

    def add_child(
        self,
        parent_id: int,
        content: str,
        score: float = 0.0,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Add child node to parent and return child ID.

        Args:
            parent_id: ID of parent node
            content: Content for new child node
            score: Evaluation score for child
            metadata: Optional metadata dict

        Returns:
            New child node ID

        Raises:
            ValueError: If parent_id not found
        """
        if parent_id not in self.nodes:
            raise ValueError(f"Parent node {parent_id} not found")

        parent = self.nodes[parent_id]
        child_id = self.next_id
        self.next_id += 1

        child = ReasoningNode(
            id=child_id,
            content=content,
            parent_id=parent_id,
            depth=parent.depth + 1,
            score=score,
            metadata=metadata or {}
        )

        self.nodes[child_id] = child
        parent.add_child(child_id)

        # Update max depth
        if child.depth > self.max_depth:
            self.max_depth = child.depth

        return child_id

    def get_node(self, node_id: int) -> Optional[ReasoningNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_children(self, node_id: int) -> List[ReasoningNode]:
        """Get all children of a node."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_path(self, node_id: int) -> List[ReasoningNode]:
        """
        Get path from root to node.

        Args:
            node_id: Target node ID

        Returns:
            List of nodes from root to target (inclusive)
        """
        path = []
        current_id = node_id

        while current_id is not None:
            node = self.nodes.get(current_id)
            if not node:
                break
            path.insert(0, node)
            current_id = node.parent_id

        return path

    def get_path_text(self, node_id: int, delimiter: str = "\n") -> str:
        """
        Get concatenated text of path from root to node.

        Args:
            node_id: Target node ID
            delimiter: Delimiter between steps

        Returns:
            Concatenated path text
        """
        path = self.get_path(node_id)
        return delimiter.join(node.content for node in path)

    def get_leaves(self) -> List[ReasoningNode]:
        """Get all leaf nodes (nodes with no children)."""
        return [node for node in self.nodes.values() if node.is_leaf()]

    def get_best_leaf(self) -> Optional[ReasoningNode]:
        """Get leaf node with highest score."""
        leaves = self.get_leaves()
        if not leaves:
            return None
        return max(leaves, key=lambda n: n.score)

    def prune_node(self, node_id: int) -> None:
        """
        Mark node as pruned.

        Args:
            node_id: ID of node to prune
        """
        node = self.nodes.get(node_id)
        if node:
            node.state = NodeState.PRUNED

    def get_statistics(self) -> dict[str, Any]:
        """
        Get tree statistics.

        Returns:
            Dict with statistics (total_nodes, max_depth, leaves, etc.)
        """
        leaves = self.get_leaves()
        evaluated = [n for n in self.nodes.values() if n.state == NodeState.EVALUATED]
        pruned = [n for n in self.nodes.values() if n.state == NodeState.PRUNED]

        return {
            "total_nodes": len(self.nodes),
            "max_depth": self.max_depth,
            "num_leaves": len(leaves),
            "num_evaluated": len(evaluated),
            "num_pruned": len(pruned),
            "avg_score": sum(n.score for n in leaves) / len(leaves) if leaves else 0.0,
            "best_score": max((n.score for n in leaves), default=0.0)
        }
