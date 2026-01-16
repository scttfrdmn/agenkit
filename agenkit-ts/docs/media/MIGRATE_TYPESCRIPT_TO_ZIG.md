# Quick Reference: TypeScript → Zig Migration

**For**: TypeScript developers migrating Agenkit code to Zig
**Time**: 15 minute read
**Full Details**: See [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) and [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md)

---

## Key Differences at a Glance

| Aspect | TypeScript | Zig |
|--------|------------|-----|
| **Typing** | Structural, optional | Explicit, comptime |
| **Errors** | Exceptions (`try/catch`) | Error unions (`!Type`) |
| **Concurrency** | Promises + async/await | std.Thread (manual) |
| **Memory** | GC (automatic) | Manual + explicit allocators |
| **Performance** | JIT (V8) | Compiled (native) |
| **Deployment** | Node.js + packages | Single binary |

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
    },
};
```

### Zig
```zig
const agenkit = @import("agenkit");
const std = @import("std");

// Stack-allocated (no heap)
var msg = agenkit.Message{
    .role = "user",
    .content = "Hello!",
};

// With owned strings (requires allocator)
pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    var metadata = std.StringHashMap([]const u8).init(allocator);
    errdefer metadata.deinit();
    try metadata.put("key", "value");

    return agenkit.Message{
        .role = "user",
        .content = content,
        .metadata = metadata,
    };
}

// Cleanup required
defer allocator.free(msg.content);
defer msg.metadata.deinit();
```

**Changes**:
- Import: `'@agenkit/core'` → `@import("agenkit")`
- Object literal → Struct literal with `.field` syntax
- Automatic GC → Manual cleanup with `defer`
- `metadata: {}` → `std.StringHashMap([]const u8)`
- String type: `string` → `[]const u8` (slice)
- No optional fields by default → Use `?T` for nullable

---

## Agent Implementation

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    private config: Config;

    constructor(config: Config) {
        this.config = config;
    }

    get name(): string {
        return 'my-agent';
    }

    get capabilities(): string[] {
        return ['text', 'analysis'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `Processed: ${message.content}`,
        };
    }
}
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
        // Cleanup resources
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
        errdefer self.allocator.free(content);

        return agenkit.Message{
            .role = "assistant",
            .content = content,
        };
    }
};

// Usage
var agent = try MyAgent.init(allocator, config);
defer agent.deinit();
```

**Changes**:
- `class` → `struct` (no inheritance)
- `constructor` → `init` function (convention)
- `get` properties → Regular functions
- `async/await` → Synchronous (returns `!Type` for errors)
- `Promise<T>` → `!T` (error union)
- `this.` → `self.` (explicit parameter)
- Destructor: automatic → `deinit()` called manually
- Pass allocator explicitly to every allocating function

---

## Error Handling

### TypeScript
```typescript
try {
    const result = await agent.process(message);
    console.log(result.content);
} catch (error) {
    if (error instanceof AgentError) {
        throw new Error(`Agent failed: ${error.message}`);
    }
    throw error;
}
```

### Zig
```zig
// Using 'try' to propagate errors
const result = try agent.process(msg);
std.debug.print("{s}\n", .{result.content});

// Or catch and handle explicitly
const result = agent.process(msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.AgentFailed;
        },
        else => return err,
    }
};

// Or use if syntax for optional handling
if (agent.process(msg)) |success| {
    std.debug.print("Success: {s}\n", .{success.content});
} else |err| {
    std.debug.print("Error: {}\n", .{err});
    return err;
}
```

**Changes**:
- `try/catch` → `try` keyword or `catch |err|` block
- Exception unwinding → Explicit error propagation
- `throw new Error()` → `return error.ErrorName`
- `instanceof` checks → `switch` on error type
- Error wrapping: automatic stack traces → manual context
- No `finally` block → use `defer` instead

### Error Type Definitions

**TypeScript**:
```typescript
class AgentError extends Error {
    constructor(message: string, public cause?: Error) {
        super(message);
        this.name = 'AgentError';
    }
}
```

**Zig**:
```zig
const AgentError = error{
    InvalidMessage,
    ProcessingFailed,
    Timeout,
    OutOfMemory,
};

// Function returning error union
fn processMessage(msg: Message) AgentError!Message {
    if (msg.content.len == 0) {
        return error.InvalidMessage;
    }
    // ...
}
```

---

## Concurrency

