"""
Using 100+ providers via LiteLLM.

Shows:
- OpenAI via LiteLLM
- Azure OpenAI
- Local Ollama
- Provider-agnostic code
"""

import asyncio
import os

from agenkit.adapters.llm import LiteLLMLLM
from agenkit.interfaces import Message


async def openai_via_litellm():
    """Use OpenAI through LiteLLM."""
    print("=" * 60)
    print("OpenAI via LiteLLM")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    # LiteLLM uses OpenAI's model naming
    llm = LiteLLMLLM(model="gpt-4o-mini", api_key=api_key)

    messages = [
        Message(role="user", content="What is LiteLLM?")
    ]

    response = await llm.complete(messages, max_tokens=100)
    print(f"Response: {response.content}\n")
    print(f"Model: {response.metadata.get('model')}\n")


async def anthropic_via_litellm():
    """Use Anthropic through LiteLLM."""
    print("=" * 60)
    print("Anthropic via LiteLLM")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    # LiteLLM format: "claude-" prefix
    llm = LiteLLMLLM(
        model="claude-3-haiku-20240307",
        api_key=api_key,
    )

    messages = [
        Message(role="user", content="Explain the benefits of using LiteLLM.")
    ]

    response = await llm.complete(messages, max_tokens=100)
    print(f"Response: {response.content}\n")


async def ollama_via_litellm():
    """Use local Ollama through LiteLLM."""
    print("=" * 60)
    print("Local Ollama via LiteLLM")
    print("=" * 60)

    try:
        # LiteLLM format: "ollama/" prefix
        llm = LiteLLMLLM(model="ollama/llama2")

        messages = [
            Message(role="user", content="What is a local LLM?")
        ]

        print("Attempting to connect to Ollama at http://localhost:11434...")
        response = await llm.complete(messages, max_tokens=100)
        print(f"✅ Response: {response.content}\n")

    except Exception as e:
        print(f"❌ Ollama not available: {e}")
        print("   To use Ollama:")
        print("   1. Start: docker-compose -f docker-compose.test.yml up -d")
        print("   2. Pull model: docker exec agenkit-ollama-test ollama pull llama2\n")


async def provider_agnostic_function():
    """Write code that works with any provider."""
    print("=" * 60)
    print("Provider-Agnostic Code")
    print("=" * 60)

    async def ask_question(model: str, api_key: str | None = None) -> str:
        """Ask a question using any LiteLLM-supported provider."""
        llm = LiteLLMLLM(model=model, api_key=api_key)

        messages = [
            Message(role="user", content="What is 2+2?")
        ]

        response = await llm.complete(messages, max_tokens=50)
        return response.content

    # Try different providers with the same function
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("OpenAI:")
        result = await ask_question("gpt-4o-mini", openai_key)
        print(f"  {result}\n")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("Anthropic:")
        result = await ask_question("claude-3-haiku-20240307", anthropic_key)
        print(f"  {result}\n")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("Gemini:")
        result = await ask_question("gemini/gemini-2.0-flash-exp", gemini_key)
        print(f"  {result}\n")


async def streaming_via_litellm():
    """Stream responses via LiteLLM."""
    print("=" * 60)
    print("Streaming via LiteLLM")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = LiteLLMLLM(model="gpt-4o-mini", api_key=api_key)

    messages = [
        Message(role="user", content="Count from 1 to 10.")
    ]

    print("Streaming: ", end="", flush=True)

    async for chunk in llm.stream(messages, max_tokens=100):
        print(chunk.content, end="", flush=True)

    print("\n")


async def azure_openai_example():
    """Example for Azure OpenAI (requires Azure setup)."""
    print("=" * 60)
    print("Azure OpenAI (Example)")
    print("=" * 60)

    # Note: This requires Azure OpenAI setup
    azure_api_key = os.getenv("AZURE_API_KEY")
    azure_api_base = os.getenv("AZURE_API_BASE")
    azure_api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")

    if not azure_api_key or not azure_api_base:
        print("❌ Azure credentials not configured")
        print("   Required: AZURE_API_KEY, AZURE_API_BASE")
        print("   Optional: AZURE_API_VERSION")
        print("\n   Example:")
        print("   export AZURE_API_KEY='your-key'")
        print("   export AZURE_API_BASE='https://your-resource.openai.azure.com'")
        print("   export AZURE_API_VERSION='2024-02-15-preview'\n")
        return

    try:
        # LiteLLM format for Azure: "azure/<deployment-name>"
        llm = LiteLLMLLM(
            model="azure/gpt-4",
            api_key=azure_api_key,
            api_base=azure_api_base,
            api_version=azure_api_version,
        )

        messages = [Message(role="user", content="Hello from Azure!")]
        response = await llm.complete(messages, max_tokens=50)
        print(f"✅ Response: {response.content}\n")

    except Exception as e:
        print(f"❌ Azure OpenAI error: {e}\n")


async def bedrock_via_litellm():
    """Example for AWS Bedrock via LiteLLM."""
    print("=" * 60)
    print("AWS Bedrock via LiteLLM (Example)")
    print("=" * 60)

    aws_region = os.getenv("AWS_REGION", "us-east-1")
    aws_profile = os.getenv("AWS_PROFILE")

    if not aws_profile:
        print("❌ AWS credentials not configured")
        print("   Required: AWS_PROFILE or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")
        print("\n   Example:")
        print("   export AWS_PROFILE='aws'")
        print("   # or")
        print("   export AWS_ACCESS_KEY_ID='...'")
        print("   export AWS_SECRET_ACCESS_KEY='...'\n")
        return

    try:
        # LiteLLM format for Bedrock: "bedrock/<model-id>"
        llm = LiteLLMLLM(
            model="bedrock/anthropic.claude-3-haiku-20240307-v1:0",
            aws_region_name=aws_region,
        )

        messages = [Message(role="user", content="Hello from Bedrock!")]
        response = await llm.complete(messages, max_tokens=50)
        print(f"✅ Response: {response.content}\n")

    except Exception as e:
        print(f"❌ Bedrock error: {e}\n")


async def main():
    """Run all examples."""
    print("\n🌐 LiteLLM Provider Examples\n")
    print("LiteLLM provides access to 100+ LLM providers with a unified interface.\n")

    await openai_via_litellm()
    await anthropic_via_litellm()
    await ollama_via_litellm()
    await provider_agnostic_function()
    await streaming_via_litellm()
    await azure_openai_example()
    await bedrock_via_litellm()

    print("✅ All examples complete!")
    print("\nSee https://docs.litellm.ai/docs/providers for all supported providers.")


if __name__ == "__main__":
    asyncio.run(main())
