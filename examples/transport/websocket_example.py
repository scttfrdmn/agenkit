"""WebSocket Transport Example.

This example demonstrates the WebSocket transport for Agenkit, showing:
- Setting up WebSocket server and client
- Regular request/response communication
- Streaming responses
- Benefits of WebSocket over HTTP

WHY USE WEBSOCKET?
==================

WebSocket is ideal when you need:

1. **Bidirectional Communication**: Unlike HTTP, WebSocket maintains a persistent,
   full-duplex connection allowing the server to push data to the client.

2. **Lower Latency**: After the initial handshake, WebSocket communication has
   minimal overhead compared to HTTP's request/response cycle.

3. **Single Persistent Connection**: Eliminates the overhead of establishing
   new connections for each request (as with HTTP).

4. **Real-time Applications**: Perfect for chat, live updates, streaming data,
   and interactive applications.

5. **Better for Streaming**: Natural fit for streaming responses where the server
   sends multiple chunks over time.

WHEN TO USE EACH TRANSPORT:
===========================

Use **WebSocket** when:
- You need real-time, bidirectional communication
- You're building interactive or streaming applications
- You want lower latency for frequent communications
- You need server-to-client push capabilities

Use **HTTP** when:
- You need simple request/response patterns
- You want to leverage HTTP infrastructure (load balancers, caching, etc.)
- You're exposing agents as REST APIs
- Firewall/proxy compatibility is a concern

Use **TCP** when:
- You need maximum performance in a controlled network
- You're building internal microservices
- You want direct, low-level communication
- You don't need HTTP semantics or WebSocket features

Use **Unix Socket** when:
- Communicating between processes on the same machine
- You need the highest performance and security
- You're building local development tools
"""

import asyncio

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class ChatAgent(Agent):
    """Simple chat agent that responds to messages."""

    @property
    def name(self) -> str:
        return "chat"

    async def process(self, message: Message) -> Message:
        """Process a single message and return a complete response."""
        user_message = message.content.lower()

        if "hello" in user_message or "hi" in user_message:
            response = "Hello! I'm a chat agent. How can I help you today?"
        elif "how are you" in user_message:
            response = "I'm doing great! Thanks for asking. How about you?"
        elif "bye" in user_message or "goodbye" in user_message:
            response = "Goodbye! Have a great day!"
        elif "help" in user_message:
            response = (
                "I can respond to greetings, check how you're doing, "
                "or provide information. Try asking me something!"
            )
        else:
            response = f"You said: '{message.content}'. That's interesting!"

        return Message(role="agent", content=response)


class StoryAgent(Agent):
    """Agent that streams a story in chunks."""

    @property
    def name(self) -> str:
        return "story"

    async def process(self, message: Message) -> Message:
        """Return complete story."""
        return Message(
            role="agent",
            content=(
                "Once upon a time, in a land of code and data, "
                "there lived agents who processed messages. "
                "They communicated over many transports, "
                "but WebSocket was their favorite for real-time chat. "
                "The End."
            ),
        )

    async def stream(self, message: Message):
        """Stream story one sentence at a time."""
        story_parts = [
            "Once upon a time, in a land of code and data,",
            "there lived agents who processed messages.",
            "They communicated over many transports:",
            "HTTP for simplicity, TCP for speed,",
            "Unix sockets for local efficiency,",
            "but WebSocket was their favorite for real-time chat.",
            "The persistent connection kept them together,",
            "and the low latency made conversations flow naturally.",
            "And they all lived happily ever after.",
            "The End.",
        ]

        for i, part in enumerate(story_parts):
            # Simulate natural typing delay
            await asyncio.sleep(0.3)
            yield Message(
                role="agent",
                content=part,
                metadata={"part": i + 1, "total": len(story_parts)},
            )


