# Quick Reference: C++ → Python Migration

**For**: C++ developers migrating Agenkit code to Python
**Time**: 15 minute read
**Full Details**: See [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) and [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md)

---

## Key Differences at a Glance

| Aspect | C++ | Python |
|--------|-----|--------|
| **Typing** | Static, compile-time | Dynamic, runtime with optional hints |
| **Memory** | Manual + RAII, smart pointers | GC + refcounting, automatic |
| **Errors** | Exceptions or `std::expected` | Exceptions (`try/except`) |
| **Concurrency** | OS threads (`std::thread`) | Event loop (`async/await`) |
| **Performance** | Very fast (compiled, zero-overhead) | Slower (interpreted, 20-100x) |
| **Compilation** | Required (slow builds) | None (interpreted) |
| **Deployment** | Single binary | Interpreter + packages |

---

## Message Creation

### C++
```cpp
#include <agenkit/message.hpp>

// Struct with designated initializers
Message msg{
    .role = "user",
    .content = "Hello!",
    .metadata = {
        {"key", "value"},
        {"confidence", 0.95},
    },
};

// Or with builder
auto msg = MessageBuilder()
    .role("user")
    .content("Hello!")
    .metadata("key", "value")
    .build();
```

### Python
```python
from agenkit import Message

# Constructor with keyword arguments
msg = Message(
    role="user",
    content="Hello!",
    metadata={
        "key": "value",
        "confidence": 0.95,
    }
)
```

**Changes**:
- Struct literal → Constructor call
- Designated initializers (`{}`) → Keyword arguments
- Type: `std::map<std::string, std::any>` → `dict`
- No need for explicit type declarations
- Builder pattern less common in Python

---

## Agent Implementation

### C++
```cpp
#include <agenkit/agent.hpp>
#include <future>

class MyAgent : public Agent {
    std::string name_;
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

### Python
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    def __init__(self, config: dict):
        self.config = config

    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        # Process message
        return Message(
            role="assistant",
            content=f"Processed: {message.content}"
        )
```

**Changes**:
- Abstract base class → Regular class (duck typing)
- Constructor: explicit initializer list → `__init__` method
- Getter methods → `@property` decorators
- `std::future` + `std::async` → `async def` with `await`
- `const` correctness → Not needed in Python
- Move semantics (`std::move`) → Not needed (automatic GC)
- Type annotations optional but recommended

---

## Error Handling

### C++
```cpp
// Using exceptions
try {
    Message result = agent.process(msg).get();
    // Use result
} catch (const std::invalid_argument& e) {
    std::cerr << "Invalid argument: " << e.what() << '\n';
} catch (const std::runtime_error& e) {
    std::cerr << "Runtime error: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}

// Or using std::expected (C++23)
auto result = process_message(agent, msg);
if (result) {
    Message response = result.value();
} else {
    AgentError error = result.error();
    // Handle error
}
```

### Python
```python
# Using exceptions (similar!)
try:
    result = await agent.process(message)
    # Use result
except ValueError as e:
    print(f"Invalid argument: {e}")
except RuntimeError as e:
    print(f"Runtime error: {e}")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Optional cleanup (always runs)
    await cleanup()
```

**Changes**:
- `.get()` call removed (no future unwrapping needed)
- `const` references → Not needed
- `std::cerr` → `print()` or proper logging
- `e.what()` → `str(e)` or just `e` in f-strings
- `std::expected` → Not available (use exceptions)
- Exception hierarchy similar (both use inheritance)
- `finally` block available for cleanup (like destructors)

---

## Memory Management

### C++ (Manual + RAII)
```cpp
// Smart pointers for ownership
std::unique_ptr<Agent> agent = std::make_unique<MyAgent>();

// Shared ownership
std::shared_ptr<Agent> shared = std::make_shared<MyAgent>();
std::shared_ptr<Agent> copy = shared;  // Reference counted

// Weak reference
std::weak_ptr<Agent> weak = shared;
if (auto locked = weak.lock()) {
    locked->process(msg);
}

// RAII: Resource cleanup in destructor
class Handler {
    std::FILE* file_;
public:
    Handler(const char* path) : file_(std::fopen(path, "r")) {}
    ~Handler() { if (file_) std::fclose(file_); }
};
```

