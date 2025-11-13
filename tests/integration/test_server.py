"""Simple HTTP test server for cross-language integration tests.

This server can be run standalone for testing Go clients against Python servers.

Usage:
    python -m tests.integration.test_server [port]
"""

import asyncio
import sys

from agenkit.adapters.python.http_server import HTTPAgentServer
from agenkit.interfaces import Agent, Message


class CrossLanguageTestAgent(Agent):
    """Test agent for cross-language integration tests."""

    @property
    def name(self) -> str:
        return "cross-language-test-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["echo", "metadata", "unicode", "streaming"]

    async def process(self, message: Message) -> Message:
        """Echo the message back with metadata.

        Args:
            message: Input message

        Returns:
            Message with echoed content and metadata
        """
        return Message(
            role="agent",
            content=f"Echo: {message.content}",
            metadata={
                "original_content": message.content,
                "original_role": message.role,
                "original_metadata": message.metadata,
                "server_language": "python",
                "server_name": self.name,
            }
        )


async def main():
    """Run the test server."""
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    # Create agent and HTTP server wrapper
    agent = CrossLanguageTestAgent()
    server = HTTPAgentServer(agent, host="localhost", port=port)

    print(f"Starting Python test server on port {port}...")
    print(f"Agent: {agent.name}")
    print(f"Capabilities: {agent.capabilities}")
    print("Press Ctrl+C to stop")

    try:
        await server.start()
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
