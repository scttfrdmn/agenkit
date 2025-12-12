"""
Least-to-Most Reasoning Example

Demonstrates how to use Least-to-Most prompting to break complex problems
into simpler subproblems and solve them sequentially.

This example shows:
- Basic problem decomposition and sequential solving
- Solution composition (using previous solutions)
- Custom decomposer functions
- Comparison with direct solving
- Real-world multi-step problems

Requirements:
    pip install agenkit
"""

import asyncio
from agenkit import Message
from agenkit.techniques.reasoning import LeastToMost


# Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM for demonstration."""

    def __init__(self):
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock responses based on prompt type."""
        self.call_count += 1

        # Decomposition prompts
        if "Break down" in prompt:
            if "3*4 + 2*5" in prompt:
                return """1. Calculate 3*4
2. Calculate 2*5
3. Add the results together"""

            if "shopping trip" in prompt:
                return """1. Calculate cost of apples: 3 × $2
2. Calculate cost of oranges: 2 × $3
3. Add both costs for total"""

            if "plan a vacation" in prompt:
                return """1. Choose destination
2. Book transportation
3. Book accommodation
4. Plan activities"""

            return "1. First step\n2. Second step"

        # Solving prompts
        if "Calculate 3*4" in prompt or "3 × $2" in prompt:
            return "6" if "apples" in prompt else "12"

        if "Calculate 2*5" in prompt or "2 × $3" in prompt:
            return "6"

        if "Add the results" in prompt or "Add both costs" in prompt:
            if "Previous solution 1: 6" in prompt:
                return "The total cost is $12"
            return "22"

        if "Choose destination" in prompt:
            return "Paris, France"

        if "Book transportation" in prompt:
            return "Round-trip flight on June 15-25"

        if "Book accommodation" in prompt:
            return "Hotel in central Paris for 10 nights"

        if "Plan activities" in prompt:
            return "Visit Eiffel Tower, Louvre, Notre-Dame"

        return "Generic solution"


async def basic_example():
    """Basic Least-to-Most with automatic decomposition."""
    print("=" * 60)
    print("Example 1: Basic Least-to-Most (Math Problem)")
    print("=" * 60)

    llm = MockLLM()
    ltm = LeastToMost(llm=llm, max_subproblems=5)

    query = "Calculate 3*4 + 2*5"
    response = await ltm.process(Message(role="user", content=query))

    print(f"\nOriginal Problem: {query}")
    print(f"\nDecomposed Subproblems:")
    for i, subproblem in enumerate(response.metadata['subproblems'], 1):
        print(f"  {i}. {subproblem}")

    print(f"\nSubproblem Solutions:")
    for i, solution in enumerate(response.metadata['subproblem_solutions'], 1):
        print(f"  {i}. {solution}")

    print(f"\nFinal Answer: {response.content}")
    print(f"Number of Steps: {response.metadata['num_subproblems']}")


async def composition_example():
    """Show how solution composition works."""
    print("\n" + "=" * 60)
    print("Example 2: Solution Composition (Context Building)")
    print("=" * 60)

    llm = MockLLM()
    ltm = LeastToMost(llm=llm, compose_solutions=True)

    query = "Calculate total cost: 3 apples at $2 each and 2 oranges at $3 each"
    response = await ltm.process(Message(role="user", content=query))

    print(f"\nProblem: {query}")
    print(f"\nWith Composition Enabled (compose_solutions=True):")
    print(f"  Each subproblem uses previous solutions as context")

    for i, (problem, solution) in enumerate(zip(
        response.metadata['subproblems'],
        response.metadata['subproblem_solutions']
    ), 1):
        print(f"\n  Step {i}: {problem}")
        print(f"  → Solution: {solution}")

    print(f"\n✓ Final Answer: {response.content}")


async def custom_decomposer_example():
    """Example with custom decomposer function."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Decomposer Function")
    print("=" * 60)

    def step_decomposer(problem: str) -> list[str]:
        """Custom decomposer that splits on 'then' keyword."""
        steps = problem.split(" then ")
        return [step.strip() for step in steps]

    llm = MockLLM()
    ltm = LeastToMost(llm=llm, decomposer=step_decomposer)

    query = "Choose destination then Book transportation then Book accommodation then Plan activities"
    response = await ltm.process(Message(role="user", content=query))

    print(f"\nOriginal Problem:")
    print(f"  {query}")

    print(f"\nCustom Decomposer splits on 'then':")
    for i, subproblem in enumerate(response.metadata['subproblems'], 1):
        solution = response.metadata['subproblem_solutions'][i-1]
        print(f"  {i}. {subproblem}")
        print(f"     → {solution}")

    print(f"\n💡 Custom decomposers are useful for:")
    print(f"   - Domain-specific problem structures")
    print(f"   - Deterministic decomposition strategies")
    print(f"   - Avoiding LLM calls for decomposition")


