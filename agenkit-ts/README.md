# @agenkit/core

Minimal, composable interfaces for AI agents in TypeScript.

## Features

- **Minimal API**: Only 2 required methods per agent (`name`, `process`)
- **Type Safe**: Full TypeScript support with comprehensive type definitions
- **Composable**: Easy middleware pattern for retry, timeout, caching, etc.
- **Transport Agnostic**: HTTP, WebSocket, gRPC support
- **LLM Ready**: Built-in adapters for OpenAI, Anthropic (Claude), and OpenAI-compatible services (vLLM, llama.cpp, SGLang, etc.)
- **Production Ready**: Middleware for resilience, observability, and control

## Installation

```bash
npm install @agenkit/core
```

## Quick Start

### Local Agent

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

const agent = new LocalAgent({
  name: 'greeter',
  process: async (message) => ({
    role: 'assistant',
    content: `Hello, ${message.content}!`,
  }),
});

const response = await agent.process(createMessage('user', 'World'));
console.log(response.content); // "Hello, World!"
```

### OpenAI Agent

```typescript
import { OpenAIAgent } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
});

const response = await agent.process({
  role: 'user',
  content: 'What is the capital of France?',
});

console.log(response.content); // "The capital of France is Paris."
```

### Anthropic (Claude) Agent

```typescript
import { AnthropicAgent } from '@agenkit/core';

const agent = new AnthropicAgent({
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: 'claude-sonnet-4-20250514',
});

const response = await agent.process({
  role: 'user',
  content: 'Explain TypeScript in one sentence.',
});

console.log(response.content);
```

### OpenAI-Compatible Services (vLLM, llama.cpp, etc.)

```typescript
import { OpenAICompatibleAgent } from '@agenkit/core';

// vLLM local deployment
const agent = new OpenAICompatibleAgent({
  baseURL: 'http://localhost:8000/v1',
  model: 'meta-llama/Llama-2-7b-chat-hf',
  provider: 'vllm',
});

// llama.cpp server
const agent2 = new OpenAICompatibleAgent({
  baseURL: 'http://localhost:8080/v1',
  model: 'llama-2-7b-chat',
  provider: 'llamacpp',
});

const response = await agent.process({
  role: 'user',
  content: 'What is machine learning?',
});

console.log(response.content);
```

Supports: vLLM, llama.cpp, SGLang, TensorRT-LLM, OpenLLM, MLC LLM, TGI, Inferflow

### HTTP Transport

```typescript
import { HTTPAgent } from '@agenkit/core';

const agent = new HTTPAgent({
  baseUrl: 'http://localhost:8000',
});

const response = await agent.process({
  role: 'user',
  content: 'Hello',
});
```

### WebSocket Transport

```typescript
import { WebSocketAgent } from '@agenkit/core';

const agent = new WebSocketAgent({
  url: 'ws://localhost:8080',
  maxRetries: 5,
  pingInterval: 30000,
});

await agent.connect();

const response = await agent.process({
  role: 'user',
  content: 'Hello',
});

await agent.close();
```

### gRPC Transport

High-performance RPC with Protocol Buffers:

```typescript
import { GrpcAgent, GrpcServer } from '@agenkit/core';

// Client
const client = new GrpcAgent('my-service', {
  address: 'localhost:50051',
  timeout: 5000,
  useTLS: false,
});

const response = await client.process({
  role: 'user',
  content: 'Hello',
});

await client.close();

// Server
const server = new GrpcServer(myAgent, {
  address: '0.0.0.0:50051',
  useTLS: false,
});

await server.start();
// ... handle requests ...
await server.stop();
```

### Middleware

Apply retry, timeout, or custom middleware:

```typescript
import { LocalAgent, applyMiddleware, retry, timeout } from '@agenkit/core';

const baseAgent = new LocalAgent({
  name: 'flaky',
  process: async (msg) => {
    // May fail occasionally
    if (Math.random() < 0.3) throw new Error('Network error');
    return { role: 'assistant', content: 'Success!' };
  },
});

// Apply retry and timeout middleware
const robustAgent = applyMiddleware(baseAgent, [
  retry({ maxAttempts: 3, initialDelay: 1000 }),
  timeout({ timeout: 5000 }),
]);

const response = await robustAgent.process({
  role: 'user',
  content: 'Hello',
});
```

### Streaming

Stream responses for real-time interaction:

```typescript
import { OpenAIAgent } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
});

