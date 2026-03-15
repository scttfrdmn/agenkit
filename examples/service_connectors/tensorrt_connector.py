"""
TensorRT-LLM Service Connector Example

TensorRT-LLM is NVIDIA's inference framework that compiles models to optimised
TensorRT engines for maximum throughput on NVIDIA GPUs.  It is typically served
via NVIDIA Triton Inference Server with an OpenAI-compatible frontend.

Setup:
    docker run --gpus all -p 8000:8000 \
        nvcr.io/nvidia/tritonserver:24.12-trtllm-python-py3

    The container must have your model repository mounted or the model
    already baked in.  Consult the TensorRT-LLM documentation for model
    conversion and Triton model repository layout.

    Check readiness with: curl http://localhost:8000/v2/health/ready

Run:
    uv run python examples/service_connectors/tensorrt_connector.py
"""

import asyncio

from agenkit.adapters.llm import TensorRTLLMConnector
from agenkit.interfaces import Message


async def main() -> None:
    """Demonstrate the TensorRTLLMConnector factory function."""
    print("TensorRT-LLM Service Connector")
    print("==============================")

    # One-line connector — uses default URL http://localhost:8000/v1
    # TensorRT-LLM model names match the Triton model repository name
    llm = TensorRTLLMConnector("llama-3.1-8b-instruct")

    print(f"Model   : {llm.model}")
    print()

    # Basic completion
    basic_messages = [
        Message(role="user", content="Reply in one sentence: what is TensorRT-LLM?"),
    ]

    print(f"Basic completion: {basic_messages[0].content}")
    try:
        response = await llm.complete(basic_messages, temperature=0.3, max_tokens=80)
    except Exception as e:
        print(f"Not available (is the TensorRT-LLM/Triton server running?): {e}")
        print()
        print("Start the server with:")
        print("  docker run --gpus all -p 8000:8000 \\")
        print("      nvcr.io/nvidia/tritonserver:24.12-trtllm-python-py3")
        return

    print(f"Response : {response.content}")
    print(f"Provider : {response.metadata.get('provider')}")
    print(f"Tokens   : {response.metadata.get('usage', {}).get('total_tokens')}")
    print()

    # Multi-message conversation (batch-style)
    conversation = [
        Message(role="system", content="You are a concise technical assistant."),
        Message(role="user", content="What is CUDA?"),
        Message(
            role="agent",
            content="CUDA is NVIDIA's parallel computing platform for GPU programming.",
        ),
        Message(role="user", content="How does TensorRT use it?"),
    ]

    print("Multi-turn conversation:")
    try:
        conv_response = await llm.complete(conversation, temperature=0.4, max_tokens=120)
        print(f"Response : {conv_response.content}")
        print(f"Model    : {conv_response.metadata.get('model')}")
    except Exception as e:
        print(f"Not available: {e}")


if __name__ == "__main__":
    asyncio.run(main())
