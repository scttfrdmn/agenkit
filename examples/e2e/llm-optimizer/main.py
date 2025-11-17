"""
Multi-LLM Cost Optimizer - Demo

Demonstrates intelligent routing to optimize costs while maintaining quality.

Usage:
    python main.py
"""

import asyncio
from llm_optimizer import (
    ComplexityClassifier,
    CostTracker,
    LLMRouter,
    MODELS
)


async def demo():
    """Run cost optimization demo."""
    print("="*70)
    print("MULTI-LLM COST OPTIMIZER - DEMO")
    print("="*70)
    print("\nDemonstrating intelligent LLM routing for cost optimization.")
    print(f"Available models: {', '.join(MODELS.keys())}")
    print()

    # Initialize components
    classifier = ComplexityClassifier()
    cost_tracker = CostTracker()
    router = LLMRouter(classifier, cost_tracker, budget_limit=1.0)

    # Test requests with varying complexity
    test_requests = [
        {
            "prompt": "What is Python?",
            "description": "Simple factual query"
        },
        {
            "prompt": "Explain the differences between Python and JavaScript in terms of syntax, use cases, performance, and ecosystem.",
            "description": "Complex comparative analysis"
        },
        {
            "prompt": "Write a function to sort a list",
            "description": "Medium coding task"
        },
        {
            "prompt": "I need medical advice about chest pain symptoms",
            "description": "Critical request"
        },
        {
            "prompt": "List 5 programming languages",
            "description": "Simple list request"
        },
    ]

    print(f"{'*'*70}")
    print(f"PROCESSING {len(test_requests)} REQUESTS")
    print(f"{'*'*70}\n")

    # Process each request
    for i, req in enumerate(test_requests, 1):
        print(f"\n{'='*70}")
        print(f"REQUEST #{i}: {req['description']}")
        print(f"{'='*70}")

        try:
            response = await router.execute(req["prompt"], verbose=True)
            print(f"\nResponse: {response}")

        except Exception as e:
            print(f"\n❌ Error: {e}")

        await asyncio.sleep(0.3)

    # Show final statistics
    print(f"\n\n{'='*70}")
    print("COST OPTIMIZATION SUMMARY")
    print(f"{'='*70}")

    stats = cost_tracker.get_stats()

    print(f"\nTotal Requests: {stats['total_requests']}")
    print(f"Total Cost: ${stats['total_cost']:.6f}")
    print(f"Total Tokens: {stats['total_tokens']}")
    print(f"Avg Cost/Request: ${stats['avg_cost_per_request']:.6f}")
    print(f"Success Rate: {stats['success_rate']*100:.1f}%")

    print(f"\nUsage by Model:")
    for model, data in stats['by_model'].items():
        model_config = MODELS[model]
        print(f"  {model}:")
        print(f"    Requests: {data['count']}")
        print(f"    Cost: ${data['cost']:.6f}")
        print(f"    Tokens: {data['tokens']}")
        print(f"    Quality Score: {model_config.quality_score}/10")
        print(f"    Cost per 1K tokens: ${model_config.cost_per_1k_tokens}")

    # Calculate savings
    print(f"\nCost Analysis:")
    most_expensive_model = max(MODELS.values(), key=lambda m: m.cost_per_1k_tokens)
    cost_if_all_expensive = sum(
        most_expensive_model.cost_per_1k_tokens * req.tokens_used / 1000
        for req in cost_tracker.requests
    )
    savings = cost_if_all_expensive - stats['total_cost']
    savings_pct = (savings / cost_if_all_expensive * 100) if cost_if_all_expensive > 0 else 0

    print(f"  If all requests used {most_expensive_model.name}: ${cost_if_all_expensive:.6f}")
    print(f"  Actual cost with routing: ${stats['total_cost']:.6f}")
    print(f"  💰 Savings: ${savings:.6f} ({savings_pct:.1f}% reduction)")

    print(f"\n{'='*70}")
    print("DEMO COMPLETE")
    print(f"{'='*70}")


async def interactive():
    """Interactive mode for testing."""
    print("="*70)
    print("MULTI-LLM COST OPTIMIZER - INTERACTIVE MODE")
    print("="*70)
    print("\nType your prompts (or 'quit' to exit)")
    print("Commands: 'stats' to view statistics")
    print("="*70 + "\n")

    classifier = ComplexityClassifier()
    cost_tracker = CostTracker()
    router = LLMRouter(classifier, cost_tracker)

    while True:
        prompt = input("\nPrompt > ").strip()

        if not prompt:
            continue

        if prompt.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        if prompt.lower() == "stats":
            stats = cost_tracker.get_stats()
            print(f"\nStatistics:")
            print(f"  Total Requests: {stats['total_requests']}")
            print(f"  Total Cost: ${stats['total_cost']:.6f}")
            print(f"  Avg Cost: ${stats.get('avg_cost_per_request', 0):.6f}")
            continue

        try:
            response = await router.execute(prompt, verbose=True)
            print(f"\nResponse: {response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1].lower() == "interactive":
        await interactive()
    else:
        await demo()


if __name__ == "__main__":
    asyncio.run(main())
