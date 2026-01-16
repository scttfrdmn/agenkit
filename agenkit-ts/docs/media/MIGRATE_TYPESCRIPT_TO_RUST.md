# Quick Reference: TypeScript → Rust Migration

**For**: TypeScript developers migrating Agenkit code to Rust
**Time**: 15 minute read
**Full Details**: See [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) and [Rust Language Profile](LANGUAGE_PROFILE_RUST.md)

---

## Key Differences at a Glance

| Aspect | TypeScript | Rust |
|--------|------------|------|
| **Typing** | Structural, optional | Nominal, required |
| **Errors** | Exceptions (`try/catch`) | `Result<T, E>` + `?` operator |
| **Concurrency** | Promises (single-threaded) | Futures (multi-threaded tokio) |
| **Memory** | GC (V8) | Ownership system (no GC) |
| **Performance** | JIT compiled (~10-20x slower) | Ahead-of-time compiled |
| **Deployment** | Node.js + node_modules | Single binary |
| **Null safety** | `undefined`/`null` | `Option<T>` |

---

## Message Creation

### TypeScript
```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
    role: 'user',
    content: 'Hello!',
    metadata: {
        key: 'value',
        score: 0.95
    },
    timestamp: new Date()
};
```

### Rust
```rust
use agenkit::{Message, Role};
use std::collections::HashMap;
use serde_json::json;

let mut metadata = HashMap::new();
metadata.insert("key".to_string(), json!("value"));
metadata.insert("score".to_string(), json!(0.95));

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata,
    timestamp: Some(Utc::now()),
    ..Default::default()
};
```

**Changes**:
- Import path: `@agenkit/core` → `agenkit`
- Object literal → Struct initialization
- String constants: `'user'` → `Role::User` enum
- Strings: Automatic → Explicit `.to_string()` or `"str".to_owned()`
- Objects: `{}` → `HashMap::new()` + `.insert()`
- Optional: `field?:` → `Option<T>` type
- Default fields: Not needed → `..Default::default()` pattern

---

## Agent Implementation

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
            content: `Processed: ${message.content}`
        };
    }
}
```

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, AgentError, Role};

struct MyAgent {
    config: Config,
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text".to_string(), "analysis".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message {
            role: Role::Assistant,
            content: format!("Processed: {}", message.content),
            ..Default::default()
        })
    }
}
```

**Changes**:
- `class` → `struct` + `impl` block
- `implements Agent` → `impl Agent for MyAgent`
- `constructor` → `impl MyAgent { fn new() }` (by convention)
- Getters: `get name()` → `fn name(&self)` (explicit self reference)
- `async` functions → `#[async_trait]` macro required for traits
- Return type: `Promise<T>` → `Result<T, E>` (errors as values)
- Template strings: `` `text ${var}` `` → `format!("text {}", var)`
- String arrays: `['text']` → `vec!["text".to_string()]`

---

## Error Handling

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

### Rust
```rust
match agent.process(message).await {
    Ok(result) => {
        // Use result
    }
    Err(e) => {
        if let AgentError::ProcessingFailed(name, msg) = e {
            return Err(AgentError::Other(anyhow::anyhow!("process failed: {}", msg)));
        }
        return Err(e);
    }
}

// Or use ? operator for simpler propagation
let result = agent.process(message).await?;
// Use result
```

**Changes**:
- `try/catch` → `match` on `Result` or use `?` operator
- `throw error` → `return Err(error)`
- Error wrapping: `throw new Error(...)` → `Err(AgentError::Other(...))`
- `instanceof` → Pattern matching with `if let` or `matches!`
- No exception unwinding → Explicit error returns up call stack

---

## Concurrency

### TypeScript (Promises + Event Loop)
```typescript
// Launch promise (runs on event loop)
const taskPromise = agent.process(message);

// Create background task
const task = (async () => {
    try {
        const result = await agent.process(message);
        // Use result
    } catch (error) {
        console.error(`Error: ${error}`);
    }
})();

// Wait for multiple (parallel on event loop)
const results = await Promise.all([
    agent1.process(message),
    agent2.process(message),
    agent3.process(message)
]);

// Race: first to complete
const fastest = await Promise.race([
    agent1.process(message),
    agent2.process(message)
]);
```

