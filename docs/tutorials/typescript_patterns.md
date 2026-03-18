# Building Production AI Agents in TypeScript

A practical guide to building robust AI agents with agenkit-ts (`@agenkit/core`). Each
tutorial is self-contained and runnable with `npx ts-node`.

---

## Introduction: TypeScript's Advantages for AI Agents

TypeScript combines JavaScript's rich async ecosystem with compile-time type safety:

- **Async/await and Promises** map directly onto LLM streaming APIs — no callbacks needed.
- **Generics** let you type tool inputs and outputs at compile time, catching schema mismatches
  before the LLM ever runs.
- **Structural typing** makes composing agents natural: if a class has a `process()` method
  with the right signature, it satisfies `Agent` automatically.
- **npm ecosystem** provides thousands of utilities for HTTP, parsing, storage, and UI.
- **Frontend-native**: run the same agent code in a React component, a Next.js API route,
  or a Node.js server — no language switch.

The trade-offs:
- Single-threaded event loop — CPU-bound work blocks other requests.
- Runtime errors for type mismatches that TypeScript couldn't catch (e.g. `JSON.parse`).
- Slower than Go or Rust for high-throughput services.

For web frontends, full-stack TypeScript projects, and rapid prototyping, TypeScript is the
right choice.

### Prerequisites

```bash
npm install @agenkit/core @agenkit/patterns
npm install -D typescript @types/node ts-node vitest fast-check
```

Node.js 20+ is required. All examples run with `npx ts-node src/main.ts`.

---

## Tutorial 1: Async Agent Chains

### Goal

Chain agents sequentially using `async/await`, then compose them using async iterators
for streaming output.

### Basic Sequential Chain

```typescript
import { Agent, Message } from '@agenkit/core';
import { SequentialAgent } from '@agenkit/patterns';

// Define two simple agents.
class SummariserAgent implements Agent {
    get name(): string { return 'summariser'; }
    get capabilities(): string[] { return ['text']; }

    async process(message: Message): Promise<Message> {
        // In a real agent, call an LLM here.
        return {
            role: 'assistant',
            content: `Summary: ${message.content.slice(0, 100)}`,
        };
    }
}

class CriticAgent implements Agent {
    get name(): string { return 'critic'; }
    get capabilities(): string[] { return ['text']; }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `Critique of "${message.content}": well-structured but could be shorter.`,
        };
    }
}

// Compose them sequentially.
const chain = new SequentialAgent({
    agents: [new SummariserAgent(), new CriticAgent()],
});

const result = await chain.process({
    role: 'user',
    content: 'Explain the theory of relativity in plain English.',
});
console.log(result.content);
```

### Manual Promise Chain

When you need intermediate values or conditional branching:

```typescript
async function processWithBranch(message: Message): Promise<Message> {
    const summariser = new SummariserAgent();
    const critic = new CriticAgent();
    const expander = new ExpanderAgent();

    const summary = await summariser.process(message);

    // Branch based on content.
    if (summary.content.length < 50) {
        // Too short — expand before critiquing.
        const expanded = await expander.process(summary);
        return critic.process(expanded);
    }

    return critic.process(summary);
}
```

### Async Iterators for Streaming

```typescript
import { AgentStream } from '@agenkit/core';

// Stream tokens from a streaming-capable agent.
async function streamToConsole(agent: AgentStream, message: Message): Promise<void> {
    const stream = agent.processStream(message);

    process.stdout.write('Response: ');
    for await (const chunk of stream) {
        process.stdout.write(chunk.delta ?? '');
    }
    console.log(); // newline at end
}

// Compose streaming with post-processing.
async function* transformStream(
    source: AsyncIterable<MessageChunk>,
    transform: (s: string) => string,
): AsyncGenerator<MessageChunk> {
    for await (const chunk of source) {
        yield { ...chunk, delta: transform(chunk.delta ?? '') };
    }
}

// Usage:
const rawStream = streamingAgent.processStream(message);
const uppercasedStream = transformStream(rawStream, s => s.toUpperCase());
for await (const chunk of uppercasedStream) {
    process.stdout.write(chunk.delta ?? '');
}
```

