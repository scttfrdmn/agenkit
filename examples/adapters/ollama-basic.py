"""
Basic Ollama LLM usage.

Shows:
- Local LLM completions
- Streaming responses
- Multi-turn conversations
- Model configuration

Setup:
1. Install Ollama: https://ollama.ai/download
2. Pull a model: `ollama pull llama2`
3. Verify: `ollama list`
4. Run this example: `python examples/adapters/ollama-basic.py`
"""

import asyncio
import os

from agenkit.adapters.llm import OllamaLLM
from agenkit.interfaces import Message


async def basic_completion():
    """Basic completion with Ollama."""
    print("=" * 60)
    print("Basic Completion (Ollama)")
    print("=" * 60)

    # Initialize the LLM (no API key needed - runs locally!)
    llm = OllamaLLM(
        model="llama2",  # Or: mistral, codellama, phi, gemma
        base_url="http://localhost:11434",  # Default Ollama server
    )

    print(f"Using model: {llm.model}")
    print("Server: http://localhost:11434")
    print()

    # Create a message
    messages = [Message(role="user", content="What is AgentKit and why would I use it?")]

    print("Sending request to local Ollama server...")

    try:
        # Get a response
        response = await llm.complete(messages, temperature=0.7, max_tokens=150)

        print(f"\nResponse: {response.content}\n")

        # Access metadata
        print("Metadata:")
        print(f"  Model: {response.metadata.get('model')}")
        if "total_duration_ns" in response.metadata:
            duration_ms = response.metadata["total_duration_ns"] / 1_000_000
            print(f"  Duration: {duration_ms:.0f}ms")
        if "usage" in response.metadata:
            usage = response.metadata["usage"]
            print(f"  Prompt tokens: {usage.get('prompt_tokens')}")
            print(f"  Completion tokens: {usage.get('completion_tokens')}")
            print(f"  Total tokens: {usage.get('total_tokens')}")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Is Ollama running? (ollama serve)")
        print("  2. Do you have the model? (ollama pull llama2)")
        print("  3. Is the server accessible at http://localhost:11434?")
        return


async def streaming_example():
    """Stream tokens as they're generated."""
    print("=" * 60)
    print("Streaming Response (Ollama)")
    print("=" * 60)

    llm = OllamaLLM(model="llama2")

    messages = [Message(role="user", content="Write a haiku about AI agents.")]

    print("Streaming from local Ollama: ", end="", flush=True)
    full_response = ""

    try:
        async for chunk in llm.stream(messages, max_tokens=100):
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

        print("\n")
        print(f"✓ Streamed {len(full_response)} characters")
        print()

    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        return


async def conversation_example():
    """Multi-turn conversation with Ollama."""
    print("=" * 60)
    print("Multi-turn Conversation (Ollama)")
    print("=" * 60)

    llm = OllamaLLM(model="llama2")

    # Build conversation history
    messages = [
        Message(
            role="system",
            content="You are a helpful assistant that explains technical concepts concisely.",
        ),
        Message(role="user", content="What is an agent pattern?"),
    ]

    print("Turn 1:")
    print(f"User: {messages[1].content}")

    try:
        # First response
        response1 = await llm.complete(messages, temperature=0.7, max_tokens=100)
        print(f"Assistant: {response1.content}\n")

        # Add to history for next turn
        messages.append(response1)
        messages.append(Message(role="user", content="Can you give me an example?"))

        print("Turn 2:")
        print(f"User: {messages[-1].content}")

        # Second response with full context
        response2 = await llm.complete(messages, temperature=0.7, max_tokens=150)
        print(f"Assistant: {response2.content}\n")

        print(f"✓ Conversation with {len(messages)} messages in history")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        return


async def model_comparison():
    """Compare different Ollama models."""
    print("=" * 60)
    print("Model Comparison (Ollama)")
    print("=" * 60)

    prompt = "Explain what an AI agent is in one sentence."
    messages = [Message(role="user", content=prompt)]

    # Try different models (only if they're pulled)
    models = ["llama2", "mistral", "phi"]

    print(f"Prompt: {prompt}\n")

    for model_name in models:
        llm = OllamaLLM(model=model_name)

        print(f"Model: {model_name}")
        print("-" * 40)

        try:
            response = await llm.complete(messages, temperature=0.7, max_tokens=50)
            print(f"Response: {response.content}\n")

        except Exception as e:
            print(f"❌ {model_name} not available: {e}")
            print(f"   Pull with: ollama pull {model_name}\n")


async def temperature_comparison():
    """Show effect of temperature parameter."""
    print("=" * 60)
    print("Temperature Comparison (Ollama)")
    print("=" * 60)

    llm = OllamaLLM(model="llama2")
    messages = [Message(role="user", content="List 3 creative uses for AI agents.")]

    temperatures = [0.0, 0.5, 1.0]

    print("Same prompt, different temperatures:\n")

    for temp in temperatures:
        print(f"Temperature: {temp}")
        print("-" * 40)

        try:
            response = await llm.complete(messages, temperature=temp, max_tokens=100)
            print(f"{response.content}\n")

        except Exception as e:
            print(f"❌ Error: {e}\n")
            return


async def main():
    """Run all Ollama adapter examples."""
    print("\n" + "=" * 60)
    print("OLLAMA ADAPTER EXAMPLES")
    print("=" * 60)
    print("Local LLM inference with Ollama")
    print()

    # Check if Ollama might be available
    print("Prerequisites:")
    print("  ✓ No API key required (runs locally)")
    print("  ✓ Install: https://ollama.ai/download")
    print("  ✓ Pull model: ollama pull llama2")
    print()

    await basic_completion()
    await streaming_example()
    await conversation_example()
    await model_comparison()
    await temperature_comparison()

    print("=" * 60)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 60)
    print()
    print("💡 Key Advantages of Ollama:")
    print("  • No API keys or costs")
    print("  • Runs entirely locally")
    print("  • Fast inference on local hardware")
    print("  • Privacy - data never leaves your machine")
    print("  • Great for development and testing")
    print()
    print("Popular Ollama models:")
    print("  • llama2 - Meta's Llama 2 (balanced)")
    print("  • mistral - Mistral 7B (fast, capable)")
    print("  • codellama - Code-focused Llama")
    print("  • phi - Microsoft's efficient model")
    print("  • gemma - Google's open model")
    print()
    print("Commands:")
    print("  ollama list          - Show installed models")
    print("  ollama pull <model>  - Download a model")
    print("  ollama serve         - Start Ollama server")


if __name__ == "__main__":
    asyncio.run(main())
