# Getting Started with Agenkit TypeScript

A beginner-friendly guide to building AI agents with TypeScript.

## Table of Contents

- [Installation](#installation)
- [Your First Agent](#your-first-agent)
- [Understanding Messages](#understanding-messages)
- [TypeScript Configuration](#typescript-configuration)
- [Using LocalAgent](#using-localagent)
- [Async/Await Patterns](#asyncawait-patterns)
- [Working with LLMs](#working-with-llms)
- [Error Handling](#error-handling)
- [Adding Middleware](#adding-middleware)
- [Testing with Vitest](#testing-with-vitest)
- [Next Steps](#next-steps)

---

## Installation

### Prerequisites

You need Node.js 22 or later and TypeScript 5 or later:

```bash
node --version
# Should output: v22.x.x or higher

tsc --version
# Should output: Version 5.x.x or higher
```

If you need Node.js, download it from [nodejs.org](https://nodejs.org/).

### Install Agenkit

```bash
# Using npm (recommended)
npm install @agenkit/core

# Using yarn
yarn add @agenkit/core

# Using pnpm
pnpm add @agenkit/core
```

### Install Optional LLM Providers

```bash
# OpenAI
npm install openai

# Anthropic
npm install @anthropic-ai/sdk

# For all providers
npm install openai @anthropic-ai/sdk
```

### Verify Installation

Create a quick test file:

```typescript
import { createMessage } from '@agenkit/core';

const msg = createMessage('user', 'Hello!');
console.log(msg.role);    // "user"
console.log(msg.content); // "Hello!"
console.log(msg.timestamp); // ISO 8601 timestamp
```

Run it:

```bash
npx tsx verify.ts
```

---

## Your First Agent

Let's build a simple echo agent that responds to messages.

### Step 1: Create the Project

```bash
mkdir my-first-agent
cd my-first-agent
npm init -y
npm install @agenkit/core typescript tsx
```

### Step 2: Write the Agent Code

Create `src/main.ts`:

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

// Create an echo agent using LocalAgent
const echoAgent = new LocalAgent({
  name: 'echo-agent',
  process: async (message) => ({
    role: 'assistant',
    content: `Echo: ${message.content}`,
    metadata: { processed_by: 'echo-agent' },
  }),
});

async function main(): Promise<void> {
  console.log('=== My First Agent ===\n');

  const message = createMessage('user', 'Hello, agent!');
  console.log(`User: ${message.content}`);

  const response = await echoAgent.process(message);
  console.log(`Agent: ${response.content}`);
  // Output: Agent: Echo: Hello, agent!
}

main().catch(console.error);
```

### Step 3: Run the Agent

```bash
npx tsx src/main.ts
```

**Output:**
```
=== My First Agent ===

User: Hello, agent!
Agent: Echo: Hello, agent!
```

**Congratulations!** You've built your first AI agent with TypeScript.

---

## Understanding Messages

Messages are the core data structure in Agenkit. Every agent interaction uses messages.

### Message Structure

A message has four fields:

1. **role** - Who sent the message (`"user"`, `"assistant"`, `"system"`, `"tool"`)
2. **content** - The message content (string, object, or any serializable data)
3. **metadata** - Optional key-value pairs for session tracking, tracing, etc.
4. **timestamp** - ISO 8601 timestamp (auto-generated if not provided)

```typescript
interface Message {
  role: string;
  content: unknown;
  metadata?: Record<string, unknown>;
  timestamp?: string;
}
```

### Creating Messages

#### Using createMessage (Recommended)

```typescript
import { createMessage } from '@agenkit/core';

// Positional syntax (most common)
const msg = createMessage('user', 'Hello!');

// Object syntax (more explicit)
const msg2 = createMessage({
  role: 'user',
  content: 'Hello!',
  metadata: { session_id: 'abc-123' },
});
```

#### Using createValidatedMessage

When you need input validation:

```typescript
import { createValidatedMessage } from '@agenkit/core';

// Validates role, content size (max 16MB), and metadata constraints
const msg = createValidatedMessage('user', 'Hello!', {
  session_id: 'abc-123',
  priority: 5,
});
```

Validation rules:
- `role`: non-empty, max 20 characters, must be one of: `user`, `assistant`, `system`, `tool`, `agent`
- `content`: max 16MB
- `metadata`: max 100 keys, each key max 50 characters, each value max 16MB

#### Object Literals

You can also use plain object literals:

```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
  role: 'user',
  content: 'Hello!',
  metadata: { session_id: 'abc-123' },
};
```

### Message Roles

| Role | When to Use |
|------|-------------|
| `"user"` | Input from a human user |
| `"assistant"` | Output from an agent or LLM |
| `"system"` | Instructions or context for the agent |
| `"tool"` | Results from tool execution |

### Structured Content

Content can be any JSON-serializable value, not just strings:

```typescript
// Text message
const textMsg = createMessage('user', 'What is 2 + 2?');

// Structured message (for tool results, multimodal content, etc.)
const structuredMsg = createMessage('tool', {
  action: 'search',
  results: ['result1', 'result2'],
  count: 2,
});

// Array content
const arrayMsg = createMessage('user', [
  { type: 'text', text: 'Describe this image:' },
  { type: 'image_url', url: 'https://example.com/image.jpg' },
]);
```

### Reading Messages

```typescript
const response = await agent.process(message);

// Get string content
if (typeof response.content === 'string') {
  console.log(`Response: ${response.content}`);
}

// Get metadata
const sessionId = response.metadata?.session_id;
console.log(`Session: ${sessionId}`);

// Check role
if (response.role === 'assistant') {
  console.log('Got agent response');
}
```

---

## TypeScript Configuration

Agenkit TypeScript requires a well-configured `tsconfig.json` for the best experience.

### Recommended tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "exactOptionalPropertyTypes": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### Key Settings Explained

- `"strict": true` - Enables all strict type checks; catches bugs at compile time
- `"exactOptionalPropertyTypes": true` - Prevents assigning `undefined` to optional properties explicitly
- `"noUncheckedIndexedAccess": true` - Array/object indexing returns `T | undefined` instead of `T`
- `"module": "Node16"` - Correct module resolution for modern Node.js with ESM support

### package.json Setup

For ESM projects:

```json
{
  "name": "my-agent",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/main.js",
    "dev": "tsx src/main.ts",
    "test": "vitest run"
  },
  "dependencies": {
    "@agenkit/core": "^0.75.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "tsx": "^4.0.0",
    "vitest": "^2.0.0"
  }
}
```

---

## Using LocalAgent

`LocalAgent` is the simplest way to create agents — wrap any async function:

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

// Basic usage
const greeter = new LocalAgent({
  name: 'greeter',
  process: async (message) => ({
    role: 'assistant',
    content: `Hello, ${message.content}!`,
  }),
});

// With capabilities and streaming
const advancedAgent = new LocalAgent({
  name: 'advanced',
  capabilities: ['text-generation', 'streaming'],
  process: async (message) => ({
    role: 'assistant',
    content: `Processed: ${message.content}`,
    metadata: { model: 'local', latency_ms: 0 },
  }),
  processStream: async function* (message) {
    const words = `Streaming: ${message.content}`.split(' ');
    for (const word of words) {
      yield { role: 'assistant', content: word + ' ' };
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
  },
});

const response = await greeter.process(createMessage('user', 'World'));
console.log(response.content); // "Hello, World!"
```

### LocalAgent Configuration

```typescript
interface LocalAgentConfig {
  /** Agent identifier */
  name: string;

  /** Required: function that processes messages */
  process: (message: Message) => Promise<Message>;

  /** Optional: streaming support via AsyncGenerator */
  processStream?: (message: Message) => AsyncGenerator<Message, void, undefined>;

  /** Optional: list of capability strings */
  capabilities?: string[];
}
```

### Implementing the Agent Interface Directly

For more control, implement the `Agent` interface:

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';

class GreetingAgent implements Agent {
  readonly name = 'greeting-agent';
  readonly capabilities = ['greeting', 'text-generation'];

  async process(message: Message): Promise<Message> {
    const userText = typeof message.content === 'string'
      ? message.content
      : JSON.stringify(message.content);

    return createMessage('assistant', `Hello! You said: ${userText}`, {
      processed_by: this.name,
    });
  }

  // Optional: implement streaming
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    const words = `Hello! You said: ${message.content}`.split(' ');
    for (const word of words) {
      yield { role: 'assistant', content: word + ' ' };
    }
  }
}

const agent = new GreetingAgent();
const response = await agent.process(createMessage('user', 'Hi there!'));
console.log(response.content); // "Hello! You said: Hi there!"
```

---

## Async/Await Patterns

Agenkit is built around native TypeScript async/await. Every agent operation is asynchronous.

### Basic Async/Await

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

const agent = new LocalAgent({
  name: 'async-agent',
  process: async (message) => {
    // Simulate async work (database query, API call, etc.)
    const result = await fetchFromDatabase(message.content as string);

    return {
      role: 'assistant',
      content: result,
    };
  },
});

// Always await agent.process()
const response = await agent.process(createMessage('user', 'query'));
```

### Concurrent Processing with Promise.all

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

const agent = new LocalAgent({
  name: 'processor',
  process: async (msg) => ({ role: 'assistant', content: `Processed: ${msg.content}` }),
});

// Process multiple messages concurrently
const messages = [
  createMessage('user', 'Query 1'),
  createMessage('user', 'Query 2'),
  createMessage('user', 'Query 3'),
];

const responses = await Promise.all(
  messages.map((msg) => agent.process(msg))
);

responses.forEach((r) => console.log(r.content));
```

### Sequential Processing

```typescript
// Process messages one after another, where each depends on the previous
async function processSequentially(
  agent: Agent,
  messages: Message[]
): Promise<Message[]> {
  const responses: Message[] = [];

  for (const message of messages) {
    const response = await agent.process(message);
    responses.push(response);
  }

  return responses;
}
```

### Streaming Responses

```typescript
import { OpenAIAgent } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
});

// Stream chunks to stdout
for await (const chunk of agent.processStream!(createMessage('user', 'Count to 5'))) {
  if (typeof chunk.content === 'string') {
    process.stdout.write(chunk.content);
  }
}
console.log(); // newline after stream
```

### Handling Timeouts with AbortController

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

async function processWithTimeout(
  agent: Agent,
  message: Message,
  timeoutMs: number
): Promise<Message> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await agent.process(message);
    return response;
  } finally {
    clearTimeout(timer);
  }
}
```

---

## Working with LLMs

### OpenAI Agent

```typescript
import { OpenAIAgent, createMessage } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
  temperature: 0.7,  // 0.0 to 2.0
  maxTokens: 1024,   // max tokens in response
  systemPrompt: 'You are a helpful assistant.',
});

const response = await agent.process(
  createMessage('user', 'What is TypeScript?')
);
console.log(response.content);
```

### Anthropic Agent

```typescript
import { AnthropicAgent, createMessage } from '@agenkit/core';

const agent = new AnthropicAgent({
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: 'claude-sonnet-4-20250514',
  temperature: 1.0,  // 0.0 to 1.0 for Anthropic
  maxTokens: 4096,
  systemPrompt: 'You are a TypeScript expert.',
});

const response = await agent.process(
  createMessage('user', 'Explain async/await.')
);
console.log(response.content);
```

### OpenAI-Compatible Agents (vLLM, llama.cpp, etc.)

```typescript
import { OpenAICompatibleAgent, createMessage } from '@agenkit/core';

// vLLM local deployment
const agent = new OpenAICompatibleAgent({
  baseURL: 'http://localhost:8000/v1',
  model: 'meta-llama/Llama-2-7b-chat-hf',
  provider: 'vllm',
});

// llama.cpp server
const llamaCppAgent = new OpenAICompatibleAgent({
  baseURL: 'http://localhost:8080/v1',
  model: 'llama-2-7b-chat',
  provider: 'llamacpp',
});

const response = await agent.process(
  createMessage('user', 'What is machine learning?')
);
```

Supported providers: `vllm`, `llamacpp`, `sglang`, `tensorrt-llm`, `openllm`, `mlc-llm`, `tgi`, `inferflow`

### Multi-Turn Conversations

LLM agents maintain conversation history across calls:

```typescript
import { OpenAIAgent, createMessage } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
});

// The agent tracks conversation history internally
const r1 = await agent.process(createMessage('user', 'My name is Alice.'));
const r2 = await agent.process(createMessage('user', 'What is my name?'));
// r2.content will reference "Alice" from the prior context
console.log(r2.content);
```

---

## Error Handling

TypeScript uses exceptions for error handling. Agenkit integrates naturally with `try/catch` and `async/await`.

### Basic Error Handling

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

const agent = new LocalAgent({
  name: 'fallible-agent',
  process: async (message) => {
    if (!message.content) {
      throw new Error('empty input');
    }
    return { role: 'assistant', content: `Processed: ${message.content}` };
  },
});

async function main(): Promise<void> {
  try {
    const response = await agent.process(createMessage('user', ''));
    console.log(response.content);
  } catch (error) {
    if (error instanceof Error) {
      console.error(`Agent failed: ${error.message}`);
    }
  }
}
```

### Custom Error Types

```typescript
// Define domain-specific errors
class AgentTimeoutError extends Error {
  constructor(public readonly agentName: string, public readonly timeoutMs: number) {
    super(`agent '${agentName}' timed out after ${timeoutMs}ms`);
    this.name = 'AgentTimeoutError';
  }
}

class InvalidInputError extends Error {
  constructor(message: string) {
    super(`invalid input: ${message}`);
    this.name = 'InvalidInputError';
  }
}

// Use in agents
class ValidatingAgent implements Agent {
  readonly name = 'validator';

  async process(message: Message): Promise<Message> {
    if (typeof message.content !== 'string') {
      throw new InvalidInputError('content must be a string');
    }
    if (message.content.length === 0) {
      throw new InvalidInputError('content cannot be empty');
    }
    return { role: 'assistant', content: `Valid: ${message.content}` };
  }
}
```

### Error Recovery Patterns

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

// Pattern 1: Default fallback
async function processWithFallback(
  agent: Agent,
  message: Message,
  fallback: string
): Promise<Message> {
  try {
    return await agent.process(message);
  } catch {
    return { role: 'assistant', content: fallback };
  }
}

// Pattern 2: Retry with backoff
async function processWithRetry(
  agent: Agent,
  message: Message,
  maxAttempts = 3,
  initialDelayMs = 1000
): Promise<Message> {
  let lastError: Error | undefined;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await agent.process(message);
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      if (attempt < maxAttempts) {
        const delay = initialDelayMs * Math.pow(2, attempt - 1);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

// Pattern 3: Use RetryMiddleware (preferred)
import { applyMiddleware, retry } from '@agenkit/core';

const robustAgent = applyMiddleware(baseAgent, [
  retry({ maxAttempts: 3, initialDelay: 1000 }),
]);
```

### Validation Errors

```typescript
import { createValidatedMessage } from '@agenkit/core';

try {
  // Throws if role is invalid, content too large, or metadata malformed
  const msg = createValidatedMessage('invalid-role!', 'Hello');
} catch (error) {
  if (error instanceof Error) {
    // "Invalid message role: invalid-role!. Must be one of: user, assistant, system, tool, agent"
    console.error(error.message);
  }
}
```

---

## Adding Middleware

Middleware wraps agents to add cross-cutting concerns like retries, timeouts, and caching.

### The applyMiddleware Pattern

```typescript
import { LocalAgent, applyMiddleware, retry, timeout } from '@agenkit/core';

const base = new LocalAgent({
  name: 'base',
  process: async (msg) => ({ role: 'assistant', content: `ok: ${msg.content}` }),
});

// Compose middleware — applied right-to-left (retry wraps timeout)
const robust = applyMiddleware(base, [
  retry({ maxAttempts: 3, initialDelay: 1000 }),
  timeout({ timeout: 5000 }),
]);

const response = await robust.process(createMessage('user', 'hello'));
```

### RetryMiddleware

```typescript
import { RetryMiddleware } from '@agenkit/core/middleware';

const withRetry = new RetryMiddleware(baseAgent, {
  maxRetries: 3,
  initialDelayMs: 1000,
  backoffMultiplier: 2.0,
  maxDelayMs: 30000,
  shouldRetry: (error) => {
    // Custom retry predicate
    return error.message.includes('network') || error.message.includes('timeout');
  },
});
```

### TimeoutMiddleware

```typescript
import { TimeoutMiddleware } from '@agenkit/core/middleware';

const withTimeout = new TimeoutMiddleware(baseAgent, {
  timeoutMs: 5000,
  // Per-method timeouts (optional)
  methodTimeouts: {
    health_check: 1000,
    long_analysis: 60000,
  },
});
```

### CachingMiddleware

```typescript
import { CachingMiddleware } from '@agenkit/core/middleware';

const withCache = new CachingMiddleware(baseAgent, {
  ttlMs: 300000, // 5 minutes
  maxSize: 100,  // max cached entries
});
```

### CircuitBreakerMiddleware

```typescript
import { CircuitBreakerMiddleware } from '@agenkit/core/middleware';

const withCircuitBreaker = new CircuitBreakerMiddleware(baseAgent, {
  failureThreshold: 5,      // open after 5 failures
  recoveryTimeoutMs: 30000, // try again after 30s
  halfOpenMaxRequests: 1,   // requests allowed in half-open state
});
```

### Composing Multiple Middleware

```typescript
import {
  RetryMiddleware,
  TimeoutMiddleware,
  CircuitBreakerMiddleware,
  CachingMiddleware,
} from '@agenkit/core/middleware';

let agent: Agent = baseAgent;

// Layer middleware from innermost to outermost
agent = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 1000 });
agent = new TimeoutMiddleware(agent, { timeoutMs: 10000 });
agent = new CircuitBreakerMiddleware(agent, { failureThreshold: 5, recoveryTimeoutMs: 30000 });
agent = new CachingMiddleware(agent, { ttlMs: 60000, maxSize: 50 });

// Requests flow: Cache -> CircuitBreaker -> Timeout -> Retry -> Base
const response = await agent.process(message);
```

---

## Testing with Vitest

Vitest is the recommended test runner for Agenkit TypeScript projects.

### Setup

```bash
npm install --save-dev vitest @vitest/coverage-v8
```

Add to `package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

Create `vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
});
```

### Basic Test Structure

```typescript
import { describe, it, expect } from 'vitest';
import { LocalAgent, createMessage } from '@agenkit/core';

describe('GreetingAgent', () => {
  it('responds with a greeting', async () => {
    const agent = new LocalAgent({
      name: 'greeter',
      process: async (msg) => ({
        role: 'assistant',
        content: `Hello, ${msg.content}!`,
      }),
    });

    const message = createMessage('user', 'World');
    const response = await agent.process(message);

    expect(response.role).toBe('assistant');
    expect(response.content).toBe('Hello, World!');
  });

  it('returns error for empty input', async () => {
    const agent = new LocalAgent({
      name: 'validator',
      process: async (msg) => {
        if (!msg.content) throw new Error('empty input');
        return { role: 'assistant', content: 'ok' };
      },
    });

    await expect(
      agent.process(createMessage('user', ''))
    ).rejects.toThrow('empty input');
  });
});
```

### Running Tests

```bash
# Run all tests
npm test

# Watch mode (re-runs on changes)
npm run test:watch

# With coverage report
npm run test:coverage

# Run specific test file
npx vitest run src/__tests__/greeting.test.ts
```

---

## Next Steps

Now that you understand the basics, explore more advanced topics:

### 1. Learn Agent Patterns

Agenkit provides 11 built-in patterns:

- **Sequential** - Pipeline processing
- **Parallel** - Concurrent `Promise.all` processing
- **Reflection** - Self-improvement loops
- **ReAct** - Reasoning and acting with tools
- **And 7 more...**

See [PATTERNS.md](PATTERNS.md) for the complete guide.

### 2. Explore the API

See [API.md](API.md) for complete API reference including all interfaces, classes, and configuration options.

### 3. Set Up Observability

See [OBSERVABILITY.md](OBSERVABILITY.md) to add OpenTelemetry tracing, metrics, and structured logging.

### 4. Port from Another Language

If you're coming from Python, Go, Rust, C++, or Zig, see [MIGRATION.md](MIGRATION.md).

### 5. Read the Examples

The `examples/` directory contains runnable examples:

```bash
npx tsx examples/basic-usage.ts
npx tsx examples/middleware-example.ts
npx tsx examples/llm-integration.ts
npx tsx examples/transport-comparison.ts
```

### 6. Build Real Agents

Try building:
- **Chat bot** - Use `ConversationalAgent` pattern
- **Task executor** - Use `TaskAgent` pattern
- **Research assistant** - Combine `ParallelAgent` + `SequentialAgent`
- **Autonomous agent** - Use `AutonomousAgent` for goal-driven behavior

---

## Quick Reference

### Project Setup

```bash
mkdir my-agent && cd my-agent
npm init -y
npm install @agenkit/core
npm install --save-dev typescript tsx vitest
```

### Common Patterns

```typescript
import { LocalAgent, createMessage, createValidatedMessage } from '@agenkit/core';

// Create a message
const msg = createMessage('user', 'Hello!');

// Create a validated message
const validMsg = createValidatedMessage('user', 'Hello!', { session: 'abc' });

// Create a local agent
const agent = new LocalAgent({
  name: 'my-agent',
  process: async (m) => ({ role: 'assistant', content: `Reply: ${m.content}` }),
});

// Process a message
const response = await agent.process(msg);
console.log(response.content);

// Stream a response
for await (const chunk of agent.processStream!(msg)) {
  process.stdout.write(chunk.content as string);
}
```

### Testing

```typescript
import { describe, it, expect, vi } from 'vitest';

describe('my agent', () => {
  it('processes messages', async () => {
    const response = await agent.process(createMessage('user', 'test'));
    expect(response.role).toBe('assistant');
    expect(typeof response.content).toBe('string');
  });
});
```

Run with: `npm test`

---

## Troubleshooting

### "Cannot find module '@agenkit/core'"

**Cause:** Package not installed.

**Fix:** Run `npm install @agenkit/core`

### "Type 'string' is not assignable to type 'unknown'"

**Cause:** TypeScript strict mode catches type mismatches. This is usually correct behavior.

**Fix:** Use type guards:
```typescript
if (typeof response.content === 'string') {
  console.log(response.content); // TypeScript knows it's a string here
}
```

### "await is only allowed in async functions"

**Cause:** Using `await` outside an `async` function.

**Fix:** Wrap your code in an `async` function:
```typescript
async function main(): Promise<void> {
  const response = await agent.process(message);
}
main().catch(console.error);
```

### "Cannot use import statement outside a module"

**Cause:** Node.js treating the file as CommonJS when it uses ESM imports.

**Fix:** Add `"type": "module"` to `package.json`, or use `.mts` file extension, or compile with `tsc` first.

### Agent returns unexpected content type

**Cause:** `content` is typed as `unknown` for flexibility. Always check the type before using it.

**Fix:**
```typescript
const response = await agent.process(message);
if (typeof response.content === 'string') {
  console.log(response.content);
} else {
  console.log(JSON.stringify(response.content));
}
```

---

## Getting Help

- **Documentation:** [API.md](API.md), [PATTERNS.md](PATTERNS.md), [OBSERVABILITY.md](OBSERVABILITY.md)
- **Examples:** Check `examples/` directory
- **Issues:** [GitHub Issues](https://github.com/agenkit/agenkit/issues)
- **Discussions:** [GitHub Discussions](https://github.com/agenkit/agenkit/discussions)

**Welcome to the Agenkit community! Happy building!**
