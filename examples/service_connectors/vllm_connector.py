"""
vLLM Service Connector Example

vLLM is a high-throughput inference engine optimised for GPU clusters.
It exposes an OpenAI-compatible /v1/chat/completions endpoint.

Setup:
    pip install vllm
    python -m vllm.entrypoints.openai.api_server \
        --model meta-llama/Llama-3.1-8B-Instruct

    Wait for the server to print "Application startup complete" before running
    this example.  Check readiness with: curl http://localhost:8000/health

Run:
    uv run python examples/service_connectors/vllm_connector.py
"""

import asyncio

from agenkit.adapters.llm import VLLMConnector
from agenkit.interfaces import Message


async def main() -> None:
    """Demonstrate the VLLMConnector factory function."""
    print("vLLM Service Connector")
    print("======================")

    # One-line connector — uses default URL http://localhost:8000/v1
    llm = VLLMConnector("meta-llama/Llama-3.1-8B-Instruct")

    messages = [
        Message(role="user", content="Reply in one sentence: what makes vLLM fast?"),
    ]

    print(f"Model   : {llm.model}")
    print(f"Sending : {messages[0].content}")
    print()

    try:
        response = await llm.complete(messages, temperature=0.3, max_tokens=80)
    except Exception as e:
        print(f"Not available (is the vLLM server running?): {e}")
        print()
        print("Start the server with:")
        print("  python -m vllm.entrypoints.openai.api_server \\")
        print("      --model meta-llama/Llama-3.1-8B-Instruct")
        return

    print(f"Response : {response.content}")
    print()
    print("Metadata:")
    print(f"  model    : {response.metadata.get('model')}")
    print(f"  provider : {response.metadata.get('provider')}")
    usage = response.metadata.get("usage", {})
    print(f"  tokens   : {usage.get('total_tokens')}")

    # Demonstrate overriding base_url for a remote deployment
    print()
    print("Override example (remote host):")
    remote_llm = VLLMConnector(
        "meta-llama/Llama-3.1-8B-Instruct",
        base_url="http://gpu-cluster:8000/v1",
    )
    print(f"  Would connect to: http://gpu-cluster:8000/v1 — model: {remote_llm.model}")


if __name__ == "__main__":
    asyncio.run(main())