async def run_chat_example():
    """Demonstrate basic WebSocket request/response."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Chat with WebSocket")
    print("=" * 70)
    print()
    print("Starting WebSocket server on ws://127.0.0.1:8765...")

    # Create and start server
    chat_agent = ChatAgent()
    server = LocalAgent(chat_agent, endpoint="ws://127.0.0.1:8765")
    await server.start()

    try:
        # Create client
        remote = RemoteAgent("chat", endpoint="ws://127.0.0.1:8765")
        print("Client connected!\n")

        # Have a conversation
        conversation = [
            "Hello!",
            "How are you?",
            "What can you do?",
            "Tell me something interesting.",
            "Goodbye!",
        ]

        for user_msg in conversation:
            print(f"User: {user_msg}")
            message = Message(role="user", content=user_msg)
            response = await remote.process(message)
            print(f"Agent: {response.content}\n")

            # Small delay between messages
            await asyncio.sleep(0.5)

    finally:
        await server.stop()
        print("Server stopped.\n")


async def run_streaming_example():
    """Demonstrate WebSocket streaming."""
    print("=" * 70)
    print("EXAMPLE 2: Streaming Story with WebSocket")
    print("=" * 70)
    print()
    print("Starting WebSocket server on ws://127.0.0.1:8766...")

    # Create and start server
    story_agent = StoryAgent()
    server = LocalAgent(story_agent, endpoint="ws://127.0.0.1:8766")
    await server.start()

    try:
        # Create client
        remote = RemoteAgent("story", endpoint="ws://127.0.0.1:8766")
        print("Client connected!\n")

        # First, get complete story (non-streaming)
        print("--- Non-Streaming Mode ---")
        print("User: Tell me a story")
        message = Message(role="user", content="Tell me a story")
        response = await remote.process(message)
        print(f"Agent: {response.content}\n")

        await asyncio.sleep(1)

        # Now, get story via streaming
        print("--- Streaming Mode ---")
        print("User: Tell me a story (streamed)")
        print("Agent: ", end="", flush=True)

        message = Message(role="user", content="Tell me a story")
        async for chunk in remote.stream(message):
            print(f"{chunk.content} ", end="", flush=True)
            # Part indicator
            if chunk.metadata.get("part") == chunk.metadata.get("total"):
                print()  # New line at the end

        print()

    finally:
        await server.stop()
        print("\nServer stopped.\n")


async def run_concurrent_example():
    """Demonstrate concurrent WebSocket connections."""
    print("=" * 70)
    print("EXAMPLE 3: Concurrent WebSocket Connections")
    print("=" * 70)
    print()
    print("Starting WebSocket server on ws://127.0.0.1:8767...")

    # Create and start server
    chat_agent = ChatAgent()
    server = LocalAgent(chat_agent, endpoint="ws://127.0.0.1:8767")
    await server.start()

    try:
        print("Creating 5 concurrent clients...\n")

        # Create multiple clients
        clients = [
            RemoteAgent("chat", endpoint="ws://127.0.0.1:8767") for _ in range(5)
        ]

        # Send concurrent requests
        async def send_message(client_id, remote):
            message = Message(role="user", content=f"Hello from client {client_id}")
            response = await remote.process(message)
            print(f"Client {client_id}: {response.content}")

        tasks = [send_message(i, client) for i, client in enumerate(clients)]
        await asyncio.gather(*tasks)

        print("\nAll clients completed successfully!")
        print(
            "Note: WebSocket maintains separate connections for each client,\n"
            "allowing true concurrent communication."
        )

    finally:
        await server.stop()
        print("\nServer stopped.\n")


async def run_persistence_example():
    """Demonstrate WebSocket connection persistence."""
    print("=" * 70)
    print("EXAMPLE 4: Connection Persistence")
    print("=" * 70)
    print()
    print("Starting WebSocket server on ws://127.0.0.1:8768...")

    # Create and start server
    chat_agent = ChatAgent()
    server = LocalAgent(chat_agent, endpoint="ws://127.0.0.1:8768")
    await server.start()

    try:
        # Create client
        remote = RemoteAgent("chat", endpoint="ws://127.0.0.1:8768")
        print("Client connected!\n")

        print("Sending 10 messages over the same persistent connection...\n")

        # Send multiple messages over the same connection
        for i in range(10):
            message = Message(role="user", content=f"Message {i + 1}")
            response = await remote.process(message)
            print(f"  [{i + 1}/10] {response.content}")

        print(
            "\nAll messages sent over a SINGLE WebSocket connection!"
            "\n(With HTTP, each request would need a new connection or keep-alive)"
        )

    finally:
        await server.stop()
        print("\nServer stopped.\n")


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "WebSocket Transport Demo" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Run examples
    await run_chat_example()
    await asyncio.sleep(1)

    await run_streaming_example()
    await asyncio.sleep(1)

    await run_concurrent_example()
    await asyncio.sleep(1)

    await run_persistence_example()

    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("WebSocket Benefits Demonstrated:")
    print("  ✓ Persistent connection (Example 4)")
    print("  ✓ Low-latency communication (All examples)")
    print("  ✓ Excellent streaming support (Example 2)")
    print("  ✓ Concurrent connections (Example 3)")
    print("  ✓ Bidirectional communication capability")
    print()
    print("WebSocket is perfect for:")
    print("  • Real-time applications (chat, live updates)")
    print("  • Streaming AI responses (LLM outputs)")
    print("  • Interactive agents")
    print("  • Long-running conversations")
    print()
    print("For simple request/response, consider HTTP.")
    print("For local inter-process communication, consider Unix sockets.")
    print("For maximum performance in controlled networks, consider TCP.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
