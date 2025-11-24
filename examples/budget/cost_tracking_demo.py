"""
Cost Tracking and Budget Management Demo

Demonstrates how to track LLM costs and enforce budgets to prevent
runaway spending in autonomous agents.

This example shows:
1. Basic cost tracking
2. Session and agent budget enforcement
3. Cost analysis and reporting
4. Model cost comparison
5. Realistic 30-hour scenario simulation
"""

import asyncio

from agenkit.budget import BudgetExceededError, BudgetLimiter, CostTracker, ModelPricing

# ===== Example 1: Basic Cost Tracking =====


async def example_basic_tracking():
    """Example: Track costs for different models."""
    print("\n=== Example 1: Basic Cost Tracking ===\n")

    tracker = CostTracker()

    # Simulate agent responses with different models
    sessions = [
        ("session-1", "assistant", "claude-haiku-3", 1000, 500),
        ("session-1", "assistant", "claude-sonnet-4", 2000, 1000),
        ("session-2", "research-agent", "claude-opus-4", 5000, 2500),
    ]

    for session_id, agent_name, model, input_tokens, output_tokens in sessions:
        cost = await tracker.record_cost(
            session_id=session_id,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        print(f"[{session_id}] {agent_name} using {model}:")
        print(f"  Tokens: {input_tokens} in, {output_tokens} out")
        print(f"  Cost: ${cost.total_cost:.4f}\n")

    # Get total costs
    session1_cost = await tracker.get_session_cost("session-1")
    session2_cost = await tracker.get_session_cost("session-2")

    print(f"Session 1 total: ${session1_cost:.4f}")
    print(f"Session 2 total: ${session2_cost:.4f}")


# ===== Example 2: Budget Enforcement =====


async def example_budget_enforcement():
    """Example: Enforce session budget and handle exceeding."""
    print("\n=== Example 2: Budget Enforcement ===\n")

    tracker = CostTracker()

    # Create budget limiter with $1.00 session budget
    BudgetLimiter(tracker=tracker, session_budget=1.00, action="error")

    print("Session budget: $1.00")
    print("Recording costs until budget exceeded...\n")

    try:
        # Simulate multiple expensive requests
        for i in range(10):
            await tracker.record_cost(
                session_id="budget-test",
                agent_name="assistant",
                model="claude-opus-4",  # Expensive model
                input_tokens=10000,
                output_tokens=5000,
            )

            current = await tracker.get_session_cost("budget-test")
            print(f"Request {i + 1}: Session cost = ${current:.2f}")

            # Check budget manually (in real usage, middleware does this)
            if current >= 1.00:
                raise BudgetExceededError(f"Budget exceeded: ${current:.2f}")

    except BudgetExceededError as e:
        print(f"\n❌ {e}")
        final_cost = await tracker.get_session_cost("budget-test")
        print(f"Final session cost: ${final_cost:.2f}")


# ===== Example 3: Cost Analysis and Reporting =====


async def example_cost_analysis():
    """Example: Analyze costs and generate reports."""
    print("\n=== Example 3: Cost Analysis ===\n")

    tracker = CostTracker()

    # Simulate various agent activities
    activities = [
        ("user-alice", "chat-agent", "claude-haiku-3", 500, 250),
        ("user-alice", "chat-agent", "claude-haiku-3", 600, 300),
        ("user-bob", "research-agent", "claude-sonnet-4", 5000, 2500),
        ("user-bob", "research-agent", "claude-sonnet-4", 6000, 3000),
        ("user-charlie", "analysis-agent", "claude-opus-4", 10000, 5000),
    ]

    for session_id, agent_name, model, input_tokens, output_tokens in activities:
        await tracker.record_cost(session_id, agent_name, model, input_tokens, output_tokens)

    # Get breakdown by model
    breakdown = await tracker.get_breakdown()
    print("Cost breakdown by model:")
    for model, cost in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f"  {model}: ${cost:.4f}")

    # Get top sessions
    print("\nTop sessions by cost:")
    top_sessions = await tracker.get_top_sessions(limit=3)
    for session_id, cost in top_sessions:
        print(f"  {session_id}: ${cost:.4f}")

    # Get statistics
    print("\nGlobal statistics:")
    stats = await tracker.get_statistics()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Total tokens: {stats['total_tokens']:,}")
    print(f"  Total cost: ${stats['total_cost']:.4f}")
    print(f"  Avg cost/request: ${stats['avg_cost_per_request']:.4f}")