for await (const chunk of agent.processStream({
  role: 'user',
  content: 'Count from 1 to 10',
})) {
  process.stdout.write(chunk.content);
}
```

## Core Interfaces

### Agent

```typescript
interface Agent {
  name: string;
  process(message: Message): Promise<Message>;
  processStream?(message: Message): AsyncGenerator<Message>;
  capabilities?: string[];
}
```

### Message

```typescript
interface Message {
  role: string; // "user", "assistant", "system", "tool"
  content: unknown; // string, object, array, etc.
  metadata?: Record<string, unknown>;
  timestamp?: string; // ISO 8601
}
```

### Tool

```typescript
interface Tool {
  name: string;
  description: string;
  parametersSchema?: Record<string, unknown>;
  execute(params: Record<string, unknown>): Promise<ToolResult>;
}
```

## Adapters

- **LocalAgent**: Wrap TypeScript functions as agents
- **HTTPAgent**: Communicate over HTTP/REST
- **WebSocketAgent**: Real-time bidirectional communication
- **GrpcAgent**: High-performance gRPC transport ✨ NEW
- **OpenAIAgent**: OpenAI Chat Completion API (GPT-4, GPT-3.5)
- **AnthropicAgent**: Anthropic Messages API (Claude 3)

## Middleware

- **retry**: Automatic retries with exponential backoff
- **timeout**: Prevent long-running requests
- **circuitBreaker**: Fail fast when service is unhealthy
- **Custom**: Easy to implement your own

## Why Agenkit?

### Minimal

Only 2 required methods per agent. No complex inheritance, no framework lock-in.

### Composable

Middleware pattern allows easy wrapping for cross-cutting concerns.

### Type Safe

Full TypeScript support with comprehensive type definitions.

### Production Ready

Built-in resilience patterns and LLM integrations.

## Migration Guides

### Migrating to TypeScript

Choose your source language for detailed migration guide:

| From | Guide | Key Benefits |
|------|-------|-------------|
| **Python** | [MIGRATE_PYTHON_TO_TYPESCRIPT.md](../docs/MIGRATE_PYTHON_TO_TYPESCRIPT.md) | Similar async/await, ~2x faster, universal deployment |
| **Go** | [MIGRATE_GO_TO_TYPESCRIPT.md](../docs/MIGRATE_GO_TO_TYPESCRIPT.md) | Web/browser support, NPM ecosystem, universal code |
| **Rust** | [MIGRATE_RUST_TO_TYPESCRIPT.md](../docs/MIGRATE_RUST_TO_TYPESCRIPT.md) | Web deployment, easier maintenance, universal code |
| **C++** | [MIGRATE_CPP_TO_TYPESCRIPT.md](../docs/MIGRATE_CPP_TO_TYPESCRIPT.md) | Web deployment, cross-platform, simpler memory |
| **Zig** | [MIGRATE_ZIG_TO_TYPESCRIPT.md](../docs/MIGRATE_ZIG_TO_TYPESCRIPT.md) | Web deployment, GC simplification, universal code |

### Migrating from TypeScript

| To | Guide | Primary Use Case |
|----|-------|-----------------|
| **Python** | [MIGRATE_TYPESCRIPT_TO_PYTHON.md](../docs/MIGRATE_TYPESCRIPT_TO_PYTHON.md) | Data science, ML integration, rapid prototyping |
| **Go** | [MIGRATE_TYPESCRIPT_TO_GO.md](../docs/MIGRATE_TYPESCRIPT_TO_GO.md) | Backend services, true parallelism, better performance |
| **Rust** | [MIGRATE_TYPESCRIPT_TO_RUST.md](../docs/MIGRATE_TYPESCRIPT_TO_RUST.md) | Systems programming, WASM, 10-20x performance |
| **C++** | [MIGRATE_TYPESCRIPT_TO_CPP.md](../docs/MIGRATE_TYPESCRIPT_TO_CPP.md) | Native performance, legacy integration, 10-20x faster |
| **Zig** | [MIGRATE_TYPESCRIPT_TO_ZIG.md](../docs/MIGRATE_TYPESCRIPT_TO_ZIG.md) | Embedded systems, explicit control, no GC |

**See also:**
- [Language Profile: TypeScript](../docs/LANGUAGE_PROFILE_TYPESCRIPT.md) - Deep dive into TypeScript idioms and patterns
- [Migration Index](../docs/MIGRATION_INDEX.md) - Complete migration documentation hub

## Examples

See `examples/` directory for complete, runnable examples:

- **basic-usage.ts**: Simple getting started examples
- **middleware-example.ts**: Production resilience patterns (retry, timeout, circuit breaker) ✨ NEW
- **transport-comparison.ts**: HTTP vs WebSocket vs gRPC comparison ✨ NEW
- **llm-integration.ts**: OpenAI & Anthropic integration with best practices ✨ NEW

Run any example:

```bash
npx ts-node examples/middleware-example.ts
```

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Test
npm test

# Lint
npm run lint

# Format
npm run format
```

## License

MIT

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) in the main repository.
