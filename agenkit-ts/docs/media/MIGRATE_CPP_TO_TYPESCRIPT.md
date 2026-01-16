# Quick Reference: C++ → TypeScript Migration

**For**: C++ developers migrating Agenkit code to TypeScript
**Time**: 15 minute read
**Full Details**: See [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) and [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md)

---

## Key Differences at a Glance

| Aspect | C++ | TypeScript |
|--------|-----|------------|
| **Typing** | Static, explicit templates | Static, structural with inference |
| **Memory** | Manual + RAII (smart ptrs) | Automatic GC (V8) |
| **Errors** | Exceptions or `std::expected` | Exceptions (`try/catch`) |
| **Concurrency** | OS threads (`std::thread`) | Event loop (Promises/async) |
| **Performance** | Native, compiled (~50ns ops) | JIT, interpreted (~500ns ops) |
| **Deployment** | Platform binaries | Universal (browser + Node.js) |

---

## Message Creation

### C++
```cpp
#include <agenkit/message.hpp>

// Designated initializers (C++20)
Message msg{
    .role = "user",
    .content = "Hello!",
    .metadata = {
        {"confidence", 0.95},
        {"model", "gpt-4"},
    },
};

// Constructor
Message msg2("user", "Hello!");
```

### TypeScript
```typescript
import { Message } from '@agenkit/core';

// Object literal
const msg: Message = {
    role: 'user',
    content: 'Hello!',
    metadata: {
        confidence: 0.95,
        model: 'gpt-4',
    },
};
```

**Changes**:
- `#include` → `import` with ES modules
- Designated initializers → Object literals
- `std::map<std::string, std::any>` → `Record<string, any>`
- Optional: `std::optional<T>` → `T | undefined`
- No explicit types needed (inference)

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

    ~MyAgent() override = default;  // Virtual destructor

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

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    constructor(private config: Config) {}

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

**Changes**:
- Abstract base class → Interface implementation
- Explicit destructor → Not needed (GC)
- `const` methods → Not needed (TS has no const methods)
- `std::future<T>` → `Promise<T>`
- `std::async` → `async/await` (automatic)
- `override` keyword → Not needed
- Move semantics → Not applicable (GC handles memory)
- `std::vector<T>` → `T[]` or `Array<T>`

---

## Error Handling

### C++
```cpp
// Traditional exceptions
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const std::runtime_error& e) {
    std::cerr << "Runtime error: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}

// Modern Result type (C++23)
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

// Usage
auto result = safe_process(agent, msg);
if (result) {
    Message response = result.value();
} else {
    AgentError error = result.error();
}
```

### TypeScript
```typescript
// Try-catch (similar to C++ exceptions)
try {
    const result = await agent.process(message);
    // Use result
} catch (error) {
    if (error instanceof AgentError) {
        console.error(`Agent error: ${error.message}`);
    } else if (error instanceof Error) {
        console.error(`Error: ${error.message}`);
    } else {
        throw error;  // Re-throw unknown errors
    }
}

// Result type pattern (optional, using custom type)
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

function safeProcess(
    agent: Agent,
    msg: Message
): Promise<Result<Message, AgentError>> {
    if (msg.content === '') {
        return Promise.resolve({
            ok: false,
            error: new AgentError('InvalidMessage'),
        });
    }

    return agent.process(msg)
        .then(value => ({ ok: true, value }))
        .catch(error => ({ ok: false, error }));
}

// Usage
const result = await safeProcess(agent, msg);
if (result.ok) {
    const response = result.value;
} else {
    const error = result.error;
}
```

**Changes**:
- `catch (const Type& e)` → `catch (error)` with `instanceof` checks
- `e.what()` → `error.message`
- `std::expected<T, E>` → Custom `Result<T, E>` type or direct exceptions
- `.value()` / `.error()` → `.value` / `.error` (properties, not methods)
- Exception safety easier (GC prevents leaks)

---

## Concurrency

### C++ (OS Threads)
```cpp
#include <thread>
#include <future>

// Spawn thread
std::thread t([]() {
    auto result = agent.process(msg).get();
    // Use result
});
t.join();

// Async with future
std::future<Message> future = std::async(
    std::launch::async,
    [&agent, msg]() {
        return agent.process(msg).get();
    }
);
Message result = future.get();  // Blocks

// Wait for multiple (manual)
std::vector<std::future<Message>> futures;
for (const auto& agent : agents) {
    futures.push_back(std::async(std::launch::async, [&agent, msg]() {
        return agent.process(msg).get();
    }));
}

std::vector<Message> results;
for (auto& future : futures) {
    results.push_back(future.get());
}
```

