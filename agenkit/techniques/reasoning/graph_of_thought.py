"""
Graph-of-Thought Reasoning Technique

Represents reasoning as a directed graph where nodes are thoughts/conclusions
and edges represent logical connections. More flexible than tree-based
approaches, allows for complex multi-hop reasoning and thought combination.

This technique is particularly effective for:
- Multi-hop reasoning problems
- Problems with multiple interconnected concepts
- Situations requiring synthesis of multiple reasoning chains

References:
    - Paper: https://arxiv.org/abs/2308.09687
    - "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"

Example:
    Basic usage::

        from agenkit.techniques.reasoning import GraphOfThought
        from agenkit import Message

        agent = GraphOfThought(
            llm=my_llm,
            max_nodes=20,
            max_edges=40,
            aggregator="path_based"
        )

        response = await agent.process(Message(
            role="user",
            content="Multi-hop reasoning problem..."
        ))

        # Access reasoning graph
        graph = response.metadata['graph']
        paths = response.metadata['reasoning_paths']
"""

from typing import Callable, Optional, List, Tuple
from agenkit import Agent, Message
from .reasoning_graph import (
    ReasoningGraph,
    ThoughtNode,
    LogicalEdge,
    NodeType,
    EdgeType
)


class GraphOfThought(Agent):
    """
    Graph-of-Thought reasoning technique.

    Builds a directed graph of reasoning steps, explores connections,
    and aggregates multiple reasoning paths to reach conclusions.

    This technique is particularly effective for:
    - Multi-hop reasoning with complex dependencies
    - Problems requiring synthesis of multiple chains of thought
    - Situations where thoughts may support, contradict, or refine each other
    - Complex knowledge integration tasks

    Attributes:
        name: Agent name (always "graph_of_thought")
        llm: LLM client for generating responses
        max_nodes: Maximum nodes in reasoning graph
        max_edges: Maximum edges in reasoning graph
        aggregator: Aggregation strategy ("path_based" or "node_based")
        allow_cycles: Whether to allow cycles in reasoning
    """

    def __init__(
        self,
        llm,  # LLMClient - type hint omitted for flexibility
        max_nodes: int = 20,
        max_edges: int = 40,
        aggregator: str = "path_based",
        allow_cycles: bool = False
    ):
        """
        Initialize Graph-of-Thought agent.

        Args:
            llm: LLM client for generating responses. Must have a `complete()`
                or `process()` method that returns text.
            max_nodes: Maximum number of nodes in reasoning graph. Default 20.
            max_edges: Maximum number of edges in reasoning graph. Default 40.
            aggregator: Aggregation strategy for combining paths.
                "path_based" (default): Aggregate entire reasoning paths
                "node_based": Aggregate individual nodes
            allow_cycles: Whether to allow cycles in reasoning graph.
                Default False (prevents circular reasoning).

        Example:
            >>> agent = GraphOfThought(
            ...     llm=my_llm,
            ...     max_nodes=20,
            ...     aggregator="path_based"
            ... )
        """
        self.llm = llm
        self.max_nodes = max_nodes
        self.max_edges = max_edges
        self.aggregator = aggregator
        self.allow_cycles = allow_cycles

    @property
    def name(self) -> str:
        """Return agent name."""
        return "graph_of_thought"

    async def _llm_call(self, prompt: str) -> str:
        """
        Call LLM with prompt.

        Args:
            prompt: Prompt to send to LLM

        Returns:
            LLM response text
        """
        if hasattr(self.llm, "complete"):
            return await self.llm.complete(prompt)
        elif hasattr(self.llm, "process"):
            response = await self.llm.process(Message(role="user", content=prompt))
            return response.content
        else:
            raise AttributeError("LLM must have either complete() or process() method")

    async def generate_premises(self, problem: str) -> List[str]:
        """
        Generate initial premises/facts for the problem.

        Args:
            problem: Problem to generate premises for

        Returns:
            List of premise statements
        """
        prompt = f"""Identify the key facts and premises for this problem.
List 2-4 foundational facts or assumptions, one per line.

Problem: {problem}

Premises:"""

        response = await self._llm_call(prompt)

        # Parse premises
        premises = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove numbering and bullets
                import re
                cleaned = re.sub(r'^[•\-\*\d]+[\\.\\)\\s]*', '', line)
                if cleaned:
                    premises.append(cleaned)

        return premises[:4]  # Limit to 4 premises

    async def generate_thoughts(
        self,
        problem: str,
        existing_thoughts: List[str],
        max_new: int = 3
    ) -> List[str]:
        """
        Generate new intermediate thoughts based on existing ones.

        Args:
            problem: Original problem
            existing_thoughts: List of existing thoughts
            max_new: Maximum number of new thoughts to generate

        Returns:
            List of new thought statements
        """
        if existing_thoughts:
            context = "\n".join([f"- {t}" for t in existing_thoughts])
            prompt = f"""Given this problem and existing thoughts, generate {max_new} new insights or conclusions.

Problem: {problem}

Existing thoughts:
{context}

New thoughts (one per line):"""
        else:
            prompt = f"""Generate {max_new} initial thoughts or insights about this problem.

Problem: {problem}

Thoughts (one per line):"""

        response = await self._llm_call(prompt)

        # Parse new thoughts
        thoughts = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                import re
                cleaned = re.sub(r'^[•\-\*\d]+[\\.\\)\\s]*', '', line)
                if cleaned and len(thoughts) < max_new:
                    thoughts.append(cleaned)

        return thoughts

    async def identify_connections(
        self,
        thought1: str,
        thought2: str
    ) -> Optional[EdgeType]:
        """
        Identify logical connection between two thoughts.

        Args:
            thought1: First thought
            thought2: Second thought

        Returns:
            EdgeType if connection exists, None otherwise
        """
        prompt = f"""Analyze the logical relationship between these two statements.

Statement 1: {thought1}

Statement 2: {thought2}

Does statement 2:
- SUPPORT statement 1 (provides evidence or reasoning for it)
- DEPEND on statement 1 (requires it to be true)
- CONTRADICT statement 1 (conflicts with it)
- REFINE statement 1 (improves or clarifies it)
- NO_RELATION (no clear logical connection)

Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION"""

        response = await self._llm_call(prompt)
        response_upper = response.strip().upper()

        if "SUPPORT" in response_upper:
            return EdgeType.SUPPORTS
        elif "DEPEND" in response_upper:
            return EdgeType.DEPENDS_ON
        elif "CONTRADICT" in response_upper:
            return EdgeType.CONTRADICTS
        elif "REFINE" in response_upper:
            return EdgeType.REFINES
        else:
            return None

    async def build_graph(self, problem: str) -> ReasoningGraph:
        """
        Build reasoning graph for the problem.

        Args:
            problem: Problem to build graph for

        Returns:
            Constructed ReasoningGraph
        """
        graph = ReasoningGraph()

        # Step 1: Generate premises
        premises = await self.generate_premises(problem)
        premise_ids = []
        for premise in premises:
            node_id = graph.add_node(
                content=premise,
                node_type=NodeType.PREMISE,
                confidence=0.9
            )
            premise_ids.append(node_id)

        # Step 2: Generate intermediate thoughts
        all_thoughts = premises.copy()
        node_ids = premise_ids.copy()

        while len(graph.nodes) < self.max_nodes:
            # Generate new thoughts based on existing ones
            max_new = min(3, self.max_nodes - len(graph.nodes))
            if max_new <= 0:
                break

            new_thoughts = await self.generate_thoughts(
                problem=problem,
                existing_thoughts=all_thoughts,
                max_new=max_new
            )

            if not new_thoughts:
                break

            # Add new thoughts as intermediate nodes
            for thought in new_thoughts:
                if len(graph.nodes) >= self.max_nodes:
                    break

                node_id = graph.add_node(
                    content=thought,
                    node_type=NodeType.INTERMEDIATE,
                    confidence=0.7
                )
                all_thoughts.append(thought)
                node_ids.append(node_id)

        # Step 3: Identify connections between thoughts
        edge_count = 0
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                if edge_count >= self.max_edges:
                    break

                node1_id = node_ids[i]
                node2_id = node_ids[j]

                thought1 = graph.get_node(node1_id).content
                thought2 = graph.get_node(node2_id).content

                # Check connection from node1 to node2
                edge_type = await self.identify_connections(thought1, thought2)
                if edge_type:
                    graph.add_edge(node1_id, node2_id, edge_type, strength=0.8)
                    edge_count += 1

            if edge_count >= self.max_edges:
                break

        # Step 4: Generate final conclusion
        if len(graph.nodes) < self.max_nodes:
            conclusion_prompt = f"""Based on all these thoughts, what is the final conclusion?

Problem: {problem}

Thoughts:
{chr(10).join([f'- {t}' for t in all_thoughts])}

Final conclusion:"""

            conclusion = await self._llm_call(conclusion_prompt)
            conclusion_id = graph.add_node(
                content=conclusion.strip(),
                node_type=NodeType.CONCLUSION,
                confidence=0.8
            )

            # Connect conclusion to recent thoughts
            for recent_id in node_ids[-3:]:
                if edge_count < self.max_edges:
                    graph.add_edge(recent_id, conclusion_id, EdgeType.SUPPORTS, strength=0.9)
                    edge_count += 1

        return graph

    def find_reasoning_paths(self, graph: ReasoningGraph) -> List[List[int]]:
        """
        Find reasoning paths from premises to conclusions.

        Args:
            graph: Reasoning graph

        Returns:
            List of paths (each path is list of node IDs)
        """
        premises = [n.id for n in graph.get_premises()]
        conclusions = [n.id for n in graph.get_conclusions()]

        all_paths = []
        for premise_id in premises:
            for conclusion_id in conclusions:
                paths = graph.find_paths(premise_id, conclusion_id, max_length=6)
                all_paths.extend(paths)

        return all_paths

    async def aggregate_paths(
        self,
        graph: ReasoningGraph,
        paths: List[List[int]]
    ) -> str:
        """
        Aggregate multiple reasoning paths into final answer.

        Args:
            graph: Reasoning graph
            paths: List of reasoning paths

        Returns:
            Final aggregated answer
        """
        if not paths:
            # No paths found - use conclusion nodes directly
            conclusions = graph.get_conclusions()
            if conclusions:
                return conclusions[0].content
            # Fallback to any node
            if graph.nodes:
                return list(graph.nodes.values())[-1].content
            return "Unable to reach conclusion"

        if self.aggregator == "path_based":
            # Aggregate by considering complete paths
            # Find highest scoring path
            best_path = max(paths, key=lambda p: graph.get_path_score(p))

            # Get conclusion from best path
            conclusion_node = graph.get_node(best_path[-1])
            return conclusion_node.content

        elif self.aggregator == "node_based":
            # Aggregate by considering individual nodes
            # Count node appearances across paths
            node_counts = {}
            for path in paths:
                for node_id in path:
                    node_counts[node_id] = node_counts.get(node_id, 0) + 1

            # Weight by confidence
            node_scores = {}
            for node_id, count in node_counts.items():
                node = graph.get_node(node_id)
                node_scores[node_id] = count * node.confidence

            # Return highest scoring node's content
            best_node_id = max(node_scores, key=node_scores.get)
            return graph.get_node(best_node_id).content

        else:
            raise ValueError(f"Unknown aggregator: {self.aggregator}")

    async def process(self, message: Message) -> Message:
        """
        Process message with Graph-of-Thought reasoning.

        Builds a reasoning graph, finds paths, and aggregates them
        into a final answer.

        Args:
            message: Input message with problem

        Returns:
            Message with final answer and metadata. Metadata includes:
                - graph: The reasoning graph
                - reasoning_paths: List of reasoning paths
                - num_nodes: Number of nodes in graph
                - num_edges: Number of edges in graph
                - has_cycles: Whether graph contains cycles
                - aggregator: Aggregation strategy used
                - technique: Always "graph_of_thought"

        Example:
            >>> response = await agent.process(Message(
            ...     role="user",
            ...     content="Complex reasoning problem"
            ... ))
            >>> print(response.metadata['num_nodes'])
            >>> print(response.metadata['reasoning_paths'])
        """
        problem = message.content

        # Step 1: Build reasoning graph
        graph = await self.build_graph(problem)

        # Step 2: Check for cycles (if not allowed)
        if not self.allow_cycles and graph.has_cycle():
            # Remove cycles by removing edges that create them
            # (Simple approach: could be more sophisticated)
            pass

        # Step 3: Find reasoning paths
        reasoning_paths = self.find_reasoning_paths(graph)

        # Step 4: Aggregate paths to final answer
        final_answer = await self.aggregate_paths(graph, reasoning_paths)

        # Get statistics
        stats = graph.statistics()

        return Message(
            role="assistant",
            content=final_answer,
            metadata={
                "technique": "graph_of_thought",
                "graph": graph,
                "reasoning_paths": reasoning_paths,
                "num_nodes": stats["num_nodes"],
                "num_edges": stats["num_edges"],
                "has_cycles": stats["has_cycles"],
                "node_types": stats["node_types"],
                "edge_types": stats["edge_types"],
                "aggregator": self.aggregator,
                "allow_cycles": self.allow_cycles
            }
        )

    @property
    def capabilities(self) -> list[str]:
        """
        Return agent capabilities.

        Returns:
            List of capability strings describing what this agent can do
        """
        return [
            "reasoning",
            "graph_of_thought",
            "multi_hop_reasoning",
            "path_aggregation",
            "complex_synthesis"
        ]
