# LLM Adapters for Agenkit Go

Minimal LLM interfaces for Agenkit, providing a consistent way to interact with any LLM provider.

## Design Principles

1. **Minimal**: Only 2 required methods (`Complete`, `Stream`)
2. **Flexible**: Accepts functional options for provider-specific parameters
3. **Consistent**: Works with Agenkit's `Message` interface
4. **Swappable**: Change providers without changing agent code
5. **Escape hatch**: `Unwrap()` for advanced provider features

## Supported Providers

- ✅ **OpenAI** (GPT-4, GPT-3.5, etc.) - via `go-openai`
- ✅ **Anthropic** (Claude 3.5, Claude 3, etc.) - native HTTP client

## Installation

```bash
# OpenAI support
go get github.com/sashabaranov/go-openai

# Anthropic support (no additional dependencies needed)
```

## Quick Start

### OpenAI

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/agenkit/agenkit-go/adapter/llm"
    "github.com/agenkit/agenkit-go/agenkit"
)

func main() {
    // Create adapter
    llmAdapter := llm.NewOpenAILLM("sk-...", "gpt-4-turbo")

    // Simple completion
    ctx := context.Background()
    messages := []*agenkit.Message{
        agenkit.NewMessage("user", "Hello!"),
    }

    response, err := llmAdapter.Complete(ctx, messages)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(response.Content)
}
```

### Anthropic

```go
// Create adapter
llmAdapter := llm.NewAnthropicLLM("sk-ant-...", "claude-3-5-sonnet-20241022")

// Use exactly the same way as OpenAI!
response, err := llmAdapter.Complete(ctx, messages)
```

## Usage Examples

### Streaming

```go
stream, err := llmAdapter.Stream(ctx, messages)
if err != nil {
    log.Fatal(err)
}

for chunk := range stream {
    fmt.Print(chunk.Content)
}
```

### Custom Parameters

```go
response, err := llmAdapter.Complete(
    ctx,
    messages,
    llm.WithTemperature(0.7),
    llm.WithMaxTokens(1024),
    llm.WithTopP(0.9),
    llm.WithExtra("frequency_penalty", 0.5), // OpenAI-specific
)
```

### Conversation History

```go
messages := []*agenkit.Message{
    agenkit.NewMessage("system", "You are a helpful assistant."),
    agenkit.NewMessage("user", "What is 2+2?"),
    agenkit.NewMessage("agent", "2+2 equals 4."),
    agenkit.NewMessage("user", "What about 3+3?"),
}

response, err := llmAdapter.Complete(ctx, messages)
```

### Provider Swapping

```go
// Choose provider at runtime
var llmAdapter llm.LLM

if provider == "openai" {
    llmAdapter = llm.NewOpenAILLM(apiKey, "gpt-4-turbo")
} else {
    llmAdapter = llm.NewAnthropicLLM(apiKey, "claude-3-5-sonnet-20241022")
}

// Rest of code is identical!
response, err := llmAdapter.Complete(ctx, messages)
```

## Interface

```go
type LLM interface {
    // Complete generates a single completion
    Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error)

    // Stream generates completion chunks
    Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error)

    // Model returns the model identifier
    Model() string

    // Unwrap returns the underlying provider client
    Unwrap() interface{}
}
```

## Options

### Common Options

```go
llm.WithTemperature(0.7)    // Sampling temperature (0.0-2.0)
llm.WithMaxTokens(1024)     // Maximum tokens to generate
llm.WithTopP(0.9)           // Nucleus sampling parameter
```

### Provider-Specific Options

Use `WithExtra()` for provider-specific parameters:

```go
// OpenAI
llm.WithExtra("frequency_penalty", 0.5)
llm.WithExtra("presence_penalty", 0.5)
llm.WithExtra("stop", []string{"END"})

