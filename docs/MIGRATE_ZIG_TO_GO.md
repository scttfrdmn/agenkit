# Quick Reference: Zig → Go Migration

**For**: Zig developers migrating Agenkit code to Go
**Time**: 15 minute read
**Full Details**: See [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) and [Go Language Profile](LANGUAGE_PROFILE_GO.md)

---

## Key Differences at a Glance

| Aspect | Zig | Go |
|--------|-----|-----|
| **Memory** | Manual (explicit allocators) | GC (automatic) |
| **Errors** | Error unions `!Type` | `(result, error)` returns |
| **Concurrency** | std.Thread (OS threads) | Goroutines (green threads) |
| **Types** | Comptime generics | Interfaces (runtime) |
| **Cleanup** | defer/errdefer | defer only |
| **Performance** | No runtime overhead | GC pauses (<1ms) |
| **Deployment** | Single binary | Single binary |

---

## Message Creation

### Zig
```zig
const agenkit = @import("agenkit");

// With explicit allocator
pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    return agenkit.Message{
        .role = "user",
        .content = content,
    };
}

// Cleanup required
const msg = try createMessage(allocator);
defer allocator.free(msg.content);
```

### Go
```go
import "github.com/agenkit/agenkit-go"

// No allocator needed - GC handles memory
func createMessage() agenkit.Message {
    return agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "Hello!",
    }
}

// No cleanup needed - GC frees automatically
msg := createMessage()
// No defer needed!
```

**Changes**:
- Remove allocator parameters (GC handles memory)
- Remove `errdefer` cleanup (no manual memory management)
- Error unions `!Type` → `(result, error)` returns
- String slices `[]const u8` → Go strings `string`
- Struct literals: `.field = value` → `Field: value`

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
        // Manual cleanup
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

### Go
```go
import (
    "context"
    "fmt"
    "github.com/agenkit/agenkit-go"
)

type MyAgent struct {
    name string
}

// No init/deinit needed - GC handles lifecycle
func NewMyAgent() *MyAgent {
    return &MyAgent{
        name: "my-agent",
    }
}

func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return []string{"text", "analysis"}
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    content := fmt.Sprintf("Processed: %s", msg.Content)

    return agenkit.Message{
        Role:    agenkit.RoleAssistant,
        Content: content,
    }, nil
}
```

**Changes**:
- Remove `allocator` field (GC handles memory)
- Remove `init()`/`deinit()` methods (not needed in Go)
- Add `context.Context` parameter to async operations
- Error unions `!Type` → `(Type, error)` tuple returns
- `pub fn` → methods with receiver `func (a *MyAgent)`
- Return success with `nil` error instead of unwrapping error union

---

## Error Handling

### Zig
```zig
// Error unions - explicit error sets
const AgentError = error{
    InvalidMessage,
    ProcessingFailed,
    Timeout,
};

fn processMessage(allocator: std.mem.Allocator, msg: Message) AgentError!Message {
    if (msg.content.len == 0) {
        return error.InvalidMessage;
    }

    // Try - propagate error
    const result = try validateMessage(msg);
    return result;
}

// Catch error
const result = processMessage(allocator, msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or if-else pattern
if (processMessage(allocator, msg)) |success| {
    // Use success value
} else |err| {
    // Handle error
}
```

### Go
```go
import (
    "errors"
    "fmt"
)

// Define custom errors
var (
    ErrInvalidMessage   = errors.New("invalid message")
    ErrProcessingFailed = errors.New("processing failed")
    ErrTimeout          = errors.New("timeout")
)

func processMessage(msg Message) (Message, error) {
    if len(msg.Content) == 0 {
        return Message{}, ErrInvalidMessage
    }

    // Check error explicitly
    result, err := validateMessage(msg)
    if err != nil {
        return Message{}, fmt.Errorf("validate: %w", err)
    }

    return result, nil
}

// Check and handle error
result, err := processMessage(msg)
if err != nil {
    if errors.Is(err, ErrInvalidMessage) {
        fmt.Println("Invalid message")
        return err
    }
    return fmt.Errorf("process failed: %w", err)
}
// Use result
```

