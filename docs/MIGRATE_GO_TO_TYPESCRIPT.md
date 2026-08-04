# Quick Reference: Go → TypeScript Migration
<!-- verified: v0.76.0 -->
**For**: Go developers migrating Agenkit code to TypeScript
**Time**: 15 minute read
**Full Details**: See [Go Language Profile](LANGUAGE_PROFILE_GO.md) and [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md)

---

## Key Differences at a Glance

| Aspect | Go | TypeScript |
|--------|----|----|
| **Typing** | Static, explicit | Static, inferred |
| **Errors** | `(result, error)` returns | Exceptions (`try/catch`) |
| **Concurrency** | Goroutines + channels | Promises + async/await |
| **Memory** | GC, no manual management | GC (V8), automatic |
| **Performance** | Fast (compiled) | Moderate (JIT) |
| **Deployment** | Single binary | Node.js runtime + modules |

---

## Message Creation

### Go
```go
import "github.com/scttfrdmn/agenkit-go"

msg := agenkit.Message{
    Role:    agenkit.RoleUser,
    Content: "Hello!",
    Metadata: map[string]interface{}{
        "key": "value",
    },
}
```

### TypeScript
```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
    role: 'user',
    content: 'Hello!',
    metadata: {
        key: 'value',
    },
};
```

**Changes**:
- Import path: `agenkit-go` → `@agenkit/core`
- Struct literal → Object literal
- Constants: `agenkit.RoleUser` → `'user'` string
- Type: `map[string]interface{}` → `Record<string, any>` or plain object
- Optional commas after last field

---

## Agent Implementation

### Go
```go
type MyAgent struct {
    name string
}

func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return []string{"text"}
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    return agenkit.Message{
        Role:    agenkit.RoleAssistant,
        Content: "Response",
    }, nil
}
```

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    constructor(private agentName: string) {}

    get name(): string {
        return this.agentName;
    }

    get capabilities(): string[] {
        return ['text'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: 'Response',
        };
    }
}
```

**Changes**:
- Struct → `class` with constructor
- Methods → `get` accessors or `async` methods
- `ctx context.Context` → removed (no explicit context)
- `(result, error)` → `Promise<result>` (errors become exceptions)
- `[]string` → `string[]`

---

## Error Handling

### Go
```go
result, err := agent.Process(ctx, msg)
if err != nil {
    return nil, fmt.Errorf("process failed: %w", err)
}
// Use result
```

### TypeScript
```typescript
try {
    const result = await agent.process(message);
    // Use result
} catch (error) {
    if (error instanceof AgentError) {
        throw new Error(`process failed: ${error.message}`);
    }
    throw error;
}
```

**Changes**:
- `if err != nil` → `try/catch` block
- Error wrapping: `fmt.Errorf(..., %w, err)` → `throw new Error(...)`
- No tuple unpacking needed
- Error type checking: type assertion → `instanceof`

---

## Concurrency

### Go (Goroutines)
```go
// Launch goroutine
go func() {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        log.Printf("Error: %v", err)
        return
    }
    // Use result
}()

// Wait for multiple
var wg sync.WaitGroup
for _, agent := range agents {
    wg.Add(1)
    go func(a agenkit.Agent) {
        defer wg.Done()
        _, _ = a.Process(ctx, msg)
    }(agent)
}
wg.Wait()
```

### TypeScript (Promises)
```typescript
// Launch async operation
const processAsync = async () => {
    try {
        const result = await agent.process(message);
        // Use result
    } catch (error) {
        console.error(`Error: ${error}`);
    }
};

// Create task
processAsync(); // Fire and forget

// Wait for multiple
const results = await Promise.all(
    agents.map(agent => agent.process(message))
);
```

**Changes**:
- `go func()` → `async () => {}` with function invocation
- `sync.WaitGroup` → `Promise.all()`
- `context.Context` → implicit in Promise chain
- Channels → Event emitters or callbacks
- No goroutine closure capture issues (different scoping)

---

## Patterns

### Sequential

**Go**:
```go
sequential := patterns.NewSequential([]agenkit.Agent{agent1, agent2})
result, err := sequential.Process(ctx, msg)
```

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2],
});
const result = await sequential.process(message);
```

### Parallel

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{agentA, agentB})
result, err := parallel.Process(ctx, msg)
```

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB],
});
const result = await parallel.process(message);
```

---

## Common Gotchas

### 1. Context Cancellation

**Go**: Explicit `ctx.Done()` checks
```go
select {
case <-ctx.Done():
    return nil, ctx.Err()
default:
    // Continue
}
```

**TypeScript**: AbortController for cancellation
```typescript
const controller = new AbortController();
const signal = controller.signal;

// Check cancellation
if (signal.aborted) {
    throw new Error('Operation cancelled');
}

// Cancel after timeout
setTimeout(() => controller.abort(), 5000);
```

### 2. Nil vs undefined

**Go**: `nil` for pointers, slices, maps, interfaces
**TypeScript**: `undefined` or `null` for missing values

