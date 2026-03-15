"""
Service Connectors — named provider preset factory functions.

Service connectors are thin factory functions that wrap OpenAICompatibleLLM
with provider-specific default URLs and provider identifiers. They reduce
boilerplate for the common case where you just want to connect to a known
inference server type.

Use a service connector when:
  - You know which inference server you are talking to (vLLM, SGLang, etc.)
  - You want self-documenting code that names the provider explicitly
  - You are fine with the provider's default port and URL scheme

Use OpenAICompatibleLLM directly when:
  - You need a non-standard base URL (remote host, custom port)
  - You are building a generic abstraction that does not know the provider type

Example:

    from agenkit.adapters.llm import VLLMConnector, SGLangConnector

    # Connect to a local vLLM server — one line, no boilerplate
    llm = VLLMConnector("meta-llama/Llama-3.1-8B-Instruct")

    # Override the URL for a remote deployment
    llm = VLLMConnector("meta-llama/Llama-3.1-8B-Instruct", base_url="http://gpu-host:8000/v1")

    # Pass extra kwargs through to OpenAICompatibleLLM (e.g. timeout_ms)
    llm = SGLangConnector("meta-llama/Llama-3.1-8B-Instruct", timeout_ms=120000)
"""

from typing import Any

from agenkit.adapters.llm.openai_compatible import OpenAICompatibleLLM


def VLLMConnector(
    model: str,
    base_url: str = "http://localhost:8000/v1",
    **kwargs: Any,
) -> OpenAICompatibleLLM:
    """Return an OpenAICompatibleLLM configured for a vLLM inference server.

    vLLM is a high-throughput inference engine optimised for serving many
    requests concurrently on GPU clusters.

    Args:
        model: Model identifier as loaded by the vLLM server
            (e.g. "meta-llama/Llama-3.1-8B-Instruct").
        base_url: Base URL of the vLLM OpenAI-compatible endpoint.
            Defaults to "http://localhost:8000/v1".
        **kwargs: Additional arguments forwarded to OpenAICompatibleLLM
            (e.g. api_key, timeout_ms).

    Returns:
        Configured OpenAICompatibleLLM instance with provider="vllm".

    Example:
        >>> llm = VLLMConnector("meta-llama/Llama-3.1-8B-Instruct")
        >>> response = await llm.complete(messages)

        >>> # Remote deployment
        >>> llm = VLLMConnector("meta-llama/Llama-3.1-8B-Instruct", base_url="http://gpu01:8000/v1")
    """
    return OpenAICompatibleLLM(base_url=base_url, model=model, provider="vllm", **kwargs)


def SGLangConnector(
    model: str,
    base_url: str = "http://localhost:30000/v1",
    **kwargs: Any,
) -> OpenAICompatibleLLM:
    """Return an OpenAICompatibleLLM configured for an SGLang inference server.

    SGLang (Structured Generation Language) is optimised for complex prompts,
    structured output, and multi-turn conversations.  It can be 29–64% faster
    than vLLM for certain workloads.

    Args:
        model: Model identifier as loaded by the SGLang server
            (e.g. "meta-llama/Llama-3.1-8B-Instruct").
        base_url: Base URL of the SGLang OpenAI-compatible endpoint.
            Defaults to "http://localhost:30000/v1".
        **kwargs: Additional arguments forwarded to OpenAICompatibleLLM.

    Returns:
        Configured OpenAICompatibleLLM instance with provider="sglang".

    Example:
        >>> llm = SGLangConnector("meta-llama/Llama-3.1-8B-Instruct")
        >>> response = await llm.complete(messages)
    """
    return OpenAICompatibleLLM(base_url=base_url, model=model, provider="sglang", **kwargs)


def TensorRTLLMConnector(
    model: str,
    base_url: str = "http://localhost:8000/v1",
    **kwargs: Any,
) -> OpenAICompatibleLLM:
    """Return an OpenAICompatibleLLM configured for a TensorRT-LLM inference server.

    TensorRT-LLM is NVIDIA's inference framework that compiles models to
    optimised TensorRT engines for maximum throughput on NVIDIA GPUs.  It is
    typically served via Triton Inference Server.

    Args:
        model: Model identifier as configured in the Triton model repository
            (e.g. "llama-3.1-8b-instruct").
        base_url: Base URL of the TensorRT-LLM / Triton OpenAI-compatible endpoint.
            Defaults to "http://localhost:8000/v1".
        **kwargs: Additional arguments forwarded to OpenAICompatibleLLM.

    Returns:
        Configured OpenAICompatibleLLM instance with provider="tensorrt-llm".

    Example:
        >>> llm = TensorRTLLMConnector("llama-3.1-8b-instruct")
        >>> response = await llm.complete(messages)
    """
    return OpenAICompatibleLLM(base_url=base_url, model=model, provider="tensorrt-llm", **kwargs)


def DeepSpeedConnector(
    model: str,
    base_url: str = "http://localhost:8000/v1",
    **kwargs: Any,
) -> OpenAICompatibleLLM:
    """Return an OpenAICompatibleLLM configured for a DeepSpeed-MII inference server.

    DeepSpeed-MII (Model Implementations for Inference) provides highly
    optimised inference for large transformer models using DeepSpeed's
    inference kernels.

    Args:
        model: Model identifier as loaded by DeepSpeed-MII
            (e.g. "meta-llama/Llama-3.1-8B-Instruct").
        base_url: Base URL of the DeepSpeed-MII OpenAI-compatible endpoint.
            Defaults to "http://localhost:8000/v1".
        **kwargs: Additional arguments forwarded to OpenAICompatibleLLM.

    Returns:
        Configured OpenAICompatibleLLM instance with provider="deepspeed".

    Example:
        >>> llm = DeepSpeedConnector("meta-llama/Llama-3.1-8B-Instruct")
        >>> response = await llm.complete(messages)
    """
    return OpenAICompatibleLLM(base_url=base_url, model=model, provider="deepspeed", **kwargs)
