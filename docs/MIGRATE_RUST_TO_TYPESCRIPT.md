# Quick Reference: Rust → TypeScript Migration

**For**: Rust developers migrating Agenkit code to TypeScript
**Time**: 15 minute read
**Full Details**: See [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) and [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md)

---

## Key Differences at a Glance

| Aspect | Rust | TypeScript |
|--------|------|------------|
| **Typing** | Static, nominal | Static, structural |
| **Errors** | `Result<T, E>` | Exceptions (`try/catch`) |
| **Concurrency** | tokio futures + threads | Promises (single-threaded) |
| **Memory** | Ownership (no GC) | GC (V8) |
| **Performance** | Very fast (compiled) | Moderate (JIT) |
| **Deployment** | Single binary | Node.js + modules |

---

## Message Creation

### Rust
```rust
use agenkit::{Message, Role};

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata: HashMap::new(),
    ..Default::default()
};

// With metadata
let mut metadata = HashMap::new();
metadata.insert("key".to_string(), json!("value"));

let msg = Message {
    role: Role::Assistant,
    content: "Response".to_string(),
    metadata,
    ..Default::default()
};
```

### TypeScript
```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
    role: 'user',
    content: 'Hello!',
};

// With metadata
const msg2: Message = {
    role: 'assistant',
    content: 'Response',
    metadata: {
        key: 'value',
    },
};
```

**Changes**:
- Enum: `Role::User` → `'user'` string literal
- HashMap → object literal `{}`
- No `.to_string()` needed (strings are primitives)
- No `..Default::default()` (optional fields just omitted)
- Import path: `agenkit` → `@agenkit/core`

---

## Agent Implementation

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, AgentError, Role};

struct MyAgent {
    name: String,
    config: Config,
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text".to_string(), "analysis".to_string()]
    }

    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        Ok(Message {
            role: Role::Assistant,
            content: format!("Processed: {}", msg.content),
            ..Default::default()
        })
    }
}
```

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    constructor(private config: Config) {}

    get name(): string {
        return 'my-agent';
    }

    get capabilities(): string[] {
        return ['text', 'analysis'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `Processed: ${message.content}`,
        };
    }
}
```

**Changes**:
- Trait → Interface (both compile-time checked)
- `#[async_trait]` → native `async` (no macro needed)
- `Result<Message, AgentError>` → `Promise<Message>` (errors via exceptions)
- `&self` → `this` (no explicit borrowing)
- `Vec<String>` → `string[]` (array type)
- `format!` → template literals `` `text ${var}` ``

---

## Error Handling

### Rust
```rust
// Result type forces explicit handling
match agent.process(msg).await {
    Ok(response) => println!("Success: {}", response.content),
    Err(e) => eprintln!("Error: {}", e),
}

// Or use ? operator
async fn handle_message(msg: Message) -> Result<Message, AgentError> {
    let validated = validate_message(&msg)?;  // Early return on error
    let result = agent.process(validated).await?;
    Ok(result)
}

// Pattern match on specific errors
match process_message(&agent, msg).await {
    Ok(response) => Ok(response),
    Err(AgentError::Timeout(_)) => {
        // Retry on timeout
        agent.process(msg).await
    }
    Err(e) => Err(e),
}
```

### TypeScript
```typescript
// Try-catch blocks
try {
    const response = await agent.process(msg);
    console.log(`Success: ${response.content}`);
} catch (error) {
    console.error(`Error: ${error}`);
}

// Error propagation (throw)
async function handleMessage(msg: Message): Promise<Message> {
    const validated = validateMessage(msg);  // Throws on error
    const result = await agent.process(validated);
    return result;
}

// Catch specific error types
try {
    const response = await processMessage(agent, msg);
} catch (error) {
    if (error instanceof TimeoutError) {
        // Retry on timeout
        return await agent.process(msg);
    }
    throw error;  // Re-throw other errors
}
```

