"""
Example 2: Sequential Pattern

This example shows how to chain agents in a pipeline.
"""

import asyncio
from agenkit import Agent, Message, SequentialPattern


class ValidatorAgent(Agent):
    """Validates input."""

    @property
    def name(self) -> str:
        return "validator"

    async def process(self, message: Message) -> Message:
        text = str(message.content)

        if len(text) < 3:
            return Message(
                role="agent",
                content="ERROR: Input too short",
                metadata={"valid": False}
            )

        return Message(
            role="agent",
            content=text,
            metadata={"valid": True}
        )


class ProcessorAgent(Agent):
    """Processes valid input."""

    @property
    def name(self) -> str:
        return "processor"

    async def process(self, message: Message) -> Message:
        # Check if previous validation passed
        if not message.metadata.get("valid", True):
            return message

        text = str(message.content)
        processed = text.upper().strip()

        return Message(
            role="agent",
            content=processed,
            metadata={"processed": True}
        )


class FormatterAgent(Agent):
    """Formats the final output."""

    @property
    def name(self) -> str:
        return "formatter"

    async def process(self, message: Message) -> Message:
        text = str(message.content)

        if text.startswith("ERROR:"):
            return message

        formatted = f"✓ Result: {text}"

        return Message(
            role="agent",
            content=formatted,
            metadata={"formatted": True}
        )


async def main():
    """Run the example."""
    # Create pipeline: validate → process → format
    pipeline = SequentialPattern([
        ValidatorAgent(),
        ProcessorAgent(),
        FormatterAgent()
    ])

    # Test valid input
    print("Test 1: Valid input")
    msg1 = Message(role="user", content="hello world")
    result1 = await pipeline.process(msg1)
    print(f"Input: {msg1.content}")
    print(f"Output: {result1.content}")
    print()

    # Test invalid input
    print("Test 2: Invalid input")
    msg2 = Message(role="user", content="hi")
    result2 = await pipeline.process(msg2)
    print(f"Input: {msg2.content}")
    print(f"Output: {result2.content}")


if __name__ == "__main__":
    asyncio.run(main())
