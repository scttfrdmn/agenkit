#!/usr/bin/env python3
"""
llama.cpp Integration Example

This example demonstrates how to use Agenkit with llama.cpp, a lightweight
C++ implementation optimized for local and edge deployment. Perfect for
CPU-only environments and resource-constrained scenarios.

Setup:
    1. Install llama.cpp:
       git clone https://github.com/ggerganov/llama.cpp
       cd llama.cpp
       make server

    2. Download a model (GGUF format):
       # Example: Llama 3.3 8B Instruct (Q4_K_M quantization)
       wget https://huggingface.co/TheBloke/Llama-3.3-8B-Instruct-GGUF/resolve/main/llama-3.3-8b-instruct.Q4_K_M.gguf \
           -P models/

    3. Start llama.cpp server:
       ./server -m models/llama-3.3-8b-instruct.Q4_K_M.gguf \
           --port 8080 \
           --host 0.0.0.0 \
           --n-gpu-layers 0  # CPU-only; increase for GPU

    4. Run this example:
       uv run python examples/adapters/openai_compatible/llamacpp_example.py

Requirements:
    - CPU (GPU optional but recommended)
    - ~4-8GB RAM for Q4 quantized 7-8B models
    - Works on Mac, Linux, Windows

Learn more:
    - llama.cpp: https://github.com/ggerganov/llama.cpp
    - Server docs: https://github.com/ggerganov/llama.cpp/tree/master/examples/server
    - Model quantization: https://github.com/ggerganov/llama.cpp#quantization
"""

import asyncio
import time

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message


async def basic_completion() -> None:
    """Basic completion example with llama.cpp."""
    print("=" * 60)
    print("Basic Completion Example - CPU Inference")
    print("=" * 60)

    # Connect to local llama.cpp server
    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8080/v1",
        model="llama-3.3-8b-instruct",
        provider="llamacpp",
    )

    messages = [Message(role="user", content="What are the benefits of edge AI?")]

    print("\n📤 Sending: What are the benefits of edge AI?")
    start_time = time.time()
    response = await llm.complete(messages)
    elapsed = time.time() - start_time

    print(f"\n📥 Response: {response.content}")
    print("\n📊 Metadata:")
    print(f"  • Model: {response.metadata['model']}")
    print(f"  • Provider: {response.metadata['provider']}")
    print(f"  • Tokens: {response.metadata['usage']['total_tokens']}")
    print(f"  • Time: {elapsed:.2f}s")
    print(f"  • Tokens/sec: {response.metadata['usage']['completion_tokens'] / elapsed:.2f}")


async def quantization_comparison() -> None:
    """Demonstrate different quantization levels."""
    print("\n\n" + "=" * 60)
    print("Quantization Impact Example")
    print("=" * 60)
    print("\nNote: This example assumes you have multiple quantized models.")
    print("Quantization trades quality for speed and memory efficiency.")

    # Simulate comparison (in practice, you'd load different models)
    quantization_info = {
        "Q2_K": {"size": "2.5GB", "quality": "Low", "speed": "Very Fast"},
        "Q4_K_M": {"size": "4.1GB", "quality": "Good", "speed": "Fast"},
        "Q5_K_M": {"size": "5.0GB", "quality": "Very Good", "speed": "Medium"},
        "Q8_0": {"size": "7.2GB", "quality": "Excellent", "speed": "Slower"},
    }

    print("\n📊 Quantization Options:")
    print("-" * 60)
    for quant, info in quantization_info.items():
        print(f"  {quant:8} | Size: {info['size']:6} | Quality: {info['quality']:12} | Speed: {info['speed']}")

    print("\nRecommendation:")
    print("  • Edge devices: Q2_K or Q4_K_M")
    print("  • Development: Q4_K_M or Q5_K_M")
    print("  • Production: Q5_K_M or Q8_0")


async def local_code_generation() -> None:
    """Code generation example optimized for local inference."""
    print("\n\n" + "=" * 60)
    print("Local Code Generation Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8080/v1",
        model="llama-3.3-8b-instruct",
        provider="llamacpp",
    )

    messages = [
        Message(
            role="system",
            content="You are a code assistant. Provide concise, working code examples.",
        ),
        Message(
            role="user",
            content="Write a Python function to read a CSV file and calculate the average of a column.",
        ),
    ]

    print("\n📤 Requesting code generation...")
    response = await llm.complete(messages, temperature=0.2, max_tokens=300)

    print(f"\n📥 Generated code:\n{response.content}")
    print(f"\n📊 Tokens used: {response.metadata['usage']['total_tokens']}")


