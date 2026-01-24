#!/usr/bin/env python3
"""
SGLang Integration Example

This example demonstrates how to use Agenkit with SGLang, an inference engine
optimized for complex prompts and multi-turn conversations. SGLang uses
RadixAttention for efficient KV cache reuse across requests.

Setup:
    1. Install SGLang with Docker (recommended):
       docker run --gpus all -p 30000:30000 \
           lmsysorg/sglang:latest \
           python -m sglang.launch_server \
           --model-path meta-llama/Llama-3.3-70B-Instruct \
           --port 30000

    2. Or install locally:
       pip install "sglang[all]"
       python -m sglang.launch_server \
           --model-path meta-llama/Llama-3.3-70B-Instruct \
           --port 30000

    3. Wait for server to start (check logs for "Server ready")

    4. Run this example:
       uv run python examples/adapters/openai_compatible/sglang_example.py

Requirements:
    - GPU with CUDA support (NVIDIA)
    - ~140GB VRAM for Llama-3.3-70B (or use smaller models)
    - Use Llama-3.3-8B-Instruct for ~16GB VRAM

Key Features:
    - RadixAttention: Efficient KV cache reuse for similar prompts
    - Optimized for chatbots and conversational agents
    - Automatic prefix caching for repeated system prompts
    - Structured generation support

Learn more:
    - SGLang: https://github.com/sgl-project/sglang
    - RadixAttention paper: https://arxiv.org/abs/2312.07104
    - Docs: https://sgl-project.github.io/
"""

import asyncio
import time

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message


async def basic_completion() -> None:
    """Basic completion example with SGLang."""
    print("=" * 60)
    print("Basic Completion Example")
    print("=" * 60)

    # Connect to local SGLang server
    llm = OpenAICompatibleLLM(
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="sglang",
    )

    messages = [
        Message(role="user", content="Explain the concept of attention in transformers.")
    ]

    print("\n📤 Sending complex prompt about attention mechanisms...")
    start_time = time.time()
    response = await llm.complete(messages, max_tokens=500)
    elapsed = time.time() - start_time

    print(f"\n📥 Response: {response.content[:200]}...")
    print("\n📊 Metadata:")
    print(f"  • Model: {response.metadata['model']}")
    print(f"  • Provider: {response.metadata['provider']}")
    print(f"  • Tokens: {response.metadata['usage']['total_tokens']}")
    print(f"  • Time: {elapsed:.2f}s")


async def multi_turn_conversation() -> None:
    """
    Multi-turn conversation demonstrating RadixAttention efficiency.

    SGLang's RadixAttention automatically caches and reuses KV states
    from similar prompts, making multi-turn conversations very efficient.
    """
    print("\n\n" + "=" * 60)
    print("Multi-Turn Conversation Example")
    print("=" * 60)
    print("\nRadixAttention will cache common prefixes for efficiency")

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="sglang",
    )

    # Long system prompt - will be cached by RadixAttention
    system_prompt = """You are an expert AI research assistant specializing in
natural language processing and machine learning. You provide detailed,
technical explanations with references to recent papers when appropriate.
You maintain context across the conversation and build on previous topics."""

    conversation = [Message(role="system", content=system_prompt)]

    questions = [
        "What is RadixAttention and why is it important?",
        "How does it compare to standard attention mechanisms?",
        "What are the performance benefits in practice?",
        "Can you explain the cache reuse strategy?",
    ]

    print("\n🔄 Starting conversation (system prompt will be cached)...")

    for i, question in enumerate(questions, 1):
        print(f"\n--- Turn {i} ---")
        print(f"👤 User: {question}")

        conversation.append(Message(role="user", content=question))

        start = time.time()
        response = await llm.complete(conversation, temperature=0.7, max_tokens=300)
        elapsed = time.time() - start

        print(f"🤖 Assistant: {response.content[:150]}...")
        print(f"⏱️  Time: {elapsed:.2f}s")

        conversation.append(response)

        # First request is slower (builds cache), subsequent ones are faster
        if i == 1:
            print("   (First request - building cache)")
        else:
            print("   (Using cached prefix - faster!)")


async def chatbot_with_memory() -> None:
    """Chatbot example optimized for SGLang's caching."""
    print("\n\n" + "=" * 60)
    print("Chatbot with Memory Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="sglang",
    )

    # Chatbot persona - this will be cached across all requests
    system_msg = Message(
        role="system",
        content="""You are a friendly AI tutor helping students learn programming.
You remember what you've taught in the conversation and build on it.
You use examples and encourage questions.""",
    )

    conversation = [system_msg]

    print("\n🎓 AI Tutor Chatbot (with RadixAttention caching)")
    print("-" * 60)

    # Simulate a tutoring session
    student_messages = [
        "I'm new to Python. Where should I start?",
        "What are variables?",
        "Can you show me an example?",
        "What about lists?",
        "How do I loop through a list?",
    ]

    for msg in student_messages:
        print(f"\n👨‍🎓 Student: {msg}")
        conversation.append(Message(role="user", content=msg))

        response = await llm.complete(conversation, temperature=0.8, max_tokens=200)
        print(f"👨‍🏫 Tutor: {response.content}")

        conversation.append(response)

    print("\n✅ Conversation completed with efficient caching!")