**Changes**:
- `Result<T, E>` → `Promise<T>` (errors thrown, not returned)
- `match` or `?` → `try/catch` (implicit error propagation)
- `Ok(value)` → `return value`
- `Err(error)` → `throw error`
- Pattern matching → `instanceof` checks
- Compile-time error checking → Runtime error checking

---

## Concurrency

### Rust (tokio)
```rust
use tokio;

// Spawn task on runtime
tokio::spawn(async move {
    match agent.process(msg).await {
        Ok(resp) => println!("Success: {}", resp.content),
        Err(e) => eprintln!("Error: {}", e),
    }
});

// Join multiple tasks (parallel)
let (res1, res2, res3) = tokio::join!(
    agent1.process(msg.clone()),
    agent2.process(msg.clone()),
    agent3.process(msg.clone())
);

// Select: first to complete
tokio::select! {
    res = agent1.process(msg.clone()) => println!("Agent 1: {:?}", res),
    res = agent2.process(msg.clone()) => println!("Agent 2: {:?}", res),
}

// Channels for communication
let (tx, mut rx) = tokio::sync::mpsc::channel(32);
tx.send(message).await.unwrap();
while let Some(msg) = rx.recv().await {
    // Process message
}
```

### TypeScript (Promises)
```typescript
// Create async task (no spawning needed)
async function processAsync() {
    try {
        const resp = await agent.process(msg);
        console.log(`Success: ${resp.content}`);
    } catch (error) {
        console.error(`Error: ${error}`);
    }
}

// Run immediately (fire and forget)
processAsync().catch(console.error);

// Promise.all (parallel)
const [res1, res2, res3] = await Promise.all([
    agent1.process(msg),
    agent2.process(msg),
    agent3.process(msg),
]);

// Promise.race: first to complete
const fastest = await Promise.race([
    agent1.process(msg),
    agent2.process(msg),
]);

// Event emitters for communication
import { EventEmitter } from 'events';
const emitter = new EventEmitter();
emitter.on('message', (msg) => {
    // Process message
});
emitter.emit('message', message);
```

**Changes**:
- `tokio::spawn()` → Just call async function (single-threaded)
- `tokio::join!()` → `Promise.all()`
- `tokio::select!()` → `Promise.race()`
- `mpsc::channel` → `EventEmitter` or callbacks
- Multi-threaded → Single-threaded (event loop)
- Work stealing → Cooperative multitasking
- `Send + Sync` bounds → No thread safety concerns

---

## Patterns

### Sequential

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(agent1),
    Box::new(agent2),
    Box::new(agent3),
]);

let result = sequential.process(msg).await?;
```

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2, agent3],
});

const result = await sequential.process(msg);
```

### Parallel

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(agent_a),
    Box::new(agent_b),
    Box::new(agent_c),
]);

let result = parallel.process(msg).await?;
```

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB, agentC],
});

const result = await parallel.process(msg);
```

### Router

**Rust**:
```rust
use agenkit::patterns::Router;

let router = Router::new(
    |msg: &Message| {
        if msg.content.contains("urgent") {
            "fast"
        } else {
            "thorough"
        }
    },
    vec![
        ("fast", Box::new(sequential)),
        ("thorough", Box::new(parallel)),
    ],
);

let result = router.process(msg).await?;
```

**TypeScript**:
```typescript
import { RouterAgent } from '@agenkit/patterns';

const router = new RouterAgent({
    router: (msg: Message) => {
        if (msg.content.includes('urgent')) {
            return 'fast';
        }
        return 'thorough';
    },
    agents: {
        fast: sequential,
        thorough: parallel,
    },
});

const result = await router.process(msg);
```

**Changes**:
- `Box::new()` → No boxing needed (references are automatic)
- `Vec<(String, Box<dyn Agent>)>` → Object literal `{ [key: string]: Agent }`
- `.await?` → `await` (no `?` operator)

---

## Common Gotchas

### 1. Ownership vs Garbage Collection