**Changes**:
- Error unions `!Type` → `(Type, error)` tuple
- `try` → explicit `if err != nil` checks
- `catch |err|` → `if err != nil` blocks
- Error sets → `var Err = errors.New()`
- `return error.Name` → `return Type{}, ErrName`
- Error wrapping: same concept, different syntax

---

## Concurrency

### Zig (OS Threads)
```zig
const std = @import("std");

// Spawn OS thread
const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, msg});
defer handle.join();

fn workerFunction(allocator: std.mem.Allocator, msg: Message) void {
    const result = agent.process(msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    // Use result
}

// Multiple threads with manual synchronization
var mutex = std.Thread.Mutex{};
var counter: usize = 0;

var threads: [3]std.Thread = undefined;
for (threads) |*t| {
    t.* = try std.Thread.spawn(.{}, incrementCounter, .{&mutex, &counter});
}
for (threads) |t| {
    t.join();
}

fn incrementCounter(mutex: *std.Thread.Mutex, counter: *usize) void {
    mutex.lock();
    defer mutex.unlock();
    counter.* += 1;
}
```

### Go (Goroutines)
```go
import (
    "context"
    "fmt"
    "sync"
)

// Spawn goroutine (lightweight green thread)
go func() {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    // Use result
}()

// Multiple goroutines with WaitGroup
var wg sync.WaitGroup
for i := 0; i < 3; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        _, _ = agent.Process(ctx, msg)
    }()
}
wg.Wait()

// Channels for communication (idiomatic Go)
results := make(chan Message, 3)

for i := 0; i < 3; i++ {
    go func() {
        result, err := agent.Process(ctx, msg)
        if err == nil {
            results <- result
        }
    }()
}

// Collect results
for i := 0; i < 3; i++ {
    result := <-results
    fmt.Println(result.Content)
}
close(results)
```

**Changes**:
- `std.Thread.spawn()` → `go func()` (much lighter weight)
- Manual joins → `sync.WaitGroup` or channels
- `std.Thread.Mutex` → `sync.Mutex` (similar API)
- Add `context.Context` for cancellation (idiomatic in Go)
- OS threads → goroutines (2KB vs 2MB stack, millions possible)
- No return values from goroutines → use channels

---

## Patterns

### Sequential

**Zig**:
```zig
var sequential = try patterns.Sequential.init(allocator, &[_]Agent{
    agent1,
    agent2,
    agent3,
});
defer sequential.deinit();

const result = try sequential.process(msg);
defer allocator.free(result.content);
```

**Go**:
```go
import "github.com/agenkit/agenkit-go/patterns"

sequential := patterns.NewSequential([]agenkit.Agent{
    agent1,
    agent2,
    agent3,
})

result, err := sequential.Process(ctx, msg)
if err != nil {
    return err
}
// No cleanup needed - GC handles it
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

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{
    agentA,
    agentB,
    agentC,
})

result, err := parallel.Process(ctx, msg)
if err != nil {
    return err
}
```

**Changes**:
- Remove allocator parameter
- Remove `defer deinit()` calls
- Add `context.Context` parameter
- Error unions → error returns
- Array literals: `&[_]Type{...}` → `[]Type{...}`

---

## Common Gotchas

### 1. Allocator Removal (Simplification)

**Zig**: Must thread allocators through entire call chain
```zig
fn createAgent(allocator: std.mem.Allocator, name: []const u8) !Agent {
    const owned_name = try allocator.dupe(u8, name);
    errdefer allocator.free(owned_name);
    // ...
}
```

**Go**: GC handles everything automatically
```go
func createAgent(name string) *Agent {
    // Strings are automatically managed
    return &Agent{name: name}
}
```

