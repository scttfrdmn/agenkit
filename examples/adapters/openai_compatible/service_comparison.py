#!/usr/bin/env python3
"""
Multi-Service Comparison Example

This example demonstrates how to use the same Agenkit code with different
OpenAI-compatible inference services. This makes it easy to:

1. Compare performance across different engines
2. Migrate between services without code changes
3. Use different services for different use cases
4. Test locally before deploying to production

Supported services shown:
- vLLM: High-throughput batch inference
- llama.cpp: Lightweight, CPU-friendly
- SGLang: Optimized for complex prompts
- TensorRT-LLM: NVIDIA GPU optimized

Setup:
    Each service needs to be started separately. See individual setup instructions.

Run:
    uv run python examples/adapters/openai_compatible/service_comparison.py
"""

import asyncio
import time
from dataclasses import dataclass

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message


@dataclass
class ServiceConfig:
    """Configuration for an inference service."""

    name: str
    base_url: str
    model: str
    provider: str
    description: str


# Service configurations
SERVICES = [
    ServiceConfig(
        name="vLLM",
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="vllm",
        description="High-throughput serving, excellent for batch inference",
    ),
    ServiceConfig(
        name="llama.cpp",
        base_url="http://localhost:8080/v1",
        model="llama-2-7b-chat",
        provider="llamacpp",
        description="Lightweight C++ implementation, works on CPU",
    ),
    ServiceConfig(
        name="SGLang",
        base_url="http://localhost:30000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="sglang",
        description="Optimized for complex prompts and structured generation",
    ),
    ServiceConfig(
        name="TensorRT-LLM",
        base_url="http://localhost:8001/v1",
        model="llama-2-7b",
        provider="tensorrt",
        description="NVIDIA-optimized, fastest inference on NVIDIA GPUs",
    ),
]


async def test_service(config: ServiceConfig, messages: list[Message]) -> dict:
    """Test a single service and measure performance."""
    llm = OpenAICompatibleLLM(
        base_url=config.base_url,
        model=config.model,
        provider=config.provider,
        timeout=30.0,
    )

    try:
        # Measure completion time
        start = time.perf_counter()
        response = await llm.complete(messages, temperature=0.7)
        duration = time.perf_counter() - start

        return {
            "success": True,
            "duration": duration,
            "response": response,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "duration": 0.0,
            "response": None,
            "error": str(e),
        }


async def compare_services() -> None:
    """Compare all configured services."""
    print("=" * 80)
    print(" " * 25 + "Service Comparison")
    print("=" * 80)

    # Test prompt
    messages = [
        Message(
            role="user",
            content="Explain what a GPU is in one sentence.",
        )
    ]

    print(f"\n📤 Test prompt: {messages[0].content}")
    print("\n" + "-" * 80)

    results = []

    for config in SERVICES:
        print(f"\n🔧 Testing {config.name}...")
        print(f"   {config.description}")
        print(f"   URL: {config.base_url}")

        result = await test_service(config, messages)
        results.append((config, result))

        if result["success"]:
            response = result["response"]
            print(f"   ✅ Success ({result['duration']:.2f}s)")
            print(f"   📥 Response: {response.content[:80]}...")
            if response.metadata.get("usage"):
                tokens = response.metadata["usage"]["total_tokens"]
                print(f"   📊 Tokens: {tokens}")
        else:
            print(f"   ❌ Failed: {result['error'][:60]}")

    print("\n" + "=" * 80)
    print(" " * 30 + "Summary")
    print("=" * 80)

    # Print summary table
    successful = [r for r in results if r[1]["success"]]

    if successful:
        print("\n✅ Successful services:")
        print(f"{'Service':<20} {'Duration':<12} {'Tokens':<10}")
        print("-" * 42)

        for config, result in successful:
            tokens = result["response"].metadata.get("usage", {}).get("total_tokens", "N/A")
            print(f"{config.name:<20} {result['duration']:.2f}s{'':<6} {tokens}")

        # Find fastest
        fastest = min(successful, key=lambda x: x[1]["duration"])
        print(f"\n🏆 Fastest: {fastest[0].name} ({fastest[1]['duration']:.2f}s)")

    failed = [r for r in results if not r[1]["success"]]
    if failed:
        print(f"\n❌ Failed services ({len(failed)}):")
        for config, result in failed:
            print(f"  • {config.name}: {result['error'][:60]}")


