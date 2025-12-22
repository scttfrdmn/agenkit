"""
Reasoning Graph Data Structure for Graph-of-Thought

Provides a directed graph structure for representing reasoning as nodes
(thoughts/conclusions) connected by edges (logical relationships).

This is more flexible than tree-based approaches, allowing for:
- Multiple reasoning paths
- Complex dependencies
- Cycle detection for circular reasoning
- Path aggregation

References:
    - Graph-of-Thought paper: https://arxiv.org/abs/2308.09687
"""

from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """Type of thought node in the graph."""

    PREMISE = "premise"  # Starting assumption/fact
    INTERMEDIATE = "intermediate"  # Intermediate conclusion
    CONCLUSION = "conclusion"  # Final conclusion


class EdgeType(Enum):
    """Type of logical connection between nodes."""

    SUPPORTS = "supports"  # Node supports another
    DEPENDS_ON = "depends_on"  # Node depends on another
    CONTRADICTS = "contradicts"  # Node contradicts another
    REFINES = "refines"  # Node refines/improves another


@dataclass
class ThoughtNode:
    """A single thought/conclusion in the reasoning graph."""

    id: int
    content: str
    node_type: NodeType
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ThoughtNode):
            return self.id == other.id
        return False


@dataclass
class LogicalEdge:
    """A logical connection between two thoughts."""

    from_node: int  # Source node ID
    to_node: int  # Target node ID
    edge_type: EdgeType
    strength: float = 1.0  # Connection strength 0.0 to 1.0
    metadata: dict = field(default_factory=dict)