### Concurrent Chains with Promise.all

```typescript
async function fanOut(message: Message, agents: Agent[]): Promise<Message[]> {
    // Run all agents concurrently, fail fast on first error.
    return Promise.all(agents.map(agent => agent.process(message)));
}

async function fanOutSettled(message: Message, agents: Agent[]): Promise<Message[]> {
    // Run all agents concurrently, collect successes even if some fail.
    const results = await Promise.allSettled(
        agents.map(agent => agent.process(message))
    );

    return results
        .filter((r): r is PromiseFulfilledResult<Message> => r.status === 'fulfilled')
        .map(r => r.value);
}

const specialists = [new SummariserAgent(), new CriticAgent(), new FactCheckerAgent()];
const responses = await fanOutSettled(userMessage, specialists);
console.log(`Got ${responses.length} responses`);
```

### Key Takeaways

- `Promise.all` fails fast — use `Promise.allSettled` when partial results are acceptable.
- Async iterators (`for await...of`) are the idiomatic way to consume streaming LLM output.
- TypeScript's structural typing means any object with a matching `process()` signature
  satisfies `Agent` — no `implements` required (though explicit is clearer).

---

## Tutorial 2: Type-Safe Tools

### Goal

Use TypeScript generics to enforce correct input and output types for agent tools at
compile time.

### The Tool Interface

```typescript
import { Tool, ToolInput, ToolOutput } from '@agenkit/core';

// Generic Tool<I, O> — I is validated input, O is the return type.
interface TypedTool<I, O> {
    readonly name: string;
    readonly description: string;
    readonly inputSchema: JSONSchema;
    execute(input: I): Promise<O>;
}
```

### Defining a Typed Tool

```typescript
import { z } from 'zod'; // optional — any validator works

// 1. Define the input/output types.
interface WeatherInput {
    city: string;
    units: 'celsius' | 'fahrenheit';
}

interface WeatherOutput {
    temperature: number;
    condition: string;
    humidity: number;
}

// 2. Implement the typed tool.
class WeatherTool implements TypedTool<WeatherInput, WeatherOutput> {
    readonly name = 'get_weather';
    readonly description = 'Get current weather for a city';
    readonly inputSchema = {
        type: 'object' as const,
        properties: {
            city: { type: 'string', description: 'City name' },
            units: { type: 'string', enum: ['celsius', 'fahrenheit'] },
        },
        required: ['city', 'units'],
    };

    async execute(input: WeatherInput): Promise<WeatherOutput> {
        // TypeScript enforces input.city and input.units exist.
        const response = await fetch(
            `https://api.weather.example.com/v1/${encodeURIComponent(input.city)}?units=${input.units}`
        );
        if (!response.ok) {
            throw new Error(`weather API error: ${response.status}`);
        }
        return response.json() as Promise<WeatherOutput>;
    }
}
```

### Runtime Input Validation

TypeScript types disappear at runtime. Validate inputs from the LLM before calling tools:

```typescript
import { z } from 'zod';

const WeatherInputSchema = z.object({
    city: z.string().min(1),
    units: z.enum(['celsius', 'fahrenheit']),
});

class SafeWeatherTool extends WeatherTool {
    async execute(rawInput: unknown): Promise<WeatherOutput> {
        const parsed = WeatherInputSchema.safeParse(rawInput);
        if (!parsed.success) {
            throw new Error(`invalid tool input: ${parsed.error.message}`);
        }
        return super.execute(parsed.data);
    }
}
```

### Generic Tool Registry

```typescript
// Map tool names to their typed implementations.
class ToolRegistry {
    private tools = new Map<string, TypedTool<unknown, unknown>>();

    register<I, O>(tool: TypedTool<I, O>): this {
        this.tools.set(tool.name, tool as TypedTool<unknown, unknown>);
        return this;
    }

    get<I, O>(name: string): TypedTool<I, O> | undefined {
        return this.tools.get(name) as TypedTool<I, O> | undefined;
    }