### Python (Automatic GC)
```python
# No memory management needed
agent = MyAgent()  # Automatically garbage collected

# Multiple references (automatic refcounting)
shared = agent
copy = agent  # Same object, refcount increased

# Weak reference (if needed)
import weakref
weak = weakref.ref(agent)
if weak() is not None:
    weak().process(message)

# Context manager for resources (like RAII)
with open('file.txt', 'r') as file:
    data = file.read()
# File automatically closed (like destructor)

# Async context manager
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.text()
```

**Changes**:
- `std::unique_ptr`/`std::shared_ptr` → Not needed (automatic GC)
- `std::weak_ptr` → `weakref.ref()` (rarely needed)
- RAII destructors → Context managers (`with` statement)
- Move semantics → Not needed (GC handles everything)
- Manual `new`/`delete` → Never needed
- Resource cleanup: Deterministic (RAII) → Context managers or GC

---

## Concurrency

### C++ (OS Threads)
```cpp
#include <thread>
#include <future>
#include <vector>

// Spawn thread
std::thread t([]() {
    auto result = agent.process(msg).get();
    // Use result
});
t.join();  // Wait for completion

// Async with futures
std::vector<std::future<Message>> futures;
for (auto& agent : agents) {
    futures.push_back(std::async(std::launch::async, [&]() {
        return agent.process(msg).get();
    }));
}

// Collect results
std::vector<Message> results;
for (auto& future : futures) {
    results.push_back(future.get());
}

// Mutex for synchronization
std::mutex mtx;
std::lock_guard<std::mutex> lock(mtx);
// Critical section
```

### Python (Event Loop)
```python
import asyncio

# Create coroutine task
task = asyncio.create_task(agent.process(message))
result = await task  # Wait for completion

# Gather multiple coroutines (parallel execution)
results = await asyncio.gather(
    agent1.process(message),
    agent2.process(message),
    agent3.process(message),
)

# Or using list comprehension
results = await asyncio.gather(*[
    agent.process(message)
    for agent in agents
])

# Lock for synchronization
lock = asyncio.Lock()
async with lock:
    # Critical section
    shared_resource.modify()
```

**Changes**:
- `std::thread` → `asyncio.create_task()`
- `std::async` + `std::future` → `async def` + `await`
- `.join()` / `.get()` → `await`
- Multiple threads → Single event loop (cooperative multitasking)
- `std::mutex` → `asyncio.Lock()`
- Thread pool → Not needed (event loop handles scheduling)
- True parallelism (multi-core) → Concurrent but single-threaded (GIL)
- Heavy OS threads → Lightweight coroutines

---

## Type System

### C++ (Static + Templates)
```cpp
// Static typing with templates
template<typename T>
class Result {
    std::variant<T, std::exception_ptr> data_;
public:
    bool is_ok() const;
    T unwrap();
};

// Concepts (C++20)
template<typename T>
concept AgentLike = requires(T a, const Message& msg) {
    { a.name() } -> std::convertible_to<std::string>;
    { a.process(msg) } -> std::same_as<std::future<Message>>;
};

template<AgentLike A>
Message process_with(A& agent, const Message& msg) {
    return agent.process(msg).get();
}

// Compile-time type checking
std::optional<std::string> get_value();
auto value = get_value();
if (value.has_value()) {
    std::cout << *value << '\n';  // Explicit unwrap
}
```

