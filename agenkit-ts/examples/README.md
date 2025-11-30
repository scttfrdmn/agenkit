# Agenkit TypeScript Examples

Comprehensive examples demonstrating all Agenkit patterns and features in TypeScript/JavaScript.

## Directory Structure

```
examples/
├── patterns/          # 11 core agentic patterns
├── adapters/          # LLM provider integrations (OpenAI, Anthropic, Ollama)
├── other/            # Middleware, transport, basic usage
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
| **Reflection** | [patterns/reflection-pattern.ts](patterns/reflection-pattern.ts) | Iterative self-critique and refinement for quality improvement |
| **ReAct** | [patterns/react-pattern.ts](patterns/react-pattern.ts) | Reasoning and Acting - thought/action/observation cycles |
| **Planning** | [patterns/planning-pattern.ts](patterns/planning-pattern.ts) | Multi-step task decomposition and execution |
| **Task** | [patterns/task-pattern.ts](patterns/task-pattern.ts) | Structured task management with state tracking |
| **Multiagent** | [patterns/multiagent-pattern.ts](patterns/multiagent-pattern.ts) | Coordination between multiple specialized agents |
| **Orchestration** | [patterns/orchestration-pattern.ts](patterns/orchestration-pattern.ts) | Complex workflow management with dynamic routing |
| **Conversational** | [patterns/conversational-pattern.ts](patterns/conversational-pattern.ts) | Multi-turn conversations with context management |
| **Memory Hierarchy** | [patterns/memory-hierarchy-pattern.ts](patterns/memory-hierarchy-pattern.ts) | Working memory + long-term semantic storage |
| **Agents as Tools** | [patterns/agents-as-tools-pattern.ts](patterns/agents-as-tools-pattern.ts) | Expose agents as callable tools for composition |
| **Reasoning with Tools** | [patterns/reasoning-with-tools-pattern.ts](patterns/reasoning-with-tools-pattern.ts) | Advanced tool use with multi-step reasoning |
| **Autonomous** | [patterns/autonomous-pattern.ts](patterns/autonomous-pattern.ts) | Self-directed agents with goal-seeking behavior |

## Adapter Examples

Real LLM provider integrations for production use:

| Adapter | File | Use Case |
|---------|------|----------|
| **OpenAI** | [adapters/openai-basic.ts](adapters/openai-basic.ts) | GPT-4, GPT-3.5-turbo integration |
| **Anthropic** | [adapters/anthropic-basic.ts](adapters/anthropic-basic.ts) | Claude integration (Claude 3.5 Sonnet, Opus, Haiku) |
| **Ollama** | [adapters/ollama-basic.ts](adapters/ollama-basic.ts) | Local LLM inference (Llama 2, Mistral, etc.) |

## Other Examples

| Category | File | Description |
|----------|------|-------------|
| **Basic Usage** | [other/basic-usage.ts](other/basic-usage.ts) | Simple agent creation and message processing |
| **LLM Integration** | [other/llm-integration.ts](other/llm-integration.ts) | Connecting patterns to real LLMs |
| **Middleware** | [other/middleware-example.ts](other/middleware-example.ts) | Retry, timeout, circuit breaker patterns |
| **Transport** | [other/transport-comparison.ts](other/transport-comparison.ts) | HTTP, WebSocket, gRPC comparison |

## Getting Started

### Prerequisites

- Node.js 18 or later
- npm or yarn
- For adapter examples: API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY) or Ollama installation
- For pattern examples: **No API keys required!** Uses mock agents

### Installation

```bash
# Install dependencies
npm install

# Build the project
npm run build
```

### Running Examples

```bash
# Pattern examples (no API keys needed)
npm run build && node dist/examples/patterns/reflection-pattern.js
npm run build && node dist/examples/patterns/react-pattern.js
npm run build && node dist/examples/patterns/planning-pattern.js