    async execute(name: string, input: unknown): Promise<unknown> {
        const tool = this.tools.get(name);
        if (!tool) {
            throw new Error(`unknown tool: ${name}`);
        }
        return tool.execute(input);
    }

    schemas(): Array<{ name: string; schema: JSONSchema }> {
        return Array.from(this.tools.values()).map(t => ({
            name: t.name,
            schema: t.inputSchema,
        }));
    }
}

// Usage:
const registry = new ToolRegistry()
    .register(new WeatherTool())
    .register(new CalculatorTool())
    .register(new SearchTool());

// Pass tool schemas to the LLM.
const schemas = registry.schemas();

// Execute tool call from LLM response.
const result = await registry.execute('get_weather', { city: 'Paris', units: 'celsius' });
```

### Discriminated Union for Tool Results

```typescript
type ToolResult<O> =
    | { success: true; value: O }
    | { success: false; error: string };

async function safeTool<I, O>(
    tool: TypedTool<I, O>,
    input: I,
): Promise<ToolResult<O>> {
    try {
        const value = await tool.execute(input);
        return { success: true, value };
    } catch (err) {
        return { success: false, error: err instanceof Error ? err.message : String(err) };
    }
}

// TypeScript narrows the type after the check.
const result = await safeTool(new WeatherTool(), { city: 'Tokyo', units: 'celsius' });
if (result.success) {
    console.log(`Temperature: ${result.value.temperature}°C`);
} else {
    console.error(`Tool failed: ${result.error}`);
}
```

### Key Takeaways

- Generic `TypedTool<I, O>` enforces input/output types at compile time.
- Always validate LLM-supplied tool inputs at runtime — TypeScript types vanish after
  compilation.
- Discriminated unions (`{ success: true; value }` vs `{ success: false; error }`) give
  callers safe narrowing without try/catch scattered everywhere.

---

## Tutorial 3: React-style Agent UI Integration

### Goal

Integrate a streaming agenkit agent into a React application with proper abort support
and loading state management.

### Custom Hook: useAgent

```typescript
import { useState, useCallback, useRef } from 'react';
import { Agent, Message } from '@agenkit/core';

interface UseAgentState {
    response: string;
    isLoading: boolean;
    error: string | null;
}

interface UseAgentReturn extends UseAgentState {
    send: (content: string) => void;
    abort: () => void;
    reset: () => void;
}

export function useAgent(agent: Agent): UseAgentReturn {
    const [state, setState] = useState<UseAgentState>({
        response: '',
        isLoading: false,
        error: null,
    });
    const abortRef = useRef<AbortController | null>(null);

    const send = useCallback((content: string) => {
        // Cancel any in-flight request.
        abortRef.current?.abort();
        abortRef.current = new AbortController();
        const { signal } = abortRef.current;

        setState({ response: '', isLoading: true, error: null });

        const message: Message = { role: 'user', content };

        (async () => {
            try {
                const result = await agent.process(message);
                if (!signal.aborted) {
                    setState({ response: result.content, isLoading: false, error: null });
                }
            } catch (err) {
                if (!signal.aborted) {
                    setState({
                        response: '',
                        isLoading: false,
                        error: err instanceof Error ? err.message : 'Unknown error',
                    });
                }
            }
        })();
    }, [agent]);

    const abort = useCallback(() => {
        abortRef.current?.abort();
        setState(prev => ({ ...prev, isLoading: false }));
    }, []);

    const reset = useCallback(() => {
        abortRef.current?.abort();
        setState({ response: '', isLoading: false, error: null });
    }, []);

    return { ...state, send, abort, reset };
}
```

### Streaming Hook: useAgentStream

```typescript
import { useState, useCallback, useRef } from 'react';
import { AgentStream, Message } from '@agenkit/core';

