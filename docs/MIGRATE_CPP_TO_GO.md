# Quick Reference: C++ → Go Migration

**For**: C++ developers migrating Agenkit code to Go
**Time**: 15 minute read
**Full Details**: See [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) and [Go Language Profile](LANGUAGE_PROFILE_GO.md)

---

## Key Differences at a Glance

| Aspect | C++ | Go |
|--------|-----|-----|
| **Typing** | Static, templates | Static, interfaces |
| **Errors** | Exceptions or `std::expected` | `(result, error)` returns |
| **Concurrency** | `std::thread` (OS threads) | Goroutines (green threads) |
| **Memory** | Manual + RAII | GC, automatic |
| **Performance** | Fastest (zero overhead) | Fast (GC overhead) |
| **Deployment** | Single binary | Single binary |
| **Compilation** | Slow (templates) | Fast (minutes → seconds) |

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
        {"confidence", 0.95},
    },
};

// With timestamp
msg.timestamp = std::chrono::system_clock::now();
```

### Go
```go
import "github.com/agenkit/agenkit-go"
import "time"

msg := agenkit.Message{
    Role:    agenkit.RoleUser,
    Content: "Hello!",
    Metadata: map[string]interface{}{
        "key":        "value",
        "confidence": 0.95,
    },
}

// With timestamp
msg.Timestamp = time.Now()
```

**Changes**:
- Designated initializers `{.field = value}` → Struct literals `{Field: value}`
- `std::map` → `map[string]interface{}`
- `std::chrono::system_clock::now()` → `time.Now()`
- `std::optional<T>` → Pointer `*T` or zero value
- Lowercase vs Uppercase: `role` → `Role` (exported fields must be capitalized)

---

## Agent Implementation

### C++
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public Agent {
    std::string name_;
    std::vector<std::string> capabilities_;

public:
    explicit MyAgent(std::string name)
        : name_(std::move(name))
        , capabilities_({"text", "analysis"}) {}

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return capabilities_;
    }

    std::future<Message> process(const Message& msg) override {
        return std::async(std::launch::async, [this, msg]() {
            return Message{
                .role = "assistant",
                .content = "Response: " + msg.content,
            };
        });
    }
};
```

### Go
```go
import (
    "context"
    "fmt"
    "github.com/agenkit/agenkit-go"
)

type MyAgent struct {
    name         string
    capabilities []string
}

func NewMyAgent(name string) *MyAgent {
    return &MyAgent{
        name:         name,
        capabilities: []string{"text", "analysis"},
    }
}

func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return a.capabilities
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    return agenkit.Message{
        Role:    agenkit.RoleAssistant,
        Content: fmt.Sprintf("Response: %s", msg.Content),
    }, nil
}
```

