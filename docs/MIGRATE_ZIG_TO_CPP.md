# Quick Reference: Zig → C++ Migration

**For**: Zig developers migrating Agenkit code to C++
**Time**: 15 minute read
**Full Details**: See [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) and [C++ Language Profile](LANGUAGE_PROFILE_CPP.md)

---

## Key Differences at a Glance

| Aspect | Zig | C++ |
|--------|-----|-----|
| **Typing** | Static, comptime | Static, templates |
| **Errors** | Error unions (`!Type`) | Exceptions or `std::expected` |
| **Concurrency** | std.Thread (manual) | std::thread + std::async |
| **Memory** | Explicit allocators | RAII + smart pointers |
| **Performance** | Zero-cost, no runtime | Zero-cost, no GC |
| **Ecosystem** | Small, growing | Mature, extensive |

**Why Migrate**: Larger ecosystem, mature tooling, legacy C++ integration, broader platform support, extensive third-party libraries.

---

## Message Creation

### Zig
```zig
const agenkit = @import("agenkit");

// Basic message
var msg = agenkit.Message{
    .role = "user",
    .content = "Hello!",
};

// With allocator (owned strings)
pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    return agenkit.Message{
        .role = "user",
        .content = content,
    };
}

// Manual cleanup
defer allocator.free(msg.content);
```

### C++
```cpp
#include <agenkit/message.hpp>

// Basic message
Message msg{
    .role = "user",
    .content = "Hello!",
};

// With owned strings (automatic memory management)
Message createMessage() {
    return Message{
        .role = "user",
        .content = std::string("Hello!"),  // Automatic allocation
    };
}

// Automatic cleanup via RAII (no defer needed)
```

**Changes**:
- Explicit allocators → RAII (manual → semi-automatic)
- `[]const u8` → `std::string` (slices → owned strings)
- `defer allocator.free()` → automatic destructor
- `errdefer` → exception unwinding or smart pointers
- No allocator parameters needed in most cases

---

## Agent Implementation

### Zig
```zig
const Agent = @import("agenkit").Agent;

const MyAgent = struct {
    allocator: std.mem.Allocator,
    name_str: []const u8,

    pub fn init(allocator: std.mem.Allocator) !MyAgent {
        return MyAgent{
            .allocator = allocator,
            .name_str = "my-agent",
        };
    }

    pub fn deinit(self: *MyAgent) void {
        // Cleanup resources
    }

    pub fn name(self: *const MyAgent) []const u8 {
        return self.name_str;
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

### C++
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public Agent {
    std::string name_;

public:
    MyAgent() : name_("my-agent") {}

    // No explicit deinit - destructor handles cleanup automatically
    ~MyAgent() override = default;

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"text", "analysis"};
    }

    std::future<Message> process(const Message& msg) override {
        return std::async(std::launch::async, [msg]() {
            return Message{
                .role = "assistant",
                .content = "Processed: " + msg.content,
            };
        });
    }
};
```

**Changes**:
- Struct → Class with inheritance
- `init(allocator)` → Constructor (no allocator parameter)
- `deinit()` → Destructor `~MyAgent()` (automatic)
- `pub fn` → Member functions with `override`
- Manual allocator → RAII (std::string manages itself)
- `!Type` error union → `std::future<T>` or exceptions
- `[]const u8` → `std::string`
- `[]const []const u8` → `std::vector<std::string>`

---

## Error Handling

### Zig (Error Unions)
```zig
const AgentError = error{
    InvalidMessage,
    ProcessingFailed,
    Timeout,
};

fn processMessage(allocator: std.mem.Allocator, msg: Message) AgentError!Message {
    if (msg.content.len == 0) {
        return error.InvalidMessage;
    }

    // Propagate error with 'try'
    const result = try validateMessage(msg);
    return result;
}

// Catch and handle
const result = processMessage(allocator, msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or use if to check success
if (processMessage(allocator, msg)) |success| {
    // Use success value
} else |err| {
    // Handle error
}
```

### C++ (Exceptions)
```cpp
enum class AgentError {
    InvalidMessage,
    ProcessingFailed,
    Timeout,
};

Message processMessage(const Message& msg) {
    if (msg.content.empty()) {
        throw std::invalid_argument("Invalid message");
    }

    // Exceptions propagate automatically
    Message result = validateMessage(msg);
    return result;
}

// Catch and handle
try {
    Message result = processMessage(msg);
    // Use result
} catch (const std::invalid_argument& e) {
    std::cerr << "Invalid message: " << e.what() << '\n';
    throw;  // Re-throw if needed
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}
```

