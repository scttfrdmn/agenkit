# Testing Framework — Agenkit TypeScript

## Current State

The TypeScript implementation has **204 tests across 9 pattern test files** with solid coverage. Mock utilities are available for both unit and property-based testing.

**Test Coverage:**
- Core agent interface: 15+ tests
- Message handling: 20+ tests
- Patterns (Sequential, Parallel, Reflection, etc.): 100+ tests
- Middleware (Retry, Timeout, CircuitBreaker, etc.): 40+ tests
- Property-based tests (fast-check): 30 tests

---

## Vitest Setup

### Installation

```bash
npm install --save-dev vitest @vitest/coverage-v8
```

### vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.test.ts', 'src/**/__tests__/**'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
      },
    },
    testTimeout: 10000,
  },
});
```

### package.json Scripts

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui"
  }
}
```

### Running Tests

```bash
# All tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage

# Specific file
npx vitest run src/__tests__/patterns/sequential.test.ts

# Matching pattern
npx vitest run --reporter verbose --testNamePattern "sequential"
```

---

## Testing Patterns

### Basic Agent Test

```typescript
import { describe, it, expect } from 'vitest';
import { LocalAgent, createMessage } from '@agenkit/core';

describe('LocalAgent', () => {
  it('processes a message and returns assistant response', async () => {
    const agent = new LocalAgent({
      name: 'echo',
      process: async (msg) => ({
        role: 'assistant',
        content: `Echo: ${msg.content}`,
      }),
    });

    const response = await agent.process(createMessage('user', 'Hello'));

    expect(response.role).toBe('assistant');
    expect(response.content).toBe('Echo: Hello');
  });

  it('throws on empty content', async () => {
    const agent = new LocalAgent({
      name: 'strict',
      process: async (msg) => {
        if (!msg.content) throw new Error('empty content');
        return { role: 'assistant', content: 'ok' };
      },
    });

    await expect(agent.process(createMessage('user', ''))).rejects.toThrow('empty content');
  });
});
```

### Mocking Agents

```typescript
import { describe, it, expect, vi } from 'vitest';
import type { Agent, Message } from '@agenkit/core';
import { createMessage } from '@agenkit/core';

// Simple mock agent factory
function createMockAgent(responses: Array<string | Error>): Agent {
  let callIndex = 0;

  return {
    name: 'mock-agent',
    process: vi.fn(async (_msg: Message): Promise<Message> => {
      const response = responses[callIndex % responses.length];
      callIndex++;

      if (response instanceof Error) {
        throw response;
      }

      return { role: 'assistant', content: response };
    }),
  };
}

describe('RetryMiddleware with mock', () => {
  it('retries on failure and succeeds on third attempt', async () => {
    import { RetryMiddleware } from '@agenkit/core/middleware';

    const mock = createMockAgent([
      new Error('network error'),
      new Error('network error'),
      'success',
    ]);

    const agent = new RetryMiddleware(mock, {
      maxRetries: 3,
      initialDelayMs: 0, // no delay in tests
    });

    const response = await agent.process(createMessage('user', 'hello'));

    expect(response.content).toBe('success');
    expect(mock.process).toHaveBeenCalledTimes(3);
  });
});
```

### Cycling Mock (like Zig's MockAgent)

```typescript
import { vi } from 'vitest';
import type { Agent, Message } from '@agenkit/core';

class CyclingMockAgent implements Agent {
  readonly name = 'mock';
  private callCount = 0;
  readonly process = vi.fn();

  constructor(private readonly responses: string[]) {
    this.process.mockImplementation(async (_msg: Message): Promise<Message> => {
      const response = this.responses[this.callCount % this.responses.length];
      this.callCount++;
      return { role: 'assistant', content: response };
    });
  }

  getCallCount(): number {
    return this.callCount;
  }

  resetCallCount(): void {
    this.callCount = 0;
    this.process.mockClear();
  }
}

// Usage in tests
const mock = new CyclingMockAgent(['Response 1', 'Response 2', 'Response 3']);

const r1 = await mock.process(createMessage('user', 'first'));
expect(r1.content).toBe('Response 1');

const r2 = await mock.process(createMessage('user', 'second'));
expect(r2.content).toBe('Response 2');

expect(mock.getCallCount()).toBe(2);
mock.resetCallCount();
```

