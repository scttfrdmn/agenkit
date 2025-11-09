"""Basic remote agent example.

This example demonstrates how to expose a local agent over the protocol adapter
and access it remotely.
"""

import asyncio
import tempfile
from pathlib import Path

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class GreeterAgent(Agent):
    """Simple greeter agent."""

    @property
    def name(self) -> str:
        return "greeter"

    async def process(self, message: Message) -> Message:
        """Greet the user."""
        user_message = message.content
        greeting = f"Hello! You said: '{user_message}'. Nice to meet you!"
        return Message(role="agent", content=greeting)


async def main() -> None:
    """Run the example."""
    # Create temporary socket path
    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "greeter.sock"
        endpoint = f"unix://{socket_path}"

        print("=== Basic Remote Agent Example ===\n")

        # 1. Create and start the local agent server
        print("1. Starting local agent server...")
        greeter = GreeterAgent()
        server = LocalAgent(greeter, endpoint=endpoint)
        await server.start()
        print(f"   Server listening on: {socket_path}\n")

        # 2. Create a remote agent client
        print("2. Creating remote agent client...")
        remote = RemoteAgent("greeter", endpoint=endpoint)
        print("   Client connected!\n")

        # 3. Send messages through the remote agent
        print("3. Sending messages...\n")

        messages = [
            "Hello, agent!",
            "How are you?",
            "Tell me about yourself",
        ]

        for msg_content in messages:
            msg = Message(role="user", content=msg_content)
            print(f"   User: {msg_content}")

            response = await remote.process(msg)
            print(f"   Agent: {response.content}\n")

        # 4. Clean up
        print("4. Shutting down...")
        await server.stop()
        print("   Done!\n")


if __name__ == "__main__":
    asyncio.run(main())
