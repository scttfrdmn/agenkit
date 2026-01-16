# Quick Reference: TypeScript → C++ Migration

**For**: TypeScript developers migrating Agenkit code to C++
**Time**: 15 minute read
**Full Details**: See [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) and [C++ Language Profile](LANGUAGE_PROFILE_CPP.md)

---

## Key Differences at a Glance

| Aspect | TypeScript | C++ |
|--------|------------|-----|
| **Typing** | Structural, optional | Static, explicit (templates) |
| **Errors** | Exceptions (`try/catch`) | Exceptions or `std::expected` |
| **Concurrency** | Promises/async (single-threaded) | OS threads (`std::thread`, `std::async`) |
| **Memory** | GC (V8) | Manual + RAII + smart pointers |
| **Performance** | JIT compiled (~10-20x slower) | Compiled to native (fast) |
| **Deployment** | Node.js runtime + packages | Single binary (statically linked) |

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
        confidence: 0.95,
    },
    timestamp: new Date(),
};
```

### C++
```cpp
#include <agenkit/message.hpp>

Message msg{
    .role = "user",
    .content = "Hello!",
    .metadata = {
        {"key", std::string("value")},
        {"confidence", 0.95},
    },
    .timestamp = std::chrono::system_clock::now(),
};
```

**Changes**:
- Import: `@agenkit/core` → `<agenkit/message.hpp>`
- Object literal syntax similar, but C++ uses designated initializers
- `Record<string, any>` → `std::map<std::string, std::any>`
- `Date` → `std::chrono::system_clock::time_point`
- Optional fields use `std::optional<T>`

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
        // Process message
        return {
            role: 'assistant',
            content: `Processed: ${message.content}`,
        };
    }
}
```

### C++
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public Agent {
    Config config_;

public:
    explicit MyAgent(Config config)
        : config_(std::move(config)) {}

    std::string name() const override {
        return "my-agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"text", "analysis"};
    }

    std::future<Message> process(const Message& msg) override {
        return std::async(std::launch::async, [this, msg]() {
            // Process message
            return Message{
                .role = "assistant",
                .content = "Processed: " + msg.content,
            };
        });
    }
};
```

**Changes**:
- `implements Agent` → `public Agent` (inheritance)
- `private` fields → trailing underscore convention (`config_`)
- `get name()` → `name() const override` (virtual function)
- `async/await` → `std::future<T>` with `std::async`
- Template strings → string concatenation (`+`) or `std::format`
- Constructor: member initializer list (`: config_(std::move(config))`)

---

## Error Handling

### TypeScript
```typescript
try {
    const result = await agent.process(message);
    // Use result
} catch (error) {
    if (error instanceof AgentError) {
        throw new Error(`Process failed: ${error.message}`);
    }
    throw error;
}
```

### C++ (Exceptions)
```cpp
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const AgentError& e) {
    throw std::runtime_error(
        std::string("Process failed: ") + e.what()
    );
} catch (const std::exception& e) {
    throw;  // Re-throw
}
```

### C++ (std::expected - Modern Alternative)
```cpp
#include <expected>  // C++23

std::expected<Message, AgentError> result = safe_process(agent, msg);
if (result) {
    // Success
    Message response = result.value();
} else {
    // Error
    AgentError error = result.error();
    // Handle error
}
```

**Changes**:
- `try/catch` similar in both, but C++ catches by `const&` reference
- `.get()` on `std::future` to unwrap (blocks until ready)
- C++ offers `std::expected<T, E>` for explicit error handling (like Rust's `Result`)
- Error wrapping: string concatenation vs template literals

---

## Concurrency

### TypeScript (Promises)
```typescript
// Launch async operation
const task = asyncio.createTask(async () => {
    try {
        const result = await agent.process(message);
        // Use result
    } catch (error) {
        console.error(`Error: ${error}`);
    }
});

// Wait for multiple (parallel)
const results = await Promise.all([
    agent1.process(message),
    agent2.process(message),
    agent3.process(message),
]);

