"""
Parallel Composition Example

This example demonstrates WHY and HOW to use parallel composition for reducing
latency, gathering multiple perspectives, and implementing ensemble methods.

WHY USE PARALLEL COMPOSITION?
-----------------------------
1. Reduce Latency: Execute independent operations concurrently
2. Multiple Perspectives: Get diverse responses (ensemble, consensus)
3. A/B Testing: Compare different models/approaches simultaneously
4. Redundancy: Send same request to multiple services for reliability
5. Fan-out Search: Query multiple data sources simultaneously
6. Maximize Throughput: Utilize all available resources

WHEN TO USE:
- Independent operations (no data dependencies)
- Need consensus or voting from multiple agents
- A/B testing different models or prompts
- Querying multiple data sources (databases, APIs, search)
- Ensemble methods (combine multiple model outputs)
- Latency-critical paths where parallelism helps

WHEN NOT TO USE:
- Operations have dependencies (use SequentialAgent)
- Need to preserve order of operations
- Resource constraints (limited API quota, memory, CPU)
- When serial execution is fast enough
- Single source of truth is required

TRADE-OFFS:
- Latency Reduction: Total time = slowest agent (not sum)
- Resource Usage: N agents = N× cost (API calls, memory, CPU)
- Complexity: Need aggregation logic, handle partial failures
- Correctness: Must handle conflicting results
"""

import asyncio
import random
from typing import List
from agenkit.interfaces import Agent, Message
from agenkit.composition import ParallelAgent


# Example 1: Ensemble Decision Making
class SentimentAgent(Agent):
    """Analyzes sentiment using a specific approach."""

    def __init__(self, name: str, approach: str):
        self._name = name
        self.approach = approach

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["sentiment_analysis"]

    async def process(self, message: Message) -> Message:
        """Analyze sentiment using specific approach."""
        text = str(message.content).lower()

        # Simulate different analysis latencies
        await asyncio.sleep(random.uniform(0.05, 0.2))

        # Different approaches give slightly different results
        if self.approach == "lexicon":
            # Keyword-based
            positive = sum(1 for word in ["good", "great", "love"] if word in text)
            negative = sum(1 for word in ["bad", "hate", "terrible"] if word in text)
            score = (positive - negative) / 10 + 0.5
        elif self.approach == "ml_model":
            # Simulated ML model
            score = 0.5 + random.uniform(-0.2, 0.2)
            if "love" in text or "great" in text:
                score += 0.3
        else:  # rule_based
            # Simple rules
            if "!" in text:
                score = 0.8
            elif "?" in text:
                score = 0.5
            else:
                score = 0.6

        sentiment = "positive" if score > 0.6 else "negative" if score < 0.4 else "neutral"

        return Message(
            role="agent",
            content=sentiment,
            metadata={
                "sentiment": sentiment,
                "score": score,
                "approach": self.approach
            }
        )


def majority_vote_aggregator(messages: List[Message]) -> Message:
    """Aggregate by majority vote."""
    # Count votes
    votes = {}
    scores = []

    for msg in messages:
        sentiment = msg.metadata.get("sentiment", "neutral")
        votes[sentiment] = votes.get(sentiment, 0) + 1
        scores.append(msg.metadata.get("score", 0.5))

    # Majority wins
    winner = max(votes.items(), key=lambda x: x[1])
    avg_score = sum(scores) / len(scores)

    return Message(
        role="agent",
        content=f"Consensus: {winner[0]} ({winner[1]}/{len(messages)} votes)",
        metadata={
            "sentiment": winner[0],
            "vote_count": winner[1],
            "total_votes": len(messages),
            "average_score": avg_score,
            "all_results": [
                {"approach": m.metadata.get("approach"),
                 "sentiment": m.metadata.get("sentiment"),
                 "score": m.metadata.get("score")}
                for m in messages
            ]
        }
    )


