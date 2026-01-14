# Quick Reference: C++ → Zig Migration

**For**: C++ developers migrating Agenkit code to Zig
**Time**: 15 minute read
**Full Details**: See [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) and [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md)

---

## Key Differences at a Glance

| Aspect | C++ | Zig |
|--------|-----|-----|
| **Typing** | Static, templates | Static, comptime |
| **Errors** | Exceptions or codes | Error unions (`!Type`) |
| **Concurrency** | `std::thread`, `std::async` | `std.Thread` (manual) |
| **Memory** | RAII + smart pointers | Manual + defer/errdefer |
| **Cleanup** | Implicit (destructors) | Explicit (defer) |
| **Deployment** | Single binary | Single binary |
| **Performance** | Zero-cost abstractions | Zero-cost, no hidden control flow |

---

## Message Creation

### C++
```cpp
#include <agenkit/message.hpp>

// Using designated initializers (C++20)
Message msg{
    .role = "user",
    .content = "Hello!",
    .metadata = {
        {"key", "value"},
        {"confidence", 0.95},
    },
};
```

### Zig
```zig
const agenkit = @import("agenkit");

// Struct initialization
var msg = agenkit.Message{
    .role = "user",
    .content = "Hello!",
};

// With owned content (requires allocator)
const content = try allocator.dupe(u8, "Hello!");
errdefer allocator.free(content);

var msg_owned = agenkit.Message{
    .role = "user",
    .content = content,
};
defer allocator.free(msg_owned.content);
```

**Changes**:
- Include → `@import()`
- Implicit memory → Explicit allocator parameter
- RAII cleanup → `defer` statement
- `std::map<>` → `std.StringHashMap()`
- Destructors → Manual `deinit()` methods

---

## Agent Implementation

