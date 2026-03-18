# Building Production AI Agents in Rust

A practical guide to building safe, high-performance AI agents with agenkit-rust. Each
tutorial is self-contained and runnable with `cargo run`.

---

## Introduction: Rust's Ownership Model and AI Agents

Rust's ownership system makes AI agents safer by construction:

- **No data races** — the compiler enforces that shared state is protected by `Mutex` or
  `RwLock` at compile time, not runtime.
- **No null pointer dereferences** — `Option<T>` forces you to handle the "no value" case
  explicitly.
- **Predictable performance** — no garbage collector means no GC pauses during LLM calls.
- **Zero-cost async** — `tokio` futures compile to state machines; you pay only for what
  you use.
- **Smallest binaries** among agenkit implementations — important for edge and WASM targets.

The trade-offs:
- Ownership and lifetimes require an investment of about 2-4 weeks to feel natural.
- Async Rust requires explicit runtime (`#[tokio::main]`) and careful `Send + Sync` bounds.
- Compilation is slower than Go or TypeScript.

For safety-critical applications, edge deployments, and WASM targets, Rust is the right
language.

### Prerequisites

```toml
# Cargo.toml
[dependencies]
agenkit = "0.76"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
thiserror = "1"
anyhow = "1"
proptest = "1"
```

Rust 1.75+ is required. All examples compile and run with `cargo run`.

---

## Tutorial 1: Ownership in Agent State

### Goal

Understand when to use `Arc<Mutex<T>>` vs `Rc<RefCell<T>>` for shared agent state, and
how to avoid common ownership pitfalls.

### The Problem: Sharing State Between Agents

```rust
use agenkit::{Agent, Message};
use std::sync::{Arc, Mutex};

// Shared conversation history accessed by multiple agents.
#[derive(Default)]
struct SharedHistory {
    messages: Vec<Message>,
}

// WRONG: Cannot share `Rc<RefCell<T>>` across threads.
// Rc is single-threaded only.
use std::rc::Rc;
use std::cell::RefCell;

// This will NOT compile if passed to tokio::spawn:
// let history = Rc::new(RefCell::new(SharedHistory::default()));
// tokio::spawn(async move { history.borrow_mut().messages.push(msg); });
// ERROR: `Rc<RefCell<SharedHistory>>` cannot be sent between threads safely

// CORRECT: Use Arc<Mutex<T>> for multi-threaded sharing.
let history: Arc<Mutex<SharedHistory>> = Arc::new(Mutex::new(SharedHistory::default()));
```

### When to Use Each

| Type | Use When |
|------|----------|
| `T` | Single owner, no sharing needed |
| `&T` / `&mut T` | Temporary borrow within a function |
| `Arc<T>` | Read-only shared ownership across threads |
| `Arc<Mutex<T>>` | Mutable shared state across threads |
| `Arc<RwLock<T>>` | Many readers, infrequent writes |
| `Rc<RefCell<T>>` | Shared state within a single thread (e.g. WASM) |

### Agent with Shared Memory

```rust
use agenkit::{Agent, Message, AgentError};
use async_trait::async_trait;
use std::sync::{Arc, Mutex};

#[derive(Default)]
struct Memory {
    facts: Vec<String>,
}

struct MemoryAgent {
    name: String,
    memory: Arc<Mutex<Memory>>,
}

impl MemoryAgent {
    fn new(name: impl Into<String>, memory: Arc<Mutex<Memory>>) -> Self {
        Self { name: name.into(), memory }
    }
}

#[async_trait]
impl Agent for MemoryAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text".to_string(), "memory".to_string()]
    }

    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        // Lock is held only long enough to read/write — never across .await.
        let fact_count = {
            let mem = self.memory.lock().map_err(|_| AgentError::internal("lock poisoned"))?;
            mem.facts.len()
        }; // Lock released here.

        // Do async work WITHOUT holding the lock.
        let response = format!("I know {} facts. Processing: {}", fact_count, msg.content);

        // Lock again to write.
        {
            let mut mem = self.memory.lock().map_err(|_| AgentError::internal("lock poisoned"))?;
            mem.facts.push(msg.content.clone());
        } // Lock released here.

        Ok(Message {
            role: agenkit::Role::Assistant,
            content: response,
            ..Default::default()
        })
    }
}
```

### The Critical Rule: Never Hold a Mutex Across `.await`

