# Quick Reference: Zig → TypeScript Migration

**For**: Zig developers migrating Agenkit code to TypeScript
**Time**: 15 minute read
**Full Details**: See [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) and [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md)

---

## Key Differences at a Glance

| Aspect | Zig | TypeScript |
|--------|-----|------------|
| **Typing** | Static, comptime | Static, structural |
| **Errors** | Error unions `!T` | Exceptions (`try/catch`) |
| **Concurrency** | std.Thread (OS threads) | Promises + event loop |
| **Memory** | Manual + allocators | GC (automatic) |
| **Performance** | Native, zero overhead | JIT (V8), 10-20x slower |
| **Deployment** | Single binary | Node.js + packages |

---

## Message Creation

### Zig
```zig
const agenkit = @import("agenkit");
const std = @import("std");

pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    return agenkit.Message{
        .role = "user",
        .content = content,
        .metadata = null,
    };
}

// Cleanup required
const msg = try createMessage(allocator);
defer allocator.free(msg.content);
```

### TypeScript
```typescript
import { Message } from '@agenkit/core';

function createMessage(): Message {
    return {
        role: 'user',
        content: 'Hello!',
        metadata: {},
    };
}

// No cleanup needed - GC handles it
const msg = createMessage();
```

**Changes**:
- **Allocators removed**: GC manages memory automatically
- **No defer**: Cleanup happens automatically
- **No errdefer**: Use `try/finally` for explicit cleanup
- **Strings**: `[]const u8` → `string` (native type)
- **Optional**: `?T` → `T | undefined` or `T | null`

---

## Agent Implementation

### Zig
```zig
const Agent = @import("agenkit").Agent;
const std = @import("std");

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

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    private readonly nameStr: string = 'my-agent';

    get name(): string {
        return this.nameStr;
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

**Changes**:
- **No allocator parameter**: Memory management is automatic
- **No init/deinit**: Use constructor/destructor (rarely needed)
- **Struct → Class**: OOP with `class` keyword
- **Error unions → Promises**: `!T` becomes `Promise<T>`
- **Getters**: Use `get` keyword instead of methods
- **String formatting**: `std.fmt.allocPrint` → template literals

---

## Error Handling

### Zig
```zig
const result = agent.process(msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or use if/else
if (agent.process(msg)) |success| {
    // Use success value
} else |err| {
    // Handle error
    return err;
}
```

### TypeScript
```typescript
try {
    const result = await agent.process(message);
    // Use result
} catch (error) {
    if (error instanceof AgentError) {
        console.error('Invalid message');
        throw new AgentError('Processing failed', error);
    }
    throw error;
}
```

**Changes**:
- **Error unions → Exceptions**: Explicit `!T` → implicit exception propagation
- **catch |err|** → **catch (error)**: Different syntax, similar purpose
- **switch on error** → **instanceof checks**: Pattern matching → type checking
- **No compile-time error checking**: Errors discovered at runtime
- **Error wrapping**: `return err` → `throw new Error(..., cause)`

---

## Concurrency

### Zig (OS Threads)
```zig
const std = @import("std");

// Spawn thread
const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, data});
handle.join();  // Wait for completion

// Worker function
fn workerFunction(allocator: std.mem.Allocator, data: []const u8) void {
    std.debug.print("Worker processing: {s}\n", .{data});
}

// Multiple threads
var threads: [3]std.Thread = undefined;
for (threads) |*thread, i| {
    thread.* = try std.Thread.spawn(.{}, worker, .{i});
}
for (threads) |thread| {
    thread.join();
}

// Mutex for synchronization
var mutex = std.Thread.Mutex{};
fn safeIncrement(counter: *usize) void {
    mutex.lock();
    defer mutex.unlock();
    counter.* += 1;
}
```

### TypeScript (Promises)
```typescript
// Launch async operation
async function workerFunction(data: string): Promise<void> {
    console.log(`Worker processing: ${data}`);
}

const promise = workerFunction(data);
await promise;  // Wait for completion

// Multiple operations in parallel
const promises = [
    workerFunction('task1'),
    workerFunction('task2'),
    workerFunction('task3'),
];
await Promise.all(promises);

