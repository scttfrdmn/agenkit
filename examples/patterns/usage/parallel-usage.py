"""
Parallel Pattern Usage Example.

Demonstrates the Parallel pattern for concurrent execution of multiple agents
with result aggregation.

Use cases:
- Ensemble methods and voting
- Multi-perspective analysis
- Independent parallel tasks
- Fault-tolerant processing

This example shows:
- Running agents concurrently
- Different aggregation strategies
- Handling partial failures
- Custom aggregation functions
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import ParallelAgent, default_aggregators


class SentimentAnalyzer(Agent):
    """Analyzes sentiment of text."""

    def name(self) -> str:
        return "SentimentAnalyzer"

    def capabilities(self) -> list[str]:
        return ["sentiment", "analysis"]

    async def process(self, message: Message) -> Message:
        """Analyze sentiment."""
        print("   💭 Running sentiment analysis...")
        await asyncio.sleep(0.1)  # Simulate processing

        # Simple sentiment detection
        content = message.content.lower()
        if any(word in content for word in ["great", "excellent", "amazing"]):
            sentiment = "positive"
        elif any(word in content for word in ["bad", "poor", "terrible"]):
            sentiment = "negative"
        else:
            sentiment = "neutral"

        result = Message(
            role="agent",
            content=f"Sentiment: {sentiment}",
        )
        result.metadata["analysis_type"] = "sentiment"
        result.metadata["sentiment"] = sentiment
        return result


class TopicClassifier(Agent):
    """Classifies text into topics."""

    def name(self) -> str:
        return "TopicClassifier"

    def capabilities(self) -> list[str]:
        return ["classification", "topics"]

    async def process(self, message: Message) -> Message:
        """Classify topic."""
        print("   📚 Running topic classification...")
        await asyncio.sleep(0.15)  # Simulate processing

        # Simple topic detection
        content = message.content.lower()
        if any(word in content for word in ["product", "service", "business"]):
            topic = "business"
        elif any(word in content for word in ["ai", "technology", "software"]):
            topic = "technology"
        else:
            topic = "general"

        result = Message(
            role="agent",
            content=f"Topic: {topic}",
        )
        result.metadata["analysis_type"] = "topic"
        result.metadata["topic"] = topic
        return result


class EntityExtractor(Agent):
    """Extracts named entities from text."""

    def name(self) -> str:
        return "EntityExtractor"

    def capabilities(self) -> list[str]:
        return ["extraction", "entities"]

    async def process(self, message: Message) -> Message:
        """Extract entities."""
        print("   🏷️  Running entity extraction...")
        await asyncio.sleep(0.12)  # Simulate processing

        # Simple entity extraction (capitalized words)
        words = message.content.split()
        entities = [word.strip(",.!?") for word in words if word[0].isupper()]

        result = Message(
            role="agent",
            content=f"Entities: {', '.join(entities) if entities else 'none'}",
        )
        result.metadata["analysis_type"] = "entities"
        result.metadata["entities"] = entities
        return result


class ClassifierAgent(Agent):
    """Simple classifier for voting demonstrations."""

    def __init__(self, agent_name: str, classification: str):
        self._name = agent_name
        self._classification = classification

    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return ["classification"]

    async def process(self, message: Message) -> Message:
        """Return classification."""
        await asyncio.sleep(0.05)  # Simulate processing
        return Message(role="agent", content=self._classification)


async def multi_perspective_analysis():
    """Demonstrate multi-perspective analysis with concatenation."""
    print("=" * 60)
    print("Example 1: Multi-Perspective Analysis")
    print("=" * 60)

    # Create parallel agent with concatenation
    analyzer = ParallelAgent(
        agents=[
            SentimentAnalyzer(),
            TopicClassifier(),
            EntityExtractor(),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    message = Message(
        role="user",
        content="This AI technology is amazing! The Service team was excellent.",
    )

    print(f"\n📥 Input: {message.content}\n")
    print("Running 3 analyzers in parallel...")

    import time

    start = time.time()
    result = await analyzer.process(message)
    elapsed = time.time() - start

    print(f"\n📤 Combined Analysis:\n{result.content}")
    print(f"\n⏱️  Completed in {elapsed:.2f}s (parallel execution)")
    print(f"   Parallel agents: {result.metadata.get('parallel_agents', 0)}")
    print(f"   Successful: {result.metadata.get('successful_agents', 0)}")


async def majority_voting():
    """Demonstrate ensemble voting for classification."""
    print("\n\n" + "=" * 60)
    print("Example 2: Majority Voting Ensemble")
    print("=" * 60)

    # Create 5-classifier ensemble
    ensemble = ParallelAgent(
        agents=[
            ClassifierAgent("Classifier1", "spam"),
            ClassifierAgent("Classifier2", "spam"),
            ClassifierAgent("Classifier3", "legitimate"),
            ClassifierAgent("Classifier4", "spam"),
            ClassifierAgent("Classifier5", "legitimate"),
        ],
        aggregator=default_aggregators["majority_vote"],
    )

    message = Message(role="user", content="Check this out!")

    print(f"\n📥 Input: {message.content}")
    print("\nRunning 5-classifier ensemble...")

    result = await ensemble.process(message)

    print(f"\n📤 Ensemble Decision: {result.content}")
    print(f"   Votes: {result.metadata.get('votes', 0)}/{result.metadata.get('total_agents', 0)}")


async def fault_tolerance():
    """Demonstrate fault tolerance with partial failures."""
    print("\n\n" + "=" * 60)
    print("Example 3: Fault Tolerance")
    print("=" * 60)

    class FailingAgent(Agent):
        """An agent that always fails."""

        def name(self) -> str:
            return "FailingAgent"

        def capabilities(self) -> list[str]:
            return ["failure"]

        async def process(self, message: Message) -> Message:
            await asyncio.sleep(0.08)
            raise RuntimeError("Simulated failure")

    # Create parallel agent with one failing agent
    analyzer = ParallelAgent(
        agents=[
            SentimentAnalyzer(),
            FailingAgent(),
            TopicClassifier(),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    message = Message(role="user", content="This is a great product!")

    print(f"\n📥 Input: {message.content}")
    print("\nRunning with 1 failing agent...")

    result = await analyzer.process(message)

    print(f"\n📤 Results (from successful agents):\n{result.content}")
    print("\n⚠️  Partial execution:")
    print(f"   Total agents: {result.metadata.get('parallel_agents', 0)}")
    print(f"   Successful: {result.metadata.get('successful_agents', 0)}")
    if "errors" in result.metadata:
        errors = result.metadata["errors"]
        print(f"   Errors: {len(errors)}")
        for error in errors:
            print(f"     - {error.get('agent')}: {error.get('error')}")


async def custom_aggregation():
    """Demonstrate custom aggregation function."""
    print("\n\n" + "=" * 60)
    print("Example 4: Custom Aggregation")
    print("=" * 60)

    def sentiment_summary(messages: list[Message]) -> Message:
        """Custom aggregator that creates a sentiment summary."""
        sentiments = []
        topics = []
        entities = []

        for msg in messages:
            if "sentiment" in msg.metadata:
                sentiments.append(msg.metadata["sentiment"])
            if "topic" in msg.metadata:
                topics.append(msg.metadata["topic"])
            if "entities" in msg.metadata:
                entities.extend(msg.metadata["entities"])

        summary = "Analysis Summary:\n"
        summary += f"- Sentiment: {sentiments[0] if sentiments else 'unknown'}\n"
        summary += f"- Topic: {topics[0] if topics else 'unknown'}\n"
        summary += f"- Entities: {', '.join(entities) if entities else 'none'}\n"

        return Message(role="agent", content=summary)

    # Create analyzer with custom aggregation
    analyzer = ParallelAgent(
        agents=[
            SentimentAnalyzer(),
            TopicClassifier(),
            EntityExtractor(),
        ],
        aggregator=sentiment_summary,
    )

    message = Message(
        role="user",
        content="The Agenkit framework has excellent AI capabilities!",
    )

    print(f"\n📥 Input: {message.content}\n")

    result = await analyzer.process(message)

    print(f"📤 Custom Aggregation Result:\n{result.content}")


async def main():
    """Run all examples."""
    print("\n🔀 Parallel Pattern Usage Examples\n")

    await multi_perspective_analysis()
    await majority_voting()
    await fault_tolerance()
    await custom_aggregation()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
