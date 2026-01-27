"""
Basic Google Gemini LLM usage.

Shows:
- Simple completion
- Streaming responses
- Using options (temperature, max_tokens, top_p, top_k)
- Accessing usage metadata
"""

import asyncio
import os

from agenkit.adapters.llm import GeminiLLM
from agenkit.interfaces import Message


async def basic_completion():
    """Basic completion with Google Gemini."""
    print("=" * 60)
    print("Basic Completion")
    print("=" * 60)

    # Initialize the LLM
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY or GEMINI_API_KEY not set")
        return

    llm = GeminiLLM(
        api_key=api_key,
        model="gemini-2.0-flash-exp",  # Fast Gemini model
    )

    # Create a message
    messages = [Message(role="user", content="Explain Agenkit in one sentence.")]

    # Get a response
    response = await llm.complete(messages, temperature=0.7, max_tokens=100)

    print(f"Response: {response.content}\n")

    # Access metadata
    print("Metadata:")
    print(f"  Model: {response.metadata.get('model')}")
    if "usage" in response.metadata:
        usage = response.metadata["usage"]
        print(f"  Prompt tokens: {usage.get('prompt_tokens')}")
        print(f"  Completion tokens: {usage.get('completion_tokens')}")
        print(f"  Total tokens: {usage.get('total_tokens')}")
    print()


async def streaming_example():
    """Stream tokens as they're generated."""
    print("=" * 60)
    print("Streaming Response")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY or GEMINI_API_KEY not set")
        return

    llm = GeminiLLM(api_key=api_key, model="gemini-2.0-flash-exp")

    messages = [Message(role="user", content="Count from 1 to 10, one number per line.")]

    print("Streaming: ", end="", flush=True)
    full_response = ""

    try:
        async for chunk in llm.stream(messages, max_tokens=100):
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        return

    print("\n")
    print(f"Full response length: {len(full_response)} characters\n")


async def with_options():
    """Use Gemini-specific options."""
    print("=" * 60)
    print("With Options (temperature, top_p, top_k)")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY or GEMINI_API_KEY not set")
        return

    llm = GeminiLLM(api_key=api_key, model="gemini-2.0-flash-exp")

    messages = [
        Message(role="system", content="You are a creative writer."),
        Message(role="user", content="Write a haiku about AI agents."),
    ]

    # Use Gemini-specific options
    response = await llm.complete(
        messages,
        temperature=1.2,  # Higher temperature for creativity
        max_tokens=150,
        top_p=0.95,  # Nucleus sampling
        top_k=40,  # Top-k sampling
    )

    print(f"Response:\n{response.content}\n")


async def conversation_example():
    """Multi-turn conversation."""
    print("=" * 60)
    print("Multi-turn Conversation")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY or GEMINI_API_KEY not set")
        return

    llm = GeminiLLM(api_key=api_key, model="gemini-2.0-flash-exp")

    # Build conversation history
    messages = [
        Message(role="user", content="What is the capital of France?"),
        Message(role="agent", content="The capital of France is Paris."),
        Message(role="user", content="What's the population of that city?"),
    ]

    response = await llm.complete(messages, temperature=0.3)

    print("User: What's the population of that city?")
    print(f"Gemini: {response.content}\n")


async def main():
    """Run all examples."""
    try:
        await basic_completion()
        await streaming_example()
        await with_options()
        await conversation_example()

        print("=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