```go
// Go
var msg *Message = nil  // nil pointer
if msg != nil {
    // Use msg
}
```

```typescript
// TypeScript
let msg: Message | undefined = undefined;
if (msg !== undefined) {
    // Use msg
}

// Or use optional chaining
const content = msg?.content;
```

### 3. Type Assertions

**Go**: Runtime type checking
```go
value, ok := metadata["key"].(string)
if !ok {
    return nil, errors.New("wrong type")
}
```

**TypeScript**: Type guards and runtime checks
```typescript
// Type guard
function isString(value: any): value is string {
    return typeof value === 'string';
}

const value = metadata['key'];
if (!isString(value)) {
    throw new Error('wrong type');
}
```

### 4. Array/Slice Differences

**Go**: Slices have capacity, arrays are fixed
**TypeScript**: Only dynamic arrays (like Go slices)

```go
// Go
slice := make([]string, 0, 10)  // length 0, capacity 10
slice = append(slice, "item")
```

```typescript
// TypeScript
const array: string[] = [];  // No capacity concept
array.push('item');
```

### 5. String Handling

**Go**: Strings are immutable byte slices
**TypeScript**: Strings are immutable, UTF-16 encoded

```go
// Go
str := "Hello"
length := len(str)  // Byte length
runes := []rune(str)  // Unicode code points
```

```typescript
// TypeScript
const str = 'Hello';
const length = str.length;  // Character count (UTF-16 code units)
const codePoints = Array.from(str);  // Code points
```

---

## Testing

### Go
```go
func TestAgent(t *testing.T) {
    agent := NewMyAgent()
    msg := agenkit.Message{Role: agenkit.RoleUser, Content: "Test"}

    result, err := agent.Process(context.Background(), msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if result.Content != "Expected" {
        t.Errorf("got %q, want %q", result.Content, "Expected")
    }
}
```

### TypeScript
```typescript
import { describe, it, expect } from 'vitest';
import { Message } from '@agenkit/core';

describe('MyAgent', () => {
    it('should process message correctly', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: 'Test',
        };

        const result = await agent.process(msg);

        expect(result.content).toBe('Expected');
    });
});
```

**Changes**:
- `func TestXxx(t *testing.T)` → `describe/it` blocks
- `t.Fatalf/t.Errorf` → `expect()` assertions
- No `context.Background()` needed
- Tests are async by default
- Use Vitest, Jest, or similar framework

---

## Performance Considerations

| Operation | Go | TypeScript | Notes |
|-----------|----|----|-------|
| Agent creation | ~100ns | ~500ns | TS 5x slower |
| Message processing | ~1μs | ~5μs | TS 5x slower |
| Sequential (3 agents) | ~3μs | ~15μs | TS 5x slower |
| Parallel (3 agents) | ~1μs | ~5μs | Single-threaded event loop |

**When to use TypeScript**:
- Web/browser integration (only option)
- Node.js backend services
- Rapid prototyping with npm ecosystem
- Full-stack JavaScript/TypeScript projects
- When team expertise is in TypeScript

**When to keep Go**:
- CPU-intensive workloads
- High-concurrency servers (millions of goroutines)
- Memory-constrained environments
- Single-binary deployment preferred
- When true parallelism is needed

---

## Migration Checklist

- [ ] Replace `struct` with `class` or interface
- [ ] Convert `(result, error)` returns to `Promise<result>` + exceptions
- [ ] Change goroutines to `async/await`
- [ ] Remove `context.Context` parameter
- [ ] Update imports: `agenkit-go` → `@agenkit/core`
- [ ] Replace type assertions with type guards
- [ ] Convert tests: `*testing.T` → Vitest/Jest
- [ ] Update error handling: `if err != nil` → `try/catch`
- [ ] Change constants: `agenkit.RoleUser` → `'user'`
- [ ] Update build: `go build` → `npm run build`
- [ ] Configure TypeScript compiler (`tsconfig.json`)
- [ ] Set up package.json with dependencies

---

## Quick Start

```bash
# Go project structure
agenkit-go/
├── go.mod
├── main.go
└── agent.go

# TypeScript equivalent
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── main.ts
│   └── agent.ts
└── dist/  # Compiled output
```

**Build/Run**:
```bash
# Go
go build -o myagent
./myagent

# TypeScript
npm install
npm run build  # Compile TS to JS
npm start      # Run compiled code

# Or dev mode (ts-node)
npm run dev
```

**Project Setup**:
```bash
# Initialize TypeScript project
npm init -y
npm install typescript @types/node --save-dev
npm install @agenkit/core @agenkit/patterns

# Create tsconfig.json
npx tsc --init

# Add scripts to package.json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/main.js",
    "dev": "ts-node src/main.ts",
    "test": "vitest"
  }
}
```

---

## Full Resources

- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms
- [TypeScript Documentation](https://www.typescriptlang.org/docs/) - Official TypeScript docs
- [Agenkit TypeScript Examples](../agenkit-ts/examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
