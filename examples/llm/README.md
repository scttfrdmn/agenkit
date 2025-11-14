# LLM Adapter Examples

Complete, runnable examples for using Agenkit's LLM adapters.

## Prerequisites

```bash
# Install Agenkit with LLM adapters
pip install agenkit[llm]

# Or install specific providers
pip install agenkit anthropic openai google-genai boto3 ollama litellm
```

## API Key Setup

Create a `.env` file in the project root:

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-...

# Google Gemini
GEMINI_API_KEY=...

# AWS (for Bedrock)
AWS_PROFILE=aws
# or
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1
```

## Examples

### Basic Provider Usage

- **[anthropic_example.py](anthropic_example.py)** - Anthropic Claude usage
  - Simple completion
  - Streaming responses
  - Temperature and token control
  - Usage metadata

- **[openai_example.py](openai_example.py)** - OpenAI GPT usage
  - GPT-4 completions
  - Streaming
  - Error handling
  - Token usage tracking

### Advanced Patterns

- **[swapping_providers.py](swapping_providers.py)** - Provider swapping
  - Switch between providers with one line
  - Compare responses
  - Fallback pattern
  - A/B testing

- **[streaming_example.py](streaming_example.py)** - Real-time streaming
  - Stream tokens as they generate
  - Show progress indicators
  - Handle streaming errors

### Multi-Provider

- **[litellm_providers.py](litellm_providers.py)** - 100+ providers via LiteLLM
  - OpenAI via LiteLLM
  - Azure OpenAI
  - Local Ollama
  - Provider-agnostic code

### Agent Integration

- **[agent_with_llm.py](agent_with_llm.py)** - Building agents with LLMs
  - Conversational agents
  - State management
  - Provider swapping in agents
  - Production patterns

## Running Examples

```bash
# Run any example
python examples/llm/anthropic_example.py

# With environment variables
ANTHROPIC_API_KEY=sk-ant-... python examples/llm/anthropic_example.py
```

## What's Demonstrated

Each example shows:
- ✅ Proper async/await usage
- ✅ Environment variable handling
- ✅ Error handling
- ✅ Best practices
- ✅ Usage metadata tracking
- ✅ Clean, production-ready code

## Next Steps

- Read the [LLM Adapters Guide](../../docs-site/features/llm-adapters.md)
- Check the [API Reference](../../docs-site/api/llm.md)
- Review the [Testing Guide](../../TESTING.md)
