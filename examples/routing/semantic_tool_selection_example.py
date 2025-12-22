"""
Semantic Tool Selection Example

Demonstrates embedding-based tool selection using semantic matching
rather than keyword matching.

This example shows:
1. Basic semantic tool selection
2. Comparison with keyword matching
3. Multi-tool workflows
4. Performance optimization with caching
"""

import asyncio

from agenkit.routing.semantic_selector import SemanticToolSelector, ToolDescription


# For this example, we'll use a simple mock provider
# In production, use OpenAIEmbeddingProvider or VoyageEmbeddingProvider
class SimpleMockProvider:
    """Simple mock for demonstration (use real provider in production)."""

    async def embed(self, text: str) -> list[float]:
        """Generate simple embedding based on keywords."""
        import hashlib

        # Simple hash-based embedding for demo
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val >> (i * 8)) & 0xFF / 255.0 for i in range(10)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]


async def example_1_basic_selection():
    """Example 1: Basic semantic tool selection."""
    print("=" * 60)
    print("Example 1: Basic Semantic Tool Selection")
    print("=" * 60)

    # Define tools with rich descriptions
    tools = [
        ToolDescription(
            name="web_search",
            description="Search the internet for current information and recent news",
            category="information",
            examples=[
                "What's happening in tech today?",
                "Find recent news about AI",
                "Search for Python tutorials",
            ],
            tags=["search", "web", "news", "current", "online"],
        ),
        ToolDescription(
            name="calculator",
            description="Perform mathematical calculations and solve equations",
            category="computation",
            examples=[
                "Calculate 15% of 200",
                "What's 45 * 23?",
                "Solve x² - 5x + 6 = 0",
            ],
            tags=["math", "calculate", "compute", "arithmetic"],
        ),
        ToolDescription(
            name="weather",
            description="Get weather forecasts and current conditions for any location",
            category="information",
            examples=[
                "What's the weather in Seattle?",
                "Is it going to rain tomorrow?",
                "Temperature forecast for next week",
            ],
            tags=["weather", "temperature", "forecast", "rain", "climate"],
        ),
        ToolDescription(
            name="database_query",
            description="Query internal database for customer records and order history",
            category="data",
            examples=[
                "Find customer orders from last month",
                "Get user profile for john@example.com",
                "Show recent transactions",
            ],
            tags=["database", "sql", "records", "data", "query"],
        ),
    ]

    # Create selector
    selector = SemanticToolSelector(tools=tools, provider=SimpleMockProvider(), min_confidence=0.3)

    print("\n📊 Initialized selector with 4 tools")
    print(f"Tools: {', '.join(t.name for t in tools)}")

    # Test natural language queries
    queries = [
        "I need to know if I should bring an umbrella today",
        "What's 15% of my $250 bill?",
        "Can you find me some information about Python 3.12?",
        "Show me orders from customer ID 12345",
    ]

    print("\n🔍 Testing semantic matching:")
    for query in queries:
        matches = await selector.select(query, top_k=2, include_reasoning=True)

        print(f"\nQuery: '{query}'")
        if matches:
            top_match = matches[0]
            print(f"  ✓ Selected: {top_match.name}")
            print(f"  ✓ Confidence: {top_match.confidence:.2%}")
            if top_match.reasoning:
                print(f"  ✓ Reasoning: {top_match.reasoning}")
        else:
            print("  ✗ No suitable tool found")


async def example_2_keyword_vs_semantic():
    """Example 2: Keyword matching vs semantic matching."""
    print("\n" + "=" * 60)
    print("Example 2: Keyword vs Semantic Matching")
    print("=" * 60)

    tools = [
        ToolDescription(
            name="email_sender",
            description="Send email messages to recipients",
            examples=["Send email to john@example.com", "Email the report"],
            tags=["email", "send", "message"],
        ),
        ToolDescription(
            name="calendar",
            description="Schedule meetings and manage appointments",
            examples=["Schedule a meeting", "Add event to calendar"],
            tags=["calendar", "meeting", "schedule", "appointment"],
        ),
    ]

    selector = SemanticToolSelector(tools=tools, provider=SimpleMockProvider())

    # Query without obvious keywords
    query = "I need to arrange a discussion with my team next Tuesday"

    print(f"\nQuery: '{query}'")
    print("\nKeyword matching would struggle (no 'meeting' or 'schedule' keywords)")
    print("Semantic matching understands intent:")

    matches = await selector.select(query, top_k=1)
    if matches:
        print(f"  ✓ Selected: {matches[0].name}")
        print(f"  ✓ Confidence: {matches[0].confidence:.2%}")
        print("  ✓ Understood: 'arrange a discussion' → scheduling/calendar functionality")