### Rust (Futures + Tokio Runtime)
```rust
use tokio;

// Launch task on runtime (multi-threaded)
let task = tokio::spawn(async move {
    match agent.process(message).await {
        Ok(result) => {
            // Use result
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }
});

// Wait for multiple (truly parallel)
let (res1, res2, res3) = tokio::join!(
    agent1.process(message.clone()),
    agent2.process(message.clone()),
    agent3.process(message.clone())
);

// Select: first to complete
tokio::select! {
    res = agent1.process(message.clone()) => println!("Agent 1: {:?}", res),
    res = agent2.process(message.clone()) => println!("Agent 2: {:?}", res),
}
```

**Changes**:
- Single-threaded event loop → Multi-threaded work-stealing runtime
- `Promise` → `Future` trait (different semantics)
- `async function()` → `async move { }` block (explicit ownership)
- `Promise.all()` → `tokio::join!()` macro
- `Promise.race()` → `tokio::select!` macro
- `console.log()` → `println!()` / `eprintln!()`
- Automatic cloning → Explicit `.clone()` for shared data
- `await` lazy → `await` requires pinning (tokio handles this)

---

## Patterns

### Sequential

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2, agent3]
});
const result = await sequential.process(message);
```

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(agent1),
    Box::new(agent2),
    Box::new(agent3),
]);
let result = sequential.process(message).await?;
```

### Parallel

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB, agentC]
});
const result = await parallel.process(message);
```

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(agent_a),
    Box::new(agent_b),
    Box::new(agent_c),
]);
let result = parallel.process(message).await?;
```

**Changes**:
- Constructor object: `new Agent({...})` → `Agent::new(...)` (arguments)
- Array: `[item1, item2]` → `vec![item1, item2]` macro
- Dynamic dispatch: Automatic → Explicit `Box<dyn Trait>`
- Error handling: Implicit throw → Explicit `?` operator

---

## Common Gotchas

### 1. Ownership and Borrowing (HUGE Change)

**TypeScript**: Garbage collector manages memory automatically
```typescript
const msg = { role: 'user', content: 'Hello' };
const copy1 = msg;  // Both reference same object
const copy2 = msg;  // All three share the object
copy1.content = 'Modified';  // All see the change
```

**Rust**: Ownership system enforces single owner
```rust
let msg = Message { role: Role::User, content: "Hello".to_string(), ..Default::default() };
let moved = msg;  // msg is now INVALID, moved owns the data
// println!("{}", msg.content);  // COMPILER ERROR: value borrowed after move

// Solutions:
// 1. Clone explicitly
let msg = Message { role: Role::User, content: "Hello".to_string(), ..Default::default() };
let copy = msg.clone();  // Explicit deep copy
println!("{}", msg.content);  // OK, msg still valid

// 2. Borrow (reference)
let msg = Message { role: Role::User, content: "Hello".to_string(), ..Default::default() };
let borrowed = &msg;  // Immutable borrow
println!("{}", msg.content);  // OK, both valid

// 3. Mutable borrow (exclusive)
let mut msg = Message { role: Role::User, content: "Hello".to_string(), ..Default::default() };
let mutable_ref = &mut msg;
mutable_ref.content = "Modified".to_string();
// Can't use msg while mutable_ref exists
```

### 2. Null/Undefined → Option<T>

**TypeScript**: Two null-like values with subtle differences
```typescript
let value: string | undefined = undefined;
let nullable: string | null = null;

if (value !== undefined) {
    console.log(value.length);
}
```

**Rust**: Single `Option<T>` type with pattern matching
```rust
let value: Option<String> = None;

// Pattern matching
match value {
    Some(s) => println!("Length: {}", s.len()),
    None => println!("No value"),
}

// Or use if let
if let Some(s) = value {
    println!("Length: {}", s.len());
}

// Or unwrap_or for defaults
let len = value.unwrap_or_default().len();
```