### TypeScript (Promises)
```typescript
// Create async tasks
const task1 = agent1.process(message);
const task2 = agent2.process(message);
const task3 = agent3.process(message);

// Wait for all in parallel
const [result1, result2, result3] = await Promise.all([
    task1,
    task2,
    task3
]);

// Race (first wins)
const fastest = await Promise.race([
    agent1.process(message),
    agent2.process(message)
]);

// Sequential with async/await
const step1 = await agent1.process(message);
const step2 = await agent2.process(step1);
const step3 = await agent3.process(step2);
```

### Zig (Manual Threading)
```zig
const std = @import("std");

// Spawn threads manually
const handle1 = try std.Thread.spawn(.{}, workerFn, .{ &agent1, msg });
const handle2 = try std.Thread.spawn(.{}, workerFn, .{ &agent2, msg });
const handle3 = try std.Thread.spawn(.{}, workerFn, .{ &agent3, msg });

// Wait for all
handle1.join();
handle2.join();
handle3.join();

// Worker function
fn workerFn(agent: *Agent, msg: Message) void {
    const result = agent.process(msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    // Use result
}

// Sequential (just call functions)
const step1 = try agent1.process(msg);
defer allocator.free(step1.content);

const step2 = try agent2.process(step1);
defer allocator.free(step2.content);

const step3 = try agent3.process(step2);
defer allocator.free(step3.content);
```

**Changes**:
- `Promise.all()` → Manual thread spawning + join
- `Promise.race()` → No built-in equivalent (implement with mutex)
- `async/await` → Synchronous blocking calls
- Event loop → OS threads (std.Thread)
- Single-threaded → Multi-threaded (if you spawn threads)
- No built-in async/await (removed in Zig 0.11)

### Synchronization

**TypeScript** (implicit via event loop):
```typescript
// No explicit synchronization needed
let counter = 0;
await Promise.all([
    async () => counter++,  // Race condition in theory, but event loop prevents it
    async () => counter++,
]);
```

**Zig** (explicit mutexes):
```zig
var counter: usize = 0;
var mutex = std.Thread.Mutex{};

fn increment() void {
    mutex.lock();
    defer mutex.unlock();
    counter += 1;
}

// Spawn threads
const h1 = try std.Thread.spawn(.{}, increment, .{});
const h2 = try std.Thread.spawn(.{}, increment, .{});
h1.join();
h2.join();
```

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

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var sequential = try patterns.Sequential.init(
    allocator,
    &[_]Agent{ agent1, agent2, agent3 }
);
defer sequential.deinit();

const result = try sequential.process(msg);
defer allocator.free(result.content);
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

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var parallel = try patterns.Parallel.init(
    allocator,
    &[_]Agent{ agent_a, agent_b, agent_c }
);
defer parallel.deinit();

const result = try parallel.process(msg);
defer allocator.free(result.content);
```

**Changes**:
- Constructor `new` → `init()` function
- Automatic cleanup → Manual `defer deinit()`
- Array literal `[]` → Array literal `[_]Type{}`
- Pass allocator explicitly

---

## Common Gotchas

### 1. Memory Management

**TypeScript**: Automatic garbage collection
```typescript
function processData() {
    const buffer = new ArrayBuffer(1024);
    // buffer automatically freed when function exits
}
```

**Zig**: Manual allocation and deallocation
```zig
fn processData(allocator: std.mem.Allocator) !void {
    const buffer = try allocator.alloc(u8, 1024);
    defer allocator.free(buffer);  // MUST free manually

    // If you forget defer, memory leak!
}
```

**Key Points**:
- Every `alloc()` needs a corresponding `free()`
- Use `defer` immediately after allocation
- Use `errdefer` for error-path cleanup
- Debug builds detect leaks with GeneralPurposeAllocator

### 2. String Handling

**TypeScript**: Mutable strings, automatic memory
```typescript
let str = "Hello";
str += " World";  // Creates new string
const upper = str.toUpperCase();
```

**Zig**: Immutable slices, manual memory
```zig
const str = "Hello";  // []const u8 (immutable slice)
// Cannot mutate!

// String concatenation requires allocation
const combined = try std.fmt.allocPrint(
    allocator,
    "{s} World",
    .{str}
);
defer allocator.free(combined);

// Upper case requires allocation
const upper = try std.ascii.allocUpperString(allocator, str);
defer allocator.free(upper);
```

**Key Points**:
- TypeScript `string` → Zig `[]const u8` (const slice)
- No string mutation in Zig (create new strings)
- All string operations require explicit allocator
- Template strings → `std.fmt.allocPrint()`

### 3. Null vs Optional

**TypeScript**: `null`, `undefined`, `?` operator
```typescript
let value: string | null = null;
let maybeValue: string | undefined;

