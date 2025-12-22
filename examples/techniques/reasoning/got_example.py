"""
Graph-of-Thought Reasoning Example

Demonstrates how to use Graph-of-Thought to represent reasoning as a directed
graph where nodes are thoughts/conclusions and edges are logical connections.

This example shows:
- Basic graph-based reasoning
- Path-based vs node-based aggregation
- Graph statistics and visualization
- Cycle detection
- Multi-hop reasoning chains

Requirements:
    pip install agenkit
"""

import asyncio

from agenkit import Message
from agenkit.techniques.reasoning import GraphOfThought


# Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM for demonstration."""

    def __init__(self):
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock responses based on prompt type."""
        self.call_count += 1

        # Premise generation
        if "key facts" in prompt.lower() or "Premises" in prompt:
            if "climate change" in prompt:
                return """1. Global temperatures are rising
2. CO2 levels are increasing
3. Ice caps are melting"""

            if "electric cars" in prompt:
                return """1. EVs produce zero direct emissions
2. Battery technology is improving
3. Charging infrastructure is expanding"""

            return "1. Fact A\n2. Fact B"

        # Thought generation
        if "generate" in prompt.lower() and ("thoughts" in prompt.lower() or "insights" in prompt.lower()):
            if "climate" in prompt:
                return """1. Rising temperatures cause extreme weather
2. Reducing emissions is critical
3. Renewable energy is key"""

            if "electric" in prompt or "EV" in prompt:
                return """1. EVs reduce carbon footprint
2. Range anxiety is decreasing
3. Cost parity is approaching"""

            return "1. Intermediate thought\n2. Another insight"

        # Relationship identification
        if "relationship" in prompt.lower():
            # Vary responses for more interesting graphs
            if self.call_count % 4 == 0:
                return "DEPEND"
            elif self.call_count % 4 == 1:
                return "SUPPORT"
            elif self.call_count % 4 == 2:
                return "REFINE"
            else:
                return "NO_RELATION"

        # Conclusion generation
        if "final conclusion" in prompt:
            if "climate" in prompt:
                return "Urgent action on climate change requires transitioning to renewable energy and reducing emissions"
            if "electric" in prompt or "EV" in prompt:
                return "Electric vehicles are becoming a practical and environmentally sound choice for most consumers"
            return "This is the synthesized conclusion"

        return "Generic response"


async def basic_example():
    """Basic Graph-of-Thought reasoning."""
    print("=" * 60)
    print("Example 1: Basic Graph-of-Thought")
    print("=" * 60)

    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=10, max_edges=20)

    problem = "Should we transition to electric cars?"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print("\n📊 Graph Statistics:")
    print(f"   Nodes: {response.metadata['num_nodes']}")
    print(f"   Edges: {response.metadata['num_edges']}")
    print(f"   Node Types: {response.metadata['node_types']}")
    print(f"   Edge Types: {response.metadata['edge_types']}")

    print(f"\n🎯 Final Answer: {response.content}")

    graph = response.metadata['graph']
    print("\n📋 Graph Structure:")
    for node_id, node in graph.nodes.items():
        print(f"   Node {node_id} [{node.node_type.value}]: {node.content[:50]}...")


async def path_aggregation_example():
    """Compare path-based vs node-based aggregation."""
    print("\n" + "=" * 60)
    print("Example 2: Path-Based vs Node-Based Aggregation")
    print("=" * 60)

    problem = "What causes climate change?"

    # Path-based aggregation
    llm_path = MockLLM()
    agent_path = GraphOfThought(llm=llm_path, max_nodes=8, aggregator="path_based")
    response_path = await agent_path.process(Message(role="user", content=problem))

    # Node-based aggregation
    llm_node = MockLLM()
    agent_node = GraphOfThought(llm=llm_node, max_nodes=8, aggregator="node_based")
    response_node = await agent_node.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")

    print("\n📍 Path-Based Aggregation:")
    print("   Strategy: Find best complete reasoning path")
    print(f"   Answer: {response_path.content}")
    print(f"   Paths found: {len(response_path.metadata['reasoning_paths'])}")

    print("\n📊 Node-Based Aggregation:")
    print("   Strategy: Aggregate most frequently used nodes")
    print(f"   Answer: {response_node.content}")

    print("\n💡 Choose aggregation based on your needs:")
    print("   - Path-based: Best for finding coherent reasoning chains")
    print("   - Node-based: Best for identifying key recurring concepts")


async def reasoning_paths_example():
    """Visualize reasoning paths."""
    print("\n" + "=" * 60)
    print("Example 3: Reasoning Paths Visualization")
    print("=" * 60)

    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=8, max_edges=15)

    problem = "How can we reduce emissions?"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")

    graph = response.metadata['graph']
    paths = response.metadata['reasoning_paths']

    print(f"\n🔗 Found {len(paths)} reasoning paths:")

    for i, path in enumerate(paths[:3], 1):  # Show first 3 paths
        print(f"\n   Path {i} (score: {graph.get_path_score(path):.2f}):")
        for j, node_id in enumerate(path):
            node = graph.get_node(node_id)
            connector = "   └─>" if j == len(path) - 1 else "   ├─>"
            print(f"   {connector} {node.content[:50]}...")

    if len(paths) > 3:
        print(f"\n   ... and {len(paths) - 3} more paths")


async def cycle_detection_example():
    """Demonstrate cycle detection."""
    print("\n" + "=" * 60)
    print("Example 4: Cycle Detection")
    print("=" * 60)

    llm = MockLLM()

    # Without allowing cycles
    agent_no_cycles = GraphOfThought(llm=llm, max_nodes=8, allow_cycles=False)
    response_no = await agent_no_cycles.process(Message(role="user", content="Test"))

    # With allowing cycles
    agent_with_cycles = GraphOfThought(llm=llm, max_nodes=8, allow_cycles=True)
    response_yes = await agent_with_cycles.process(Message(role="user", content="Test"))

    print("\n❌ Without Cycles (allow_cycles=False):")
    print("   Prevents circular reasoning")
    print(f"   Has cycles: {response_no.metadata['has_cycles']}")

    print("\n✓ With Cycles (allow_cycles=True):")
    print("   Allows thoughts to reinforce each other")
    print(f"   Has cycles: {response_yes.metadata['has_cycles']}")

    print("\n💡 Cycle detection helps identify:")
    print("   - Circular reasoning flaws")
    print("   - Mutually reinforcing concepts")
    print("   - Complex dependency patterns")


async def graph_statistics_example():
    """Show detailed graph statistics."""
    print("\n" + "=" * 60)
    print("Example 5: Graph Statistics and Analysis")
    print("=" * 60)

    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=12, max_edges=25)

    problem = "What are the benefits of renewable energy?"
    response = await agent.process(Message(role="user", content=problem))

    graph = response.metadata['graph']
    stats = graph.statistics()

    print(f"\nProblem: {problem}")

    print("\n📊 Detailed Statistics:")
    print(f"   Total Nodes: {stats['num_nodes']}")
    print(f"   Total Edges: {stats['num_edges']}")
    print(f"   Average Confidence: {stats['avg_confidence']:.2f}")
    print(f"   Has Cycles: {stats['has_cycles']}")

    print("\n📋 Node Distribution:")
    for node_type, count in stats['node_types'].items():
        print(f"   {node_type.capitalize()}: {count}")

    print("\n🔗 Edge Distribution:")
    for edge_type, count in stats['edge_types'].items():
        print(f"   {edge_type.capitalize()}: {count}")

    # Analyze path structure
    paths = response.metadata['reasoning_paths']
    if paths:
        avg_path_length = sum(len(p) for p in paths) / len(paths)
        print("\n🔍 Path Analysis:")
        print(f"   Number of paths: {len(paths)}")
        print(f"   Average path length: {avg_path_length:.1f} nodes")
        print(f"   Shortest path: {min(len(p) for p in paths)} nodes")
        print(f"   Longest path: {max(len(p) for p in paths)} nodes")


async def multi_hop_reasoning_example():
    """Demonstrate multi-hop reasoning capability."""
    print("\n" + "=" * 60)
    print("Example 6: Multi-Hop Reasoning")
    print("=" * 60)

    llm = MockLLM()
    agent = GraphOfThought(llm=llm, max_nodes=10, max_edges=20)

    problem = "If A implies B, and B implies C, what can we conclude about A and C?"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print("\n🔗 Multi-Hop Reasoning:")
    print("   Graph-of-Thought excels at chaining multiple logical steps")

    graph = response.metadata['graph']
    print(f"\n📊 Graph has {graph.statistics()['num_nodes']} nodes connected by")
    print(f"   {graph.statistics()['num_edges']} logical relationships")

    paths = response.metadata['reasoning_paths']
    if paths:
        longest_path = max(paths, key=len)
        print(f"\n🎯 Longest reasoning chain: {len(longest_path)} steps")

    print(f"\n💡 Conclusion: {response.content}")


async def when_to_use():
    """Guidelines on when to use Graph-of-Thought."""
    print("\n" + "=" * 60)
    print("When to Use Graph-of-Thought")
    print("=" * 60)

    print("""
