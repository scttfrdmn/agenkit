# Quick Reference: C++ → Rust Migration

**For**: C++ developers migrating Agenkit code to Rust
**Time**: 15 minute read
**Full Details**: See [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) and [Rust Language Profile](LANGUAGE_PROFILE_RUST.md)

---

## Key Differences at a Glance

| Aspect | C++ | Rust |
|--------|-----|------|
| **Memory Safety** | Manual + RAII (runtime) | Ownership (compile-time) |
| **Errors** | Exceptions or codes | `Result<T, E>` (explicit) |
| **Concurrency** | `std::thread` (OS threads) | `async/await` (tokio, green threads) |
| **Memory** | Manual + smart pointers | Ownership + borrowing |
| **Performance** | Zero-cost (optimized) | Zero-cost (optimized) |
| **Safety** | Undefined behavior possible | Memory safe by default |

---

## Message Creation

### C++
```cpp
#include <agenkit/message.hpp>

Message msg{
    .role = "user",
    .content = "Hello!",
    .metadata = {
        {"key", "value"},
    },
};
```

### Rust
```rust
use agenkit::{Message, Role};

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata: {
        let mut m = HashMap::new();
        m.insert("key".to_string(), json!("value"));
        m
    },
    ..Default::default()
};
```

**Changes**:
- Designated initializers → Struct literals with `..Default::default()`
- String literals → `.to_string()` (ownership)
- `std::map` → `HashMap`
- Implicit conversions → Explicit type conversions
- `std::any` → `serde_json::Value`

---

## Agent Implementation

### C++
```cpp
class MyAgent : public Agent {
    std::string name_;
    Config config_;

public:
    explicit MyAgent(Config config)
        : config_(std::move(config)) {}

    std::string name() const override {
        return "my-agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"text", "analysis"};
    }

    std::future<Message> process(const Message& msg) override {
        return std::async(std::launch::async, [this, msg]() {
            return Message{
                .role = "assistant",
                .content = "Processed: " + msg.content,
            };
        });
    }
};
```

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
        "my-agent"
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

**Changes**:
- Abstract base class → Trait (`Agent`)
- Constructor → Associated function (`new()`)
- `override` keyword → Trait implementation
- `std::future` → `async fn` returns `impl Future`
- Lambda capture `[this, msg]` → Borrows via `&self`
- Return type → `Result<T, E>` (explicit error handling)
- `#[async_trait]` macro for async trait methods

---

## Error Handling

### C++
```cpp
// Exception-based
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const std::runtime_error& e) {
    std::cerr << "Error: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Unknown error: " << e.what() << '\n';
}

// Or std::expected (C++23)
auto result = process_message(agent, msg);
if (result) {
    Message response = result.value();
} else {
    AgentError error = result.error();
}
```

### Rust
```rust
// Result type (standard)
match agent.process(msg).await {
    Ok(result) => {
        // Use result
        println!("Success: {}", result.content);
    }
    Err(e) => {
        eprintln!("Error: {}", e);
    }
}

// Or with ? operator (propagate)
async fn handle_message(agent: &impl Agent, msg: Message) -> Result<Message, AgentError> {
    let result = agent.process(msg).await?;  // Returns early if Err
    Ok(result)
}
```

**Changes**:
- `try/catch` → `match` or `?` operator
- Exception unwinding → Explicit error returns
- `throw` → `return Err(...)`
- `std::expected<T, E>` → `Result<T, E>` (built-in)
- Implicit error propagation → Explicit with `?`
- Runtime overhead → Zero-cost (compile-time)

---

## Concurrency

### C++ (std::thread)
```cpp
#include <thread>
#include <future>

// Spawn thread
std::thread t([&agent, msg]() {
    try {
        Message result = agent.process(msg).get();
        // Use result
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << '\n';
    }
});
t.join();

// Async with futures
std::vector<std::future<Message>> futures;
for (const auto& agent : agents) {
    futures.push_back(std::async(std::launch::async, [&agent, msg]() {
        return agent.process(msg).get();
    }));
}

// Wait for all
for (auto& future : futures) {
    Message result = future.get();
}
```