async def swappable_code_example() -> None:
    """Demonstrate code that works with any service."""
    print("\n\n" + "=" * 80)
    print(" " * 25 + "Swappable Code Example")
    print("=" * 80)

    print("\n💡 The same code works with ANY OpenAI-compatible service!")
    print("\nExample function that works with all services:")

    print("""
    async def ask_question(base_url: str, model: str, question: str) -> str:
        '''Ask a question using any OpenAI-compatible service.'''
        llm = OpenAICompatibleLLM(
            base_url=base_url,
            model=model,
            provider='auto'  # Auto-detect provider
        )

        messages = [Message(role='user', content=question)]
        response = await llm.complete(messages)
        return response.content
    """)

    print("\nThis function works with:")
    print("  • vLLM: ask_question('http://localhost:8000/v1', 'llama-2-7b', q)")
    print("  • llama.cpp: ask_question('http://localhost:8080/v1', 'llama-2-7b', q)")
    print("  • SGLang: ask_question('http://localhost:30000/v1', 'llama-2-7b', q)")
    print("  • Any other OpenAI-compatible service!")


async def migration_example() -> None:
    """Show how to migrate from OpenAI to self-hosted."""
    print("\n\n" + "=" * 80)
    print(" " * 22 + "Migration from OpenAI Example")
    print("=" * 80)

    print("\n🔄 Migrating from OpenAI to self-hosted is simple:")

    print("\nBefore (OpenAI):")
    print("""
    from agenkit.adapters.llm import OpenAILLM

    llm = OpenAILLM(
        api_key="sk-...",
        model="gpt-4"
    )
    """)

    print("\nAfter (vLLM self-hosted):")
    print("""
    from agenkit.adapters.llm import OpenAICompatibleLLM

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-2-7b-chat-hf",
        provider="vllm"
    )
    """)

    print("\n✨ The rest of your code stays exactly the same!")
    print("   • Same methods: complete(), stream(), unwrap()")
    print("   • Same message format: Message(role='user', content=...)")
    print("   • Same metadata structure")


async def setup_instructions() -> None:
    """Print setup instructions for each service."""
    print("\n\n" + "=" * 80)
    print(" " * 27 + "Setup Instructions")
    print("=" * 80)

    print("\n📋 How to start each service:")

    print("\n1️⃣  vLLM:")
    print("   docker run --gpus all -p 8000:8000 vllm/vllm-openai \\")
    print("       --model meta-llama/Llama-2-7b-chat-hf")

    print("\n2️⃣  llama.cpp:")
    print("   ./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080")
    print("   (Download from: https://github.com/ggerganov/llama.cpp)")

    print("\n3️⃣  SGLang:")
    print("   python -m sglang.launch_server \\")
    print("       --model-path meta-llama/Llama-2-7b-chat-hf \\")
    print("       --port 30000")

    print("\n4️⃣  TensorRT-LLM:")
    print(
        "   docker run --gpus all -p 8001:8001 nvcr.io/nvidia/tritonserver:23.10-trtllm-python-py3 \\"
    )
    print("       tritonserver --model-repository=/models")

    print("\n📚 For detailed setup, see:")
    print("   examples/adapters/openai_compatible/production_setup.py")


async def main() -> None:
    """Run all comparison examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "OpenAI-Compatible Service Comparison" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")

    # Run examples
    await compare_services()
    await swappable_code_example()
    await migration_example()
    await setup_instructions()

    print("\n\n" + "=" * 80)
    print("✅ Comparison complete!")
    print("=" * 80)

    print("\n💡 Key takeaways:")
    print("  • Same code works with all OpenAI-compatible services")
    print("  • Easy to switch services based on your needs")
    print("  • No vendor lock-in - migrate anytime")
    print("  • Compare performance to find the best fit")

    print("\n📖 Next steps:")
    print("  • Try vllm_example.py for detailed vLLM usage")
    print("  • See production_setup.py for deployment examples")
    print("  • Read ARCHITECTURE.md for design principles")


if __name__ == "__main__":
    asyncio.run(main())