# Adapter examples (requires API keys or Ollama)
# OpenAI
export OPENAI_API_KEY="sk-..."
npm run build && node dist/examples/adapters/openai-basic.js

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
npm run build && node dist/examples/adapters/anthropic-basic.js

# Ollama (local, free)
# Install from https://ollama.ai then:
ollama pull llama2
npm run build && node dist/examples/adapters/ollama-basic.js

# Other examples
npm run build && node dist/examples/other/basic-usage.js
npm run build && node dist/examples/other/middleware-example.js
```

### Development Mode

For faster iteration during development:
```bash
# Watch mode (auto-rebuild on changes)
npm run watch

# In another terminal
node dist/examples/patterns/reflection-pattern.js
```

## Key Principles

### Pattern Examples Use Mock Agents

All pattern examples in `patterns/` use **mock agents** that simulate LLM behavior:

```typescript
/**
 * Mock agent - no API calls
 */
class CodeGeneratorAgent implements Agent {
  private iteration = 0;

  async process(message: Message): Promise<Message> {
    this.iteration++;
    // Simulated behavior for demonstration
    const code = this.generateMockCode(this.iteration);
    return createMessage('assistant', code);
  }
}
```

**Why mock agents?**
- ✅ Learn pattern mechanics without API costs
- ✅ Fast, deterministic, reproducible
- ✅ No external dependencies or API keys
- ✅ Focus on pattern logic, not LLM responses

### Swapping Mock Agents for Real LLMs

Once you understand a pattern, swap the mock agent for a real LLM:

```typescript
// Development: Mock agent (from pattern example)
const generator = new MockCodeGenerator();

// Production: Real LLM (Ollama - free, local)
const generator = new OllamaAgent({
  model: 'llama2',
  baseUrl: 'http://localhost:11434'
});

// Production: Real LLM (OpenAI - paid, cloud)
const generator = new OpenAIAgent({
  model: 'gpt-4',
  apiKey: process.env.OPENAI_API_KEY
});

// Pattern works identically with all agents!
const reflectionAgent = new ReflectionAgent(generator, critic, config);
```

The pattern orchestration remains **identical** - only the agents change.

## Learning Path

We recommend following this progression:

### 1. Start with Patterns (Mock Agents)
Learn pattern mechanics without external dependencies:
```bash
npm run build && node dist/examples/patterns/reflection-pattern.js
npm run build && node dist/examples/patterns/react-pattern.js
npm run build && node dist/examples/patterns/planning-pattern.js
npm run build && node dist/examples/patterns/multiagent-pattern.js
```

### 2. Explore Adapters (Real LLMs)

#### Local Development (Free)
Start with Ollama for local, free LLM access:
```bash
# Install Ollama: https://ollama.ai
ollama pull llama2

# Run Ollama example
npm run build && node dist/examples/adapters/ollama-basic.js
```

**Ollama advantages:**
- ✅ Completely free
- ✅ Runs locally (no internet required)
- ✅ Fast for development
- ✅ Privacy-preserving
- ✅ Multiple models available (Llama 2, Mistral, CodeLlama, etc.)

#### Cloud Providers (Paid)
Move to cloud providers when ready:
```bash
# OpenAI (GPT-4)
export OPENAI_API_KEY="sk-..."
npm run build && node dist/examples/adapters/openai-basic.js

# Anthropic (Claude 3.5 Sonnet)
export ANTHROPIC_API_KEY="sk-ant-..."
npm run build && node dist/examples/adapters/anthropic-basic.js
```

### 3. Production Features
Add resilience and observability:
```bash
npm run build && node dist/examples/other/middleware-example.js
npm run build && node dist/examples/other/transport-comparison.js
```

### 4. Advanced Patterns
Explore composition and specialized patterns:
```bash
npm run build && node dist/examples/patterns/autonomous-pattern.js
npm run build && node dist/examples/patterns/memory-hierarchy-pattern.js
npm run build && node dist/examples/patterns/orchestration-pattern.js
```

## Best Practices

### Async/Await
All agent operations are async:
```typescript
const result = await agent.process(message);
```

### Error Handling
Use try/catch for robust error handling:
```typescript
try {
  const result = await agent.process(message);
  console.log('Success:', result.content);
} catch (error) {
  console.error('Failed to process:', error);
}
```

### Type Safety
TypeScript provides full type safety:
```typescript
import { Agent, Message, createMessage } from 'agenkit-ts';