---

## Async Test Patterns

### Testing Concurrent Operations

```typescript
import { describe, it, expect } from 'vitest';
import { ParallelAgent, LocalAgent, createMessage } from '@agenkit/core';

describe('ParallelAgent', () => {
  it('runs all agents concurrently', async () => {
    const timings: number[] = [];

    function makeTimedAgent(name: string, delayMs: number): Agent {
      return new LocalAgent({
        name,
        process: async (msg) => {
          timings.push(Date.now());
          await new Promise((r) => setTimeout(r, delayMs));
          return { role: 'assistant', content: `${name}: done` };
        },
      });
    }

    const parallel = new ParallelAgent([
      makeTimedAgent('a', 50),
      makeTimedAgent('b', 50),
      makeTimedAgent('c', 50),
    ]);

    const start = Date.now();
    const results = await parallel.processAll(createMessage('user', 'go'));
    const elapsed = Date.now() - start;

    expect(results).toHaveLength(3);
    // Should complete in ~50ms not ~150ms (sequential would be 150ms)
    expect(elapsed).toBeLessThan(120);
  });
});
```

### Testing Timeouts

```typescript
import { describe, it, expect } from 'vitest';
import { LocalAgent, createMessage } from '@agenkit/core';
import { TimeoutMiddleware, TimeoutError } from '@agenkit/core/middleware';

describe('TimeoutMiddleware', () => {
  it('throws TimeoutError when agent takes too long', async () => {
    const slow = new LocalAgent({
      name: 'slow',
      process: async () => {
        await new Promise((r) => setTimeout(r, 500));
        return { role: 'assistant', content: 'too late' };
      },
    });

    const agent = new TimeoutMiddleware(slow, { timeoutMs: 50 });

    await expect(
      agent.process(createMessage('user', 'hello'))
    ).rejects.toThrow(TimeoutError);
  });

  it('succeeds when agent responds within timeout', async () => {
    const fast = new LocalAgent({
      name: 'fast',
      process: async (msg) => ({ role: 'assistant', content: `ok: ${msg.content}` }),
    });

    const agent = new TimeoutMiddleware(fast, { timeoutMs: 1000 });
    const response = await agent.process(createMessage('user', 'hello'));

    expect(response.content).toBe('ok: hello');
  });
});
```

### Testing Streaming

```typescript
import { describe, it, expect } from 'vitest';
import { LocalAgent, createMessage } from '@agenkit/core';

describe('Streaming', () => {
  it('collects all chunks from processStream', async () => {
    const agent = new LocalAgent({
      name: 'streamer',
      process: async (msg) => ({ role: 'assistant', content: msg.content }),
      processStream: async function* (msg) {
        const words = (msg.content as string).split(' ');
        for (const word of words) {
          yield { role: 'assistant' as const, content: word };
        }
      },
    });

    const chunks: string[] = [];
    for await (const chunk of agent.processStream!(createMessage('user', 'hello world'))) {
      chunks.push(chunk.content as string);
    }

    expect(chunks).toEqual(['hello', 'world']);
  });
});
```

---

## Property-Based Tests with fast-check

### Installation

```bash
npm install --save-dev fast-check
```

### Message Invariants

