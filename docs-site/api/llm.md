# LLM Adapters API Reference

Complete API documentation for all LLM adapters in Agenkit.

## Base LLM Interface

All adapters implement the `LLM` abstract base class.

### `agenkit.adapters.llm.LLM`

```python
class LLM(ABC):
    """Base interface for LLM adapters."""

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Message:
        """
        Generate a completion for the given messages.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            Message with role="agent" and response content

        Raises:
            Provider-specific exceptions for API errors
        """

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Message]:
        """
        Stream completion chunks as they're generated.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Yields:
            Message chunks with partial content

        Raises:
            Provider-specific exceptions for API errors
        """

    @property
    def model(self) -> str:
        """Return the model identifier."""

    def unwrap(self) -> Any:
        """
        Get the underlying provider client for advanced usage.

        Returns:
            The native provider client (e.g., AsyncAnthropic, AsyncOpenAI)
        """
```

## Message Format

### `agenkit.interfaces.Message`

```python
@dataclass
class Message:
    """Standard message format across all adapters."""

    role: str  # "user", "agent", or "system"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Role Mapping:**

| Agenkit Role | Anthropic | OpenAI | Gemini | Ollama |
|--------------|-----------|---------|--------|--------|
| `user` | user | user | user | user |
| `agent` | assistant | assistant | model | assistant |
| `system` | system | system | *(merged)* | system |

**Response Metadata:**

All adapters include these metadata fields in responses:

- `model` (str): Model identifier used
- `usage` (dict): Token usage statistics
  - `input_tokens` / `prompt_tokens`: Tokens in request
  - `output_tokens` / `completion_tokens`: Tokens in response
  - `total_tokens`: Total tokens used
- `streaming` (bool): True for streaming chunks, absent for complete responses

## Anthropic Adapter

### `agenkit.adapters.llm.AnthropicLLM`

```python
class AnthropicLLM(LLM):
    """Anthropic Claude adapter using AsyncAnthropic."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        **client_kwargs: Any,
    ):
        """
        Initialize Anthropic LLM.

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Model identifier (default: claude-3-5-sonnet-20241022)
            **client_kwargs: Additional arguments for AsyncAnthropic client
        """
```

**Supported Models:**

- `claude-3-5-sonnet-20241022` - Latest Claude 3.5 Sonnet
- `claude-3-opus-20240229` - Claude 3 Opus (most capable)
- `claude-3-haiku-20240307` - Claude 3 Haiku (fastest)
- `claude-3-sonnet-20240229` - Claude 3 Sonnet

**Additional Parameters:**

- `top_p` (float): Nucleus sampling parameter
- `top_k` (int): Top-k sampling parameter
- `stop_sequences` (list[str]): Custom stop sequences

**Example:**

```python
from agenkit.adapters.llm import AnthropicLLM

llm = AnthropicLLM(
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022",
    timeout=30.0,
)

response = await llm.complete(
    messages,
    temperature=0.7,
    max_tokens=1024,
    top_p=0.9,
)
```

**Unwrap:**

```python
client = llm.unwrap()  # Returns AsyncAnthropic
```

## OpenAI Adapter

### `agenkit.adapters.llm.OpenAILLM`

```python
class OpenAILLM(LLM):
    """OpenAI GPT adapter using AsyncOpenAI."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        **client_kwargs: Any,
    ):
        """
        Initialize OpenAI LLM.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model identifier (default: gpt-4o)
            **client_kwargs: Additional arguments for AsyncOpenAI client
        """
```

**Supported Models:**

- `gpt-4o` - GPT-4 Omni (multimodal)
- `gpt-4o-mini` - Smaller, faster GPT-4 Omni
- `gpt-4-turbo` - GPT-4 Turbo (128K context)
- `gpt-4` - GPT-4 (8K context)
- `gpt-3.5-turbo` - GPT-3.5 Turbo (cost-effective)

**Additional Parameters:**

- `top_p` (float): Nucleus sampling parameter
- `frequency_penalty` (float): Penalize frequent tokens (-2.0 to 2.0)
- `presence_penalty` (float): Penalize present tokens (-2.0 to 2.0)
- `stop` (str | list[str]): Stop sequences
- `seed` (int): Deterministic sampling seed

**Example:**

```python
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(
    api_key="sk-...",
    model="gpt-4o-mini",
    organization="org-...",
)

