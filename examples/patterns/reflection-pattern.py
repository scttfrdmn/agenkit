"""
Reflection Pattern Example - Self-Critique and Iterative Refinement

The Reflection pattern enables agents to review and improve their own outputs
through an iterative cycle of generation, critique, and refinement.

WHY use this pattern:
✅ Improve output quality through self-review
✅ Catch and fix errors automatically
✅ Iteratively refine until quality threshold met
✅ Reduce need for manual review cycles
✅ Works with any generator/critic agent pair

WHEN to use:
- Code generation that needs review
- Content creation requiring quality
- Multi-draft writing
- Error detection and correction
- Any task where iteration improves quality

Run: python examples/patterns/06_reflection_agent.py
"""

import asyncio

from agenkit.interfaces import Message
from agenkit.patterns import ReflectionAgent


# Mock agents for demonstration (replace with real LLM agents in production)
class CodeGeneratorAgent:
    """
    Mock code generator that simulates improvement over iterations.

    In production, replace with actual LLM (OpenAI, Anthropic, etc.)
    """

    def __init__(self):
        self.name = "CodeGenerator"
        self.capabilities = ["code_generation"]
        self.iteration = 0

    async def process(self, message: Message) -> Message:
        """Generate or refine code based on feedback."""
        self.iteration += 1

        # Simulate improving output based on critique
        if self.iteration == 1:
            # Initial attempt - has issues
            code = """def fibonacci(n):
    # Bug: doesn't handle n <= 0
    if n == 1:
        return 0
    if n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)"""

        elif self.iteration == 2:
            # Second attempt - fixed some issues
            code = """def fibonacci(n):
    # Better but still has issues with n=0
    if n <= 0:
        return 0
    if n == 1:
        return 0
    if n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)"""

        else:
            # Final version - all issues fixed
            code = """def fibonacci(n):
    \"\"\"
    Calculate the nth Fibonacci number (0-indexed).

    Args:
        n: Position in Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(5)
        5
    \"\"\"
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""

        return Message(role="assistant", content=code)


class CodeCriticAgent:
    """
    Mock code critic that evaluates code quality.

    In production, replace with actual LLM configured for code review.
    """

    def __init__(self):
        self.name = "CodeCritic"
        self.capabilities = ["code_review"]

    async def process(self, message: Message) -> Message:
        """Critique code and provide feedback."""
        # Extract code from critique prompt (simplified)
        code = message.content

        # Simulate quality scoring based on code characteristics
        score = 0.5  # Base score

        # Check for documentation
        if '"""' in code or "'''" in code:
            score += 0.2

        # Check for error handling
        if "raise" in code or "ValueError" in code:
            score += 0.15

        # Check for negative number handling
        if "< 0" in code or "<= 0" in code:
            score += 0.1

        # Check for proper base cases
        if "n <= 1" in code or "n == 0" in code:
            score += 0.05

        # Cap at 1.0
        score = min(1.0, score)

        # Generate feedback based on score
        if score < 0.7:
            feedback = """Issues found:
1. Missing docstring - add function documentation
2. No error handling for negative inputs
3. Base case logic could be clearer
4. Consider adding examples in docstring"""
        elif score < 0.9:
            feedback = """Good progress! Minor improvements needed:
1. Consider adding more detailed docstring with examples
2. Error handling could be more specific"""
        else:
            feedback = "Excellent! Code is well-documented, handles edge cases, and is clear."

        # Return structured critique
        critique = f'{{"score": {score}, "feedback": "{feedback}"}}'

        return Message(role="assistant", content=critique)


async def demo_basic_reflection():
    """Demo 1: Basic reflection with quality improvement."""
    print("=" * 70)
    print("Demo 1: Basic Reflection - Code Generation with Self-Review")
    print("=" * 70)

    generator = CodeGeneratorAgent()
    critic = CodeCriticAgent()

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_iterations=5,
        quality_threshold=0.9,  # Stop when quality >= 0.9
        improvement_threshold=0.05,  # Stop if improvement < 5%
    )

    print("\n📝 Task: Write a function to calculate Fibonacci numbers\n")

    result = await agent.process(Message(role="user", content="Write a fibonacci function"))

    print(f"\n✅ Final Code (after {result.metadata['reflection_iterations']} iterations):")
    print("-" * 70)
    print(result.content)
    print("-" * 70)

    print(f"\n📊 Results:")
    print(f"  Initial Quality: {result.metadata['initial_quality_score']:.2f}")
    print(f"  Final Quality: {result.metadata['final_quality_score']:.2f}")
    print(f"  Improvement: {result.metadata['total_improvement']:.2f} (+{result.metadata['total_improvement']*100:.0f}%)")
    print(f"  Stop Reason: {result.metadata['stop_reason']}")
    print(f"  Iterations: {result.metadata['reflection_iterations']}")


