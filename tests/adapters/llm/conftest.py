"""Shared fixtures and utilities for LLM adapter tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agenkit.interfaces import Message

# Load .env file for integration tests
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use system env vars


@pytest.fixture
def test_messages():
    """Standard test messages for adapter testing."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
    ]


@pytest.fixture
def simple_test_message():
    """Single simple test message."""
    return [Message(role="user", content="Hello!")]


@pytest.fixture
def expected_response_content():
    """Expected response content for tests."""
    return "Hello! I'm doing well, thank you for asking."


# API Key fixtures
@pytest.fixture
def anthropic_api_key():
    """Get Anthropic API key from environment, skip if not present."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return api_key


@pytest.fixture
def openai_api_key():
    """Get OpenAI API key from environment, skip if not present."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    return api_key


@pytest.fixture
def gemini_api_key():
    """Get Gemini API key from environment, skip if not present."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY or GOOGLE_API_KEY not set")
    return api_key


@pytest.fixture
def aws_profile():
    """Get AWS profile for Bedrock testing."""
    profile = os.getenv("AWS_PROFILE", "aws")
    # Check if AWS is configured
    has_creds = bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_PROFILE")
        or (os.path.expanduser("~/.aws/credentials"))
    )
    if not has_creds:
        pytest.skip("AWS credentials not configured")
    return profile


@pytest.fixture
def ollama_available():
    """Check if Ollama is available."""
    import socket

    try:
        # Try to connect to Ollama default port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 11434))
        sock.close()
        if result != 0:
            pytest.skip("Ollama not running on localhost:11434")
        return True
    except Exception:
        pytest.skip("Could not check Ollama availability")


# Mock fixtures for unit tests
@pytest.fixture
def mock_anthropic_response(expected_response_content):
    """Mock Anthropic API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=expected_response_content)]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=15)
    mock_response.stop_reason = "end_turn"
    mock_response.id = "msg_test123"
    return mock_response


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response):
    """Mock AsyncAnthropic client."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_anthropic_response)
    return mock_client


@pytest.fixture
def mock_openai_response(expected_response_content):
    """Mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content=expected_response_content),
            finish_reason="stop",
        )
    ]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=15, total_tokens=25)
    mock_response.model = "gpt-4o-mini"
    mock_response.id = "chatcmpl_test123"
    return mock_response


@pytest.fixture
def mock_openai_client(mock_openai_response):
    """Mock AsyncOpenAI client."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
    return mock_client


@pytest.fixture
def mock_gemini_response(expected_response_content):
    """Mock Gemini API response."""
    mock_response = MagicMock()
    mock_response.text = expected_response_content
    mock_response.usage_metadata = MagicMock(
        prompt_token_count=10, candidates_token_count=15, total_token_count=25
    )
    mock_response.candidates = [MagicMock(finish_reason="STOP")]
    return mock_response


@pytest.fixture
def mock_gemini_client(mock_gemini_response):
    """Mock Gemini client."""
    mock_client = MagicMock()
    mock_aio = AsyncMock()
    mock_aio.models.generate_content = AsyncMock(return_value=mock_gemini_response)
    mock_client.aio = mock_aio
    return mock_client


@pytest.fixture
def mock_bedrock_response(expected_response_content):
    """Mock Bedrock Converse API response."""
    return {
        "output": {
            "message": {"role": "assistant", "content": [{"text": expected_response_content}]}
        },
        "stopReason": "end_turn",
        "usage": {"inputTokens": 10, "outputTokens": 15, "totalTokens": 25},
    }


@pytest.fixture
def mock_ollama_response(expected_response_content):
    """Mock Ollama API response."""
    return {
        "model": "llama2",
        "message": {"role": "assistant", "content": expected_response_content},
        "eval_count": 15,
        "total_duration": 1000000000,
    }
