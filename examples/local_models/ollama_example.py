"""
Ollama via OpenAI-compatible endpoint.

Ollama exposes an OpenAI-compatible /v1 API on port 11434, so the same
OpenAICompatibleLLM adapter used for cloud services works here too.

Setup:
  1. Install: https://ollama.ai/download
  2. Pull a model: ollama pull llama3.2
  3. Start server: ollama serve   (or it starts automatically)
  4. Run: uv run python examples/local_models/ollama_example.py
"""

import asyncio

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "llama3.2"


async def basic_completion() -> None:
    """Simple one-shot completion."""
    print("=== Basic Completion ===")

    llm = OpenAICompatibleLLM(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        provider="ollama",
    )

    messages = [Message(role="user", content="What is an AI agent in one sentence?")]

    try:
        response = await llm.complete(messages, max_tokens=80)
        print(f"Model  : {response.metadata.get('model', OLLAMA_MODEL)}")
        print(f"Reply  : {response.content}")
        if usage := response.metadata.get("usage"):
            print(f"Tokens : {usage.get('total_tokens')}")
    except Exception as e:
        print(f"Error (is Ollama running?): {e}")
        print("  ollama serve && ollama pull llama3.2")
    print()


async def streaming_completion() -> None:
    """Stream tokens as they arrive."""
    print("=== Streaming ===")

    llm = OpenAICompatibleLLM(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        provider="ollama",
    )

    messages = [Message(role="user", content="Count from 1 to 5, one number per line.")]

    print("Streaming: ", end="", flush=True)
    try:
        async for chunk in llm.stream(messages, max_tokens=60):
            print(chunk.content, end="", flush=True)
        print()
    except Exception as e:
        print(f"\nError: {e}")
    print()


async def conversation() -> None:
    """Multi-turn conversation using the same adapter interface."""
    print("=== Multi-turn Conversation ===")

    llm = OpenAICompatibleLLM(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        provider="ollama",
    )

    history: list[Message] = [
        Message(role="system", content="You are a concise technical assistant."),
        Message(role="user", content="What is an LLM?"),
    ]

    try:
        r1 = await llm.complete(history, max_tokens=60)
        print(f"User : What is an LLM?")
        print(f"Agent: {r1.content}")

        history.append(r1)
        history.append(Message(role="user", content="Give me one real-world example."))

        r2 = await llm.complete(history, max_tokens=60)
        print(f"User : Give me one real-world example.")
        print(f"Agent: {r2.content}")
    except Exception as e:
        print(f"Error: {e}")
    print()


async def main() -> None:
    print("Ollama — Local Model via OpenAI-Compatible Endpoint")
    print("====================================================")
    print(f"URL   : {OLLAMA_BASE_URL}")
    print(f"Model : {OLLAMA_MODEL}")
    print()

    await basic_completion()
    await streaming_completion()
    await conversation()

    print("Done. To try other models: ollama pull mistral")


if __name__ == "__main__":
    asyncio.run(main())
