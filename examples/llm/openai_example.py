"""
Basic OpenAI LLM usage.

Shows:
- GPT-4 completions
- Streaming responses
- Error handling
- Token usage tracking
"""

import asyncio
import os

from agenkit.adapters.llm import OpenAILLM
from agenkit.interfaces import Message


async def basic_completion():
    """Basic completion with OpenAI GPT."""
    print("=" * 60)
    print("Basic Completion")
    print("=" * 60)

    # Initialize the LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(
        api_key=api_key,
        model="gpt-4o-mini",  # Fast and cost-effective
    )

    # Create a message
    messages = [
        Message(role="user", content="What is Agenkit and why would I use it?")
    ]

    # Get a response
    response = await llm.complete(messages, temperature=0.7, max_tokens=150)

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

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    messages = [
        Message(role="user", content="Write a haiku about AI agents.")
    ]

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


async def conversation_example():
    """Multi-turn conversation."""
    print("=" * 60)
    print("Multi-turn Conversation")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Build conversation history
    messages = [
        Message(role="system", content="You are a helpful assistant that explains technical concepts concisely."),
        Message(role="user", content="What is an agent?"),
    ]

    # First response
    response1 = await llm.complete(messages, max_tokens=100)
    print(f"Assistant: {response1.content}\n")
    messages.append(response1)

    # Follow-up question
    messages.append(Message(role="user", content="Can you give an example?"))

    response2 = await llm.complete(messages, max_tokens=100)
    print(f"Assistant: {response2.content}\n")


async def cost_tracking():
    """Track token usage for cost estimation."""
    print("=" * 60)
    print("Token Usage Tracking")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    messages = [
        Message(role="user", content="Explain machine learning in 50 words.")
    ]

    response = await llm.complete(messages, max_tokens=100)

    # Calculate approximate cost (GPT-4o-mini pricing as of Jan 2025)
    if "usage" in response.metadata:
        usage = response.metadata["usage"]
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # GPT-4o-mini: $0.15/1M input, $0.60/1M output
        input_cost = (prompt_tokens / 1_000_000) * 0.15
        output_cost = (completion_tokens / 1_000_000) * 0.60
        total_cost = input_cost + output_cost

        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Estimated cost: ${total_cost:.6f}")
        print()


async def error_handling():
    """Demonstrate proper error handling."""
    print("=" * 60)
    print("Error Handling")
    print("=" * 60)

    # Test with invalid API key
    llm = OpenAILLM(api_key="sk-invalid-key-123")
    messages = [Message(role="user", content="Hello!")]

    try:
        response = await llm.complete(messages)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"✅ Caught error (expected): {type(e).__name__}")
        print(f"   Message: {str(e)[:100]}...")
        print()


async def main():
    """Run all examples."""
    print("\n🤖 OpenAI LLM Examples\n")

    await basic_completion()
    await streaming_example()
    await conversation_example()
    await cost_tracking()
    await error_handling()

    print("✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