### C++ (std::expected - Modern Alternative)
```cpp
#include <expected>  // C++23

std::expected<Message, AgentError> processMessage(const Message& msg) {
    if (msg.content.empty()) {
        return std::unexpected(AgentError::InvalidMessage);
    }

    auto result = validateMessage(msg);
    if (!result) {
        return std::unexpected(result.error());
    }

    return result.value();
}

// Usage
auto result = processMessage(msg);
if (result) {
    // Success
    Message response = result.value();
} else {
    // Error
    AgentError error = result.error();
}
```

**Changes**:
- `error.Name` → `throw std::exception` or `std::unexpected(Error::Name)`
- `try` → automatic propagation (exceptions) or explicit checks (`std::expected`)
- `catch |err|` → `catch (const std::exception& e)`
- Error unions → Exceptions (implicit) or `std::expected` (explicit)
- No allocator parameter for error handling
- Both explicit and implicit error patterns available

---

## Memory Management

### Zig (Explicit Allocators)
```zig
// Pass allocator explicitly
fn createData(allocator: std.mem.Allocator) ![]u8 {
    const buffer = try allocator.alloc(u8, 1024);
    errdefer allocator.free(buffer);

    // Use buffer
    return buffer;
}

// Manual cleanup with defer
const data = try createData(allocator);
defer allocator.free(data);

// Arena for batch cleanup
var arena = std.heap.ArenaAllocator.init(allocator);
defer arena.deinit();  // Frees everything at once
const temp_allocator = arena.allocator();
```

### C++ (RAII + Smart Pointers)
```cpp
// Automatic memory management with RAII
std::vector<uint8_t> createData() {
    std::vector<uint8_t> buffer(1024);
    // Use buffer
    return buffer;  // Move semantics, no copy
}

// Automatic cleanup (no defer needed)
auto data = createData();
// Destructor frees memory automatically at scope exit

// Smart pointers for dynamic allocation
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();
// Automatic cleanup when unique_ptr goes out of scope

// Shared ownership
std::shared_ptr<Agent> shared = std::make_shared<MyAgent>();
std::shared_ptr<Agent> copy = shared;  // Reference counted
// Cleanup when last reference is destroyed

// Arena-like pattern with allocator
std::pmr::monotonic_buffer_resource pool;
std::pmr::vector<uint8_t> buffer(&pool);
// All allocations from pool freed when pool destroyed
```

**Changes**:
- `allocator.alloc()` → `std::vector` or `new` (prefer vector)
- `defer allocator.free()` → automatic destructors (RAII)
- `errdefer` → exception unwinding or smart pointer cleanup
- Explicit allocators → RAII + smart pointers
- Manual cleanup → automatic cleanup
- Arena allocator → `std::pmr` allocators (optional)
- `try allocator.alloc()` → constructors that can't fail (vector) or exceptions

---

## Concurrency

### Zig (std.Thread)
```zig
const std = @import("std");

// Spawn OS thread
const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, data});
handle.join();  // Wait for completion

fn workerFunction(allocator: std.mem.Allocator, data: []const u8) void {
    // Process data
    std.debug.print("Processing: {s}\n", .{data});
}

// Mutex for synchronization
var mutex = std.Thread.Mutex{};

fn safeIncrement(counter: *usize) void {
    mutex.lock();
    defer mutex.unlock();
    counter.* += 1;
}

// Manual thread management
const threads = try allocator.alloc(std.Thread, 4);
defer allocator.free(threads);

for (threads) |*t| {
    t.* = try std.Thread.spawn(.{}, worker, .{});
}

for (threads) |t| {
    t.join();
}
```