async def example_ensemble_voting():
    """Example 1: Ensemble sentiment analysis with voting."""
    print("\n=== Example 1: Ensemble Voting ===")
    print("Use case: Combine multiple sentiment models for robust predictions\n")

    # Create ensemble of different approaches
    ensemble = ParallelAgent(
        name="sentiment-ensemble",
        agents=[
            SentimentAgent("lexicon-analyzer", "lexicon"),
            SentimentAgent("ml-analyzer", "ml_model"),
            SentimentAgent("rule-analyzer", "rule_based")
        ],
        aggregator=majority_vote_aggregator
    )

    test_texts = [
        "I love this product! It's great!",
        "This is terrible. Very disappointed.",
        "It's okay, nothing special."
    ]

    for text in test_texts:
        print(f"Text: '{text}'")
        result = await ensemble.process(Message(role="user", content=text))
        print(f"Result: {result.content}")
        print(f"Average Score: {result.metadata['average_score']:.2f}")
        print(f"Individual Results:")
        for r in result.metadata['all_results']:
            print(f"  - {r['approach']}: {r['sentiment']} ({r['score']:.2f})")
        print()

    print("💡 Why Parallel Ensemble?")
    print("   - More robust than single model")
    print("   - Reduces individual model bias")
    print("   - Latency = slowest model (not sum of 3)")
    print("   - Can detect when models disagree (low confidence)")


# Example 2: Multi-Source Search
class SearchAgent(Agent):
    """Searches a specific data source."""

    def __init__(self, name: str, source: str):
        self._name = name
        self.source = source

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["search"]

    async def process(self, message: Message) -> Message:
        """Search the data source."""
        query = str(message.content)

        # Simulate different latencies per source
        latencies = {
            "database": 0.05,
            "cache": 0.01,
            "api": 0.3,
            "web": 0.5
        }
        await asyncio.sleep(latencies.get(self.source, 0.1))

        # Simulate search results
        results = [
            f"{self.source.upper()} result {i+1} for '{query}'"
            for i in range(random.randint(0, 3))
        ]

        return Message(
            role="agent",
            content=f"Found {len(results)} results",
            metadata={
                "source": self.source,
                "results": results,
                "count": len(results)
            }
        )


def merge_search_results(messages: List[Message]) -> Message:
    """Merge and deduplicate search results."""
    all_results = []
    sources = []

    for msg in messages:
        source = msg.metadata.get("source", "unknown")
        results = msg.metadata.get("results", [])
        sources.append(f"{source}({len(results)})")
        all_results.extend(results)

    return Message(
        role="agent",
        content=f"Found {len(all_results)} total results from {len(messages)} sources",
        metadata={
            "total_results": len(all_results),
            "sources": sources,
            "results": all_results
        }
    )


async def example_multisource_search():
    """Example 2: Search multiple data sources in parallel."""
    print("\n=== Example 2: Multi-Source Search ===")
    print("Use case: Fan-out search across multiple backends\n")

    # Create multi-source search
    search = ParallelAgent(
        name="multi-search",
        agents=[
            SearchAgent("cache-search", "cache"),
            SearchAgent("db-search", "database"),
            SearchAgent("api-search", "api"),
            SearchAgent("web-search", "web")
        ],
        aggregator=merge_search_results
    )

    query = "agenkit framework"
    print(f"Query: '{query}'")
    print("Searching: cache, database, API, web...\n")

    import time
    start = time.time()
    result = await search.process(Message(role="user", content=query))
    elapsed = time.time() - start

    print(f"Result: {result.content}")
    print(f"Sources: {', '.join(result.metadata['sources'])}")
    print(f"Total Time: {elapsed:.2f}s")
    print(f"\n💡 Performance Comparison:")
    print(f"   Parallel:   {elapsed:.2f}s (actual)")
    print(f"   Sequential: ~0.86s (0.01 + 0.05 + 0.3 + 0.5)")
    print(f"   Speedup:    ~{0.86/elapsed:.1f}x faster")
    print(f"\n   Latency = max(all sources), not sum!")


# Example 3: A/B Testing
class LLMAgent(Agent):
    """Simulates an LLM with specific characteristics."""

    def __init__(self, name: str, model: str, latency: float, quality: float):
        self._name = name
        self.model = model
        self.latency = latency
        self.quality = quality  # 0.0 to 1.0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text_generation"]

    async def process(self, message: Message) -> Message:
        """Generate response with model characteristics."""
        await asyncio.sleep(self.latency)

        # Simulate response quality
        response = f"Response from {self.model}"
        if self.quality > 0.8:
            response += " (high quality, detailed)"
        elif self.quality > 0.6:
            response += " (good quality)"
        else:
            response += " (basic quality)"

        return Message(
            role="agent",
            content=response,
            metadata={
                "model": self.model,
                "latency": self.latency,
                "quality": self.quality
            }
        )