**Rust**: Explicit ownership transfer and borrowing
```rust
// Move (ownership transfer)
let msg1 = Message { /* ... */ };
let msg2 = msg1;  // msg1 is now invalid

// Borrow (temporary access)
fn process_msg(msg: &Message) {  // Immutable borrow
    println!("{}", msg.content);
}  // Borrow ends

// Clone when needed
let msg_copy = msg.clone();  // Explicit copy
```

**TypeScript**: References and automatic GC
```typescript
// Assignment creates reference (not copy)
const msg1: Message = { /* ... */ };
const msg2 = msg1;  // Both reference same object

// Mutations affect all references
msg2.content = 'Modified';
console.log(msg1.content);  // 'Modified' (!!)

// Spread operator for shallow copy
const msgCopy = { ...msg };  // New object, same nested references

// Deep clone when needed
const msgDeepCopy = JSON.parse(JSON.stringify(msg));
```

**Migration tip**: Rust's ownership prevents bugs that can happen in TypeScript. Be careful with object mutations.

### 2. Result vs Exceptions

**Rust**: Errors are values, must be handled explicitly
```rust
// Compile error if Result not handled
let result = agent.process(msg).await;  // ❌ Won't compile

// Must handle explicitly
let result = agent.process(msg).await?;  // ✅ Propagate error
let result = agent.process(msg).await.unwrap();  // ✅ Panic on error
match agent.process(msg).await {  // ✅ Handle explicitly
    Ok(r) => r,
    Err(e) => return Err(e),
}
```

**TypeScript**: Errors can be ignored (runtime failure)
```typescript
// Compiles fine, but crashes at runtime if error thrown
const result = await agent.process(msg);  // ⚠️ Uncaught exception risk

// Should use try-catch
try {
    const result = await agent.process(msg);  // ✅ Safe
} catch (error) {
    console.error(error);
}
```

**Migration tip**: TypeScript doesn't force error handling at compile time. Add try-catch blocks where Rust had `?` or `match`.

### 3. Trait vs Interface (Structural vs Nominal)

**Rust**: Explicit trait implementation (nominal typing)
```rust
// Must explicitly implement trait
impl Agent for MyAgent {
    fn name(&self) -> &str { &self.name }
    fn capabilities(&self) -> Vec<String> { vec![] }
    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        // ...
    }
}
```

**TypeScript**: Implicit interface matching (structural typing)
```typescript
// No explicit declaration needed if shape matches
const agent = {
    name: 'my-agent',
    capabilities: ['text'],
    async process(msg: Message): Promise<Message> {
        // ...
    },
};

// Works as Agent without explicit declaration
function useAgent(agent: Agent) {
    // ...
}
useAgent(agent);  // ✅ Works (duck typing)
```

**Migration tip**: TypeScript doesn't require explicit `implements`. Any object matching the interface shape works.

### 4. Zero-Cost Abstractions vs Runtime Overhead

**Rust**: Compile-time optimizations, no runtime cost
```rust
// Generic code monomorphized at compile time
fn process_with<A: Agent>(agent: &A, msg: Message) -> Result<Message, AgentError> {
    agent.process(msg)  // No dynamic dispatch, fully inlined
}

// Zero-cost iterator chains
let results: Vec<_> = messages
    .iter()
    .filter(|m| m.role == Role::User)
    .map(|m| process(m))
    .collect();  // Compiles to tight loop
```

**TypeScript**: JIT optimization, some runtime overhead
```typescript
// Function calls have overhead until JIT warms up
function processWith(agent: Agent, msg: Message): Promise<Message> {
    return agent.process(msg);  // Virtual dispatch, not inlined immediately
}

// Array methods convenient but allocate
const results = messages
    .filter(m => m.role === 'user')
    .map(m => process(m));  // Creates intermediate arrays
```

**Migration tip**: TypeScript is convenient but slower. Optimize hot paths if performance critical.

### 5. Static Lifetimes vs Closure Captures

