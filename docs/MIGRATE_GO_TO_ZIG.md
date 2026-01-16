# Quick Reference: Go → Zig Migration

**For**: Go developers migrating Agenkit code to Zig
**Time**: 15 minute read
**Full Details**: See [Go Language Profile](LANGUAGE_PROFILE_GO.md) and [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md)

---

## Key Differences at a Glance

| Aspect | Go | Zig |
|--------|----|----|
| **Typing** | Static, explicit | Static, explicit + comptime |
| **Errors** | `(result, error)` returns | Error unions `!Type` |
| **Concurrency** | Goroutines + channels | Manual threads (no async yet) |
| **Memory** | GC, automatic | Manual + allocators + defer |
| **Performance** | Fast (compiled) | Very fast (no runtime) |
| **Deployment** | Single binary | Single binary (smaller) |

---

## Message Creation

### Go
```go
import "github.com/agenkit/agenkit-go"

msg := agenkit.Message{
    Role:    agenkit.RoleUser,
    Content: "Hello!",
    Metadata: map[string]interface{}{
        "key": "value",
    },
}
```

### Zig
```zig
const agenkit = @import("agenkit");
const std = @import("std");

// Basic message (stack allocated)
var msg = agenkit.Message{
    .role = "user",
    .content = "Hello!",
};

// With owned content (requires allocator)
pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    var metadata = std.StringHashMap([]const u8).init(allocator);
    try metadata.put("key", "value");

    return agenkit.Message{
        .role = "user",
        .content = content,
        .metadata = metadata,
    };
}
```

**Changes**:
- Import: `import` → `@import` (comptime)
- Package: `agenkit-go` → `"agenkit"` module
- Struct literal: similar syntax
- Constants: `agenkit.RoleUser` → `"user"` string literal
- Type: `map[string]interface{}` → `std.StringHashMap(T)`
- **Must pass allocator** for heap allocations
- Cleanup: `defer allocator.free(content);`

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

### Zig
```zig
const std = @import("std");
const agenkit = @import("agenkit");

const MyAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8) !MyAgent {
        return MyAgent{
            .allocator = allocator,
            .name = name,
        };
    }

    pub fn deinit(self: *MyAgent) void {
        // Cleanup resources if needed
    }

    pub fn name(self: *const MyAgent) []const u8 {
        return self.name;
    }

    pub fn capabilities(self: *const MyAgent, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "text";
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
- Struct → `struct` with `pub fn` methods
- Methods: `func (a *MyAgent)` → `pub fn name(self: *MyAgent)`
- Constructor: `func New()` → `pub fn init()`
- Destructor: Add `pub fn deinit()` for cleanup
- `ctx context.Context` → removed (manual cancellation)
- `(result, error)` → `!Result` error union
- Return `error.Name` instead of `nil` error
- **Every allocating function takes `allocator: std.mem.Allocator`**

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

### Zig
```zig
// Using try (propagates errors)
const result = try agent.process(msg);
// Use result

// Or catch for specific handling
const result = agent.process(msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or if for optional handling
if (agent.process(msg)) |result| {
    // Use result
} else |err| {
    std.debug.print("Error: {}\n", .{err});
    return err;
}
```

**Changes**:
- `if err != nil` → `try` or `catch`
- Error wrapping: `fmt.Errorf(..., %w, err)` → return explicit error
- Error types: Must define explicit error set
- No tuple unpacking needed

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

### Zig (Manual Threading)
```zig
// Spawn thread
const thread = try std.Thread.spawn(.{}, workerFn, .{allocator, agent, msg});
thread.join();  // Wait for completion

fn workerFn(allocator: std.mem.Allocator, agent: *MyAgent, msg: agenkit.Message) void {
    const result = agent.process(msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    defer allocator.free(result.content);
    // Use result
}

// Multiple threads (manual management)
var threads = std.ArrayList(std.Thread).init(allocator);
defer threads.deinit();

for (agents) |agent| {
    const thread = try std.Thread.spawn(.{}, workerFn, .{allocator, agent, msg});
    try threads.append(thread);
}

// Wait for all
for (threads.items) |thread| {
    thread.join();
}
```

**Changes**:
- `go func()` → `std.Thread.spawn(.{}, fn, .{args})`
- `sync.WaitGroup` → Manual thread collection + `.join()`
- `context.Context` → manual cancellation flag
- Channels → `std.ArrayList` + `std.Thread.Mutex`
- **No async/await** in Zig (yet)
- Heavier than goroutines (OS threads)

---

## Patterns

### Sequential

**Go**:
```go
sequential := patterns.NewSequential([]agenkit.Agent{agent1, agent2})
result, err := sequential.Process(ctx, msg)
```

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var sequential = try patterns.Sequential.init(allocator, &[_]*MyAgent{
    &agent1,
    &agent2,
});
defer sequential.deinit();

const result = try sequential.process(msg);
defer allocator.free(result.content);
```

### Parallel

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{agentA, agentB})
result, err := parallel.Process(ctx, msg)
```

**Zig**:
```zig
var parallel = try patterns.Parallel.init(allocator, &[_]*MyAgent{
    &agent_a,
    &agent_b,
});
defer parallel.deinit();

const result = try parallel.process(msg);
defer allocator.free(result.content);
```

---

## Common Gotchas

### 1. Explicit Allocators

**Go**: GC handles allocations automatically
**Zig**: Must pass allocator to every allocating function

```go
// Go - automatic
msg := agenkit.Message{Content: "Hello"}
// Cleaned up by GC
```

```zig
// Zig - explicit allocator
pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello");
    errdefer allocator.free(content);  // Cleanup on error

    return agenkit.Message{
        .content = content,
    };
}