def compare_models_aggregator(messages: List[Message]) -> Message:
    """Compare model results for A/B testing."""
    results = []

    for msg in messages:
        results.append({
            "model": msg.metadata.get("model"),
            "latency": msg.metadata.get("latency"),
            "quality": msg.metadata.get("quality"),
            "response": msg.content
        })

    # Sort by quality (for comparison)
    results.sort(key=lambda x: x["quality"], reverse=True)

    best = results[0]
    comparison = f"Tested {len(results)} models. Best: {best['model']}"

    return Message(
        role="agent",
        content=comparison,
        metadata={
            "results": results,
            "best_model": best["model"],
            "best_quality": best["quality"]
        }
    )


async def example_ab_testing():
    """Example 3: A/B test different LLM models."""
    print("\n=== Example 3: A/B Testing Models ===")
    print("Use case: Compare different models simultaneously\n")

    # Test multiple models at once
    ab_test = ParallelAgent(
        name="ab-test",
        agents=[
            LLMAgent("gpt-4", "GPT-4", latency=0.5, quality=0.95),
            LLMAgent("gpt-3.5", "GPT-3.5-Turbo", latency=0.2, quality=0.75),
            LLMAgent("claude", "Claude-3", latency=0.3, quality=0.90),
            LLMAgent("llama", "Llama-3", latency=0.1, quality=0.70)
        ],
        aggregator=compare_models_aggregator
    )

    prompt = Message(role="user", content="Explain quantum computing")

    print("Testing 4 models in parallel...")
    import time
    start = time.time()
    result = await ab_test.process(prompt)
    elapsed = time.time() - start

    print(f"\n{result.content}")
    print(f"Total Time: {elapsed:.2f}s (vs ~1.1s sequential)\n")

    print("Model Comparison:")
    print(f"{'Model':<20} {'Quality':<10} {'Latency':<10}")
    print("-" * 40)
    for r in result.metadata['results']:
        print(f"{r['model']:<20} {r['quality']:<10.2f} {r['latency']:<10.2f}s")

    print("\n💡 A/B Testing Benefits:")
    print("   - Get results from all models in parallel")
    print("   - Compare quality, latency, cost simultaneously")
    print("   - Make data-driven model selection decisions")
    print("   - Can route production traffic based on results")


# Example 4: Redundant Requests for Reliability
class UnreliableAgent(Agent):
    """Agent that fails randomly."""

    def __init__(self, name: str, failure_rate: float):
        self._name = name
        self.failure_rate = failure_rate

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["processing"]

    async def process(self, message: Message) -> Message:
        """Process with random failures."""
        await asyncio.sleep(0.1)

        if random.random() < self.failure_rate:
            raise Exception(f"{self.name} failed (simulated)")

        return Message(
            role="agent",
            content=f"Success from {self.name}",
            metadata={"agent": self.name}
        )


def first_success_aggregator(messages: List[Message]) -> Message:
    """Return first successful result."""
    # With gather, all run to completion
    # In practice, could use return_when=FIRST_COMPLETED
    if messages:
        return messages[0]
    raise Exception("All agents failed")


async def example_redundant_requests():
    """Example 4: Send redundant requests for reliability."""
    print("\n=== Example 4: Redundant Requests ===")
    print("Use case: Improve reliability with redundancy\n")

    # Send same request to multiple instances
    # If one fails, others may succeed
    redundant = ParallelAgent(
        name="redundant",
        agents=[
            UnreliableAgent("instance-1", failure_rate=0.3),
            UnreliableAgent("instance-2", failure_rate=0.3),
            UnreliableAgent("instance-3", failure_rate=0.3)
        ],
        aggregator=first_success_aggregator
    )

    print("Simulating 10 requests to unreliable service (30% failure rate)...")
    print("Using 3 redundant instances in parallel\n")

    successes = 0
    for i in range(10):
        try:
            result = await redundant.process(
                Message(role="user", content=f"Request {i+1}")
            )
            successes += 1
        except Exception:
            pass

    success_rate = successes / 10
    single_success = 0.7  # 1 - failure_rate
    parallel_success = 1 - (0.3 ** 3)  # Probability at least one succeeds

    print(f"Results:")
    print(f"  Successful Requests: {successes}/10 ({success_rate:.0%})")
    print(f"\n💡 Reliability Improvement:")
    print(f"   Single instance:  ~70% success rate")
    print(f"   3× redundant:     ~97% success rate")
    print(f"   Improvement:      ~{parallel_success/single_success:.1f}x better")
    print(f"\n   Trade-off: 3× cost for ~1.4x reliability")


