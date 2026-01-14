# Quick Reference: Zig → Python Migration

**For**: Zig developers migrating Agenkit code to Python
**Time**: 15 minute read
**Full Details**: See [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) and [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md)

---

## Key Differences at a Glance

| Aspect | Zig | Python |
|--------|-----|--------|
| **Typing** | Static, explicit, comptime | Dynamic, optional hints |
| **Errors** | Error unions `!Type` | Exceptions (`try/except`) |
| **Concurrency** | std.Thread (OS threads) | `async/await` + `asyncio` |
| **Memory** | Manual + allocators | GC + refcounting |
| **Performance** | Native code, no runtime | Interpreted, 20-100x slower |
| **Deployment** | Single binary | Interpreter + packages |
| **Philosophy** | Explicit everything | Batteries included |

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
        .timestamp = null,
    };
}

// Usage with cleanup
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();

var msg = try createMessage(allocator);
defer allocator.free(msg.content);
```

### Python
```python
from agenkit import Message

def create_message() -> Message:
    return Message(
        role="user",
        content="Hello!",
        metadata=None,
        timestamp=None,
    )

# Usage - no cleanup needed
msg = create_message()
# Memory automatically managed
```

**Changes**:
- **Allocators**: Remove all `std.mem.Allocator` parameters
- **Manual cleanup**: Remove all `defer` and `errdefer` statements
- **Error unions**: `!Type` returns → simple return type
- **String types**: `[]const u8` → `str`
- **Null types**: `?T` → `Optional[T]` or `T | None`
- **Memory**: Everything automatically garbage collected

---

## Agent Implementation

### Zig
```zig
const std = @import("std");
const agenkit = @import("agenkit");

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
        // Cleanup resources if needed
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
        errdefer self.allocator.free(content);

        return agenkit.Message{
            .role = "assistant",
            .content = content,
        };
    }
};
```

### Python
```python
from agenkit import Agent, Message
from typing import List

