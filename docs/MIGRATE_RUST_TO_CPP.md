# Quick Reference: Rust → C++ Migration

**For**: Rust developers migrating Agenkit code to C++
**Time**: 15 minute read
**Full Details**: See [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) and [C++ Language Profile](LANGUAGE_PROFILE_CPP.md)

---

## Key Differences at a Glance

| Aspect | Rust | C++ |
|--------|------|-----|
| **Typing** | Static, ownership-based | Static, manual/RAII |
| **Errors** | `Result<T, E>` (explicit) | Exceptions or `std::expected` |
| **Concurrency** | async/await (tokio) | std::thread (OS threads) |
| **Memory** | Ownership + borrow checker | RAII + smart pointers |
| **Performance** | Zero-cost abstractions | Zero-overhead abstractions |
| **Safety** | Compile-time guarantees | Runtime checks optional |

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

### C++
```cpp
#include <agenkit/message.hpp>

Message msg{
    .role = "user",
    .content = "Hello!",
};

// With metadata
Message msg{
    .role = "assistant",
    .content = "Response",
    .metadata = {
        {"key", "value"},
    },
};
```

**Changes**:
- `Role::User` enum → `"user"` string literal
- `.to_string()` → Direct string literals
- `HashMap` → `std::map` or designated initializers
- `..Default::default()` → Not needed (members have defaults)

---

## Agent Implementation

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, AgentError};

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

