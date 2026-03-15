"""
SGLang Service Connector Example

SGLang (Structured Generation Language) is a high-performance inference engine
optimised for complex prompts and structured output.  It runs 29-64% faster
than vLLM for certain workloads and has first-class support for constrained
generation.

Setup:
    pip install sglang
    python -m sglang.launch_server \
        --model-path meta-llama/Llama-3.1-8B-Instruct \
        --port 30000

    Check readiness with: curl http://localhost:30000/health

Run:
    uv run python examples/service_connectors/sglang_connector.py
"""

import asyncio

from agenkit.adapters.llm import SGLangConnector
from agenkit.interfaces import Message


async def main() -> None:
    """Demonstrate the SGLangConnector factory function."""
    print("SGLang Service Connector")
    print("========================")

    # One-line connector — uses default URL http://localhost:30000/v1
    llm = SGLangConnector("meta-llama/Llama-3.1-8B-Instruct")

    print(f"Model   : {llm.model}")
    print()

    # Basic completion
    messages = [
        Message(role="user", content="Reply in one sentence: what makes SGLang fast?"),
    ]

    print(f"Basic completion: {messages[0].content}")
    try:
        response = await llm.complete(messages, temperature=0.3, max_tokens=80)
    except Exception as e:
        print(f"Not available (is the SGLang server running?): {e}")
        print()
        print("Start the server with:")
        print("  python -m sglang.launch_server \\")
        print("      --model-path meta-llama/Llama-3.1-8B-Instruct --port 30000")
        return

    print(f"Response : {response.content}")
    print(f"Tokens   : {response.metadata.get('usage', {}).get('total_tokens')}")
    print()

    # Structured output example — system prompt asks for JSON
    structured_messages = [
        Message(
            role="system",
            content=(
                "You are a JSON API. Always respond with valid JSON only. "
                "No prose, no code fences — just the JSON object."
            ),
        ),
        Message(
            role="user",
            content='Return a JSON object with keys "language" and "year_created" for Python.',
        ),
    ]

    print("Structured output example (JSON):")
    try:
        structured_response = await llm.complete(
            structured_messages,
            temperature=0.0,
            max_tokens=60,
        )
        print(f"Response : {structured_response.content}")
        print(f"Provider : {structured_response.metadata.get('provider')}")
    except Exception as e:
        print(f"Not available: {e}")


if __name__ == "__main__":
    asyncio.run(main())
