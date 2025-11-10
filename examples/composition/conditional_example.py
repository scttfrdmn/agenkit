"""
Conditional Composition Example

This example demonstrates WHY and HOW to use conditional composition for intent
routing, specialized agents, and resource optimization.

WHY USE CONDITIONAL COMPOSITION?
--------------------------------
1. Intent Routing: Route to specialized agents based on request type
2. Resource Optimization: Use expensive resources only when needed
3. Domain Expertise: Leverage specialized agents for specific domains
4. Load Balancing: Distribute work based on agent capacity
5. Personalization: Route based on user preferences/tier
6. A/B Testing: Route percentage of traffic to different implementations

WHEN TO USE:
- Multi-domain systems (code, docs, customer service)
- Tiered service offerings (free, pro, enterprise)
- Language-specific routing
- Complexity-based routing (simple → fast, complex → powerful)
- User-specific routing (preferences, permissions)
- Feature flags and gradual rollouts

WHEN NOT TO USE:
- Single domain/purpose
- All requests need same processing (use SequentialAgent)
- Want all agents to run (use ParallelAgent)
- Order of execution matters more than selection
- Routing logic is trivial (simple if/else is clearer)

TRADE-OFFS:
- Routing Complexity vs Agent Specialization
- Maintenance (N agents) vs Performance (optimized per case)
- Classification accuracy vs routing speed
- Flexibility vs simplicity
"""

import asyncio
import re
from agenkit.interfaces import Agent, Message
from agenkit.composition import ConditionalAgent, content_contains, metadata_equals


# Example 1: Intent-Based Routing
class CodeAgent(Agent):
    """Specialized in code generation and debugging."""

    @property
    def name(self) -> str:
        return "code-specialist"

    @property
    def capabilities(self) -> list[str]:
        return ["code_generation", "debugging", "code_review"]

    async def process(self, message: Message) -> Message:
        """Process code-related requests."""
        await asyncio.sleep(0.2)  # Simulate processing

        return Message(
            role="agent",
            content="""Here's the implementation:
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```""",
            metadata={
                "type": "code",
                "language": "python",
                "agent": self.name
            }
        )


class DocsAgent(Agent):
    """Specialized in documentation and explanations."""

    @property
    def name(self) -> str:
        return "docs-specialist"

    @property
    def capabilities(self) -> list[str]:
        return ["documentation", "explanations", "tutorials"]

    async def process(self, message: Message) -> Message:
        """Process documentation requests."""
        await asyncio.sleep(0.15)

        return Message(
            role="agent",
            content="""# Understanding Async/Await

Async/await is a pattern for handling asynchronous operations:

1. **async def**: Defines an async function
2. **await**: Pauses execution until operation completes
3. **Benefits**: Better than callbacks, cleaner than threads

Example: `result = await fetch_data()`""",
            metadata={
                "type": "documentation",
                "format": "markdown",
                "agent": self.name
            }
        )


class GeneralAgent(Agent):
    """General-purpose agent for other requests."""

    @property
    def name(self) -> str:
        return "general-assistant"

    @property
    def capabilities(self) -> list[str]:
        return ["general_qa", "conversation"]

    async def process(self, message: Message) -> Message:
        """Process general requests."""
        await asyncio.sleep(0.1)

        return Message(
            role="agent",
            content="I'm here to help! I can answer general questions, have conversations, and assist with various tasks.",
            metadata={
                "type": "general",
                "agent": self.name
            }
        )


async def example_intent_routing():
    """Example 1: Route by intent/domain."""
    print("\n=== Example 1: Intent-Based Routing ===")
    print("Use case: Multi-domain assistant with specialized agents\n")

    # Create router with specialized agents
    router = ConditionalAgent(
        name="multi-domain-router",
        default_agent=GeneralAgent()
    )

    # Route code requests to code agent
    router.add_route(
        condition=lambda msg: any(
            keyword in msg.content.lower()
            for keyword in ["code", "function", "implement", "debug", "bug"]
        ),
        agent=CodeAgent()
    )

    # Route documentation requests to docs agent
    router.add_route(
        condition=lambda msg: any(
            keyword in msg.content.lower()
            for keyword in ["explain", "document", "how does", "what is", "tutorial"]
        ),
        agent=DocsAgent()
    )

    # Test different request types
    requests = [
        "Write a function to calculate fibonacci",
        "Explain how async/await works",
        "How are you today?"
    ]

    for query in requests:
        print(f"Query: {query}")
        result = await router.process(Message(role="user", content=query))
        print(f"Routed to: {result.metadata.get('agent')}")
        print(f"Response type: {result.metadata.get('type')}")
        print(f"Preview: {result.content[:80]}...")
        print()

    print("💡 Why Conditional Routing?")
    print("   - Code agent: Optimized for syntax, patterns, best practices")
    print("   - Docs agent: Optimized for clear explanations, tutorials")
    print("   - General agent: Handles everything else")
    print("   - Better than single agent trying to do everything")


