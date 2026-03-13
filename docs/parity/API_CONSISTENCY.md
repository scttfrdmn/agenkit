# API Consistency Reference

Cross-language reference for constructor parameters, defaults, and token metadata conventions.

---

## Standard Constructor Parameters

All LLM adapters across all 6 languages accept the same logical parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | string | (env var) | Provider API key |
| `model` | string | see below | Model identifier |
| `max_tokens` | int | 4096 | Maximum tokens to generate |
| `temperature` | float | 1.0 (Anthropic) / 0.7 (OpenAI) | Sampling temperature |

Constructor patterns are idiomatic per language (structs, keyword args, etc.) — this is acceptable.

---

## Default Models

All adapters default to the same models:

| Provider | Default Model |
|----------|--------------|
| Anthropic | `claude-sonnet-4-6` |
| OpenAI | `gpt-4o` |

### Per-Language Files

| Language | Anthropic File | OpenAI File |
|----------|---------------|-------------|
| Python | `agenkit/adapters/llm/anthropic.py` | `agenkit/adapters/llm/openai.py` |
| Go | `agenkit-go/adapter/llm/anthropic.go` | `agenkit-go/adapter/llm/openai.go` |
| TypeScript | `agenkit-ts/src/llm/anthropic.ts` | `agenkit-ts/src/llm/openai.ts` |
| Rust | `agenkit-rust/src/adapters/anthropic.rs` | `agenkit-rust/src/adapters/openai.rs` |
| C++ | `agenkit-cpp/include/agenkit/adapters/claude_agent.hpp` | `agenkit-cpp/include/agenkit/adapters/openai_agent.hpp` |
| Zig | `agenkit-zig/src/adapter/anthropic.zig` | N/A |

---

## Default Values Table

| Parameter | Python | Go | TypeScript | Rust | C++ | Zig |
|-----------|--------|----|------------|------|-----|-----|
| Anthropic model | `claude-sonnet-4-6` | `claude-sonnet-4-6` | `claude-sonnet-4-6` | `claude-sonnet-4-6` | `claude-sonnet-4-6` | `claude-sonnet-4-6` |
| OpenAI model | `gpt-4o` | `gpt-4o` | `gpt-4o` | `gpt-4o` | `gpt-4o` | N/A |
| max_tokens | 4096 | 4096 | 4096 | 4096 | 4096 | 4096 |
| temperature (Anthropic) | 1.0 | — | 1.0 | 1.0 | 1.0 | — |
| temperature (OpenAI) | 1.0 | — | 0.7 | 0.7 | 0.7 | — |

---

## Token Metadata Field Naming Convention

All adapters return token usage in message metadata using these flat keys:

| Field | Type | Description |
|-------|------|-------------|
| `input_tokens` | int | Tokens in the input/prompt |
| `output_tokens` | int | Tokens in the generated response |
| `total_tokens` | int | input_tokens + output_tokens |

### Anthropic metadata example

```python
response.metadata = {
    "model": "claude-sonnet-4-6",
    "input_tokens": 42,
    "output_tokens": 128,
    "total_tokens": 170,
    "stop_reason": "end_turn",
    "id": "msg_...",
}
```

### OpenAI metadata example

```python
response.metadata = {
    "model": "gpt-4o",
    "input_tokens": 42,      # mapped from prompt_tokens
    "output_tokens": 128,    # mapped from completion_tokens
    "total_tokens": 170,
    "stop_reason": "stop",   # mapped from finish_reason
    "id": "chatcmpl-...",
}
```

---

## Stop Reason Normalization

All adapters normalize the stop/finish reason to `stop_reason` in metadata:

| Provider | Raw API Field | Normalized Field |
|----------|--------------|-----------------|
| Anthropic | `stop_reason` | `stop_reason` |
| OpenAI | `finish_reason` | `stop_reason` |

Common values: `"stop"`, `"end_turn"`, `"length"`, `"max_tokens"`, `"tool_use"`

---

## Language-Specific Notes

### Python
- `max_tokens` is a parameter on `complete()` and `stream()`, not the constructor
- OpenAI: `max_tokens=None` (model decides) is also accepted

### Go
- Model defaults are applied in the `NewXxxLLM` constructor
- Options are passed via functional options: `WithMaxTokens(n)`, `WithTemperature(t)`

### TypeScript
- Token metadata fields use snake_case keys to match all other languages
- `finishReason` (camelCase) is NOT used — always `stop_reason`

### Rust
- Config struct uses `Default` trait: `AnthropicConfig { api_key: "..".to_string(), ..Default::default() }`

### C++
- Config struct with member initializers: `ClaudeConfig config; config.api_key = "...";`

### Zig
- `AnthropicLLM.init(allocator, api_key, model)` — pass `""` for model to use default

---

## When to Update This Document

Update this document when:
1. Default model versions are bumped (e.g., new Claude/GPT release)
2. New metadata fields are added to response messages
3. New LLM provider adapters are added
4. Token counting conventions change

The source of truth is always the adapter source files listed above.
