# TypeScript API Reference

Complete API documentation for Agenkit TypeScript implementation.

## Official Documentation

TypeScript API documentation is generated using TypeDoc and published with each release.

[📚 View TypeScript API Documentation](https://agenkit.dev/ts-api/){ .md-button .md-button--primary }

---

## Quick Start

### Installation

```bash
npm install @agenkit/core
# or
yarn add @agenkit/core
# or
pnpm add @agenkit/core
```

### Basic Example

```typescript
import { Agent, Message } from '@agenkit/core';

class EchoAgent implements Agent {
  name(): string {
    return 'echo-agent';
  }

  capabilities(): string[] {
    return ['echo', 'simple'];
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Echo: ${message.content}`,
      metadata: {}
    };
  }

  introspect() {
    return {
      name: this.name(),
      capabilities: this.capabilities(),
      patterns: [],
      version: '1.0.0'
    };
  }
}

// Use the agent
const agent = new EchoAgent();
const response = await agent.process({
  role: 'user',
  content: 'Hello!',
  metadata: {}
});

console.log(response.content); // "Echo: Hello!"
```

---

## Core Interfaces

### Agent

The core interface that all agents must implement.

```typescript
interface Agent {
  /**
   * Returns the agent's unique identifier
   */
  name(): string;

  /**
   * Returns the agent's capabilities
   */
  capabilities(): string[];

  /**
   * Processes a message and returns a response
   */
  process(message: Message): Promise<Message>;

  /**
   * Returns agent metadata for introspection
   */
  introspect(): IntrospectionResult;
}
```

### Message

Standard message format for agent communication.

```typescript
interface Message {
  /** Message role: 'system' | 'user' | 'assistant' */
  role: string;

  /** Message content */
  content: string;

  /** Optional metadata */
  metadata?: Record<string, any>;

  /** Optional tool calls */
  toolCalls?: ToolCall[];

  /** Optional tool results */
  toolResults?: ToolResult[];
}
```

### Tool

Interface for tools that agents can use.

```typescript
interface Tool {
  /** Tool name */
  name(): string;

  /** Tool description for LLMs */
  description(): string;

  /** Execute the tool */
  execute(params: Record<string, any>): Promise<ToolResult>;
}
```

### ToolResult

Result from tool execution.

```typescript
interface ToolResult {
  /** Whether execution succeeded */
  success: boolean;

  /** Result data */
  data?: any;

  /** Error message if failed */
  error?: string;
}
```

---

## Composition Patterns

### SequentialAgent

Execute agents in sequence.

```typescript
import { SequentialAgent } from '@agenkit/core/composition';

const pipeline = new SequentialAgent([
  agent1,
  agent2,
  agent3
]);

const result = await pipeline.process(message);
```

### ParallelAgent

Execute agents concurrently.

```typescript
import { ParallelAgent } from '@agenkit/core/composition';

const parallel = new ParallelAgent([
  agent1,
  agent2,
  agent3
]);

const result = await parallel.process(message);
```

### ConditionalAgent

Route based on conditions.

```typescript
import { ConditionalAgent } from '@agenkit/core/composition';

const conditional = new ConditionalAgent(
  (message) => message.content.includes('urgent'),
  urgentAgent,
  normalAgent
);

const result = await conditional.process(message);
```

---

## Agent Patterns

### ConversationalAgent

Multi-turn conversations with memory.

```typescript
import { ConversationalAgent } from '@agenkit/core/patterns';
import { OpenAIAdapter } from '@agenkit/core/adapters';

const agent = new ConversationalAgent({
  llm: new OpenAIAdapter({ apiKey: process.env.OPENAI_API_KEY }),
  systemPrompt: 'You are a helpful assistant.',
  maxHistory: 10
});

const response1 = await agent.process({
  role: 'user',
  content: "Hi, I'm Alice",
  metadata: {}
});

const response2 = await agent.process({
  role: 'user',
  content: "What's my name?",
  metadata: {}
});
// Agent remembers "Alice"
```

### ReActAgent

Reasoning + Acting pattern with tools.

```typescript
import { ReActAgent } from '@agenkit/core/patterns';
import { OpenAIAdapter } from '@agenkit/core/adapters';

const agent = new ReActAgent({
  llm: new OpenAIAdapter({ apiKey: process.env.OPENAI_API_KEY }),
  tools: [searchTool, calculatorTool],
  maxIterations: 5
});

const result = await agent.process({
  role: 'user',
  content: 'What is 15% of 200?',
  metadata: {}
});
```

### ReflectionAgent

Self-critique and revision loop.

```typescript
import { ReflectionAgent } from '@agenkit/core/patterns';

const agent = new ReflectionAgent({
  agent: writerAgent,
  critic: reviewerAgent,
  maxIterations: 3
});

const result = await agent.process(message);
```

---

## LLM Adapters

### OpenAI

```typescript
import { OpenAIAdapter } from '@agenkit/core/adapters';

const llm = new OpenAIAdapter({
  apiKey: process.env.OPENAI_API_KEY,
  model: 'gpt-4'
});

const response = await llm.generate(message);
```

### Anthropic

```typescript
import { AnthropicAdapter } from '@agenkit/core/adapters';

const llm = new AnthropicAdapter({
  apiKey: process.env.ANTHROPIC_API_KEY,
  model: 'claude-3-5-sonnet-20241022'
});

