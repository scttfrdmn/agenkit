# Agenkit TypeScript API Reference

Complete API documentation for `@agenkit/core` v0.75.0.

## Table of Contents

- [Core Types](#core-types)
  - [Message](#message)
  - [Agent](#agent)
  - [Tool](#tool)
  - [ToolResult](#toolresult)
- [Helper Functions](#helper-functions)
  - [createMessage](#createmessage)
  - [createValidatedMessage](#createvalidatedmessage)
  - [validateMessage](#validatemessage)
- [Built-in Agents](#built-in-agents)
  - [LocalAgent](#localagent)
  - [OpenAIAgent](#openaiagent)
  - [AnthropicAgent](#anthropicagent)
  - [OpenAICompatibleAgent](#openaicompatibleagent)
  - [HTTPAgent](#httpagent)
  - [WebSocketAgent](#websocketagent)
  - [GrpcAgent](#grpcagent)
- [Middleware](#middleware)
  - [applyMiddleware](#applymiddleware)
  - [RetryMiddleware](#retrymiddleware)
  - [TimeoutMiddleware](#timeoutmiddleware)
  - [CachingMiddleware](#cachingmiddleware)
  - [CircuitBreakerMiddleware](#circuitbreakermiddleware)
  - [RateLimiterMiddleware](#ratelimitermiddleware)
  - [MetricsMiddleware](#metricsmiddleware)
  - [BudgetMiddleware](#budgetmiddleware)
- [Patterns](#patterns)
  - [SequentialAgent](#sequentialagent)
  - [ParallelAgent](#parallelagent)
  - [ReflectionAgent](#reflectionagent)
  - [ReActAgent](#reactagent)
  - [PlanningAgent](#planningagent)
  - [TaskAgent](#taskagent)
  - [ConversationalAgent](#conversationalagent)
  - [AgentsAsToolsAgent](#agentsastoolsagent)
  - [AutonomousAgent](#autonomousagent)
  - [MultiagentSystem](#multiagentsystem)
  - [MemoryHierarchyAgent](#memoryhierarchyagent)
- [Observability](#observability)
  - [TracingAgent](#tracingagent)
  - [MetricsCollector](#metricscollector)
- [Introspection](#introspection)

---

## Core Types

### Message

The fundamental unit of communication in Agenkit.

```typescript
interface Message {
  /** Message source: "user", "assistant", "system", "tool", or "agent" */
  role: string;

  /** Message content — can be string, object, array, or any serializable data */
  content: unknown;

  /** Optional metadata for session tracking, tracing, etc. */
  metadata?: Record<string, unknown>;

  /** ISO 8601 timestamp — defaults to now if not provided */
  timestamp?: string;
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | `string` | Yes | Message source identifier |
| `content` | `unknown` | Yes | Message payload — any JSON-serializable value |
| `metadata` | `Record<string, unknown>` | No | Extension point for framework-specific data |
| `timestamp` | `string` | No | ISO 8601 timestamp for ordering and debugging |

**Valid Roles:**

| Role | Usage |
|------|-------|
| `"user"` | Input from a human |
| `"assistant"` | Response from an agent or LLM |
| `"system"` | Instructions or context |
| `"tool"` | Results from tool execution |
| `"agent"` | Messages from another agent in multiagent systems |

**Example:**

```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
  role: 'user',
  content: 'What is the capital of France?',
  metadata: { session_id: 'abc-123', priority: 1 },
  timestamp: new Date().toISOString(),
};
```

---

### Agent

The minimal contract for agent communication.

```typescript
interface Agent {
  /** Agent identifier — must be unique within a system */
  readonly name: string;

  /**
   * Process a message and return a response.
   * Always asynchronous — agents typically perform I/O.
   */
  process(message: Message): Promise<Message>;

  /**
   * Process a message with streaming response (optional).
   * Returns an async generator that yields message chunks.
   */
  processStream?(message: Message): AsyncGenerator<Message, void, undefined>;

  /**
   * What this agent can do (optional).
   * Used for agent discovery and selection.
   */
  readonly capabilities?: string[];

  /**
   * Examine agent's internal state (optional).
   * Returns a snapshot of memory, capabilities, and internal variables.
   */
  introspect?(): IntrospectionResult;
}
```

**Implementing the Agent Interface:**

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';

class SummarizerAgent implements Agent {
  readonly name = 'summarizer';
  readonly capabilities = ['text-summarization'];

  async process(message: Message): Promise<Message> {
    const text = typeof message.content === 'string'
      ? message.content
      : JSON.stringify(message.content);

    const summary = await this.summarize(text);

    return createMessage('assistant', summary, {
      original_length: text.length,
      summary_length: summary.length,
    });
  }

  private async summarize(text: string): Promise<string> {
    // Implementation...
    return `Summary of: ${text.slice(0, 50)}...`;
  }
}
```

---

### Tool

Interface for deterministic operations that agents can invoke.

```typescript
interface Tool {
  /** Tool identifier — must be unique within a tool set */
  readonly name: string;

  /** Description for LLMs — explains when and how to use the tool */
  readonly description: string;

  /**
   * JSON schema for tool parameters.
   * Used by LLMs to understand valid inputs.
   */
  parametersSchema?: Record<string, unknown>;

  /**
   * Execute the tool with given parameters.
   *
   * @param params Tool parameters — validated against parametersSchema if provided
   * @param signal Optional AbortSignal for cancellation support
   */
  execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult>;
}
```

**Example Implementation:**

```typescript
import { Tool, ToolResult } from '@agenkit/core';

class WebSearchTool implements Tool {
  readonly name = 'web_search';
  readonly description = 'Search the web for current information';

  readonly parametersSchema = {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'The search query',
      },
      maxResults: {
        type: 'number',
        description: 'Maximum number of results to return',
        default: 5,
      },
    },
    required: ['query'],
  };

  async execute(
    params: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<ToolResult> {
    const query = params.query as string;
    const maxResults = (params.maxResults as number | undefined) ?? 5;

    try {
      const results = await searchAPI(query, maxResults, { signal });
      return {
        output: results,
        success: true,
        metadata: { query, resultCount: results.length },
      };
    } catch (error) {
      return {
        output: null,
        success: false,
        error: error instanceof Error ? error.message : 'search failed',
      };
    }
  }
}
```

---

### ToolResult

Result from tool execution.

```typescript
interface ToolResult {
  /** Tool output — any JSON-serializable data */
  output: unknown;

  /** Whether execution succeeded */
  success: boolean;

  /** Error message if execution failed (optional) */
  error?: string;

  /** Metadata about the execution (optional) */
  metadata?: Record<string, unknown>;
}
```

---

## Helper Functions

### createMessage

Creates a Message with defaults applied.

```typescript
function createMessage(
  role: string | Partial<Message>,
  content?: unknown,
  metadata?: Record<string, unknown>,
): Message
```

**Overloads:**

```typescript
// Positional syntax
createMessage('user', 'Hello!');
createMessage('assistant', { type: 'json', data: {} }, { source: 'llm' });

// Object syntax
createMessage({ role: 'user', content: 'Hello!' });
createMessage({ role: 'assistant', content: 'Hi!', metadata: { model: 'gpt-4o' } });
```

**Returns:** A `Message` with `timestamp` set to the current ISO 8601 time if not provided.

**Example:**

```typescript
import { createMessage } from '@agenkit/core';

const userMsg = createMessage('user', 'What is TypeScript?');
// { role: 'user', content: 'What is TypeScript?', metadata: {}, timestamp: '2026-...' }

const sysMsg = createMessage('system', 'You are a helpful assistant.');

const toolResult = createMessage('tool', {
  function: 'search',
  result: 'TypeScript is a typed superset of JavaScript.',
}, { call_id: 'call_abc123' });
```

---

### createValidatedMessage

Creates a message and validates it against structure and size constraints.

```typescript
function createValidatedMessage(
  role: string,
  content: unknown,
  metadata?: Record<string, unknown>,
): Message
```

**Throws:** `Error` if:
- Role is empty, exceeds 20 characters, or is not a recognized role
- Content is `null` or `undefined`
- Content exceeds 16MB
- Metadata exceeds 100 keys
- Any metadata key exceeds 50 characters
- Any metadata value exceeds 16MB

**Example:**

```typescript
import { createValidatedMessage } from '@agenkit/core';

const msg = createValidatedMessage('user', 'Hello!', { session_id: '123' });

// Throws immediately:
createValidatedMessage('bad-role!', 'Hello');
// Error: Invalid message role: bad-role!. Must be one of: user, assistant, system, tool, agent
```

---

### validateMessage

Validates an existing message object.

```typescript
function validateMessage(message: Message): void
```

**Throws:** `Error` describing the first validation failure found.

**Example:**

```typescript
import { validateMessage } from '@agenkit/core';

const msg: Message = { role: 'user', content: 'Hello' };
validateMessage(msg); // OK — no throw

const invalid: Message = { role: 'bad', content: 'Hello' };
validateMessage(invalid); // throws Error
```

---

## Built-in Agents

### LocalAgent

Wraps a TypeScript function as an agent. No network overhead.

```typescript
class LocalAgent implements Agent {
  constructor(config: LocalAgentConfig)

  readonly name: string;
  readonly capabilities?: string[];
  process(message: Message): Promise<Message>;
  processStream?(message: Message): AsyncGenerator<Message, void, undefined>;
}

interface LocalAgentConfig {
  name: string;
  process: (message: Message) => Promise<Message>;
  processStream?: (message: Message) => AsyncGenerator<Message, void, undefined>;
  capabilities?: string[];
}
```

**Example:**

```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

const agent = new LocalAgent({
  name: 'echo',
  capabilities: ['echo'],
  process: async (msg) => ({
    role: 'assistant',
    content: `Echo: ${msg.content}`,
    metadata: { agent: 'echo' },
  }),
});

const response = await agent.process(createMessage('user', 'Hello'));
console.log(response.content); // "Echo: Hello"
```

---

### OpenAIAgent

Uses the OpenAI Chat Completions API.

```typescript
class OpenAIAgent implements Agent {
  constructor(config: OpenAIAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  processStream(message: Message): AsyncGenerator<Message, void, undefined>;
}

interface OpenAIAgentConfig {
  apiKey: string;
  model: string;           // e.g., 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'
  temperature?: number;    // 0.0 to 2.0 (default: 1.0)
  maxTokens?: number;      // max tokens in response (default: 1024)
  topP?: number;           // 0.0 to 1.0 (default: 1.0)
  systemPrompt?: string;   // optional system instruction
  organization?: string;   // optional OpenAI organization ID
  baseURL?: string;        // optional override for proxy endpoints
}
```

**Example:**

```typescript
import { OpenAIAgent, createMessage } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
  temperature: 0.7,
  maxTokens: 2048,
  systemPrompt: 'You are a TypeScript expert.',
});

const response = await agent.process(
  createMessage('user', 'Explain generics in TypeScript.')
);
console.log(response.content);

// Streaming
for await (const chunk of agent.processStream(createMessage('user', 'Count to 5'))) {
  process.stdout.write(chunk.content as string);
}
```

**Parameter Validation:** `temperature`, `maxTokens`, and `topP` are validated at construction time. Invalid values throw immediately.

---

### AnthropicAgent

Uses the Anthropic Messages API (Claude).

```typescript
class AnthropicAgent implements Agent {
  constructor(config: AnthropicAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  processStream(message: Message): AsyncGenerator<Message, void, undefined>;
}

interface AnthropicAgentConfig {
  apiKey: string;
  model: string;           // e.g., 'claude-sonnet-4-20250514', 'claude-3-5-haiku-20241022'
  temperature?: number;    // 0.0 to 1.0 (default: 1.0)
  maxTokens?: number;      // max tokens in response (default: 1024)
  topP?: number;           // 0.0 to 1.0 (default: 1.0)
  systemPrompt?: string;   // optional system instruction
}
```

**Example:**

```typescript
import { AnthropicAgent, createMessage } from '@agenkit/core';

const agent = new AnthropicAgent({
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: 'claude-sonnet-4-20250514',
  temperature: 1.0,
  maxTokens: 4096,
});

const response = await agent.process(
  createMessage('user', 'What is async/await?')
);
```

---

### OpenAICompatibleAgent

Connects to any OpenAI-compatible API endpoint.

```typescript
class OpenAICompatibleAgent implements Agent {
  constructor(config: OpenAICompatibleAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  processStream(message: Message): AsyncGenerator<Message, void, undefined>;
}

interface OpenAICompatibleAgentConfig {
  baseURL: string;          // e.g., 'http://localhost:8000/v1'
  model: string;            // model name for the endpoint
  provider?: string;        // hint: 'vllm' | 'llamacpp' | 'sglang' | 'tgi' | ...
  apiKey?: string;          // optional — some endpoints require a key
  temperature?: number;
  maxTokens?: number;
}
```

**Supported Providers:** `vllm`, `llamacpp`, `sglang`, `tensorrt-llm`, `openllm`, `mlc-llm`, `tgi`, `inferflow`

**Example:**

```typescript
import { OpenAICompatibleAgent, createMessage } from '@agenkit/core';

// Local vLLM deployment
const agent = new OpenAICompatibleAgent({
  baseURL: 'http://localhost:8000/v1',
  model: 'meta-llama/Llama-2-7b-chat-hf',
  provider: 'vllm',
});

const response = await agent.process(createMessage('user', 'Hello!'));
```

---

### HTTPAgent

Communicates with an agent over HTTP/REST.

```typescript
class HTTPAgent implements Agent {
  constructor(config: HTTPAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface HTTPAgentConfig {
  baseUrl: string;           // e.g., 'http://localhost:8000'
  name?: string;             // agent name (default: 'http-agent')
  headers?: Record<string, string>;
  timeoutMs?: number;
}
```

---

### WebSocketAgent

Communicates with an agent over WebSocket for real-time bidirectional interaction.

```typescript
class WebSocketAgent implements Agent {
  constructor(config: WebSocketAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  connect(): Promise<void>;
  close(): Promise<void>;
}

interface WebSocketAgentConfig {
  url: string;               // e.g., 'ws://localhost:8080'
  name?: string;
  maxRetries?: number;       // reconnect attempts (default: 5)
  pingInterval?: number;     // heartbeat interval ms (default: 30000)
}
```

**Example:**

```typescript
import { WebSocketAgent, createMessage } from '@agenkit/core';

const agent = new WebSocketAgent({
  url: 'ws://localhost:8080',
  maxRetries: 5,
  pingInterval: 30000,
});

await agent.connect();
const response = await agent.process(createMessage('user', 'Hello'));
console.log(response.content);
await agent.close();
```

---

### GrpcAgent

High-performance gRPC transport with Protocol Buffers.

```typescript
class GrpcAgent implements Agent {
  constructor(name: string, config: GrpcAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  close(): Promise<void>;
}

interface GrpcAgentConfig {
  address: string;           // e.g., 'localhost:50051'
  timeout?: number;          // timeout ms (default: 5000)
  useTLS?: boolean;          // enable TLS (default: false)
  credentials?: object;      // gRPC credentials object
}
```

---

## Middleware

### applyMiddleware

Applies an array of middleware to an agent.

```typescript
function applyMiddleware(
  agent: Agent,
  middleware: MiddlewareFn[],
): Agent

type MiddlewareFn = (agent: Agent) => Agent;
```

**Example:**

```typescript
import { applyMiddleware, retry, timeout, circuitBreaker } from '@agenkit/core';

const robust = applyMiddleware(baseAgent, [
  retry({ maxAttempts: 3, initialDelay: 1000 }),
  timeout({ timeout: 5000 }),
  circuitBreaker({ failureThreshold: 5, recoveryTimeout: 30000 }),
]);
```

---

### RetryMiddleware

Retries failed requests with exponential backoff.

```typescript
class RetryMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config: RetryConfig)

  getMetrics(): RetryMetrics;
  resetMetrics(): void;
}

interface RetryConfig {
  maxRetries?: number;           // default: 3
  initialDelayMs?: number;       // default: 1000
  backoffMultiplier?: number;    // default: 2.0
  maxDelayMs?: number;           // default: 30000
  shouldRetry?: (error: Error) => boolean;  // default: retries on network/timeout errors
}

interface RetryMetrics {
  totalAttempts: number;
  successfulFirstAttempt: number;
  successfulOnRetry: number;
  failedAfterRetries: number;
  totalRetries: number;
}
```

**Example:**

```typescript
import { RetryMiddleware } from '@agenkit/core/middleware';

const agent = new RetryMiddleware(baseAgent, {
  maxRetries: 5,
  initialDelayMs: 500,
  backoffMultiplier: 2.0,
  maxDelayMs: 60000,
  shouldRetry: (err) => !err.message.includes('invalid input'),
});

const response = await agent.process(message);

const metrics = agent.getMetrics();
console.log(`Total retries: ${metrics.totalRetries}`);
```

---

### TimeoutMiddleware

Cancels requests that exceed a time limit.

```typescript
class TimeoutMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config: TimeoutConfig)

  getMetrics(): TimeoutMetrics;
}

interface TimeoutConfig {
  timeoutMs: number;
  methodTimeouts?: Record<string, number>;  // per-operation timeouts
}

interface TimeoutMetrics {
  totalRequests: number;
  successfulRequests: number;
  timedOutRequests: number;
  failedRequests: number;
  minDuration: number | null;
  maxDuration: number | null;
  averageDuration: number | null;
}
```

**Throws:** `TimeoutError` if the request exceeds `timeoutMs`.

**Example:**

```typescript
import { TimeoutMiddleware, TimeoutError } from '@agenkit/core/middleware';

const agent = new TimeoutMiddleware(baseAgent, {
  timeoutMs: 5000,
  methodTimeouts: {
    health_check: 1000,
    long_analysis: 120000,
  },
});

try {
  const response = await agent.process(message);
} catch (error) {
  if (error instanceof TimeoutError) {
    console.error(`Timed out after ${error.message}`);
  }
}
```

---

### CachingMiddleware

Caches responses with TTL-based expiration.

```typescript
class CachingMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config: CachingConfig)

  getMetrics(): CachingMetrics;
  clearCache(): void;
}

interface CachingConfig {
  ttlMs: number;         // cache entry lifetime in milliseconds
  maxSize?: number;      // max entries (default: 100)
  keyFn?: (message: Message) => string;  // custom cache key function
}

interface CachingMetrics {
  hits: number;
  misses: number;
  evictions: number;
  currentSize: number;
}
```

**Example:**

```typescript
import { CachingMiddleware } from '@agenkit/core/middleware';

const agent = new CachingMiddleware(baseAgent, {
  ttlMs: 5 * 60 * 1000, // 5 minutes
  maxSize: 200,
  keyFn: (msg) => `${msg.role}:${JSON.stringify(msg.content)}`,
});

const r1 = await agent.process(message); // cache miss — calls base agent
const r2 = await agent.process(message); // cache hit — instant response

const metrics = agent.getMetrics();
console.log(`Cache hit rate: ${metrics.hits / (metrics.hits + metrics.misses)}`);
```

---

### CircuitBreakerMiddleware

Prevents cascading failures by stopping requests when the service is unhealthy.

```typescript
class CircuitBreakerMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config: CircuitBreakerConfig)

  getState(): 'closed' | 'open' | 'half-open';
  getMetrics(): CircuitBreakerMetrics;
}

interface CircuitBreakerConfig {
  failureThreshold: number;      // failures before opening circuit
  recoveryTimeoutMs: number;     // ms to wait before trying again
  halfOpenMaxRequests?: number;  // requests allowed in half-open state (default: 1)
  onStateChange?: (state: string) => void;
}

interface CircuitBreakerMetrics {
  state: 'closed' | 'open' | 'half-open';
  failures: number;
  successes: number;
  rejectedRequests: number;
  lastFailureTime: number | null;
}
```

**Circuit States:**
- `closed` — Normal operation; requests pass through
- `open` — Service unhealthy; requests rejected immediately
- `half-open` — Testing recovery; limited requests allowed

**Example:**

```typescript
import { CircuitBreakerMiddleware } from '@agenkit/core/middleware';

const agent = new CircuitBreakerMiddleware(baseAgent, {
  failureThreshold: 5,
  recoveryTimeoutMs: 30000,
  halfOpenMaxRequests: 1,
  onStateChange: (state) => console.log(`Circuit: ${state}`),
});
```

---

### RateLimiterMiddleware

Throttles request rates to prevent overloading downstream services.

```typescript
class RateLimiterMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config: RateLimiterConfig)
}

interface RateLimiterConfig {
  requestsPerSecond: number;   // max requests per second
  maxWaitMs?: number;          // max time to wait for a slot (default: 30000)
  burst?: number;              // burst capacity (default: requestsPerSecond)
}
```

**Example:**

```typescript
import { RateLimiterMiddleware } from '@agenkit/core/middleware';

const agent = new RateLimiterMiddleware(baseAgent, {
  requestsPerSecond: 10,
  maxWaitMs: 5000,
  burst: 20, // allow bursts up to 20 requests
});
```

---

### MetricsMiddleware

Collects request/response metrics.

```typescript
class MetricsMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config?: MetricsConfig)

  getMetrics(): AgentMetrics;
  resetMetrics(): void;
}

interface MetricsConfig {
  histogramBuckets?: number[];   // latency histogram bucket boundaries in ms
}

interface AgentMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  totalLatencyMs: number;
  averageLatencyMs: number;
  p50LatencyMs: number;
  p95LatencyMs: number;
  p99LatencyMs: number;
}
```

---

### BudgetMiddleware

Enforces cost budgets for LLM API calls.

```typescript
class BudgetMiddleware extends BaseMiddleware {
  constructor(agent: Agent, config: BudgetConfig)

  getSpend(): number;
  getRemainingBudget(): number;
}

interface BudgetConfig {
  maxCostUSD: number;
  onBudgetExceeded?: () => void;
  costPerToken?: number;       // default: model-specific
}
```

**Example:**

```typescript
import { BudgetMiddleware } from '@agenkit/core/middleware';

const agent = new BudgetMiddleware(openaiAgent, {
  maxCostUSD: 5.00,
  onBudgetExceeded: () => console.warn('Budget exceeded!'),
});

const response = await agent.process(message);
console.log(`Spend so far: $${agent.getSpend().toFixed(4)}`);
console.log(`Remaining: $${agent.getRemainingBudget().toFixed(4)}`);
```

---

## Patterns

All patterns implement the `Agent` interface and can be used interchangeably with any other agent.

### SequentialAgent

Processes messages through agents in order, passing each response as input to the next.

```typescript
class SequentialAgent implements Agent {
  constructor(agents: Agent[], config?: SequentialConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface SequentialConfig {
  name?: string;
  stopOnError?: boolean;  // stop pipeline on first failure (default: true)
}
```

**Example:**

```typescript
import { SequentialAgent, createMessage } from '@agenkit/core';

const pipeline = new SequentialAgent([
  validationAgent,
  processingAgent,
  formatterAgent,
], { name: 'validation-pipeline' });

const response = await pipeline.process(createMessage('user', 'raw input'));
```

---

### ParallelAgent

Processes a message with all agents concurrently using `Promise.all`.

```typescript
class ParallelAgent implements Agent {
  constructor(agents: Agent[], config?: ParallelConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;  // returns merged result
  processAll(message: Message): Promise<Message[]>;  // returns all results
}

interface ParallelConfig {
  name?: string;
  merge?: (responses: Message[]) => Message;  // custom merge function
  failFast?: boolean;  // fail immediately if any agent fails (default: false)
}
```

**Example:**

```typescript
import { ParallelAgent, createMessage } from '@agenkit/core';

const parallel = new ParallelAgent([
  researchAgent,
  analyticsAgent,
  summaryAgent,
]);

// Get all results
const allResults = await parallel.processAll(createMessage('user', 'Query'));
allResults.forEach((r, i) => console.log(`Agent ${i}: ${r.content}`));

// Or get merged result
const merged = await parallel.process(createMessage('user', 'Query'));
```

---

### ReflectionAgent

Iteratively improves output through a draft-critique-refine loop.

```typescript
class ReflectionAgent implements Agent {
  constructor(agent: Agent, config?: ReflectionConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface ReflectionConfig {
  name?: string;
  maxIterations?: number;        // default: 3
  reflectionPrompt?: string;     // prompt for the critique step
  qualityThreshold?: number;     // stop early if quality score >= threshold
}
```

**Example:**

```typescript
import { ReflectionAgent, createMessage } from '@agenkit/core';

const agent = new ReflectionAgent(writingAgent, {
  maxIterations: 3,
  reflectionPrompt: 'Critique this response and identify improvements:',
});

const response = await agent.process(
  createMessage('user', 'Write a product description.')
);
```

---

### ReActAgent

Implements the Reasoning + Acting loop: think before acting.

```typescript
class ReActAgent implements Agent {
  constructor(agent: Agent, tools: Tool[], config?: ReActConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface ReActConfig {
  name?: string;
  maxIterations?: number;    // max think-act cycles (default: 10)
  systemPrompt?: string;
}
```

**Example:**

```typescript
import { ReActAgent, createMessage } from '@agenkit/core';

const agent = new ReActAgent(llmAgent, [searchTool, calculatorTool], {
  maxIterations: 5,
  systemPrompt: 'Use tools to find accurate answers.',
});

const response = await agent.process(
  createMessage('user', "What's 15% of Paris population?")
);
```

---

### PlanningAgent

Decomposes complex tasks into steps before executing.

```typescript
class PlanningAgent implements Agent {
  constructor(plannerAgent: Agent, executorAgent: Agent, config?: PlanningConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface PlanningConfig {
  name?: string;
  maxSteps?: number;        // max plan steps (default: 10)
  planningPrompt?: string;  // prompt for plan generation
}
```

---

### TaskAgent

Executes a specific named task.

```typescript
class TaskAgent implements Agent {
  constructor(config: TaskAgentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface TaskAgentConfig {
  name: string;
  taskName: string;
  process: (message: Message, taskName: string) => Promise<Message>;
  capabilities?: string[];
}
```

---

### ConversationalAgent

Maintains dialogue context across multiple turns.

```typescript
class ConversationalAgent implements Agent {
  constructor(agent: Agent, config?: ConversationalConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  clearHistory(): void;
  getHistory(): Message[];
}

interface ConversationalConfig {
  name?: string;
  maxHistoryLength?: number;   // max messages in context window (default: 50)
  systemPrompt?: string;
  memory?: MemoryHierarchy;
}
```

**Example:**

```typescript
import { ConversationalAgent, createMessage } from '@agenkit/core';

const chat = new ConversationalAgent(llmAgent, {
  maxHistoryLength: 20,
  systemPrompt: 'You are a helpful assistant.',
});

await chat.process(createMessage('user', 'My name is Alice.'));
const response = await chat.process(createMessage('user', 'What is my name?'));
// response.content references "Alice" from history

console.log(`History length: ${chat.getHistory().length}`);
chat.clearHistory(); // start fresh conversation
```

---

### AgentsAsToolsAgent

Enables an orchestrator agent to call other agents as if they were tools.

```typescript
class AgentsAsToolsAgent implements Agent {
  constructor(orchestratorAgent: Agent, config?: AgentsAsToolsConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  registerTool(name: string, agent: Agent): void;
}

interface AgentsAsToolsConfig {
  name?: string;
  tools?: Record<string, Agent>;  // initial tool agents
}
```

**Example:**

```typescript
import { AgentsAsToolsAgent, createMessage } from '@agenkit/core';

const orchestrator = new AgentsAsToolsAgent(llmAgent, {
  tools: {
    translator: translationAgent,
    summarizer: summaryAgent,
  },
});

orchestrator.registerTool('calculator', calculatorAgent);

const response = await orchestrator.process(
  createMessage('user', 'Summarize and translate this to French.')
);
```

---

### AutonomousAgent

Self-directed agent that pursues a goal over multiple steps.

```typescript
class AutonomousAgent {
  constructor(agent: Agent, config: AutonomousConfig)

  run(): Promise<Message>;
  stop(): void;
}

interface AutonomousConfig {
  goal: string;
  maxSteps?: number;        // default: 100
  tools?: Tool[];
  onStep?: (step: number, message: Message) => void;
}
```

**Example:**

```typescript
import { AutonomousAgent } from '@agenkit/core';

const auto = new AutonomousAgent(llmAgent, {
  goal: 'Research TypeScript best practices and compile a summary',
  maxSteps: 20,
  tools: [searchTool, readFileTool],
  onStep: (step, msg) => console.log(`Step ${step}: ${msg.content}`),
});

const result = await auto.run();
console.log(result.content);
```

---

### MultiagentSystem

Coordinates multiple specialized agents toward a common goal.

```typescript
class MultiagentSystem implements Agent {
  constructor(config?: MultiagentConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  addAgent(name: string, agent: Agent): void;
  coordinate(message: Message): Promise<Message[]>;
}

interface MultiagentConfig {
  name?: string;
  agents?: Record<string, Agent>;
  coordinator?: Agent;       // optional coordinator agent
}
```

---

### MemoryHierarchyAgent

Manages working, short-term, and long-term memory for context-aware responses.

```typescript
class MemoryHierarchyAgent implements Agent {
  constructor(agent: Agent, config?: MemoryHierarchyConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
  getWorkingMemory(): Message[];
  clearWorkingMemory(): void;
}

interface MemoryHierarchyConfig {
  name?: string;
  workingMemorySize?: number;     // default: 10 messages
  shortTermSize?: number;         // default: 100 messages
  longTermStorage?: LongTermStore;
}
```

**Example:**

```typescript
import { MemoryHierarchyAgent, createMessage } from '@agenkit/core';

const agent = new MemoryHierarchyAgent(llmAgent, {
  workingMemorySize: 5,
  shortTermSize: 50,
});

for (const turn of conversation) {
  const response = await agent.process(createMessage('user', turn));
  console.log(response.content);
}

console.log('Working memory:', agent.getWorkingMemory().length, 'messages');
```

---

## Observability

### TracingAgent

Wraps an agent with OpenTelemetry distributed tracing.

```typescript
class TracingAgent implements Agent {
  constructor(agent: Agent, config?: TracingConfig)

  readonly name: string;
  process(message: Message): Promise<Message>;
}

interface TracingConfig {
  tracer?: Tracer;             // OpenTelemetry tracer (default: auto-created)
  serviceName?: string;
  additionalAttributes?: Record<string, string>;
}
```

**Example:**

```typescript
import { TracingAgent, createMessage } from '@agenkit/core';
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('my-agent-service', '1.0.0');
const agent = new TracingAgent(llmAgent, {
  tracer,
  serviceName: 'my-agent-service',
  additionalAttributes: { environment: 'production' },
});

// Every process() call automatically creates an OpenTelemetry span
const response = await agent.process(createMessage('user', 'Hello'));
```

---

### MetricsCollector

Collects and exposes Prometheus-compatible metrics.

```typescript
class MetricsCollector {
  constructor(config?: MetricsCollectorConfig)

  record(agentName: string, latencyMs: number, success: boolean): void;
  getSnapshot(): MetricsSnapshot;
  getPrometheusText(): string;
  reset(): void;
}

interface MetricsCollectorConfig {
  buckets?: number[];   // latency histogram buckets in ms
}

interface MetricsSnapshot {
  agents: Record<string, AgentMetrics>;
  collectedAt: string;  // ISO 8601
}
```

**Example:**

```typescript
import { MetricsCollector } from '@agenkit/core/observability';

const collector = new MetricsCollector({ buckets: [10, 50, 100, 500, 1000] });

const start = Date.now();
try {
  const response = await agent.process(message);
  collector.record(agent.name, Date.now() - start, true);
} catch (error) {
  collector.record(agent.name, Date.now() - start, false);
  throw error;
}

// Export Prometheus metrics
const prometheusText = collector.getPrometheusText();
// Serve this at /metrics endpoint
```

---

## Introspection

The `IntrospectionResult` type carries a snapshot of an agent's internal state.

```typescript
interface IntrospectionResult {
  /** ISO 8601 timestamp of when introspection occurred */
  timestamp: string;

  /** Agent name */
  agentName: string;

  /** List of capabilities */
  capabilities: string[];

  /** Memory state snapshot (if agent has memory) */
  memoryState?: {
    shortTermCount: number;
    longTermCount: number;
    workingMemoryCount?: number;
  };

  /** Arbitrary internal state key-value pairs */
  internalState: Record<string, unknown>;

  /** Arbitrary metadata */
  metadata: Record<string, unknown>;
}
```

**Implementing Introspection:**

```typescript
import { Agent, Message, IntrospectionResult, createDefaultIntrospectionResult } from '@agenkit/core';

class StatefulAgent implements Agent {
  readonly name = 'stateful';
  private messageCount = 0;
  private history: Message[] = [];

  async process(message: Message): Promise<Message> {
    this.messageCount++;
    this.history.push(message);
    return { role: 'assistant', content: `Message #${this.messageCount}` };
  }

  introspect(): IntrospectionResult {
    return {
      timestamp: new Date().toISOString(),
      agentName: this.name,
      capabilities: this.capabilities ?? [],
      memoryState: {
        shortTermCount: this.history.length,
        longTermCount: 0,
      },
      internalState: {
        messageCount: this.messageCount,
        hasHistory: this.history.length > 0,
      },
      metadata: {},
    };
  }
}
```

---

## Cross-Language Compatibility

Agenkit TypeScript maintains API parity with all other language implementations:

| Language | Package |
|----------|---------|
| Python | `agenkit` (pip) |
| Go | `github.com/agenkit/agenkit-go` |
| Rust | `agenkit-rs` (crates.io) |
| C++ | `agenkit-cpp` (CMake) |
| Zig | `agenkit-zig` (build.zig.zon) |
| C# | `Agenkit` (NuGet) |
| Java | `io.agenkit:agenkit` (Maven) |
| Scala | `io.agenkit:agenkit-scala_3` (sbt) |

### Universal Message Structure (JSON)

```json
{
  "role": "user|assistant|system|tool|agent",
  "content": "string or object",
  "metadata": { "key": "value" },
  "timestamp": "2026-03-17T12:00:00.000Z"
}
```

### Universal Agent Interface

Every language implements the same conceptual interface:
- `name` / `getName()` — Agent identifier
- `process(message)` — Process a message
- `capabilities` — Optional capability list
- `close()` / `deinit()` / `destroy()` — Cleanup (language-specific)

---

## Version Information

**API Version:** 0.75.0
**Node.js:** >= 22.0.0
**TypeScript:** >= 5.0.0
**Stability:** Production-ready

### See Also

- [Getting Started Guide](GETTING_STARTED.md)
- [Patterns Guide](PATTERNS.md)
- [Migration Guide](MIGRATION.md)
- [Observability Guide](OBSERVABILITY.md)
- [Testing Framework](TESTING_FRAMEWORK.md)
