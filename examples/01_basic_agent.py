"""
Example 1: Basic Agent

This example shows how to create a simple agent that processes messages.
"""

import asyncio
from agenkit import Agent, Message


class GreetingAgent(Agent):
    """Simple agent that greets users."""

    @property
    def name(self) -> str:
        return "greeting_agent"

    async def process(self, message: Message) -> Message:
        """Process a greeting request."""
        name = str(message.content)
        greeting = f"Hello, {name}! Welcome to agenkit."

        return Message(
            role="agent",
            content=greeting,
            metadata={"greeted": True}
        )


async def main():
    """Run the example."""
    agent = GreetingAgent()

    # Create a message
    msg = Message(
        role="user",
        content="Alice"
    )

    # Process it
    response = await agent.process(msg)

    print(f"User: {msg.content}")
    print(f"Agent: {response.content}")
    print(f"Metadata: {response.metadata}")


if __name__ == "__main__":
    asyncio.run(main())