### 2. Error Union vs Tuple Returns

**Zig**: Single return type with `!`
```zig
fn process(msg: Message) !Message {
    return Message{...};  // Success
    // return error.Failed;  // Error
}

const result = try process(msg);  // Unwrap or propagate
```

**Go**: Explicit tuple `(result, error)`
```go
func process(msg Message) (Message, error) {
    return Message{...}, nil  // Success
    // return Message{}, errors.New("failed")  // Error
}

result, err := process(msg)  // Always check both
if err != nil {
    return err
}
```

### 3. Defer Differences

**Zig**: `defer` and `errdefer`
```zig
const file = try std.fs.cwd().openFile(path, .{});
defer file.close();  // Always runs

const buffer = try allocator.alloc(u8, 1024);
errdefer allocator.free(buffer);  // Only on error after this line
```

**Go**: `defer` only (no `errdefer`)
```go
file, err := os.Open(path)
if err != nil {
    return err
}
defer file.Close()  // Always runs

buffer := make([]byte, 1024)
// No cleanup needed - GC handles it!
```

### 4. Optionals vs Nil

**Zig**: Optional types with `?T`
```zig
var maybe_value: ?[]const u8 = null;
if (maybe_value) |value| {
    // value is []const u8 here
} else {
    // Handle null case
}
```

**Go**: Use pointers for optionals
```go
var maybeValue *string = nil

if maybeValue != nil {
    value := *maybeValue
    // Use value
} else {
    // Handle nil case
}
```

### 5. Comptime vs Runtime Interfaces

**Zig**: Compile-time polymorphism
```zig
fn process(comptime T: type, value: T) T {
    // Code generated at compile time for each T
    return value;
}
```

**Go**: Runtime interfaces
```go
type Processor interface {
    Process() interface{}
}

func process(p Processor) interface{} {
    // Dynamic dispatch at runtime
    return p.Process()
}
```

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
    try testing.expect(std.mem.indexOf(u8, result.content, "Processed") != null);
}

test "agent handles empty message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const empty_msg = Message{
        .role = "user",
        .content = "",
    };

    try testing.expectError(error.InvalidMessage, agent.process(empty_msg));
}
```

### Go
```go
import (
    "context"
    "strings"
    "testing"
)

func TestAgent_Process(t *testing.T) {
    // No allocator setup needed
    agent := NewMyAgent()

    msg := agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "Test",
    }

    result, err := agent.Process(context.Background(), msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    // No cleanup needed

    if result.Role != agenkit.RoleAssistant {
        t.Errorf("got role %s, want %s", result.Role, agenkit.RoleAssistant)
    }

    if !strings.Contains(result.Content, "Processed") {
        t.Errorf("result content missing 'Processed': %s", result.Content)
    }
}