# Example 2: Complexity-Based Routing
class SimpleQueryAgent(Agent):
    """Fast agent for simple queries."""

    @property
    def name(self) -> str:
        return "simple-query-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["simple_qa"]

    async def process(self, message: Message) -> Message:
        """Process simple queries quickly."""
        await asyncio.sleep(0.05)  # Very fast

        # Simple keyword matching
        text = message.content.lower()
        if "weather" in text:
            response = "Today is sunny, 72°F."
        elif "time" in text:
            response = "It's 2:30 PM."
        else:
            response = "Simple answer to your question."

        return Message(
            role="agent",
            content=response,
            metadata={
                "complexity": "simple",
                "latency": 0.05,
                "cost": 0.0001
            }
        )


class ComplexQueryAgent(Agent):
    """Powerful agent for complex queries."""

    @property
    def name(self) -> str:
        return "complex-query-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["complex_reasoning", "analysis"]

    async def process(self, message: Message) -> Message:
        """Process complex queries with deep reasoning."""
        await asyncio.sleep(0.5)  # Slower but more thorough

        return Message(
            role="agent",
            content="After careful analysis considering multiple perspectives, historical context, and potential implications, here's my comprehensive answer: [detailed response with reasoning]",
            metadata={
                "complexity": "complex",
                "latency": 0.5,
                "cost": 0.01
            }
        )


def is_simple_query(message: Message) -> bool:
    """Classify query complexity."""
    text = message.content.lower()

    # Simple queries are short and use simple words
    simple_patterns = [
        r"\bwhat is\b",
        r"\bwhen\b",
        r"\bwhere\b",
        r"\bwho\b",
        r"\bweather\b",
        r"\btime\b"
    ]

    # Check length
    if len(text.split()) <= 5:
        return True

    # Check for simple patterns
    if any(re.search(pattern, text) for pattern in simple_patterns):
        return True

    return False


async def example_complexity_routing():
    """Example 2: Route by query complexity."""
    print("\n=== Example 2: Complexity-Based Routing ===")
    print("Use case: Optimize cost and latency based on query complexity\n")

    router = ConditionalAgent(
        name="complexity-router",
        default_agent=ComplexQueryAgent()
    )

    # Route simple queries to fast agent
    router.add_route(
        condition=is_simple_query,
        agent=SimpleQueryAgent()
    )

    queries = [
        "What is the weather?",
        "Analyze the socioeconomic impacts of climate change",
        "What time is it?",
        "Compare and contrast various machine learning architectures"
    ]

    print("Processing queries with complexity-based routing...\n")

    total_cost = 0
    total_latency = 0

    for query in queries:
        print(f"Query: {query}")
        result = await router.process(Message(role="user", content=query))

        complexity = result.metadata.get("complexity")
        latency = result.metadata.get("latency")
        cost = result.metadata.get("cost")

        total_cost += cost
        total_latency += latency

        print(f"  Complexity: {complexity}")
        print(f"  Latency: {latency:.2f}s")
        print(f"  Cost: ${cost:.4f}")
        print()

    print(f"📊 Performance Summary:")
    print(f"   Total Latency: {total_latency:.2f}s")
    print(f"   Total Cost: ${total_cost:.4f}")
    print(f"\n💡 Without Routing (all complex):")
    print(f"   Total Latency: {0.5 * 4:.2f}s")
    print(f"   Total Cost: ${0.01 * 4:.4f}")
    print(f"\n   Savings: {((0.04 - total_cost) / 0.04):.0%} cost, {((2.0 - total_latency) / 2.0):.0%} latency")


