"""
Example 6: Pattern Composition

This example shows how to compose patterns to create complex workflows.
"""

import asyncio
from agenkit import Agent, Message, SequentialPattern, ParallelPattern, RouterPattern


# ============================================
# Analysis Agents (for parallel step)
# ============================================

class SentimentAgent(Agent):
    @property
    def name(self) -> str:
        return "sentiment"

    async def process(self, message: Message) -> Message:
        text = str(message.content).lower()
        sentiment = "positive" if "good" in text or "great" in text else "neutral"

        return Message(
            role="agent",
            content=message.content,
            metadata={**message.metadata, "sentiment": sentiment}
        )


class UrgencyAgent(Agent):
    @property
    def name(self) -> str:
        return "urgency"

    async def process(self, message: Message) -> Message:
        text = str(message.content).lower()
        urgent = any(word in text for word in ["urgent", "asap", "critical", "emergency"])

        return Message(
            role="agent",
            content=message.content,
            metadata={**message.metadata, "urgent": urgent}
        )


# ============================================
# Handler Agents (for router step)
# ============================================

class PriorityHandler(Agent):
    @property
    def name(self) -> str:
        return "priority"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"⚡ PRIORITY: {message.content}",
            metadata=message.metadata
        )


class StandardHandler(Agent):
    @property
    def name(self) -> str:
        return "standard"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"📝 Standard: {message.content}",
            metadata=message.metadata
        )


# ============================================
# Aggregator for Parallel Pattern
# ============================================

def merge_analysis(messages: list[Message]) -> Message:
    """Merge all analysis metadata."""
    # Start with first message
    merged = messages[0]

    # Merge metadata from all messages
    combined_metadata = {}
    for msg in messages:
        combined_metadata.update(msg.metadata)

    return Message(
        role=merged.role,
        content=merged.content,
        metadata=combined_metadata
    )


# ============================================
# Router Function
# ============================================

def route_by_urgency(message: Message) -> str:
    """Route based on urgency analysis."""
    is_urgent = message.metadata.get("urgent", False)
    return "priority" if is_urgent else "standard"


# ============================================
# Build Complex Workflow
# ============================================

def create_workflow() -> Agent:
    """
    Create a composed workflow:

    Sequential [
        Parallel [ SentimentAgent, UrgencyAgent ],
        Router { priority → PriorityHandler, standard → StandardHandler }
    ]

    Flow:
    1. Input message goes to parallel analysis
    2. Both sentiment and urgency agents analyze concurrently
    3. Results merged with metadata
    4. Router routes based on urgency
    5. Appropriate handler processes final message
    """

    # Step 1: Parallel analysis
    analysis = ParallelPattern(
        agents=[SentimentAgent(), UrgencyAgent()],
        aggregator=merge_analysis,
        name="analysis"
    )

    # Step 2: Router based on analysis
    router = RouterPattern(
        router=route_by_urgency,
        handlers={
            "priority": PriorityHandler(),
            "standard": StandardHandler()
        },
        name="handler"
    )

    # Compose into sequential workflow
    workflow = SequentialPattern(
        agents=[analysis, router],
        name="message_processor"
    )

    return workflow


async def main():
    """Run the example."""
    workflow = create_workflow()

    # Test cases
    test_cases = [
        "This is an urgent request that needs attention ASAP",
        "This is a good standard message",
        "Critical issue needs immediate action",
        "Just a regular update, no rush"
    ]

    for test in test_cases:
        msg = Message(role="user", content=test)
        result = await workflow.process(msg)

        print(f"Input: {test}")
        print(f"Output: {result.content}")
        print(f"Metadata: {result.metadata}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
