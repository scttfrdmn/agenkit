"""Streaming chat UI example with MiniCopilotKit.

This example demonstrates:
- Streaming chat interface (like <CopilotChat>)
- Real-time message updates
- Tool call visualization
- Simple text-based UI

Compare with CopilotKit:
- CopilotKit: <CopilotChat> React component
- MiniCopilotKit: ChatUI with AG-UI events
- Both: Streaming, tool visualization, real-time updates
"""

import asyncio

from agenkit import Agent, Message

from minicopilotkit import ChatUI, CopilotAgent


class AssistantAgent(Agent):
    """Simple assistant agent."""

    @property
    def name(self) -> str:
        return "AssistantAgent"

    async def process(self, message: Message) -> Message:
        """Process user message."""
        content = message.content.lower()

        if "hello" in content or "hi" in content:
            response = "Hello! I'm your assistant. How can I help you today?"
        elif "weather" in content:
            response = (
                "I don't have real-time weather data, but I can help you find weather information!"
            )
        elif "help" in content:
            response = (
                "I can assist with:\n"
                "  • General questions\n"
                "  • Information lookup\n"
                "  • Task planning\n"
                "\nWhat would you like help with?"
            )
        else:
            response = f"You said: '{message.content}'. How can I help with that?"

        return Message(role="assistant", content=response)


async def demo_basic_chat():
    """Demonstrate basic chat functionality."""
    print("=" * 60)
    print("Basic Chat UI Demo")
    print("=" * 60)
    print()

    # Create agent
    agent = AssistantAgent()
    copilot = CopilotAgent(agent)

    # Create chat UI
    ui = ChatUI(copilot)

    # Send messages
    messages = [
        "Hello!",
        "What's the weather like?",
        "Can you help me?",
    ]

    for msg in messages:
        print(f"User: {msg}")
        response = await ui.send_message(msg)
        print(f"Assistant: {response}")
        print()

    # Display full chat history
    print("\n" + "=" * 60)
    print("Chat History:")
    print("=" * 60)
    print(ui.display_chat())


async def demo_streaming_visualization():
    """Demonstrate streaming with visual feedback."""
    print("\n\n" + "=" * 60)
    print("Streaming Visualization Demo")
    print("=" * 60)
    print()

    agent = AssistantAgent()
    copilot = CopilotAgent(agent)

    message = Message(role="user", content="Tell me about AI agents")
    print("User: Tell me about AI agents")
    print("Assistant: ", end="", flush=True)

    # Stream response with visual feedback
    async for event in copilot.stream_chat(message, "demo-thread"):
        if event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


async def demo_with_context():
    """Demonstrate chat with conversation context."""
    print("\n" + "=" * 60)
    print("Contextual Chat Demo")
    print("=" * 60)
    print()

    agent = AssistantAgent()
    copilot = CopilotAgent(agent)
    ui = ChatUI(copilot)

    # Multi-turn conversation
    conversation = [
        ("What can you help me with?", "I'll show you what I can do"),
        ("Great, let's start", "I'm ready to help"),
        ("Thank you!", "You're welcome! What else can I help with?"),
    ]

    for user_msg, _ in conversation:
        print(f"User: {user_msg}")
        response = await ui.send_message(user_msg)
        print(f"Assistant: {response}")
        print()


async def main():
    """Run all chat UI demos."""
    print("🤖 MiniCopilotKit - Streaming Chat UI\n")

    await demo_basic_chat()
    await demo_streaming_visualization()
    await demo_with_context()

    print("\n" + "=" * 60)
    print("Key Concepts:")
    print("=" * 60)
    print("""
1. **ChatUI Class**:
   - Similar to CopilotKit's <CopilotChat>
   - Manages conversation state
   - Streams responses in real-time

2. **Streaming Events**:
   - text_message_content: Incremental text chunks
   - text_message_start/end: Message boundaries
   - Real-time UI updates

3. **CopilotAgent Wrapper**:
   - Wraps any Agenkit agent
   - Adds CopilotKit-style features
   - Maintains conversation context

4. **Comparison**:
   CopilotKit:
   - <CopilotChat> React component
   - Built on AG-UI protocol
   - Streaming via SSE/WebSocket

   MiniCopilotKit:
   - ChatUI Python class
   - Built on AG-UI protocol
   - Same streaming events

   Both use AG-UI Standard under the hood!
""")


if __name__ == "__main__":
    asyncio.run(main())