### Rust (tokio)
```rust
use tokio;

// Spawn task (green thread)
tokio::spawn(async move {
    match agent.process(msg).await {
        Ok(result) => {
            // Use result
            println!("Success: {}", result.content);
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }
});

// Join multiple tasks
let results: Vec<Result<Message, AgentError>> = futures::future::join_all(
    agents.iter().map(|agent| agent.process(msg.clone()))
).await;

// Or with tokio::join! macro
let (res1, res2, res3) = tokio::join!(
    agent1.process(msg.clone()),
    agent2.process(msg.clone()),
    agent3.process(msg.clone())
);
```

**Changes**:
- `std::thread` → `tokio::spawn()` (green threads)
- `std::future` → `async fn` returns Future
- `.get()` (blocks) → `.await` (cooperative)
- OS threads → Tokio runtime (lightweight)
- Thread pool → Work-stealing runtime
- `std::async()` → `async move {}` blocks
- Manual joining → `tokio::join!()` or `join_all()`

---

## Memory Management

### C++ (RAII + Smart Pointers)
```cpp
// Unique ownership
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();

// Shared ownership (reference counted)
std::shared_ptr<Agent> shared = std::make_shared<MyAgent>();
std::shared_ptr<Agent> copy = shared;  // Both own

// Move semantics
std::unique_ptr<Agent> moved = std::move(agent);  // agent is now nullptr

// RAII: Automatic cleanup
{
    std::unique_ptr<Agent> local = std::make_unique<MyAgent>();
    local->process(msg);
}  // Destructor called automatically
```

### Rust (Ownership)
```rust
// Unique ownership (default)
let agent = MyAgent::new();

// Shared ownership (reference counted)
use std::sync::Arc;
let shared = Arc::new(MyAgent::new());
let clone = Arc::clone(&shared);  // Both own (atomic refcount)

// Move semantics (default for non-Copy types)
let moved = agent;  // agent is now invalid (moved)

// Automatic cleanup (Drop trait)
{
    let local = MyAgent::new();
    local.process(msg);
}  // Drop called automatically (compile-time guaranteed)

// Borrowing (no ownership transfer)
fn use_agent(agent: &Agent) {  // Borrow, doesn't take ownership
    agent.process(msg);
}  // agent still valid in caller
```

**Changes**:
- `std::unique_ptr<T>` → `T` (owned) or `Box<T>` (heap)
- `std::shared_ptr<T>` → `Arc<T>` (multi-thread) or `Rc<T>` (single-thread)
- `std::move()` → Default behavior for non-`Copy` types
- RAII destructor → `Drop` trait (compile-time enforced)
- Manual lifetime tracking → Compiler-enforced lifetimes
- Runtime dangling pointer bugs → Compile-time prevention
- `nullptr` checks → Eliminated by type system

---

## Patterns

### Sequential

**C++**:
```cpp
#include <agenkit/patterns.hpp>

auto sequential = Sequential(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<Agent1>(),
    std::make_unique<Agent2>(),
    std::make_unique<Agent3>(),
});

auto result = sequential.process(msg).get();
```

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(Agent1::new()),
    Box::new(Agent2::new()),
    Box::new(Agent3::new()),
]);

let result = sequential.process(msg).await?;
```

### Parallel

**C++**:
```cpp
auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
    std::make_unique<AgentC>(),
});

auto result = parallel.process(msg).get();
```

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(AgentA::new()),
    Box::new(AgentB::new()),
    Box::new(AgentC::new()),
]);

let result = parallel.process(msg).await?;
```

**Changes**:
- `std::vector<std::unique_ptr<T>>` → `Vec<Box<dyn T>>`
- Constructor arguments → `::new()` associated functions
- `.get()` (blocking) → `.await` (async)
- Implicit error handling → `?` operator for `Result`

---

## Common Gotchas