async def demo_reflection_with_history():
    """Demo 2: Reflection with detailed history tracking."""
    print("\n\n" + "=" * 70)
    print("Demo 2: Reflection with History - See the Iteration Process")
    print("=" * 70)

    generator = CodeGeneratorAgent()
    critic = CodeCriticAgent()

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_iterations=5,
        quality_threshold=0.9,
        verbose=True,  # Include full history in response
    )

    print("\n📝 Task: Generate code with detailed iteration tracking\n")

    result = await agent.process(Message(role="user", content="Write a fibonacci function"))

    print(f"📊 Iteration History:")
    print("-" * 70)

    for step in result.metadata["reflection_history"]:
        print(f"\nIteration {step['iteration']}:")
        print(f"  Quality Score: {step['quality_score']:.2f}")
        print(f"  Improvement: +{step['improvement']:.2f}")
        print(f"  Critique: {step['critique'][:80]}...")

    print("-" * 70)
    print(f"\n✅ Final Result:")
    print(f"  Achieved {result.metadata['final_quality_score']:.2f} quality")
    print(f"  Stopped due to: {result.metadata['stop_reason']}")


async def demo_reflection_thresholds():
    """Demo 3: Different stopping conditions."""
    print("\n\n" + "=" * 70)
    print("Demo 3: Stopping Conditions - Quality vs Max Iterations")
    print("=" * 70)

    print("\n🎯 Test 1: High quality threshold (0.95)")
    print("-" * 70)

    generator = CodeGeneratorAgent()
    critic = CodeCriticAgent()

    high_threshold_agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_iterations=10,
        quality_threshold=0.95,  # Very high threshold
    )

    result1 = await high_threshold_agent.process(
        Message(role="user", content="Write a fibonacci function")
    )

    print(f"  Iterations: {result1.metadata['reflection_iterations']}")
    print(f"  Final Quality: {result1.metadata['final_quality_score']:.2f}")
    print(f"  Stop Reason: {result1.metadata['stop_reason']}")

    print("\n🎯 Test 2: Low max iterations (2)")
    print("-" * 70)

    generator2 = CodeGeneratorAgent()
    critic2 = CodeCriticAgent()

    low_iter_agent = ReflectionAgent(
        generator=generator2,
        critic=critic2,
        max_iterations=2,  # Very few iterations
        quality_threshold=0.9,
    )

    result2 = await low_iter_agent.process(
        Message(role="user", content="Write a fibonacci function")
    )

    print(f"  Iterations: {result2.metadata['reflection_iterations']}")
    print(f"  Final Quality: {result2.metadata['final_quality_score']:.2f}")
    print(f"  Stop Reason: {result2.metadata['stop_reason']}")


async def demo_get_history():
    """Demo 4: Using get_history() for debugging."""
    print("\n\n" + "=" * 70)
    print("Demo 4: Debugging with get_history()")
    print("=" * 70)

    generator = CodeGeneratorAgent()
    critic = CodeCriticAgent()

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_iterations=5,
        quality_threshold=0.9,
    )

    print("\n📝 Running reflection...\n")

    await agent.process(Message(role="user", content="Write a fibonacci function"))

    # Access history via agent method
    history = agent.get_history()

    print(f"📊 Retrieved {len(history)} reflection steps\n")

    for step in history:
        print(f"Step {step.iteration}:")
        print(f"  Time: {step.timestamp.strftime('%H:%M:%S')}")
        print(f"  Score: {step.quality_score:.2f}")
        print(f"  Improvement: +{step.improvement:.2f}")
        print()


async def main():
    """Run all demos."""
    print("\n" + "🔄" * 35)
    print("REFLECTION PATTERN DEMONSTRATION")
    print("🔄" * 35 + "\n")

    await demo_basic_reflection()
    await demo_reflection_with_history()
    await demo_reflection_thresholds()
    await demo_get_history()

    print("\n" + "=" * 70)
    print("🎉 All demos completed!")
    print("=" * 70)

    print("\n📚 Key Takeaways:")
    print("  • Reflection improves quality through iteration")
    print("  • Configurable stopping conditions (quality, improvement, iterations)")
    print("  • Full history tracking available for debugging")
    print("  • Works with any generator/critic agent pair")
    print("  • Suitable for code, content, analysis, and more")

    print("\n💡 Production Usage:")
    print("  from agenkit.patterns import ReflectionAgent")
    print("  from anthropic import Anthropic")
    print()
    print("  generator = YourLLMAgent(model='claude-3-sonnet')")
    print("  critic = YourLLMAgent(model='claude-3-sonnet', system='You are a code reviewer...')")
    print()
    print("  agent = ReflectionAgent(")
    print("      generator=generator,")
    print("      critic=critic,")
    print("      max_iterations=5,")
    print("      quality_threshold=0.9")
    print("  )")
    print()
    print("  result = await agent.process(user_message)")
    print()

    print("\n🔗 See also:")
    print("  • docs/patterns/REFLECTION.md - Detailed pattern guide")
    print("  • examples/patterns/02_react_agent.py - ReAct pattern")
    print("  • examples/patterns/03_planning_agent.py - Planning pattern")
    print()


if __name__ == "__main__":
    asyncio.run(main())
