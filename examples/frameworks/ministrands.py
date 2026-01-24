#!/usr/bin/env python3
"""
MiniStrands - Strands Equivalent Built on Agenkit

Demonstrates how AWS Strands' graph-based orchestration patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy for niche frameworks.

Pattern Mappings: Strands Graph → Custom orchestration,
Node → Agent wrapper, A2A Protocol → Agents-as-Tools

Migration guide: docs/migrations/strands-to-agenkit.md

Usage: uv run python examples/frameworks/ministrands.py
"""

import asyncio
from typing import cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


class Node:
    """
    Graph node wrapping an agent (mirrors Strands.Node).
    Pattern: Strands.Node → Agent wrapper with node metadata
    """

    def __init__(self, node_id: str, agent: Agent) -> None:
        """
        Create graph node.

        Args:
            node_id: Unique node identifier
            agent: Agent to execute at this node
        """
        self.node_id = node_id
        self.agent = agent
        self.edges: list[Edge] = []

    def add_edge(self, edge: "Edge") -> None:
        """Add outgoing edge from this node."""
        self.edges.append(edge)


class Edge:
    """
    Connection between nodes (mirrors Strands.Edge).
    Pattern: Strands.Edge → Conditional routing with conditions
    """

    def __init__(
        self,
        from_node: str,
        to_node: str,
        condition: str | None = None,
    ) -> None:
        """
        Create edge between nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            condition: Optional condition for routing (simple string match)
        """
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition

    def should_traverse(self, message: Message) -> bool:
        """Check if edge should be traversed based on condition."""
        if self.condition is None:
            return True  # Unconditional edge

        # Simple condition checking (in real Strands, this is more sophisticated)
        content = cast("str", message.content).lower()
        return self.condition.lower() in content


class Graph:
    """
    Graph-based orchestration (mirrors Strands.Graph).
    Pattern: Strands.Graph → Explicit graph structure with nodes and edges
    """

    def __init__(self, name: str) -> None:
        """
        Create graph.

        Args:
            name: Graph name/identifier
        """
        self.name = name
        self.nodes: dict[str, Node] = {}
        self.start_node: str | None = None

    def add_node(self, node: Node) -> None:
        """Add node to graph."""
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add edge to graph."""
        if edge.from_node in self.nodes:
            self.nodes[edge.from_node].add_edge(edge)

    def set_start_node(self, node_id: str) -> None:
        """Set starting node for graph execution."""
        self.start_node = node_id


class GraphExecutor:
    """
    Executes graph-based workflows (Strands execution engine).
    Pattern: Strands execution → Custom graph traversal
    """

    def __init__(self, graph: Graph, max_iterations: int = 10) -> None:
        """
        Create graph executor.

        Args:
            graph: Graph to execute
            max_iterations: Maximum iterations to prevent infinite loops
        """
        self.graph = graph
        self.max_iterations = max_iterations

    async def execute(self, initial_message: Message) -> Message:
        """
        Execute graph starting from start node.

        Args:
            initial_message: Initial input message

        Returns:
            Final message after graph execution
        """
        if not self.graph.start_node:
            raise ValueError("Graph has no start node")

        current_node_id = self.graph.start_node
        current_message = initial_message
        execution_path = []

        for iteration in range(self.max_iterations):
            # Get current node
            if current_node_id not in self.graph.nodes:
                break

            current_node = self.graph.nodes[current_node_id]
            execution_path.append(current_node_id)

            # Execute agent at current node
            current_message = await current_node.agent.process(current_message)

            # Find next node based on edges
            next_node_id = None
            for edge in current_node.edges:
                if edge.should_traverse(current_message):
                    next_node_id = edge.to_node
                    break

            # No more edges or reached end
            if next_node_id is None:
                break

            current_node_id = next_node_id

        # Add execution metadata
        current_message.metadata["execution_path"] = execution_path
        current_message.metadata["iterations"] = iteration + 1

        return current_message


class StrandAgent(Agent):
    """
    Simple agent wrapper for Strands-style agents.
    Pattern: Strands Agent → Agenkit Agent with system instructions
    """

    def __init__(self, name: str, instructions: str, llm: LLM) -> None:
        """
        Create Strands-style agent.

        Args:
            name: Agent name (like Strands "routine" name)
            instructions: System instructions (like Strands instructions)
            llm: LLM adapter to use
        """
        self._name = name
        self.instructions = instructions
        self.llm = llm

    @property
    def name(self) -> str:
        """Return agent's name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return [self._name.lower().replace(" ", "_")]

    async def process(self, message: Message) -> Message:
        """Process message with agent's instructions."""
        # Build prompt with instructions
        prompt = f"{self.instructions}\n\nTask: {message.content}"
        messages = [Message(role="user", content=prompt)]

        response = await self.llm.complete(messages)

        return Message(
            role="agent",
            content=cast("str", response.content),
            metadata={"agent_name": self._name, "instructions": self.instructions},
        )