// Race: first to complete
const fastest = await Promise.race([
    agent1.process(message),
    agent2.process(message),
]);
```

### C++ (std::thread, std::async)
```cpp
#include <thread>
#include <future>

// Launch thread
std::thread t([&agent, msg]() {
    try {
        Message result = agent.process(msg).get();
        // Use result
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << '\n';
    }
});
t.join();  // Wait for completion

// Wait for multiple (std::async)
auto future1 = std::async(std::launch::async, [&]() { return agent1.process(msg).get(); });
auto future2 = std::async(std::launch::async, [&]() { return agent2.process(msg).get(); });
auto future3 = std::async(std::launch::async, [&]() { return agent3.process(msg).get(); });

std::vector<Message> results{
    future1.get(),
    future2.get(),
    future3.get(),
};

// Race: use std::future::wait_for with timeout
auto future_a = std::async(std::launch::async, [&]() { return agent1.process(msg).get(); });
auto future_b = std::async(std::launch::async, [&]() { return agent2.process(msg).get(); });

// Poll with small timeout
while (true) {
    if (future_a.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) {
        return future_a.get();
    }
    if (future_b.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) {
        return future_b.get();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
}
```

**Changes**:
- `Promise` → `std::future<T>`
- `async/await` → `std::async` + `.get()` (blocking)
- `Promise.all()` → Multiple `std::future`s, call `.get()` on each
- `Promise.race()` → Manual polling with `wait_for()`
- No built-in cancellation (use custom mechanism or stop tokens)
- OS threads (heavier) vs event loop (lighter)

---

## Patterns

### Sequential

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2, agent3],
});

const result = await sequential.process(message);
```

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

### Parallel

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB, agentC],
});

const result = await parallel.process(message);
```

**C++**:
```cpp
#include <agenkit/patterns.hpp>

auto parallel = Parallel(std::vector<std::unique_ptr<Agent>>{
    std::make_unique<AgentA>(),
    std::make_unique<AgentB>(),
    std::make_unique<AgentC>(),
});

Message result = parallel.process(msg).get();
```

**Changes**:
- Constructor syntax: object literal → function call
- Agent ownership: TypeScript GC manages → C++ uses `std::unique_ptr` for ownership
- `await` → `.get()` on future

---

## Common Gotchas

### 1. Memory Management (GC → Manual)

**TypeScript**: Automatic garbage collection
```typescript
function processMessages(messages: Message[]): void {
    const results = messages.map(msg => processOne(msg));
    // 'results' automatically cleaned up when function exits
}
```

**C++**: Manual memory management with RAII
```cpp
void processMessages(const std::vector<Message>& messages) {
    std::vector<Message> results;
    for (const auto& msg : messages) {
        results.push_back(processOne(msg));
    }
    // 'results' automatically destroyed via RAII
    // But beware: raw pointers (T*) are NOT automatically cleaned!
}

// Use smart pointers for dynamic allocation
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();  // Automatic cleanup
std::shared_ptr<Agent> shared = std::make_shared<MyAgent>(); // Reference counted
```

**Key Points**:
- Stack variables cleaned up automatically (RAII)
- Heap allocations (`new`) require `delete` OR use smart pointers
- Prefer `std::unique_ptr` for single ownership
- Use `std::shared_ptr` for shared ownership (reference counted)
- Avoid raw `new/delete` in modern C++

### 2. undefined/null → std::optional/nullptr

**TypeScript**: `undefined` and `null` are special values
```typescript
function findAgent(name: string): Agent | undefined {
    return agents.find(a => a.name === name);
}

const agent = findAgent('gpt-4');
if (agent !== undefined) {
    await agent.process(message);
}
```

**C++**: Use `std::optional<T>` for missing values
```cpp
std::optional<Agent*> findAgent(const std::string& name) {
    auto it = std::find_if(agents.begin(), agents.end(),
        [&name](const auto& a) { return a->name() == name; });

    if (it != agents.end()) {
        return it->get();
    }
    return std::nullopt;
}

