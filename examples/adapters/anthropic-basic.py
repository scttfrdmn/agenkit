"""
Basic Anthropic LLM usage.

Shows:
- Simple completion
- Streaming responses
- Using options (temperature, max_tokens)
- Accessing usage metadata
"""

import asyncio
import os

from agenkit.adapters.llm import AnthropicLLM
from agenkit.interfaces import Message


async def basic_completion():
    """Basic completion with Anthropic Claude."""
    print("=" * 60)
    print("Basic Completion")
    print("=" * 60)

    # Initialize the LLM
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    llm = AnthropicLLM(
        api_key=api_key,
        model="claude-3-haiku-20240307",  # Fast Claude model
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
        print(f"  Input tokens: {usage.get('input_tokens')}")
        print(f"  Output tokens: {usage.get('output_tokens')}")
    print()


async def streaming_example():
    """Stream tokens as they're generated."""
    print("=" * 60)
    print("Streaming Response")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")

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


async def temperature_comparison():
    """Compare responses with different temperatures."""
    print("=" * 60)
    print("Temperature Comparison")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")

    messages = [
        Message(role="user", content="Write a creative tagline for a framework called Agenkit.")
    ]

    # Low temperature (more focused/deterministic)
    print("Low temperature (0.3):")
    response_low = await llm.complete(messages, temperature=0.3, max_tokens=50)
    print(f"  {response_low.content}\n")

    # High temperature (more creative/random)
    print("High temperature (1.0):")
    response_high = await llm.complete(messages, temperature=1.0, max_tokens=50)
    print(f"  {response_high.content}\n")


async def error_handling():
    """Demonstrate proper error handling."""
    print("=" * 60)
    print("Error Handling")
    print("=" * 60)

    # Test with invalid API key
    llm = AnthropicLLM(api_key="invalid-key-123")
    messages = [Message(role="user", content="Hello!")]

    try:
        response = await llm.complete(messages)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"✅ Caught error (expected): {type(e).__name__}")
        print(f"   Message: {str(e)[:100]}...\n")


async def main():
    """Run all examples."""
    print("\n🤖 Anthropic LLM Examples\n")

    await basic_completion()
    await streaming_example()
    await temperature_comparison()
    await error_handling()

    print("✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
