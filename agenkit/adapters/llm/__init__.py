"""
LLM adapters for connecting to language model providers.

This module provides a minimal, consistent interface for interacting with
any LLM provider (commercial or local). Each adapter wraps an existing
provider SDK and adapts it to the Agenkit Message interface.

Design principles:
- Minimal: Only 2 required methods (complete, stream)
- Consistent: Same interface for all providers
- Swappable: Change providers with one line
- Not reinventing: Wraps existing provider SDKs
- Escape hatch: unwrap() for provider-specific features

Example:
    >>> from agenkit.adapters.llm import AnthropicLLM
    >>> from agenkit import Message
    >>>
    >>> llm = AnthropicLLM(api_key="...")
    >>> messages = [Message(role="user", content="Hello!")]
    >>> response = await llm.complete(messages)
    >>> print(response.content)

Swapping providers:
    >>> # Start with Anthropic
    >>> llm = AnthropicLLM()
    >>>
    >>> # Swap to OpenAI (same interface!)
    >>> llm = OpenAILLM()
    >>>
    >>> # Or use LiteLLM for 100+ providers
    >>> llm = LiteLLMLLM(model="gpt-4")
"""

from agenkit.adapters.llm.base import LLM

# Import adapters with graceful fallback for missing dependencies
__all__ = ["LLM"]

# Anthropic adapter (optional dependency)
try:
    from agenkit.adapters.llm.anthropic import AnthropicLLM

    __all__.append("AnthropicLLM")
except ImportError:
    pass

# OpenAI adapter - For official OpenAI API (api.openai.com)
# Use this for: GPT-4, GPT-3.5, o1, o3, official OpenAI models
try:
    from agenkit.adapters.llm.openai import OpenAILLM

    __all__.append("OpenAILLM")
except ImportError:
    pass

# LiteLLM adapter (optional dependency)
try:
    from agenkit.adapters.llm.litellm import LiteLLMLLM

    __all__.append("LiteLLMLLM")
except ImportError:
    pass

# Google Gemini adapter (optional dependency)
try:
    from agenkit.adapters.llm.gemini import GeminiLLM

    __all__.append("GeminiLLM")
except ImportError:
    pass

# Amazon Bedrock adapter (optional dependency)
try:
    from agenkit.adapters.llm.bedrock import BedrockLLM

    __all__.append("BedrockLLM")
except ImportError:
    pass

# Ollama adapter (optional dependency)
try:
    from agenkit.adapters.llm.ollama import OllamaLLM

    __all__.append("OllamaLLM")
except ImportError:
    pass

# OpenAI-compatible adapter - For self-hosted/local inference services
# Use this for: vLLM, llama.cpp, SGLang, TensorRT-LLM, Ollama, LocalAI, etc.
# Any service implementing the OpenAI Chat Completions API
try:
    from agenkit.adapters.llm.openai_compatible import OpenAICompatibleLLM

    __all__.append("OpenAICompatibleLLM")
except ImportError:
    pass

# Service Connectors — named presets for production inference servers
try:
    from agenkit.adapters.llm.service_connectors import (
        DeepSpeedConnector,
        SGLangConnector,
        TensorRTLLMConnector,
        VLLMConnector,
    )

    __all__.extend(
        ["VLLMConnector", "SGLangConnector", "TensorRTLLMConnector", "DeepSpeedConnector"]
    )
except ImportError:
    pass