### C++
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public Agent {
    std::string name_;
    Config config_;

public:
    explicit MyAgent(Config config)
        : config_(std::move(config)) {}

    ~MyAgent() override = default;  // Automatic cleanup

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

### Zig
```zig
const agenkit = @import("agenkit");
const std = @import("std");

const MyAgent = struct {
    allocator: std.mem.Allocator,
    config: Config,

    pub fn init(allocator: std.mem.Allocator, config: Config) !MyAgent {
        return MyAgent{
            .allocator = allocator,
            .config = config,
        };
    }

    pub fn deinit(self: *MyAgent) void {
        // Manual cleanup of owned resources
    }

    pub fn name(self: *const MyAgent) []const u8 {
        return "my-agent";
    }

    pub fn capabilities(self: *const MyAgent) []const []const u8 {
        const caps = &[_][]const u8{ "text", "analysis" };
        return caps;
    }

    pub fn process(self: *MyAgent, msg: agenkit.Message) !agenkit.Message {
        const content = try std.fmt.allocPrint(
            self.allocator,
            "Processed: {s}",
            .{msg.content}
        );

        return agenkit.Message{
            .role = "assistant",
            .content = content,
        };
    }
};
```

**Changes**:
- Class → Struct with methods
- Constructor → `init()` function
- Destructor → `deinit()` method (manual call)
- `virtual` methods → Function pointers (manual vtable)
- `std::future<>` → Synchronous or manual threading
- RAII → Explicit allocator + defer
- `std::string` → `[]const u8` (slice)
- `std::vector<>` → `[]` or `std.ArrayList()`

---

## Error Handling

### C++
```cpp
// Exception-based
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const std::runtime_error& e) {
    std::cerr << "Runtime error: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}

// Modern C++23: std::expected
std::expected<Message, AgentError> result = process_message(agent, msg);
if (result) {
    Message response = result.value();
} else {
    AgentError error = result.error();
}
```

### Zig
```zig
// Error union return type
const AgentError = error{
    InvalidMessage,
    ProcessingFailed,
    Timeout,
};

fn processMessage(agent: *Agent, msg: Message) AgentError!Message {
    if (msg.content.len == 0) {
        return error.InvalidMessage;
    }
    return try agent.process(msg);
}

// Try operator (propagates error)
const result = try processMessage(agent, msg);

// Catch operator (handles error)
const result = processMessage(agent, msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// If-else syntax for pattern matching
if (processMessage(agent, msg)) |success| {
    // Use success value
} else |err| {
    // Handle error
}
```

**Changes**:
- Exceptions → Error unions (`!Type`)
- `try/catch` → `try` operator or `catch` operator
- Implicit unwinding → Explicit error propagation
- `throw` → `return error.ErrorName`
- Stack unwinding → No hidden control flow
- `std::expected<T, E>` → `Error!Type`

---

## Memory Management

### C++
```cpp
// RAII: Automatic cleanup via destructors
class FileHandler {
    std::FILE* file_;
public:
    FileHandler(const char* path) : file_(std::fopen(path, "r")) {
        if (!file_) throw std::runtime_error("Failed to open");
    }
    ~FileHandler() {  // Automatic cleanup
        if (file_) std::fclose(file_);
    }
};

// Smart pointers
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();
std::shared_ptr<Agent> shared = std::make_shared<MyAgent>();

// Scope-based cleanup
{
    std::vector<Message> messages;
    messages.push_back(msg);
    // Vector automatically cleaned up at scope exit
}
```

### Zig
```zig
// defer: Explicit cleanup
fn processFile(allocator: std.mem.Allocator, path: []const u8) ![]const u8 {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();  // Runs at scope exit

    const buffer = try allocator.alloc(u8, 1024);
    errdefer allocator.free(buffer);  // Only on error path

    const bytes_read = try file.read(buffer);
    return buffer[0..bytes_read];
}

// Manual ownership
var agent = try MyAgent.init(allocator, config);
defer agent.deinit();

// Arena allocator (free all at once)
var arena = std.heap.ArenaAllocator.init(allocator);
defer arena.deinit();  // Frees everything
const temp_allocator = arena.allocator();

// All temporary allocations
const data = try temp_allocator.alloc(u8, 1024);
// No individual free needed - arena.deinit() handles it
```

**Changes**:
- Destructors → `deinit()` + `defer`
- RAII → Explicit defer/errdefer
- `std::unique_ptr<>` → Manual ownership tracking
- `std::shared_ptr<>` → Reference counting (manual or library)
- `std::vector<>` → `std.ArrayList()` or slices
- Implicit cleanup → Explicit `defer` statements
- No hidden allocations → Pass allocator explicitly

---

## Concurrency

### C++
```cpp
#include <thread>
#include <future>

// Spawn thread
std::thread t([&agent, msg]() {
    try {
        auto result = agent.process(msg).get();
        // Use result
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << '\n';
    }
});
t.join();

// Async with future
std::future<Message> future = std::async(std::launch::async, [&agent, msg]() {
    return agent.process(msg).get();
});
Message result = future.get();

// Multiple threads with promise
std::vector<std::future<Message>> futures;
for (const auto& agent : agents) {
    futures.push_back(std::async(std::launch::async, [&agent, msg]() {
        return agent.process(msg).get();
    }));
}

std::vector<Message> results;
for (auto& f : futures) {
    results.push_back(f.get());
}
```

### Zig
```zig
const std = @import("std");

// Spawn thread
const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, agent, msg});
handle.join();  // Wait for completion

fn workerFunction(allocator: std.mem.Allocator, agent: *Agent, msg: Message) void {
    const result = agent.process(msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    // Use result
}

// Multiple threads (manual coordination)
const thread_count = 3;
var threads: [thread_count]std.Thread = undefined;
var results: [thread_count]?Message = [_]?Message{null} ** thread_count;
var mutex = std.Thread.Mutex{};

for (threads, 0..) |*thread, i| {
    thread.* = try std.Thread.spawn(.{}, processWorker, .{
        allocator, &agents[i], msg, &results[i], &mutex
    });
}

for (threads) |thread| {
    thread.join();
}

fn processWorker(
    allocator: std.mem.Allocator,
    agent: *Agent,
    msg: Message,
    result_slot: *?Message,
    m: *std.Thread.Mutex,
) void {
    const result = agent.process(msg) catch return;

    m.lock();
    defer m.unlock();
    result_slot.* = result;
}
```

**Changes**:
- `std::thread` → `std.Thread`
- `std::async` → Manual thread spawning
- `std::future<T>` → Manual result storage + synchronization
- Lambda captures → Explicit parameter passing
- `std::promise<T>` → Manual mutex + condition variable
- Thread pools → Manual implementation or library
- Similar OS thread overhead for both

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

Message result = sequential.process(msg).get();
```

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var sequential = try patterns.Sequential.init(allocator, &[_]Agent{
    agent1,
    agent2,
    agent3,
});
defer sequential.deinit();

const result = try sequential.process(msg);
```

### Parallel

**C++**:
```cpp
auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
    std::make_unique<AgentC>(),
});

Message result = parallel.process(msg).get();
```

**Zig**:
```zig
var parallel = try patterns.Parallel.init(allocator, &[_]Agent{
    agent_a,
    agent_b,
    agent_c,
});
defer parallel.deinit();

const result = try parallel.process(msg);
```

**Changes**:
- `std::vector<std::unique_ptr<>>` → Array or `std.ArrayList()`
- Constructor → `init()` function
- Destructor → `deinit()` + defer
- `.get()` on future → Direct return (synchronous)

---

## Common Gotchas

### 1. Hidden Allocations

**C++**: Many standard library operations allocate implicitly
```cpp
std::string str = "Hello";  // May allocate
std::vector<int> vec = {1, 2, 3};  // Allocates
str += " World";  // May allocate
```

**Zig**: All allocations are explicit
```zig
// Must pass allocator
const str = try allocator.dupe(u8, "Hello");
defer allocator.free(str);

var list = std.ArrayList(i32).init(allocator);
defer list.deinit();

try list.append(1);
try list.append(2);
```

**Solution**: Accept that Zig requires more verbosity for memory safety and explicitness.

---

### 2. RAII vs defer

**C++**: Cleanup happens automatically
```cpp
{
    std::lock_guard<std::mutex> lock(mutex);
    // Mutex automatically unlocked at scope exit
}

{
    std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();
    // Agent automatically deleted at scope exit
}
```

**Zig**: Must explicitly defer cleanup
```zig
{
    mutex.lock();
    defer mutex.unlock();  // Must remember to defer
    // Mutex unlocked at scope exit
}

{
    var agent = try MyAgent.init(allocator, config);
    defer agent.deinit();  // Must remember to defer
    // Agent cleaned up at scope exit
}
```

**Solution**: Always pair allocation/acquisition with `defer` immediately. Use `errdefer` for error-path-only cleanup.

---

### 3. Templates vs comptime

**C++**: Template instantiation with type deduction
```cpp
template<typename T>
T process(T value) {
    return value;
}

// Automatic type deduction
auto result = process(42);
auto result2 = process("hello");
```

**Zig**: Comptime with explicit types
```zig
fn process(comptime T: type, value: T) T {
    return value;
}

// Must specify type explicitly
const result = process(i32, 42);
const result2 = process([]const u8, "hello");
```

**Solution**: Embrace comptime's explicitness. It's more verbose but eliminates many template error messages.

---

### 4. Exceptions vs Error Unions

**C++**: Can throw anywhere, implicit propagation
```cpp
void risky_operation() {
    throw std::runtime_error("Failed");  // Can throw from anywhere
}

void caller() {
    risky_operation();  // Exception propagates implicitly
}
```

**Zig**: Error unions make errors explicit in signatures
```zig
fn riskyOperation() !void {
    return error.Failed;  // Explicit in return type
}

fn caller() !void {
    try riskyOperation();  // Must explicitly propagate with 'try'
}

// Or handle explicitly
fn callerWithHandling() void {
    riskyOperation() catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
}
```

**Solution**: Update all function signatures to include error unions. Use `try` for propagation, `catch` for handling.

---

### 5. Virtual Functions vs Manual Vtables

**C++**: Polymorphism via virtual functions
```cpp
class Agent {
public:
    virtual ~Agent() = default;
    virtual std::string name() const = 0;
    virtual Message process(const Message& msg) = 0;
};

void use_agent(Agent& agent) {
    auto result = agent.process(msg);  // Dynamic dispatch
}
```

**Zig**: Manual vtable implementation
```zig
const Agent = struct {
    ptr: *anyopaque,
    nameFn: *const fn (*anyopaque) []const u8,
    processFn: *const fn (*anyopaque, Message) anyerror!Message,

    pub fn name(self: Agent) []const u8 {
        return self.nameFn(self.ptr);
    }

    pub fn process(self: Agent, msg: Message) !Message {
        return self.processFn(self.ptr, msg);
    }
};

// Create agent interface
fn createAgent(agent_ptr: anytype) Agent {
    const T = @TypeOf(agent_ptr);
    return Agent{
        .ptr = @ptrCast(*anyopaque, agent_ptr),
        .nameFn = &T.name,
        .processFn = &T.process,
    };
}

fn useAgent(agent: Agent, msg: Message) !Message {
    return try agent.process(msg);  // Manual dispatch
}
```

**Solution**: Use comptime generics when possible (monomorphization). For runtime polymorphism, implement manual vtables or use libraries.

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

### Zig
```zig
const std = @import("std");
const testing = std.testing;

test "agent processes message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator, config);
    defer agent.deinit();

    const msg = Message{
        .role = "user",
        .content = "Test",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    try testing.expectEqualStrings("assistant", result.role);
    try testing.expect(std.mem.indexOf(u8, result.content, "Processed") != null);
}

test "agent handles empty message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator, config);
    defer agent.deinit();

    const empty_msg = Message{
        .role = "user",
        .content = "",
    };

    try testing.expectError(error.InvalidMessage, agent.process(empty_msg));
}
```

**Changes**:
- `TEST(...)` → `test "..."`
- GoogleTest → `std.testing`
- `EXPECT_*` → `try testing.expect*`
- `EXPECT_THROW` → `try testing.expectError`
- Setup/teardown → Manual allocator init/deinit
- Automatic cleanup → Explicit defer statements

---

## Performance Considerations

| Operation | C++ | Zig | Notes |
|-----------|-----|-----|-------|
| Agent creation | ~50ns | ~50ns | Comparable |
| Message processing | ~500ns | ~500ns | Comparable |
| Sequential (3 agents) | ~1.5μs | ~1.5μs | Both zero-overhead |
| Parallel (3 agents) | ~500ns | ~5μs | Zig has more threading overhead |
| Compilation time | Slower (templates) | Faster | Zig compiles much faster |
| Binary size | Medium | Small | Zig produces smaller binaries |
| Memory safety | Manual + smart pointers | Manual + bounds checking | Zig has runtime checks in debug |

**When to use Zig**:
- Simpler systems programming (no C++ complexity)
- Embedded systems (small binary, no runtime)
- Learning systems programming (clearer mental model)
- Projects prioritizing maintainability over ecosystem
- When you want explicit control without C++ baggage

**When to keep C++**:
- Existing large C++ codebase
- Need mature ecosystem (Boost, Qt, etc.)
- Team expertise in C++
- C++ libraries required (no Zig equivalent)
- Async/await patterns (Zig async is experimental)

---

## Migration Checklist

- [ ] Replace includes with `@import()`
- [ ] Convert classes to structs with methods
- [ ] Replace destructors with `deinit()` + defer
- [ ] Change exceptions to error unions (`!Type`)
- [ ] Add explicit allocator parameters
- [ ] Convert `std::vector<>` to `std.ArrayList()` or slices
- [ ] Replace `std::string` with `[]const u8` or owned strings
- [ ] Change `std::future<>` to synchronous or manual threading
- [ ] Update virtual functions to comptime or vtables
- [ ] Convert templates to comptime generics
- [ ] Replace RAII with defer/errdefer
- [ ] Update tests: GoogleTest → `test` blocks
- [ ] Add explicit error handling (try/catch operators)
- [ ] Remove smart pointers, use manual ownership
- [ ] Update build system: CMake → build.zig

---

## Quick Start

```bash
# C++ project structure
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── agent.cpp
└── include/
    └── agent.hpp

# Zig equivalent
agenkit-zig/
├── build.zig
└── src/
    ├── main.zig
    └── agent.zig
```

**Build/Run**:
```bash
# C++
mkdir build && cd build
cmake ..
make
./myagent

# Zig
zig build
./zig-out/bin/myagent

# Zig run (no build step)
zig build run
```

**Test**:
```bash
# C++
make test
# or
ctest

# Zig
zig build test
```

---

## Code Size Comparison

**Example: Simple Agent**

| Language | Lines of Code | Binary Size | Compile Time |
|----------|--------------|-------------|--------------|
| **C++** | 150 lines | 2.5 MB | 8.0s |
| **Zig** | 120 lines | 1.2 MB | 2.5s |

**Why Zig is smaller**:
- No C++ standard library bloat
- No exception handling machinery
- No RTTI (unless explicitly enabled)
- Simpler language with fewer features

---

## Full Resources

- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [Zig Learn](https://ziglearn.org/) - Comprehensive Zig guide
- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/) - C++ best practices

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