const response = await llm.generate(message);
```

### Bedrock

```typescript
import { BedrockAdapter } from '@agenkit/core/adapters';

const llm = new BedrockAdapter({
  region: 'us-east-1',
  model: 'anthropic.claude-3-sonnet-20240229-v1:0'
});

const response = await llm.generate(message);
```

### Gemini

```typescript
import { GeminiAdapter } from '@agenkit/core/adapters';

const llm = new GeminiAdapter({
  apiKey: process.env.GEMINI_API_KEY,
  model: 'gemini-pro'
});

const response = await llm.generate(message);
```

---

## Middleware

### RetryMiddleware

Automatic retries with exponential backoff.

```typescript
import { RetryMiddleware } from '@agenkit/core/middleware';

const agent = new RetryMiddleware(baseAgent, {
  maxRetries: 3,
  backoffFactor: 2.0
});
```

### TimeoutMiddleware

Timeout handling.

```typescript
import { TimeoutMiddleware } from '@agenkit/core/middleware';

const agent = new TimeoutMiddleware(baseAgent, {
  timeout: 30000 // 30 seconds
});
```

### CircuitBreakerMiddleware

Circuit breaker pattern.

```typescript
import { CircuitBreakerMiddleware } from '@agenkit/core/middleware';

const agent = new CircuitBreakerMiddleware(baseAgent, {
  failureThreshold: 5,
  recoveryTimeout: 60000
});
```

---

## Reasoning Techniques

### Chain-of-Thought

```typescript
import { ChainOfThought } from '@agenkit/core/techniques/reasoning';

const cot = new ChainOfThought({
  llm: openaiAdapter,
  promptTemplate: "Let's solve this step by step:\n{query}",
  maxSteps: 5
});

const result = await cot.process(message);
console.log(result.metadata.reasoning_steps);
```

### Tree-of-Thought

```typescript
import { TreeOfThought } from '@agenkit/core/techniques/reasoning';

const tot = new TreeOfThought({
  agent: baseAgent,
  branchingFactor: 3,
  maxDepth: 4,
  strategy: 'best-first'
});

const result = await tot.process(message);
```

### Self-Consistency

```typescript
import { SelfConsistency } from '@agenkit/core/techniques/reasoning';

const sc = new SelfConsistency({
  agent: cotAgent,
  numSamples: 7,
  votingStrategy: 'majority'
});

const result = await sc.process(message);
```

---

## Observability

### Tracing

```typescript
import { TracingMiddleware } from '@agenkit/core/observability';
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';

const provider = new NodeTracerProvider();
provider.register();

const agent = new TracingMiddleware(baseAgent, {
  tracerName: 'my-service'
});
```

### Metrics

```typescript
import { MetricsMiddleware } from '@agenkit/core/observability';

const agent = new MetricsMiddleware(baseAgent, {
  prefix: 'agenkit_',
  labels: { service: 'my-service' }
});
```

---

## Transport

### HTTP Server

```typescript
import { HTTPAgent } from '@agenkit/core/transport';
import express from 'express';

const app = express();
const httpAgent = new HTTPAgent(agent);

app.post('/agent', httpAgent.handler());
app.listen(8080);
```

### HTTP Client

```typescript
import { HTTPClient } from '@agenkit/core/transport';

const remoteAgent = new HTTPClient('http://localhost:8080/agent');
const result = await remoteAgent.process(message);
```

---

## Type Safety

Agenkit TypeScript is fully typed with TypeScript 5.3+. Import types as needed:

```typescript
import type {
  Agent,
  Message,
  Tool,
  ToolResult,
  IntrospectionResult
} from '@agenkit/core';
```

---

## Building Documentation Locally

To generate TypeDoc documentation locally:

```bash
cd agenkit-ts

# Install dependencies
npm install

# Generate docs
npm run docs

# Output will be in ./docs directory
# Open docs/index.html in your browser
```

---

## IDE Integration

### VS Code

Full IntelliSense support with type hints:

1. Install the TypeScript extension (usually built-in)
2. Hover over any type/function for inline documentation
3. Use `Ctrl+Space` for autocomplete

### WebStorm / IntelliJ IDEA

Built-in TypeScript support:

1. Hover over types for documentation
2. `Ctrl+Q` (Windows/Linux) or `F1` (Mac) for quick documentation
3. `Ctrl+B` to jump to definition

---

## Examples

Comprehensive TypeScript examples are available in the repository:

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-ts/examples
```

Examples include:
- Basic agents
- Composition patterns
- ReAct with tools
- Conversational agents
- HTTP/gRPC servers
- Production middleware

---

## Testing

Agenkit TypeScript uses Vitest for testing:

```bash
# Run tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage
```

---

## Contributing

Help improve TypeScript implementation:

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Improve docs**: Add TSDoc comments to code
3. **Add examples**: [Submit PR](https://github.com/scttfrdmn/agenkit/pulls)

---

## See Also

- **[Python API Reference](python.md)**: Python implementation
- **[Go API Reference](go.md)**: Go implementation
- **[Cross-Language Guide](../guides/cross-language.md)**: Language interop
- **[TypeScript README](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-ts/README.md)**: TypeScript-specific features

---

**Last Updated**: December 2025
**Node.js Version**: 18.0.0+
**TypeScript Version**: 5.3+
**Agenkit Version**: 0.43.1+
