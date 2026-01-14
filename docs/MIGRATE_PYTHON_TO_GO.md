# Quick Reference: Python → Go Migration

**For**: Python developers migrating Agenkit code to Go
**Time**: 15 minute read
**Full Details**: See [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) and [Go Language Profile](LANGUAGE_PROFILE_GO.md)

---

## Key Differences at a Glance

| Aspect | Python | Go |
|--------|--------|-----|
| **Typing** | Dynamic, optional hints | Static, explicit |
| **Errors** | Exceptions (`try/except`) | `(result, error)` returns |
| **Concurrency** | `async/await` + `asyncio` | Goroutines + channels |
| **Memory** | GC + refcounting | GC only |
| **Performance** | Slow (interpreted) | Fast (compiled) |
| **Deployment** | Interpreter + packages | Single binary |
| **Parallelism** | Limited (GIL) | True multi-core |

---

## Message Creation

### Python
```python
from agenkit import Message

msg = Message(
    role="user",
    content="Hello!",
    metadata={"key": "value"}
)
```

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

**Changes**:
- Import path: `agenkit` → `agenkit-go`
- Constructor call → Struct literal
- String constants: `"user"` → `agenkit.RoleUser`
- Type: `dict` → `map[string]interface{}`
- Variable declaration: `=` → `:=` (short declaration)

---

## Agent Implementation

### Python
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content="Response"
        )
```

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

**Changes**:
- Class → Struct
- `__init__` → Struct initialization (no constructor method)
- `@property` decorators → Regular methods (convention: no `Get` prefix)
- `async def` → Regular function with `context.Context` parameter
- `return result` → `return result, nil` (explicit error)
- Method receivers: `(a *MyAgent)` for pointer receiver

---

## Error Handling

### Python
```python
try:
    result = await agent.process(message)
    # Use result
except InvalidMessageError as e:
    raise RuntimeError(f"process failed: {e}") from e
```

### Go
```go
result, err := agent.Process(ctx, msg)
if err != nil {
    return agenkit.Message{}, fmt.Errorf("process failed: %w", err)
}
// Use result
```

**Changes**:
- `try/except` → `if err != nil` checks
- Exceptions → Error values (return multiple values)
- `raise ... from e` → `fmt.Errorf(..., %w, err)` (error wrapping)
- No automatic error propagation (must check explicitly)
- Return zero value + error on failure: `return agenkit.Message{}, err`

---

## Concurrency

### Python (async/await)
```python
# Launch coroutine
async def process_async():
    try:
        result = await agent.process(message)
        # Use result
    except Exception as e:
        print(f"Error: {e}")

# Create task
task = asyncio.create_task(process_async())

# Wait for multiple
results = await asyncio.gather(*[
    agent.process(message)
    for agent in agents
])
```

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

**Changes**:
- `async def` → `go func()` (goroutine)
- `await` → Blocking call (Go functions are naturally concurrent)
- `asyncio.create_task()` → `go` keyword
- `asyncio.gather()` → `sync.WaitGroup` or channels
- Event loop → Runtime scheduler (automatic)
- No explicit `async/await` needed (all functions can be concurrent)

---

## Patterns

### Sequential

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[agent1, agent2])
result = await sequential.process(message)
```

**Go**:
```go
sequential := patterns.NewSequential([]agenkit.Agent{agent1, agent2})
result, err := sequential.Process(ctx, msg)
if err != nil {
    return nil, err
}
```

### Parallel

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[agent_a, agent_b])
result = await parallel.process(message)
```

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{agentA, agentB})
result, err := parallel.Process(ctx, msg)
if err != nil {
    return nil, err
}
```

---

## Common Gotchas

### 1. Context Management

**Python**: Implicit context in asyncio
```python
# No context parameter needed
async def process(self, message: Message) -> Message:
    result = await some_async_operation()
    return result
```

**Go**: Explicit context parameter (REQUIRED)
```go
// Context MUST be first parameter
func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    // Check cancellation
    select {
    case <-ctx.Done():
        return agenkit.Message{}, ctx.Err()
    default:
    }

    // Pass context to all operations
    result, err := someOperation(ctx)
    return result, err
}
```

**Migration**: Add `context.Context` as first parameter to ALL async functions.

### 2. Error Handling is NOT Optional

**Python**: Can ignore errors (exceptions will propagate)
```python
result = await agent.process(message)
# If error occurs, exception automatically propagates up
```

**Go**: MUST check every error
```go
// WRONG: Ignoring error (will not compile if assigned)
result := agent.Process(ctx, msg)  // Compile error: multiple return values

// CORRECT: Check error
result, err := agent.Process(ctx, msg)
if err != nil {
    return agenkit.Message{}, fmt.Errorf("failed: %w", err)
}

// If you intentionally ignore error (rare)
result, _ := agent.Process(ctx, msg)  // Explicit ignore
```

**Migration**: Every function call that returns an error MUST handle it.