### C++
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public Agent {
    std::string name_;
    Config config_;

public:
    explicit MyAgent(std::string name, Config config)
        : name_(std::move(name)), config_(std::move(config)) {}

    std::string name() const override {
        return name_;
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

**Changes**:
- Trait → Abstract base class (`virtual` methods)
- `#[async_trait]` → `std::future` + `std::async`
- `impl` block → Class member functions
- `&self` → `this` pointer (implicit or explicit)
- Borrowing (`&str`) → Value return or `const&`
- `Result<T, E>` → Return `std::future<T>`, throw exceptions

---

## Error Handling

### Rust
```rust
// Result type is explicit
let result = agent.process(msg).await;

match result {
    Ok(response) => println!("Success: {}", response.content),
    Err(e) => eprintln!("Error: {}", e),
}

// Or use ? operator
async fn handle_request(msg: Message) -> Result<Message, AgentError> {
    let agent = create_agent()?;
    let result = agent.process(msg).await?;
    Ok(result)
}
```

### C++
```cpp
// Option 1: Exceptions (traditional)
try {
    Message result = agent.process(msg).get();
    std::cout << "Success: " << result.content << '\n';
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}

// Option 2: std::expected (C++23, Rust-like)
std::expected<Message, AgentError> safe_process(
    Agent& agent,
    const Message& msg
) {
    if (msg.content.empty()) {
        return std::unexpected(AgentError::InvalidMessage);
    }

    try {
        return agent.process(msg).get();
    } catch (const std::exception& e) {
        return std::unexpected(AgentError::ProcessingFailed);
    }
}

auto result = safe_process(agent, msg);
if (result) {
    std::cout << "Success: " << result.value().content << '\n';
} else {
    std::cerr << "Error code: " << static_cast<int>(result.error()) << '\n';
}
```

**Changes**:
- `Result<T, E>` → `std::expected<T, E>` (C++23) or exceptions
- `?` operator → `.get()` (throws) or explicit checks
- Pattern matching → `if (result)` or `try/catch`
- Explicit error handling → Can be implicit with exceptions

---

## Concurrency

### Rust (Tokio)
```rust
use tokio;

// Spawn task on tokio runtime
tokio::spawn(async move {
    let result = agent.process(msg).await;
    match result {
        Ok(resp) => println!("Success: {}", resp.content),
        Err(e) => eprintln!("Error: {}", e),
    }
});

// Join multiple tasks
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

// Channels
let (tx, mut rx) = tokio::sync::mpsc::channel(32);
tx.send(message).await.unwrap();
while let Some(msg) = rx.recv().await {
    println!("Received: {}", msg.content);
}
```

### C++ (std::thread)
```cpp
#include <thread>
#include <future>

// Spawn OS thread
std::thread t([&agent, msg]() {
    try {
        Message result = agent.process(msg).get();
        std::cout << "Success: " << result.content << '\n';
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << '\n';
    }
});
t.join();  // Wait for completion

// Launch async tasks
auto future1 = std::async(std::launch::async, [&]() { return agent1.process(msg).get(); });
auto future2 = std::async(std::launch::async, [&]() { return agent2.process(msg).get(); });
auto future3 = std::async(std::launch::async, [&]() { return agent3.process(msg).get(); });

auto res1 = future1.get();
auto res2 = future2.get();
auto res3 = future3.get();

// No built-in select - use wait_for with timeout
auto status = future1.wait_for(std::chrono::milliseconds(100));
if (status == std::future_status::ready) {
    auto res = future1.get();
}

// Thread-safe queue (manual implementation)
#include <queue>
#include <mutex>
#include <condition_variable>

class ThreadSafeQueue {
    std::queue<Message> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cond_;

public:
    void push(Message msg) {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(std::move(msg));
        cond_.notify_one();
    }

    Message pop() {
        std::unique_lock<std::mutex> lock(mutex_);
        cond_.wait(lock, [this] { return !queue_.empty(); });
        Message msg = std::move(queue_.front());
        queue_.pop();
        return msg;
    }
};
```

**Changes**:
- `tokio::spawn` → `std::thread` or `std::async`
- Green threads → OS threads (heavier)
- `tokio::join!` → Multiple `.get()` calls
- `tokio::select!` → Manual polling with `wait_for()`
- `tokio::sync::mpsc` → Manual queue with mutex
- `.await` → `.get()` (blocks)

---

## Memory Management

### Rust (Ownership)
```rust
// Ownership enforced at compile time
let msg = Message {
    role: Role::User,
    content: "Hello".to_string(),
    ..Default::default()
};

// Borrowing (no ownership transfer)
fn process_msg(msg: &Message) {
    println!("{}", msg.content);
}  // Borrow ends, msg still valid in caller

// Move (ownership transfer)
let msg2 = msg;  // msg is now invalid

// Shared ownership with Arc
use std::sync::Arc;
let agent = Arc::new(MyAgent::new());
let agent_clone = Arc::clone(&agent);

tokio::spawn(async move {
    agent_clone.process(msg).await;
});
```

### C++ (RAII + Smart Pointers)
```cpp
// Value semantics by default
Message msg{
    .role = "user",
    .content = "Hello",
};

// Passing by reference (similar to Rust borrow)
void process_msg(const Message& msg) {
    std::cout << msg.content << '\n';
}  // No ownership transfer

// Move semantics (explicit)
Message msg2 = std::move(msg);  // msg is now in moved-from state

// Smart pointers for shared ownership
auto agent = std::make_shared<MyAgent>();
auto agent_copy = agent;  // Reference count incremented

std::thread t([agent_copy, msg]() {
    agent_copy->process(msg).get();
});
t.detach();

// Unique ownership
auto unique = std::make_unique<MyAgent>();  // Exclusive ownership
// auto copy = unique;  // Error: cannot copy unique_ptr
auto moved = std::move(unique);  // Transfer ownership
```

**Changes**:
- Borrow checker → Programmer discipline
- `&T` and `&mut T` → `const T&` and `T&` (no compiler enforcement)
- `Arc<T>` → `std::shared_ptr<T>` (similar reference counting)
- `Box<T>` → `std::unique_ptr<T>` (exclusive ownership)
- Compile-time safety → Runtime bugs possible (use-after-move)

**Key Gotcha**: C++ allows use-after-move (undefined behavior), Rust prevents it:
```cpp
// C++ - compiles but UNDEFINED BEHAVIOR
auto msg = Message{.role = "user", .content = "Hello"};
auto msg2 = std::move(msg);
std::cout << msg.content;  // UB! msg was moved

// Rust equivalent - compile error
let msg = Message { /* ... */ };
let msg2 = msg;
println!("{}", msg.content);  // Error: value borrowed after move
```

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

**C++**:
```cpp
#include <agenkit/patterns.hpp>

auto sequential = Sequential(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<Agent1>(),
    std::make_unique<Agent2>(),
    std::make_unique<Agent3>(),
});

Message result = sequential.process(msg).get();
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

**C++**:
```cpp
#include <agenkit/patterns.hpp>

auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
    std::make_unique<AgentC>(),
});