# Example 3: Language-Specific Routing
class EnglishAgent(Agent):
    """Optimized for English."""

    @property
    def name(self) -> str:
        return "english-specialist"

    @property
    def capabilities(self) -> list[str]:
        return ["english"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.1)
        return Message(
            role="agent",
            content="Processed with English-optimized model",
            metadata={"language": "en", "model": "en-optimized"}
        )


class MultilingualAgent(Agent):
    """Handles all languages (slower, more expensive)."""

    @property
    def name(self) -> str:
        return "multilingual-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["multilingual"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.3)
        return Message(
            role="agent",
            content="Processed with multilingual model",
            metadata={"language": "multi", "model": "multilingual"}
        )


def detect_language(message: Message) -> bool:
    """Simple language detection."""
    text = message.content.lower()

    # Very simple detection (in production, use proper library)
    non_english_indicators = [
        "hola", "bonjour", "hallo", "ciao", "こんにちは",
        "你好", "안녕", "привет"
    ]

    return not any(indicator in text for indicator in non_english_indicators)


async def example_language_routing():
    """Example 3: Route by language."""
    print("\n=== Example 3: Language-Specific Routing ===")
    print("Use case: Use optimized models for common languages\n")

    router = ConditionalAgent(
        name="language-router",
        default_agent=MultilingualAgent()
    )

    router.add_route(
        condition=detect_language,
        agent=EnglishAgent()
    )

    queries = [
        ("Hello, how are you?", "English"),
        ("Bonjour, comment allez-vous?", "French"),
        ("What's the weather like?", "English")
    ]

    for query, expected_lang in queries:
        print(f"Query: {query} ({expected_lang})")
        result = await router.process(Message(role="user", content=query))
        print(f"  Routed to: {result.metadata.get('model')}")
        print()

    print("💡 Language Routing Benefits:")
    print("   - English queries: Use faster, cheaper English-only model")
    print("   - Other languages: Use comprehensive multilingual model")
    print("   - 70% of queries are English → 70% cost/latency savings")


# Example 4: User Tier Routing
class PremiumAgent(Agent):
    """Premium service with advanced features."""

    @property
    def name(self) -> str:
        return "premium-service"

    @property
    def capabilities(self) -> list[str]:
        return ["premium", "advanced_features"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.3)
        return Message(
            role="agent",
            content="Premium response with advanced analysis, personalization, and priority support.",
            metadata={
                "tier": "premium",
                "features": ["advanced_analysis", "priority", "personalization"]
            }
        )


class FreeAgent(Agent):
    """Free tier with basic features."""

    @property
    def name(self) -> str:
        return "free-service"

    @property
    def capabilities(self) -> list[str]:
        return ["basic"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.1)
        return Message(
            role="agent",
            content="Basic response. Upgrade to premium for advanced features!",
            metadata={
                "tier": "free",
                "features": ["basic"]
            }
        )


async def example_tier_routing():
    """Example 4: Route by user tier."""
    print("\n=== Example 4: User Tier Routing ===")
    print("Use case: Different service levels for free vs premium users\n")

    router = ConditionalAgent(
        name="tier-router",
        default_agent=FreeAgent()
    )

    # Premium users get premium service
    router.add_route(
        condition=lambda msg: msg.metadata.get("user_tier") == "premium",
        agent=PremiumAgent()
    )

    # Test free user
    print("Test 1: Free user")
    result = await router.process(
        Message(
            role="user",
            content="Analyze this data",
            metadata={"user_tier": "free"}
        )
    )
    print(f"  Service: {result.metadata.get('tier')}")
    print(f"  Features: {result.metadata.get('features')}")

    # Test premium user
    print("\nTest 2: Premium user")
    result = await router.process(
        Message(
            role="user",
            content="Analyze this data",
            metadata={"user_tier": "premium"}
        )
    )
    print(f"  Service: {result.metadata.get('tier')}")
    print(f"  Features: {result.metadata.get('features')}")

    print("\n💡 Tier-Based Routing:")
    print("   - Monetization: Premium users get better service")
    print("   - Cost control: Free users don't use expensive resources")
    print("   - Clear value proposition for upgrades")


# Example 5: A/B Testing with Gradual Rollout
class VariantAAgent(Agent):
    """Current production implementation."""

    @property
    def name(self) -> str:
        return "variant-a"

    @property
    def capabilities(self) -> list[str]:
        return ["production"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.15)
        return Message(
            role="agent",
            content="Response from Variant A (current)",
            metadata={"variant": "A", "version": "1.0"}
        )