### Python (Dynamic + Duck Typing)
```python
from typing import Optional, Protocol, Generic, TypeVar

# Duck typing (runtime checked)
class AgentLike(Protocol):
    @property
    def name(self) -> str: ...

    async def process(self, msg: Message) -> Message: ...

def process_with(agent: AgentLike, msg: Message) -> Message:
    return await agent.process(msg)  # No type check at runtime

# Optional type hints
def get_value() -> Optional[str]:
    return "value" if condition else None

value = get_value()
if value is not None:
    print(value)  # Type checker understands narrowing

# Generic types
T = TypeVar('T')

class Result(Generic[T]):
    def __init__(self, value: T | Exception):
        self.value = value

    def is_ok(self) -> bool:
        return not isinstance(self.value, Exception)

    def unwrap(self) -> T:
        if isinstance(self.value, Exception):
            raise self.value
        return self.value
```

**Changes**:
- Templates → Generics (runtime, not compile-time)
- Concepts → Protocols (duck typing, runtime checked)
- `std::optional<T>` → `Optional[T]` or `T | None`
- `std::variant<T, E>` → Union types or class hierarchy
- Type safety: Compile-time → Runtime (with optional static analysis)
- `.has_value()` / `*value` → `is not None` / direct access
- Explicit instantiation → Duck typing (works if methods exist)

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

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[
    Agent1(),
    Agent2(),
    Agent3(),
])

result = await sequential.process(message)
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

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[
    AgentA(),
    AgentB(),
    AgentC(),
])

result = await parallel.process(message)
```

### Router

**C++**:
```cpp
auto router = Router(
    [](const Message& msg) -> std::string {
        return msg.content.find("urgent") != std::string::npos
            ? "fast" : "thorough";
    },
    {
        {"fast", std::move(fast_agent)},
        {"thorough", std::move(thorough_agent)},
    }
);
```

**Python**:
```python
from agenkit.patterns import RouterAgent

def router_fn(msg: Message) -> str:
    return "fast" if "urgent" in msg.content else "thorough"

router = RouterAgent(
    router=router_fn,
    agents={
        "fast": fast_agent,
        "thorough": thorough_agent,
    }
)
```

---

## Common Gotchas

### 1. Memory Management Philosophy

**C++**: Manual control with RAII
```cpp
// Need to think about ownership
std::unique_ptr<Agent> agent = create_agent();  // Owns
Agent* raw = agent.get();  // Borrows, doesn't own

// Move semantics required
std::vector<std::unique_ptr<Agent>> agents;
agents.push_back(std::move(agent));  // Explicit move
```

**Python**: Automatic, zero thought
```python
# Never think about memory
agent = create_agent()  # GC handles it
raw = agent  # Another reference, refcount++

# No move semantics needed
agents = []
agents.append(agent)  # Just works
```

**Impact**: C++ developers need to stop thinking about memory management. Python handles it automatically. No smart pointers, no move semantics, no ownership concerns.

### 2. Const Correctness

**C++**: Explicit const everywhere
```cpp
void process(const Message& msg) const {  // const method, const ref
    // msg.content cannot be modified
    // 'this' is const (cannot modify members)
}

const auto& agents = get_agents();  // const reference
```

**Python**: No const keyword
```python
def process(self, message: Message) -> Message:
    # message can be modified (no const enforcement)
    # Convention: don't modify unless documented
    pass

agents = get_agents()  # No const
# Immutability through conventions or immutable types (tuple, frozenset)
```

**Impact**: Python relies on conventions, not language enforcement. Use immutable types (tuples, named tuples, frozen dataclasses) when immutability is important.

### 3. Compile-Time vs Runtime Errors

**C++**: Most errors caught at compile time
```cpp
template<AgentLike A>
void process(A& agent) {
    agent.process(msg);  // Compile error if method doesn't exist
}

std::optional<int> value = get_value();
std::cout << value;  // Compile error: cannot print optional directly
```

**Python**: Most errors caught at runtime
```python
def process(agent):
    agent.process(msg)  # Runtime error if method doesn't exist
    # (unless using type checker like mypy)