Message result = parallel.process(msg).get();
```

---

## Common Gotchas

### 1. Ownership vs References

**Rust**: Compiler enforces borrow rules
```rust
fn process(msg: Message) { }      // Takes ownership
fn process_ref(msg: &Message) { } // Borrows immutably
fn process_mut(msg: &mut Message) { } // Borrows mutably
// Compiler prevents use-after-move and data races
```

**C++**: Programmer must track ownership
```cpp
void process(Message msg) { }         // Takes by value (copy)
void process_ref(const Message& msg) { } // Reference (no copy)
void process_mut(Message& msg) { }    // Mutable reference

// Dangling reference possible!
const Message& get_message() {
    Message temp{.role = "user", .content = "Hi"};
    return temp;  // Compiles but UNDEFINED BEHAVIOR
}
```

**Migration Tip**: In C++, prefer passing by `const&` for read-only access, and use smart pointers for ownership transfer.

### 2. Result vs Exceptions

**Rust**: Errors are values
```rust
// Must explicitly handle Result
match agent.process(msg).await {
    Ok(result) => { /* ... */ },
    Err(e) => { /* ... */ },  // Compiler forces handling
}

// Or propagate with ?
let result = agent.process(msg).await?;  // Explicit propagation
```

**C++**: Exceptions can be ignored
```cpp
// Exception can propagate silently
Message result = agent.process(msg).get();  // May throw

// Easy to forget error handling
try {
    Message result = agent.process(msg).get();
} catch (...) {  // Catches ALL exceptions - too broad
}
```

**Migration Tip**: Use `std::expected<T, E>` (C++23) to get Rust-like explicit error handling, or be disciplined with exception handling.

### 3. Async Runtime

**Rust**: Cooperative multitasking
```rust
// Lightweight tasks (green threads)
for _ in 0..10000 {
    tokio::spawn(async { /* work */ });  // Low overhead
}

// Tasks yield at .await points
let data = fetch_data().await;  // Yields to runtime
```

**C++**: OS threads
```cpp
// Heavyweight threads
for (int i = 0; i < 10000; ++i) {
    std::thread([](){ /* work */ }).detach();  // High overhead!
}

// Blocking calls don't yield
Message data = fetch_data().get();  // Blocks thread
```

**Migration Tip**: Consider thread pools or a task library (e.g., Boost.Asio, folly::Future) for efficient concurrency in C++.

### 4. Lifetime Elision

**Rust**: Compiler infers lifetimes
```rust
// Lifetimes explicit when needed
fn first_word<'a>(s: &'a str) -> &'a str {
    s.split_whitespace().next().unwrap()
}

// Often inferred
fn first_word(s: &str) -> &str {  // Lifetimes implicit
    s.split_whitespace().next().unwrap()
}
```

**C++**: No lifetime tracking
```cpp
// Returning reference to parameter - programmer must ensure validity
const std::string& first_word(const std::string& s) {
    // Dangling reference if returning temporary!
    static std::istringstream iss;
    iss.str(s);
    static std::string word;
    iss >> word;
    return word;  // Safe only because static
}
```

**Migration Tip**: Be extra careful with references in C++. When in doubt, return by value (compilers optimize with move semantics).

### 5. Pattern Matching vs Switch

**Rust**: Exhaustive pattern matching
```rust
match role {
    Role::User => println!("User"),
    Role::Assistant => println!("Assistant"),
    Role::System => println!("System"),
    // Compiler error if any variant is missing
}
```

**C++**: Switch on integral types
```cpp
enum class Role { User, Assistant, System };

switch (role) {
    case Role::User:
        std::cout << "User\n";
        break;
    case Role::Assistant:
        std::cout << "Assistant\n";
        break;
    // Compiles even if System is missing (warning with -Wall)
}

// For string-based roles, use if-else
if (role == "user") {
    // ...
} else if (role == "assistant") {
    // ...
}
```

**Migration Tip**: Enable `-Wall -Wextra -Werror` to catch non-exhaustive switches.

---

## Testing

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent::new("test-agent".to_string());
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
        let agent = MyAgent::new("test-agent".to_string());
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

### C++
```cpp
#include <gtest/gtest.h>

TEST(MyAgentTest, ProcessMessage) {
    MyAgent agent("test-agent", Config{});
    Message msg{
        .role = "user",
        .content = "Test",
    };

    Message result = agent.process(msg).get();

    EXPECT_EQ(result.role, "assistant");
    EXPECT_NE(result.content.find("Processed"), std::string::npos);
}

