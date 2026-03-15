"""
llama.cpp server via OpenAI-compatible endpoint.

llama.cpp runs GGUF-quantized models efficiently on CPU and Apple Silicon.
Its built-in HTTP server exposes an OpenAI-compatible API.

Setup:
  # Build llama.cpp
  git clone https://github.com/ggerganov/llama.cpp
  cd llama.cpp && make -j$(nproc)   # Linux/macOS; on macOS: make LLAMA_METAL=1

  # Download a GGUF model (example: Llama-3.2-3B Q4)
  # From: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF
  # Save to: models/Llama-3.2-3B-Instruct-Q4_K_M.gguf

  # Start the server
  ./llama-server -m models/Llama-3.2-3B-Instruct-Q4_K_M.gguf -c 2048 --port 8080

  # Then run:
  uv run python examples/local_models/llamacpp_example.py
"""

import asyncio

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message

LLAMACPP_BASE_URL = "http://localhost:8080/v1"
# llama.cpp server accepts any string here; it uses whichever model was loaded.
LLAMACPP_MODEL = "llama-3.2-3b-instruct"


async def basic_completion() -> None:
    """Simple one-shot completion."""
    print("=== Basic Completion ===")

    llm = OpenAICompatibleLLM(
        base_url=LLAMACPP_BASE_URL,
        model=LLAMACPP_MODEL,
        provider="llamacpp",
    )

    messages = [Message(role="user", content="What is llama.cpp in one sentence?")]

    try:
        response = await llm.complete(messages, max_tokens=80)
        print(f"Reply  : {response.content}")
        if usage := response.metadata.get("usage"):
            print(f"Tokens : {usage.get('total_tokens')}")
    except Exception as e:
        print(f"Error (is llama-server running?): {e}")
        print("  ./llama-server -m models/model.gguf -c 2048 --port 8080")
    print()


async def streaming_completion() -> None:
    """Stream tokens as they arrive."""
    print("=== Streaming ===")

    llm = OpenAICompatibleLLM(
        base_url=LLAMACPP_BASE_URL,
        model=LLAMACPP_MODEL,
        provider="llamacpp",
    )

    messages = [Message(role="user", content="Write a haiku about local AI inference.")]

    print("Streaming: ", end="", flush=True)
    try:
        async for chunk in llm.stream(messages, max_tokens=60):
            print(chunk.content, end="", flush=True)
        print()
    except Exception as e:
        print(f"\nError: {e}")
    print()


async def system_prompt() -> None:
    """Use a system prompt to shape the response style."""
    print("=== System Prompt ===")

    llm = OpenAICompatibleLLM(
        base_url=LLAMACPP_BASE_URL,
        model=LLAMACPP_MODEL,
        provider="llamacpp",
    )

    messages = [
        Message(
            role="system",
            content="You are a terse engineer. Answer in at most 15 words.",
        ),
        Message(role="user", content="Why use quantized models?"),
    ]

    try:
        response = await llm.complete(messages, max_tokens=40, temperature=0.3)
        print(f"Reply  : {response.content}")
    except Exception as e:
        print(f"Error: {e}")
    print()


async def main() -> None:
    print("llama.cpp — CPU/Metal Inference via OpenAI-Compatible Endpoint")
    print("================================================================")
    print(f"URL   : {LLAMACPP_BASE_URL}")
    print(f"Model : {LLAMACPP_MODEL}  (whichever GGUF was loaded at server start)")
    print()

    await basic_completion()
    await streaming_completion()
    await system_prompt()

    print("Done. Swap the GGUF file to change models — no code changes needed.")


if __name__ == "__main__":
    asyncio.run(main())