# Example 5: Handling Partial Failures
async def example_partial_failures():
    """Example 5: Handle partial failures gracefully."""
    print("\n=== Example 5: Handling Partial Failures ===")
    print("Use case: Continue with partial results when some agents fail\n")

    class MaybeFailAgent(Agent):
        def __init__(self, name: str, will_fail: bool):
            self._name = name
            self.will_fail = will_fail

        @property
        def name(self) -> str:
            return self._name

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            await asyncio.sleep(0.05)
            if self.will_fail:
                raise Exception(f"{self.name} failed")
            return Message(
                role="agent",
                content=f"Result from {self.name}",
                metadata={"agent": self.name}
            )

    def partial_results_aggregator(messages: List[Message]) -> Message:
        """Aggregate even with some failures."""
        # Note: gather with return_exceptions=True would include exceptions
        # This is simplified - would need error handling in real code
        success_count = len(messages)
        return Message(
            role="agent",
            content=f"Got {success_count} successful results",
            metadata={"success_count": success_count, "results": messages}
        )

    # Create parallel execution where some agents fail
    partial = ParallelAgent(
        name="partial",
        agents=[
            MaybeFailAgent("agent-1", will_fail=False),
            MaybeFailAgent("agent-2", will_fail=False),
            MaybeFailAgent("agent-3", will_fail=False)
        ],
        aggregator=partial_results_aggregator
    )

    print("Test 1: All agents succeed")
    try:
        result = await partial.process(Message(role="user", content="test"))
        print(f"  ✅ {result.content}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")

    # Modify to have failures
    partial._agents[1].will_fail = True

    print("\nTest 2: One agent fails")
    try:
        result = await partial.process(Message(role="user", content="test"))
        print(f"  ✅ {result.content}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"     (ParallelAgent fails if any agent fails)")

    print("\n💡 Partial Failure Handling:")
    print("   - By default, one failure fails entire parallel group")
    print("   - Use return_exceptions=True for graceful degradation")
    print("   - Aggregator can decide minimum required successes")
    print("   - Trade-off: Partial results vs all-or-nothing")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("PARALLEL COMPOSITION EXAMPLES")
    print("="*70)
    print("\nParallel composition reduces latency and enables ensemble methods.")
    print("Use it for independent operations that can run concurrently.\n")

    await example_ensemble_voting()
    await example_multisource_search()
    await example_ab_testing()
    await example_redundant_requests()
    await example_partial_failures()

    print("\n" + "="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. Use parallel composition when:
   - Operations are independent (no data dependencies)
   - Latency matters more than resource cost
   - Need consensus/voting from multiple sources
   - Comparing different approaches (A/B testing)
   - Redundancy improves reliability

2. Performance characteristics:
   - Latency = max(all agents), NOT sum
   - Resource usage = N× cost
   - Best speedup when agents have similar latency
   - Network I/O bound operations benefit most

3. Aggregation strategies:
   - Majority vote: Ensemble/consensus
   - First result: Fastest wins (race)
   - Merge all: Combine outputs
   - Best quality: Choose optimal result

4. Reliability patterns:
   - Redundancy: Send to N instances, take first success
   - Consensus: Require M of N to agree
   - Quality check: Validate before returning

5. When NOT to use:
   - Operations have dependencies → SequentialAgent
   - Resource constraints (API quota, cost)
   - Serial execution is fast enough
   - Order matters

REAL-WORLD USE CASES:
✅ Multi-model ensemble for better accuracy
✅ Fan-out search across multiple databases
✅ A/B testing different models/prompts
✅ Redundant requests to unreliable services
✅ Parallel validation checks

TRADE-OFF SUMMARY:
✅ Pros: Lower latency, redundancy, consensus
❌ Cons: Higher resource cost, complexity
🎯 Choose when: Latency reduction > cost increase
    """)


if __name__ == "__main__":
    asyncio.run(main())