### 1. String Ownership

**C++**: String views and references are common
```cpp
std::string_view get_name() const {
    return name_;  // Dangling if name_ is temporary!
}

const std::string& get_content(const Message& msg) {
    return msg.content;  // OK, caller owns msg
}
```

**Rust**: Compiler prevents dangling references
```rust
// Won't compile - can't return reference to local
// fn get_name() -> &str {
//     let name = String::from("agent");
//     &name  // ERROR: name dropped at end of function
// }

// Correct: Return owned String
fn get_name() -> String {
    String::from("agent")
}

// Or borrow with lifetime tied to self
fn get_name(&self) -> &str {
    &self.name  // OK, borrow valid as long as self exists
}
```

### 2. Mutable References

**C++**: Multiple mutable pointers/references allowed (undefined behavior if misused)
```cpp
std::string& ref1 = msg.content;
std::string& ref2 = msg.content;
ref1 += "foo";  // Could conflict with ref2 in multithreaded code
ref2 += "bar";
```

**Rust**: Only one mutable reference at a time (compile-time enforced)
```rust
let ref1 = &mut msg.content;
// let ref2 = &mut msg.content;  // ERROR: cannot borrow as mutable more than once
ref1.push_str("foo");

// Must drop ref1 before creating ref2
drop(ref1);
let ref2 = &mut msg.content;
ref2.push_str("bar");
```

### 3. Move Semantics

**C++**: Moved-from objects in valid but unspecified state
```cpp
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();
auto moved = std::move(agent);

// agent is now nullptr, but can still be used (undefined if dereferenced!)
if (agent) {  // Must check manually
    agent->process(msg);
}
```

**Rust**: Moved values are completely unusable (compile-time)
```rust
let agent = MyAgent::new();
let moved = agent;

// agent.process(msg);  // ERROR: value borrowed after move
// Compiler prevents use-after-move entirely
```

### 4. Exception Safety

**C++**: Exception safety guarantees must be maintained manually
```cpp
void process_messages(std::vector<Message>& messages) {
    for (auto& msg : messages) {
        process(msg);  // If throws, messages may be in inconsistent state
    }
}
```

**Rust**: No exceptions, explicit error handling
```rust
fn process_messages(messages: &mut Vec<Message>) -> Result<(), AgentError> {
    for msg in messages.iter_mut() {
        process(msg)?;  // Returns early on error, no cleanup needed
    }
    Ok(())
}
```

### 5. Concurrency and Data Races

**C++**: Data races are undefined behavior (runtime detection needed)
```cpp
std::string shared_data;

// Thread 1
std::thread t1([&shared_data]() {
    shared_data += "foo";  // Race condition!
});

// Thread 2
std::thread t2([&shared_data]() {
    shared_data += "bar";  // Race condition!
});
```

**Rust**: Data races prevented at compile time
```rust
let mut shared_data = String::new();

// Won't compile - can't share mutable reference across threads
// let t1 = std::thread::spawn(|| {
//     shared_data.push_str("foo");  // ERROR: shared_data not Send
// });

// Correct: Use Arc + Mutex
let shared_data = Arc::new(Mutex::new(String::new()));
let data1 = Arc::clone(&shared_data);
let data2 = Arc::clone(&shared_data);

let t1 = std::thread::spawn(move || {
    data1.lock().unwrap().push_str("foo");  // Safe, mutex protects
});

let t2 = std::thread::spawn(move || {
    data2.lock().unwrap().push_str("bar");  // Safe, mutex protects
});
```

---

## Testing