```typescript
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { createMessage, createValidatedMessage } from '@agenkit/core';

describe('Message property tests', () => {
  it('createMessage always produces a valid message', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('user', 'assistant', 'system', 'tool'),
        fc.string({ minLength: 1, maxLength: 1000 }),
        (role, content) => {
          const msg = createMessage(role, content);
          expect(msg.role).toBe(role);
          expect(msg.content).toBe(content);
          expect(typeof msg.timestamp).toBe('string');
        }
      )
    );
  });

  it('createValidatedMessage rejects invalid roles', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }).filter((s) => !['user', 'assistant', 'system', 'tool', 'agent'].includes(s)),
        (invalidRole) => {
          expect(() => createValidatedMessage(invalidRole, 'content')).toThrow();
        }
      )
    );
  });

  it('agent process is deterministic for same input', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1 }),
        async (content) => {
          const agent = new LocalAgent({
            name: 'deterministic',
            process: async (msg) => ({ role: 'assistant', content: `echo:${msg.content}` }),
          });

          const msg = createMessage('user', content);
          const r1 = await agent.process(msg);
          const r2 = await agent.process(msg);

          expect(r1.content).toEqual(r2.content);
        }
      )
    );
  });
});
```

### Middleware Invariants

```typescript
import fc from 'fast-check';

describe('RetryMiddleware property tests', () => {
  it('succeeds after at most maxRetries+1 total calls on always-succeeding agent', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 5 }),
        async (maxRetries) => {
          let callCount = 0;
          const agent = new LocalAgent({
            name: 'counting',
            process: async () => {
              callCount++;
              return { role: 'assistant', content: 'ok' };
            },
          });

          const withRetry = new RetryMiddleware(agent, {
            maxRetries,
            initialDelayMs: 0,
          });

          callCount = 0;
          await withRetry.process(createMessage('user', 'hello'));

          // Should call once on success (no retries needed)
          expect(callCount).toBe(1);
        }
      )
    );
  });
});
```

---

## Snapshot Testing

### Message Snapshots

```typescript
import { describe, it, expect } from 'vitest';
import { createMessage } from '@agenkit/core';

describe('Message snapshots', () => {
  it('matches expected structure', () => {
    const msg = createMessage('user', 'Hello, agent!', { session_id: 'test-123' });

    // Strip dynamic timestamp for snapshot stability
    const { timestamp: _ts, ...stable } = msg;

    expect(stable).toMatchSnapshot();
  });
});
```

Run once to create snapshots:
```bash
npx vitest run --reporter verbose
```

Update snapshots after intentional changes:
```bash
npx vitest run --update-snapshots
```

---

## Test Organization

### Recommended File Structure

```
src/
├── __tests__/
│   ├── core/
│   │   ├── message.test.ts      # Message creation + validation
│   │   └── interfaces.test.ts   # Agent interface
│   ├── middleware/
│   │   ├── retry.test.ts
│   │   ├── timeout.test.ts
│   │   └── circuit-breaker.test.ts
│   ├── patterns/
│   │   ├── sequential.test.ts
│   │   ├── parallel.test.ts
│   │   ├── reflection.test.ts
│   │   └── react.test.ts
│   ├── property/
│   │   └── message.property.test.ts
│   └── integration/
│       └── pipeline.integration.test.ts
```

### Best Practices

1. **Use `std.testing.allocator` equivalent** — In Vitest, prefer `vi.fn()` over ad-hoc stubs so call counts are tracked

2. **Test error paths explicitly** — Don't just test happy paths:
   ```typescript
   it('handles network errors', async () => {
     const agent = createMockAgent([new Error('ECONNREFUSED')]);
     await expect(agent.process(message)).rejects.toThrow('ECONNREFUSED');
   });
   ```

3. **Use `afterEach` for cleanup** — Reset mock state between tests:
   ```typescript
   afterEach(() => {
     vi.clearAllMocks();
   });
   ```

4. **Descriptive test names** — `'retries 3 times on network error'` not `'test1'`

5. **Avoid real LLM calls** — Mock LLM agents in unit tests; use integration tests for real API calls

6. **Set `testTimeout`** — Async tests should have explicit timeouts to avoid hanging:
   ```typescript
   it('completes within 5 seconds', { timeout: 5000 }, async () => {
     // ...
   });
   ```

---

## Related

- #360 — TypeScript property-based test coverage (COMPLETED)
- #217 — Test coverage milestone (COMPLETED)
- [GETTING_STARTED.md](GETTING_STARTED.md) — Vitest setup
- [API.md](API.md) — Agent and middleware interfaces
