"""
Real-time streaming examples.

Shows:
- Stream tokens as they generate
- Progress indicators
- Handling streaming errors
- Different streaming patterns
"""

import asyncio
import os
import sys
import time

from agenkit.adapters.llm import AnthropicLLM, OpenAILLM
from agenkit.interfaces import Message


async def basic_streaming():
    """Basic streaming example."""
    print("=" * 60)
    print("Basic Streaming")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")

    messages = [
        Message(role="user", content="Write a short story about an AI agent (max 100 words).")
    ]

    print("Streaming response:\n")
    print("-" * 60)

    async for chunk in llm.stream(messages, max_tokens=200):
        print(chunk.content, end="", flush=True)

    print("\n" + "-" * 60)
    print()


async def streaming_with_progress():
    """Streaming with character count progress."""
    print("=" * 60)
    print("Streaming with Progress")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    messages = [
        Message(role="user", content="Explain neural networks in 100 words.")
    ]

    print("Streaming response (with character count):\n")
    print("-" * 60)

    char_count = 0
    start_time = time.time()

    async for chunk in llm.stream(messages, max_tokens=200):
        print(chunk.content, end="", flush=True)
        char_count += len(chunk.content)

    elapsed = time.time() - start_time

    print("\n" + "-" * 60)
    print(f"Characters: {char_count} | Time: {elapsed:.2f}s | Rate: {char_count/elapsed:.0f} chars/sec")
    print()


async def streaming_with_callback():
    """Streaming with custom callback for each chunk."""
    print("=" * 60)
    print("Streaming with Custom Callback")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    llm = AnthropicLLM(api_key=api_key)

    messages = [
        Message(role="user", content="List 5 benefits of using agents.")
    ]

    print("Processing stream with custom callback:\n")

    chunks = []
    chunk_count = 0

    async for chunk in llm.stream(messages, max_tokens=200):
        chunk_count += 1
        chunks.append(chunk.content)

        # Custom processing: print every 10th chunk
        if chunk_count % 10 == 0:
            sys.stdout.write(f"[{chunk_count}]")
            sys.stdout.flush()

        # Also print the content
        print(chunk.content, end="", flush=True)

    print(f"\n\nReceived {chunk_count} chunks")
    print(f"Full response: {len(''.join(chunks))} characters\n")


async def error_handling():
    """Handle streaming errors gracefully."""
    print("=" * 60)
    print("Error Handling in Streaming")
    print("=" * 60)

    # Invalid API key
    llm = AnthropicLLM(api_key="invalid-key")
    messages = [Message(role="user", content="Hello!")]

    try:
        print("Attempting to stream with invalid key...")
        async for chunk in llm.stream(messages):
            print(chunk.content, end="", flush=True)
    except Exception as e:
        print(f"\n✅ Caught error (expected): {type(e).__name__}")
        print(f"   Message: {str(e)[:100]}...\n")


async def multiple_providers():
    """Compare streaming speed across providers."""
    print("=" * 60)
    print("Provider Streaming Comparison")
    print("=" * 60)

    messages = [
        Message(role="user", content="Count from 1 to 20.")
    ]

    # Test Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("Anthropic Claude (streaming):")
        llm = AnthropicLLM(api_key=anthropic_key, model="claude-3-haiku-20240307")

        start = time.time()
        chunk_count = 0

        async for chunk in llm.stream(messages, max_tokens=100):
            print(chunk.content, end="", flush=True)
            chunk_count += 1

        elapsed = time.time() - start
        print(f"\n  Time: {elapsed:.2f}s | Chunks: {chunk_count}\n")

    # Test OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("OpenAI GPT (streaming):")
        llm = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")

        start = time.time()
        chunk_count = 0

        async for chunk in llm.stream(messages, max_tokens=100):
            print(chunk.content, end="", flush=True)
            chunk_count += 1

        elapsed = time.time() - start
        print(f"\n  Time: {elapsed:.2f}s | Chunks: {chunk_count}\n")


async def streaming_conversation():
    """Multi-turn conversation with streaming."""
    print("=" * 60)
    print("Streaming Conversation")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")

    # Conversation history
    conversation = [
        Message(role="system", content="You are a helpful AI assistant. Keep responses brief."),
    ]

    questions = [
        "What is an agent?",
        "Can you give an example?",
        "How do I build one?",
    ]

    for question in questions:
        print(f"User: {question}")
        print(f"Assistant: ", end="", flush=True)

        # Add user message
        conversation.append(Message(role="user", content=question))

        # Stream response
        response_content = ""
        async for chunk in llm.stream(conversation, max_tokens=100):
            print(chunk.content, end="", flush=True)
            response_content += chunk.content

        print("\n")

        # Add assistant response to history
        conversation.append(Message(role="agent", content=response_content))

    print()


async def main():
    """Run all examples."""
    print("\n🌊 Streaming Examples\n")

    await basic_streaming()
    await streaming_with_progress()
    await streaming_with_callback()
    await multiple_providers()
    await streaming_conversation()
    await error_handling()

    print("✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
