#!/usr/bin/env python3
"""
Test script for verifying LLM adapter API keys.

This script tests all available LLM adapters with your API keys to ensure
they're configured correctly.

Setup:
1. Copy .env.example to .env
2. Fill in your API keys in .env
3. Install optional dependencies: pip install -e ".[llm]"
4. Run this script: python test_api_keys.py
"""

import asyncio
import os
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment variables from {env_path}")
    else:
        print("⚠ No .env file found. Using system environment variables.")
        print(f"  Create one at: {env_path}")
except ImportError:
    print("⚠ python-dotenv not installed. Using system environment variables.")
    print("  Install with: pip install python-dotenv")

from agenkit import Message

# Test message
TEST_MESSAGE = [Message(role="user", content="Say 'Hello from Agenkit!' and nothing else.")]


async def test_anthropic():
    """Test Anthropic Claude adapter."""
    try:
        from agenkit.adapters.llm import AnthropicLLM

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("⏭  Skipping Anthropic (ANTHROPIC_API_KEY not set)")
            return

        print("\n🧪 Testing Anthropic Claude...")
        # Use Claude 3 Haiku - stable and widely available
        llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")
        response = await llm.complete(TEST_MESSAGE, max_tokens=50)
        print(f"✅ Anthropic works!")
        print(f"   Model: {response.metadata.get('model')}")
        print(f"   Response: {response.content[:100]}")
    except ImportError:
        print("⏭  Skipping Anthropic (anthropic package not installed)")
    except Exception as e:
        print(f"❌ Anthropic failed: {e}")


async def test_openai():
    """Test OpenAI GPT adapter."""
    try:
        from agenkit.adapters.llm import OpenAILLM

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⏭  Skipping OpenAI (OPENAI_API_KEY not set)")
            return

        print("\n🧪 Testing OpenAI GPT...")
        llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")
        response = await llm.complete(TEST_MESSAGE, max_tokens=50)
        print(f"✅ OpenAI works!")
        print(f"   Model: {response.metadata.get('model')}")
        print(f"   Response: {response.content[:100]}")
    except ImportError:
        print("⏭  Skipping OpenAI (openai package not installed)")
    except Exception as e:
        print(f"❌ OpenAI failed: {e}")


async def test_gemini():
    """Test Google Gemini adapter."""
    try:
        from agenkit.adapters.llm import GeminiLLM

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("⏭  Skipping Gemini (GEMINI_API_KEY or GOOGLE_API_KEY not set)")
            return

        print("\n🧪 Testing Google Gemini...")
        llm = GeminiLLM(api_key=api_key, model="gemini-2.0-flash-exp")
        response = await llm.complete(TEST_MESSAGE, max_tokens=50)
        print(f"✅ Gemini works!")
        print(f"   Model: {response.metadata.get('model')}")
        print(f"   Response: {response.content[:100]}")
    except ImportError:
        print("⏭  Skipping Gemini (google-genai package not installed)")
    except Exception as e:
        print(f"❌ Gemini failed: {e}")


async def test_bedrock():
    """Test Amazon Bedrock adapter."""
    try:
        from agenkit.adapters.llm import BedrockLLM

        # Bedrock uses AWS credential chain - check if configured
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        has_creds = bool(
            os.getenv("AWS_ACCESS_KEY_ID")
            or os.getenv("AWS_PROFILE")
            or Path.home() / ".aws" / "credentials"
        )

        if not has_creds:
            print(
                "⏭  Skipping Bedrock (AWS credentials not configured)\n"
                "   Configure with: aws configure"
            )
            return

        print("\n🧪 Testing Amazon Bedrock...")
        llm = BedrockLLM(
            model_id="anthropic.claude-3-haiku-20240307-v1:0", region_name=region
        )
        response = await llm.complete(TEST_MESSAGE, max_tokens=50)
        print(f"✅ Bedrock works!")
        print(f"   Model: {response.metadata.get('model')}")
        print(f"   Response: {response.content[:100]}")
    except ImportError:
        print("⏭  Skipping Bedrock (boto3 package not installed)")
    except Exception as e:
        print(f"❌ Bedrock failed: {e}")


async def test_ollama():
    """Test Ollama adapter."""
    try:
        from agenkit.adapters.llm import OllamaLLM

        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        print("\n🧪 Testing Ollama...")
        print(f"   Host: {host}")
        print("   Note: Make sure Ollama is running and a model is pulled")
        print("   (e.g., `ollama pull llama2`)")

        llm = OllamaLLM(model="llama2", base_url=host)
        response = await llm.complete(TEST_MESSAGE, max_tokens=50)
        print(f"✅ Ollama works!")
        print(f"   Model: {response.metadata.get('model')}")
        print(f"   Response: {response.content[:100]}")
    except ImportError:
        print("⏭  Skipping Ollama (ollama package not installed)")
    except Exception as e:
        print(f"❌ Ollama failed: {e}")
        print("   Make sure Ollama is running: ollama serve")


async def main():
    """Run all adapter tests."""
    print("=" * 60)
    print("Agenkit LLM Adapter API Key Test")
    print("=" * 60)

    # Test all adapters
    await test_anthropic()
    await test_openai()
    await test_gemini()
    await test_bedrock()
    await test_ollama()

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