class ReasoningGraph:
    """
    Directed graph for representing reasoning structures.

    Nodes represent thoughts, conclusions, or premises.
    Edges represent logical connections and dependencies.

    Supports:
    - Adding nodes and edges
    - Path finding between nodes
    - Cycle detection
    - Topological sorting
    - Graph statistics
    """

    def __init__(self):
        """Initialize empty reasoning graph."""
        self.nodes: dict[int, ThoughtNode] = {}
        self.edges: list[LogicalEdge] = []
        self._next_id = 0

        # Adjacency lists for efficient traversal
        self._outgoing: dict[int, list[int]] = {}  # node_id -> [target_ids]
        self._incoming: dict[int, list[int]] = {}  # node_id -> [source_ids]

    def add_node(
        self,
        content: str,
        node_type: NodeType,
        confidence: float = 1.0,
        metadata: dict | None = None,
    ) -> int:
        """
        Add a thought node to the graph.

        Args:
            content: The thought/conclusion content
            node_type: Type of node (premise, intermediate, conclusion)
            confidence: Confidence score 0.0 to 1.0
            metadata: Optional metadata dict

        Returns:
            Node ID
        """
        node_id = self._next_id
        self._next_id += 1

        node = ThoughtNode(
            id=node_id,
            content=content,
            node_type=node_type,
            confidence=confidence,
            metadata=metadata or {},
        )

        self.nodes[node_id] = node
        self._outgoing[node_id] = []
        self._incoming[node_id] = []

        return node_id

    def add_edge(
        self,
        from_node: int,
        to_node: int,
        edge_type: EdgeType,
        strength: float = 1.0,
        metadata: dict | None = None,
    ) -> None:
        """
        Add a logical edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            edge_type: Type of logical connection
            strength: Connection strength 0.0 to 1.0
            metadata: Optional metadata dict
        """
        if from_node not in self.nodes or to_node not in self.nodes:
            raise ValueError("Both nodes must exist in graph")

        edge = LogicalEdge(
            from_node=from_node,
            to_node=to_node,
            edge_type=edge_type,
            strength=strength,
            metadata=metadata or {},
        )

        self.edges.append(edge)
        self._outgoing[from_node].append(to_node)
        self._incoming[to_node].append(from_node)

    def get_node(self, node_id: int) -> ThoughtNode | None:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_outgoing_edges(self, node_id: int) -> list[LogicalEdge]:
        """Get all edges originating from node."""
        return [e for e in self.edges if e.from_node == node_id]

    def get_incoming_edges(self, node_id: int) -> list[LogicalEdge]:
        """Get all edges pointing to node."""
        return [e for e in self.edges if e.to_node == node_id]

    def find_paths(self, start: int, end: int, max_length: int | None = None) -> list[list[int]]:
        """
        Find all paths from start node to end node.

        Args:
            start: Starting node ID
            end: Ending node ID
            max_length: Maximum path length (optional)

        Returns:
            List of paths, where each path is a list of node IDs
        """
        if start not in self.nodes or end not in self.nodes:
            return []

        paths = []

        def dfs(current: int, path: list[int], visited: set[int]):
            if current == end:
                paths.append(path.copy())
                return

            if max_length and len(path) >= max_length:
                return

            for next_node in self._outgoing[current]:
                if next_node not in visited:
                    path.append(next_node)
                    visited.add(next_node)
                    dfs(next_node, path, visited)
                    visited.remove(next_node)
                    path.pop()

        visited = {start}
        dfs(start, [start], visited)
        return paths

    def has_cycle(self) -> bool:
        """
        Check if graph contains any cycles.

        Returns:
            True if cycle exists, False otherwise
        """
        white = 0  # Not visited
        gray = 1  # Being processed
        black = 2  # Fully processed

        color = dict.fromkeys(self.nodes, white)

        def visit(node_id: int) -> bool:
            color[node_id] = gray

            for next_node in self._outgoing[node_id]:
                if color[next_node] == gray:
                    # Back edge found - cycle detected
                    return True
                if color[next_node] == white and visit(next_node):
                    return True

            color[node_id] = black
            return False

        return any(color[node_id] == white and visit(node_id) for node_id in self.nodes)

    def find_cycles(self) -> list[list[int]]:
        """
        Find all cycles in the graph.

        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        cycles = []
        visited = set()
        rec_stack = []

        def dfs(node_id: int) -> None:
            visited.add(node_id)
            rec_stack.append(node_id)

            for next_node in self._outgoing[node_id]:
                if next_node not in visited:
                    dfs(next_node)
                elif next_node in rec_stack:
                    # Found cycle
                    cycle_start = rec_stack.index(next_node)
                    cycle = [*rec_stack[cycle_start:], next_node]
                    cycles.append(cycle)

            rec_stack.pop()

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def topological_sort(self) -> list[int] | None:
        """
        Return nodes in topological order (if graph is acyclic).

        Returns:
            List of node IDs in topological order, or None if graph has cycles
        """
        if self.has_cycle():
            return None

        in_degree = {node_id: len(self._incoming[node_id]) for node_id in self.nodes}
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for next_node in self._outgoing[node_id]:
                in_degree[next_node] -= 1
                if in_degree[next_node] == 0:
                    queue.append(next_node)

        return result if len(result) == len(self.nodes) else None

    def get_premises(self) -> list[ThoughtNode]:
        """Get all premise nodes."""
        return [n for n in self.nodes.values() if n.node_type == NodeType.PREMISE]

    def get_conclusions(self) -> list[ThoughtNode]:
        """Get all conclusion nodes."""
        return [n for n in self.nodes.values() if n.node_type == NodeType.CONCLUSION]

    def get_path_score(self, path: list[int]) -> float:
        """
        Calculate score for a reasoning path.

        Combines node confidence and edge strength.

        Args:
            path: List of node IDs forming a path

        Returns:
            Path score (0.0 to 1.0)
        """
        if not path:
            return 0.0

        # Average node confidences
        node_scores = [self.nodes[node_id].confidence for node_id in path]
        avg_node_score = sum(node_scores) / len(node_scores)

        # Average edge strengths
        if len(path) < 2:
            return avg_node_score

        edge_scores = []
        for i in range(len(path) - 1):
            edges = [e for e in self.edges if e.from_node == path[i] and e.to_node == path[i + 1]]
            if edges:
                edge_scores.append(edges[0].strength)

        avg_edge_score = sum(edge_scores) / len(edge_scores) if edge_scores else 1.0

        # Combine scores
        return (avg_node_score + avg_edge_score) / 2

    def statistics(self) -> dict:
        """
        Get graph statistics.

        Returns:
            Dict with statistics about the graph
        """
        node_types = {}
        for node in self.nodes.values():
            node_types[node.node_type.value] = node_types.get(node.node_type.value, 0) + 1

        edge_types = {}
        for edge in self.edges:
            edge_types[edge.edge_type.value] = edge_types.get(edge.edge_type.value, 0) + 1

        return {
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "has_cycles": self.has_cycle(),
            "avg_confidence": sum(n.confidence for n in self.nodes.values()) / len(self.nodes)
            if self.nodes
            else 0.0,
        }