### C++ (std::thread + std::async)
```cpp
#include <thread>
#include <future>

// Spawn OS thread
std::thread t([](const std::vector<uint8_t>& data) {
    // Process data
    std::cout << "Processing data\n";
}, data);
t.join();  // Wait for completion

// std::async for future-based results
auto future = std::async(std::launch::async, [](const Message& msg) {
    return processMessage(msg);
}, msg);
Message result = future.get();  // Blocks until ready

// Mutex for synchronization
std::mutex mutex;

void safeIncrement(std::atomic<size_t>& counter) {
    std::lock_guard<std::mutex> lock(mutex);
    ++counter;
}

// Multiple threads
std::vector<std::thread> threads;
for (int i = 0; i < 4; ++i) {
    threads.emplace_back(worker);
}

for (auto& t : threads) {
    t.join();
}

// Or with futures
std::vector<std::future<Message>> futures;
for (const auto& msg : messages) {
    futures.push_back(std::async(std::launch::async, process, msg));
}

for (auto& fut : futures) {
    Message result = fut.get();
}
```

**Changes**:
- `std.Thread.spawn()` → `std::thread` or `std::async`
- `handle.join()` → `t.join()` or `future.get()`
- Lambda syntax: `.{arg1, arg2}` → `[capture](params) {}`
- `std.Thread.Mutex` → `std::mutex` + `std::lock_guard`
- `defer mutex.unlock()` → RAII lock guards
- Manual thread array → `std::vector<std::thread>`
- Same OS thread model (both use OS threads)
- `std::future` for return values (Zig threads don't return)

---

## Patterns

### Sequential

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
defer allocator.free(result.content);
```

**C++**:
```cpp
#include <agenkit/patterns.hpp>

auto sequential = Sequential(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<Agent1>(),
    std::make_unique<Agent2>(),
    std::make_unique<Agent3>(),
});

// No defer needed - RAII handles cleanup
auto result = sequential.process(msg).get();
```

### Parallel

**Zig**:
```zig
var parallel = try patterns.Parallel.init(allocator, &[_]Agent{
    agent_a,
    agent_b,
    agent_c,
});
defer parallel.deinit();

const result = try parallel.process(msg);
defer allocator.free(result.content);
```

**C++**:
```cpp
auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
    std::make_unique<AgentC>(),
});

auto result = parallel.process(msg).get();
// Automatic cleanup via RAII
```

**Changes**:
- `&[_]Agent{...}` → `std::vector<std::unique_ptr<Agent>>{...}`
- `defer pattern.deinit()` → automatic destructor
- `try pattern.process()` → `pattern.process().get()` (future)
- Explicit allocator → implicit memory management
- Manual cleanup → RAII

---

## Optional Types

### Zig (?T)
```zig
const std = @import("std");

// Optional type
const optional: ?i32 = null;

// Check and unwrap
if (optional) |value| {
    std.debug.print("Value: {}\n", .{value});
} else {
    std.debug.print("No value\n", .{});
}

// Optional in struct
const Config = struct {
    timeout: ?u64 = null,
    retries: ?u32 = null,
};

const config = Config{
    .timeout = 5000,
    .retries = null,
};

// Use with orelse
const timeout = config.timeout orelse 1000;  // Default value
```

### C++ (std::optional)
```cpp
#include <optional>

// Optional type
std::optional<int> optional = std::nullopt;

// Check and unwrap
if (optional) {
    std::cout << "Value: " << *optional << '\n';
} else {
    std::cout << "No value\n";
}

// Or use has_value()
if (optional.has_value()) {
    std::cout << "Value: " << optional.value() << '\n';
}

// Optional in struct
struct Config {
    std::optional<uint64_t> timeout;
    std::optional<uint32_t> retries;
};

Config config{
    .timeout = 5000,
    .retries = std::nullopt,
};

// Use with value_or
uint64_t timeout = config.timeout.value_or(1000);  // Default value
```

**Changes**:
- `?T` → `std::optional<T>`
- `null` → `std::nullopt`
- `if (opt) |value|` → `if (opt)` then `*opt` or `opt.value()`
- `opt orelse default` → `opt.value_or(default)`
- Similar semantics, different syntax

---

## Comptime vs Templates

### Zig (comptime)
```zig
// Generic function with comptime
fn process(comptime T: type, value: T) T {
    return value;
}

// Comptime assertions
comptime {
    if (@sizeOf(Message) > 1024) {
        @compileError("Message too large");
    }
}

// Generic container
fn ArrayList(comptime T: type) type {
    return struct {
        items: []T,
        allocator: std.mem.Allocator,

        pub fn init(allocator: std.mem.Allocator) ArrayList(T) {
            return ArrayList(T){
                .items = &[_]T{},
                .allocator = allocator,
            };
        }
    };
}

