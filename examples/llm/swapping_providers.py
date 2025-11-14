"""
Provider swapping demonstration.

Shows:
- Switch between providers with one line
- Compare responses from different models
- Fallback pattern
- A/B testing
"""

import asyncio
import os
from typing import Any

from agenkit.adapters.llm import AnthropicLLM, LLM, OpenAILLM
from agenkit.interfaces import Message

try:
    from agenkit.adapters.llm import GeminiLLM
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


async def basic_swapping():
    """Demonstrate basic provider swapping."""
    print("=" * 60)
    print("Basic Provider Swapping")
    print("=" * 60)

    # Same messages for all providers
    messages = [
        Message(role="user", content="What is the capital of France?")
    ]

    # Try Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("Anthropic Claude:")
        llm = AnthropicLLM(api_key=anthropic_key, model="claude-3-haiku-20240307")
        response = await llm.complete(messages, max_tokens=50)
        print(f"  {response.content}\n")

    # Switch to OpenAI (same interface!)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("OpenAI GPT:")
        llm = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")
        response = await llm.complete(messages, max_tokens=50)
        print(f"  {response.content}\n")

    # Switch to Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and GEMINI_AVAILABLE:
        print("Google Gemini:")
        llm = GeminiLLM(api_key=gemini_key)
        response = await llm.complete(messages, max_tokens=50)
        print(f"  {response.content}\n")


async def compare_responses():
    """Compare responses from multiple providers."""
    print("=" * 60)
    print("Response Comparison")
    print("=" * 60)

    messages = [
        Message(role="user", content="Write a creative tagline for an AI agent framework.")
    ]

    providers: dict[str, LLM] = {}

    # Add available providers
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        providers["Anthropic"] = AnthropicLLM(api_key=anthropic_key)

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        providers["OpenAI"] = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and GEMINI_AVAILABLE:
        providers["Gemini"] = GeminiLLM(api_key=gemini_key)

    # Get responses from all providers
    for name, llm in providers.items():
        try:
            response = await llm.complete(messages, temperature=0.9, max_tokens=50)
            print(f"{name}:")
            print(f"  {response.content}\n")
        except Exception as e:
            print(f"{name}: ❌ {e}\n")


async def fallback_pattern():
    """Try one provider, fall back to another if it fails."""
    print("=" * 60)
    print("Fallback Pattern")
    print("=" * 60)

    messages = [Message(role="user", content="Hello! How are you?")]

    async def complete_with_fallback(
        primary: LLM,
        fallback: LLM,
        messages: list[Message],
        **kwargs: Any,
    ) -> Message:
        """Try primary provider, fall back to secondary if it fails."""
        try:
            print("Trying primary provider...")
            return await primary.complete(messages, **kwargs)
        except Exception as e:
            print(f"Primary failed ({type(e).__name__}), trying fallback...")
            return await fallback.complete(messages, **kwargs)

    # Simulate failure with invalid API key
    primary = AnthropicLLM(api_key="invalid-key")

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY not set")
        return

    fallback = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")

    try:
        response = await complete_with_fallback(primary, fallback, messages, max_tokens=50)
        print(f"✅ Got response: {response.content[:100]}...\n")
    except Exception as e:
        print(f"❌ Both providers failed: {e}\n")


async def ab_testing():
    """A/B test different models on the same prompts."""
    print("=" * 60)
    print("A/B Testing")
    print("=" * 60)

    test_prompts = [
        "Explain quantum computing in 20 words.",
        "What is the meaning of life?",
        "Write a Python function to calculate fibonacci numbers.",
    ]

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key or not openai_key:
        print("❌ Both ANTHROPIC_API_KEY and OPENAI_API_KEY required")
        return

    model_a = AnthropicLLM(api_key=anthropic_key, model="claude-3-haiku-20240307")
    model_b = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")

    for i, prompt in enumerate(test_prompts, 1):
        print(f"Test {i}: {prompt}")
        print()

        messages = [Message(role="user", content=prompt)]

        # Model A
        response_a = await model_a.complete(messages, max_tokens=100)
        print(f"  Model A (Claude Haiku):")
        print(f"    {response_a.content[:100]}...")

        # Model B
        response_b = await model_b.complete(messages, max_tokens=100)
        print(f"  Model B (GPT-4o-mini):")
        print(f"    {response_b.content[:100]}...")
        print()


async def main():
    """Run all examples."""
    print("\n🔄 Provider Swapping Examples\n")

    await basic_swapping()
    await compare_responses()
    await fallback_pattern()
    await ab_testing()

    print("✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
