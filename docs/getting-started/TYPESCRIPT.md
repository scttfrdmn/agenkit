# Getting Started with Agenkit (TypeScript)

**Target audience**: TypeScript/JavaScript developers new to Agenkit
**Time to first agent**: 15-30 minutes
**Prerequisites**: Node.js 22+, TypeScript 5+

---

## Installation

```bash
# Using npm
npm install agenkit

# Using yarn
yarn add agenkit

# Using pnpm
pnpm add agenkit

# Install optional LLM providers
npm install openai @anthropic-ai/sdk
```

---

## Your First Agent

Let's create a simple greeting agent:

```typescript
import { Agent, Message } from 'agenkit';

class GreetingAgent implements Agent {
  get name(): string {
    return 'greeting-agent';
  }

  async process(message: Message): Promise<Message> {
    const userContent = message.content;
    const greeting = `Hello! You said: ${userContent}`;

    return {
      role: 'assistant',
      content: greeting,
      metadata: { processed_by: this.name }
    };
  }
}

async function main() {
  const agent = new GreetingAgent();

  const message: Message = {
    role: 'user',
    content: 'Hi there!'
  };

  const response = await agent.process(message);
  console.log(`Agent: ${response.content}`);
  // Output: Agent: Hello! You said: Hi there!
}

main();
```

Run it:
```bash
npx tsx main.ts  # or: node main.js if compiled
```

---

## Production-Ready Agent with Middleware

Add resilience with retry, circuit breaker, and timeout middleware:

```typescript
import { Agent, Message } from 'agenkit';
import {
  RetryDecorator,
  CircuitBreakerDecorator,
  TimeoutDecorator
} from 'agenkit/middleware';

class ProductionAgent implements Agent {
  get name(): string {
    return 'production-agent';
  }

  async process(message: Message): Promise<Message> {
    // Simulate some processing
    await new Promise(resolve => setTimeout(resolve, 100));

    return {
      role: 'assistant',
      content: `Processed: ${message.content}`,
      metadata: { agent: this.name }
    };
  }
}

async function main() {
  const baseAgent = new ProductionAgent();

  // Wrap with middleware (v0.50.0 uses milliseconds)
  let agent: Agent = new RetryDecorator(baseAgent, {
    maxAttempts: 3,
    initialDelayMs: 100
  });

  agent = new CircuitBreakerDecorator(agent, {
    failureThreshold: 5,
    recoveryTimeoutMs: 30000
  });

  agent = new TimeoutDecorator(agent, {
    timeoutMs: 5000
  });

  const message: Message = {
    role: 'user',
    content: 'Hello production!'
  };

  const response = await agent.process(message);
  console.log(response.content);
}

main();
```

**Note**: TypeScript uses milliseconds for all timeout parameters (v0.50.0).

---

## Using LLM Adapters

### OpenAI Example

```typescript
import { Message } from 'agenkit';
import { OpenAILLM } from 'agenkit/llm';

async function main() {
  // Initialize LLM (validates parameters at construction)
  const llm = new OpenAILLM({
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4-turbo',
    temperature: 0.7,   // Validated: 0-2
    maxTokens: 1024     // Validated: >0
  });

  // Create conversation
  const messages: Message[] = [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'What is Agenkit?' }
  ];

  // Get completion
  const response = await llm.complete(messages);
  console.log(response.content);

  // Stream response
  for await (const chunk of llm.stream(messages)) {
    process.stdout.write(chunk.content);
  }
}

main();
```

### Anthropic Example

```typescript
import { AnthropicLLM } from 'agenkit/llm';

const llm = new AnthropicLLM({
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: 'claude-3-5-sonnet-20241022',
  temperature: 1.0,
  maxTokens: 4096
});
```

**Parameter Validation** (v0.50.0):
- `temperature`: 0.0 - 2.0 (validated at construction)
- `maxTokens`: > 0 (validated at construction)
- `topP`: 0.0 - 1.0 (validated at construction)

Invalid values throw `Error` immediately.

---

## Common Patterns

Agenkit provides **18 core patterns** for building AI agents (see the [Agent Patterns Book](../../agent-patterns-book) for comprehensive details). Here are three essential patterns to get started:

### 1. Reflection Pattern

**One-line**: Iterative self-improvement through draft-critique-refine loop

```typescript
import { Message } from 'agenkit';
import { ReflectionAgent } from 'agenkit/patterns';
import { OpenAILLM } from 'agenkit/llm';

async function main() {
  const llm = new OpenAILLM({ model: 'gpt-4-turbo' });

  const agent = new ReflectionAgent(llm, {
    maxIterations: 3,
    reflectionPrompt: 'Review and improve this response:'
  });

  const message: Message = {
    role: 'user',
    content: 'Explain async/await in TypeScript'
  };

  const response = await agent.process(message);
  console.log(response.content);
}

main();
```

### 2. ReAct Pattern

**One-line**: Reasoning + Acting with explicit thought-action-observation loop