### 3. String Types (Big Complexity Jump)

**TypeScript**: Single string type
```typescript
const str1 = "Hello";  // string
const str2: string = 'World';  // string
const str3 = `${str1} ${str2}`;  // string (template)
```

**Rust**: Multiple string types with different ownership
```rust
// &str: String slice (borrowed, immutable)
let str1: &str = "Hello";  // String literal (in binary data)

// String: Owned, growable string
let str2: String = "World".to_string();
let str3: String = String::from("World");

// Concatenation (different ownership rules)
let combined = format!("{} {}", str1, str2);  // Borrows both

// When to use which:
// - Function parameters: Use &str (accepts both types)
// - Struct fields: Use String (owned data)
// - Return values: Use String (transfer ownership)
// - Constants: Use &'static str (compile-time known)

fn process(s: &str) {  // Accepts both String and &str
    println!("{}", s);
}

process(str1);  // &str → &str (direct)
process(&str2);  // String → &str (deref coercion)
```

### 4. Async Trait Methods (Requires macro)

**TypeScript**: async works naturally in interfaces
```typescript
interface Agent {
    process(msg: Message): Promise<Message>;
}

class MyAgent implements Agent {
    async process(msg: Message): Promise<Message> {
        // Implementation
    }
}
```

**Rust**: async in traits requires `async_trait` macro
```rust
use async_trait::async_trait;

trait Agent {
    async fn process(&self, msg: Message) -> Result<Message, AgentError>;
    // ERROR: async fn in traits is unstable without macro
}

// Correct approach:
#[async_trait]
trait Agent {
    async fn process(&self, msg: Message) -> Result<Message, AgentError>;
}

struct MyAgent;

#[async_trait]
impl Agent for MyAgent {
    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        // Implementation
    }
}
```

### 5. Error Handling Philosophy

**TypeScript**: Exceptions for control flow
```typescript
async function getUser(id: string): Promise<User> {
    if (!id) {
        throw new Error('Invalid ID');  // Exception
    }
    return await fetchUser(id);
}

// Caller must use try/catch
try {
    const user = await getUser(userId);
} catch (error) {
    // Handle error
}
```

**Rust**: Errors as values (explicit handling)
```rust
async fn get_user(id: &str) -> Result<User, AppError> {
    if id.is_empty() {
        return Err(AppError::InvalidInput("Invalid ID".to_string()));
    }
    fetch_user(id).await
}

// Caller chooses error handling strategy
let user = get_user(user_id).await?;  // Propagate with ?

// Or handle explicitly
match get_user(user_id).await {
    Ok(user) => {
        // Use user
    }
    Err(e) => {
        // Handle error
    }
}

// Or unwrap (panics on error, use only in tests/examples)
let user = get_user(user_id).await.unwrap();
```

---

## Testing

### TypeScript (Jest/Vitest)
```typescript
import { describe, it, expect } from 'vitest';
import { MyAgent } from './agent';
import { Message } from '@agenkit/core';

describe('MyAgent', () => {
    it('should process message correctly', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: 'Test'
        };

        const result = await agent.process(msg);

        expect(result.role).toBe('assistant');
        expect(result.content).toContain('Processed');
    });

    it('should handle errors', async () => {
        const agent = new MyAgent();
        const invalidMsg: Message = {
            role: 'user',
            content: ''  // Invalid
        };

        await expect(agent.process(invalidMsg))
            .rejects
            .toThrow('Empty content');
    });
});
```

### Rust (Cargo Test)
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent::new();
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
        let agent = MyAgent::new();
        let invalid_msg = Message {
            role: Role::User,
            content: "".to_string(),  // Invalid
            ..Default::default()
        };

        let result = agent.process(invalid_msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::InvalidMessage(_)));
    }
}
```

**Changes**:
- `describe/it` → `#[cfg(test)] mod tests` + `#[tokio::test]`
- `expect(x).toBe(y)` → `assert_eq!(x, y)`
- `expect(x).toContain(y)` → `assert!(x.contains(y))`
- `await expect(...).rejects.toThrow()` → `assert!(result.is_err())`
- Test framework: Jest/Vitest → Built-in `cargo test`
- Async tests: Automatic → Requires `#[tokio::test]` attribute