value: Optional[int] = get_value()
print(value)  # Works at runtime even if None (might not be intended)
```

**Impact**: Use type hints + mypy for static analysis. Write more tests to catch runtime errors. Defensive programming more important.

### 4. Concurrency Model

**C++**: True parallelism, multiple CPU cores
```cpp
// These truly run in parallel on different cores
std::vector<std::future<void>> futures;
for (int i = 0; i < 10; ++i) {
    futures.push_back(std::async(std::launch::async, cpu_bound_work));
}
// All 10 tasks use separate CPU cores
```

**Python**: Concurrent but not parallel (GIL)
```python
# These are concurrent but NOT parallel (due to GIL)
tasks = []
for i in range(10):
    tasks.append(asyncio.create_task(cpu_bound_work()))
await asyncio.gather(*tasks)
# All 10 tasks share one CPU core (cooperative multitasking)

# For true parallelism, need multiprocessing
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor() as executor:
    results = list(executor.map(cpu_bound_work, range(10)))
# Now uses multiple CPU cores (separate processes)
```

**Impact**: Python's `async/await` is for I/O-bound work, not CPU-bound. For CPU-intensive tasks, use `multiprocessing` or migrate to C++/Go/Rust.

### 5. Error Handling Similarity (But Different!)

**C++**: Exceptions similar but with RAII cleanup
```cpp
std::unique_ptr<Resource> resource;
try {
    resource = std::make_unique<Resource>();
    process(resource.get());
} catch (const std::exception& e) {
    // resource automatically destroyed even if exception thrown
    std::cerr << "Error: " << e.what() << '\n';
}
```

**Python**: Exceptions but need explicit cleanup
```python
resource = None
try:
    resource = Resource()
    process(resource)
except Exception as e:
    print(f"Error: {e}")
finally:
    # Need explicit cleanup in finally block
    if resource:
        resource.close()

# Better: use context manager
try:
    with Resource() as resource:
        process(resource)
        # Automatic cleanup even on exception
except Exception as e:
    print(f"Error: {e}")
```

**Impact**: Use context managers (`with` statement) for resources. They're Python's equivalent to RAII destructors.

---

## Testing

### C++ (Google Test)
```cpp
#include <gtest/gtest.h>

TEST(MyAgentTest, ProcessMessage) {
    MyAgent agent;
    Message msg{.role = "user", .content = "Test"};

    auto result = agent.process(msg).get();

    EXPECT_EQ(result.role, "assistant");
    EXPECT_TRUE(result.content.find("Processed") != std::string::npos);
}

TEST(MyAgentTest, HandleEmptyMessage) {
    MyAgent agent;
    Message empty_msg{.role = "user", .content = ""};

    EXPECT_THROW(agent.process(empty_msg).get(), std::invalid_argument);
}

// Benchmark
#include <benchmark/benchmark.h>

static void BM_AgentProcess(benchmark::State& state) {
    MyAgent agent;
    Message msg{.role = "user", .content = "Test"};

    for (auto _ : state) {
        auto result = agent.process(msg).get();
        benchmark::DoNotOptimize(result);
    }
}
BENCHMARK(BM_AgentProcess);
```

### Python (pytest)
```python
import pytest
from agenkit import Message
from myagent import MyAgent

@pytest.mark.asyncio
async def test_agent_process():
    agent = MyAgent()
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Processed" in result.content

@pytest.mark.asyncio
async def test_agent_handles_empty_message():
    agent = MyAgent()
    empty_msg = Message(role="user", content="")

    with pytest.raises(ValueError):
        await agent.process(empty_msg)

# Fixtures for reusable setup
@pytest.fixture
def agent():
    return MyAgent()

@pytest.fixture
def sample_message():
    return Message(role="user", content="Test")

# Benchmark (using pytest-benchmark)
def test_agent_process_benchmark(benchmark, agent, sample_message):
    result = benchmark(lambda: asyncio.run(agent.process(sample_message)))
    assert result.role == "assistant"
