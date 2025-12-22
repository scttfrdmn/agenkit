"""
Sequential Pattern Usage Example.

Demonstrates the Sequential pattern for creating processing pipelines where
each agent's output becomes the input for the next agent.

Use cases:
- Multi-stage data transformations
- Document processing workflows
- Step-by-step refinement

This example shows:
- Creating a content moderation pipeline
- Passing data through transformation stages
- Accessing pipeline metadata
- Error propagation through the pipeline
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import SequentialAgent


class ContentExtractor(Agent):
    """Extracts structured content from raw text."""

    def name(self) -> str:
        return "ContentExtractor"

    def capabilities(self) -> list[str]:
        return ["extraction", "parsing"]

    async def process(self, message: Message) -> Message:
        """Extract key content elements."""
        print("📄 Stage 1: Extracting content...")

        # Simulate extraction
        lines = message.content.split("\n")
        content = {
            "text": message.content,
            "line_count": len(lines),
            "word_count": len(message.content.split()),
            "has_urls": "http" in message.content.lower(),
        }

        result = Message(
            role="agent",
            content=f"Extracted content: {content['word_count']} words, "
            f"{content['line_count']} lines",
        )
        result.metadata.update(
            {
                "stage": "extraction",
                "content_info": content,
            }
        )

        print("   ✓ Content extracted")
        return result


class ContentModerator(Agent):
    """Checks content against moderation policies."""

    def name(self) -> str:
        return "ContentModerator"

    def capabilities(self) -> list[str]:
        return ["moderation", "safety"]

    async def process(self, message: Message) -> Message:
        """Moderate content for safety."""
        print("\n🛡️  Stage 2: Moderating content...")

        # Get original content from metadata
        original = message.content
        if "content_info" in message.metadata:
            original = message.metadata["content_info"].get("text", message.content)

        # Simple moderation rules
        flagged_words = ["spam", "malicious", "harmful"]
        flags = [word for word in flagged_words if word in original.lower()]

        is_safe = len(flags) == 0
        status = "approved" if is_safe else "flagged"

        result = Message(
            role="agent",
            content=f"Moderation: {status}",
        )
        result.metadata.update(
            {
                "stage": "moderation",
                "safe": is_safe,
                "flags": flags,
                "previous_metadata": message.metadata,
            }
        )

        print(f"   ✓ Content {status}")
        return result


class ContentEnricher(Agent):
    """Enriches content with metadata and tags."""

    def name(self) -> str:
        return "ContentEnricher"

    def capabilities(self) -> list[str]:
        return ["enrichment", "tagging"]

    async def process(self, message: Message) -> Message:
        """Enrich content with additional metadata."""
        print("\n✨ Stage 3: Enriching content...")

        # Extract previous stage info
        is_safe = message.metadata.get("safe", False)
        prev_meta = message.metadata.get("previous_metadata", {})
        content_info = prev_meta.get("content_info", {})

        # Add enrichment
        tags = []
        if content_info.get("has_urls"):
            tags.append("contains-links")
        if content_info.get("word_count", 0) > 50:
            tags.append("long-form")
        else:
            tags.append("short-form")
        if is_safe:
            tags.append("safe")

        result = Message(
            role="agent",
            content=f"Processing complete: {', '.join(tags)}",
        )
        result.metadata.update(
            {
                "stage": "enrichment",
                "tags": tags,
                "safe": is_safe,
                "content_info": content_info,
            }
        )

        print(f"   ✓ Content enriched with tags: {', '.join(tags)}")
        return result


async def basic_pipeline():
    """Demonstrate basic sequential pipeline."""
    print("=" * 60)
    print("Example 1: Basic Content Processing Pipeline")
    print("=" * 60)

    # Create pipeline
    pipeline = SequentialAgent(
        [
            ContentExtractor(),
            ContentModerator(),
            ContentEnricher(),
        ]
    )

    # Process message
    message = Message(
        role="user",
        content="Check out this amazing new AI framework!\n"
        "It makes building agents easy and fun.\n"
        "Visit https://example.com to learn more.",
    )

    print(f"\n📥 Input:\n{message.content}\n")
    result = await pipeline.process(message)

    print(f"\n📤 Final Output: {result.content}")
    print("\nMetadata:")
    print(f"  Tags: {result.metadata.get('tags')}")
    print(f"  Safe: {result.metadata.get('safe')}")
    print(f"  Pipeline stages: {result.metadata.get('pipeline_length', 0)}")


async def error_handling():
    """Demonstrate error handling in pipeline."""
    print("\n\n" + "=" * 60)
    print("Example 2: Error Handling")
    print("=" * 60)

    class FailingAgent(Agent):
        """An agent that fails to demonstrate error propagation."""

        def name(self) -> str:
            return "FailingAgent"

        def capabilities(self) -> list[str]:
            return ["failure"]

        async def process(self, message: Message) -> Message:
            raise ValueError("Simulated processing error")

    # Create pipeline with failing agent
    pipeline = SequentialAgent(
        [
            ContentExtractor(),
            FailingAgent(),
            ContentEnricher(),
        ]
    )

    message = Message(role="user", content="Test message")

    print("\n📥 Processing with failing agent...")
    try:
        result = await pipeline.process(message)
        print(f"Result: {result.content}")
    except Exception as e:
        print(f"✓ Pipeline stopped on error (expected): {e}")


async def conditional_pipeline():
    """Demonstrate pipeline with metadata-based decisions."""
    print("\n\n" + "=" * 60)
    print("Example 3: Metadata Flow Through Pipeline")
    print("=" * 60)

    # Create pipeline
    pipeline = SequentialAgent(
        [
            ContentExtractor(),
            ContentModerator(),
            ContentEnricher(),
        ]
    )

    # Test with flagged content
    message = Message(
        role="user",
        content="This is spam content with malicious intent.",
    )

    print(f"\n📥 Input (flagged content):\n{message.content}\n")
    result = await pipeline.process(message)

    print(f"\n📤 Final Output: {result.content}")
    print("\nMetadata:")
    print(f"  Tags: {result.metadata.get('tags')}")
    print(f"  Safe: {result.metadata.get('safe')}")
    if not result.metadata.get("safe"):
        print("  ⚠️  Content was flagged during moderation")


async def main():
    """Run all examples."""
    print("\n🔄 Sequential Pattern Usage Examples\n")

    await basic_pipeline()
    await error_handling()
    await conditional_pipeline()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