class MyAgent(Agent):
    def __init__(self):
        self._name = "my-agent"

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> List[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        content = f"Processed: {message.content}"

        return Message(
            role="assistant",
            content=content,
        )
```

**Changes**:
- **Struct → Class**: `pub const MyAgent = struct` → `class MyAgent(Agent)`
- **Constructor**: `pub fn init()` → `def __init__(self)`
- **No deinit**: Remove `pub fn deinit()` (automatic GC)
- **Properties**: Methods → `@property` decorators
- **Allocators**: Remove all allocator parameters and state
- **Async**: Methods become `async def` (not blocking threads)
- **Error unions**: `!Type` → return type (errors become exceptions)
- **String formatting**: `std.fmt.allocPrint` → f-strings (`f"..."`)

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

    // Try operation, propagate with 'try'
    const validated = try validateMessage(msg);

    return validated;
}

// Call site with error handling
const result = processMessage(allocator, msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or with if statement
if (processMessage(allocator, msg)) |success| {
    // Use success value
    std.debug.print("Result: {s}\n", .{success.content});
} else |err| {
    // Handle error
    std.debug.print("Error: {}\n", .{err});
}
```

### Python (Exceptions)
```python
class AgentError(Exception):
    """Base exception for agent errors."""
    pass

class InvalidMessageError(AgentError):
    """Message validation failed."""
    pass

class ProcessingFailedError(AgentError):
    """Processing failed."""
    pass

class TimeoutError(AgentError):
    """Operation timed out."""
    pass

async def process_message(msg: Message) -> Message:
    if not msg.content:
        raise InvalidMessageError("Message content cannot be empty")

    # Call operation - exceptions propagate automatically
    validated = await validate_message(msg)

    return validated

# Call site with error handling
try:
    result = await process_message(msg)
    # Use result
except InvalidMessageError as e:
    print(f"Invalid message: {e}")
    raise  # Re-raise exception
except AgentError as e:
    print(f"Agent error: {e}")
    raise
```

**Changes**:
- **Error sets**: `error{...}` → exception class hierarchy
- **Error unions**: `!Type` → normal return type
- **Return errors**: `return error.InvalidMessage` → `raise InvalidMessageError(...)`
- **Try keyword**: `try expr` → `await expr` (exceptions auto-propagate)
- **Catch blocks**: `catch |err| {...}` → `try/except`
- **Switch on error**: Pattern matching → exception class hierarchy
- **If-else syntax**: `if (call()) |val| {} else |err| {}` → `try/except`

---

## Concurrency

### Zig (OS Threads)
```zig
const std = @import("std");

// Spawn thread
const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, msg});
handle.join();  // Wait for completion

fn workerFunction(allocator: std.mem.Allocator, msg: Message) void {
    const result = agent.process(msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    // Use result
}

// Multiple threads with manual synchronization
var mutex = std.Thread.Mutex{};
var results = std.ArrayList(Message).init(allocator);
defer results.deinit();

var threads = std.ArrayList(std.Thread).init(allocator);
defer threads.deinit();

for (agents) |agent| {
    const handle = try std.Thread.spawn(.{}, processWithSync, .{
        agent, msg, &mutex, &results,
    });
    try threads.append(handle);
}

// Wait for all threads
for (threads.items) |handle| {
    handle.join();
}

fn processWithSync(
    agent: *Agent,
    msg: Message,
    mutex: *std.Thread.Mutex,
    results: *std.ArrayList(Message),
) void {
    const result = agent.process(msg) catch return;

    mutex.lock();
    defer mutex.unlock();
    results.append(result) catch {};
}
```

### Python (async/await)
```python
import asyncio

# Launch coroutine as task
async def worker_function(agent: Agent, msg: Message):
    try:
        result = await agent.process(msg)
        # Use result
    except Exception as e:
        print(f"Error: {e}")

# Create and run task
task = asyncio.create_task(worker_function(agent, msg))
await task  # Wait for completion

# Multiple coroutines with gather
results = await asyncio.gather(*[
    agent.process(msg)
    for agent in agents
])

# Or with error handling
results = await asyncio.gather(*[
    agent.process(msg)
    for agent in agents
], return_exceptions=True)

# Check results
for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"Agent {i} failed: {result}")
    else:
        print(f"Agent {i} succeeded: {result.content}")
```

**Changes**:
- **std.Thread**: OS threads → asyncio coroutines (cooperative)
- **spawn + join**: `Thread.spawn()` → `asyncio.create_task()` + `await`
- **Function signature**: Blocking function → `async def`
- **Waiting**: `handle.join()` → `await task`
- **Multiple workers**: Manual thread management → `asyncio.gather()`
- **Mutex**: `std.Thread.Mutex` → `asyncio.Lock()` (rarely needed)
- **No allocator**: Remove allocator parameters
- **Simplification**: ~20 lines of Zig → ~10 lines of Python

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
defer {
    if (result.content) |content| {
        allocator.free(content);
    }
}
```

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[agent1, agent2, agent3])
result = await sequential.process(msg)
# No cleanup needed
```

### Parallel

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var parallel = try patterns.Parallel.init(allocator, &[_]Agent{
    agent_a,
    agent_b,
    agent_c,
});
defer parallel.deinit();

const result = try parallel.process(msg);
defer allocator.free(result.content);
```

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[agent_a, agent_b, agent_c])
result = await parallel.process(msg)
# Automatic memory management
```

### Router

**Zig**:
```zig
fn routerFn(msg: Message) []const u8 {
    if (std.mem.indexOf(u8, msg.content, "urgent")) |_| {
        return "fast";
    }
    return "thorough";
}

var router = try patterns.Router.init(allocator, routerFn);
defer router.deinit();

try router.addRoute("fast", fast_agent);
try router.addRoute("thorough", thorough_agent);

const result = try router.process(msg);
defer allocator.free(result.content);
```

**Python**:
```python
from agenkit.patterns import RouterAgent

def router_fn(msg: Message) -> str:
    if "urgent" in msg.content:
        return "fast"
    return "thorough"

router = RouterAgent(
    router=router_fn,
    agents={
        "fast": fast_agent,
        "thorough": thorough_agent,
    },
)

result = await router.process(msg)
```

---

## Common Gotchas

### 1. Allocator Parameters Are Gone

**Zig**: Every function needs allocator
```zig
fn createAgent(allocator: std.mem.Allocator, name: []const u8) !Agent {
    const owned_name = try allocator.dupe(u8, name);
    errdefer allocator.free(owned_name);
    // ...
}
```

**Python**: Just create objects
```python
def create_agent(name: str) -> Agent:
    # No allocator needed - memory is automatic
    return Agent(name=name)
```

**Migration**: Remove ALL allocator parameters from function signatures.

### 2. defer/errdefer → Context Managers

**Zig**: Explicit cleanup with defer
```zig
const file = try std.fs.cwd().openFile(path, .{});
defer file.close();  // Always runs

const buffer = try allocator.alloc(u8, 1024);
errdefer allocator.free(buffer);  // Only on error
```

**Python**: Context managers with `with`
```python
with open(path, 'r') as file:
    # file.close() called automatically
    data = file.read()

# For custom cleanup
from contextlib import contextmanager

@contextmanager
def managed_resource():
    resource = acquire()
    try:
        yield resource
    finally:
        release(resource)
```

**Key Insight**: Python's `with` statement is similar to Zig's `defer`, but for specific resources (files, locks, etc.). Most memory cleanup is automatic via GC.

### 3. Comptime → Runtime (Duck Typing)

**Zig**: Compile-time generics
```zig
fn process(comptime T: type, value: T) T {
    // Type-specific code generated at compile time
    return value;
}

comptime {
    if (@sizeOf(Message) > 1024) {
        @compileError("Message too large");
    }
}
```

**Python**: Runtime duck typing
```python
def process(value):
    # Type doesn't matter - just needs right methods
    return value

# No compile-time checks - duck typing at runtime
# Type hints are optional and for tools only
```

**Migration**: Remove ALL `comptime` code. Python resolves types at runtime.

### 4. Blocking Threads → async/await

**Zig**: OS threads block
```zig
const handle = try std.Thread.spawn(.{}, blockingWork, .{data});
handle.join();  // Block until thread completes
```

**Python**: Coroutines yield control
```python
task = asyncio.create_task(async_work(data))
await task  # Yield to event loop, non-blocking
```

**Key Difference**:
- Zig threads are **truly parallel** (multi-core)
- Python async is **concurrent but not parallel** (single-threaded event loop, limited by GIL)

### 5. Error Unions → Exception Handling

**Zig**: Explicit error propagation
```zig
const result = doWork() catch |err| {
    std.debug.print("Failed: {}\n", .{err});
    return err;
};
// Errors must be explicitly handled or propagated with 'try'
```

**Python**: Implicit exception propagation
```python
try:
    result = do_work()
except Exception as e:
    print(f"Failed: {e}")
    raise  # Re-raise exception
# Exceptions automatically bubble up if not caught
```

**Migration**: Replace all `try expr` with `await expr` (for async) or just `expr`. Replace all `catch |err|` blocks with `try/except`.

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

test "no memory leaks" {
    // GeneralPurposeAllocator detects leaks automatically
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer {
        const leaked = gpa.deinit();
        try testing.expect(!leaked);
    }
    const allocator = gpa.allocator();

    const msg = try createMessage(allocator, "Test");
    defer allocator.free(msg.content);
    // If we forget defer, test fails
}
```

### Python
```python
import pytest
from agenkit import Message
from myagent import MyAgent

@pytest.mark.asyncio
async def test_agent_processes_message():
    agent = MyAgent()
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Processed" in result.content
    # No memory management needed

@pytest.mark.asyncio
async def test_agent_handles_empty_message():
    agent = MyAgent()
    empty_msg = Message(role="user", content="")

    with pytest.raises(InvalidMessageError):
        await agent.process(empty_msg)

# No explicit memory leak testing - GC handles it
# Use memory profilers if needed (memory_profiler, tracemalloc)

# Fixtures for reusable setup
@pytest.fixture
def agent():
    return MyAgent()

@pytest.fixture
def sample_message():
    return Message(role="user", content="Test message")

@pytest.mark.asyncio
async def test_with_fixtures(agent, sample_message):
    result = await agent.process(sample_message)
    assert result.role == "assistant"
```

**Changes**:
- **Test syntax**: `test "name"` → `def test_name()` or `async def test_name()`
- **Async tests**: Add `@pytest.mark.asyncio` decorator
- **Setup/teardown**: `var gpa = ...; defer gpa.deinit()` → pytest fixtures
- **Assertions**: `try testing.expect(...)` → `assert ...`
- **Error testing**: `try testing.expectError(error.X, call)` → `with pytest.raises(XError)`
- **Memory leaks**: Manual leak detection → automatic (no need to test)

---

## Performance Considerations

| Operation | Zig | Python | Slowdown |
|-----------|-----|--------|----------|
| Agent creation | ~50ns | ~1μs | 20x |
| Message processing | ~500ns | ~10μs | 20x |
| Sequential (3 agents) | ~1.5μs | ~30μs | 20x |
| Parallel (3 agents) | ~5μs | ~20μs | 4x (GIL) |
| Thread/task spawn | ~10μs | ~5μs | 2x faster! |
| String formatting | ~100ns | ~500ns | 5x |
| Memory allocation | ~50ns | N/A (GC) | Hidden cost |

### Performance Impact Deep Dive

**Why Python is Slower**:
1. **Interpreted execution**: Bytecode vs native machine code
2. **Dynamic typing**: Runtime type checking overhead
3. **GC overhead**: Reference counting + cycle detection
4. **GIL (Global Interpreter Lock)**: Limits CPU-bound parallelism
5. **Boxing/unboxing**: Everything is a PyObject pointer

**Why Python Can Be Faster (Sometimes)**:
1. **asyncio.create_task()**: Lighter than spawning OS threads
2. **NumPy/C extensions**: Drop to native code for heavy computation
3. **JIT compilation**: PyPy can approach compiled speeds
4. **No compilation step**: Faster iteration during development

### When to Use Python (Migrate from Zig)

**Good reasons**:
- **Prototyping**: 10x faster development time
- **ML/AI integration**: Best ecosystem (PyTorch, TensorFlow, HuggingFace)
- **Data analysis**: pandas, NumPy, scikit-learn
- **High-level APIs**: Rapid iteration on business logic
- **Scripting**: One-off automation tasks
- **Large teams**: Easier onboarding, simpler syntax

**Bad reasons** (stay in Zig):
- Performance-critical paths (20-100x slower)
- Embedded systems (no Python runtime fits)
- Real-time systems (GC pauses unpredictable)
- Memory-constrained environments (Python uses 5-10x more RAM)
- Safety-critical systems (dynamic typing too risky)

### When to Keep Zig (Don't Migrate)

**Stay in Zig if**:
- Sub-microsecond latency requirements
- Hard real-time constraints
- Embedded or resource-constrained targets
- Single-binary deployment required
- Memory safety without GC needed
- Building systems-level infrastructure

**Consider hybrid approach**:
- Zig for performance kernels (FFI from Python)
- Python for high-level orchestration
- Example: ML inference in Zig, training in Python

---

## Migration Checklist

### Language Changes
- [ ] Remove all `std.mem.Allocator` parameters from functions
- [ ] Remove all `defer` and `errdefer` statements
- [ ] Replace `!Type` error unions with plain return types
- [ ] Change `error.Name` returns to `raise NameError(...)`
- [ ] Replace `catch |err|` blocks with `try/except`
- [ ] Remove all `comptime` code (Python is runtime)
- [ ] Change `[]const u8` to `str`, `[]T` to `List[T]`
- [ ] Change `?T` to `Optional[T]` or `T | None`

### Concurrency Changes
- [ ] Replace `std.Thread.spawn()` with `asyncio.create_task()`
- [ ] Change blocking functions to `async def`
- [ ] Replace `handle.join()` with `await task`
- [ ] Replace manual thread coordination with `asyncio.gather()`
- [ ] Replace `std.Thread.Mutex` with `asyncio.Lock()` (rarely needed)
- [ ] Remove thread-local storage (use async context instead)

### Agent Implementation
- [ ] Change `pub const MyAgent = struct` to `class MyAgent(Agent)`
- [ ] Replace `pub fn init()` with `def __init__(self)`
- [ ] Remove `pub fn deinit()` methods (automatic GC)
- [ ] Convert methods to `@property` decorators where appropriate
- [ ] Add `async` to `process()` method: `async def process()`
- [ ] Update imports: `@import("agenkit")` → `from agenkit import ...`

### Testing
- [ ] Change `test "name"` to `def test_name()` or `async def test_name()`
- [ ] Add `@pytest.mark.asyncio` to async tests
- [ ] Replace `try testing.expect()` with `assert`
- [ ] Replace `try testing.expectError()` with `with pytest.raises()`
- [ ] Remove manual memory leak tests
- [ ] Convert `defer` cleanup to pytest fixtures

### Build/Deploy
- [ ] Replace `build.zig` with `pyproject.toml` or `requirements.txt`
- [ ] Update CI/CD: `zig build test` → `pytest`
- [ ] Change deployment: single binary → Python package
- [ ] Add Python version requirements (3.10+)
- [ ] Consider Docker for consistent runtime environment

---

## Quick Start

### Project Structure Comparison

```bash
# Zig project
agenkit-zig/
├── build.zig           # Build configuration
├── src/
│   ├── main.zig
│   └── agent.zig
└── tests/
    └── test_agent.zig

# Python equivalent
agenkit/
├── pyproject.toml     # or requirements.txt
├── agenkit/
│   ├── __init__.py
│   ├── main.py
│   └── agent.py
└── tests/
    └── test_agent.py
```

### Build and Run

```bash
# Zig
zig build test          # Run tests
zig build -Doptimize=ReleaseFast  # Build optimized
./zig-out/bin/myagent   # Run binary

# Python
uv run pytest           # Run tests (preferred)
# or
python -m pytest        # Run tests

python main.py          # Run script
# or
uv run python main.py   # With uv (recommended)
```

### Example: Complete Migration

**Before (Zig)**:
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
        .content = "Hello!",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    std.debug.print("Result: {s}\n", .{result.content});
}
```

**After (Python)**:
```python
import asyncio
from agenkit import Message
from myagent import MyAgent

async def main():
    agent = MyAgent()
    msg = Message(role="user", content="Hello!")
    result = await agent.process(msg)
    print(f"Result: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Lines of code**: 22 lines (Zig) → 11 lines (Python) = 50% reduction

---

## Full Resources

- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python patterns
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples in all languages
- [Python Documentation](../agenkit/) - Full Python API reference

### External Resources

- [Zig Learn](https://ziglearn.org/) - If you need to refresh Zig concepts
- [Real Python](https://realpython.com/) - Python tutorials
- [Python asyncio docs](https://docs.python.org/3/library/asyncio.html) - Async programming guide

---

## Summary: The Big Picture

**What You Gain**:
- 50-70% less code to write and maintain
- 10x faster development iteration
- Rich ML/AI ecosystem (PyTorch, HuggingFace, etc.)
- No manual memory management
- Easy parallelism with async/await
- Massive standard library and package ecosystem

**What You Lose**:
- 20-100x performance (runtime speed)
- Compile-time guarantees (comptime, error sets)
- Sub-millisecond latency
- Explicit memory control
- Single binary deployment
- True parallelism (GIL limits CPU-bound work)

**The Sweet Spot**:
- Use Python for high-level orchestration, prototyping, ML integration
- Keep Zig for performance-critical kernels (expose via FFI if needed)
- Migrate **from** Zig **to** Python when development speed > execution speed
- Migrate **from** Python **to** Zig when execution speed becomes critical

**Common Migration Path**:
1. Start in Zig for systems-level work
2. Prototype higher-level logic in Python
3. Keep hot paths in Zig, expose via Python FFI
4. Best of both worlds: Python productivity + Zig performance

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
