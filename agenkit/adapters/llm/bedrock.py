"""
Amazon Bedrock adapter for Agenkit.

This module provides an adapter for AWS Bedrock foundation models using boto3.
Supports full AWS credential chain and enterprise deployment patterns.
"""

import asyncio
from collections.abc import AsyncIterator
from functools import partial
from typing import Any

from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError as e:
    raise ImportError(
        "The boto3 package is required to use BedrockLLM. "
        "Install it with: pip install boto3>=1.34.0"
    ) from e


class BedrockLLM(LLM):
    """
    Amazon Bedrock adapter.

    Provides enterprise-grade AWS integration for foundation models available
    through Amazon Bedrock (Claude, Llama, Mistral, Titan, etc.).

    Supports full AWS credential chain:
    - Explicit credentials (access_key_id, secret_access_key)
    - AWS profiles (~/.aws/config)
    - Environment variables (AWS_ACCESS_KEY_ID, etc.)
    - IAM roles (EC2, ECS, EKS)
    - STS assume role

    Args:
        model_id: Bedrock model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
        region_name: AWS region (default: us-east-1)
        aws_access_key_id: AWS access key (optional)
        aws_secret_access_key: AWS secret key (optional)
        aws_session_token: AWS session token (optional)
        profile_name: AWS profile name (optional)
        endpoint_url: Custom endpoint URL for VPC endpoints (optional)
        **config_kwargs: Additional boto3 Config parameters

    Example:
        >>> from agenkit.adapters.llm import BedrockLLM
        >>> from agenkit import Message
        >>>
        >>> # Use IAM role (ECS/EKS/EC2)
        >>> llm = BedrockLLM(model_id="anthropic.claude-3-5-sonnet-20241022-v2:0")
        >>>
        >>> # Use AWS profile
        >>> llm = BedrockLLM(
        ...     model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        ...     profile_name="production"
        ... )
        >>>
        >>> # Use explicit credentials
        >>> llm = BedrockLLM(
        ...     model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        ...     aws_access_key_id="...",
        ...     aws_secret_access_key="..."
        ... )
        >>>
        >>> messages = [Message(role="user", content="Hello!")]
        >>> response = await llm.complete(messages)

    VPC endpoint example:
        >>> llm = BedrockLLM(
        ...     model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        ...     endpoint_url="https://bedrock-runtime.us-east-1.vpce-xxx.amazonaws.com"
        ... )

    Popular model IDs:
        - anthropic.claude-3-5-sonnet-20241022-v2:0 - Claude 3.5 Sonnet
        - anthropic.claude-3-haiku-20240307-v1:0 - Claude 3 Haiku
        - meta.llama3-70b-instruct-v1:0 - Llama 3 70B
        - mistral.mistral-large-2402-v1:0 - Mistral Large
        - amazon.titan-text-premier-v1:0 - Amazon Titan
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile_name: str | None = None,
        endpoint_url: str | None = None,
        **config_kwargs: Any,
    ):
        """Initialize Bedrock LLM adapter."""
        self._model_id = model_id
        self._region_name = region_name

        # Build boto3 config
        config = Config(region_name=region_name, **config_kwargs)

        # Create session with credentials if provided
        session_kwargs: dict[str, Any] = {}
        if profile_name:
            session_kwargs["profile_name"] = profile_name
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            session_kwargs["aws_session_token"] = aws_session_token

        session = boto3.Session(**session_kwargs) if session_kwargs else boto3.Session()

        # Create bedrock-runtime client
        client_kwargs: dict[str, Any] = {"config": config}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        self._client = session.client("bedrock-runtime", **client_kwargs)

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return self._model_id

    async def complete(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> Message:
        """
        Generate a completion from Bedrock.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Bedrock options (topP, stopSequences, etc.)

        Returns:
            Response as Agenkit Message with metadata including:
            - model: Model ID used
            - usage: Token counts (input, output, total)
            - stop_reason: Why generation stopped

        Example:
            >>> messages = [
            ...     Message(role="system", content="You are a helpful assistant."),
            ...     Message(role="user", content="What is 2+2?")
            ... ]
            >>> response = await llm.complete(messages, temperature=0.2)
            >>> print(response.content)
            >>> print(response.metadata["usage"])
        """
        # Convert Agenkit Messages to Bedrock format
        bedrock_messages, system_prompts = self._convert_messages(messages)

        # Build inference config
        inference_config = {
            "temperature": temperature,
            "maxTokens": max_tokens,
        }

        # Merge additional kwargs (topP, stopSequences, etc.)
        for key in ("topP", "stopSequences"):
            if key in kwargs:
                inference_config[key] = kwargs.pop(key)

        # Build converse parameters
        converse_params: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": bedrock_messages,
            "inferenceConfig": inference_config,
        }

        # Add system prompts if present
        if system_prompts:
            converse_params["system"] = system_prompts

        # Add additional kwargs (guardrailConfig, etc.)
        converse_params.update(kwargs)

        # Call Bedrock API asynchronously (boto3 is sync, so use executor)
        loop = asyncio.get_running_loop()
        converse_func = partial(self._client.converse, **converse_params)

        try:
            response = await loop.run_in_executor(None, converse_func)
        except ClientError as e:
            raise RuntimeError(f"Bedrock API error: {e}") from e

        # Extract response content
        output = response.get("output", {})
        message_output = output.get("message", {})
        content_blocks = message_output.get("content", [])

        # Combine all text content
        text_content = ""
        for block in content_blocks:
            if "text" in block:
                text_content += block["text"]

        # Build metadata
        metadata: dict[str, Any] = {
            "model": self._model_id,
        }

        # Add usage if available
        if "usage" in response:
            usage = response["usage"]
            metadata["usage"] = {
                "prompt_tokens": usage.get("inputTokens", 0),
                "completion_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0),
            }

        # Add stop reason
        if "stopReason" in response:
            metadata["stop_reason"] = response["stopReason"]

        # Convert response to Agenkit Message
        return Message(
            role="agent",
            content=text_content,
            metadata=metadata,
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[Message]:
        """
        Stream completion chunks from Bedrock.

        Args:
            messages: Conversation history as Agenkit Messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Bedrock options

        Yields:
            Message chunks as they arrive from Bedrock

        Example:
            >>> messages = [Message(role="user", content="Count to 10")]
            >>> async for chunk in llm.stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        # Convert messages
        bedrock_messages, system_prompts = self._convert_messages(messages)

        # Build inference config
        inference_config = {
            "temperature": temperature,
            "maxTokens": max_tokens,
        }

        # Merge additional kwargs
        for key in ("topP", "stopSequences"):
            if key in kwargs:
                inference_config[key] = kwargs.pop(key)

        # Build converse parameters
        converse_params: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": bedrock_messages,
            "inferenceConfig": inference_config,
        }

        if system_prompts:
            converse_params["system"] = system_prompts

        converse_params.update(kwargs)

        # Call Bedrock streaming API
        loop = asyncio.get_running_loop()
        converse_stream_func = partial(self._client.converse_stream, **converse_params)

        try:
            response = await loop.run_in_executor(None, converse_stream_func)
        except ClientError as e:
            raise RuntimeError(f"Bedrock API error: {e}") from e

        # Stream chunks
        stream = response.get("stream", [])
        for event in stream:
            # Extract text delta from contentBlockDelta events
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    yield Message(
                        role="agent",
                        content=delta["text"],
                        metadata={"streaming": True, "model": self._model_id},
                    )
            # Allow other async tasks to run
            await asyncio.sleep(0)

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """
        Convert Agenkit Messages to Bedrock Converse format.

        Bedrock expects:
        - role: "user" or "assistant"
        - content: list of content blocks with {"text": "..."}

        System messages are handled separately via system parameter.

        Returns:
            Tuple of (bedrock_messages, system_prompts)
        """
        bedrock_messages = []
        system_prompts = []

        for msg in messages:
            # Handle system messages separately
            if msg.role == "system":
                system_prompts.append({"text": str(msg.content)})
                continue

            # Map roles
            if msg.role == "user":
                role = "user"
            else:
                # Map "agent" and others to "assistant"
                role = "assistant"

            bedrock_messages.append(
                {"role": role, "content": [{"text": str(msg.content)}]}
            )

        return bedrock_messages, system_prompts

    def unwrap(self) -> Any:
        """
        Get the underlying boto3 bedrock-runtime client.

        Returns:
            The boto3 client for direct API access

        Example:
            >>> llm = BedrockLLM()
            >>> client = llm.unwrap()
            >>> # Use Bedrock-specific features
            >>> response = client.converse(...)
        """
        return self._client
