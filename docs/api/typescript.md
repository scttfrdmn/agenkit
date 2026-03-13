# TypeScript API Reference

**Package:** `agenkit-ts`
**Node.js:** 22+ / modern bundlers
**TypeScript:** 5.0+

---

## Core Types

### `Message`

```typescript
// src/core/index.ts

interface Message {
    role: string;
    content: string;
    metadata: Record<string, unknown>;
}
```

`role` is typically `"user"`, `"assistant"`, or `"system"`. Token usage from LLM adapters is stored in `metadata` as flat keys: `input_tokens`, `output_tokens`, `total_tokens`, `stop_reason`.

### `Agent` (interface)

```typescript
interface Agent {
    process(message: Message): Promise<Message>;
    name(): string;
    capabilities(): string[];
}
```

All adapters, patterns, and middleware implement this interface.

### `Tool`

```typescript
interface Tool {
    name: string;
    description: string;
    parameters: Record<string, unknown>;  // JSON Schema
    execute(args: Record<string, unknown>): Promise<unknown>;
}
```

---

## LLM Adapters

**Module:** `agenkit-ts/src/adapters`

### `AnthropicClient`

```typescript
new AnthropicClient({
    model?: string;       // default: "claude-sonnet-4-6"
    apiKey: string;       // or ANTHROPIC_API_KEY env var
    maxTokens?: number;   // default: 4096
    temperature?: number; // default: 1.0
})
```

Implements `Agent`. Response metadata fields: `input_tokens`, `output_tokens`, `total_tokens`, `stop_reason`.

### `OpenAIClient`

```typescript
new OpenAIClient({
    model?: string;       // default: "gpt-4o"
    apiKey: string;       // or OPENAI_API_KEY env var
    maxTokens?: number;   // default: 4096
    temperature?: number; // default: 0.7
})
```

### Additional Adapters

| Class | Notes |
|-------|-------|
| `BedrockClient` | AWS Bedrock |
| `GeminiClient` | Google Gemini |
| `OllamaClient` | Local Ollama |
| `LiteLLMClient` | LiteLLM proxy |

---

## Patterns

**Module:** `agenkit-ts/src/patterns`

All pattern constructors accept an options object. `agent` is always the underlying `Agent`.

| Class | Key Options |
|-------|-------------|
| `ReflectionAgent` | `agent`, `maxIterations?: number` |
| `ReactAgent` | `agent`, `tools: Tool[]` |
| `AgentsAsToolsAgent` | `agent`, `subAgents: Agent[]` |
| `OrchestrationAgent` | `orchestrator: Agent`, `workers: Agent[]` |
| `ReasoningWithToolsAgent` | `agent`, `tools: Tool[]`, `maxSteps?: number` |
| `ConversationalAgent` | `agent`, `memory?: Memory` |
| `TaskAgent` | `agent`, `taskDescription: string` |
| `MultiagentAgent` | `agents: Agent[]` |
| `PlanningAgent` | `planner: Agent`, `executor: Agent` |
| `AutonomousAgent` | `agent`, `maxIterations?: number`, `stopCondition?: (msg: Message) => boolean` |
| `SequentialAgent` | `agents: Agent[]` |
| `ParallelAgent` | `agents: Agent[]`, `aggregator?: (results: Message[]) => Message` |
| `RouterAgent` | `router: Agent`, `routes: Record<string, Agent>` |
| `FallbackAgent` | `primary: Agent`, `fallbacks: Agent[]` |
| `CollaborativeAgent` | `agents: Agent[]`, `coordinator: Agent` |
| `HumanInLoopAgent` | `agent`, `approvalCallback: (msg: Message) => Promise<boolean>` |
| `SupervisorAgent` | `supervisor: Agent`, `workers: Agent[]` |
| `WorkingMemoryAgent` | `agent`, `memory: Memory` |

---

## Middleware

**Module:** `agenkit-ts/src/middleware`

All middleware classes accept an `agent: Agent` as their first argument and implement `Agent`.

### `RetryMiddleware`

```typescript
new RetryMiddleware(agent: Agent, {
    maxAttempts?: number;   // default: 3
    backoffFactor?: number; // default: 2.0
    retryOn?: (error: Error) => boolean;
})
```