**Rust**: Lifetime tracking prevents dangling references
```rust
// Compile error: reference doesn't live long enough
fn create_processor() -> impl Fn(Message) -> String {
    let prefix = String::from("Processed: ");
    move |msg| format!("{}{}", prefix, msg.content)  // prefix moved into closure
}
```

**TypeScript**: Closures capture references freely
```typescript
// Works fine, GC keeps prefix alive
function createProcessor(): (msg: Message) => string {
    const prefix = 'Processed: ';
    return (msg) => `${prefix}${msg.content}`;  // Captures prefix
}
```

**Migration tip**: TypeScript closures are easier but can cause memory leaks if not careful with event listeners.

---

## Testing

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent::new("test-agent");
        let msg = Message {
            role: Role::User,
            content: "Test".to_string(),
            ..Default::default()
        };

        let result = agent.process(msg).await.unwrap();

        assert_eq!(result.role, Role::Assistant);
        assert!(result.content.contains("Processed"));
    }

    #[tokio::test]
    async fn test_agent_error() {
        let agent = MyAgent::new("test-agent");
        let invalid_msg = Message {
            role: Role::User,
            content: "".to_string(),
            ..Default::default()
        };

        let result = agent.process(invalid_msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::InvalidMessage(_)));
    }
}
```

### TypeScript
```typescript
import { describe, it, expect } from 'vitest';
import { MyAgent } from './agent';
import { Message } from '@agenkit/core';

describe('MyAgent', () => {
    it('should process message correctly', async () => {
        const agent = new MyAgent('test-agent');
        const msg: Message = {
            role: 'user',
            content: 'Test',
        };

        const result = await agent.process(msg);

        expect(result.role).toBe('assistant');
        expect(result.content).toContain('Processed');
    });

    it('should handle errors', async () => {
        const agent = new MyAgent('test-agent');
        const invalidMsg: Message = {
            role: 'user',
            content: '',
        };

        await expect(agent.process(invalidMsg))
            .rejects
            .toThrow('Invalid message');
    });
});
```

**Changes**:
- `#[tokio::test]` → `it('test name', async () => {})`
- `assert_eq!` → `expect(x).toBe(y)`
- `assert!(condition)` → `expect(condition).toBe(true)`
- `matches!` → `expect().rejects.toThrow()`
- `mod tests` → `describe('suite')`
- `cargo test` → `npm test` or `vitest`

---

## Performance Considerations

| Operation | Rust | TypeScript | Notes |
|-----------|------|------------|-------|
| Agent creation | ~50ns | ~500ns | TypeScript 10x slower |
| Message processing | ~500ns | ~5μs | TypeScript 10x slower |
| Sequential (3 agents) | ~1.5μs | ~15μs | Consistent overhead |
| Parallel (3 agents) | ~500ns | ~5μs | TypeScript single-threaded |
| Memory usage | Low (no GC) | Higher (V8 GC) | TypeScript ~2-3x more RAM |

**When to use TypeScript**:
- Web deployment (browser + Node.js universal code)
- Rapid prototyping (no compilation)
- NPM ecosystem integration (rich library selection)
- Full-stack JavaScript projects (same language everywhere)
- Frontend integration (React, Vue, etc.)

**When to keep Rust**:
- Performance critical applications (10-20x faster)
- Memory-constrained environments (embedded, serverless)
- WASM deployment (browser + native performance)
- Systems programming (low-level control needed)
- Security-critical code (memory safety guarantees)

---

## Migration Checklist

- [ ] Replace `Result<T, E>` returns with `Promise<T>` and exceptions
- [ ] Change trait implementations to interface implementations
- [ ] Remove ownership annotations (`&self`, `&mut`, `'lifetimes`)
- [ ] Convert `match` on Result to `try/catch` blocks
- [ ] Replace `tokio::spawn` with direct async function calls
- [ ] Change `tokio::join!` to `Promise.all()`
- [ ] Convert enum variants to string literals
- [ ] Remove `.clone()` calls (automatic references)
- [ ] Replace `format!` with template literals `` `${}` ``
- [ ] Convert `Vec<T>` to `T[]` or `Array<T>`
- [ ] Replace `HashMap` with object literals `{}`
- [ ] Update tests: `#[tokio::test]` → `it('name', async () => {})`
- [ ] Change assertions: `assert_eq!` → `expect().toBe()`
- [ ] Update imports: `use agenkit` → `import { } from '@agenkit/core'`
- [ ] Remove `Box<dyn Trait>` (dynamic dispatch not needed)
- [ ] Replace `Option<T>` with `T | undefined` or `T | null`

