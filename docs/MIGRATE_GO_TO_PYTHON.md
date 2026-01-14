# Quick Reference: Go → Python Migration

**For**: Go developers migrating Agenkit code to Python
**Time**: 15 minute read
**Full Details**: See [Go Language Profile](LANGUAGE_PROFILE_GO.md) and [Python docs](../agenkit/)

---

## Key Differences at a Glance

| Aspect | Go | Python |
|--------|----|----|
| **Typing** | Static, explicit | Dynamic, optional hints |
| **Errors** | `(result, error)` returns | Exceptions (`try/except`) |
| **Concurrency** | Goroutines + channels | `async/await` + `asyncio` |
| **Memory** | GC, no manual management | GC + refcounting |
| **Performance** | Fast (compiled) | Slower (interpreted) |
| **Deployment** | Single binary | Interpreter + packages |

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

### Python
```python
from agenkit import Message

msg = Message(
    role="user",
    content="Hello!",
    metadata={"key": "value"}
)
```

**Changes**:
- Import path: `agenkit-go` → `agenkit`
- Struct literal → Constructor call
- Constants: `agenkit.RoleUser` → `"user"` string
- Type: `map[string]interface{}` → `dict`

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

### Python
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    def __init__(self, name: str):
        self.name = name

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

**Changes**:
- Struct → Class with `__init__`
- Methods → `@property` decorators or `async def`
- `ctx context.Context` → removed (Python uses asyncio context implicitly)
- `(result, error)` → `return result` (errors become exceptions)

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

### Python
```python
try:
    result = await agent.process(message)
    # Use result
except AgentError as e:
    raise RuntimeError(f"process failed: {e}") from e
```

**Changes**:
- `if err != nil` → `try/except` block
- Error wrapping: `fmt.Errorf(..., %w, err)` → `raise ... from e`
- No tuple unpacking needed in Python

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

**Changes**:
- `go func()` → `asyncio.create_task(async def)`
- `sync.WaitGroup` → `asyncio.gather()`
- `context.Context` → implicit in asyncio
- Channels → `asyncio.Queue()`

---

## Patterns

### Sequential

**Go**:
```go
sequential := patterns.NewSequential([]agenkit.Agent{agent1, agent2})
result, err := sequential.Process(ctx, msg)
```

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[agent1, agent2])
result = await sequential.process(message)
```

### Parallel

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{agentA, agentB})
result, err := parallel.Process(ctx, msg)
```

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[agent_a, agent_b])
result = await parallel.process(message)
```

---

## Common Gotchas

### 1. Context Cancellation

**Go**: Explicit `ctx.Done()` checks
```go
select {
case <-ctx.Done():
    return nil, ctx.Err()
default:
    // Continue
}
```

**Python**: Implicit with `asyncio` tasks
```python
# Cancellation happens via task.cancel()
# No explicit checking needed in most cases
```

### 2. Nil vs None

**Go**: `nil` for pointers, slices, maps, interfaces
**Python**: `None` for missing values

```go
// Go
var msg *Message = nil  // nil pointer
```

```python
# Python
msg: Message | None = None  # Optional type
```

### 3. Type Assertions

**Go**: Runtime type checking
```go
value, ok := metadata["key"].(string)
if !ok {
    return nil, errors.New("wrong type")
}
```

**Python**: Duck typing (runtime)
```python
try:
    value = str(metadata["key"])
except (KeyError, TypeError) as e:
    raise ValueError("wrong type") from e
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

**Changes**:
- `func TestXxx(t *testing.T)` → `async def test_xxx()`
- `t.Fatalf/t.Errorf` → `assert` statements or `pytest.raises()`
- `@pytest.mark.asyncio` decorator for async tests

---

## Performance Considerations

| Operation | Go | Python | Notes |
|-----------|----|----|-------|
| Agent creation | ~100ns | ~1μs | Python 10x slower |
| Message processing | ~1μs | ~10μs | Python 10x slower |
| Sequential (3 agents) | ~3μs | ~30μs | Consistent overhead |
| Parallel (3 agents) | ~1μs | ~20μs | GIL limits Python |

**When to use Python**:
- Prototyping and experimentation
- Data science / ML integration (NumPy, pandas, scikit-learn)
- Scripting and automation
- Quick iteration (no compilation)

**When to keep Go**:
- Production deployments (performance critical)
- High concurrency workloads
- Memory-constrained environments
- Single-binary deployment

---

## Migration Checklist

- [ ] Replace `struct` with `class`
- [ ] Convert `(result, error)` returns to exceptions
- [ ] Change `goroutines` to `async/await`
- [ ] Remove `context.Context` parameter (implicit in asyncio)
- [ ] Update imports: `agenkit-go` → `agenkit`
- [ ] Replace type assertions with duck typing
- [ ] Convert tests: `*testing.T` → `pytest`
- [ ] Update error handling: `if err != nil` → `try/except`
- [ ] Change constants: `agenkit.RoleUser` → `"user"`
- [ ] Update dependencies: `go.mod` → `requirements.txt`

---

## Quick Start

```bash
# Go project structure
agenkit-go/
├── go.mod
├── main.go
└── agent.go

# Python equivalent
agenkit/
├── pyproject.toml  # or requirements.txt
├── main.py
└── agent.py
```

**Build/Run**:
```bash
# Go
go build -o myagent
./myagent

# Python
python main.py
# or with venv
uv run python main.py
```

---

## Full Resources

- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Python Documentation](../agenkit/) - Full Python API reference
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
