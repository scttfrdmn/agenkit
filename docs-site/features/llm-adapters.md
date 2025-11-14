# LLM Adapters

Connect to any LLM provider with a consistent, minimal interface.

## Overview

Agenkit provides thin adapters for LLM providers that wrap existing SDKs and provide a consistent interface for your agents.

**Design Principles:**

- **Minimal**: Only 2 required methods (`complete`, `stream`)
- **Consistent**: Same interface across all providers
- **Swappable**: Change providers with one line of code
- **Not Reinventing**: Wraps existing battle-tested SDKs
- **Escape Hatch**: `unwrap()` gives you the underlying client for advanced features

## Supported Providers

### Direct Adapters

First-class support with dedicated adapters:

| Provider | Adapter | Models | Use Case |
|----------|---------|--------|----------|
| **Anthropic** | `AnthropicLLM` | Claude 3.5 Sonnet, Haiku, Opus | Best reasoning, long context |
| **OpenAI** | `OpenAILLM` | GPT-4, GPT-4 Turbo, GPT-3.5 | General purpose, function calling |
| **Google Gemini** | `GeminiLLM` | Gemini Pro, Flash, Ultra | Google Cloud integration |
| **AWS Bedrock** | `BedrockLLM` | Claude, Llama, Mistral, Titan | Enterprise AWS deployments |
| **Ollama** | `OllamaLLM` | Llama 2/3, Mistral, CodeLlama | Local/on-premises |

### Via LiteLLM (100+ Providers)

Access any provider through `LiteLLMLLM`:

- Azure OpenAI
- Cohere
- Hugging Face
- AWS Bedrock (alternative)
- Google Vertex AI
- Replicate
- Together AI
- And 100+ more!

