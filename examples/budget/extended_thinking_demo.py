"""
Extended Thinking and Reasoning Budget Demo.

Demonstrates how to use ThinkingBudgetAllocator to dynamically allocate
thinking budgets based on query complexity and budget constraints.

Key features:
- Instant vs extended thinking mode selection
- Budget-aware thinking allocation
- Integration with CostTracker for thinking token tracking
- Model selection with thinking budget optimization

Run: python examples/budget/extended_thinking_demo.py
"""

import asyncio

from agenkit import Message
from agenkit.budget import (CostTracker, ThinkingBudgetAllocator, ThinkingMode,
                            ThinkingModeDetector)


async def demo_basic_allocation():
    """Demo 1: Basic thinking budget allocation based on complexity."""
    print("=" * 80)
    print("DEMO 1: Basic Thinking Budget Allocation")
    print("=" * 80)

    allocator = ThinkingBudgetAllocator(
        instant_thinking_tokens=0, light_thinking_tokens=3000, full_thinking_tokens=15000
    )

    queries = [
        ("Hello!", "simple"),
        ("Explain quantum computing", "medium"),
        ("Analyze the trade-offs between microservices and monolithic architectures", "complex"),
    ]

    for content, complexity in queries:
        messages = [Message(role="user", content=content)]
        budget = await allocator.allocate(messages, complexity)

        print(f"\nQuery: {content[:50]}...")
        print(f"Complexity: {complexity}")
        print(f"Thinking Mode: {budget.mode.value}")
        print(f"Max Thinking Tokens: {budget.max_thinking_tokens:,}")
        print(f"Estimated Cost: ${budget.estimated_cost:.4f}")
        print(f"Time Multiplier: {budget.reasoning_time_multiplier}x")


async def demo_budget_constraints():
    """Demo 2: Thinking allocation with budget constraints."""
    print("\n" + "=" * 80)
    print("DEMO 2: Budget-Constrained Thinking Allocation")
    print("=" * 80)

    allocator = ThinkingBudgetAllocator(
        full_thinking_tokens=15000,
        min_budget_for_extended=0.50,  # Require $0.50 remaining for extended thinking
    )

    messages = [
        Message(role="user", content="Provide a comprehensive analysis of this complex system")
    ]

    budgets = [10.0, 1.0, 0.30, 0.05]

    for remaining in budgets:
        budget = await allocator.allocate(
            messages=messages, complexity="complex", budget_remaining=remaining
        )

        print(f"\nBudget Remaining: ${remaining:.2f}")
        print(f"Selected Mode: {budget.mode.value}")
        print(f"Thinking Tokens: {budget.max_thinking_tokens:,}")
        print(
            f"Reason: {'Extended thinking allowed' if budget.mode == ThinkingMode.EXTENDED else 'Insufficient budget, using instant'}"
        )


async def demo_thinking_mode_detector():
    """Demo 3: Automatic thinking mode detection."""
    print("\n" + "=" * 80)
    print("DEMO 3: Automatic Thinking Mode Detection")
    print("=" * 80)

    detector = ThinkingModeDetector()

    queries = [
        "Hello, how are you?",
        "Please solve this math equation step by step: 2x + 5 = 15",
        "Analyze and compare the pros and cons of these approaches",
        "Quick question about syntax",
        "Think through this problem carefully and evaluate all trade-offs",
    ]

    for content in queries:
        messages = [Message(role="user", content=content)]
        needs_extended = await detector.needs_extended_thinking(messages)

        print(f"\nQuery: {content[:60]}...")
        print(f"Needs Extended Thinking: {needs_extended}")
        print(f"Recommended Mode: {'Extended' if needs_extended else 'Instant'}")


async def demo_cost_tracking_with_thinking():
    """Demo 4: Cost tracking with thinking tokens."""
    print("\n" + "=" * 80)
    print("DEMO 4: Cost Tracking with Thinking Tokens")
    print("=" * 80)

    tracker = CostTracker()
    allocator = ThinkingBudgetAllocator(full_thinking_tokens=10000)

    # Simulate multiple queries with thinking budgets
    queries = [
        ("Simple greeting", "simple", 500, 200),
        ("Medium analysis", "medium", 1500, 800),
        ("Complex reasoning task", "complex", 3000, 1500),
    ]

    for content, complexity, input_tokens, output_tokens in queries:
        messages = [Message(role="user", content=content)]

        # Allocate thinking budget
        budget = await allocator.allocate(messages, complexity)

        # Record cost with thinking tokens
        cost = await tracker.record_cost(
            session_id="demo-session",
            agent_name="reasoning-agent",
            model="claude-sonnet-4",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=budget.max_thinking_tokens,
        )

        print(f"\nQuery: {content}")
        print(f"  Input tokens: {cost.input_tokens:,}")
        print(f"  Output tokens: {cost.output_tokens:,}")
        print(f"  Thinking tokens: {cost.thinking_tokens:,}")
        print(f"  Input cost: ${cost.input_cost:.4f}")
        print(f"  Output cost: ${cost.output_cost:.4f}")
        print(f"  Thinking cost: ${cost.thinking_cost:.4f}")
        print(f"  Total cost: ${cost.total_cost:.4f}")

    # Get session statistics
    stats = await tracker.get_statistics(session_id="demo-session")

    print("\n" + "-" * 80)
    print("SESSION STATISTICS")
    print("-" * 80)
    print(f"Total requests: {stats['total_requests']}")
    print(f"Total input tokens: {stats['total_input_tokens']:,}")
    print(f"Total output tokens: {stats['total_output_tokens']:,}")
    print(f"Total thinking tokens: {stats['total_thinking_tokens']:,}")
    print(f"Total tokens (all types): {stats['total_tokens']:,}")
    print(f"Total cost: ${stats['total_cost']:.4f}")
    print(f"Average cost per request: ${stats['avg_cost_per_request']:.4f}")