---

## Performance Considerations

| Operation | TypeScript | Rust | Speedup |
|-----------|------------|------|---------|
| Agent creation | ~1μs | ~50ns | 20x faster |
| Message processing | ~10μs | ~500ns | 20x faster |
| Sequential (3 agents) | ~30μs | ~1.5μs | 20x faster |
| Parallel (3 agents) | ~20μs | ~500ns | 40x faster |
| Memory usage | 50-100MB baseline | 1-5MB baseline | 10-50x less |
| Startup time | ~100ms (Node.js) | ~1ms (native) | 100x faster |

**When to use Rust**:
- Performance-critical applications (low latency, high throughput)
- Memory-constrained environments (embedded, edge)
- WASM for browser (near-native performance)
- Systems programming (OS integration, drivers)
- Safety-critical applications (medical, aerospace)
- Long-running services (no GC pauses)

**When to keep TypeScript**:
- Rapid prototyping (faster development)
- Web development (natural fit with browsers)
- Full-stack JavaScript (shared code between frontend/backend)
- Rich ecosystem (npm has 2M+ packages)
- Team expertise (TypeScript is more common)
- Integration with existing JS/TS codebase

---

## Type System Migration

### Structural → Nominal Typing

**TypeScript**: Types match by shape
```typescript
interface Message {
    role: string;
    content: string;
}

interface Task {
    role: string;
    content: string;
}

// Compatible: same structure
const msg: Message = { role: 'user', content: 'Hi' };
const task: Task = msg;  // OK in TypeScript
```

**Rust**: Types match by name and explicit implementation
```rust
struct Message {
    role: String,
    content: String,
}

struct Task {
    role: String,
    content: String,
}

// NOT compatible: different types
let msg = Message {
    role: "user".to_string(),
    content: "Hi".to_string(),
};
// let task: Task = msg;  // COMPILER ERROR: mismatched types

// Must explicitly convert
let task = Task {
    role: msg.role.clone(),
    content: msg.content.clone(),
};

// Or implement From/Into traits
impl From<Message> for Task {
    fn from(msg: Message) -> Self {
        Task {
            role: msg.role,
            content: msg.content,
        }
    }
}

let task: Task = msg.into();  // Now works
```

### Generic Constraints

**TypeScript**: Structural constraints
```typescript
function process<T extends { content: string }>(item: T): T {
    console.log(item.content);
    return item;
}

// Any object with content field works
process({ content: 'Hello', other: 42 });
```

**Rust**: Trait bounds
```rust
trait HasContent {
    fn content(&self) -> &str;
}

fn process<T: HasContent>(item: T) -> T {
    println!("{}", item.content());
    item
}

// Must explicitly implement HasContent trait
impl HasContent for Message {
    fn content(&self) -> &str {
        &self.content
    }
}

process(msg);
```

---

## Package Management

### TypeScript (npm/yarn/pnpm)
```bash
# Install dependencies
npm install @agenkit/core

# Run script
npm run build
npm test

# Project structure
package.json      # Dependencies
tsconfig.json     # TypeScript config
node_modules/     # Dependencies (can be huge)
src/
dist/
```

### Rust (Cargo)
```bash
# Add dependency
cargo add agenkit

# Build
cargo build --release

# Test
cargo test

# Project structure
Cargo.toml        # Dependencies
Cargo.lock        # Locked versions
src/
target/           # Build artifacts (debug + release)
```

**Changes**:
- `package.json` → `Cargo.toml`
- `npm install` → `cargo add` or edit `Cargo.toml`
- `npm test` → `cargo test`
- `npm run build` → `cargo build --release`
- Semantic versioning: Same in both
- Lock files: `package-lock.json` → `Cargo.lock`

---

## Migration Checklist