[See full provider list →](https://docs.litellm.ai/docs/providers)

## Quick Start

### Installation

```bash
# Install Agenkit with LLM adapters
pip install agenkit[llm]

# Or install specific providers
pip install agenkit anthropic openai google-genai
```

### Basic Usage

```python
import asyncio
from agenkit.adapters.llm import AnthropicLLM
from agenkit import Message

async def main():
    # Initialize the LLM
    llm = AnthropicLLM(api_key="your-api-key")

    # Create a message
    messages = [Message(role="user", content="Explain Agenkit in one sentence.")]

    # Get a response
    response = await llm.complete(messages)
    print(response.content)

asyncio.run(main())
```

## Swapping Providers

**The Killer Feature**: Swap providers with one line of code.

```python
from agenkit.adapters.llm import AnthropicLLM, OpenAILLM, GeminiLLM

# Start with Anthropic
llm = AnthropicLLM(api_key="...")

# Switch to OpenAI (same interface!)
llm = OpenAILLM(api_key="...")

# Or try Google Gemini
llm = GeminiLLM(api_key="...")

# All use the same interface!
response = await llm.complete(messages)
```

**Why this matters:**

- **A/B Testing**: Compare providers on the same prompts
- **Fallback**: Try another provider if one fails
- **Cost Optimization**: Use cheaper models for dev, powerful for prod
- **No Vendor Lock-in**: Switch providers anytime

## Provider-Specific Examples

### Anthropic Claude

```python
from agenkit.adapters.llm import AnthropicLLM

llm = AnthropicLLM(
    api_key="your-api-key",
    model="claude-3-5-sonnet-20241022"  # Latest Claude
)

response = await llm.complete(
    messages,
    temperature=0.7,
    max_tokens=1024,
    top_p=0.9
)

# Access usage metadata
print(f"Tokens used: {response.metadata['usage']}")
```

### OpenAI GPT

```python
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(
    api_key="your-api-key",
    model="gpt-4o"
)

response = await llm.complete(
    messages,
    temperature=0.7,
    max_tokens=1024
)
```

### Google Gemini

```python
from agenkit.adapters.llm import GeminiLLM

llm = GeminiLLM(
    api_key="your-api-key",
    model="gemini-2.0-flash-exp"
)

response = await llm.complete(messages, max_tokens=1024)
```

### AWS Bedrock

```python
from agenkit.adapters.llm import BedrockLLM

llm = BedrockLLM(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    profile_name="aws",  # or use IAM role
    region_name="us-east-1"
)

response = await llm.complete(messages, max_tokens=1024)
```

### Ollama (Local)

```python
from agenkit.adapters.llm import OllamaLLM

llm = OllamaLLM(
    model="llama2",
    base_url="http://localhost:11434"
)

response = await llm.complete(messages)
```

### LiteLLM (Any Provider)

```python
from agenkit.adapters.llm import LiteLLMLLM

# OpenAI via LiteLLM
llm = LiteLLMLLM(model="gpt-4", api_key="...")

# Azure OpenAI
llm = LiteLLMLLM(model="azure/gpt-4", api_key="...")

# Local Ollama
llm = LiteLLMLLM(model="ollama/llama2")

# All use the same interface!
```

## Streaming Responses

All adapters support streaming for real-time output:

```python
async for chunk in llm.stream(messages):
    print(chunk.content, end="", flush=True)
```

**Full example:**

```python
import asyncio
from agenkit.adapters.llm import OpenAILLM
from agenkit import Message

async def stream_example():
    llm = OpenAILLM(api_key="...")
    messages = [Message(role="user", content="Count from 1 to 10")]

    print("Streaming response: ", end="")
    async for chunk in llm.stream(messages):
        print(chunk.content, end="", flush=True)
    print()  # New line

asyncio.run(stream_example())
```

## Using LLMs with Agents

The real power comes from combining LLMs with Agenkit's agent patterns:

```python
from agenkit import Agent, Message
from agenkit.adapters.llm import AnthropicLLM

class ChatAgent:
    """Simple chat agent powered by an LLM."""

    def __init__(self, llm):
        self.llm = llm
        self.history = []

    async def chat(self, user_message: str) -> str:
        # Add user message to history
        self.history.append(Message(role="user", content=user_message))

        # Get LLM response
        response = await self.llm.complete(self.history)

        # Add to history
        self.history.append(response)

        return response.content

# Use it
agent = ChatAgent(AnthropicLLM(api_key="..."))
response = await agent.chat("Hello! What can you help with?")
```

**Swap providers without changing agent code:**

```python
# Use OpenAI instead
agent = ChatAgent(OpenAILLM(api_key="..."))

# Or Gemini
agent = ChatAgent(GeminiLLM(api_key="..."))

# Agent code stays the same!
```

## Advanced Features

### Accessing Provider-Specific Features

Use `unwrap()` to get the underlying client:

```python
llm = AnthropicLLM(api_key="...")

# Get the underlying AsyncAnthropic client
client = llm.unwrap()

# Use Anthropic-specific features
response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[...],
    # Anthropic-specific parameters
    stop_sequences=["Human:", "Assistant:"],
    top_k=40
)
```

### Error Handling

```python
from anthropic import APIError

try:
    response = await llm.complete(messages)
except APIError as e:
    print(f"Anthropic API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Fallback Pattern

```python
from agenkit.adapters.llm import AnthropicLLM, OpenAILLM

async def complete_with_fallback(messages):
    """Try Anthropic, fall back to OpenAI if it fails."""
    try:
        llm = AnthropicLLM(api_key="...")
        return await llm.complete(messages)
    except Exception as e:
        print(f"Anthropic failed ({e}), trying OpenAI...")
        llm = OpenAILLM(api_key="...")
        return await llm.complete(messages)
```

## API Reference

### LLM Base Interface

All adapters implement this interface:

```python
class LLM(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs
    ) -> Message:
        """Generate a completion."""

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs
    ) -> AsyncIterator[Message]:
        """Stream completion chunks."""

    @property
    def model(self) -> str:
        """Return the model identifier."""

    def unwrap(self) -> Any:
        """Get the underlying provider client."""