auto agent = findAgent("gpt-4");
if (agent.has_value()) {
    agent.value()->process(msg).get();
}
// Or more concise:
if (agent) {
    (*agent)->process(msg).get();
}
```

**Key Points**:
- `T | undefined` → `std::optional<T>`
- `null` (for pointers) → `nullptr`
- Always check before dereferencing: `if (opt) { *opt }`

### 3. Single-threaded Event Loop → OS Threads

**TypeScript**: Non-blocking I/O, single-threaded execution
```typescript
// These run concurrently but NOT in parallel (single thread)
const [r1, r2, r3] = await Promise.all([
    fetch('url1'),  // I/O, doesn't block event loop
    fetch('url2'),
    fetch('url3'),
]);
```

**C++**: True parallelism with OS threads
```cpp
// These run in parallel on different CPU cores
auto f1 = std::async(std::launch::async, []() { return fetch("url1"); });
auto f2 = std::async(std::launch::async, []() { return fetch("url2"); });
auto f3 = std::async(std::launch::async, []() { return fetch("url3"); });

std::vector<Response> results{f1.get(), f2.get(), f3.get()};
```

**Key Points**:
- TypeScript: Concurrent but not parallel (single thread)
- C++: True parallelism possible (but heavier threads)
- C++ requires thread safety (mutexes, atomics) for shared data
- TypeScript doesn't need locks (single-threaded)

### 4. Duck Typing → Static Typing

**TypeScript**: Structural typing (compile-time duck typing)
```typescript
interface Agent {
    name: string;
    process(msg: Message): Promise<Message>;
}

// Any object with these properties works
const agent = {
    name: 'custom',
    process: async (msg: Message) => ({ role: 'assistant', content: 'ok' }),
};
```

**C++**: Explicit types (inheritance or templates)
```cpp
// Option 1: Inheritance
class Agent {
public:
    virtual ~Agent() = default;
    virtual std::string name() const = 0;
    virtual std::future<Message> process(const Message&) = 0;
};

class MyAgent : public Agent { /* ... */ };

// Option 2: Templates (compile-time duck typing)
template<typename T>
concept AgentLike = requires(T a, const Message& msg) {
    { a.name() } -> std::convertible_to<std::string>;
    { a.process(msg) } -> std::same_as<std::future<Message>>;
};

template<AgentLike T>
void useAgent(T& agent) { /* ... */ }
```

**Key Points**:
- TypeScript: Structural typing (shape matters)
- C++: Nominal typing (inheritance) OR templates/concepts
- C++20 concepts provide compile-time duck typing

### 5. Package Management (npm → CMake/vcpkg)

**TypeScript**: npm/yarn/pnpm for dependencies
```bash
npm install @agenkit/core
npm install lodash axios
```

**C++**: Multiple options (CMake, vcpkg, conan)
```cmake
# CMakeLists.txt
find_package(agenkit REQUIRED)
find_package(nlohmann_json REQUIRED)

target_link_libraries(my_project
    PRIVATE
    agenkit::core
    nlohmann_json::nlohmann_json
)
```

```bash
# vcpkg
vcpkg install agenkit nlohmann-json

# conan
conan install . --build=missing
```

**Key Points**:
- No single standard package manager in C++
- CMake is de facto build system
- vcpkg and conan are popular package managers
- Header-only libraries can be included directly

---

## Testing

### TypeScript (Jest/Vitest)
```typescript
import { describe, it, expect } from 'vitest';
import { MyAgent } from './agent';

describe('MyAgent', () => {
    it('should process message correctly', async () => {
        const agent = new MyAgent();
        const msg = {
            role: 'user',
            content: 'Test',
        };

        const result = await agent.process(msg);

        expect(result.role).toBe('assistant');
        expect(result.content).toContain('Processed');
    });

    it('should throw on empty content', async () => {
        const agent = new MyAgent();
        const invalidMsg = {
            role: 'user',
            content: '',
        };

        await expect(agent.process(invalidMsg))
            .rejects
            .toThrow('Empty content');
    });
});
```

### C++ (Google Test)
```cpp
#include <gtest/gtest.h>
#include "agent.hpp"