class MyAgent implements Agent {
  name(): string {
    return 'MyAgent';
  }

  async process(message: Message): Promise<Message> {
    // Type-safe implementation
    return createMessage('assistant', 'Response');
  }
}
```

### Middleware Composition
Stack middleware for production resilience:
```typescript
let agent: Agent = new MyBaseAgent();

// Add retry capability
agent = new RetryMiddleware(agent, { maxAttempts: 3 });

// Add timeout protection
agent = new TimeoutMiddleware(agent, { timeout: 30000 });

// Add circuit breaker
agent = new CircuitBreakerMiddleware(agent, cbConfig);
```

## Pattern Achievements (v0.31.0)

Agenkit TypeScript now has **full pattern parity** across all 4 languages (Python, Go, C++, Rust):

✅ **11/11 patterns implemented**
- All patterns use consistent APIs
- Mock agents for demonstration
- Production-ready implementations
- Comprehensive documentation

## Examples Statistics

- **Pattern Examples**: 11 (all use mock agents)
- **Adapter Examples**: 3 (OpenAI, Anthropic, Ollama)
- **Other Examples**: 4 (basic usage, LLM integration, middleware, transport)
- **Total**: 18 comprehensive examples

## Documentation Links

- **Main README**: [/README.md](../../README.md) - Project overview
- **API Documentation**: [/docs/API.md](../../docs/API.md) - Detailed API reference
- **Architecture**: [/ARCHITECTURE.md](../../ARCHITECTURE.md) - Design principles
- **Roadmap**: [/ROADMAP.md](../../ROADMAP.md) - Development status and plans
- **Python Examples**: [/examples/README.md](../../examples/README.md) - Python reference implementation

## Cross-Language Compatibility

All TypeScript examples are designed for cross-language interoperability:
- **gRPC Transport**: Communicate with Python/Go/C++/Rust agents
- **WebSocket Transport**: Real-time bidirectional messaging
- **Consistent APIs**: Same patterns work across all languages

Example: TypeScript agent ↔ Python agent via WebSocket:
```bash
# Terminal 1: Start Python agent server
python examples/transport/websocket_example.py

# Terminal 2: Connect with TypeScript client
npm run build && node dist/examples/other/transport-comparison.js
```

## Why TypeScript?

TypeScript brings several advantages to Agenkit:
- **Type Safety**: Catch errors at compile time
- **IDE Support**: Excellent autocomplete and inline documentation
- **Modern Async**: Native Promise/async-await support
- **npm Ecosystem**: Access to millions of packages
- **Browser Support**: Run agents in the browser (WASM coming soon)
- **Node.js Performance**: Fast execution with V8 engine

## Testing

Run the test suite:
```bash
npm test
```

All examples are production-ready and well-tested. See [tests/](../../tests/) for additional patterns.

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/agenkit/agenkit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/agenkit/agenkit/discussions)
- **Documentation**: [/docs](../../docs/)
- **Tests**: [/tests](../../tests/) - 137+ test examples

## Next Steps

1. **Run a pattern example**: Start with `reflection-pattern.ts`
2. **Understand the pattern**: Read the code comments and output
3. **Try Ollama**: Free, local LLM for development (`ollama-basic.ts`)
4. **Add a cloud provider**: OpenAI or Anthropic when ready
5. **Build something**: Combine patterns for your use case
6. **Add production features**: Middleware, error handling, observability

Happy building! 🚀