```rust
// DEADLOCK RISK: holding lock across .await
async fn bad_example(memory: Arc<Mutex<Memory>>) {
    let _guard = memory.lock().unwrap();
    // If this .await suspends the task, another task trying to lock
    // memory will deadlock — tokio may not run on another thread.
    some_async_operation().await;
    // _guard dropped here — but task may have switched threads!
}

// CORRECT: release lock before .await
async fn good_example(memory: Arc<Mutex<Memory>>) -> String {
    let value = {
        let guard = memory.lock().unwrap();
        guard.facts.len().to_string()
    }; // Lock released before .await
    some_async_operation().await;
    value
}
```

### `RwLock` for Read-Heavy State

```rust
use std::sync::RwLock;

struct CachingAgent {
    cache: Arc<RwLock<HashMap<String, Message>>>,
    inner: Box<dyn Agent + Send + Sync>,
}

#[async_trait]
impl Agent for CachingAgent {
    fn name(&self) -> &str { "caching" }
    fn capabilities(&self) -> Vec<String> { self.inner.capabilities() }

    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        // Multiple readers can hold this simultaneously.
        if let Some(cached) = self.cache.read().unwrap().get(&msg.content) {
            return Ok(cached.clone());
        }

        // Only one writer at a time.
        let result = self.inner.process(msg.clone()).await?;

        self.cache
            .write()
            .unwrap()
            .insert(msg.content.clone(), result.clone());

        Ok(result)
    }
}
```

### Key Takeaways

- Use `Arc<Mutex<T>>` for shared mutable state across async tasks; `Rc<RefCell<T>>` is
  single-thread only.
- Never hold a `Mutex` guard across an `.await` point — prefer `RwLock` for read-heavy state.
- Keep critical sections short: lock, read/write, unlock, then do async work.

---

## Tutorial 2: Async Agent Patterns

### Goal

Use `tokio::spawn`, `tokio::join!`, and `tokio::select!` to run agents concurrently and
handle cancellation correctly.

### tokio::spawn for Fire-and-Forget

```rust
use tokio;

async fn spawn_example(agent: Arc<dyn Agent + Send + Sync>) {
    let msg = Message {
        role: agenkit::Role::User,
        content: "Hello".to_string(),
        ..Default::default()
    };

    // tokio::spawn requires the future to be 'static + Send.
    let agent_clone = Arc::clone(&agent);
    let handle = tokio::spawn(async move {
        match agent_clone.process(msg).await {
            Ok(resp) => println!("Got: {}", resp.content),
            Err(e) => eprintln!("Error: {}", e),
        }
    });

    // Optionally await the handle to get its result.
    if let Err(e) = handle.await {
        eprintln!("task panicked: {}", e);
    }
}
```

### tokio::join! for Concurrent Agents

```rust
use tokio;

async fn run_agents_concurrently(
    fact_checker: &impl Agent,
    summariser: &impl Agent,
    critic: &impl Agent,
    msg: Message,
) -> Result<(Message, Message, Message), AgentError> {
    // All three run concurrently on the tokio runtime.
    let (r1, r2, r3) = tokio::join!(
        fact_checker.process(msg.clone()),
        summariser.process(msg.clone()),
        critic.process(msg.clone()),
    );

    // All three must succeed — if one fails, we propagate that error.
    Ok((r1?, r2?, r3?))
}
```

### tokio::select! for Racing and Cancellation

```rust
use tokio::time::{timeout, Duration};

async fn first_to_respond(
    agent_a: Arc<dyn Agent + Send + Sync>,
    agent_b: Arc<dyn Agent + Send + Sync>,
    msg: Message,
) -> Result<Message, AgentError> {
    let a = Arc::clone(&agent_a);
    let b = Arc::clone(&agent_b);
    let msg_a = msg.clone();
    let msg_b = msg.clone();

    // Race: whichever completes first wins; the other is dropped (cancelled).
    tokio::select! {
        result = a.process(msg_a) => result,
        result = b.process(msg_b) => result,
    }
}

// With timeout:
async fn with_deadline(agent: &impl Agent, msg: Message, ms: u64) -> Result<Message, AgentError> {
    timeout(Duration::from_millis(ms), agent.process(msg))
        .await
        .map_err(|_| AgentError::timeout(ms))?
}
```

### Collecting Results with JoinSet

```rust
use tokio::task::JoinSet;

async fn fan_out(
    agents: Vec<Arc<dyn Agent + Send + Sync>>,
    msg: Message,
) -> Vec<Result<Message, AgentError>> {
    let mut set = JoinSet::new();

    for agent in agents {
        let msg = msg.clone();
        set.spawn(async move { agent.process(msg).await });
    }

    let mut results = Vec::new();
    while let Some(result) = set.join_next().await {
        match result {
            Ok(agent_result) => results.push(agent_result),
            Err(join_err) => results.push(Err(AgentError::internal(join_err.to_string()))),
        }
    }
    results
}
```