// Caller must cleanup
const msg = try createMessage(allocator);
defer allocator.free(msg.content);
```

### 2. No Hidden Control Flow

**Go**: `defer` for cleanup, GC in background
**Zig**: `defer` for cleanup, no hidden allocations

```go
// Go - some allocations hidden
str := fmt.Sprintf("Result: %d", value)
// String allocated automatically
```

```zig
// Zig - allocations explicit
const str = try std.fmt.allocPrint(
    allocator,
    "Result: {}",
    .{value}
);
defer allocator.free(str);  // Must free
```

### 3. Error Union vs Tuple

**Go**: Return tuple `(result, error)`
**Zig**: Return error union `!Result`

```go
// Go
func process(msg Message) (Message, error) {
    if invalid {
        return Message{}, errors.New("invalid")
    }
    return result, nil
}
```

```zig
// Zig
fn process(msg: Message) !Message {
    if (invalid) {
        return error.Invalid;
    }
    return result;
}
```

### 4. String Types

**Go**: `string` type
**Zig**: `[]const u8` for string slices

```go
// Go
func getName() string {
    return "Agent"
}
```

```zig
// Zig - string literal (comptime known)
fn getName() []const u8 {
    return "Agent";
}

// Or owned string (allocated)
fn getName(allocator: std.mem.Allocator) ![]u8 {
    return try allocator.dupe(u8, "Agent");
}
```

### 5. Nil vs null vs Optional

**Go**: `nil` for zero values
**Zig**: `null` for `?T` optional types

```go
// Go
var msg *Message = nil
if msg != nil {
    // Use msg
}
```

```zig
// Zig
var msg: ?*Message = null;
if (msg) |m| {
    // Use m
}

// Or with orelse
const m = msg orelse return error.NoMessage;
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

### Zig
```zig
const std = @import("std");
const testing = std.testing;

test "agent processes message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator, "test");
    defer agent.deinit();

    const msg = agenkit.Message{
        .role = "user",
        .content = "Test",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    try testing.expectEqualStrings("assistant", result.role);
    try testing.expect(std.mem.indexOf(u8, result.content, "Expected") != null);
}
```

**Changes**:
- `func TestXxx(t *testing.T)` → `test "description"`
- `t.Fatalf/t.Errorf` → `try testing.expect*` functions
- Must manage allocator in tests
- Use `testing.allocator` for leak detection

---

## Performance Considerations

| Operation | Go | Zig | Notes |
|-----------|----|----|-------|
| Agent creation | ~100ns | ~50ns | Zig 2x faster |
| Message processing | ~1μs | ~500ns | Zig 2x faster |
| Sequential (3 agents) | ~3μs | ~1.5μs | Zig 2x faster |
| Parallel (3 agents) | ~1μs | ~5μs | OS threads vs goroutines |

**When to use Zig**:
- Maximum performance + control
- Embedded systems / bare metal
- Small binary size critical
- No runtime dependencies acceptable
- Explicit memory management preferred
- WASM with minimal overhead

**When to keep Go**:
- Faster development (no manual memory)
- Goroutines for concurrency (simpler)
- Larger ecosystem
- GC acceptable
- Team expertise in Go

---

## Migration Checklist

- [ ] Replace `struct` with `struct` + `pub fn` methods
- [ ] Convert `(result, error)` to `!Result` error unions
- [ ] Change goroutines to `std.Thread.spawn`
- [ ] Remove `context.Context` parameter
- [ ] Update imports: `import` → `@import`
- [ ] Add `allocator: std.mem.Allocator` to all allocating functions
- [ ] Add `defer` for resource cleanup
- [ ] Use `errdefer` for error path cleanup
- [ ] Convert `nil` to `null` and use `?T` optionals
- [ ] Update error handling: `if err != nil` → `try` or `catch`
- [ ] Change tests: `*testing.T` → `test` blocks
- [ ] Add `init()` and `deinit()` methods for resources
- [ ] Configure `build.zig` build system
- [ ] Handle string types: `string` → `[]const u8`

---

## Quick Start

```bash
# Go project structure
agenkit-go/
├── go.mod
├── main.go
└── agent.go

# Zig equivalent
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig
└── zig-out/  # Build output
```

**Build/Run**:
```bash
# Go
go build -o myagent
./myagent

# Zig
zig build
./zig-out/bin/myagent

# Or run directly
zig build run
```

**Project Setup**:
```bash
# Initialize Zig project
zig init-exe

# Edit build.zig to add dependencies
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "myagent",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    // Add agenkit dependency
    const agenkit = b.dependency("agenkit", .{
        .target = target,
        .optimize = optimize,
    });
    exe.addModule("agenkit", agenkit.module("agenkit"));

    b.installArtifact(exe);
}
```

---

## Full Resources

- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms
- [Zig Learn](https://ziglearn.org/) - Comprehensive Zig guide
- [Agenkit Zig Examples](../agenkit-zig/examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