TEST(MyAgentTest, ProcessMessage) {
    MyAgent agent;
    Message msg{
        .role = "user",
        .content = "Test",
    };

    Message result = agent.process(msg).get();

    EXPECT_EQ(result.role, "assistant");
    EXPECT_NE(result.content.find("Processed"), std::string::npos);
}

TEST(MyAgentTest, ThrowOnEmptyContent) {
    MyAgent agent;
    Message invalid_msg{
        .role = "user",
        .content = "",
    };

    EXPECT_THROW(agent.process(invalid_msg).get(), std::invalid_argument);
}
```

**Changes**:
- `describe/it` → `TEST(TestSuite, TestCase)`
- `expect(...).toBe(...)` → `EXPECT_EQ(..., ...)`
- `await expect(...).rejects.toThrow()` → `EXPECT_THROW(..., ExceptionType)`
- `.toContain()` → `.find() != std::string::npos`
- No async needed (tests are synchronous, use `.get()` on futures)

---

## Performance Considerations

| Operation | TypeScript | C++ | Speedup |
|-----------|------------|-----|---------|
| Agent creation | ~1μs | ~50ns | 20x |
| Message processing | ~10μs | ~500ns | 20x |
| Sequential (3 agents) | ~30μs | ~1.5μs | 20x |
| Parallel (3 agents) | ~20μs | ~500ns | 40x |
| Memory overhead | High (V8 + GC) | Low (native) | 5-10x |

**When to use C++**:
- Performance-critical applications (latency, throughput)
- Resource-constrained environments (embedded, edge)
- Native desktop applications
- Games, real-time systems
- Single-binary deployment (no runtime dependency)
- High-frequency trading, HPC, systems programming

**When to stay with TypeScript**:
- Web applications (frontend, backend)
- Rapid prototyping
- Node.js ecosystem integration
- Full-stack JavaScript teams
- Cross-platform web deployment
- When development speed > runtime speed

---

## Migration Checklist

- [ ] Replace `class implements Interface` with `class : public Interface`
- [ ] Convert `Promise<T>` to `std::future<T>`
- [ ] Change `async/await` to `std::async` + `.get()`
- [ ] Add memory management: use smart pointers (`std::unique_ptr`, `std::shared_ptr`)
- [ ] Replace `undefined/null` with `std::optional<T>` or `nullptr`
- [ ] Update imports: `@agenkit/core` → `<agenkit/message.hpp>`
- [ ] Convert object literals to designated initializers or constructors
- [ ] Replace template strings with string concatenation or `std::format`
- [ ] Change error handling: `try/catch` similar, but consider `std::expected`
- [ ] Update tests: Jest/Vitest → Google Test
- [ ] Setup build system: package.json → CMakeLists.txt
- [ ] Handle thread safety: add mutexes for shared mutable state
- [ ] Replace `Array<T>` with `std::vector<T>`
- [ ] Replace `Map<K, V>` with `std::map<K, V>` or `std::unordered_map<K, V>`
- [ ] Replace `Set<T>` with `std::set<T>` or `std::unordered_set<T>`

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

# C++ equivalent
agenkit-cpp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── agent.cpp
├── include/
│   └── agent.hpp
└── tests/
    └── agent_test.cpp
```

**Build/Run**:
```bash
# TypeScript
npm install
npm run build
node dist/index.js

# C++
mkdir build && cd build
cmake ..
cmake --build .
./my_agent
```

**Testing**:
```bash
# TypeScript
npm test

# C++
cd build
ctest
# Or run directly
./tests/agent_test
```

---

## Full Resources

- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms guide
- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [C++ Reference](https://en.cppreference.com/) - Comprehensive C++ reference
- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/) - Modern C++ best practices
- [Agenkit C++ Examples](../agenkit-cpp/examples/) - Side-by-side code samples
- [Main Migration Guide](MIGRATION.md) - Python → All languages

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