### TypeScript (Event Loop)
```typescript
// Launch async operation (non-blocking)
const processAsync = async () => {
    const result = await agent.process(message);
    // Use result
};

// Create task (doesn't block)
const task = processAsync();  // Returns Promise

// Await result (blocks current async context)
const result = await agent.process(message);

// Wait for multiple (parallel execution)
const results = await Promise.all(
    agents.map(agent => agent.process(message))
);

// Race: first to complete
const fastest = await Promise.race(
    agents.map(agent => agent.process(message))
);
```

**Changes**:
- `std::thread` → Not applicable (single-threaded runtime)
- `std::async` + `std::future` → `async` functions + `Promise`
- `.get()` blocking → `await` (yields to event loop)
- Thread joining → Promise resolution
- OS-level parallelism → Concurrent I/O only
- `std::mutex` → Not needed (single-threaded)
- Thread pool → Event loop (built-in)

**Important**: TypeScript is **single-threaded** (except Web Workers). Multiple Promises run concurrently but NOT in parallel.

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

std::future<Message> future = sequential.process(msg);
Message result = future.get();
```

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2, agent3],
});

const result = await sequential.process(message);
```

### Parallel

**C++**:
```cpp
auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
    std::make_unique<AgentC>(),
});

std::future<Message> future = parallel.process(msg);
Message result = future.get();
```

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB, agentC],
});

const result = await parallel.process(message);
```

### Router

**C++**:
```cpp
auto router = Router(
    [](const Message& msg) -> std::string {
        return msg.content.find("urgent") != std::string::npos
            ? "fast"
            : "thorough";
    },
    {
        {"fast", std::move(sequential)},
        {"thorough", std::move(parallel)},
    }
);
```

**TypeScript**:
```typescript
import { RouterAgent } from '@agenkit/patterns';

const router = new RouterAgent({
    router: (msg: Message) => {
        return msg.content.includes('urgent') ? 'fast' : 'thorough';
    },
    agents: {
        fast: sequential,
        thorough: parallel,
    },
});
```

**Changes**:
- `std::vector<std::unique_ptr<T>>` → `T[]` (no ownership concerns)
- `std::make_unique` → `new` (GC handles cleanup)
- `std::move` → Not needed (GC, references)
- `.find() != npos` → `.includes()`
- Lambda capture `[=]` or `[&]` → Automatic closure capture

---

## Common Gotchas

### 1. No True Parallelism (Single-Threaded)

**C++**: Multiple threads run simultaneously on multiple cores
```cpp
// These run in parallel on separate CPU cores
std::thread t1(heavy_computation1);
std::thread t2(heavy_computation2);
std::thread t3(heavy_computation3);
t1.join(); t2.join(); t3.join();
```

**TypeScript**: Event loop is single-threaded, only I/O is concurrent
```typescript
// These DON'T run in parallel (event loop is single-threaded)
// CPU-bound work blocks the event loop
await Promise.all([
    heavyComputation1(),  // Blocks event loop
    heavyComputation2(),  // Must wait for 1
    heavyComputation3(),  // Must wait for 2
]);

// I/O operations ARE concurrent (don't block event loop)
await Promise.all([
    fetchFromAPI1(),  // Concurrent I/O
    fetchFromAPI2(),  // Concurrent I/O
    fetchFromAPI3(),  // Concurrent I/O
]);
```

**Migration Impact**: 10-20x performance loss for CPU-bound parallel workloads. Consider Web Workers for true parallelism.

### 2. Memory Management Philosophy

**C++**: Explicit ownership, RAII, move semantics
```cpp
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();
std::unique_ptr<Agent> moved = std::move(agent);  // Transfer ownership
// agent is now nullptr
```

**TypeScript**: Garbage collection, no ownership concept
```typescript
let agent: Agent = new MyAgent();
let reference = agent;  // Both point to same object
agent = null;  // Object still alive (reference exists)
reference = null;  // Now GC can collect
```

**Gotcha**: No destructors in TypeScript. Use explicit cleanup methods if needed.

```typescript
class MyAgent implements Agent {
    private connection: Connection;

    async cleanup(): Promise<void> {
        await this.connection.close();
    }
}