// No mutex needed - single-threaded event loop
// For shared state, use atomics with SharedArrayBuffer (advanced)
```

**Changes**:
- **std.Thread → Promises**: OS threads → event loop concurrency
- **True parallelism → Cooperative**: Multiple cores → single thread
- **Blocking → Non-blocking**: join() → await
- **Mutex → Event loop**: Manual locking → automatic serialization
- **Performance**: Threads faster for CPU-bound, Promises better for I/O

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

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2, agent3],
});

const result = await sequential.process(message);
// No cleanup needed
```

### Parallel

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var parallel = try patterns.Parallel.init(allocator, &[_]Agent{
    agentA,
    agentB,
    agentC,
});
defer parallel.deinit();

const result = try parallel.process(msg);
defer allocator.free(result.content);
```

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB, agentC],
});

const result = await parallel.process(message);
```

---

## Common Gotchas

### 1. Memory Management Paradigm Shift

**Zig**: Explicit allocators everywhere
```zig
fn createData(allocator: std.mem.Allocator) ![]u8 {
    const data = try allocator.alloc(u8, 1024);
    errdefer allocator.free(data);
    // Must track who owns data
    return data;
}

// Caller must free
const data = try createData(allocator);
defer allocator.free(data);
```

**TypeScript**: GC handles everything
```typescript
function createData(): Uint8Array {
    const data = new Uint8Array(1024);
    // GC automatically frees when no references
    return data;
}

// No cleanup needed
const data = createData();
```