### 3. None vs nil vs Zero Values

**Python**: `None` for missing values
```python
msg: Message | None = None  # Optional type
if msg is None:
    return
```

**Go**: `nil` and zero values
```go
// Nil for pointers, slices, maps, interfaces
var msg *Message = nil
if msg == nil {
    return
}

// Zero values for structs (NOT nil)
var msg Message  // msg is NOT nil, fields have zero values
// msg.Role == ""
// msg.Content == ""
// msg.Metadata == nil (map is nil though)
```

**Migration**:
- `None` → `nil` for reference types
- Understand zero values for structs (not nil)
- Initialize maps before use: `make(map[string]interface{})`

### 4. Duck Typing → Interface Checking

**Python**: Runtime duck typing
```python
# Any object with process() method works
def use_agent(agent):
    return await agent.process(message)
```

**Go**: Compile-time interface checking
```go
// Must explicitly satisfy Agent interface
func useAgent(agent agenkit.Agent) (agenkit.Message, error) {
    return agent.Process(ctx, message)  // Checked at compile time
}

// Interface satisfied implicitly (no "implements" keyword)
type MyAgent struct {}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    // This struct now implements Agent interface automatically
}
```

**Migration**: Define interfaces explicitly, implementation is automatic.

### 5. GIL → True Parallelism

**Python**: GIL limits parallelism
```python
# These run concurrently, but NOT in parallel (GIL)
await asyncio.gather(*[
    cpu_intensive_task() for _ in range(10)
])
# Only one task executes at a time due to GIL
```

**Go**: True parallel execution
```go
// These run in PARALLEL on multiple cores
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        cpuIntensiveTask()  // Truly parallel execution
    }()
}
wg.Wait()
```

**Migration**: Go goroutines provide real parallelism, not just concurrency.

---

## Testing

### Python
```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.content == "Expected"
```

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

**Changes**:
- `async def test_xxx()` → `func TestXxx(t *testing.T)`
- `@pytest.mark.asyncio` → Not needed (Go tests are synchronous)
- `assert` statements → `t.Errorf()` / `t.Fatalf()` calls
- Function naming: `test_agent` → `TestAgent` (CamelCase, exported)
- No pytest fixtures (use table-driven tests or test helpers)

---

## Performance Considerations

| Operation | Python | Go | Speedup |
|-----------|--------|-----|---------|
| Agent creation | ~1μs | ~100ns | 10x |
| Message processing | ~10μs | ~1μs | 10x |
| Sequential (3 agents) | ~30μs | ~3μs | 10x |
| Parallel (3 agents) | ~20μs (GIL limited) | ~1μs (true parallel) | 20x |
| Startup time | ~500ms | ~10ms | 50x |
| Memory footprint | ~50MB | ~5MB | 10x |
| Binary size | Interpreter | ~10MB | Self-contained |

**When to migrate Python → Go**:
- **Production deployments**: 5-10x better performance, single binary
- **High concurrency**: True parallelism without GIL limitations
- **Resource-constrained**: Lower memory footprint, faster startup
- **Latency-sensitive**: Sub-millisecond GC pauses, predictable performance
- **Deployment simplicity**: Single binary, no runtime dependencies
- **Long-running services**: Better resource efficiency over time

**When to keep Python**:
- **Prototyping**: Faster iteration, dynamic typing
- **ML/AI integration**: Best ecosystem (NumPy, TensorFlow, PyTorch)
- **Data science**: pandas, scikit-learn, matplotlib
- **Scripting**: Quick automation tasks
- **Rapid development**: No compilation step

---

## Migration Checklist

- [ ] Replace `class` with `struct` types
- [ ] Convert exception handling to `(result, error)` returns
- [ ] Add `context.Context` as first parameter to all async functions
- [ ] Change `async/await` to goroutines (or keep synchronous)
- [ ] Update imports: `agenkit` → `github.com/agenkit/agenkit-go`
- [ ] Replace duck typing with explicit interfaces
- [ ] Convert tests: `pytest` → `testing` package
- [ ] Update error handling: `try/except` → `if err != nil`
- [ ] Change constants: `"user"` → `agenkit.RoleUser`
- [ ] Update dependencies: `requirements.txt` → `go.mod`
- [ ] Initialize maps before use: `make(map[string]interface{})`
- [ ] Add error checks for ALL operations that can fail
- [ ] Replace `@property` decorators with regular methods
- [ ] Convert `None` checks to `nil` checks (for reference types)
- [ ] Update type hints to Go type declarations

---

## Type Mapping Reference

### Basic Types

| Python | Go |
|--------|-----|
| `str` | `string` |
| `int` | `int`, `int64`, `int32` |
| `float` | `float64`, `float32` |
| `bool` | `bool` |
| `bytes` | `[]byte` |
| `None` | `nil` (for pointers/refs) |

### Container Types

| Python | Go |
|--------|-----|
| `list[T]` | `[]T` (slice) |
| `dict[K, V]` | `map[K]V` |
| `set[T]` | `map[T]struct{}` |
| `tuple` | Struct or `[N]T` (array) |