**Changes**:
- Abstract class → Interface (implicit implementation)
- Constructor `explicit MyAgent()` → Factory function `NewMyAgent()`
- `override` keyword → Method on struct type
- `std::future<T>` → `(result, error)` return
- `std::async` → Goroutines (if needed)
- `this` pointer → Receiver `(a *MyAgent)`
- `const` methods → No concept (convention: don't mutate in getters)
- Virtual inheritance → Composition

---

## Error Handling

### C++ (Exceptions)
```cpp
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const std::runtime_error& e) {
    std::cerr << "Runtime error: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}

// Or with std::expected (C++23)
auto result = process_message(agent, msg);
if (result) {
    Message response = result.value();
} else {
    AgentError error = result.error();
}
```

### Go
```go
result, err := agent.Process(ctx, msg)
if err != nil {
    return nil, fmt.Errorf("agent failed: %w", err)
}
// Use result safely here

// Check specific error types
if errors.Is(err, context.Canceled) {
    log.Println("Operation canceled")
}
```

**Changes**:
- `try/catch` → `if err != nil` checks
- `throw exception` → `return error`
- Exception unwinding → Explicit error propagation
- `e.what()` → `err.Error()`
- Error wrapping: `throw nested` → `fmt.Errorf("context: %w", err)`
- No automatic cleanup on exception → Use `defer` for cleanup
- `std::expected<T, E>` → `(T, error)` tuple

**IMPORTANT**: This is the biggest paradigm shift from C++ to Go. Exceptions become explicit error returns.

---

## Memory Management

### C++ (RAII + Smart Pointers)
```cpp
// RAII: Automatic cleanup
{
    std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();
    agent->process(msg).get();
} // agent automatically deleted

// Shared ownership
std::shared_ptr<Agent> shared = std::make_shared<MyAgent>();
std::shared_ptr<Agent> copy = shared;  // Reference counted

// Manual file management with RAII
class FileHandler {
    std::FILE* file_;
public:
    FileHandler(const char* path) : file_(std::fopen(path, "r")) {
        if (!file_) throw std::runtime_error("Failed to open");
    }
    ~FileHandler() {
        if (file_) std::fclose(file_);
    }
};
```

### Go
```go
// Garbage collected - no manual management
{
    agent := NewMyAgent()
    agent.Process(ctx, msg)
} // agent freed automatically by GC

// No reference counting - GC handles everything
agent1 := NewMyAgent()
agent2 := agent1  // Both point to same agent, GC-managed

// File management with defer
func processFile(path string) error {
    file, err := os.Open(path)
    if err != nil {
        return fmt.Errorf("failed to open: %w", err)
    }
    defer file.Close()  // Automatic cleanup at function exit

    // Use file...
    return nil
}
```

**Changes**:
- `std::unique_ptr` → Regular pointers (GC-managed)
- `std::shared_ptr` → Regular pointers (no explicit refcounting)
- Destructors `~ClassName()` → `defer` statements
- RAII pattern → `defer` pattern
- Manual memory control → GC (simpler but less control)
- `new`/`delete` → `new()` or `&Type{}` (GC handles deletion)
- No move semantics (Go copies or shares via pointers)

**Why migrate**: Simpler code, no memory leaks, faster development

---

## Concurrency

### C++ (OS Threads)
```cpp
#include <thread>
#include <future>
#include <vector>

// Spawn thread
std::thread t([]() {
    process_data();
});
t.join();

// Async with future
std::future<Message> future = std::async(std::launch::async, [&]() {
    return agent.process(msg).get();
});
Message result = future.get();

// Multiple threads
std::vector<std::thread> threads;
for (int i = 0; i < 10; i++) {
    threads.emplace_back([i]() {
        process_task(i);
    });
}
for (auto& t : threads) {
    t.join();
}
```

### Go (Goroutines)
```go
import (
    "context"
    "sync"
)

// Spawn goroutine
go func() {
    processData()
}()

// With result channel
resultCh := make(chan agenkit.Message, 1)
go func() {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        log.Printf("Error: %v", err)
        return
    }
    resultCh <- result
}()
result := <-resultCh

// Multiple goroutines with WaitGroup
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(id int) {
        defer wg.Done()
        processTask(id)
    }(i)
}
wg.Wait()
```

**Changes**:
- `std::thread` → `go func()` (OS threads → green threads)
- `std::future` → Channels (`chan T`)
- `std::promise` → Channel send
- `.get()` on future → `<-channel` receive
- Thread join → `sync.WaitGroup` or channel close
- Thread-local storage → Per-goroutine context
- ~2MB stack per thread → 2KB per goroutine (500x lighter!)

**Performance Impact**:
- C++: 1,000s of threads before issues
- Go: Millions of goroutines easily

---

## Concurrency Synchronization

### C++ (Mutexes)
```cpp
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

### Go (Channels - Preferred)
```go
// Idiomatic Go: Use channels instead of mutexes
type ThreadSafeQueue struct {
    ch chan agenkit.Message
}

func NewThreadSafeQueue(capacity int) *ThreadSafeQueue {
    return &ThreadSafeQueue{
        ch: make(chan agenkit.Message, capacity),
    }
}

func (q *ThreadSafeQueue) Push(msg agenkit.Message) {
    q.ch <- msg  // Thread-safe by design
}

func (q *ThreadSafeQueue) Pop() agenkit.Message {
    return <-q.ch  // Blocks until available
}

// Or with mutex if needed
import "sync"

type MutexQueue struct {
    queue []agenkit.Message
    mu    sync.Mutex
}

func (q *MutexQueue) Push(msg agenkit.Message) {
    q.mu.Lock()
    defer q.mu.Unlock()
    q.queue = append(q.queue, msg)
}
```

**Changes**:
- `std::mutex` → `sync.Mutex` (but prefer channels)
- `std::condition_variable` → Channels (blocking send/receive)
- `std::lock_guard` → `defer mutex.Unlock()`
- `std::unique_lock` → `mutex.Lock()` + `defer mutex.Unlock()`

**Go Philosophy**: "Don't communicate by sharing memory; share memory by communicating" (use channels)

---

## Context and Cancellation

### C++ (No Built-in Concept)
```cpp
// Manual cancellation with atomic flag
#include <atomic>

std::atomic<bool> canceled{false};

void process() {
    while (!canceled.load()) {
        // Do work
    }
}

// Separate thread to cancel
canceled.store(true);

// Or use stop_token (C++20)
#include <stop_token>

void process(std::stop_token stoken) {
    while (!stoken.stop_requested()) {
        // Do work
    }
}
```

### Go (Built-in Context)
```go
import (
    "context"
    "time"
)

// Context with timeout
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

// Pass through all operations
result, err := agent.Process(ctx, msg)

// Check for cancellation
func longOperation(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()  // Canceled or timed out
        default:
            // Continue work
        }
    }
}
```

**Changes**:
- Manual cancellation → `context.Context` (standard)
- No standard pattern → First parameter of async functions
- `std::stop_token` (C++20) → `context.Context` (Go 1.7+)

**Why this matters**: Context is pervasive in Go - thread it through all async operations

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

**Go**:
```go
import "github.com/agenkit/agenkit-go/patterns"

