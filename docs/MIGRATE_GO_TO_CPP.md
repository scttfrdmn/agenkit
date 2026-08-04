# Quick Reference: Go → C++ Migration

**For**: Go developers migrating Agenkit code to C++
**Time**: 15 minute read
**Full Details**: See [Go Language Profile](LANGUAGE_PROFILE_GO.md) and [C++ Language Profile](LANGUAGE_PROFILE_CPP.md)

---

## Key Differences at a Glance

| Aspect | Go | C++ |
|--------|----|----|
| **Typing** | Static, explicit | Static, explicit + templates |
| **Errors** | `(result, error)` returns | Exceptions or `std::expected` |
| **Concurrency** | Goroutines + channels | `std::thread`, `std::async` |
| **Memory** | GC, automatic | Manual + RAII + smart pointers |
| **Performance** | Fast (compiled) | Very fast (zero overhead) |
| **Deployment** | Single binary | Single binary (larger) |

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

// Or using builder
auto msg = MessageBuilder()
    .role("user")
    .content("Hello!")
    .metadata("key", "value")
    .build();
```

**Changes**:
- Import: `import` → `#include`
- Package: `agenkit-go` → `<agenkit/message.hpp>`
- Struct literal: similar designated initializers (C++20)
- Constants: `agenkit.RoleUser` → `"user"` string
- Type: `map[string]interface{}` → `std::map<std::string, std::any>`
- Semicolons required

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

### C++
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public Agent {
    std::string name_;

public:
    explicit MyAgent(std::string name)
        : name_(std::move(name)) {}

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"text"};
    }

    std::future<Message> process(const Message& msg) override {
        return std::async(std::launch::async, [this, msg]() {
            return Message{
                .role = "assistant",
                .content = "Response",
            };
        });
    }
};
```

**Changes**:
- Struct → `class` with inheritance
- Methods: `func (a *MyAgent)` → member functions with `override`
- Constructor: explicit `MyAgent(...)` with initializer list
- `ctx context.Context` → removed (or pass custom context)
- `(result, error)` → `std::future<Result>` for async
- `[]string` → `std::vector<std::string>`
- `const` for read-only methods
- Virtual destructor needed: `virtual ~Agent() = default;`

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

### C++ (Modern with std::expected)
```cpp
// Using std::expected (C++23)
auto result = process_message(agent, msg);
if (result) {
    // Use result.value()
} else {
    // Handle result.error()
    return std::unexpected(
        AgentError::ProcessingFailed
    );
}

// Or with exceptions
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const std::exception& e) {
    throw std::runtime_error(
        std::string("process failed: ") + e.what()
    );
}
```

**Changes**:
- `if err != nil` → `if (result)` or `try/catch`
- Error wrapping: `fmt.Errorf(..., %w, err)` → exception chaining or `std::expected`
- Must check future with `.get()` (blocks until ready)
- Exception unwinding vs explicit checks

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

### C++ (std::async and threads)
```cpp
// Launch async task
auto future = std::async(std::launch::async, [&agent, msg]() {
    try {
        return agent.process(msg).get();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << '\n';
        throw;
    }
});

// Wait for result
Message result = future.get();

// Wait for multiple with futures
std::vector<std::future<Message>> futures;
for (auto& agent : agents) {
    futures.push_back(
        std::async(std::launch::async, [&agent, msg]() {
            return agent.process(msg).get();
        })
    );
}

// Collect results
for (auto& fut : futures) {
    Message result = fut.get();
}
```

**Changes**:
- `go func()` → `std::async(std::launch::async, []{})`
- `sync.WaitGroup` → `std::vector<std::future<T>>`
- `context.Context` → custom cancellation mechanism
- Channels → `std::queue` + `std::mutex` + `std::condition_variable`
- Heavier weight than goroutines (OS threads)

---

## Patterns

### Sequential

**Go**:
```go
sequential := patterns.NewSequential([]agenkit.Agent{agent1, agent2})
result, err := sequential.Process(ctx, msg)
```

**C++**:
```cpp
#include <agenkit/patterns.hpp>

auto sequential = Sequential(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<Agent1>(),
    std::make_unique<Agent2>(),
});

Message result = sequential.process(msg).get();
```

### Parallel

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{agentA, agentB})
result, err := parallel.Process(ctx, msg)
```

**C++**:
```cpp
auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
});

Message result = parallel.process(msg).get();
```

---

## Common Gotchas

### 1. Memory Management

**Go**: GC handles everything
**C++**: RAII + smart pointers or manual

```go
// Go - automatic cleanup
msg := agenkit.Message{Content: "Hello"}
// msg cleaned up automatically
```

```cpp
// C++ - use smart pointers
auto msg = std::make_unique<Message>(Message{
    .content = "Hello",
});
// msg deleted automatically when out of scope

// Or use values (RAII)
Message msg{.content = "Hello"};
// Destructor called automatically
```

### 2. String Handling

**Go**: Single `string` type
**C++**: `std::string`, `const char*`, `std::string_view`

```go
// Go
func get_name() string {
    return "Agent"
}
```