### Type Annotations

| Python | Go |
|--------|-----|
| `Optional[T]` | `*T` (pointer) |
| `Union[A, B]` | `interface{}` (or separate types) |
| `Any` | `interface{}` |
| `Callable` | `func` type |

---

## Context Management

### Python
```python
# Async context manager
async with aiohttp.ClientSession() as session:
    result = await session.get(url)
# Automatic cleanup

# Timeout
async with asyncio.timeout(5.0):
    result = await agent.process(message)
```

### Go
```go
// Defer for cleanup
file, err := os.Open(filename)
if err != nil {
    return err
}
defer file.Close()  // Called when function returns

// Context with timeout
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
result, err := agent.Process(ctx, message)
```

**Changes**:
- `async with` → `defer` statement
- Context managers → Explicit defer calls
- Timeout context → `context.WithTimeout()`
- Cancellation → `context.WithCancel()`

---

## Concurrency Patterns

### Producer-Consumer

**Python**:
```python
import asyncio

queue = asyncio.Queue()

async def producer():
    await queue.put(message)

async def consumer():
    msg = await queue.get()
    # Process msg
```

**Go**:
```go
ch := make(chan agenkit.Message, 10)  // Buffered channel

func producer() {
    ch <- message  // Send to channel
}

func consumer() {
    msg := <-ch  // Receive from channel
    // Process msg
}
```

### Fan-Out / Fan-In

**Python**:
```python
# Fan-out: Distribute work
tasks = [asyncio.create_task(worker(item)) for item in items]

# Fan-in: Collect results
results = await asyncio.gather(*tasks)
```

**Go**:
```go
// Fan-out: Distribute work
for _, item := range items {
    go worker(item, resultsCh)
}

// Fan-in: Collect results
for i := 0; i < len(items); i++ {
    result := <-resultsCh
    results = append(results, result)
}
```

---

## Package Structure

### Python
```
agenkit/
├── __init__.py
├── agent.py
├── message.py
├── patterns/
│   ├── __init__.py
│   ├── sequential.py
│   └── parallel.py
└── tests/
    └── test_agent.py
```

### Go
```
agenkit-go/
├── go.mod
├── agent.go
├── message.go
├── patterns/
│   ├── sequential.go
│   └── parallel.go
└── agent_test.go
```

**Changes**:
- `__init__.py` → Not needed (packages are directories)
- Test files: `test_*.py` → `*_test.go` (same directory)
- Package imports: By directory path, not file

---

## Build and Run

### Python
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py

# Or with uv
uv run python main.py

# Test
pytest tests/
```

### Go
```bash
# Initialize module
go mod init myproject

# Install dependencies (automatic on build)
go get github.com/agenkit/agenkit-go

# Build
go build -o myapp

# Run
./myapp

# Or build + run
go run main.go

# Test
go test ./...

# Benchmark
go test -bench=. ./...
```

**Changes**:
- No virtual environment needed
- Dependencies in `go.mod` (auto-generated)
- Compilation required (but fast: <1s typical)
- Single binary output (no runtime needed)
- Built-in benchmark support

---

## Dependency Management

### Python
```python
# requirements.txt
agenkit==0.46.0
pydantic>=2.0.0
aiohttp>=3.9.0

# pyproject.toml
[project]
dependencies = [
    "agenkit>=0.46.0",
    "pydantic>=2.0.0",
]
```

### Go
```go
// go.mod
module myproject

go 1.22

require (
    github.com/agenkit/agenkit-go v0.46.0
)

// No need to specify transitive dependencies
```

**Changes**:
- `requirements.txt` → `go.mod`
- Semantic versioning: `v0.46.0` format
- Transitive dependencies managed automatically
- Update: `go get -u` or `go mod tidy`

---

## Quick Start

**Python Project**:
```python
# main.py
from agenkit import Message, Agent

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["text"]

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="Response")

# Run
import asyncio
agent = MyAgent()
result = asyncio.run(agent.process(Message(role="user", content="Hello")))
```

**Go Equivalent**:
```go
// main.go
package main

import (
    "context"
    "fmt"
    "github.com/agenkit/agenkit-go"
)

type MyAgent struct{}

func (a *MyAgent) Name() string {
    return "my-agent"
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

func main() {
    agent := &MyAgent{}
    result, err := agent.Process(
        context.Background(),
        agenkit.Message{Role: agenkit.RoleUser, Content: "Hello"},
    )
    if err != nil {
        panic(err)
    }
    fmt.Println(result.Content)
}
```

**Build and run**:
```bash
# Go
go run main.go

# Or compile first
go build -o myapp
./myapp
```

---

## Full Resources

- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python idioms guide
- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Effective Go](https://go.dev/doc/effective_go) - Official Go style guide
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [Go by Example](https://gobyexample.com/) - Go patterns and idioms

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