```

### Message Format

Agenkit uses a simple, consistent message format:

```python
Message(
    role="user",  # or "agent", "system"
    content="Hello!",
    metadata={}  # Optional metadata
)
```

**Response messages include metadata:**

```python
response = await llm.complete(messages)

print(response.role)      # "agent"
print(response.content)   # "Hello! How can I help?"
print(response.metadata)  # {"model": "...", "usage": {...}}
```

## Best Practices

### 1. Use Environment Variables for API Keys

```python
import os

llm = AnthropicLLM(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### 2. Set Timeouts for Production

```python
from agenkit.patterns import Task

# Task pattern provides timeout support
async with Task(agent, timeout=30.0) as task:
    result = await task.execute(messages)
```

### 3. Handle Rate Limits

```python
import asyncio
from anthropic import RateLimitError

async def complete_with_retry(llm, messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await llm.complete(messages)
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)
```

### 4. Log Usage Metrics

```python
response = await llm.complete(messages)

# Log token usage
if "usage" in response.metadata:
    usage = response.metadata["usage"]
    print(f"Prompt tokens: {usage.get('prompt_tokens')}")
    print(f"Completion tokens: {usage.get('completion_tokens')}")
    print(f"Total tokens: {usage.get('total_tokens')}")
```

### 5. Choose the Right Model

| Task | Recommended Models |
|------|-------------------|
| **Complex Reasoning** | Claude 3.5 Sonnet, GPT-4 |
| **Fast/Cheap** | Claude Haiku, GPT-3.5, Gemini Flash |
| **Long Context** | Claude 3.5 Sonnet (200K), GPT-4 Turbo (128K) |
| **Code Generation** | Claude 3.5 Sonnet, GPT-4, CodeLlama (Ollama) |
| **Local/Private** | Ollama (Llama 2/3, Mistral) |

## Examples

See the [examples/llm/](https://github.com/agenkit/agenkit/tree/main/examples/llm) directory for complete working examples:

- `anthropic_example.py` - Basic Anthropic usage
- `openai_example.py` - Basic OpenAI usage
- `swapping_providers.py` - Swapping between providers
- `streaming_example.py` - Real-time streaming
- `litellm_providers.py` - Using 100+ providers via LiteLLM
- `agent_with_llm.py` - Building agents with LLMs

## Related Documentation

- [Agent Patterns Guide](../guide/agent-patterns.md) - Learn about Agent vs Task vs Tool
- [Task Pattern](../patterns/task.md) - One-shot LLM execution with cleanup
- [Testing Guide](../../TESTING.md) - Testing LLM adapters
- [API Reference](../api/llm.md) - Complete API documentation

## FAQ

### Q: Which provider should I use?

**A:** It depends on your needs:

- **Best overall**: Claude 3.5 Sonnet (via Anthropic or Bedrock)
- **Fastest**: Gemini Flash, Claude Haiku
- **Cheapest**: GPT-3.5 Turbo, Claude Haiku
- **Most capable**: GPT-4, Claude 3.5 Sonnet
- **Local/Private**: Ollama with Llama 2/3

### Q: Can I use multiple providers in one application?

**A:** Yes! That's the point of the abstraction. Use different providers for different tasks, or implement fallback logic.

### Q: Do I need to change my code when swapping providers?

**A:** No! The interface is consistent. Just change the adapter initialization:

```python
# Before
llm = AnthropicLLM(api_key="...")

# After
llm = OpenAILLM(api_key="...")

# Everything else stays the same!
```

### Q: What if I need provider-specific features?

**A:** Use `unwrap()` to get the underlying client and access provider-specific APIs directly.

### Q: How do I test without hitting real APIs?

**A:** Use unit tests with mocks (see `tests/adapters/llm/`). All adapters have comprehensive test coverage with mocked responses.

## Next Steps

- **[Try the Examples](../../examples/llm/)** - Run the example scripts
- **[Read API Docs](../api/llm.md)** - Detailed API reference
- **[Build an Agent](../guide/agent-patterns.md)** - Combine LLMs with agent patterns
- **[Run Tests](../../TESTING.md)** - Test with your API keys