TEST(MyAgentTest, HandleEmptyMessage) {
    MyAgent agent("test-agent", Config{});
    Message empty_msg{
        .role = "user",
        .content = "",
    };

    EXPECT_THROW(agent.process(empty_msg).get(), std::invalid_argument);
}

TEST(MyAgentTest, AsyncProcessing) {
    MyAgent agent("test-agent", Config{});
    Message msg{.role = "user", .content = "Test"};

    auto future = agent.process(msg);

    // Can do other work here

    Message result = future.get();
    EXPECT_EQ(result.role, "assistant");
}
```

**Changes**:
- `#[test]` → `TEST(Suite, Name)` macro
- `#[tokio::test]` → Regular test with `.get()` blocking
- `assert!` → `EXPECT_TRUE` / `ASSERT_TRUE`
- `assert_eq!` → `EXPECT_EQ` / `ASSERT_EQ`
- `matches!` → `EXPECT_THROW` or manual type checking

---

## Performance Considerations

| Operation | Rust (tokio) | C++ (std::thread) | Notes |
|-----------|--------------|-------------------|-------|
| Agent creation | ~50ns | ~50ns | Comparable |
| Message processing | ~500ns | ~500ns | Comparable |
| Sequential (3 agents) | ~1.5μs | ~1.5μs | Similar abstraction cost |
| Parallel (3 agents) | ~500ns | ~500ns | C++ may be heavier with OS threads |
| Task spawn | ~100ns | ~5μs | Rust 50x faster (green threads vs OS threads) |
| Memory safety | Compile-time | Runtime (if checked) | Rust prevents bugs at compile time |

**When to use C++**:
- Legacy codebase integration (existing C++ infrastructure)
- C ABI compatibility requirements
- Specific library dependencies (e.g., CUDA, TensorFlow C++)
- Team expertise (established C++ team)
- Gradual migration from C++98/11/14 codebases

**When to keep Rust**:
- Greenfield projects (no legacy constraints)
- Memory safety critical (prevents entire bug classes)
- Concurrent workloads (tokio's efficiency)
- WebAssembly targets (better tooling)
- Modern development (better build system, package manager)

---

## Migration Checklist

- [ ] Replace `trait` implementations with `virtual` base classes
- [ ] Convert `Result<T, E>` to `std::expected<T, E>` or exceptions
- [ ] Change `async fn` to `std::future` + `std::async`
- [ ] Update `tokio::spawn` to `std::thread` or `std::async`
- [ ] Replace `Arc<T>` with `std::shared_ptr<T>`
- [ ] Replace `Box<T>` with `std::unique_ptr<T>`
- [ ] Convert `.await` to `.get()` (blocking)
- [ ] Change ownership patterns to smart pointers + references
- [ ] Update tests: `#[test]` → `TEST()` macro
- [ ] Replace `?` operator with explicit error handling
- [ ] Convert enums to `enum class` or string literals
- [ ] Update build: `Cargo.toml` → `CMakeLists.txt`
- [ ] Add manual synchronization for concurrent access

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

# C++ equivalent
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── agent.cpp
├── include/
│   └── agent.hpp
└── tests/
```

**Build/Run**:
```bash
# Rust
cargo build --release
cargo run

# C++
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
./agenkit-app
```

---

## Type Mapping Reference

| Rust Type | C++ Equivalent | Notes |
|-----------|----------------|-------|
| `String` | `std::string` | Owned string |
| `&str` | `std::string_view` or `const std::string&` | String reference |
| `Vec<T>` | `std::vector<T>` | Dynamic array |
| `HashMap<K, V>` | `std::unordered_map<K, V>` | Hash table |
| `Option<T>` | `std::optional<T>` | Maybe value |
| `Result<T, E>` | `std::expected<T, E>` (C++23) | Fallible result |
| `Box<T>` | `std::unique_ptr<T>` | Unique ownership |
| `Arc<T>` | `std::shared_ptr<T>` | Shared ownership |
| `Rc<T>` | `std::shared_ptr<T>` | Shared (non-atomic) |
| `Mutex<T>` | `std::mutex` + data | Mutual exclusion |
| `async fn` | `std::future<T>` | Async function |
| `trait` | Abstract base class | Interface |

---

## Full Resources

- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