async def edge_chatbot() -> None:
    """Simple chatbot for edge deployment."""
    print("\n\n" + "=" * 60)
    print("Edge Chatbot Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8080/v1",
        model="llama-3.3-8b-instruct",
        provider="llamacpp",
    )

    conversation = [
        Message(
            role="system",
            content="You are a helpful assistant running on local hardware. Keep responses concise.",
        ),
    ]

    # Simulate a conversation
    user_messages = [
        "What is edge computing?",
        "What are its main advantages?",
        "Thank you!",
    ]

    for user_msg in user_messages:
        print(f"\n👤 User: {user_msg}")
        conversation.append(Message(role="user", content=user_msg))

        response = await llm.complete(conversation, temperature=0.7, max_tokens=150)
        print(f"🤖 Assistant: {response.content}")

        conversation.append(response)


async def performance_tuning() -> None:
    """Demonstrate performance tuning options."""
    print("\n\n" + "=" * 60)
    print("Performance Tuning Example")
    print("=" * 60)

    print("\n⚙️  llama.cpp Server Configuration Options:")
    print("-" * 60)
    print("  --threads N         : CPU threads to use (default: all)")
    print("  --n-gpu-layers N    : GPU offload layers (0=CPU only)")
    print("  --ctx-size N        : Context window size (default: 2048)")
    print("  --batch-size N      : Batch size for prompt processing")
    print("  --mlock             : Lock model in RAM (prevent swapping)")

    print("\n📊 Recommended Settings by Use Case:")
    print("-" * 60)
    print("  Edge Device (CPU only):")
    print("    ./server -m model.gguf --threads 4 --ctx-size 2048")
    print("\n  Development (Mac M1/M2):")
    print("    ./server -m model.gguf --n-gpu-layers 35 --ctx-size 4096")
    print("\n  Production (Linux + GPU):")
    print("    ./server -m model.gguf --n-gpu-layers 40 --ctx-size 8192 --mlock")

    # Test with different parameters
    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8080/v1",
        model="llama-3.3-8b-instruct",
        provider="llamacpp",
        timeout=30.0,
    )

    messages = [Message(role="user", content="Quick test message")]

    print("\n🧪 Testing current configuration...")
    start = time.time()
    response = await llm.complete(messages, max_tokens=50)
    elapsed = time.time() - start

    print(f"✅ Response time: {elapsed:.2f}s")
    print(f"   Tokens/sec: {response.metadata['usage']['completion_tokens'] / elapsed:.2f}")


async def offline_deployment() -> None:
    """Example configuration for offline/air-gapped deployment."""
    print("\n\n" + "=" * 60)
    print("Offline Deployment Example")
    print("=" * 60)

    print("\n🔒 Offline Deployment Checklist:")
    print("-" * 60)
    print("  ✓ Download model files (.gguf format)")
    print("  ✓ Build llama.cpp binary: make server")
    print("  ✓ No internet connection required after setup")
    print("  ✓ All inference runs locally")
    print("  ✓ Perfect for secure/regulated environments")

    print("\n📦 Model Files to Download:")
    print("  • Model weights: llama-3.3-8b-instruct.Q4_K_M.gguf (~4.1GB)")
    print("  • Config (if needed): config.json")

    print("\n🚀 Deployment Steps:")
    print("  1. Copy llama.cpp binary and model to target")
    print("  2. Start server: ./server -m model.gguf --port 8080")
    print("  3. Deploy your application with Agenkit")
    print("  4. All runs without internet!")

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8080/v1",
        model="llama-3.3-8b-instruct",
        provider="llamacpp",
    )

    messages = [Message(role="user", content="Confirm offline operation works.")]

    print("\n🧪 Testing offline operation...")
    response = await llm.complete(messages)
    print(f"✅ Offline inference successful!")
    print(f"   Response preview: {response.content[:80]}...")


async def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "llama.cpp Integration Examples" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # Run examples
        await basic_completion()
        await quantization_comparison()
        await local_code_generation()
        await edge_chatbot()
        await performance_tuning()
        await offline_deployment()

        print("\n\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        print("\n🎯 Key Takeaways:")
        print("  • llama.cpp is perfect for CPU-only and edge deployments")
        print("  • Quantization enables running large models on small devices")
        print("  • No internet required - ideal for secure environments")
        print("  • Runs on Mac, Linux, Windows without dependencies")
        print("\nNext steps:")
        print("  • Try different quantization levels for your use case")
        print("  • Tune threads and GPU layers for optimal performance")
        print("  • See production_setup.py for deployment examples")

    except Exception as e:
        print(f"\n\n❌ Error running examples: {e}")
        print("\nTroubleshooting:")
        print("  1. Is llama.cpp server running? Check: curl http://localhost:8080/health")
        print("  2. Build server: cd llama.cpp && make server")
        print("  3. Start server: ./server -m models/model.gguf --port 8080")
        print("  4. Download model from HuggingFace (GGUF format)")
        raise


if __name__ == "__main__":
    asyncio.run(main())