### Key Takeaways

- `tokio::join!` runs futures concurrently but waits for ALL; `tokio::select!` takes the FIRST.
- Futures passed to `tokio::spawn` must be `'static + Send` — use `Arc` to share ownership.
- Dropping a `JoinSet` cancels all its tasks — a safe way to limit concurrent work.
- `tokio::time::timeout` wraps any future with a deadline without modifying the future itself.

---

## Tutorial 3: Zero-Copy Message Processing

### Goal

Process agent messages with minimal heap allocations using `Cow<str>` and avoiding
unnecessary `.clone()` calls.

### The Cost of Cloning

```rust
// SLOW: clones the entire content string on every agent hop.
fn pipeline_slow(msg: Message, agents: &[&dyn Agent]) {
    let mut current = msg;
    for agent in agents {
        // .clone() allocates a new String on the heap.
        current = agent.process(current.clone()).await.unwrap();
    }
}
```

### Cow<str> for Borrowed-or-Owned Content

```rust
use std::borrow::Cow;

// MessageView holds a reference when possible, owned data when necessary.
struct MessageView<'a> {
    role: agenkit::Role,
    content: Cow<'a, str>,
}

impl<'a> MessageView<'a> {
    /// Borrow from an existing Message — zero allocation.
    fn borrow(msg: &'a Message) -> Self {
        Self {
            role: msg.role,
            content: Cow::Borrowed(&msg.content),
        }
    }

    /// Truncate content to `max_len` chars, allocating only if needed.
    fn truncate(msg: &'a Message, max_len: usize) -> Self {
        let content: Cow<'a, str> = if msg.content.len() <= max_len {
            Cow::Borrowed(&msg.content) // no allocation
        } else {
            Cow::Owned(msg.content[..max_len].to_string()) // allocates only when truncating
        };
        Self { role: msg.role, content }
    }

    /// Get content without allocating if it is already ASCII-uppercase.
    fn to_uppercase(&self) -> Cow<str> {
        if self.content.chars().all(|c| c.is_uppercase() || !c.is_alphabetic()) {
            Cow::Borrowed(self.content.as_ref()) // already uppercase — no allocation
        } else {
            Cow::Owned(self.content.to_uppercase()) // allocates new String
        }
    }
}
```

### Avoiding Clones in Hot Paths

```rust
// Instead of cloning Messages for each agent, pass references.
trait AgentRef {
    fn name(&self) -> &str;
    // Process takes a reference — no clone needed.
    async fn process_ref(&self, msg: &Message) -> Result<Message, AgentError>;
}

// Use Arc<Message> when you need shared ownership.
use std::sync::Arc as StdArc;

async fn shared_message_pipeline(
    msg: StdArc<Message>,
    agents: &[Box<dyn AgentRef + Send + Sync>],
) -> Vec<Message> {
    let mut results = Vec::with_capacity(agents.len());
    for agent in agents {
        // Arc::clone increments a reference counter — not a content clone.
        match agent.process_ref(&msg).await {
            Ok(resp) => results.push(resp),
            Err(e) => eprintln!("agent error: {}", e),
        }
    }
    results
}
```

### String Building with `write!` Instead of `format!`

```rust
use std::fmt::Write;

fn build_prompt(system: &str, history: &[Message], user_input: &str) -> String {
    // Pre-allocate approximately the right size.
    let estimated_size = system.len() + history.iter().map(|m| m.content.len()).sum::<usize>() + user_input.len() + 128;
    let mut buf = String::with_capacity(estimated_size);

    // write! into the buffer — no intermediate allocations.
    let _ = writeln!(buf, "System: {}", system);
    for msg in history {
        let _ = writeln!(buf, "{:?}: {}", msg.role, msg.content);
    }
    let _ = write!(buf, "User: {}", user_input);

    buf
}
```

### Key Takeaways

- `Cow<'a, str>` avoids allocation when the original string suffices; allocates only on
  modification — ideal for content filtering and truncation.
- `Arc::clone` is O(1) (atomic counter increment) vs `String::clone` which is O(n).
- `String::with_capacity` avoids repeated reallocations when building prompts.
- Use `write!(buf, ...)` instead of repeated `+` or `format!()` for multi-part strings.

---

## Tutorial 4: Error Propagation

### Goal

Design a clean error hierarchy using `thiserror` for library errors and `anyhow` for
application-level context.

### Defining a Library Error Enum with thiserror

