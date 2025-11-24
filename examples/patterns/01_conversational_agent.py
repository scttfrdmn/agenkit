"""
Conversational Agent Example

Demonstrates how to use ConversationalAgent to maintain context across
multiple turns of conversation.

This example uses a mock LLM for demonstration purposes. In production,
you would use a real LLM client (OpenAI, Anthropic, etc.).
"""

import asyncio

from agenkit import Message
from agenkit.patterns import ConversationalAgent


class MockLLMClient:
    """
    Mock LLM client for demonstration.

    In production, replace this with a real LLM client:
    - OpenAI: from openai import AsyncOpenAI
    - Anthropic: from anthropic import AsyncAnthropic
    - LiteLLM: from litellm import acompletion
    """

    def __init__(self):
        self.call_count = 0

    async def chat(self, messages: list[Message]) -> Message:
        """Generate a mock response based on conversation context."""
        self.call_count += 1

        # Get the last user message
        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return Message(role="assistant", content="Hello! How can I help you?")

        last_message = user_messages[-1].content.lower()

        # Simple pattern matching for demo
        # Check for "what's my name" questions first (more specific)
        if "what" in last_message and "my name" in last_message:
            # Look for name in history
            for msg in reversed(messages):
                if msg.role == "user" and "my name is" in msg.content.lower():
                    words = msg.content.lower().split()
                    if "is" in words:
                        idx = words.index("is")
                        name = words[idx + 1].strip(".,!?")
                        return Message(
                            role="assistant", content=f"Your name is {name.capitalize()}."
                        )
            return Message(
                role="assistant",
                content="I don't recall you telling me your name yet.",
            )

        elif "name" in last_message and "my" in last_message and "is" in last_message:
            # Extract name (simple parsing)
            words = last_message.split()
            if "is" in words:
                idx = words.index("is")
                name = words[idx + 1].strip(".,!?")
                return Message(
                    role="assistant",
                    content=f"Nice to meet you, {name.capitalize()}! How can I assist you today?",
                )

        elif "favorite" in last_message and "color" in last_message:
            return Message(
                role="assistant",
                content="That's a great color choice! I don't have a favorite color myself, but I appreciate all colors equally.",
            )

        elif "remember" in last_message:
            # Show awareness of history
            return Message(
                role="assistant",
                content=f"Yes, I remember our conversation. We've exchanged {len(messages)} messages so far.",
            )

        else:
            return Message(
                role="assistant",
                content="I understand. Is there anything specific I can help you with?",
            )


async def basic_conversation_example():
    """Demonstrate basic conversational agent usage."""
    print("=" * 60)
    print("Example 1: Basic Conversation")
    print("=" * 60)

    # Create agent with system prompt
    llm = MockLLMClient()
    agent = ConversationalAgent(
        llm_client=llm,
        max_history=10,
        system_prompt="You are a helpful and friendly assistant.",
    )

    # Simulate a conversation
    conversation = [
        "Hi! My name is Alice.",
        "What's my name?",
        "My favorite color is blue.",
        "Can you remember what we talked about?",
    ]

    for user_input in conversation:
        print(f"\nUser: {user_input}")
        response = await agent.process(Message(role="user", content=user_input))
        print(f"Assistant: {response.content}")

    # Show history
    print(f"\nConversation length: {agent.get_context_length()} messages")


async def history_management_example():
    """Demonstrate history management features."""
    print("\n" + "=" * 60)
    print("Example 2: History Management")
    print("=" * 60)

    llm = MockLLMClient()
    agent = ConversationalAgent(llm_client=llm, max_history=5)  # Small limit

    # Fill up history
    for i in range(4):
        msg = Message(role="user", content=f"Message {i + 1}")
        await agent.process(msg)

    print(f"History after 4 exchanges: {agent.get_context_length()} messages")

    # Add one more - should trigger pruning
    await agent.process(Message(role="user", content="Message 5"))
    print(f"History after 5 exchanges: {agent.get_context_length()} messages")
    print("(Oldest messages were pruned to stay within limit)")

    # Export history
    history_export = agent.export_history()
    print(f"\nExported history: {len(history_export)} messages")

    # Clear and import
    agent.clear_history()
    print(f"History after clear: {agent.get_context_length()} messages")

    agent.import_history(history_export)
    print(f"History after import: {agent.get_context_length()} messages")


async def context_preservation_example():
    """Demonstrate how context is preserved across turns."""
    print("\n" + "=" * 60)
    print("Example 3: Context Preservation")
    print("=" * 60)

    llm = MockLLMClient()
    agent = ConversationalAgent(
        llm_client=llm,
        max_history=10,
        system_prompt="You are a helpful assistant with a good memory.",
    )

    # Provide information
    print("\nUser: My name is Bob and I'm a software engineer.")
    response1 = await agent.process(
        Message(role="user", content="My name is Bob and I'm a software engineer.")
    )
    print(f"Assistant: {response1.content}")

    # Ask unrelated question
    print("\nUser: What's the weather like?")
    response2 = await agent.process(Message(role="user", content="What's the weather like?"))
    print(f"Assistant: {response2.content}")

    # Reference earlier information
    print("\nUser: What did I say my name was?")
    response3 = await agent.process(Message(role="user", content="What did I say my name was?"))
    print(f"Assistant: {response3.content}")

    # Show that context includes all previous messages
    print(f"\nThe agent has access to {agent.get_context_length()} messages of context")
    print("This allows it to remember information from earlier in the conversation")


async def streaming_example():
    """Demonstrate streaming conversational agent."""
    print("\n" + "=" * 60)
    print("Example 4: Streaming Responses")
    print("=" * 60)

    from agenkit.patterns import StreamingConversationalAgent

    # Note: This example shows the API, but MockLLMClient doesn't support streaming
    # In production, use an LLM client that supports streaming

    class MockStreamingLLM(MockLLMClient):
        async def stream(self, messages: list[Message]):
            """Simulate streaming response by yielding chunks."""
            response = await self.chat(messages)
            # Split response into chunks
            words = response.content.split()
            for word in words:
                yield Message(role="assistant", content=word + " ")
                await asyncio.sleep(0.05)  # Simulate network delay

    llm = MockStreamingLLM()
    agent = StreamingConversationalAgent(llm_client=llm, max_history=10)

    print("\nUser: Tell me a story")
    print("Assistant: ", end="", flush=True)

    # Stream the response
    async for chunk in agent.stream(Message(role="user", content="Tell me a story")):
        print(chunk.content, end="", flush=True)

    print("\n\n(Response was streamed word-by-word)")
    print(f"History now contains {agent.get_context_length()} messages")


async def main():
    """Run all examples."""
    await basic_conversation_example()
    await history_management_example()
    await context_preservation_example()
    await streaming_example()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. ConversationalAgent maintains context across turns")
    print("2. History is automatically managed and pruned")
    print("3. System prompts can guide agent behavior")
    print("4. History can be exported/imported for persistence")
    print("5. Streaming variant available for real-time responses")
    print("\nNext Steps:")
    print("- Replace MockLLMClient with a real LLM (OpenAI, Anthropic, etc.)")
    print("- Add middleware (retry, timeout, rate limiting)")
    print("- Implement conversation persistence (database, files)")
    print("- Add conversation branching for complex scenarios")


if __name__ == "__main__":
    asyncio.run(main())