const list = ArrayList(i32).init(allocator);
```

### C++ (Templates)
```cpp
// Generic function with template
template<typename T>
T process(T value) {
    return value;
}

// Static assertions
static_assert(sizeof(Message) <= 1024, "Message too large");

// Generic container
template<typename T>
class ArrayList {
    std::vector<T> items;

public:
    ArrayList() = default;

    void append(T item) {
        items.push_back(std::move(item));
    }

    size_t size() const {
        return items.size();
    }
};

ArrayList<int> list;
```

**Changes**:
- `comptime T: type` → `template<typename T>` or `template<class T>`
- `@compileError()` → `static_assert(condition, "message")`
- `comptime {}` blocks → `static_assert()` or `constexpr`
- Function returns type → Template class definition
- Explicit allocator → Standard library containers handle it
- More verbose template syntax in C++

---

## Common Gotchas

### 1. Allocator Threading

**Zig**: Explicit allocator makes threading clear
```zig
// Each thread needs thread-safe allocator or separate allocator
fn worker(allocator: std.mem.Allocator) void {
    const data = allocator.alloc(u8, 1024) catch return;
    defer allocator.free(data);
    // Allocator must be thread-safe
}
```

**C++**: RAII handles it, but watch for shared state
```cpp
// Standard containers are NOT thread-safe for modification
void worker() {
    std::vector<uint8_t> data(1024);
    // Thread-local, no issues
}

// Shared containers need synchronization
std::vector<int> shared;  // Needs mutex for thread safety
std::mutex mutex;

void worker() {
    std::lock_guard<std::mutex> lock(mutex);
    shared.push_back(42);  // Now thread-safe
}
```

### 2. String Ownership

**Zig**: Explicit with slices
```zig
// []const u8 is a view (no ownership)
fn processString(s: []const u8) void {
    // Can't free s, don't own it
}

// Caller owns the memory
const owned = try allocator.dupe(u8, "Hello");
defer allocator.free(owned);
```

**C++**: std::string manages itself
```cpp
// std::string owns its memory
void processString(const std::string& s) {
    // Reference, no copy
}

void processString(std::string s) {
    // Copy (or move if passed with std::move)
    // Automatic cleanup
}

// Ownership is automatic
std::string owned = "Hello";
// No manual cleanup needed
```

**Pitfall**: In C++, forgetting `const&` on string parameters causes unnecessary copies.

### 3. Error Handling Philosophy

**Zig**: Errors are values (explicit)
```zig
// Must handle errors explicitly
const result = operation() catch |err| {
    return err;  // Can't ignore
};

// Or with try (propagates error)
const result = try operation();
```

**C++**: Two patterns (choose one consistently)
```cpp
// Exceptions (implicit propagation)
try {
    Message result = operation();  // May throw
} catch (const std::exception& e) {
    // Handle
}

// std::expected (explicit like Zig)
auto result = operation();  // Returns std::expected
if (!result) {
    // Handle error
    AgentError err = result.error();
}
```

**Pitfall**: Mixing exception and explicit error patterns in same codebase leads to confusion. Agenkit C++ prefers `std::expected` for consistency with Zig's explicit approach.

### 4. defer vs RAII

**Zig**: Explicit defer statements
```zig
const file = try std.fs.cwd().openFile("data.txt", .{});
defer file.close();  // Explicit cleanup

const buffer = try allocator.alloc(u8, 1024);
defer allocator.free(buffer);  // Explicit cleanup

// Order: Last defer executes first (stack order)
```

**C++**: RAII automatic cleanup
```cpp
// Automatic cleanup via destructors
{
    std::ifstream file("data.txt");
    std::vector<uint8_t> buffer(1024);

    // Use file and buffer

}  // Destructors called automatically in reverse order
```

**Pitfall**: In C++, relying on manual cleanup (like C-style malloc/free) defeats RAII. Always use RAII types (std::vector, std::unique_ptr, etc.) instead of raw new/delete.

### 5. Slice vs Pointer Arithmetic

**Zig**: Slices carry length
```zig
fn sum(numbers: []const i32) i32 {
    var total: i32 = 0;
    for (numbers) |n| {
        total += n;
    }
    return total;
}