```rust
use thiserror::Error;
use std::time::Duration;

#[derive(Debug, Error)]
pub enum AgentError {
    #[error("invalid message: {0}")]
    InvalidMessage(String),

    #[error("LLM request failed: {0}")]
    LlmError(#[from] reqwest::Error),

    #[error("rate limited, retry after {retry_after:?}")]
    RateLimit { retry_after: Duration },

    #[error("timed out after {timeout:?}")]
    Timeout { timeout: Duration },

    #[error("tool {name:?} failed: {source}")]
    ToolError {
        name: String,
        #[source]
        source: Box<dyn std::error::Error + Send + Sync>,
    },

    #[error("internal error: {0}")]
    Internal(String),
}

impl AgentError {
    pub fn is_transient(&self) -> bool {
        matches!(self, AgentError::RateLimit { .. } | AgentError::Timeout { .. })
    }

    pub fn tool(name: impl Into<String>, source: impl std::error::Error + Send + Sync + 'static) -> Self {
        AgentError::ToolError {
            name: name.into(),
            source: Box::new(source),
        }
    }
}
```

### The ? Operator and Error Conversion

```rust
// #[from] in the enum makes this automatic:
impl From<reqwest::Error> for AgentError {
    fn from(e: reqwest::Error) -> Self {
        AgentError::LlmError(e)
    }
}

async fn call_llm(prompt: &str) -> Result<String, AgentError> {
    let resp = reqwest::get("https://api.example.com/complete")
        .await?; // reqwest::Error → AgentError::LlmError via From impl
    let text = resp.text().await?; // same
    Ok(text)
}
```

### anyhow for Application Code

In application binaries (not libraries), use `anyhow` to add context without defining
new error types:

```rust
use anyhow::{Context, Result};

async fn run_pipeline(input: &str) -> Result<String> {
    let agent = build_agent()
        .context("failed to build agent")?;

    let msg = Message {
        role: agenkit::Role::User,
        content: input.to_string(),
        ..Default::default()
    };

    let result = agent
        .process(msg)
        .await
        .context("agent failed to process message")?;

    Ok(result.content)
}
```

### Retry Logic with Error Inspection

```rust
use std::time::Duration;
use tokio::time::sleep;

async fn with_retry<F, Fut>(
    mut f: F,
    max_retries: u32,
    base_delay: Duration,
) -> Result<Message, AgentError>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<Message, AgentError>>,
{
    let mut last_err = None;

    for attempt in 0..=max_retries {
        match f().await {
            Ok(msg) => return Ok(msg),
            Err(e) if e.is_transient() && attempt < max_retries => {
                let delay = if let AgentError::RateLimit { retry_after } = &e {
                    *retry_after
                } else {
                    base_delay * 2u32.pow(attempt)
                };
                eprintln!("attempt {} failed (transient), retrying after {:?}", attempt + 1, delay);
                sleep(delay).await;
                last_err = Some(e);
            }
            Err(e) => return Err(e), // non-transient or final attempt
        }
    }

    Err(last_err.unwrap_or(AgentError::Internal("retry loop exited unexpectedly".into())))
}

// Usage:
let result = with_retry(
    || agent.process(msg.clone()),
    3,
    Duration::from_millis(500),
).await?;
```

### Converting Between Error Representations

```rust
// From library AgentError to HTTP status codes.
impl From<&AgentError> for u16 {
    fn from(e: &AgentError) -> Self {
        match e {
            AgentError::InvalidMessage(_) => 400,
            AgentError::RateLimit { .. } => 429,
            AgentError::Timeout { .. } => 504,
            AgentError::LlmError(_) => 502,
            AgentError::ToolError { .. } => 500,
            AgentError::Internal(_) => 500,
        }
    }
}
```

### Key Takeaways

- `thiserror` is for library crates: generates `Display` + `Error` impls from enum variants.
- `anyhow` is for application code: adds `context()` without defining error types.
- `#[from]` in `thiserror` generates `From` impls so `?` works across error types.
- Always implement `is_transient()` so retry logic can inspect errors without matching.

---

## Tutorial 5: Property Testing with proptest

### Goal

Define strategies for random agent inputs and verify correctness invariants hold across
thousands of generated cases.

### Setup

```toml
[dev-dependencies]
proptest = "1"
```

### Defining Strategies