sequential := patterns.NewSequential([]agenkit.Agent{
    NewAgent1(),
    NewAgent2(),
    NewAgent3(),
})

result, err := sequential.Process(ctx, msg)
if err != nil {
    log.Fatalf("Sequential failed: %v", err)
}
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

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{
    NewAgentA(),
    NewAgentB(),
    NewAgentC(),
})

result, err := parallel.Process(ctx, msg)
if err != nil {
    log.Fatalf("Parallel failed: %v", err)
}
```

**Changes**:
- `std::vector<std::unique_ptr<Agent>>` → `[]agenkit.Agent` (slice)
- `.get()` on future → Check `err != nil`
- Move semantics → Copy or pointer passing

---

## Templates vs Interfaces

### C++ (Templates - Compile-time Polymorphism)
```cpp
// Generic function with template
template<typename T>
T process_with_agent(Agent& agent, const T& input) {
    // Process input with agent
    return result;
}

// Concept (C++20)
template<typename T>
concept AgentLike = requires(T a, const Message& msg) {
    { a.name() } -> std::convertible_to<std::string>;
    { a.process(msg) } -> std::same_as<std::future<Message>>;
};

template<AgentLike A>
Message process(A& agent, const Message& msg) {
    return agent.process(msg).get();
}
```

### Go (Interfaces - Runtime Polymorphism)
```go
// Interface (duck typing at compile time)
type Agent interface {
    Name() string
    Capabilities() []string
    Process(ctx context.Context, msg Message) (Message, error)
}

// Any type that implements these methods is an Agent (implicit)
type MyAgent struct { /* ... */ }