```cpp
// C++ - return by value
std::string get_name() {
    return "Agent";
}

// Or return string_view for efficiency (C++17)
std::string_view get_name() {
    return "Agent";  // Must outlive the view
}

// Or const reference
const std::string& get_name(const std::string& stored) {
    return stored;
}
```

### 3. Nil vs nullptr

**Go**: `nil` for zero value
**C++**: `nullptr` for pointers, `std::optional<T>` for optional values

```go
// Go
var msg *Message = nil
if msg != nil {
    // Use msg
}
```

```cpp
// C++ with raw pointer
Message* msg = nullptr;
if (msg != nullptr) {
    // Use msg
}

// Better: use std::optional
std::optional<Message> msg = std::nullopt;
if (msg.has_value()) {
    // Use msg.value()
}
```

### 4. Slice vs Vector

**Go**: Slices are dynamic, backed by arrays
**C++**: `std::vector` is dynamic array

```go
// Go
slice := make([]string, 0, 10)
slice = append(slice, "item")
len := len(slice)
cap := cap(slice)
```

```cpp
// C++
std::vector<std::string> vec;
vec.reserve(10);  // Capacity hint
vec.push_back("item");
size_t len = vec.size();
size_t cap = vec.capacity();
```

### 5. Move Semantics

**Go**: Copying or GC
**C++**: Move for efficiency

```go
// Go - copied or GC'd
msg1 := agenkit.Message{Content: "Hello"}
msg2 := msg1  // Copy
```

```cpp
// C++ - explicit move
Message msg1{.content = "Hello"};
Message msg2 = std::move(msg1);  // msg1 now invalid

// Or pass by const reference to avoid copy
void process(const Message& msg) {
    // Read-only access, no copy
}
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

### C++
```cpp
#include <gtest/gtest.h>

TEST(MyAgentTest, ProcessMessage) {
    MyAgent agent("test");
    Message msg{
        .role = "user",
        .content = "Test",
    };

    Message result = agent.process(msg).get();

    EXPECT_EQ(result.role, "assistant");
    EXPECT_TRUE(result.content.find("Expected") != std::string::npos);
}

TEST(MyAgentTest, HandleError) {
    MyAgent agent("test");
    Message empty{.role = "user", .content = ""};

    EXPECT_THROW(agent.process(empty).get(), std::invalid_argument);
}
```

**Changes**:
- `func TestXxx(t *testing.T)` → `TEST(Suite, Name)`
- `t.Fatalf/t.Errorf` → `EXPECT_*` or `ASSERT_*` macros
- Use Google Test, Catch2, or similar framework
- No `context.Background()` needed

---

## Performance Considerations

| Operation | Go | C++ | Notes |
|-----------|----|----|-------|
| Agent creation | ~100ns | ~50ns | C++ 2x faster |
| Message processing | ~1μs | ~500ns | C++ 2x faster |
| Sequential (3 agents) | ~3μs | ~1.5μs | C++ 2x faster |
| Parallel (3 agents) | ~1μs | ~500ns | C++ better control |

**When to use C++**:
- Maximum performance required
- Fine-grained memory control needed
- Legacy C/C++ integration
- Embedded systems
- Game development or graphics
- When binary size matters (with optimization)

**When to keep Go**:
- Faster development (no manual memory)
- Simpler concurrency (goroutines)
- Built-in GC acceptable
- Faster compilation times
- Team expertise in Go

---

## Migration Checklist

- [ ] Replace `struct` with `class` + inheritance
- [ ] Convert `(result, error)` to `std::future` or `std::expected`
- [ ] Change goroutines to `std::async` or `std::thread`
- [ ] Remove `context.Context` parameter (or implement custom)
- [ ] Update imports: `import` → `#include`
- [ ] Add smart pointers: `std::unique_ptr`, `std::shared_ptr`
- [ ] Use move semantics for efficiency: `std::move()`
- [ ] Convert `nil` to `nullptr` or `std::optional`
- [ ] Update error handling: `if err != nil` → `try/catch` or `if (result)`
- [ ] Change tests: `*testing.T` → Google Test macros
- [ ] Add virtual destructors to base classes
- [ ] Configure CMake build system
- [ ] Handle const-correctness (`const` methods, parameters)

---

## Quick Start

```bash
# Go project structure
agenkit-go/
├── go.mod
├── main.go
└── agent.go

# C++ equivalent
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── agent.hpp
├── include/
│   └── agenkit/
└── build/  # Build output
```

**Build/Run**:
```bash
# Go
go build -o myagent
./myagent

# C++
mkdir build && cd build
cmake ..
cmake --build . --config Release
./myagent
```

**Project Setup**:
```bash
# Create CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(myagent)

set(CMAKE_CXX_STANDARD 20)

find_package(agenkit REQUIRED)

add_executable(myagent src/main.cpp)
target_link_libraries(myagent agenkit::core)
```

---

## Full Resources

- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms
- [C++ Reference](https://en.cppreference.com/) - Comprehensive reference
- [Agenkit C++ Examples](../agenkit-cpp/examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