class VariantBAgent(Agent):
    """New experimental implementation."""

    @property
    def name(self) -> str:
        return "variant-b"

    @property
    def capabilities(self) -> list[str]:
        return ["experimental"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.12)
        return Message(
            role="agent",
            content="Response from Variant B (experimental, faster)",
            metadata={"variant": "B", "version": "2.0"}
        )


def ab_test_routing(rollout_percentage: float):
    """Create routing function for A/B test."""
    import hashlib

    def route(message: Message) -> bool:
        """Route to variant B based on user_id hash."""
        user_id = message.metadata.get("user_id", "anonymous")

        # Consistent hashing for same user
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        percentage = (hash_value % 100) / 100.0

        return percentage < rollout_percentage

    return route


async def example_ab_testing():
    """Example 5: A/B testing with gradual rollout."""
    print("\n=== Example 5: A/B Testing & Gradual Rollout ===")
    print("Use case: Test new implementation on subset of users\n")

    # 20% rollout to variant B
    router = ConditionalAgent(
        name="ab-test-router",
        default_agent=VariantAAgent()
    )

    router.add_route(
        condition=ab_test_routing(rollout_percentage=0.2),
        agent=VariantBAgent()
    )

    # Simulate 100 users
    print("Simulating 100 users with 20% rollout to Variant B...")

    variant_counts = {"A": 0, "B": 0}

    for i in range(100):
        result = await router.process(
            Message(
                role="user",
                content="test",
                metadata={"user_id": f"user_{i}"}
            )
        )
        variant = result.metadata.get("variant")
        variant_counts[variant] += 1

    print(f"\n📊 Rollout Distribution:")
    print(f"   Variant A: {variant_counts['A']} users ({variant_counts['A']}%)")
    print(f"   Variant B: {variant_counts['B']} users ({variant_counts['B']}%)")

    print("\n💡 A/B Testing Benefits:")
    print("   - Test new implementations safely")
    print("   - Consistent: Same user always gets same variant")
    print("   - Gradual rollout: 5% → 20% → 50% → 100%")
    print("   - Monitor metrics per variant, rollback if needed")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("CONDITIONAL COMPOSITION EXAMPLES")
    print("="*70)
    print("\nConditional composition routes requests to specialized agents.")
    print("Use it for intent routing, optimization, and personalization.\n")

    await example_intent_routing()
    await example_complexity_routing()
    await example_language_routing()
    await example_tier_routing()
    await example_ab_testing()

    print("\n" + "="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. Use conditional composition when:
   - Multiple specialized agents (code, docs, data)
   - Optimization opportunities (simple vs complex)
   - User-specific routing (tier, language, preferences)
   - A/B testing and gradual rollouts
   - Cost/performance trade-offs based on input

2. Routing strategies:
   - Intent/Domain: keyword matching, classification
   - Complexity: length, patterns, keywords
   - Language: detection libraries
   - User attributes: tier, permissions, preferences
   - Load balancing: round-robin, least loaded
   - A/B testing: consistent hashing

3. Condition design principles:
   - Fast: Routing should be O(1) or O(log n)
   - Accurate: Misrouting hurts user experience
   - Observable: Log routing decisions
   - Testable: Unit test each condition
   - Maintainable: Clear, documented logic

4. When NOT to use:
   - Single domain/purpose (unnecessary complexity)
   - All agents must run (use ParallelAgent)
   - Simple if/else suffices (don't over-engineer)
   - Routing logic changes frequently (hard to maintain)

5. Advanced patterns:
   - Hierarchical routing: coarse → fine-grained
   - Fallback on routing error: default agent
   - Multi-stage: route → process → route again
   - Learning routers: ML-based classification

REAL-WORLD USE CASES:
✅ Multi-domain: Code/docs/data specialists
✅ Optimization: Simple (fast) vs complex (thorough)
✅ Language: English-only vs multilingual models
✅ Monetization: Free/pro/enterprise tiers
✅ Testing: A/B tests, feature flags, canary deploys

TRADE-OFF SUMMARY:
✅ Pros: Specialized agents, optimization, personalization
❌ Cons: Routing complexity, maintenance burden
🎯 Choose when: Specialization benefits > routing cost
    """)


if __name__ == "__main__":
    asyncio.run(main())