### C++
```cpp
#include <gtest/gtest.h>

TEST(MyAgentTest, ProcessMessage) {
    MyAgent agent;
    Message msg{
        .role = "user",
        .content = "Test",
    };

    auto result = agent.process(msg).get();

    EXPECT_EQ(result.role, "assistant");
    EXPECT_TRUE(result.content.find("Processed") != std::string::npos);
}

TEST(MyAgentTest, HandleEmptyMessage) {
    MyAgent agent;
    Message empty_msg{
        .role = "user",
        .content = "",
    };

    EXPECT_THROW(agent.process(empty_msg).get(), std::invalid_argument);
}
```

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_process_message() {
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
    async fn test_handle_empty_message() {
        let agent = MyAgent::new();
        let empty_msg = Message {
            role: Role::User,
            content: "".to_string(),
            ..Default::default()
        };

        let result = agent.process(empty_msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::InvalidMessage(_)));
    }
}
```

**Changes**:
- `TEST()` macro → `#[test]` or `#[tokio::test]`
- `EXPECT_EQ/EXPECT_TRUE` → `assert_eq!/assert!`
- `EXPECT_THROW` → `assert!(result.is_err())`
- `.get()` (blocking) → `.await` (async)
- Exception matching → `matches!()` macro for enum variants

---

## Performance Considerations

| Operation | C++ | Rust | Notes |
|-----------|-----|------|-------|
| Agent creation | ~50ns | ~50ns | Identical (both zero-cost) |
| Message processing | ~500ns | ~500ns | Identical (optimized) |
| Sequential (3 agents) | ~1.5μs | ~1.5μs | Identical throughput |
| Parallel (3 agents) | ~500ns | ~500ns | Identical (both efficient) |
| Thread spawn | ~5μs | ~100ns | Rust 50x faster (green threads) |
| Memory allocations | Direct | Same | Both zero-cost abstractions |
| Compilation time | Moderate | Slower | Rust has more compile-time checks |

**When to migrate to Rust**:
- Memory safety is critical (eliminate entire bug classes)
- Prevent data races at compile time
- Need async/await ecosystem (tokio, serde, etc.)
- Want guaranteed memory safety without runtime overhead
- Building WebAssembly modules
- Long-term maintenance (fewer runtime bugs)

**When to keep C++**:
- Existing large C++ codebase
- Need C ABI compatibility (though Rust supports this)
- Team expertise in C++ (learning curve is steep)
- Compile times are critical (Rust is slower)
- Need specific C++ libraries not available in Rust

---

## Migration Checklist

- [ ] Replace `class` inheritance with trait (`impl Trait for Type`)
- [ ] Convert exceptions to `Result<T, E>` return types
- [ ] Change `std::future` to `async fn` with `.await`
- [ ] Replace `std::unique_ptr<T>` with `T` or `Box<T>`
- [ ] Replace `std::shared_ptr<T>` with `Arc<T>` or `Rc<T>`
- [ ] Update error handling: `try/catch` → `match` or `?` operator
- [ ] Convert `std::thread` to `tokio::spawn()` (or keep for OS threads)
- [ ] Replace raw/smart pointers with borrowing (`&` and `&mut`)
- [ ] Add `#[async_trait]` for async trait methods
- [ ] Update string types: `std::string` → `String`, string literals → `.to_string()`
- [ ] Convert collections: `std::vector` → `Vec`, `std::map` → `HashMap`
- [ ] Update tests: Google Test → `#[test]` or `#[tokio::test]`
- [ ] Add explicit ownership and borrowing annotations
- [ ] Replace `nullptr` checks with `Option<T>`

---

## Quick Start

```bash
# C++ project structure
agenkit-cpp/
├── CMakeLists.txt
├── main.cpp
└── agent.cpp

# Rust equivalent
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   └── agent.rs
```

**Build/Run**:
```bash
# C++
mkdir build && cd build
cmake ..
make
./myagent

# Rust
cargo build --release
cargo run --release
```

**Add Dependencies**:
```bash
# C++ (CMakeLists.txt)
find_package(agenkit REQUIRED)
target_link_libraries(myapp agenkit)

# Rust (Cargo.toml)
[dependencies]
agenkit = "0.46"
tokio = { version = "1.0", features = ["full"] }
async-trait = "0.1"
```

---

## Full Resources

- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [The Rust Book](https://doc.rust-lang.org/book/) - Official learning resource
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
