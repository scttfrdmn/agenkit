"""
DeepSpeed-MII Service Connector Example

DeepSpeed-MII (Model Implementations for Inference) provides highly optimised
inference for large transformer models using DeepSpeed's inference kernels,
including tensor parallelism and kernel fusion.

Setup:
    pip install deepspeed-mii
    python -c "import mii; mii.serve('meta-llama/Llama-3.1-8B-Instruct')"

    DeepSpeed-MII exposes an OpenAI-compatible endpoint on port 8000 by default.
    Check readiness with: curl http://localhost:8000/health

Run:
    uv run python examples/service_connectors/deepspeed_connector.py
"""

import asyncio

from agenkit.adapters.llm import DeepSpeedConnector
from agenkit.interfaces import Message


async def main() -> None:
    """Demonstrate the DeepSpeedConnector factory function."""
    print("DeepSpeed-MII Service Connector")
    print("================================")

    # One-line connector — uses default URL http://localhost:8000/v1
    llm = DeepSpeedConnector("meta-llama/Llama-3.1-8B-Instruct")

    print(f"Model   : {llm.model}")
    print()

    # Basic completion
    messages = [
        Message(role="user", content="Reply in one sentence: what is DeepSpeed-MII?"),
    ]

    print(f"Basic completion: {messages[0].content}")
    try:
        response = await llm.complete(messages, temperature=0.3, max_tokens=80)
    except Exception as e:
        print(f"Not available (is the DeepSpeed-MII server running?): {e}")
        print()
        print("Start the server with:")
        print('  python -c "import mii; mii.serve(\'meta-llama/Llama-3.1-8B-Instruct\')"')
        return

    print(f"Response : {response.content}")
    print(f"Provider : {response.metadata.get('provider')}")
    print(f"Tokens   : {response.metadata.get('usage', {}).get('total_tokens')}")
    print()

    # Demonstrate kwargs: temperature and max_tokens
    print("Custom generation parameters (temperature=0.8, max_tokens=50):")
    creative_messages = [
        Message(role="user", content="Describe inference in one creative metaphor."),
    ]
    try:
        creative_response = await llm.complete(
            creative_messages,
            temperature=0.8,
            max_tokens=50,
        )
        print(f"Response : {creative_response.content}")
        print(f"Finish   : {creative_response.metadata.get('finish_reason')}")
    except Exception as e:
        print(f"Not available: {e}")

    # Show how to pass extra kwargs to the connector itself (timeout_ms)
    print()
    print("Custom timeout example:")
    slow_llm = DeepSpeedConnector(
        "meta-llama/Llama-3.1-8B-Instruct",
        timeout_ms=120000,  # 2 minutes for large-model deployments
    )
    print(f"  Connector created with timeout_ms=120000, model={slow_llm.model}")


if __name__ == "__main__":
    asyncio.run(main())