**Gotcha**: Coming from Zig, you might:
- Add unnecessary cleanup code
- Worry about memory leaks (GC prevents most)
- Try to manually manage memory (can't in JS/TS)

**Solution**: Trust the GC, focus on business logic.

### 2. Error Handling Invisibility

**Zig**: Errors visible in type signatures
```zig
// You KNOW this can fail by looking at return type
fn process(msg: Message) !Message {
    return error.Failed;
}

// Compiler forces you to handle error
const result = try process(msg);  // or catch
```

**TypeScript**: Exceptions are invisible
```typescript
// No indication this can throw
async function process(msg: Message): Promise<Message> {
    throw new Error('Failed');
}

// Easy to forget error handling
const result = await process(msg);  // Might throw!

// Should be:
try {
    const result = await process(msg);
} catch (error) {
    // Handle error
}
```

**Gotcha**: Silent failures if you forget try/catch.

**Solution**:
- Use linters (ESLint) to catch unhandled promises
- Document throws with JSDoc: `@throws {AgentError}`
- Consider Result types library for explicit errors

### 3. Concurrency Model Confusion

**Zig**: True parallelism with threads
```zig
// These run on different CPU cores simultaneously
const t1 = try std.Thread.spawn(.{}, cpuIntensive, .{});
const t2 = try std.Thread.spawn(.{}, cpuIntensive, .{});
// Both use 100% of their core
```

**TypeScript**: Cooperative concurrency
```typescript
// These DON'T run in parallel (single thread)
const p1 = cpuIntensive();
const p2 = cpuIntensive();
await Promise.all([p1, p2]);
// Only uses one CPU core, switches between tasks
```

**Gotcha**: Expecting parallel execution for CPU-bound work.

**Solution**:
- Use Web Workers (browser) or worker_threads (Node.js) for true parallelism
- Reserve async/await for I/O-bound operations
- Consider offloading CPU work to separate process

### 4. Comptime vs. Generics

**Zig**: Compile-time execution
```zig
fn ArrayList(comptime T: type) type {
    return struct {
        items: []T,
        // Type-specific code generated at compile time
    };
}

// Compile-time assertions
comptime {
    if (@sizeOf(Message) > 1024) {
        @compileError("Message too large");
    }
}
```

**TypeScript**: Runtime generics (type erasure)
```typescript
class ArrayList<T> {
    items: T[];
    // Generic type info erased at runtime
}

// No compile-time execution
// Can't assert on type properties at compile time
```

**Gotcha**: Trying to use generics for compile-time decisions.

**Solution**:
- Accept that TS generics are compile-time only
- Use runtime checks for size/type validation
- Leverage TypeScript's type system for static checks

### 5. Optional Type Handling

**Zig**: Explicit unwrapping required
```zig
const value: ?u32 = getOptional();

// Must unwrap explicitly
if (value) |v| {
    std.debug.print("Value: {}\n", .{v});
} else {
    std.debug.print("No value\n", .{});
}

// Or provide default
const v = value orelse 0;
```

**TypeScript**: Easier but less safe
```typescript
const value: number | undefined = getOptional();

// Can forget to check
console.log(value.toFixed(2));  // Runtime error if undefined!

// Should check first
if (value !== undefined) {
    console.log(value.toFixed(2));
}

// Or use optional chaining
console.log(value?.toFixed(2));  // Returns undefined if null/undefined

// Nullish coalescing
const v = value ?? 0;
```

**Gotcha**: Runtime errors from unchecked undefined/null.

**Solution**:
- Enable `strictNullChecks` in tsconfig.json
- Use optional chaining `?.` and nullish coalescing `??`
- Let TypeScript catch potential undefined access

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

### TypeScript
```typescript
import { describe, it, expect } from 'vitest';
import { MyAgent } from './agent';
import { Message } from '@agenkit/core';

describe('MyAgent', () => {
    it('should process message correctly', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: 'Test',
        };

        const result = await agent.process(msg);

        expect(result.role).toBe('assistant');
        expect(result.content).toContain('Processed');
    });

    it('should handle empty message', async () => {
        const agent = new MyAgent();
        const emptyMsg: Message = {
            role: 'user',
            content: '',
        };

        await expect(agent.process(emptyMsg))
            .rejects
            .toThrow('Invalid message');
    });
});
```

**Changes**:
- **test "name"** → **it('should...', async () => {})**: Different syntax
- **No allocator setup**: GC handles memory
- **No defer cleanup**: Automatic
- **testing.expectX** → **expect(x).toBe/toContain**: Different assertions
- **Error testing**: `expectError` → `expect(...).rejects.toThrow()`
- **Async tests**: Add `async` keyword, use `await`

---

## Performance Considerations

| Operation | Zig | TypeScript | Performance Gap |
|-----------|-----|------------|-----------------|
| Message creation | ~50ns | ~500ns | 10x slower |
| Agent processing | ~500ns | ~5μs | 10x slower |
| Sequential (3 agents) | ~1.5μs | ~15μs | 10x slower |
| Parallel (3 agents) | ~5μs | ~5μs | Similar (I/O bound) |
| Thread/Promise spawn | ~10μs | ~1μs | TS faster (lighter) |
| Memory usage (baseline) | ~1MB | ~50MB | 50x more memory |

**Why TypeScript is Slower**:
- **JIT warmup**: V8 needs time to optimize hot code
- **GC pauses**: Garbage collection introduces latency
- **Type erasure**: Runtime type checking overhead
- **Single-threaded**: Can't use multiple CPU cores (without workers)
- **Interpreted**: No ahead-of-time native compilation

**When to Migrate to TypeScript**:
- **Web deployment**: Browser/Node.js universal code
- **Rapid iteration**: No compilation step
- **Team familiarity**: JS/TS ecosystem dominance
- **NPM ecosystem**: Access to 2M+ packages
- **Cross-platform**: Same code everywhere

**When to Keep Zig**:
- **Performance critical**: Embedded, real-time, HPC
- **Memory constrained**: IoT, mobile, edge devices
- **Latency sensitive**: <1ms response time requirements
- **No runtime**: Environments without JS engine
- **Binary deployment**: Single executable

---

## Migration Checklist

- [ ] Remove all `allocator` parameters and variables
- [ ] Delete all `defer` and `errdefer` cleanup code
- [ ] Convert error unions `!T` to `Promise<T>` for async or plain `T`
- [ ] Replace `catch |err|` with `try/catch (error)`
- [ ] Change `std.Thread` to `async/await` with Promises
- [ ] Convert string slices `[]const u8` to `string`
- [ ] Replace optional `?T` with `T | undefined` or `T | null`
- [ ] Update struct initialization to object literals
- [ ] Convert comptime generics to TypeScript generics
- [ ] Replace `std.debug.print` with `console.log`
- [ ] Update imports: `@import("agenkit")` → `import { } from '@agenkit/core'`
- [ ] Convert tests: `test "name"` → `it('should...', async () => {})`
- [ ] Remove manual memory leak checks (GC handles it)
- [ ] Update build: `zig build` → `npm build` or `tsc`

---

## Quick Start

```bash
# Zig project structure
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig
└── zig-out/
    └── bin/myagent

# TypeScript equivalent
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── main.ts
│   └── agent.ts
└── dist/
    └── main.js
```

**Build/Run**:
```bash
# Zig
zig build
./zig-out/bin/myagent

# TypeScript (development)
npm run dev  # or: ts-node src/main.ts

# TypeScript (production)
npm run build  # Compiles to dist/
node dist/main.js
```

**Install Agenkit**:
```bash
# Zig
# Add to build.zig.zon or build.zig

# TypeScript
npm install @agenkit/core
```

---

## Real-World Example

### Complete Zig Program
```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const msg = agenkit.Message{
        .role = "user",
        .content = "Hello, Zig!",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    std.debug.print("Agent: {s}\n", .{result.content});
}

const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !MyAgent {
        return MyAgent{ .allocator = allocator };
    }

    pub fn deinit(self: *MyAgent) void {
        _ = self;
    }

    pub fn process(self: *MyAgent, msg: agenkit.Message) !agenkit.Message {
        const content = try std.fmt.allocPrint(
            self.allocator,
            "Echo: {s}",
            .{msg.content}
        );

        return agenkit.Message{
            .role = "assistant",
            .content = content,
        };
    }
};
```

### Equivalent TypeScript Program
```typescript
import { Message, Agent } from '@agenkit/core';

async function main() {
    const agent = new MyAgent();

    const msg: Message = {
        role: 'user',
        content: 'Hello, TypeScript!',
    };

    const result = await agent.process(msg);

    console.log(`Agent: ${result.content}`);
}

class MyAgent implements Agent {
    get name(): string {
        return 'echo-agent';
    }

    get capabilities(): string[] {
        return ['text'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `Echo: ${message.content}`,
        };
    }
}

main().catch(console.error);
```

**Key Differences Highlighted**:
1. **50% less code**: No allocator boilerplate
2. **Simpler**: No manual memory management
3. **Readable**: Template literals, async/await
4. **Safe**: GC prevents memory leaks
5. **Slower**: ~10x performance cost

---

## Architecture Patterns

### Resource Management

**Zig Pattern**: Arena allocator for batch cleanup
```zig
fn processMany(allocator: std.mem.Allocator, messages: []Message) !void {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();  // Frees everything at once
    const temp_allocator = arena.allocator();

    for (messages) |msg| {
        const result = try agent.process(temp_allocator, msg);
        // No individual cleanup needed
    }
    // arena.deinit() cleans up all allocations
}
```

**TypeScript Pattern**: Let GC handle it
```typescript
async function processMany(messages: Message[]): Promise<void> {
    for (const msg of messages) {
        const result = await agent.process(msg);
        // GC automatically frees when result goes out of scope
    }
    // No explicit cleanup
}
```

### Error Context

**Zig Pattern**: Error wrapping with context
```zig
fn processWithContext(allocator: std.mem.Allocator, msg: Message) !Message {
    const result = agent.process(allocator, msg) catch |err| {
        std.log.err("Failed to process message: {}", .{err});
        return err;  // Propagate original error
    };
    return result;
}
```

**TypeScript Pattern**: Error chaining with cause
```typescript
async function processWithContext(msg: Message): Promise<Message> {
    try {
        return await agent.process(msg);
    } catch (error) {
        const err = error as Error;
        throw new Error(
            `Failed to process message: ${err.message}`,
            { cause: err }  // ES2022: Error cause
        );
    }
}
```

---

## Full Resources

- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript patterns
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html) - Official docs
- [Main Migration Guide](MIGRATION.md) - Python → All languages

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
