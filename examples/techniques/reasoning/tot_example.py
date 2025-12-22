"""
Tree-of-Thought (ToT) Reasoning Example

Demonstrates how to use Tree-of-Thought to explore multiple reasoning
paths simultaneously using tree search with branching and evaluation.

This example shows:
- Basic ToT usage with different search strategies
- Custom evaluator functions
- Path pruning and backtracking
- Tree statistics and best path selection

Requirements:
    pip install agenkit openai  # or your preferred LLM provider
"""

import asyncio

from agenkit import Message
from agenkit.techniques.reasoning import TreeOfThought


# Example 1: Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM that demonstrates ToT branching."""

    def __init__(self):
        self.responses = [
            # Alternative reasoning branches
            "Approach 1: Break the problem into smaller subproblems",
            "Approach 2: Look for patterns in similar problems",
            "Approach 3: Work backwards from the desired solution",
            "Step: Identify the constraints and requirements",
            "Step: Consider edge cases and special scenarios",
            "Step: Evaluate trade-offs between different solutions",
            "Conclusion: Choose the most efficient approach",
            "Conclusion: Verify the solution meets all requirements",
        ]
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock response cycling through alternatives."""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


def quality_evaluator(text: str) -> float:
    """
    Evaluate reasoning quality.

    Scores based on:
    - Length (more detailed = better)
    - Structure (numbered/bulleted = better)
    - Keywords indicating good reasoning
    """
    score = 0.0

    # Length component (up to 0.4)
    length_score = min(len(text) / 500, 0.4)
    score += length_score

    # Structure component (up to 0.3)
    has_structure = any(marker in text for marker in ["1.", "2.", "-", "•", "Step"])
    if has_structure:
        score += 0.3

    # Quality keywords (up to 0.3)
    quality_keywords = [
        "because", "therefore", "however", "consider",
        "approach", "solution", "conclusion", "verify"
    ]
    keyword_count = sum(1 for kw in quality_keywords if kw.lower() in text.lower())
    score += min(keyword_count * 0.1, 0.3)

    return min(score, 1.0)


async def basic_example():
    """Basic Tree-of-Thought example with best-first search."""
    print("=" * 60)
    print("Example 1: Basic Tree-of-Thought with Best-First Search")
    print("=" * 60)

    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=3,  # Explore 3 alternatives per step
        max_depth=3,         # Up to 3 reasoning steps
        evaluator=quality_evaluator,
        strategy="best-first"
    )

    query = "How should I approach solving a complex software architecture problem?"
    response = await tot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nSearch Strategy: {response.metadata['search_strategy']}")
    print(f"\nBest Reasoning Path (Score: {response.metadata['best_score']:.2f}):")
    for i, step in enumerate(response.metadata['reasoning_path'], 1):
        print(f"  {i}. {step}")

    print("\nTree Statistics:")
    stats = response.metadata['reasoning_tree_stats']
    print(f"  Total nodes explored: {stats['total_nodes']}")
    print(f"  Max depth reached: {stats['max_depth']}")
    print(f"  Leaf nodes: {stats['num_leaves']}")
    print(f"  Pruned nodes: {stats['num_pruned']}")


async def bfs_example():
    """Example with breadth-first search strategy."""
    print("\n" + "=" * 60)
    print("Example 2: Breadth-First Search Strategy")
    print("=" * 60)

    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=4,
        strategy="bfs"  # Explore all nodes at each depth before going deeper
    )

    query = "Plan a strategy for learning a new programming language"
    response = await tot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nStrategy: {response.metadata['search_strategy']} (explores breadth-first)")
    print(f"\nBest Path ({response.metadata['num_steps']} steps):")
    print(response.content)

    stats = response.metadata['reasoning_tree_stats']
    print(f"\nExplored {stats['total_nodes']} reasoning paths")


async def dfs_example():
    """Example with depth-first search strategy."""
    print("\n" + "=" * 60)
    print("Example 3: Depth-First Search Strategy")
    print("=" * 60)

    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=2,
        max_depth=4,
        strategy="dfs"  # Explore deep before wide
    )

    query = "Debug a complex issue in a distributed system"
    response = await tot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nStrategy: {response.metadata['search_strategy']} (explores depth-first)")
    print(f"\nBest Path Score: {response.metadata['best_score']:.2f}")

    stats = response.metadata['reasoning_tree_stats']
    print(f"Nodes explored: {stats['total_nodes']}")
    print(f"Max depth: {stats['max_depth']}")


async def pruning_example():
    """Example demonstrating path pruning."""
    print("\n" + "=" * 60)
    print("Example 4: Path Pruning with Threshold")
    print("=" * 60)

    def strict_evaluator(text: str) -> float:
        """Strict evaluator that scores harshly."""
        # Only high-quality reasoning gets good scores
        if len(text) < 30:
            return 0.1
        if any(kw in text.lower() for kw in ["approach", "solution", "consider"]):
            return 0.8
        return 0.3

    llm = MockLLM()
    tot = TreeOfThought(
        llm=llm,
        branching_factor=3,
        max_depth=3,
        evaluator=strict_evaluator,
        prune_threshold=0.5  # Prune paths scoring below 0.5
    )

    query = "Design a caching strategy for a high-traffic web application"
    response = await tot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print("\nPrune Threshold: 0.5 (removes low-quality reasoning paths)")

    stats = response.metadata['reasoning_tree_stats']
    print("\nTree Statistics:")
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Pruned nodes: {stats['num_pruned']}")
    print(f"  Pruning rate: {stats['num_pruned'] / stats['total_nodes'] * 100:.1f}%")
    print(f"\nBest path kept with score: {response.metadata['best_score']:.2f}")


async def comparison_example():
    """Compare CoT vs ToT on the same problem."""
    print("\n" + "=" * 60)
    print("Example 5: Chain-of-Thought vs Tree-of-Thought")
    print("=" * 60)

    from agenkit.techniques.reasoning import ChainOfThought

    query = "Optimize database query performance"

    # Chain-of-Thought: Single path
    llm_cot = MockLLM()
    cot = ChainOfThought(llm=llm_cot)
    cot_response = await cot.process(Message(role="user", content=query))

    # Tree-of-Thought: Multiple paths
    llm_tot = MockLLM()
    tot = TreeOfThought(
        llm=llm_tot,
        branching_factor=3,
        max_depth=2
    )
    tot_response = await tot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}\n")

    print("Chain-of-Thought (CoT):")
    print("  - Single reasoning path")
    print(f"  - Steps: {cot_response.metadata['num_steps']}")
    print("  - Direct and fast")

    print("\nTree-of-Thought (ToT):")
    stats = tot_response.metadata['reasoning_tree_stats']
    print(f"  - Explored {stats['total_nodes']} alternative paths")
    print(f"  - Selected best path with score: {tot_response.metadata['best_score']:.2f}")
    print("  - More thorough but more expensive")

    print("\n💡 Use CoT for: straightforward problems, speed-critical tasks")
    print("💡 Use ToT for: creative tasks, planning, exploring alternatives")


async def main():
    """Run all examples."""
    await basic_example()
    await bfs_example()
    await dfs_example()
    await pruning_example()
    await comparison_example()

    print("\n" + "=" * 60)
    print("Tree-of-Thought Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
