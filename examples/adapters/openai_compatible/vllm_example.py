#!/usr/bin/env python3
"""
vLLM Integration Example

This example demonstrates how to use Agenkit with vLLM, a high-throughput
inference engine for LLMs. vLLM is optimized for serving many requests
concurrently with low latency.

Setup:
    1. Start vLLM server with Docker:
       docker run --gpus all -p 8000:8000 vllm/vllm-openai \
           --model meta-llama/Llama-2-7b-chat-hf

    2. Or install and run locally:
       pip install vllm
       python -m vllm.entrypoints.openai.api_server \
           --model meta-llama/Llama-2-7b-chat-hf

    3. Wait for server to start (check http://localhost:8000/health)

    4. Run this example:
       uv run python examples/adapters/openai_compatible/vllm_example.py

Requirements:
    - GPU with CUDA support (for vLLM)
    - ~14GB VRAM for Llama-2-7b
    - Or use CPU-only mode (much slower)

Learn more:
    - vLLM docs: https://docs.vllm.ai/
    - OpenAI API compatibility: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
"""

import asyncio

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message


async def basic_completion() -> None:
    """Basic completion example with vLLM."""
    print("=" * 60)
    print("Basic Completion Example")
    print("=" * 60)

    # Connect to local vLLM server
    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="vllm",
    )

    # Simple question
    messages = [Message(role="user", content="What is machine learning in one sentence?")]

    print("\n📤 Sending: What is machine learning in one sentence?")
    response = await llm.complete(messages)

    print(f"\n📥 Response: {response.content}")
    print("\n📊 Metadata:")
    print(f"  • Model: {response.metadata['model']}")
    print(f"  • Provider: {response.metadata['provider']}")
    print(f"  • Tokens: {response.metadata['usage']['total_tokens']}")
    print(f"  • Finish reason: {response.metadata['finish_reason']}")


async def streaming_response() -> None:
    """Streaming completion example with vLLM."""
    print("\n\n" + "=" * 60)
    print("Streaming Response Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="vllm",
    )

    messages = [Message(role="user", content="Count from 1 to 10 slowly.")]

    print("\n📤 Sending: Count from 1 to 10 slowly.")
    print("\n📥 Streaming response:")
    print("-" * 60)

    async for chunk in llm.stream(messages):
        print(chunk.content, end="", flush=True)

    print("\n" + "-" * 60)


async def conversation_example() -> None:
    """Multi-turn conversation example."""
    print("\n\n" + "=" * 60)
    print("Conversation Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="vllm",
    )

    # Build a conversation
    conversation = [
        Message(role="system", content="You are a helpful AI assistant."),
        Message(role="user", content="What is Python?"),
    ]

    print("\n📤 User: What is Python?")
    response1 = await llm.complete(conversation)
    print(f"📥 Assistant: {response1.content[:100]}...")

    # Continue conversation
    conversation.append(response1)
    conversation.append(Message(role="user", content="Can you give me a simple code example?"))

    print("\n📤 User: Can you give me a simple code example?")
    response2 = await llm.complete(conversation)
    print(f"📥 Assistant:\n{response2.content}")


async def custom_parameters() -> None:
    """Example with custom generation parameters."""
    print("\n\n" + "=" * 60)
    print("Custom Parameters Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="vllm",
        timeout=120.0,  # Longer timeout for larger models
    )

    messages = [Message(role="user", content="Write a haiku about coding.")]

    print("\n📤 Sending: Write a haiku about coding.")
    print("⚙️  Parameters: temperature=0.7, max_tokens=100")

    response = await llm.complete(
        messages,
        temperature=0.7,  # More creative
        max_tokens=100,  # Limit response length
    )

    print(f"\n📥 Response:\n{response.content}")


async def error_handling() -> None:
    """Example of error handling."""
    print("\n\n" + "=" * 60)
    print("Error Handling Example")
    print("=" * 60)

    # Try connecting to a non-existent server
    llm = OpenAICompatibleLLM(
        base_url="http://localhost:9999/v1",  # Wrong port
        model="test-model",
        provider="vllm",
    )

    messages = [Message(role="user", content="Hello")]

    print("\n📤 Attempting to connect to non-existent server...")

    try:
        await llm.complete(messages)
    except Exception as e:
        print(f"❌ Error (expected): {type(e).__name__}: {str(e)[:80]}")
        print("✅ Error handling works correctly!")


async def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "vLLM Integration Examples" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # Run examples
        await basic_completion()
        await streaming_response()
        await conversation_example()
        await custom_parameters()
        await error_handling()

        print("\n\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  • Try different models by changing the model parameter")
        print("  • Adjust temperature and max_tokens for different use cases")
        print("  • See production_setup.py for deployment examples")
        print("  • See service_comparison.py for multi-service setup")

    except Exception as e:
        print(f"\n\n❌ Error running examples: {e}")
        print("\nTroubleshooting:")
        print("  1. Is vLLM server running? Check: curl http://localhost:8000/health")
        print("  2. Start server with: docker run --gpus all -p 8000:8000 \\")
        print("       vllm/vllm-openai --model meta-llama/Llama-2-7b-chat-hf")
        print("  3. Wait for model to load (may take a few minutes)")
        raise


if __name__ == "__main__":
    asyncio.run(main())