// Bounds checked in Debug mode
const value = numbers[5];  // Runtime panic if out of bounds
```

**C++**: Raw pointers lose length, prefer containers
```cpp
// BAD: Raw pointer (no length)
int sum(const int* numbers, size_t len) {
    int total = 0;
    for (size_t i = 0; i < len; ++i) {
        total += numbers[i];  // No bounds checking!
    }
    return total;
}

// GOOD: Use span (C++20) or vector
int sum(std::span<const int> numbers) {
    int total = 0;
    for (int n : numbers) {
        total += n;
    }
    return total;
}

// Or vector
int sum(const std::vector<int>& numbers) {
    return std::accumulate(numbers.begin(), numbers.end(), 0);
}
```

**Pitfall**: Raw pointers in C++ are dangerous. Use `std::span` (view) or `std::vector` (owned) instead.

---

## Performance Considerations

| Operation | Zig | C++ | Notes |
|-----------|-----|-----|-------|
| Message creation | ~50ns | ~50ns | Comparable (both zero-cost) |
| Agent process (mock) | ~500ns | ~500ns | Same performance tier |
| Sequential (3 agents) | ~1.5μs | ~1.5μs | Identical pattern |
| Parallel (3 agents) | ~5μs | ~500ns | C++ std::async optimized |
| Thread spawn | ~10μs | ~5μs | C++ slightly faster |
| String allocation | Explicit | RAII overhead | Zig slightly more control |

**When to use C++**:
- Legacy C++ codebase integration
- Need extensive third-party libraries (Boost, Qt, etc.)
- Require mature tooling (debuggers, profilers)
- Platform support (Windows, embedded, console)
- Team familiarity (large C++ developer pool)

**When to keep Zig**:
- Greenfield project with no legacy code
- Value explicit control over implicit magic
- Want simpler, more predictable language
- Prefer faster compilation times
- Enjoy comptime over templates

---

## Testing

### Zig
```zig
const std = @import("std");
const testing = std.testing;

test "agent processes message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const msg = Message{
        .role = "user",
        .content = "Test",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    try testing.expectEqualStrings("assistant", result.role);
}

test "agent handles empty message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const msg = Message{
        .role = "user",
        .content = "",
    };

    try testing.expectError(error.InvalidMessage, agent.process(msg));
}
```

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
    // No manual cleanup needed (RAII)
}

TEST(MyAgentTest, HandleEmptyMessage) {
    MyAgent agent;
    Message msg{
        .role = "user",
        .content = "",
    };

    EXPECT_THROW(agent.process(msg).get(), std::invalid_argument);
    // Or with std::expected:
    // auto result = agent.process(msg);
    // EXPECT_FALSE(result.has_value());
}
```

**Changes**:
- `test "name"` → `TEST(SuiteName, TestName)`
- Manual GPA setup → automatic memory management
- `defer` cleanup → RAII automatic cleanup
- `try testing.expectEqual` → `EXPECT_EQ` macros
- `try testing.expectError` → `EXPECT_THROW`
- No allocator needed in tests

---

## Migration Checklist

- [ ] Replace explicit allocators with RAII (std::string, std::vector)
- [ ] Convert `!Type` error unions to exceptions or `std::expected`
- [ ] Change `defer` statements to RAII resource management
- [ ] Replace `errdefer` with exception unwinding or smart pointers
- [ ] Update `std.Thread` to `std::thread` or `std::async`
- [ ] Convert `?T` optional to `std::optional<T>`
- [ ] Replace `comptime` with templates or `constexpr`
- [ ] Change slices `[]T` to `std::span<T>` or `std::vector<T>`
- [ ] Update tests from Zig test to Google Test
- [ ] Remove allocator parameters from functions
- [ ] Replace `init()/deinit()` with constructors/destructors
- [ ] Convert string handling from `[]const u8` to `std::string`
- [ ] Update build system: `build.zig` → `CMakeLists.txt`

---

## Quick Start

```bash
# Zig project structure
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig

# C++ equivalent
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── agent.cpp
├── include/
│   └── agent.hpp
```

**Build/Run**:
```bash
# Zig
zig build
./zig-out/bin/myagent

# C++
mkdir build && cd build
cmake ..
make
./myagent
```

---

## Full Resources

- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/) - Modern C++ best practices
- [Zig Learn](https://ziglearn.org/) - Zig fundamentals

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
