"""
LLM Integration Example - OpenAI, Anthropic, and Ollama

Demonstrates how to integrate real LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Ollama (Local models)
- Middleware for production resilience

Setup:
    export OPENAI_API_KEY="your-key"
    export ANTHROPIC_API_KEY="your-key"
    # For Ollama: ollama pull llama2

Run: python examples/integration/llm-integration.py
"""

import asyncio
import os

from agenkit.adapters.llm import AnthropicLLM, OllamaLLM, OpenAILLM
from agenkit.interfaces import Message
from agenkit.middleware.circuit_breaker import circuit_breaker
from agenkit.middleware.retry import retry
from agenkit.middleware.timeout import timeout


def print_separator(title: str = "") -> None:
    """Print a formatted section separator."""
    print("\n" + "=" * 70)
    if title:
        print(title)
        print("=" * 70)
    print()


async def example_openai() -> None:
    """Example 1: OpenAI Integration."""
    print_separator("Example 1: OpenAI Integration")
    print("  GPT-4 and GPT-3.5 Turbo support\n")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY not set, skipping...\n")
        return

    llm = OpenAILLM(
        api_key=api_key,
        model="gpt-3.5-turbo",  # or 'gpt-4'
        temperature=0.7,
        max_tokens=150,
    )

    print('  Asking OpenAI: "What is agenkit?"')
    try:
        messages = [Message(role="user", content="What is agenkit? Answer in one sentence.")]
        response = await llm.complete(messages)
        print(f"  🤖 OpenAI: {response.content}\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")


async def example_anthropic() -> None:
    """Example 2: Anthropic Integration (Claude)."""
    print_separator("Example 2: Anthropic Integration")
    print("  Claude 3 (Opus, Sonnet, Haiku) support\n")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ⚠️  ANTHROPIC_API_KEY not set, skipping...\n")
        return

    llm = AnthropicLLM(
        api_key=api_key,
        model="claude-3-5-sonnet-20241022",
        max_tokens=150,
    )

    print('  Asking Claude: "What makes a good AI agent framework?"')
    try:
        messages = [
            Message(role="user", content="What makes a good AI agent framework? One sentence.")
        ]
        response = await llm.complete(messages)
        print(f"  🤖 Claude: {response.content}\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")


async def example_ollama() -> None:
    """Example 3: Ollama Integration (Local models)."""
    print_separator("Example 3: Ollama Integration")
    print("  Local LLM inference (Llama 2, Mistral, etc.)\n")

    llm = OllamaLLM(
        model="llama2",
        base_url="http://localhost:11434",
        temperature=0.7,
        max_tokens=150,
    )

    print('  Asking Ollama: "What are AI agents?"')
    try:
        messages = [Message(role="user", content="What are AI agents? One sentence.")]
        response = await llm.complete(messages)
        print(f"  🤖 Ollama: {response.content}\n")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print("  💡 Make sure Ollama is running: ollama serve")
        print("  💡 And model is downloaded: ollama pull llama2\n")


async def example_production_middleware() -> None:
    """Example 4: Production-Ready LLM with Middleware."""
    print_separator("Example 4: Production-Ready LLM with Middleware")
    print("  Add resilience: Retry + Timeout + Circuit Breaker\n")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY not set, skipping...\n")
        return

    # Create base LLM
    base_llm = OpenAILLM(
        api_key=api_key,
        model="gpt-3.5-turbo",
        temperature=0.7,
    )

    # Wrap with production middleware
    production_llm = circuit_breaker(
        timeout(
            retry(
                base_llm,
                max_retries=3,
                initial_delay=1.0,
                backoff_multiplier=2.0,
            ),
            timeout_seconds=30.0,
        ),
        failure_threshold=5,
        recovery_timeout=60.0,
    )

    print("  Middleware stack: Circuit Breaker → Timeout → Retry → OpenAI")
    print("  Processing request...")

    try:
        messages = [Message(role="user", content="Explain middleware in one sentence.")]
        response = await production_llm.complete(messages)
        print(f"  ✅ Success: {response.content}\n")
    except Exception as e:
        print(f"  ❌ Failed: {e}\n")


async def example_streaming() -> None:
    """Example 5: Streaming LLM Responses."""
    print_separator("Example 5: Streaming LLM Responses")
    print("  Real-time token-by-token output\n")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  OPENAI_API_KEY not set, skipping...\n")
        return

    llm = OpenAILLM(
        api_key=api_key,
        model="gpt-3.5-turbo",
    )

    print('  Streaming response: "Tell me a haiku about code"')
    print("  🤖 ", end="", flush=True)

    try:
        messages = [Message(role="user", content="Tell me a haiku about code.")]
        async for chunk in llm.stream(messages):
            print(chunk.content, end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\n  ❌ Error: {e}\n")


def print_best_practices() -> None:
    """Print LLM configuration best practices."""
    print_separator("🎯 LLM Configuration Best Practices")

    print("  Model Selection:")
    print("    • GPT-4: Most capable, slower, $$$")
    print("    • GPT-3.5-turbo: Fast, cheap, good for most tasks")
    print("    • Claude Opus: Highest capability")
    print("    • Claude Sonnet: Balanced performance/cost")
    print("    • Claude Haiku: Fastest, cheapest")
    print("    • Ollama (local): Free, private, offline\n")

    print("  Temperature Settings:")
    print("    • 0.0-0.3: Deterministic, factual (code, facts)")
    print("    • 0.4-0.7: Balanced (most applications)")
    print("    • 0.8-1.0: Creative (writing, brainstorming)\n")

    print("  Production Checklist:")
    print("    ✓ Add retry middleware (handle rate limits)")
    print("    ✓ Add timeout middleware (prevent hangs)")
    print("    ✓ Add circuit breaker (handle outages)")
    print("    ✓ Monitor token usage (cost control)")
    print("    ✓ Cache responses (reduce API calls)")
    print("    ✓ Use streaming for UX (show progress)\n")


def print_cost_optimization() -> None:
    """Print cost optimization tips."""
    print_separator("💰 Cost Optimization Tips")

    print("  1. Use appropriate models:")
    print("     • Don't use GPT-4 for simple tasks")
    print("     • Start with GPT-3.5, upgrade if needed\n")

    print("  2. Limit max_tokens:")
    print("     • Set reasonable limits (e.g., 150 for short answers)")
    print("     • Prevents runaway costs\n")

    print("  3. Cache responses:")
    print("     • Use caching middleware for repeated queries")
    print("     • Especially effective for FAQ-style apps\n")

    print("  4. Batch requests:")
    print("     • Use batching middleware when possible")
    print("     • OpenAI Batch API: 50% cheaper!\n")

    print("  5. Use local models (Ollama):")
    print("     • Free for development and testing")
    print("     • No API costs or rate limits")
    print("     • Privacy-preserving (data stays local)\n")

    print("✨ Pro Tip: Monitor your API usage in production!")
    print("   Set up alerts for unexpected cost spikes.\n")


async def main() -> None:
    """Run all integration examples."""
    print("\n🤖 Agenkit LLM Integration Examples\n")

    await example_openai()
    await example_anthropic()
    await example_ollama()
    await example_production_middleware()
    await example_streaming()

    print_best_practices()
    print_cost_optimization()

    print_separator("✅ ALL EXAMPLES COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