---

## Quick Start

```bash
# Rust project structure
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   └── agent.rs
└── tests/
    └── integration_test.rs

# TypeScript equivalent
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   └── agent.ts
└── tests/
    └── integration.test.ts
```

**Build/Run**:
```bash
# Rust
cargo build --release
./target/release/myagent

# TypeScript
npm run build
node dist/index.js
# or for development
npm run dev
```

**Dependencies**:
```bash
# Rust
cargo add agenkit tokio async-trait

# TypeScript
npm install @agenkit/core
# or
yarn add @agenkit/core
```

---

## Type System Migration

### Rust Types → TypeScript Types

| Rust | TypeScript | Notes |
|------|------------|-------|
| `String` | `string` | Primitive in TS |
| `&str` | `string` | No distinction in TS |
| `Vec<T>` | `T[]` or `Array<T>` | Both syntaxes work |
| `HashMap<K, V>` | `Map<K, V>` or `Record<K, V>` | Object literal often used |
| `Option<T>` | `T \| undefined` or `T \| null` | Nullable types |
| `Result<T, E>` | `Promise<T>` | Errors thrown |
| `Box<T>` | `T` | No boxing needed |
| `Arc<T>` | `T` | No reference counting |
| `&T` | `T` | No borrow syntax |
| `&mut T` | `T` | No mutability distinction |

### Example Conversion

**Rust**:
```rust
struct Config {
    timeout: Option<Duration>,
    retries: u32,
    endpoints: Vec<String>,
    metadata: HashMap<String, String>,
}

impl Config {
    fn new(timeout: Option<Duration>) -> Self {
        Config {
            timeout,
            retries: 3,
            endpoints: vec![],
            metadata: HashMap::new(),
        }
    }
}
```

**TypeScript**:
```typescript
interface Config {
    timeout?: number;  // milliseconds
    retries: number;
    endpoints: string[];
    metadata: Record<string, string>;
}

function createConfig(timeout?: number): Config {
    return {
        timeout,
        retries: 3,
        endpoints: [],
        metadata: {},
    };
}
```

---

## Async Patterns Comparison

### Spawning Tasks

**Rust** (true parallelism):
```rust
// Spawn on thread pool
let handle = tokio::spawn(async move {
    agent.process(msg).await
});

// Wait for result
let result = handle.await.unwrap()?;
```

**TypeScript** (concurrency, not parallelism):
```typescript
// Just call async function (runs on event loop)
const promise = agent.process(msg);

// Wait for result
const result = await promise;
```

### Timeouts

**Rust**:
```rust
use tokio::time::{timeout, Duration};

let result = timeout(
    Duration::from_secs(5),
    agent.process(msg)
).await?;
```

**TypeScript**:
```typescript
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
    return Promise.race([
        promise,
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), ms)
        ),
    ]);
}

const result = await withTimeout(agent.process(msg), 5000);
```

### Cancellation

**Rust** (tokio cancellation):
```rust
let handle = tokio::spawn(async move {
    agent.process(msg).await
});

// Cancel by dropping handle
drop(handle);  // Task cancelled
```

**TypeScript** (AbortController):
```typescript
const controller = new AbortController();

async function processWithCancellation(signal: AbortSignal) {
    if (signal.aborted) throw new Error('Cancelled');

    signal.addEventListener('abort', () => {
        throw new Error('Cancelled');
    });

    return await agent.process(msg);
}

// Cancel
controller.abort();
```

---

## Full Resources

- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms guide
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