export function useAgentStream(agent: AgentStream) {
    const [chunks, setChunks] = useState<string[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const abortRef = useRef<AbortController | null>(null);

    const stream = useCallback((content: string) => {
        abortRef.current?.abort();
        abortRef.current = new AbortController();
        const { signal } = abortRef.current;

        setChunks([]);
        setIsStreaming(true);
        setError(null);

        const message: Message = { role: 'user', content };

        (async () => {
            try {
                for await (const chunk of agent.processStream(message)) {
                    if (signal.aborted) break;
                    if (chunk.delta) {
                        setChunks(prev => [...prev, chunk.delta!]);
                    }
                }
            } catch (err) {
                if (!signal.aborted) {
                    setError(err instanceof Error ? err.message : 'Stream error');
                }
            } finally {
                if (!signal.aborted) {
                    setIsStreaming(false);
                }
            }
        })();
    }, [agent]);

    const abort = useCallback(() => {
        abortRef.current?.abort();
        setIsStreaming(false);
    }, []);

    return {
        response: chunks.join(''),
        chunks,
        isStreaming,
        error,
        stream,
        abort,
    };
}
```

### React Component

```tsx
import React from 'react';
import { useAgentStream } from './useAgentStream';
import { MyStreamingAgent } from './agents';

export function AgentChat(): JSX.Element {
    const agent = React.useMemo(() => new MyStreamingAgent(), []);
    const { response, isStreaming, error, stream, abort } = useAgentStream(agent);
    const [input, setInput] = React.useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;
        stream(input);
        setInput('');
    };

    return (
        <div className="agent-chat">
            <div className="response">
                {error && <p className="error">{error}</p>}
                <p>{response}</p>
                {isStreaming && <span className="cursor">|</span>}
            </div>
            <form onSubmit={handleSubmit}>
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="Ask something..."
                    disabled={isStreaming}
                />
                <button type="submit" disabled={isStreaming || !input.trim()}>
                    Send
                </button>
                {isStreaming && (
                    <button type="button" onClick={abort}>
                        Stop
                    </button>
                )}
            </form>
        </div>
    );
}
```

### Key Takeaways

- Always pair `AbortController` with streaming calls so the user can cancel.
- Reset the abort controller on each new call to prevent stale signals.
- Use `useCallback` + `useRef` for the controller — not state — to avoid re-render loops.
- Check `signal.aborted` before updating state inside async functions.

---

## Tutorial 4: Property-Based Testing with fast-check

### Goal

Use `fast-check` to verify agent invariants hold across thousands of random inputs.

### Setup

```bash
npm install -D fast-check vitest
```

### Defining Arbitraries

```typescript
import * as fc from 'fast-check';
import { Message, Agent } from '@agenkit/core';

// Arbitrary that generates valid Messages.
const messageArb = fc.record({
    role: fc.constantFrom('user', 'assistant', 'system') as fc.Arbitrary<'user' | 'assistant' | 'system'>,
    content: fc.string({ minLength: 1, maxLength: 500 }),
    metadata: fc.option(fc.dictionary(fc.string(), fc.string()), { nil: undefined }),
});

// Arbitrary that generates non-empty user messages.
const userMessageArb = fc.record({
    role: fc.constant('user' as const),
    content: fc.string({ minLength: 1, maxLength: 500 }),
});
```

### Writing Property Tests

```typescript
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { EchoAgent, UpperAgent } from './agents';
import { SequentialAgent } from '@agenkit/patterns';

describe('EchoAgent properties', () => {
    const agent = new EchoAgent();

    it('always returns role=assistant', async () => {
        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const result = await agent.process(msg);
                expect(result.role).toBe('assistant');
            }),
            { numRuns: 200 },
        );
    });

    it('never returns empty content for non-empty input', async () => {
        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const result = await agent.process(msg);
                expect(result.content.length).toBeGreaterThan(0);
            }),
        );
    });

    it('is deterministic — same input produces same output', async () => {
        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const r1 = await agent.process(msg);
                const r2 = await agent.process(msg);
                expect(r1.content).toBe(r2.content);
                expect(r1.role).toBe(r2.role);
            }),
        );
    });
});

describe('SequentialAgent properties', () => {
    const seq = new SequentialAgent({
        agents: [new EchoAgent(), new UpperAgent()],
    });

    it('output of UpperAgent is always uppercase', async () => {
        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const result = await seq.process(msg);
                expect(result.content).toBe(result.content.toUpperCase());
            }),
        );
    });

    it('sequential preserves role=assistant at every stage', async () => {
        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const result = await seq.process(msg);
                expect(result.role).toBe('assistant');
            }),
        );
    });
});