# ===== Example 4: Model Cost Comparison =====


async def example_model_comparison():
    """Example: Compare costs across different models."""
    print("\n=== Example 4: Model Cost Comparison ===\n")

    pricing = ModelPricing()

    # Compare models for same workload
    models = ["claude-haiku-3", "claude-sonnet-4", "claude-opus-4", "gpt-4o", "o3"]
    input_tokens = 100000  # 100K tokens
    output_tokens = 50000  # 50K tokens

    print(f"Workload: {input_tokens:,} input + {output_tokens:,} output tokens\n")

    comparison = pricing.compare_models(models, input_tokens, output_tokens)

    print("Cost comparison:")
    for model, cost in sorted(comparison.items(), key=lambda x: x[1]):
        print(f"  {model:25} ${cost:>8.2f}")

    # Show cost ratios
    print("\nCost ratios (vs cheapest):")
    cheapest_cost = min(comparison.values())
    for model, cost in sorted(comparison.items(), key=lambda x: x[1]):
        ratio = cost / cheapest_cost
        print(f"  {model:25} {ratio:>8.1f}x")


# ===== Example 5: 30-Hour Autonomous Agent Scenario =====


async def example_30_hour_scenario():
    """Example: Simulate 30-hour autonomous agent cost."""
    print("\n=== Example 5: 30-Hour Autonomous Agent ===\n")

    pricing = ModelPricing()

    # Scenario parameters
    duration_hours = 30
    requests_per_hour = 33  # ~1 request every 2 minutes
    total_requests = duration_hours * requests_per_hour  # ~1000 requests

    avg_input_tokens = 10000  # 10K per request
    avg_output_tokens = 5000  # 5K per request

    total_input = total_requests * avg_input_tokens  # 10M tokens
    total_output = total_requests * avg_output_tokens  # 5M tokens

    print(f"Scenario: {duration_hours}-hour autonomous agent")
    print(f"  Duration: {duration_hours} hours")
    print(f"  Requests: ~{total_requests}")
    print(f"  Avg per request: {avg_input_tokens:,} in + {avg_output_tokens:,} out")
    print(f"  Total tokens: {total_input:,} in + {total_output:,} out\n")

    # Calculate costs for different models
    models_to_test = ["claude-haiku-3", "claude-sonnet-4", "claude-opus-4"]

    print("Estimated costs:")
    for model in models_to_test:
        input_cost = pricing.calculate(model, total_input, "input")
        output_cost = pricing.calculate(model, total_output, "output")
        total_cost = input_cost + output_cost

        print(f"  {model}:")
        print(f"    Input:  ${input_cost:>8.2f}")
        print(f"    Output: ${output_cost:>8.2f}")
        print(f"    Total:  ${total_cost:>8.2f} {'⚠️ EXPENSIVE!' if total_cost > 100 else ''}")
        print()


# ===== Example 6: Budget Warnings =====


async def example_budget_warnings():
    """Example: Get warnings before exceeding budget."""
    print("\n=== Example 6: Budget Warnings ===\n")

    tracker = CostTracker()
    session_budget = 5.00

    print(f"Session budget: ${session_budget:.2f}")
    print("Recording costs and checking remaining budget...\n")

    BudgetLimiter(
        tracker=tracker,
        session_budget=session_budget,
        action="warning",  # Warn instead of error
    )

    # Simulate requests
    for i in range(5):
        await tracker.record_cost("session-budget", "assistant", "claude-sonnet-4", 10000, 5000)

        current = await tracker.get_session_cost("session-budget")
        remaining = session_budget - current
        usage_pct = (current / session_budget) * 100

        print(f"Request {i + 1}:")
        print(f"  Current: ${current:.2f} ({usage_pct:.0f}% of budget)")
        print(f"  Remaining: ${remaining:.2f}")

        if usage_pct >= 75:
            print(f"  ⚠️ WARNING: {usage_pct:.0f}% of budget used!")
        print()


# ===== Main =====


async def main():
    """Run all examples."""
    await example_basic_tracking()
    await example_budget_enforcement()
    await example_cost_analysis()
    await example_model_comparison()
    await example_30_hour_scenario()
    await example_budget_warnings()

    print("\n" + "=" * 60)
    print("Cost tracking demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