```rust
use proptest::prelude::*;
use agenkit::{Message, Role};

// Strategy for generating random valid Messages.
prop_compose! {
    fn arb_role()(r in 0usize..3) -> Role {
        match r {
            0 => Role::User,
            1 => Role::Assistant,
            _ => Role::System,
        }
    }
}

prop_compose! {
    fn arb_message()(
        role in arb_role(),
        content in "[a-zA-Z0-9 ]{1,500}",
    ) -> Message {
        Message {
            role,
            content,
            ..Default::default()
        }
    }
}

prop_compose! {
    fn arb_user_message()(
        content in "[a-zA-Z0-9 ]{1,500}",
    ) -> Message {
        Message {
            role: Role::User,
            content,
            ..Default::default()
        }
    }
}
```

### Writing Property Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;
    use tokio::runtime::Runtime;

    // Helper: run an async property test synchronously.
    fn run_async<F: std::future::Future>(f: F) -> F::Output {
        Runtime::new().unwrap().block_on(f)
    }

    proptest! {
        // Property 1: EchoAgent always returns role=assistant.
        #[test]
        fn echo_always_assistant(msg in arb_user_message()) {
            run_async(async move {
                let agent = EchoAgent::new();
                let result = agent.process(msg).await.unwrap();
                prop_assert_eq!(result.role, Role::Assistant);
                Ok(())
            })?;
        }

        // Property 2: EchoAgent never returns empty content.
        #[test]
        fn echo_non_empty_output(msg in arb_user_message()) {
            run_async(async move {
                let agent = EchoAgent::new();
                let result = agent.process(msg).await.unwrap();
                prop_assert!(!result.content.is_empty());
                Ok(())
            })?;
        }

        // Property 3: Sequential(a, b) is deterministic.
        #[test]
        fn sequential_deterministic(msg in arb_user_message()) {
            run_async(async move {
                use agenkit::patterns::Sequential;
                let seq = Sequential::new(vec![
                    Box::new(EchoAgent::new()),
                    Box::new(UpperAgent::new()),
                ]);

                let r1 = seq.process(msg.clone()).await.unwrap();
                let r2 = seq.process(msg).await.unwrap();

                prop_assert_eq!(r1.content, r2.content);
                prop_assert_eq!(r1.role, r2.role);
                Ok(())
            })?;
        }

        // Property 4: UpperAgent output is always uppercase.
        #[test]
        fn upper_agent_uppercase(msg in arb_user_message()) {
            run_async(async move {
                let agent = UpperAgent::new();
                let result = agent.process(msg).await.unwrap();
                prop_assert_eq!(result.content, result.content.to_uppercase());
                Ok(())
            })?;
        }

        // Property 5: Retry middleware passes through successful response unchanged.
        #[test]
        fn retry_passthrough_on_success(msg in arb_user_message()) {
            run_async(async move {
                let inner = EchoAgent::new();
                let with_retry = RetryAgent::new(inner.clone(), 3, Duration::from_millis(0));

                let direct = inner.process(msg.clone()).await.unwrap();
                let retried = with_retry.process(msg).await.unwrap();

                prop_assert_eq!(direct.content, retried.content);
                Ok(())
            })?;
        }
    }

    // Standard unit tests for known edge cases.
    #[tokio::test]
    async fn echo_handles_unicode() {
        let agent = EchoAgent::new();
        let msg = Message {
            role: Role::User,
            content: "héllo wörld 🌍".to_string(),
            ..Default::default()
        };
        let result = agent.process(msg).await.unwrap();
        assert!(!result.content.is_empty());
    }
}
```

### Configuring proptest

```rust
// Increase the number of test cases.
proptest! {
    #![proptest_config(ProptestConfig {
        cases: 1000,
        ..Default::default()
    })]

    #[test]
    fn thorough_property(msg in arb_message()) {
        // ...
    }
}
```

### Key Takeaways

- `prop_compose!` is the idiomatic way to build complex strategies from simpler ones.
- Use `block_on` from a fresh `Runtime` to run async code inside proptest closures.
- `prop_assert!` / `prop_assert_eq!` integrate with proptest's shrinking — use them
  instead of `assert!` in property tests.
- Proptest automatically saves failing seeds in `.proptest-regressions/` for reproducible CI.

---

## Next Steps

- **Reference**: `agenkit-rust/docs/API.md` — complete crate documentation
- **Examples**: `examples/rust/` — 15+ runnable examples
- **Patterns**: `docs/PATTERNS.md` — canonical pattern catalogue (all languages)
- **Cargo docs**: `cargo doc --open` inside `agenkit-rust/`

```bash
# Run all Rust tests
cd agenkit-rust && cargo test

# Run property tests with more cases
PROPTEST_CASES=1000 cargo test

# Check memory safety with address sanitizer
RUSTFLAGS="-Z sanitizer=address" cargo +nightly test

# Benchmark
cargo bench
```