describe('Middleware properties', () => {
    it('retry does not change response when inner succeeds', async () => {
        const inner = new EchoAgent();
        const withRetry = addRetry(inner, { maxRetries: 3, backoff: 0 });

        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const direct = await inner.process(msg);
                const retried = await withRetry.process(msg);
                expect(retried.content).toBe(direct.content);
            }),
        );
    });

    it('timeout does not alter content within deadline', async () => {
        const inner = new EchoAgent(); // fast agent
        const withTimeout = addTimeout(inner, 5000); // 5 second deadline

        await fc.assert(
            fc.asyncProperty(userMessageArb, async msg => {
                const direct = await inner.process(msg);
                const timed = await withTimeout.process(msg);
                expect(timed.content).toBe(direct.content);
            }),
        );
    });
});
```

### Shrinking and Debugging

When `fast-check` finds a failing case, it automatically shrinks it to the minimal
reproducer:

```typescript
it('debug: find minimal failing input', async () => {
    await fc.assert(
        fc.asyncProperty(userMessageArb, async msg => {
            const result = await myBuggyAgent.process(msg);
            // This invariant fails for certain Unicode inputs.
            expect(result.content).not.toContain('\u0000');
        }),
        {
            numRuns: 1000,
            verbose: true, // print all cases
        },
    );
    // fast-check will print the minimal failing input after shrinking.
});
```

### Key Takeaways

- `fc.asyncProperty` supports async agent calls natively — no extra wrapping needed.
- Increase `numRuns` in CI for more thorough coverage (`{ numRuns: 1000 }`).
- Use `fc.constantFrom` to generate from a fixed set (e.g. roles) rather than arbitrary strings.
- `verbose: true` shows the search path, helping you understand what fast-check explored.

---

## Tutorial 5: Error Boundary Patterns

### Goal

Handle errors gracefully across async boundaries so a single failed tool call or LLM
timeout never crashes the entire agent pipeline.

### Typed Error Hierarchy

```typescript
// Base error class for all agenkit errors.
export class AgentError extends Error {
    constructor(
        message: string,
        public readonly cause?: unknown,
    ) {
        super(message);
        this.name = 'AgentError';
        // Maintain prototype chain in transpiled code.
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

export class TransientError extends AgentError {
    constructor(message: string, cause?: unknown) {
        super(message, cause);
        this.name = 'TransientError';
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

export class RateLimitError extends TransientError {
    constructor(
        public readonly retryAfterMs: number,
        cause?: unknown,
    ) {
        super(`rate limited, retry after ${retryAfterMs}ms`, cause);
        this.name = 'RateLimitError';
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

export class TimeoutError extends TransientError {
    constructor(timeoutMs: number, cause?: unknown) {
        super(`timed out after ${timeoutMs}ms`, cause);
        this.name = 'TimeoutError';
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

export class InvalidInputError extends AgentError {
    constructor(message: string, cause?: unknown) {
        super(message, cause);
        this.name = 'InvalidInputError';
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
```

### Result Type Pattern

Avoid throwing across async boundaries; use a Result type instead:

```typescript
type Ok<T> = { ok: true; value: T };
type Err<E> = { ok: false; error: E };
type Result<T, E = AgentError> = Ok<T> | Err<E>;

function ok<T>(value: T): Ok<T> { return { ok: true, value }; }
function err<E>(error: E): Err<E> { return { ok: false, error }; }

async function safeProcess(agent: Agent, message: Message): Promise<Result<Message>> {
    try {
        const result = await agent.process(message);
        return ok(result);
    } catch (e) {
        if (e instanceof AgentError) {
            return err(e);
        }
        return err(new AgentError('unexpected error', e));
    }
}

// Caller gets safe narrowing:
const result = await safeProcess(agent, message);
if (result.ok) {
    console.log(result.value.content);
} else if (result.error instanceof RateLimitError) {
    await sleep(result.error.retryAfterMs);
} else {
    console.error('non-retryable:', result.error.message);
}
```

### Retry with Exponential Backoff

```typescript
interface RetryOptions {
    maxRetries: number;
    initialDelayMs: number;
    maxDelayMs: number;
    jitterMs?: number;
}

async function withRetry<T>(
    fn: () => Promise<T>,
    options: RetryOptions,
): Promise<T> {
    const { maxRetries, initialDelayMs, maxDelayMs, jitterMs = 100 } = options;
    let lastError: AgentError | undefined;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (e) {
            const error = e instanceof AgentError ? e : new AgentError('unexpected', e);

            if (!(error instanceof TransientError) || attempt === maxRetries) {
                throw error;
            }

            lastError = error;

            // Exponential backoff with jitter.
            const delay = Math.min(
                initialDelayMs * 2 ** attempt + Math.random() * jitterMs,
                maxDelayMs,
            );

            if (error instanceof RateLimitError) {
                // Respect the server's retry-after header.
                await sleep(Math.max(delay, error.retryAfterMs));
            } else {
                await sleep(delay);
            }
        }
    }

    throw lastError ?? new AgentError('retry limit reached');
}

// Usage:
const result = await withRetry(
    () => agent.process(message),
    { maxRetries: 3, initialDelayMs: 500, maxDelayMs: 10_000 },
);
```

### Pipeline Error Boundary

```typescript
// Wrap a pipeline stage so errors are collected, not thrown.
async function collectErrors<T>(
    items: T[],
    fn: (item: T) => Promise<Message>,
): Promise<{ results: Message[]; errors: Array<{ item: T; error: AgentError }> }> {
    const results: Message[] = [];
    const errors: Array<{ item: T; error: AgentError }> = [];

    await Promise.allSettled(
        items.map(async item => {
            try {
                results.push(await fn(item));
            } catch (e) {
                errors.push({
                    item,
                    error: e instanceof AgentError ? e : new AgentError('unknown', e),
                });
            }
        })
    );

    return { results, errors };
}

// Usage:
const messages = [msg1, msg2, msg3];
const { results, errors } = await collectErrors(messages, msg => agent.process(msg));

console.log(`Processed: ${results.length}, Failed: ${errors.length}`);
errors.forEach(({ item, error }) =>
    console.error(`Failed for "${item.content.slice(0, 40)}": ${error.message}`)
);
```

### Timeout Wrapper

```typescript
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
    let timeoutId: ReturnType<typeof setTimeout>;

    const timeout = new Promise<never>((_, reject) => {
        timeoutId = setTimeout(() => {
            reject(new TimeoutError(ms));
        }, ms);
    });

    return Promise.race([promise, timeout]).finally(() => {
        clearTimeout(timeoutId);
    });
}

// Usage:
const result = await withTimeout(agent.process(message), 10_000);
```

### Key Takeaways

- Set `Object.setPrototypeOf(this, new.target.prototype)` in every custom Error subclass
  to fix `instanceof` checks after TypeScript/Babel transpilation.
- Use a `Result<T, E>` type for functions that can fail predictably — keep `throw` for
  truly unexpected errors.
- `Promise.race([promise, timeout])` combined with `clearTimeout` in `finally` prevents
  timer leaks even on success.
- Always check `e instanceof AgentError` before wrapping — avoid double-wrapping errors.

---

## Next Steps

- **Reference**: `agenkit-ts/docs/API.md` — complete package documentation
- **Examples**: `examples/typescript/` — 15+ runnable examples
- **Patterns**: `docs/PATTERNS.md` — canonical pattern catalogue (all languages)
- **Property tests**: `agenkit-ts/src/__tests__/property.test.ts` — 30 property tests
- **Type definitions**: `agenkit-ts/src/index.d.ts` — full TypeScript types

```bash
# Run all TypeScript tests
cd agenkit-ts && npm test

# Run property tests only
npm test -- --reporter=verbose property

# Type-check without running
npx tsc --noEmit

# Coverage report
npm run test:coverage
```