// Must call cleanup explicitly
await agent.cleanup();
```

### 3. Type System Differences

**C++**: Nominal typing (types must match by name)
```cpp
class MessageA { std::string content; };
class MessageB { std::string content; };

void process(const MessageA& msg);
process(MessageB{});  // ERROR: types don't match
```

**TypeScript**: Structural typing (types match by shape)
```typescript
interface MessageA { content: string; }
interface MessageB { content: string; }

function process(msg: MessageA): void {}
process({ content: 'test' } as MessageB);  // OK: same shape
```

**Gotcha**: TypeScript accepts any object with the right shape, even if it has extra properties.

### 4. Template vs Generic Type Erasure

**C++**: Templates generate code at compile time (monomorphization)
```cpp
template<typename T>
T identity(T value) {
    return value;
}

identity(42);        // Generates identity<int>
identity("hello");   // Generates identity<const char*>
// Two separate functions in binary
```

**TypeScript**: Generics erased at runtime (JavaScript doesn't have types)
```typescript
function identity<T>(value: T): T {
    return value;
}

identity(42);        // Same function as...
identity("hello");   // ...this at runtime
// Type information gone after compilation
```

**Gotcha**: Can't use type parameters at runtime in TypeScript.

```typescript
function create<T>(): T {
    return new T();  // ERROR: T doesn't exist at runtime
}
```

### 5. Async is Viral

**C++**: Can mix sync and async freely
```cpp
Message sync_call() {
    std::future<Message> future = agent.process(msg);
    return future.get();  // Block until ready
}
```

**TypeScript**: Once async, always async
```typescript
// If you call async function, YOU become async
async function syncCall(): Promise<Message> {  // Must return Promise
    return await agent.process(message);  // Must await
}

// Can't "de-async" without blocking event loop (bad practice)
function badSyncCall(): Message {
    agent.process(message);  // Returns Promise<Message>, not Message
    // No way to get Message synchronously
}
```

**Gotcha**: Async propagates up the call stack. Design async boundaries carefully.

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
    Message empty{.role = "user", .content = ""};

    EXPECT_THROW(agent.process(empty).get(), std::invalid_argument);
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
            .toThrow('Empty content');
    });
});
```

**Changes**:
- `TEST(Suite, Name)` → `describe()`/`it()` blocks
- `EXPECT_EQ` / `EXPECT_TRUE` → `expect().toBe()` / `.toContain()`
- `EXPECT_THROW` → `expect().rejects.toThrow()`
- `.get()` blocking → `await` in async tests
- Google Test → Jest/Vitest (framework choice)

---

## Performance Considerations

| Operation | C++ | TypeScript | Slowdown |
|-----------|-----|------------|----------|
| Message creation | ~50ns | ~500ns | 10x |
| Agent process (mock) | ~500ns | ~5μs | 10x |
| Sequential (3 agents) | ~1.5μs | ~15μs | 10x |
| Parallel (3 agents) | ~500ns | ~5μs | 10x |
| Thread/Promise spawn | ~5μs | ~1μs | TS faster! |

**Notes**:
- TypeScript Promise creation is faster than C++ thread creation
- TypeScript has ~10x overhead for compute operations
- C++ has true parallelism; TypeScript doesn't (except I/O)
- TypeScript excels at I/O-bound workloads (non-blocking)

**When to migrate C++ → TypeScript**:
- Web deployment (browser + Node.js)
- Cross-platform without recompilation
- Rapid prototyping / iteration speed
- Integration with JavaScript ecosystem
- I/O-bound workloads (network, file system)
- Universal deployment (same code everywhere)

**When to keep C++**:
- CPU-bound parallel workloads
- Real-time systems (predictable latency)
- Memory-constrained environments
- Maximum performance requirements
- Low-level system access needed
- Existing C++ codebase integration

---

## Migration Checklist

- [ ] Replace `#include` with ES module `import`
- [ ] Convert classes: remove destructors, move semantics
- [ ] Change `std::future<T>` to `Promise<T>` + `async/await`
- [ ] Remove `std::thread` / `std::async` (use Promises)
- [ ] Update error handling: similar `try/catch`, but check with `instanceof`
- [ ] Replace smart pointers (`std::unique_ptr`) with plain references (GC)
- [ ] Convert STL containers: `std::vector<T>` → `T[]`, `std::map` → `Map` or object
- [ ] Remove manual memory management (new/delete, RAII)
- [ ] Update build system: CMake → npm/tsconfig.json
- [ ] Change test framework: Google Test → Jest/Vitest
- [ ] Adapt to single-threaded model (event loop)
- [ ] Replace templates with generics (simpler, runtime type erasure)
- [ ] Add explicit cleanup methods (no destructors)