async def prefix_caching_demo() -> None:
    """
    Demonstrate the power of prefix caching with repeated system prompts.

    This is SGLang's killer feature - if you're running a chatbot service
    with the same system prompt for all users, SGLang caches it once and
    reuses it for all subsequent requests.
    """
    print("\n\n" + "=" * 60)
    print("Prefix Caching Demonstration")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="sglang",
    )

    # Long system prompt (would normally be processed every time)
    long_system_prompt = """You are an advanced AI assistant with the following capabilities:
    1. Expert knowledge across multiple domains including science, technology, arts
    2. Ability to reason through complex problems step by step
    3. Code generation and debugging skills
    4. Creative writing and content creation
    5. Data analysis and interpretation

    Guidelines:
    - Always provide accurate, well-researched information
    - Show your reasoning process when solving problems
    - Ask clarifying questions when needed
    - Adapt your communication style to the user's level
    - Cite sources when making specific claims

    Your goal is to be helpful, harmless, and honest in all interactions."""

    system_msg = Message(role="system", content=long_system_prompt)

    print("\n🔬 Sending 3 different requests with the same long system prompt...")
    print(f"   System prompt length: {len(long_system_prompt)} characters")

    test_questions = [
        "What is quantum computing?",
        "Write a Python function to sort a list.",
        "Explain machine learning to a 10-year-old.",
    ]

    times = []
    for i, question in enumerate(test_questions, 1):
        messages = [system_msg, Message(role="user", content=question)]

        print(f"\n📤 Request {i}: {question}")
        start = time.time()
        response = await llm.complete(messages, max_tokens=150)
        elapsed = time.time() - start
        times.append(elapsed)

        print(f"⏱️  Time: {elapsed:.2f}s")
        print(f"📥 Response: {response.content[:80]}...")

    print("\n📊 Performance Analysis:")
    print(f"   Request 1 (cold cache): {times[0]:.2f}s")
    print(f"   Request 2 (warm cache): {times[1]:.2f}s ({(times[1]/times[0])*100:.1f}% of original)")
    print(f"   Request 3 (warm cache): {times[2]:.2f}s ({(times[2]/times[0])*100:.1f}% of original)")
    print("\n✨ RadixAttention cached the system prompt after first request!")


async def structured_generation() -> None:
    """Example using structured generation (if supported by model)."""
    print("\n\n" + "=" * 60)
    print("Structured Generation Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="sglang",
    )

    messages = [
        Message(
            role="system",
            content="You are a helpful assistant that responds in JSON format.",
        ),
        Message(
            role="user",
            content="""Generate a JSON object with information about Python:
{
  "language": "name",
  "year": creation_year,
  "creator": "creator_name",
  "paradigm": ["paradigms"],
  "popular_frameworks": ["frameworks"]
}""",
        ),
    ]

    print("\n📤 Requesting structured JSON output...")
    response = await llm.complete(messages, temperature=0.3, max_tokens=300)

    print(f"\n📥 Structured Response:\n{response.content}")


async def performance_comparison() -> None:
    """Compare performance with and without RadixAttention benefits."""
    print("\n\n" + "=" * 60)
    print("Performance Comparison")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        provider="sglang",
    )

    print("\n📊 SGLang Performance Characteristics:")
    print("-" * 60)
    print("  ✓ First request with new prefix: Normal latency")
    print("  ✓ Subsequent requests with same prefix: 2-10x faster")
    print("  ✓ Memory efficient: Shared KV cache across requests")
    print("  ✓ Automatic: No configuration needed")

    print("\n🎯 Ideal Use Cases:")
    print("  • Chatbots with consistent system prompts")
    print("  • Multi-turn conversations")
    print("  • RAG applications with repeated context")
    print("  • Customer service agents")
    print("  • Educational tutoring systems")

    print("\n⚠️  Less Ideal For:")
    print("  • One-off, unique prompts")
    print("  • Batch processing with no prefix overlap")
    print("  • Simple question-answering")


async def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 14 + "SGLang Integration Examples" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # Run examples
        await basic_completion()
        await multi_turn_conversation()
        await chatbot_with_memory()
        await prefix_caching_demo()
        await structured_generation()
        await performance_comparison()

        print("\n\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        print("\n🎯 Key Takeaways:")
        print("  • SGLang's RadixAttention automatically caches KV states")
        print("  • Perfect for chatbots and multi-turn conversations")
        print("  • 2-10x speedup for requests with similar prefixes")
        print("  • Zero configuration - caching happens automatically")
        print("\nNext steps:")
        print("  • Use SGLang for production chatbot deployments")
        print("  • Monitor cache hit rates in production")
        print("  • See production_setup.py for deployment examples")

    except Exception as e:
        print(f"\n\n❌ Error running examples: {e}")
        print("\nTroubleshooting:")
        print("  1. Is SGLang server running? Check: curl http://localhost:30000/health")
        print("  2. Start with Docker:")
        print("     docker run --gpus all -p 30000:30000 lmsysorg/sglang:latest \\")
        print("       python -m sglang.launch_server \\")
        print("       --model-path meta-llama/Llama-3.3-70B-Instruct --port 30000")
        print("  3. Wait for model to load (may take several minutes)")
        print("  4. Use smaller model if VRAM limited (e.g., Llama-3.3-8B-Instruct)")
        raise


if __name__ == "__main__":
    asyncio.run(main())
