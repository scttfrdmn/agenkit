"""
vLLM via OpenAI-compatible endpoint.

vLLM is a high-throughput inference server that serves any HuggingFace model
with an OpenAI-compatible API. It is commonly used for GPU clusters and
production batch workloads.

Setup:
  # With Docker (GPU):
  docker run --gpus all -p 8000:8000 vllm/vllm-openai \\
      --model meta-llama/Llama-3.2-3B-Instruct

  # Or pip install (requires CUDA):
  pip install vllm
  python -m vllm.entrypoints.openai.api_server \\
      --model meta-llama/Llama-3.2-3B-Instruct --port 8000

  # Then run:
  uv run python examples/local_models/vllm_example.py
"""

import asyncio

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message

VLLM_BASE_URL = "http://localhost:8000/v1"
VLLM_MODEL = "meta-llama/Llama-3.2-3B-Instruct"


async def basic_completion() -> None:
    """Simple one-shot completion."""
    print("=== Basic Completion ===")

    llm = OpenAICompatibleLLM(
        base_url=VLLM_BASE_URL,
        model=VLLM_MODEL,
        provider="vllm",
    )

    messages = [Message(role="user", content="What is vLLM in one sentence?")]

    try:
        response = await llm.complete(messages, max_tokens=80)
        print(f"Model  : {response.metadata.get('model', VLLM_MODEL)}")
        print(f"Reply  : {response.content}")
        if usage := response.metadata.get("usage"):
            print(f"Tokens : {usage.get('total_tokens')}")
    except Exception as e:
        print(f"Error (is vLLM running?): {e}")
        print(
            "  docker run --gpus all -p 8000:8000 vllm/vllm-openai --model meta-llama/Llama-3.2-3B-Instruct"
        )
    print()


async def streaming_completion() -> None:
    """Stream tokens as they arrive."""
    print("=== Streaming ===")

    llm = OpenAICompatibleLLM(
        base_url=VLLM_BASE_URL,
        model=VLLM_MODEL,
        provider="vllm",
    )

    messages = [Message(role="user", content="List three benefits of local LLM inference.")]

    print("Streaming: ", end="", flush=True)
    try:
        async for chunk in llm.stream(messages, max_tokens=120):
            print(chunk.content, end="", flush=True)
        print()
    except Exception as e:
        print(f"\nError: {e}")
    print()


async def custom_parameters() -> None:
    """Demonstrate generation parameters."""
    print("=== Custom Parameters ===")

    llm = OpenAICompatibleLLM(
        base_url=VLLM_BASE_URL,
        model=VLLM_MODEL,
        provider="vllm",
    )

    messages = [
        Message(role="system", content="You are a concise assistant."),
        Message(role="user", content="Explain gradient descent in one sentence."),
    ]

    try:
        response = await llm.complete(
            messages,
            temperature=0.2,
            max_tokens=60,
        )
        print(f"Reply  : {response.content}")
        print("Params : temperature=0.2, max_tokens=60")
    except Exception as e:
        print(f"Error: {e}")
    print()


async def main() -> None:
    print("vLLM — GPU Inference Server via OpenAI-Compatible Endpoint")
    print("============================================================")
    print(f"URL   : {VLLM_BASE_URL}")
    print(f"Model : {VLLM_MODEL}")
    print()

    await basic_completion()
    await streaming_completion()
    await custom_parameters()

    print("Done. vLLM supports any HuggingFace model via --model <repo/name>.")


if __name__ == "__main__":
    asyncio.run(main())