---

## Quick Start

```bash
# C++ project structure
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── agent.cpp
├── include/
│   └── agent.hpp
└── build/

# TypeScript equivalent
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── main.ts
│   └── agent.ts
└── dist/          # Compiled output
```

**Build/Run**:
```bash
# C++
mkdir build && cd build
cmake ..
make
./myagent

# TypeScript
npm install
npm run build    # Compile TypeScript
npm start        # Run compiled JS
# or
npm run dev      # Run with ts-node (no compilation)
```

---

## Memory Model Migration

### C++ Manual + RAII
```cpp
class Agent {
    std::unique_ptr<Connection> conn_;  // Owned
    Config* config_;                     // Borrowed
public:
    Agent(Config* config) : config_(config) {
        conn_ = std::make_unique<Connection>();
    }
    ~Agent() {
        // conn_ automatically freed
        // config_ NOT freed (borrowed)
    }
};
```

### TypeScript GC
```typescript
class Agent {
    private conn: Connection;  // Reference
    private config: Config;    // Reference

    constructor(config: Config) {
        this.config = config;
        this.conn = new Connection();
    }

    // No destructor needed - GC handles cleanup
    // Call explicit cleanup if needed
    async dispose(): Promise<void> {
        await this.conn.close();
    }
}
```

**Key Differences**:
- No ownership tracking in TypeScript (GC figures it out)
- No move semantics (copying is reference copying)
- No RAII (but can use `finally` blocks)
- Explicit `dispose()` pattern for resources

---

## Concurrency Model Deep Dive

### C++ Multi-Threading
```cpp
// CPU-bound work runs in parallel
std::vector<std::thread> threads;
for (int i = 0; i < 4; ++i) {
    threads.emplace_back([i]() {
        heavy_computation(i);  // Runs on separate core
    });
}
for (auto& t : threads) {
    t.join();
}

// Need mutex for shared state
std::mutex mtx;
std::map<std::string, int> shared_map;

void update(const std::string& key) {
    std::lock_guard<std::mutex> lock(mtx);
    shared_map[key]++;
}
```

### TypeScript Event Loop
```typescript
// CPU-bound work blocks event loop
const promises = [];
for (let i = 0; i < 4; i++) {
    promises.push(heavyComputation(i));  // Queued, runs sequentially
}
await Promise.all(promises);  // Not parallel (single-threaded)

// I/O work is concurrent (doesn't block)
const ioPromises = [];
for (let i = 0; i < 4; i++) {
    ioPromises.push(fetchFromNetwork(i));  // Truly concurrent
}
await Promise.all(ioPromises);  // All in flight at once

// No mutex needed (single-threaded)
const sharedMap = new Map<string, number>();

function update(key: string): void {
    sharedMap.set(key, (sharedMap.get(key) || 0) + 1);
    // No race conditions (single-threaded)
}
```

**Migration Strategy**:
- CPU-bound parallel work: Consider keeping C++ or use Web Workers
- I/O-bound work: TypeScript excels here
- Shared state: Simpler in TypeScript (no synchronization)

---

## Type System Migration

### C++ Templates (Compile-Time)
```cpp
template<typename T>
class Container {
    std::vector<T> items;
public:
    void add(const T& item) {
        items.push_back(item);
    }

    T get(size_t index) const {
        return items.at(index);
    }
};

// Instantiated at compile time
Container<int> int_container;       // Generates Container<int>
Container<std::string> str_container;  // Generates Container<std::string>
```

### TypeScript Generics (Type Erasure)
```typescript
class Container<T> {
    private items: T[] = [];

    add(item: T): void {
        this.items.push(item);
    }

    get(index: number): T {
        return this.items[index];
    }
}

// Single implementation at runtime
const intContainer = new Container<number>();
const strContainer = new Container<string>();
// Both use same JavaScript code
```

**Migration Notes**:
- C++ templates → TypeScript generics (much simpler)
- SFINAE / concepts → TypeScript constraints (`extends`)
- No template metaprogramming in TypeScript
- Type information unavailable at runtime

---

## Full Resources

- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms guide
- [Agenkit TypeScript Documentation](../agenkit-ts/) - Full API reference
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [Main Migration Guide](MIGRATION.md) - Python → All languages

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
