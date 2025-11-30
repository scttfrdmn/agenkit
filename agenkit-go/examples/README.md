# Agenkit Go Examples

Comprehensive examples demonstrating all Agenkit patterns and features in Go.

## Directory Structure

```
examples/
├── patterns/          # 11 core agentic patterns
├── adapters/          # LLM provider integrations (llm/)
├── other/            # Middleware, transport, tools, memory, observability
└── README.md         # This file
```

## Pattern Examples

All pattern examples use **mock agents** (no API keys required) to demonstrate the pattern mechanics in isolation. This makes them:
- ✅ Runnable without any external dependencies
- ✅ Fast and deterministic for learning
- ✅ Adapter-agnostic (work with any LLM provider)
- ✅ Perfect for understanding pattern behavior

| Pattern | File | Description |
|---------|------|-------------|
| **Reflection** | [patterns/reflection_example.go](patterns/reflection_example.go) | Iterative self-critique and refinement for quality improvement |
| **ReAct** | [patterns/react_pattern.go](patterns/react_pattern.go) | Reasoning and Acting - thought/action/observation cycles |
| **Planning** | [patterns/planning_pattern.go](patterns/planning_pattern.go) | Multi-step task decomposition and execution |
| **Task** | [patterns/task_pattern.go](patterns/task_pattern.go) | Structured task management with state tracking |
| **Multiagent** | [patterns/multiagent_pattern.go](patterns/multiagent_pattern.go) | Coordination between multiple specialized agents |
| **Orchestration** | [patterns/orchestration_pattern.go](patterns/orchestration_pattern.go) | Complex workflow management with dynamic routing |
| **Conversational** | [patterns/conversational_pattern.go](patterns/conversational_pattern.go) | Multi-turn conversations with context management |
| **Memory Hierarchy** | [patterns/memory_hierarchy_pattern.go](patterns/memory_hierarchy_pattern.go) | Working memory + long-term semantic storage |
| **Agents as Tools** | [patterns/agents_as_tools_example.go](patterns/agents_as_tools_example.go) | Expose agents as callable tools for composition |
| **Reasoning with Tools** | [patterns/reasoning_with_tools_pattern.go](patterns/reasoning_with_tools_pattern.go) | Advanced tool use with multi-step reasoning |
| **Autonomous** | [patterns/autonomous_pattern.go](patterns/autonomous_pattern.go) | Self-directed agents with goal-seeking behavior |

## Adapter Examples

Real LLM provider integrations for production use:

| Adapter | File | Use Case |
|---------|------|----------|
| **OpenAI** | [llm/openai_example.go](llm/openai_example.go) | GPT-4, GPT-3.5-turbo integration |
| **Anthropic** | [llm/anthropic_example.go](llm/anthropic_example.go) | Claude integration (Claude 3.5 Sonnet, Opus, Haiku) |
| **Provider Swap** | [llm/provider_swap_example.go](llm/provider_swap_example.go) | Switching between providers without code changes |

**Note:** Ollama support available - see Python/TypeScript/C++/Rust examples for Ollama integration patterns.

## Other Examples

| Category | File | Description |
|----------|------|-------------|
| **Middleware** | [middleware/](middleware/) | Retry, circuit breaker, timeout, rate limiting, caching, batching, metrics |
| **Transport** | [transport/](transport/) | gRPC, WebSocket for cross-language communication |
| **Tools** | [tools/calculator_example.go](tools/calculator_example.go) | Tool creation and integration |
| **Memory** | [memory/memory_example.go](memory/memory_example.go) | Conversation memory and state management |
| **Observability** | [observability/observability_example.go](observability/observability_example.go) | OpenTelemetry tracing and Prometheus metrics |
| **Evaluation** | [evaluation/bayesian_optimization_example.go](evaluation/bayesian_optimization_example.go) | Hyperparameter tuning and optimization |
| **Composition** | [composition/](composition/) | Sequential, parallel, fallback, conditional patterns |
| **Basic** | [basic/main.go](basic/main.go) | Simple agent creation and message processing |

## Getting Started

### Prerequisites

- Go 1.21 or later
- For adapter examples: API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
- For pattern examples: **No API keys required!** Uses mock agents

### Running Examples

```bash
# Pattern examples (no API keys needed)
go run examples/patterns/reflection_example.go
go run examples/patterns/react_pattern.go
go run examples/patterns/planning_pattern.go

# Adapter examples (requires API keys)
export OPENAI_API_KEY="sk-..."
go run examples/llm/openai_example.go

export ANTHROPIC_API_KEY="sk-ant-..."
go run examples/llm/anthropic_example.go

# Middleware examples
go run examples/middleware/circuit_breaker_example.go
go run examples/middleware/retry_example.go

# Transport examples
go run examples/transport/grpc_example.go
go run examples/transport/websocket_example.go
```

## Key Principles

### Pattern Examples Use Mock Agents

All pattern examples in `patterns/` use **mock agents** that simulate LLM behavior:

```go
// Mock agent - no API calls
type MockCodeGenerator struct {
    iteration int
}

func (g *MockCodeGenerator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    // Simulated behavior for demonstration
    code := generateMockCode(g.iteration)
    return agenkit.NewMessage("assistant", code), nil
}
```