- [ ] Install Rust toolchain (`rustup`)
- [ ] Replace `class` with `struct` + `impl` blocks
- [ ] Convert exceptions to `Result<T, E>` returns
- [ ] Add `#[async_trait]` to async trait methods
- [ ] Replace `Promise` with tokio `Future` patterns
- [ ] Change `Promise.all` → `tokio::join!`
- [ ] Update imports: `@agenkit/core` → `use agenkit`
- [ ] Convert string types: `string` → `String` or `&str`
- [ ] Handle ownership: Add `.clone()` where needed
- [ ] Replace `undefined`/`null` with `Option<T>`
- [ ] Update error handling: `try/catch` → `match` or `?`
- [ ] Convert template strings to `format!()` macro
- [ ] Update tests: Jest/Vitest → `cargo test`
- [ ] Replace `console.log` with `println!`/`eprintln!`
- [ ] Update dependencies: `package.json` → `Cargo.toml`
- [ ] Handle Send/Sync bounds for multi-threaded async
- [ ] Replace dynamic typing (`any`) with proper types
- [ ] Convert JSON objects to `HashMap` or structs
- [ ] Update array operations: `[].map()` → `iter().map()`
- [ ] Handle lifetime annotations where needed

---

## Quick Start

### TypeScript Project
```
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   └── agent.ts
└── tests/
    └── agent.test.ts
```

### Rust Equivalent
```
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── lib.rs or main.rs
│   └── agent.rs
└── tests/
    └── agent_test.rs
```

**Build/Run**:
```bash
# TypeScript
npm install
npm run build
npm test
node dist/index.js

# Rust
cargo build --release
cargo test
./target/release/myagent
```

**Deployment**:
```bash
# TypeScript: Ship Node.js + code + node_modules
tar -czf app.tar.gz dist/ node_modules/ package.json
# 50-200MB typical

# Rust: Ship single binary
cargo build --release
# 5-20MB typical (includes all dependencies)
strip target/release/myagent  # Further reduce size
# 2-10MB after strip
```

---

## Common Patterns Translation

### Retry with Exponential Backoff

**TypeScript**:
```typescript
async function withRetry<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3
): Promise<T> {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve =>
                setTimeout(resolve, Math.pow(2, i) * 1000)
            );
        }
    }
    throw new Error('Max retries exceeded');
}

const result = await withRetry(() => agent.process(msg));
```

**Rust**:
```rust
use tokio::time::{sleep, Duration};

async fn with_retry<F, T, E>(
    mut fn_: F,
    max_retries: usize,
) -> Result<T, E>
where
    F: FnMut() -> Pin<Box<dyn Future<Output = Result<T, E>> + Send>>,
{
    let mut last_error = None;

    for attempt in 0..max_retries {
        match fn_().await {
            Ok(result) => return Ok(result),
            Err(e) => {
                last_error = Some(e);
                if attempt < max_retries - 1 {
                    let delay = Duration::from_secs(2u64.pow(attempt as u32));
                    sleep(delay).await;
                }
            }
        }
    }

    Err(last_error.unwrap())
}

let result = with_retry(
    || Box::pin(agent.process(msg.clone())),
    3
).await?;
```

### Timeout

**TypeScript**:
```typescript
function withTimeout<T>(
    promise: Promise<T>,
    ms: number
): Promise<T> {
    return Promise.race([
        promise,
        new Promise<T>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), ms)
        )
    ]);
}

const result = await withTimeout(agent.process(msg), 5000);
```

**Rust**:
```rust
use tokio::time::{timeout, Duration};

let result = timeout(
    Duration::from_secs(5),
    agent.process(msg)
).await
.map_err(|_| AgentError::Timeout(5))?;
```

---

## Full Resources

- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms
- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms
- [The Rust Book](https://doc.rust-lang.org/book/) - Official Rust learning resource
- [Async Book](https://rust-lang.github.io/async-book/) - Async Rust deep dive
- [Agenkit Rust Examples](../agenkit-rust/examples/) - Side-by-side code samples
- [Main Migration Guide](MIGRATION.md) - Python → All languages

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