async def no_composition_example():
    """Compare with and without composition."""
    print("\n" + "=" * 60)
    print("Example 4: Composition vs No Composition")
    print("=" * 60)

    problem = "Calculate 3*4 + 2*5"

    # With composition
    llm_with = MockLLM()
    ltm_with = LeastToMost(llm=llm_with, compose_solutions=True)
    response_with = await ltm_with.process(Message(role="user", content=problem))

    # Without composition
    llm_without = MockLLM()
    ltm_without = LeastToMost(llm=llm_without, compose_solutions=False)
    response_without = await ltm_without.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")

    print(f"\n📊 WITH Composition (compose_solutions=True):")
    print(f"   Each step sees previous solutions")
    print(f"   Better for problems where steps build on each other")
    print(f"   Final answer: {response_with.content}")

    print(f"\n📊 WITHOUT Composition (compose_solutions=False):")
    print(f"   Each step solved independently")
    print(f"   Faster, better for independent subproblems")
    print(f"   Final answer: {response_without.content}")

    print(f"\n💡 Use composition when:")
    print(f"   - Later steps depend on earlier results")
    print(f"   - Building up complex solutions incrementally")
    print(f"   - Context from previous steps is valuable")


async def complexity_comparison():
    """Compare direct solving vs Least-to-Most."""
    print("\n" + "=" * 60)
    print("Example 5: Complex Problem Comparison")
    print("=" * 60)

    problem = "Plan a 10-day vacation to Europe including destination, flights, hotel, and activities"

    # Direct solving (single shot)
    llm_direct = MockLLM()
    direct_response = await llm_direct.complete(problem)

    # Least-to-Most decomposition
    llm_ltm = MockLLM()
    ltm = LeastToMost(llm=llm_ltm, max_subproblems=5)
    ltm_response = await ltm.process(Message(role="user", content=problem))

    print(f"\nComplex Problem:")
    print(f"  {problem}")

    print(f"\n❌ Direct Solving (Single LLM Call):")
    print(f"   Response: {direct_response}")
    print(f"   Issues:")
    print(f"   - May miss important details")
    print(f"   - No step-by-step reasoning")
    print(f"   - Hard to verify completeness")

    print(f"\n✅ Least-to-Most Decomposition:")
    print(f"   {len(ltm_response.metadata['subproblems'])} subproblems identified:")
    for i, (sub, sol) in enumerate(zip(
        ltm_response.metadata['subproblems'],
        ltm_response.metadata['subproblem_solutions']
    ), 1):
        print(f"   {i}. {sub}")
        print(f"      → {sol}")

    print(f"\n   Benefits:")
    print(f"   - Systematic coverage of all aspects")
    print(f"   - Clear reasoning chain")
    print(f"   - Each step can be verified")
    print(f"   - Easier to debug if something is wrong")


async def when_to_use():
    """Guidelines on when to use Least-to-Most."""
    print("\n" + "=" * 60)
    print("When to Use Least-to-Most")
    print("=" * 60)

    print("""
✅ BEST FOR:
  - Multi-step math problems (algebra, calculus)
  - Compositional reasoning (building complex from simple)
  - Problems with natural decomposition structure
  - Tasks where simpler subtasks inform harder ones
  - Planning problems (vacation, project, workflow)
  - Problems requiring systematic coverage

❌ LESS SUITABLE FOR:
  - Simple single-step problems
  - Problems without clear decomposition
  - When exploring multiple paths (use Tree-of-Thought)
  - When you need to verify consistency (use Self-Consistency)

⚙️ CONFIGURATION:
  - max_subproblems: Limit decomposition depth (default 5)
  - compose_solutions: Use previous solutions as context (default True)
  - decomposer: Custom function for domain-specific decomposition

🔗 COMBINE WITH:
  - Chain-of-Thought: Use CoT as the base LLM for reasoning
  - Self-Consistency: Sample multiple decompositions, vote on consensus
  - Tree-of-Thought: Explore multiple decomposition strategies
""")


async def main():
    """Run all examples."""
    await basic_example()
    await composition_example()
    await custom_decomposer_example()
    await no_composition_example()
    await complexity_comparison()
    await when_to_use()

    print("\n" + "=" * 60)
    print("Least-to-Most Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