func (a *MyAgent) Name() string { /* ... */ }
func (a *MyAgent) Capabilities() []string { /* ... */ }
func (a *MyAgent) Process(ctx context.Context, msg Message) (Message, error) { /* ... */ }

// Use interface
func processWithAgent(agent Agent, msg Message) (Message, error) {
    return agent.Process(context.Background(), msg)
}
```

**Changes**:
- `template<typename T>` → Interface types (simpler but less flexible)
- Compile-time polymorphism → Runtime polymorphism (small overhead)
- Concepts → Interfaces (checked at compile time but simpler)
- Multiple template instantiations → Single interface implementation
- Complex type deduction → Explicit type declaration

**Trade-off**: Go is simpler but C++ templates are more powerful (zero overhead)

---

## Common Gotchas

### 1. No Destructors / RAII

**C++**: Automatic cleanup on scope exit
```cpp
void process() {
    std::unique_ptr<Resource> res(new Resource());
    // Use resource
} // Automatically cleaned up via destructor
```

**Go**: Use `defer` instead
```go
func process() {
    res := NewResource()
    defer res.Close()  // Explicitly schedule cleanup
    // Use resource
} // res.Close() called here
```

**Watch out**: Forgetting `defer` causes resource leaks (files, locks, connections)

### 2. Exported vs Unexported (Uppercase Matters)

**C++**: Use `public`/`private`/`protected`
```cpp
class MyAgent {
private:
    std::string secret_;  // Private field
public:
    std::string name_;    // Public field
};
```

**Go**: Use capitalization
```go
type MyAgent struct {
    secret string  // unexported (private)
    Name   string  // Exported (public)
}
```

**Watch out**: `name` vs `Name` changes visibility - and marshaling (JSON, etc.)

### 3. Nil Slices and Maps

**C++**: Containers are always valid (default-constructed)
```cpp
std::vector<int> vec;  // Empty but valid
vec.push_back(1);      // Works fine
```

**Go**: Nil slices work, but nil maps don't
```go
var slice []int  // nil slice
slice = append(slice, 1)  // Works! (allocates if needed)

var m map[string]int  // nil map
m["key"] = 1  // PANIC! Must initialize
m = make(map[string]int)  // Now works
```

**Watch out**: Always `make()` maps before writing

### 4. Slices vs Arrays

**C++**: Both types exist with different semantics
```cpp
std::array<int, 5> arr;   // Fixed size, stack allocated
std::vector<int> vec;     // Dynamic size, heap allocated
```

**Go**: Arrays fixed, slices dynamic (but slices are the default)
```go
arr := [5]int{}        // Array (rarely used)
slice := []int{}       // Slice (common)
slice = append(slice, 1)  // Dynamic growth
```

**Watch out**: Slices hold references to underlying arrays - mutations can surprise you

### 5. No Move Semantics

**C++**: Explicit move for efficiency
```cpp
std::vector<Message> messages = get_messages();
process(std::move(messages));  // Transfer ownership
```

**Go**: Copy small values, share large ones with pointers
```go
messages := getMessages()
process(messages)  // Copies slice header (cheap), shares underlying data

// Or use pointer for explicit sharing
processPtr(&messages)
```

**Watch out**: Slice/map copies are shallow (share data). Struct copies are deep.

---

## Testing

### C++ (Google Test)
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
    EXPECT_TRUE(result.content.find("Test") != std::string::npos);
}

TEST(MyAgentTest, HandleError) {
    MyAgent agent;
    Message invalid_msg{};

    EXPECT_THROW(agent.process(invalid_msg).get(), std::invalid_argument);
}
```