### `TimeoutMiddleware`

```typescript
new TimeoutMiddleware(agent: Agent, {
    timeoutMs: number;
})
```

### `RateLimiter`

```typescript
new RateLimiter(agent: Agent, {
    requestsPerMinute: number;
    burst?: number;
})
```

### `CircuitBreaker`

```typescript
new CircuitBreaker(agent: Agent, {
    failureThreshold?: number;  // default: 5
    recoveryTimeoutMs?: number; // default: 60000
})
```

### `BatchingMiddleware`

```typescript
new BatchingMiddleware(agent: Agent, {
    maxBatchSize?: number; // default: 10
    maxWaitMs?: number;    // default: 100
})
```

### `CachingMiddleware`

```typescript
new CachingMiddleware(agent: Agent, {
    ttlMs?: number;        // undefined = no expiry
    storage?: CacheStorage;
})
```

### `MetricsMiddleware`

```typescript
new MetricsMiddleware(agent: Agent, {
    collector?: MetricsCollector;
})
```

---

## Memory

**Module:** `agenkit-ts/src/memory`

### `Memory` (interface)

```typescript
interface Memory {
    add(message: Message): Promise<void>;
    history(): Promise<Message[]>;
    clear(): Promise<void>;
}
```

### Implementations

| Class | Constructor | Notes |
|-------|-------------|-------|
| `InMemoryStore` | `new InMemoryStore(maxMessages?: number)` | Ephemeral |
| `RedisMemory` | `new RedisMemory({ host, port, key })` | Persistent |
| `VectorMemory` | `new VectorMemory({ store: VectorStore })` | Semantic search |
| `HierarchicalMemory` | `new HierarchicalMemory({ short, long: Memory })` | Two-tier |
| `EndlessMemory` | `new EndlessMemory(base: Memory)` | No eviction |

---

## Checkpointing

**Module:** `agenkit-ts/src/checkpointing`

### `CheckpointManager`

```typescript
new CheckpointManager({
    storage: CheckpointStorage;
    agentId: string;
    autoSave?: boolean; // default: true
})

save(state: AgentState): Promise<string>        // returns checkpointId
load(checkpointId: string): Promise<AgentState>
list(): Promise<CheckpointMeta[]>
delete(checkpointId: string): Promise<void>
```

### `CheckpointStorage` (interface)

```typescript
interface CheckpointStorage {
    write(id: string, data: Uint8Array): Promise<void>;
    read(id: string): Promise<Uint8Array>;
    list(): Promise<string[]>;
    remove(id: string): Promise<void>;
}
```

`LocalStorage` (filesystem) is the built-in implementation. `S3Storage` is available separately.

### `DurableAgent`

```typescript
new DurableAgent(agent: Agent, manager: CheckpointManager)
```

Wraps an agent with automatic checkpoint save/restore.

---

## Reasoning Techniques

**Module:** `agenkit-ts/src/techniques/reasoning`

| Class | Key Options |
|-------|-------------|
| `ChainOfThoughtAgent` | `agent`, `steps?: number` |
| `TreeOfThoughtAgent` | `agent`, `branches?: number`, `depth?: number`, `evaluator?: Agent` |
| `SelfConsistencyAgent` | `agent`, `samples?: number`, `aggregation?: string` |
| `GraphOfThoughtAgent` | `agent`, `maxNodes?: number` |
| `PlanAndSolveAgent` | `planner: Agent`, `solver: Agent` |
| `LeastToMostAgent` | `agent`, `maxSubproblems?: number` |

---

## Budget

**Module:** `agenkit-ts/src/budget`

```typescript
new BudgetLimiter({
    maxInputTokens?: number;
    maxOutputTokens?: number;
    maxTotalTokens?: number;
})

wrap(agent: Agent): Agent
remaining(): TokenBudget
```

---

## Errors

| Class | Thrown when |
|-------|-------------|
| `AgentError` | Base class |
| `AdapterError` | LLM API call fails |
| `TimeoutError` | Agent exceeds timeout |
| `CircuitOpenError` | Circuit breaker is open |
| `BudgetExceededError` | Token budget exceeded |
| `CheckpointError` | Save / load fails |