const length = value?.length ?? 0;
```

**Zig**: Optional types `?T`
```zig
var value: ?[]const u8 = null;

// Check if value exists
if (value) |actual_value| {
    const length = actual_value.len;
} else {
    const length: usize = 0;
}

// Or use orelse
const length = if (value) |v| v.len else 0;
// Or shorthand
const actual = value orelse "default";
```

**Key Points**:
- TypeScript `null | undefined` → Zig `?T`
- `?.` operator → `if (value) |v|` syntax
- `??` operator → `orelse` keyword
- Must unwrap optional explicitly

### 4. Async/Await → Blocking Calls

**TypeScript**: Non-blocking I/O
```typescript
async function fetchMultiple() {
    // All run concurrently
    const [a, b, c] = await Promise.all([
        fetchA(),
        fetchB(),
        fetchC()
    ]);
}
```

**Zig**: Blocking calls (spawn threads for concurrency)
```zig
fn fetchMultiple(allocator: std.mem.Allocator) !void {
    // Sequential by default (blocking)
    const a = try fetchA();
    const b = try fetchB();
    const c = try fetchC();

    // For concurrency, spawn threads
    const h1 = try std.Thread.spawn(.{}, fetchA, .{});
    const h2 = try std.Thread.spawn(.{}, fetchB, .{});
    const h3 = try std.Thread.spawn(.{}, fetchC, .{});

    h1.join();
    h2.join();
    h3.join();
}
```

**Key Points**:
- TypeScript: async by default (event loop)
- Zig: sync by default (blocking)
- No built-in async/await in Zig 0.11+
- Use std.Thread for parallelism

### 5. Type System Differences

**TypeScript**: Structural typing (duck typing at compile time)
```typescript
interface Agent {
    name: string;
    process(msg: Message): Promise<Message>;
}

// Any object with these properties works
const agent: Agent = {
    name: "custom",
    process: async (msg) => msg,
};
```

**Zig**: Comptime duck typing (checked at compile time)
```zig
const Agent = struct {
    ptr: *anyopaque,
    nameFn: *const fn (*anyopaque) []const u8,
    processFn: *const fn (*anyopaque, Message) anyerror!Message,

    pub fn init(pointer: anytype) Agent {
        const T = @TypeOf(pointer.*);

        return Agent{
            .ptr = pointer,
            .nameFn = T.name,
            .processFn = T.process,
        };
    }
};

// Or use comptime polymorphism
fn processWithAgent(comptime T: type, agent: *T, msg: Message) !Message {
    // T must have .process() method (checked at compile time)
    return agent.process(msg);
}
```

**Key Points**:
- TypeScript: interfaces checked structurally
- Zig: interfaces via function pointers (vtables) or comptime
- TypeScript: runtime polymorphism
- Zig: comptime polymorphism (zero runtime cost)

---

## Testing

### TypeScript
```typescript
import { describe, it, expect } from 'vitest';
import { MyAgent } from './agent';
import { Message } from '@agenkit/core';

describe('MyAgent', () => {
    it('should process message', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: 'Test',
        };

        const result = await agent.process(msg);

        expect(result.role).toBe('assistant');
        expect(result.content).toContain('Processed');
    });

    it('should throw on empty content', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: '',
        };

        await expect(agent.process(msg))
            .rejects
            .toThrow('Empty content');
    });
});
```

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

test "agent errors on empty content" {
    const allocator = testing.allocator;

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const msg = Message{
        .role = "user",
        .content = "",
    };

    try testing.expectError(error.InvalidMessage, agent.process(msg));
}
```

**Changes**:
- `describe/it` → `test "description"`
- `expect()` → `try testing.expect()`
- No async/await in tests
- Manual setup/teardown with `defer`
- `testing.allocator` detects memory leaks automatically
- Run with: `zig build test`

---

## Performance Considerations

| Operation | TypeScript | Zig | Notes |
|-----------|------------|-----|-------|
| Agent creation | ~500ns | ~50ns | Zig 10x faster (no GC) |
| Message processing | ~5μs | ~500ns | Zig 10x faster (compiled) |
| Sequential (3 agents) | ~15μs | ~1.5μs | Zig 10x faster |
| Parallel (3 agents) | ~5μs | ~5μs | Similar (thread overhead) |
| Memory usage | Higher (GC) | Lower (manual) | Zig ~5x less memory |
| Binary size | N/A | <100KB | Zig single binary |