### Go (Built-in Testing)
```go
import "testing"

func TestMyAgent_Process(t *testing.T) {
    agent := NewMyAgent()
    msg := agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "Test",
    }

    result, err := agent.Process(context.Background(), msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if result.Role != agenkit.RoleAssistant {
        t.Errorf("got role %s, want %s", result.Role, agenkit.RoleAssistant)
    }
    if !strings.Contains(result.Content, "Test") {
        t.Errorf("result.Content = %q, want to contain 'Test'", result.Content)
    }
}

func TestMyAgent_HandleError(t *testing.T) {
    agent := NewMyAgent()
    invalid_msg := agenkit.Message{}

    _, err := agent.Process(context.Background(), invalid_msg)
    if err == nil {
        t.Fatal("expected error, got nil")
    }
}
```

**Changes**:
- `TEST()` macro → `func TestXxx(t *testing.T)`
- `EXPECT_EQ` → `if got != want { t.Errorf() }`
- `EXPECT_THROW` → Check `if err == nil { t.Fatal() }`
- Test fixtures → Table-driven tests (Go idiom)
- `benchmark::` → `func BenchmarkXxx(b *testing.B)`

---

## Performance Considerations

| Operation | C++ | Go | Notes |
|-----------|-----|----|-------|
| Agent creation | ~50ns | ~100ns | Go 2x slower (GC allocation) |
| Message processing | ~500ns | ~1μs | Go 2x slower (typical overhead) |
| Sequential (3 agents) | ~1.5μs | ~3μs | Consistent 2x overhead |
| Parallel (3 agents) | ~500ns | ~1μs | Go goroutines vs threads |
| Thread/goroutine spawn | ~5μs | ~1μs | Go 5x faster! |
| Thread-local access | ~5ns | ~50ns | Go has context overhead |

**When to migrate to Go**:
- Simpler memory management (no leaks, use-after-free)
- Faster development cycle (compilation, iteration)
- Better concurrency support (goroutines scale better)
- Simpler deployment (static binary, no C++ runtime)
- Don't need absolute maximum performance

**When to keep C++**:
- Need zero-overhead abstractions
- Real-time systems (deterministic performance)
- Fine-grained memory control required
- Existing large C++ codebase
- Performance-critical hot paths (game engines, HFT)

**Typical Performance**: Go is 10-20% slower in CPU-bound tasks, but 5x simpler code

---

## Migration Checklist

- [ ] Replace `class` with `struct` + interface
- [ ] Change `throw/catch` to `if err != nil` error checks
- [ ] Convert destructors to `defer` cleanup statements
- [ ] Replace `std::thread` with goroutines
- [ ] Replace `std::future` with channels
- [ ] Add `context.Context` parameter to async operations
- [ ] Remove `std::unique_ptr`/`std::shared_ptr` (use regular pointers)
- [ ] Replace templates with interfaces or code generation
- [ ] Convert `std::vector` to slices `[]T`
- [ ] Convert `std::map` to `map[K]V` (and initialize with `make()`)
- [ ] Replace `std::optional<T>` with `*T` or zero values
- [ ] Change `CamelCase` private fields to `camelCase`
- [ ] Change `CamelCase` public fields to `CamelCase` (capitalize)
- [ ] Update tests: Google Test → Go testing package
- [ ] Update build: CMake → `go build`

---

## Quick Start

```bash
# C++ project structure
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── agent.cpp
│   └── agent.hpp
└── tests/
    └── agent_test.cpp

# Go equivalent
agenkit-go/
├── go.mod
├── agent.go
└── agent_test.go
```

**Build/Run**:
```bash
# C++
mkdir build && cd build
cmake .. && make
./myagent

# Go
go build -o myagent
./myagent
# Or run directly
go run main.go
```

**Build Time Comparison**:
- C++ (full rebuild): 2-10 minutes (depends on template usage)
- C++ (incremental): 10-60 seconds
- Go (full rebuild): 5-30 seconds
- Go (incremental): 1-5 seconds

---

## Full Resources

- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Effective Go](https://go.dev/doc/effective_go) - Official Go style guide
- [Agenkit Examples](../examples/) - Side-by-side code samples in all languages

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