response = await llm.complete(
    messages,
    temperature=0.7,
    max_tokens=1024,
    top_p=0.9,
    seed=42,
)
```

**Unwrap:**

```python
client = llm.unwrap()  # Returns AsyncOpenAI
```

## Google Gemini Adapter

### `agenkit.adapters.llm.GeminiLLM`

```python
class GeminiLLM(LLM):
    """Google Gemini adapter using google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash-exp",
        **client_kwargs: Any,
    ):
        """
        Initialize Gemini LLM.

        Args:
            api_key: Google API key (or set GEMINI_API_KEY env var)
            model: Model identifier (default: gemini-2.0-flash-exp)
            **client_kwargs: Additional arguments for genai.Client
        """
```

**Supported Models:**

- `gemini-2.0-flash-exp` - Gemini 2.0 Flash (experimental)
- `gemini-1.5-pro` - Gemini 1.5 Pro (2M context)
- `gemini-1.5-flash` - Gemini 1.5 Flash (fast)
- `gemini-pro` - Gemini Pro

**Additional Parameters:**

- `top_p` (float): Nucleus sampling parameter
- `top_k` (int): Top-k sampling parameter
- `stop_sequences` (list[str]): Stop sequences

**Example:**

```python
from agenkit.adapters.llm import GeminiLLM

llm = GeminiLLM(
    api_key="...",
    model="gemini-2.0-flash-exp",
)

response = await llm.complete(
    messages,
    temperature=0.7,
    max_tokens=1024,
    top_k=40,
)
```

**Unwrap:**

```python
client = llm.unwrap()  # Returns genai.Client
```

## AWS Bedrock Adapter

### `agenkit.adapters.llm.BedrockLLM`

```python
class BedrockLLM(LLM):
    """AWS Bedrock adapter using boto3."""

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
        """
        Initialize Bedrock LLM.

        Args:
            model_id: Bedrock model ID
            region_name: AWS region (default: us-east-1)
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            aws_session_token: AWS session token
            profile_name: AWS profile name
            endpoint_url: Custom endpoint URL
            **config_kwargs: Additional boto3 Config parameters
        """
```

**Supported Models:**

- `anthropic.claude-3-5-sonnet-20241022-v2:0` - Claude 3.5 Sonnet
- `anthropic.claude-3-opus-20240229-v1:0` - Claude 3 Opus
- `anthropic.claude-3-haiku-20240307-v1:0` - Claude 3 Haiku
- `meta.llama3-70b-instruct-v1:0` - Llama 3 70B
- `mistral.mistral-7b-instruct-v0:2` - Mistral 7B
- `amazon.titan-text-premier-v1:0` - Titan Text

**AWS Credentials:**

Bedrock supports multiple credential methods (in order of precedence):

1. Explicit credentials (`aws_access_key_id`, `aws_secret_access_key`)
2. AWS profile (`profile_name`)
3. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
4. IAM role (when running on AWS)

**Additional Parameters:**

- `top_p` (float): Nucleus sampling
- `top_k` (int): Top-k sampling (model-specific)
- `stop_sequences` (list[str]): Stop sequences

**Example:**

```python
from agenkit.adapters.llm import BedrockLLM

# Using AWS profile
llm = BedrockLLM(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    profile_name="aws",
    region_name="us-east-1",
)

# Using explicit credentials
llm = BedrockLLM(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    aws_access_key_id="...",
    aws_secret_access_key="...",
    region_name="us-west-2",
)

response = await llm.complete(messages, max_tokens=1024)
```

**Unwrap:**

```python
client = llm.unwrap()  # Returns boto3 bedrock-runtime client
```

## Ollama Adapter

### `agenkit.adapters.llm.OllamaLLM`

```python
class OllamaLLM(LLM):
    """Ollama adapter for local LLMs using AsyncClient."""

    def __init__(
        self,
        model: str = "llama2",
        base_url: str = "http://localhost:11434",
        **client_kwargs: Any,
    ):
        """
        Initialize Ollama LLM.

        Args:
            model: Model name in Ollama (e.g., "llama2", "mistral")
            base_url: Ollama server URL (default: http://localhost:11434)
            **client_kwargs: Additional arguments for AsyncClient
        """
```

**Supported Models:**

Any model available in Ollama:

- `llama2` - Llama 2 7B/13B/70B
- `llama3` - Llama 3 8B/70B
- `mistral` - Mistral 7B
- `codellama` - Code Llama
- `phi` - Phi-2
- `gemma` - Google Gemma

[See all models →](https://ollama.ai/library)

**Additional Parameters:**

- `num_predict` (int): Max tokens (Ollama's equivalent to max_tokens)
- `top_p` (float): Nucleus sampling
- `top_k` (int): Top-k sampling
- `repeat_penalty` (float): Repetition penalty

**Example:**

```python
from agenkit.adapters.llm import OllamaLLM

# Local Ollama
llm = OllamaLLM(
    model="llama2",
    base_url="http://localhost:11434",
)

# Remote Ollama server
llm = OllamaLLM(
    model="mistral",
    base_url="http://192.168.1.100:11434",
)

response = await llm.complete(
    messages,
    temperature=0.7,
    max_tokens=1024,
)
```

**Setup:**

```bash
# Install Ollama
brew install ollama

# Or use Docker
docker run -d -p 11434:11434 ollama/ollama

# Pull a model
ollama pull llama2
```

**Unwrap:**

```python
client = llm.unwrap()  # Returns AsyncClient
```

## LiteLLM Adapter

### `agenkit.adapters.llm.LiteLLMLLM`

```python
class LiteLLMLLM(LLM):
    """LiteLLM adapter supporting 100+ providers."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        api_version: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize LiteLLM adapter.

        Args:
            model: Model identifier in LiteLLM format
            api_key: API key for the provider
            api_base: Custom API base URL
            api_version: API version (for Azure)
            **kwargs: Additional litellm.acompletion parameters
        """
```

**Provider Formats:**

LiteLLM uses prefixed model names:

| Provider | Format | Example |
|----------|--------|---------|
| OpenAI | `<model>` | `gpt-4o-mini` |
| Anthropic | `<model>` | `claude-3-5-sonnet-20241022` |
| Azure OpenAI | `azure/<deployment>` | `azure/gpt-4` |
| AWS Bedrock | `bedrock/<model>` | `bedrock/anthropic.claude-v2` |
| Ollama | `ollama/<model>` | `ollama/llama2` |
| Cohere | `command-<model>` | `command-nightly` |
| Hugging Face | `huggingface/<model>` | `huggingface/bigcode/starcoder` |

[See all formats →](https://docs.litellm.ai/docs/providers)

**Example:**

```python
from agenkit.adapters.llm import LiteLLMLLM

# OpenAI
llm = LiteLLMLLM(model="gpt-4o-mini", api_key="sk-...")

# Anthropic
llm = LiteLLMLLM(model="claude-3-5-sonnet-20241022", api_key="sk-ant-...")

# Azure OpenAI
llm = LiteLLMLLM(
    model="azure/gpt-4",
    api_key="...",
    api_base="https://your-resource.openai.azure.com",
    api_version="2024-02-15-preview",
)

# Ollama (local)
llm = LiteLLMLLM(model="ollama/llama2")

response = await llm.complete(messages, max_tokens=1024)
```

**Unwrap:**

```python
client = llm.unwrap()  # Returns None (LiteLLM is functional)
```

## Common Patterns

### Error Handling

All adapters raise provider-specific exceptions. Catch them for robust error handling:

```python
from anthropic import APIError, RateLimitError
from openai import APIError as OpenAIError

try:
    response = await llm.complete(messages)
except RateLimitError:
    # Handle rate limiting
    await asyncio.sleep(60)
except APIError as e:
    # Handle other API errors
    print(f"API error: {e}")
```

### Timeouts

Use `asyncio.wait_for` for timeouts:

```python
try:
    response = await asyncio.wait_for(
        llm.complete(messages),
        timeout=30.0,
    )
except asyncio.TimeoutError:
    print("Request timed out")
```

Or use the Task pattern:

```python
from agenkit.patterns import Task

async with Task(agent, timeout=30.0) as task:
    result = await task.execute(messages)
```

### Usage Tracking

Track token usage from response metadata:

```python
response = await llm.complete(messages)

if "usage" in response.metadata:
    usage = response.metadata["usage"]
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")

    print(f"Used {total_tokens} tokens")
```

## Type Hints

All adapters are fully typed:

```python
from typing import AsyncIterator
from agenkit.adapters.llm import LLM
from agenkit.interfaces import Message

async def chat_with_llm(llm: LLM, prompt: str) -> str:
    messages = [Message(role="user", content=prompt)]
    response: Message = await llm.complete(messages)
    return response.content

async def stream_response(llm: LLM, messages: list[Message]) -> None:
    chunk: Message
    async for chunk in llm.stream(messages):
        print(chunk.content, end="", flush=True)
```

## Installation

Install adapters with their dependencies:

```bash
# All adapters
pip install agenkit[llm]

# Specific adapters
pip install agenkit anthropic openai
pip install agenkit google-genai
pip install agenkit boto3
pip install agenkit ollama
pip install agenkit litellm
```

## Related Documentation

- [LLM Adapters Guide](../features/llm-adapters.md) - Feature overview and examples
- [Usage Examples](../../examples/llm/) - Complete working examples
- [Testing Guide](../../TESTING.md) - Running tests with API keys
