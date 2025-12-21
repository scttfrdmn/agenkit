"""
AGENTS.md middleware integration example.

Demonstrates using AgentsMdMiddleware to automatically inject project
context into agent prompts.
"""

import asyncio
from pathlib import Path

from agenkit import Agent, Message
from agenkit.agents_md import AgentsMdMiddleware


class EchoAgent(Agent):
    """Simple echo agent for demonstration."""

    @property
    def name(self) -> str:
        return "echo-agent"

    async def process(self, message: Message) -> Message:
        """Echo message with metadata."""
        # In a real agent, this would process with an LLM
        # For demo, just show what context was injected
        response = f"Received message with {len(message.content)} chars"

        if message.metadata and message.metadata.get("agents_md_context"):
            files = message.metadata.get("agents_md_files", [])
            response += f"\n\nAGENTS.md context injected from {len(files)} files:"
            for f in files:
                response += f"\n  - {f}"

        return Message(
            role="assistant",
            content=response,
            metadata={"original_length": len(message.content)},
        )


async def main():
    """Run middleware integration example."""
    print("=== AGENTS.md Middleware Integration ===\n")

    # Create base agent
    base_agent = EchoAgent()

    # Wrap with AGENTS.md middleware
    project_root = Path(__file__).parent
    agent = AgentsMdMiddleware(base_agent, project_root=project_root)

    print(f"Agent name: {agent.name}")
    print(f"Capabilities: {agent.capabilities}\n")

    # Process message - context will be automatically injected
    print("Processing message...\n")
    message = Message(
        role="user", content="Write a function to calculate the total of a list"
    )

    response = await agent.process(message)
    print(f"Response: {response.content}\n")

    # The agent now has context from AGENTS.md, including:
    # - Setup instructions
    # - Code style guidelines
    # - Testing procedures
    # - Architecture overview
    # - Common patterns

    print("The agent processed the message with full project context!")
    print("This includes code style, testing practices, and common patterns.")
    print("\nIn a real LLM agent, this would result in code that follows")
    print("your project's conventions automatically.\n")

    # Example with user message showing how context helps
    print("=== Example: Code Style Application ===\n")
    print("Without AGENTS.md:")
    print("  - Agent might use inconsistent naming")
    print("  - Missing type hints")
    print("  - No docstrings\n")

    print("With AGENTS.md:")
    print("  - Follows your code style automatically")
    print("  - Adds type hints (from Code Style section)")
    print("  - Includes docstrings (from Code Style section)")
    print("  - Uses project patterns (from Patterns section)")


if __name__ == "__main__":
    asyncio.run(main())