async def demo_adaptive_thinking():
    """Demo 5: Adaptive thinking based on performance and cost."""
    print("\n" + "=" * 80)
    print("DEMO 5: Adaptive Thinking Allocation")
    print("=" * 80)

    # Different allocators for different use cases
    allocators = {
        "cost_optimized": ThinkingBudgetAllocator(
            light_thinking_tokens=1000,
            full_thinking_tokens=5000,
            min_budget_for_extended=1.0,  # Strict budget requirement
        ),
        "quality_optimized": ThinkingBudgetAllocator(
            light_thinking_tokens=5000,
            full_thinking_tokens=20000,
            min_budget_for_extended=0.10,  # Lenient budget requirement
        ),
        "balanced": ThinkingBudgetAllocator(
            light_thinking_tokens=3000, full_thinking_tokens=12000, min_budget_for_extended=0.50
        ),
    }

    messages = [
        Message(
            role="user",
            content="Analyze this complex problem step by step and evaluate all alternatives",
        )
    ]

    print("\nComplex query with different allocation strategies:")

    for strategy, allocator in allocators.items():
        budget = await allocator.allocate(
            messages=messages, complexity="complex", budget_remaining=2.0
        )

        print(f"\n{strategy.upper()} Strategy:")
        print(f"  Mode: {budget.mode.value}")
        print(f"  Thinking tokens: {budget.max_thinking_tokens:,}")
        print(f"  Estimated cost: ${budget.estimated_cost:.4f}")
        print(f"  Time multiplier: {budget.reasoning_time_multiplier}x")


async def demo_thinking_cost_comparison():
    """Demo 6: Compare costs with and without extended thinking."""
    print("\n" + "=" * 80)
    print("DEMO 6: Cost Comparison - Instant vs Extended Thinking")
    print("=" * 80)

    tracker_instant = CostTracker()
    tracker_extended = CostTracker()

    # Simulate same query with different thinking modes
    input_tokens = 2000
    output_tokens = 1000

    # Instant mode (no thinking tokens)
    cost_instant = await tracker_instant.record_cost(
        session_id="instant",
        agent_name="agent",
        model="claude-sonnet-4",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=0,
    )

    # Extended mode (with thinking tokens)
    cost_extended = await tracker_extended.record_cost(
        session_id="extended",
        agent_name="agent",
        model="claude-sonnet-4",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=10000,  # Extended thinking
    )

    print("\nSame Query - Different Thinking Modes:")
    print("-" * 80)

    print("\nINSTANT MODE (0 thinking tokens):")
    print(f"  Total tokens: {cost_instant.input_tokens + cost_instant.output_tokens:,}")
    print(f"  Total cost: ${cost_instant.total_cost:.4f}")

    print("\nEXTENDED MODE (10,000 thinking tokens):")
    print(
        f"  Total tokens: {cost_extended.input_tokens + cost_extended.output_tokens + cost_extended.thinking_tokens:,}"
    )
    print(f"  Thinking cost: ${cost_extended.thinking_cost:.4f}")
    print(f"  Total cost: ${cost_extended.total_cost:.4f}")

    print(
        f"\nCost Increase: ${cost_extended.total_cost - cost_instant.total_cost:.4f} ({((cost_extended.total_cost / cost_instant.total_cost - 1) * 100):.1f}%)"
    )
    print("Trade-off: Higher cost for better reasoning quality")


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("EXTENDED THINKING AND REASONING BUDGET DEMO")
    print("=" * 80)

    await demo_basic_allocation()
    await demo_budget_constraints()
    await demo_thinking_mode_detector()
    await demo_cost_tracking_with_thinking()
    await demo_adaptive_thinking()
    await demo_thinking_cost_comparison()

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("1. Extended thinking provides better reasoning at higher cost")
    print("2. Budget constraints can force instant mode to control costs")
    print("3. Automatic detection helps choose appropriate thinking mode")
    print("4. Thinking tokens are tracked separately for cost transparency")
    print("5. Different strategies optimize for cost, quality, or balance")
    print("\nSee docs/packages/BUDGET.md for more information.")


if __name__ == "__main__":
    asyncio.run(main())