✅ BEST FOR:
  - Multi-hop reasoning problems
  - Problems with complex interdependencies
  - Knowledge synthesis from multiple sources
  - Situations where thoughts may:
    * Support each other
    * Contradict each other
    * Depend on each other
    * Refine each other
  - Problems requiring exploration of multiple reasoning chains
  - Complex logical inference tasks

❌ LESS SUITABLE FOR:
  - Simple linear reasoning (use Chain-of-Thought)
  - Single-path problems (use Tree-of-Thought)
  - Problems requiring explicit planning (use Plan-and-Solve)
  - Very large graphs (computational complexity)

⚙️ CONFIGURATION:
  - max_nodes: Limit graph size (default 20)
  - max_edges: Limit connections (default 40)
  - aggregator: "path_based" or "node_based" (default "path_based")
  - allow_cycles: Allow circular reasoning (default False)

🔗 COMBINE WITH:
  - Chain-of-Thought: Use CoT as base LLM for better reasoning
  - Self-Consistency: Generate multiple graphs, vote on conclusions
  - Tree-of-Thought: ToT for generation, GoT for synthesis

💡 KEY ADVANTAGES:
  - More flexible than tree-based approaches
  - Can represent contradictions and refinements
  - Supports multi-hop logical chains
  - Enables complex knowledge integration
  - Path scoring helps identify strongest arguments

🎯 COMPARED TO OTHER TECHNIQUES:
  - vs Tree-of-Thought: Graph allows cycles, multiple paths to same conclusion
  - vs Chain-of-Thought: Graph explores multiple interconnected lines of thought
  - vs Least-to-Most: Graph for synthesis, LtM for decomposition
""")


async def main():
    """Run all examples."""
    await basic_example()
    await path_aggregation_example()
    await reasoning_paths_example()
    await cycle_detection_example()
    await graph_statistics_example()
    await multi_hop_reasoning_example()
    await when_to_use()

    print("\n" + "=" * 60)
    print("Graph-of-Thought Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