**Why mock agents?**
- ✅ Learn pattern mechanics without API costs
- ✅ Fast, deterministic, reproducible
- ✅ No external dependencies or API keys
- ✅ Focus on pattern logic, not LLM responses

### Swapping Mock Agents for Real LLMs

Once you understand a pattern, swap the mock agent for a real LLM:

```go
// Development: Mock agent (from pattern example)
generator := &MockCodeGenerator{}

// Production: Real LLM
generator := openai.NewAgent(openai.Config{
    Model:  "gpt-4",
    APIKey: os.Getenv("OPENAI_API_KEY"),
})

// Pattern works identically with both!
reflectionAgent := patterns.NewReflectionAgent(generator, critic, config)
```

The pattern orchestration remains **identical** - only the agents change.

## Learning Path

We recommend following this progression:

### 1. Start with Patterns (Mock Agents)
Learn pattern mechanics without external dependencies:
```bash
go run examples/patterns/reflection_example.go    # Iterative improvement
go run examples/patterns/react_pattern.go          # Reasoning + Acting
go run examples/patterns/planning_pattern.go       # Task decomposition
go run examples/patterns/multiagent_pattern.go     # Agent coordination
```

### 2. Explore Adapters (Real LLMs)

#### Local Development (Free)
Start with Ollama for local, free LLM access:
```bash
# Install Ollama: https://ollama.ai
ollama pull llama2

# See Python/TypeScript/C++/Rust examples for Ollama patterns
# Go support coming soon!
```

#### Cloud Providers (Paid)
Move to cloud providers when ready:
```bash
# OpenAI (GPT-4)
export OPENAI_API_KEY="sk-..."
go run examples/llm/openai_example.go

# Anthropic (Claude 3.5 Sonnet)
export ANTHROPIC_API_KEY="sk-ant-..."
go run examples/llm/anthropic_example.go
```

### 3. Production Features
Add resilience and observability:
```bash
go run examples/middleware/retry_example.go
go run examples/middleware/circuit_breaker_example.go
go run examples/observability/observability_example.go
```

### 4. Advanced Patterns
Explore composition and specialized patterns:
```bash
go run examples/patterns/autonomous_pattern.go
go run examples/patterns/memory_hierarchy_pattern.go
go run examples/composition/fallback_example.go
```

## Best Practices

### Error Handling
All examples follow idiomatic Go error handling:
```go
result, err := agent.Process(ctx, message)
if err != nil {
    return fmt.Errorf("failed to process: %w", err)
}
```

### Context Management
Use contexts for cancellation and timeouts:
```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

result, err := agent.Process(ctx, message)
```

### Middleware Composition
Stack middleware for production resilience:
```go
agent = middleware.WithRetry(agent, retryConfig)
agent = middleware.WithTimeout(agent, 30*time.Second)
agent = middleware.WithCircuitBreaker(agent, cbConfig)
```

### Testing
All examples are production-ready and well-tested. See tests for additional patterns:
```bash
go test ./examples/...
```

## Pattern Achievements (v0.31.0)

Agenkit Go now has **full pattern parity** across all 4 languages (Python, TypeScript, C++, Rust):

✅ **11/11 patterns implemented**
- All patterns use consistent APIs
- Mock agents for demonstration
- Production-ready implementations
- Comprehensive documentation

## Examples Statistics

- **Pattern Examples**: 11 (all use mock agents)
- **Adapter Examples**: 3 (OpenAI, Anthropic, provider swap)
- **Middleware Examples**: 7 (retry, timeout, circuit breaker, rate limiter, caching, batching, metrics)
- **Transport Examples**: 2 (gRPC, WebSocket)
- **Other Examples**: 5 (tools, memory, observability, evaluation, composition)
- **Total**: 28 comprehensive examples

## Documentation Links

- **Main README**: [/README.md](../../README.md) - Project overview
- **API Documentation**: [/docs/API.md](../../docs/API.md) - Detailed API reference
- **Architecture**: [/ARCHITECTURE.md](../../ARCHITECTURE.md) - Design principles
- **Roadmap**: [/ROADMAP.md](../../ROADMAP.md) - Development status and plans
- **Python Examples**: [/examples/README.md](../../examples/README.md) - Python reference implementation

## Cross-Language Compatibility

All Go examples are designed for cross-language interoperability:
- **gRPC Transport**: Communicate with Python/TypeScript/C++/Rust agents
- **WebSocket Transport**: Real-time bidirectional messaging
- **Consistent APIs**: Same patterns work across all languages

Example: Python agent ↔ Go agent via gRPC:
```bash
# Terminal 1: Start Python agent server
python examples/transport/grpc_example.py

# Terminal 2: Connect with Go client
go run examples/transport/grpc_example.go
```

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/agenkit/agenkit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/agenkit/agenkit/discussions)
- **Documentation**: [/docs](../../docs/)
- **Tests**: [/tests](../../tests/) - 137+ test examples

## Next Steps

1. **Run a pattern example**: Start with `reflection_example.go`
2. **Understand the pattern**: Read the code comments and output
3. **Try an adapter**: Connect to Ollama (other languages) or OpenAI/Anthropic
4. **Build something**: Combine patterns for your use case
5. **Add production features**: Middleware, observability, error handling

Happy building! 🚀
