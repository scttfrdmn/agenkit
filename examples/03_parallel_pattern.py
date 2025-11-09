"""
Example 3: Parallel Pattern

This example shows how to run multiple agents concurrently.
"""

import asyncio
from agenkit import Agent, Message, ParallelPattern


class SentimentAgent(Agent):
    """Analyzes sentiment."""

    @property
    def name(self) -> str:
        return "sentiment"

    async def process(self, message: Message) -> Message:
        text = str(message.content).lower()

        # Simple sentiment analysis
        positive_words = ["good", "great", "excellent", "amazing", "love"]
        negative_words = ["bad", "terrible", "awful", "hate", "worst"]

        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)

        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return Message(
            role="agent",
            content={"sentiment": sentiment, "score": pos_count - neg_count}
        )


class LengthAgent(Agent):
    """Analyzes text length."""

    @property
    def name(self) -> str:
        return "length"

    async def process(self, message: Message) -> Message:
        text = str(message.content)

        analysis = {
            "chars": len(text),
            "words": len(text.split()),
            "category": "short" if len(text) < 50 else "long"
        }

        return Message(role="agent", content=analysis)


class KeywordAgent(Agent):
    """Extracts keywords."""

    @property
    def name(self) -> str:
        return "keyword"

    async def process(self, message: Message) -> Message:
        text = str(message.content).lower()

        # Simple keyword extraction (remove common words)
        common = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at"}
        words = [w.strip(".,!?") for w in text.split()]
        keywords = [w for w in words if w not in common and len(w) > 3]

        return Message(role="agent", content={"keywords": keywords[:5]})


def combine_analyses(messages: list[Message]) -> Message:
    """Combine all analysis results."""
    combined = {}

    for msg in messages:
        if isinstance(msg.content, dict):
            combined.update(msg.content)

    return Message(
        role="agent",
        content=combined,
        metadata={"analyses": len(messages)}
    )


async def main():
    """Run the example."""
    # Create parallel analyzer
    analyzer = ParallelPattern(
        agents=[
            SentimentAgent(),
            LengthAgent(),
            KeywordAgent()
        ],
        aggregator=combine_analyses
    )

    # Analyze text
    text = "This is an excellent example of parallel processing! I love how fast it is."
    msg = Message(role="user", content=text)

    print(f"Analyzing: {text}\n")

    result = await analyzer.process(msg)

    print("Combined Analysis:")
    for key, value in result.content.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
