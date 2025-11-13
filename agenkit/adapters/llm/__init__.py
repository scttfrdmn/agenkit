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

# OpenAI adapter (optional dependency)
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