```

**Changes**:
- `TEST()` macro → `def test_*()` functions
- `EXPECT_*` / `ASSERT_*` → `assert` statements
- `EXPECT_THROW` → `pytest.raises()`
- `.get()` removed (no future unwrapping)
- `@pytest.mark.asyncio` decorator for async tests
- Fixtures for setup/teardown (more flexible than C++)
- Benchmarking: Google Benchmark → pytest-benchmark

---

## Performance Considerations

| Operation | C++ | Python | Ratio |
|-----------|-----|--------|-------|
| Agent creation | ~50ns | ~1μs | 20x slower |
| Message processing | ~500ns | ~10μs | 20x slower |
| Sequential (3 agents) | ~1.5μs | ~30μs | 20x slower |
| Parallel (3 agents) | ~500ns | ~20μs | 40x slower |
| Thread spawn | ~5μs | ~5μs (task) | Comparable |
| Memory usage | Low (precise control) | High (GC overhead) | 2-5x more |

**When to use Python** (migrate FROM C++):
- **Prototyping and experimentation**: Faster iteration, no compilation
- **ML/AI integration**: Best ecosystem (PyTorch, TensorFlow, NumPy, pandas)
- **Data science**: Jupyter notebooks, visualization, pandas
- **Scripting and automation**: Quick one-off tasks
- **Easier maintenance**: Simpler codebase, less cognitive overhead
- **Rapid development**: Build features 2-5x faster

**When to keep C++** (DON'T migrate):
- **Performance-critical production**: 20-100x faster execution
- **Real-time systems**: Deterministic performance, no GC pauses
- **High concurrency**: True parallelism across CPU cores
- **Memory-constrained**: Lower memory footprint
- **Latency-sensitive**: Microsecond-level response times
- **Game engines / graphics**: Direct hardware access

**Hybrid Approach**:
- Prototype in Python, rewrite hot paths in C++ (use pybind11)
- Python for orchestration, C++ for computation
- Use Python bindings to C++ libraries (best of both worlds)

---

## Migration Checklist

- [ ] Replace `class` with abstract methods → Class with `@property` decorators
- [ ] Convert `std::unique_ptr`/`std::shared_ptr` → Regular references (GC handles it)
- [ ] Change `std::thread`/`std::async` → `async def` with `await`
- [ ] Update error handling: Keep exceptions but simplify (no `std::expected`)
- [ ] Replace templates → Generics or duck typing
- [ ] Remove `const` qualifiers (use conventions instead)
- [ ] Replace RAII destructors → Context managers (`with` statement)
- [ ] Convert `std::future` → `asyncio` coroutines
- [ ] Update tests: Google Test → pytest
- [ ] Replace `std::optional` → `Optional[T]` or `T | None`
- [ ] Remove move semantics (`std::move`) → Not needed
- [ ] Replace `.has_value()` / `*value` → `is not None` / direct access
- [ ] Update includes: `#include` → `import`
- [ ] Change build system: CMake → `pyproject.toml` or `setup.py`
- [ ] Replace struct literals → Constructor calls with keyword arguments

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

# Python equivalent
agenkit/
├── pyproject.toml  # or requirements.txt
├── main.py
├── agent.py
└── tests/
    └── test_agent.py
```

**Build/Run**:
```bash
# C++
mkdir build && cd build
cmake .. && make
./myagent

# Python
python main.py
# or with virtual environment
uv run python main.py
```

**Development Workflow**:
```bash
# C++: Edit → Compile → Run → Test
vim agent.cpp
cmake --build build/
./build/myagent
./build/tests

# Python: Edit → Run → Test (no compilation!)
vim agent.py
python main.py
pytest tests/
```

---

## Full Resources

- [C++ Language Profile](LANGUAGE_PROFILE_CPP.md) - Complete C++ idioms guide
- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python idioms guide
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [pybind11](https://pybind11.readthedocs.io/) - C++ ↔ Python bindings for hybrid approach

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