### When to Use Zig

- **Embedded systems**: Microcontrollers, IoT devices
- **Performance critical**: Real-time processing, high throughput
- **Memory constrained**: Limited RAM environments
- **Single binary deployment**: No runtime dependencies
- **Systems programming**: OS kernels, drivers, low-level tools
- **WebAssembly**: High-performance WASM modules

### When to Keep TypeScript

- **Web development**: Browser + Node.js universal code
- **Rapid prototyping**: Fast iteration without compilation
- **Rich ecosystem**: Access to 2M+ NPM packages
- **Developer familiarity**: Large TypeScript developer pool
- **Async I/O workloads**: Natural async/await patterns
- **Type safety**: Compile-time checks with gradual typing

---

## Migration Checklist

- [ ] Replace `class` with `struct`
- [ ] Convert `constructor` to `init()` function
- [ ] Add `deinit()` for cleanup
- [ ] Add `allocator: std.mem.Allocator` parameter to all allocating functions
- [ ] Replace `async/await` with synchronous calls
- [ ] Replace `Promise<T>` with `!T` (error union)
- [ ] Change `try/catch` to `try` or `catch |err|`
- [ ] Replace `throw new Error()` with `return error.Name`
- [ ] Add `defer` for resource cleanup
- [ ] Replace `string` with `[]const u8`
- [ ] Replace `Array<T>` with `[]T` or `std.ArrayList(T)`
- [ ] Replace object literals with struct literals
- [ ] Update imports: `import` → `@import()`
- [ ] Remove async/Promise-based concurrency → manual threading
- [ ] Add explicit memory management (alloc/free)
- [ ] Replace `null | undefined` with `?T`
- [ ] Update tests: Vitest/Jest → `test "name"`
- [ ] Handle compilation errors (Zig catches more at compile time)

---

## Quick Start

```bash
# TypeScript project structure
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   └── agent.ts
└── tests/
    └── agent.test.ts

# Zig equivalent
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig
└── tests/
    └── agent_test.zig
```

**Build/Run**:
```bash
# TypeScript
npm install
npm run build
node dist/index.js

# Or with tsx (no build)
npx tsx src/index.ts

# Zig
zig build
./zig-out/bin/agenkit

# Or run directly
zig build run
```

**Testing**:
```bash
# TypeScript
npm test

# Zig
zig build test
```

---

## Memory Management Deep Dive

### Allocator Patterns

**1. General Purpose Allocator** (development):
```zig
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();  // Reports leaks in debug builds
const allocator = gpa.allocator();
```

**2. Arena Allocator** (bulk cleanup):
```zig
var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
defer arena.deinit();  // Frees ALL allocations at once
const allocator = arena.allocator();

// Perfect for request-scoped data
```

**3. Fixed Buffer Allocator** (stack-based):
```zig
var buffer: [4096]u8 = undefined;
var fba = std.heap.FixedBufferAllocator.init(&buffer);
const allocator = fba.allocator();

// No heap allocations, fast but limited size
```

**4. C Allocator** (malloc/free):
```zig
const allocator = std.heap.c_allocator;
// Use for C interop only
```

### Common Memory Patterns

**TypeScript** (automatic):
```typescript
async function processRequest(data: string): Promise<Result> {
    const parsed = JSON.parse(data);
    const processed = await heavyOperation(parsed);
    return { success: true, data: processed };
    // All memory automatically freed
}
```

**Zig** (manual with arena):
```zig
fn processRequest(parent_allocator: std.mem.Allocator, data: []const u8) !Result {
    var arena = std.heap.ArenaAllocator.init(parent_allocator);
    defer arena.deinit();  // Cleanup all request memory at once
    const allocator = arena.allocator();

    const parsed = try std.json.parseFromSlice(Data, allocator, data, .{});
    const processed = try heavyOperation(allocator, parsed.value);

    // Return only what needs to outlive the function
    return Result{
        .success = true,
        .data = try parent_allocator.dupe(u8, processed),
    };
}
```

---

## Full Resources

- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms guide
- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [Zig Learn](https://ziglearn.org/) - Comprehensive Zig tutorial
- [Zig Language Reference](https://ziglang.org/documentation/master/) - Official docs
- [Agenkit Zig Examples](../agenkit-zig/examples/) - Side-by-side code samples
- [Agenkit Zig Tests](../agenkit-zig/tests/) - Test patterns

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