// Anthropic
llm.WithExtra("stop_sequences", []string{"Human:", "Assistant:"})
```

## Message Format

Agenkit uses a universal message format:

```go
type Message struct {
    Role      string                 // "user", "agent", "system", "tool"
    Content   string                 // Message content
    Metadata  map[string]interface{} // Additional data
    Timestamp time.Time              // When message was created
}
```

### Role Mapping

**OpenAI:**

- `user` → `user`
- `agent` → `assistant`
- `system` → `system`
- `tool` → `tool`

**Anthropic:**

- `user` → `user`
- `agent` → `assistant`
- `system` → Separate `system` parameter
- `tool` → `assistant` (tools handled differently)

## Response Metadata

Responses include provider-specific metadata:

```go
response, _ := llmAdapter.Complete(ctx, messages)

// Access metadata
usage := response.Metadata["usage"].(map[string]interface{})
model := response.Metadata["model"].(string)
finishReason := response.Metadata["finish_reason"].(string) // OpenAI
stopReason := response.Metadata["stop_reason"].(string)     // Anthropic
```

## Error Handling

```go
response, err := llmAdapter.Complete(ctx, messages)
if err != nil {
    // Provider-specific errors
    // - API authentication errors
    // - Rate limit errors
    // - Network errors
    // - Invalid request errors
    log.Printf("LLM error: %v", err)
    return
}
```

For streaming, errors are signaled through metadata:

```go
for chunk := range stream {
    if errMsg, ok := chunk.Metadata["error"].(string); ok {
        log.Printf("Stream error: %s", errMsg)
        break
    }
    fmt.Print(chunk.Content)
}
```

## Advanced: Using Unwrap()

When you need provider-specific features:

```go
// OpenAI
openaiClient := llmAdapter.Unwrap().(*openai.Client)
// Now use OpenAI SDK directly

// Anthropic
httpClient := llmAdapter.Unwrap().(*http.Client)
// Use for custom API calls
```

⚠️ **Warning**: Using `Unwrap()` breaks provider portability!

## Testing

Mock the LLM interface for testing:

```go
type MockLLM struct {
    response *agenkit.Message
    err      error
}

func (m *MockLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...llm.CallOption) (*agenkit.Message, error) {
    return m.response, m.err
}

// Use in tests
mock := &MockLLM{
    response: agenkit.NewMessage("agent", "test response"),
}
```

## Examples

See the [`examples/llm`](../../examples/llm) directory for complete examples:

- `openai_example.go` - OpenAI usage patterns
- `anthropic_example.go` - Anthropic usage patterns
- `provider_swap_example.go` - Provider-agnostic code

Run examples:

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
go run examples/llm/openai_example.go

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
go run examples/llm/anthropic_example.go

# Provider swap
export LLM_PROVIDER=openai  # or anthropic
go run examples/llm/provider_swap_example.go
```

## Performance

- **Interface overhead**: Negligible (<1% in benchmarks)
- **Memory**: Single allocation per message
- **Streaming**: Zero-copy where possible

## Best Practices

1. **Code against the interface**, not concrete types:

   ```go
   func processWithLLM(llm llm.LLM, messages []*agenkit.Message) error {
       // Works with any provider!
   }
   ```

2. **Use functional options** for parameters:

   ```go
   response, err := llmAdapter.Complete(
       ctx,
       messages,
       llm.WithTemperature(0.7),
       llm.WithMaxTokens(1024),
   )
   ```

3. **Handle errors consistently**:

   ```go
   response, err := llmAdapter.Complete(ctx, messages)
   if err != nil {
       return fmt.Errorf("llm completion failed: %w", err)
   }
   ```

4. **Test with multiple providers** to ensure portability

5. **Only use Unwrap() when necessary** for provider-specific features

## Provider Comparison

| Feature | OpenAI | Anthropic |
|---------|--------|-----------|
| Streaming | ✅ | ✅ |
| System messages | ✅ | ✅ (separate parameter) |
| Tool calling | ✅ | ✅ |
| Vision | ✅ (GPT-4V) | ✅ (Claude 3) |
| Function calling | ✅ | ✅ |
| Max context | Up to 128K | Up to 200K |

## Contributing

To add a new provider:

1. Implement the `llm.LLM` interface
2. Follow the existing patterns (functional options, error handling)
3. Add tests
4. Add examples
5. Update this README

## License

Same as Agenkit (see root LICENSE file)