async def example_linear_graph() -> None:
    """Example: Simple linear graph (sequential execution)."""
    print("=" * 60)
    print("Example 1: Linear Graph (Sequential Flow)")
    print("=" * 60)

    # Create LLM (using test key for demo)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create agents
    researcher = StrandAgent(
        name="researcher",
        instructions="You are a researcher. Gather information on the topic.",
        llm=llm,
    )

    analyst = StrandAgent(
        name="analyst",
        instructions="You are an analyst. Analyze the research findings.",
        llm=llm,
    )

    writer = StrandAgent(
        name="writer",
        instructions="You are a writer. Create a summary report.",
        llm=llm,
    )

    # Build graph
    graph = Graph(name="research_pipeline")

    # Add nodes
    node1 = Node("research", researcher)
    node2 = Node("analyze", analyst)
    node3 = Node("write", writer)

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)

    # Add edges (linear flow)
    graph.add_edge(Edge("research", "analyze"))
    graph.add_edge(Edge("analyze", "write"))

    # Set start
    graph.set_start_node("research")

    print("\n📝 Strands-style API:")
    print("   graph = Graph(name='research_pipeline')")
    print("   graph.add_node(Node('research', researcher))")
    print("   graph.add_edge(Edge('research', 'analyze'))")
    print("   executor = GraphExecutor(graph)")
    print("   result = await executor.execute(message)")

    print("\n✅ Pattern: Strands Linear Graph → Sequential node execution")
    print("   Research → Analyze → Write (fixed path)")


async def example_branching_graph() -> None:
    """Example: Branching graph with conditional routing."""
    print("\n\n" + "=" * 60)
    print("Example 2: Branching Graph (Conditional Routing)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create specialist agents
    billing_agent = StrandAgent(
        name="billing",
        instructions="You are a billing specialist. Handle payment questions.",
        llm=llm,
    )

    technical_agent = StrandAgent(
        name="technical",
        instructions="You are a technical support specialist. Solve technical issues.",
        llm=llm,
    )

    general_agent = StrandAgent(
        name="general",
        instructions="You are a general support agent. Handle various questions.",
        llm=llm,
    )

    # Build branching graph
    graph = Graph(name="support_routing")

    # Add nodes
    classifier_node = Node("classifier", general_agent)
    billing_node = Node("billing", billing_agent)
    technical_node = Node("technical", technical_agent)

    graph.add_node(classifier_node)
    graph.add_node(billing_node)
    graph.add_node(technical_node)

    # Add conditional edges
    graph.add_edge(Edge("classifier", "billing", condition="payment"))
    graph.add_edge(Edge("classifier", "billing", condition="billing"))
    graph.add_edge(Edge("classifier", "technical", condition="technical"))
    graph.add_edge(Edge("classifier", "technical", condition="bug"))

    # Set start
    graph.set_start_node("classifier")

    print("\n📝 Strands-style Conditional Routing:")
    print("   graph.add_edge(Edge('classifier', 'billing', condition='payment'))")
    print("   graph.add_edge(Edge('classifier', 'technical', condition='bug'))")

    print("\n✅ Pattern: Strands Conditional Edges → Simple condition matching")
    print("   Classifier → Billing (if payment) OR Technical (if bug)")


async def example_agents_as_tools() -> None:
    """Example: A2A Protocol (Agents-as-Tools pattern)."""
    print("\n\n" + "=" * 60)
    print("Example 3: A2A Protocol (Agents-as-Tools)")
    print("=" * 60)

    print("\n📝 Strands A2A Protocol:")
    print("   orchestrator = Agent(")
    print("       name='coordinator',")
    print("       agents=[specialist1, specialist2]  # Can call these agents")
    print("   )")

    print("\n✅ Agenkit Equivalent:")
    print("   from agenkit.patterns import AgentsAsToolsAgent")
    print("   ")
    print("   orchestrator = AgentsAsToolsAgent(")
    print("       orchestrator_llm=llm,")
    print("       available_agents={'specialist1': ..., 'specialist2': ...}")
    print("   )")

    print("\n💡 Key insight: Strands A2A = Agenkit Agents-as-Tools")
    print("   Same concept, same name! Direct equivalence.")


async def main() -> None:
    """Run all examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "MiniStrands - Strands Built on Agenkit" + " " * 11 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n🎯 Demonstrate: AWS Strands graph-based patterns on Agenkit")

    await example_linear_graph()
    await example_branching_graph()
    await example_agents_as_tools()

    print("\n\n" + "=" * 60)
    print("✅ MiniStrands Examples Complete")
    print("=" * 60)
    print("\n🔑 Key Takeaways:")
    print("   • Agenkit supports graph-based orchestration patterns")
    print("   • Strands patterns map to Agenkit primitives:")
    print("     - Graph → Custom graph structure with nodes/edges")
    print("     - Node → Agent wrapper")
    print("     - Edge → Conditional routing")
    print("     - A2A Protocol → Agents-as-Tools pattern (direct mapping!)")
    print("     - Workflows → Orchestration + Memory")

    print("\n📚 Migration guide: docs/migrations/strands-to-agenkit.md")
    print("\n💡 Why Agenkit over Strands?")
    print("   ✓ Platform independence (no AWS lock-in)")
    print("   ✓ Any LLM provider (not just Bedrock)")
    print("   ✓ 6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   ✓ 11+ patterns (not just 4 primitives)")
    print("   ✓ OpenTelemetry (not just CloudWatch)")
    print("   ✓ 18x faster in Go for production")


if __name__ == "__main__":
    asyncio.run(main())