async def example_3_batch_selection():
    """Example 3: Efficient batch processing."""
    print("\n" + "=" * 60)
    print("Example 3: Batch Tool Selection (Performance)")
    print("=" * 60)

    tools = [
        ToolDescription(
            name="translator",
            description="Translate text between languages",
            examples=["Translate to Spanish", "Convert to French"],
        ),
        ToolDescription(
            name="summarizer",
            description="Summarize long documents and articles",
            examples=["Summarize this document", "Create a brief summary"],
        ),
        ToolDescription(
            name="sentiment_analyzer",
            description="Analyze sentiment and emotion in text",
            examples=["Is this review positive?", "Analyze customer feedback"],
        ),
    ]

    selector = SemanticToolSelector(tools=tools, provider=SimpleMockProvider())

    # Process multiple queries at once
    queries = [
        "Convert this text to German",
        "What's the overall tone of these comments?",
        "Give me a short version of this article",
    ]

    print(f"\n⚡ Processing {len(queries)} queries in batch...")

    import time

    start = time.time()
    results = await selector.select_batch(queries, top_k=1)
    elapsed = time.time() - start

    print(f"✓ Completed in {elapsed:.3f}s")
    print("\nResults:")
    for query, matches in zip(queries, results, strict=False):
        if matches:
            print(f"  '{query[:40]}...' → {matches[0].name}")


async def example_4_dynamic_tools():
    """Example 4: Adding/removing tools dynamically."""
    print("\n" + "=" * 60)
    print("Example 4: Dynamic Tool Management")
    print("=" * 60)

    # Start with basic tools
    tools = [
        ToolDescription(name="calculator", description="Perform calculations"),
        ToolDescription(name="timer", description="Set timers and alarms"),
    ]

    selector = SemanticToolSelector(tools=tools, provider=SimpleMockProvider())
    await selector.initialize()

    print(f"\n📦 Initial tools: {', '.join(t.name for t in tools)}")

    # Add new tool
    print("\n➕ Adding image_generator tool...")
    selector.add_tool(
        ToolDescription(
            name="image_generator",
            description="Generate images from text descriptions",
            examples=["Create an image of a sunset", "Generate a logo"],
        )
    )

    # Re-initialize to cache new embeddings
    await selector.initialize()

    stats = selector.get_statistics()
    print(f"✓ Total tools: {stats['total_tools']}")

    # Test with new tool
    matches = await selector.select("Create a picture of a mountain", top_k=1)
    if matches:
        print(f"✓ Query 'Create a picture...' → {matches[0].name}")


async def example_5_production_patterns():
    """Example 5: Production deployment patterns."""
    print("\n" + "=" * 60)
    print("Example 5: Production Patterns")
    print("=" * 60)

    print(
        """
💡 Production Best Practices:

1. **Use Real Embedding Providers**:
   from agenkit.routing.semantic_selector import OpenAIEmbeddingProvider

   provider = OpenAIEmbeddingProvider(
       api_key=os.getenv("OPENAI_API_KEY"),
       model="text-embedding-3-small"  # Fast & cheap
   )

2. **Pre-initialize for Performance**:
   selector = SemanticToolSelector(tools=tools, provider=provider)
   await selector.initialize()  # Do this once at startup

   # Then use selector.select() many times (fast!)

3. **Set Appropriate Thresholds**:
   selector = SemanticToolSelector(
       tools=tools,
       provider=provider,
       min_confidence=0.6  # Adjust based on your needs
   )

4. **Monitor Statistics**:
   stats = selector.get_statistics()
   print(f"Tools: {stats['total_tools']}")
   print(f"Categories: {stats['categories']}")

5. **Handle No Matches**:
   matches = await selector.select(query, top_k=1)
   if not matches:
       # Fall back to default tool or ask user for clarification
       print("Could not confidently select a tool")

6. **Category-Based Filtering**:
   # Include category in tool descriptions for better organization
   # Tools in same category will have more similar embeddings
"""
    )

    print("\n✅ Semantic tool selection enables:")
    print("  - Natural language tool selection")
    print("  - No keyword engineering required")
    print("  - Better handling of synonyms and paraphrasing")
    print("  - Scalable to hundreds of tools")


async def main():
    """Run all examples."""
    print("\n🚀 Semantic Tool Selection Examples")
    print("=" * 60)

    await example_1_basic_selection()
    await example_2_keyword_vs_semantic()
    await example_3_batch_selection()
    await example_4_dynamic_tools()
    await example_5_production_patterns()

    print("\n" + "=" * 60)
    print("✅ Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