```typescript
import { Message, Tool, ToolResult } from 'agenkit';
import { ReActAgent } from 'agenkit/patterns';
import { OpenAILLM } from 'agenkit/llm';

class SearchTool implements Tool {
  get name(): string {
    return 'search';
  }

  get description(): string {
    return 'Search for information';
  }

  get parameters(): Record<string, unknown> {
    return {
      query: {
        type: 'string',
        description: 'Search query'
      }
    };
  }

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const query = params.query as string;
    // Simulate search
    return {
      success: true,
      result: `Search results for: ${query}`
    };
  }
}

async function main() {
  const llm = new OpenAILLM({ model: 'gpt-4-turbo' });
  const tools = [new SearchTool()];

  const agent = new ReActAgent(llm, tools, {
    maxIterations: 5
  });

  const message: Message = {
    role: 'user',
    content: "What's the weather in Paris?"
  };

  const response = await agent.process(message);
  console.log(response.content);
}

main();
```

**Note**: Tool signatures use explicit `params: Record<string, unknown>` (v0.50.0+).

### 3. Sequential Pattern

**One-line**: Execute agents in order, passing outputs between stages

```typescript
import { Message } from 'agenkit';
import { SequentialAgent } from 'agenkit/patterns';

async function main() {
  // Create agent pipeline
  const agent = new SequentialAgent([
    new ResearchAgent(),
    new SummarizerAgent(),
    new EditorAgent()
  ]);

  const message: Message = {
    role: 'user',
    content: 'Research AI safety'
  };

  const finalResponse = await agent.process(message);
  console.log(finalResponse.content);
}

main();
```

**See all 18 patterns**: Refer to the [Agent Patterns Book](../../agent-patterns-book) for complete pattern descriptions, trade-offs, and when to use each pattern.

---

## Observability

### Basic Tracing with OpenTelemetry

```typescript
import { configureObservability } from 'agenkit/observability';

// Configure OpenTelemetry
configureObservability({
  serviceName: 'my-agent-service',
  exporterType: 'jaeger',
  jaegerEndpoint: 'http://localhost:14268/api/traces'
});

// Your agent automatically gets:
// - Span creation for each process() call
// - W3C Trace Context propagation
// - LLM call tracing
// - Error tracking
```

### View Traces in Jaeger

```bash
# Start Jaeger (Docker)
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest

# Open UI
open http://localhost:16686
```

---

## Advanced Features

### 1. Memory Hierarchy

```typescript
import { MemoryHierarchy, WorkingMemory, LongTermMemory } from 'agenkit/memory';

const memory = new MemoryHierarchy({
  working: new WorkingMemory({ capacity: 10 }),
  longTerm: new LongTermMemory({ storagePath: './memory.db' })
});

const agent = new ConversationalAgent({ memory });
```

### 2. Budget Tracking

```typescript
import { BudgetTracker } from 'agenkit/budget';

const tracker = new BudgetTracker({ maxCostUSD: 10.0 });
const agent = new BudgetAwareAgent(llm, { budget: tracker });
```

### 3. Safety Framework

```typescript
import { ContentFilter, RateLimiter } from 'agenkit/safety';

const agent = new SafeAgent(llm, {
  contentFilter: new ContentFilter({ blockPII: true }),
  rateLimiter: new RateLimiter({ rate: 10, maxWaitMs: 30000 })
});
```

---

## Common Pitfalls

### 1. Timeout Parameter Naming (v0.50.0)

```typescript
// OLD (v0.49.0):
new TimeoutDecorator(agent, { timeout: 30000 });

// NEW (v0.50.0):
new TimeoutDecorator(agent, { timeoutMs: 30000 });
```

### 2. Tool Execution Signature (v0.50.0)

```typescript
// OLD (v0.49.0):
async execute(...args: unknown[]): Promise<ToolResult>

// NEW (v0.50.0):
async execute(params: Record<string, unknown>): Promise<ToolResult>
```

### 3. Parameter Validation

```typescript
// This throws Error immediately (v0.50.0):
const llm = new OpenAILLM({ temperature: 3.0 }); // ❌ Error: temperature must be 0-2

// Valid range:
const llm = new OpenAILLM({ temperature: 0.7 }); // ✅ OK
```

### 4. Streaming Pattern

```typescript
// TypeScript uses AsyncGenerator (idiomatic):
for await (const chunk of llm.stream(messages)) {
  process.stdout.write(chunk.content);
}
```

---

## Next Steps

1. **Explore Patterns**: See the [Agent Patterns Book](../../agent-patterns-book) for all 18 patterns
2. **Read Architecture**: `ARCHITECTURE.md` explains design principles
3. **Check Examples**: `examples/typescript/` has production examples
4. **API Reference**: Coming soon in `docs/api-reference/typescript/`
5. **Migration Guide**: See `docs/MIGRATION_v0.50.0.md` for breaking changes

---

## Quick Reference

```typescript
// Core imports
import { Agent, Message, Tool, ToolResult } from 'agenkit';

// Middleware
import {
  RetryDecorator,
  TimeoutDecorator,
  CircuitBreakerDecorator,
  RateLimiterDecorator
} from 'agenkit/middleware';

// LLM adapters
import { OpenAILLM, AnthropicLLM, OllamaLLM } from 'agenkit/llm';

// Patterns
import {
  ReflectionAgent,
  ReActAgent,
  SequentialAgent,
  ParallelAgent
} from 'agenkit/patterns';

// Observability
import { configureObservability } from 'agenkit/observability';

// Memory & Safety
import { MemoryHierarchy } from 'agenkit/memory';
import { ContentFilter, RateLimiter } from 'agenkit/safety';
```

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026

For help: Open an issue at https://github.com/yourusername/agenkit/issues