func TestAgent_EmptyMessage(t *testing.T) {
    agent := NewMyAgent()

    emptyMsg := agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "",
    }

    _, err := agent.Process(context.Background(), emptyMsg)
    if err != ErrInvalidMessage {
        t.Errorf("got error %v, want %v", err, ErrInvalidMessage)
    }
}
```

**Changes**:
- Remove allocator setup/cleanup from tests
- Remove `defer` cleanup for test data
- `testing.expectEqualStrings()` → string comparison with `!=`
- `testing.expectError()` → error comparison with `!=`
- `test "name"` → `func TestName(t *testing.T)`
- Add `context.Background()` to Process calls

---

## Performance Considerations

| Operation | Zig | Go | Notes |
|-----------|-----|----|-------|
| Message creation | ~50ns | ~100ns | Go GC overhead minimal |
| Agent processing | ~500ns | ~1μs | Go slightly slower (GC) |
| Sequential (3 agents) | ~1.5μs | ~3μs | Predictable 2x difference |
| Parallel (3 agents) | ~5μs | ~1μs | Go goroutines much faster |
| Thread spawn | ~10μs | ~50ns | Goroutines 200x faster |
| Memory allocation | ~20ns | ~30ns | GC trades speed for convenience |

**When to migrate to Go**:
- Simpler deployment (no allocator management)
- Better concurrency (goroutines scale to millions)
- Faster development (no manual memory management)
- Ecosystem maturity (more libraries, tooling)
- Team familiarity (more developers know Go)

**When to keep Zig**:
- Embedded systems (no GC, predictable memory)
- Real-time systems (no GC pauses)
- Minimum memory footprint (manual control)
- Maximum performance (zero-cost abstractions)
- Learning systems programming (explicit everything)

---

## Migration Checklist

- [ ] Remove `allocator: std.mem.Allocator` fields from structs
- [ ] Remove `allocator` parameters from functions
- [ ] Remove `init()` and `deinit()` methods (GC handles lifecycle)
- [ ] Replace error unions `!Type` with `(Type, error)` returns
- [ ] Add `context.Context` parameter to async operations
- [ ] Remove `try` keyword, add explicit `if err != nil` checks
- [ ] Remove `errdefer` cleanup (use `defer` sparingly for files/locks)
- [ ] Replace `[]const u8` strings with Go `string` type
- [ ] Update tests: remove allocator setup, remove cleanup
- [ ] Replace `std.Thread` with goroutines (`go func()`)
- [ ] Convert error sets to `var Err = errors.New()` variables
- [ ] Remove comptime parameters (use interfaces for polymorphism)
- [ ] Update imports: `@import("agenkit")` → `import "github.com/agenkit/agenkit-go"`
- [ ] Replace optionals `?T` with pointers `*T` (or zero values)

---

## Quick Start

```bash
# Zig project structure
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig
└── tests/
    └── agent_test.zig

# Go equivalent
agenkit-go/
├── go.mod
├── main.go
├── agent.go
└── agent_test.go
```

**Build/Run**:
```bash
# Zig
zig build run

# Go
go run .
# Or build binary
go build -o myagent
./myagent
```

**Testing**:
```bash
# Zig
zig build test

# Go
go test ./...
# With coverage
go test -cover ./...
# With benchmarks
go test -bench=. ./...
```

---

## Memory Management Summary

### Zig: Explicit Allocators
```zig
// Must pass allocator everywhere
fn createData(allocator: std.mem.Allocator) ![]u8 {
    const data = try allocator.alloc(u8, 100);
    errdefer allocator.free(data);  // Clean up on error
    return data;
}

const data = try createData(allocator);
defer allocator.free(data);  // Manual cleanup
```

### Go: Automatic GC
```go
// No allocator needed - GC handles everything
func createData() []byte {
    data := make([]byte, 100)
    return data
}

data := createData()
// No cleanup needed - GC frees automatically
```

**Trade-off**: Go is simpler but less predictable. Zig gives total control but requires more discipline.

---

## Concurrency Model Summary

### Zig: OS Threads
```zig
// Heavyweight OS threads
const handle = try std.Thread.spawn(.{}, worker, .{data});
handle.join();  // Wait for completion

// Cost: ~10μs to spawn, 2MB stack per thread
// Limit: ~1000 threads practical
```

### Go: Goroutines
```go
// Lightweight green threads
go worker(data)

// Cost: ~50ns to spawn, 2KB stack per goroutine
// Limit: Millions of goroutines possible

// Wait with WaitGroup or channels
var wg sync.WaitGroup
wg.Add(1)
go func() {
    defer wg.Done()
    worker(data)
}()
wg.Wait()
```

**Trade-off**: Go's concurrency model is much more scalable. Zig gives explicit control but doesn't scale as well.

---

## Full Resources

- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Effective Go](https://go.dev/doc/effective_go) - Official Go style guide
- [Zig Learn](https://ziglearn.org/) - Comprehensive Zig guide
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
