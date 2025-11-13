# Core Interfaces

Deep dive into Agenkit's four core interfaces.

## Overview

Agenkit defines exactly **4 interfaces**:

1. **Agent** - Processes messages
2. **Message** - Universal data format
3. **Tool** - Executable functions
4. **ToolResult** - Tool execution results

That's it. Everything else is built on top of these four primitives.

---

## The Agent Interface

The Agent interface is the heart of Agenkit. It defines a single contract: process messages.

=== "Python"

    ```python
    from abc import ABC, abstractmethod
    from agenkit.interfaces import Message

    class Agent(ABC):
        @property
        @abstractmethod
        def name(self) -> str:
            """Unique agent identifier."""
            pass

        @abstractmethod
        async def process(self, message: Message) -> Message:
            """Process a message and return a response."""
            pass

        # Optional methods
        async def stream(self, message: Message) -> AsyncIterator[Message]:
            """Stream response messages (override if supported)."""
            raise NotImplementedError

        @property
        def capabilities(self) -> list[str]:
            """What this agent can do (override if meaningful)."""
            return []
    ```

=== "Go"

    ```go
    package agenkit

    type Agent interface {
        // Required methods
        Name() string
        Process(ctx context.Context, msg *Message) (*Message, error)

        // Optional methods
        Capabilities() []string
    }
    ```

### Required Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `name` | Unique identifier for the agent | `str` (Python) / `string` (Go) |
| `process(message)` | Core processing logic | `Message` |

### Optional Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `stream(message)` | Stream responses incrementally | `AsyncIterator[Message]` |
| `capabilities` | List of capabilities | `list[str]` |

---

## The Message Type

Message is the universal data format for agent communication.

=== "Python"

    ```python
    from dataclasses import dataclass, field
    from datetime import datetime, timezone
    from typing import Any

    @dataclass(frozen=True)
    class Message:
        role: str
        content: Any
        metadata: dict[str, Any] = field(default_factory=dict)
        timestamp: datetime = field(
            default_factory=lambda: datetime.now(timezone.utc)
        )
    ```

=== "Go"

    ```go
    type Message struct {
        Role      string
        Content   interface{}
        Metadata  map[string]interface{}
        Timestamp time.Time
    }
    ```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `role` | `str` | Message source: `"user"`, `"agent"`, `"system"`, `"tool"` |
| `content` | `Any` | Flexible content - string, dict, list, or any serializable type |
| `metadata` | `dict` | Extension point for custom data (trace IDs, timestamps, etc.) |
| `timestamp` | `datetime` | UTC timestamp for ordering and debugging |

### Design Decisions

**Why frozen/immutable?**
- Thread safety
- Cacheable
- Prevents accidental mutation

**Why Any for content?**
- Maximum flexibility
- Agents decide their data format
- No serialization constraints

**Why metadata dict?**
- Framework extensions don't change Message
- Observability data (trace IDs, span IDs)
- Custom application data

### Common Roles

| Role | Used By | Example |
|------|---------|---------|
| `"user"` | Human input | `Message(role="user", content="Hello")` |
| `"agent"` | Agent responses | `Message(role="agent", content="Response")` |
| `"system"` | System prompts | `Message(role="system", content="Instructions")` |
| `"tool"` | Tool results | `Message(role="tool", content=tool_result)` |

---

## The Tool Interface

Tools are executable functions that agents can use.

=== "Python"

    ```python
    from abc import ABC, abstractmethod
    from agenkit.interfaces import ToolResult

    class Tool(ABC):
        @property
        @abstractmethod
        def name(self) -> str:
            """Tool identifier (must be unique)."""
            pass

        @property
        @abstractmethod
        def description(self) -> str:
            """What this tool does (used by LLMs)."""
            pass

        @abstractmethod
        async def execute(self, **kwargs: Any) -> ToolResult:
            """Execute the tool with given parameters."""
            pass

        # Optional methods
        @property
        def parameters_schema(self) -> dict[str, Any] | None:
            """JSON schema for tool parameters."""
            return None

        async def validate(self, **kwargs: Any) -> bool:
            """Validate inputs before execution."""
            return True
    ```

=== "Go"

    ```go
    type Tool interface {
        Name() string
        Description() string
        Execute(ctx context.Context, params map[string]interface{}) (*ToolResult, error)
    }
    ```

### Example: Calculator Tool

=== "Python"

    ```python
    class CalculatorTool(Tool):
        @property
        def name(self) -> str:
            return "calculator"

        @property
        def description(self) -> str:
            return "Perform mathematical calculations"

        async def execute(self, expression: str) -> ToolResult:
            try:
                result = eval(expression)  # DON'T DO THIS IN PRODUCTION!
                return ToolResult(success=True, data=result)
            except Exception as e:
                return ToolResult(success=False, data=None, error=str(e))
    ```

=== "Go"

    ```go
    type CalculatorTool struct{}

    func (t *CalculatorTool) Name() string {
        return "calculator"
    }

    func (t *CalculatorTool) Description() string {
        return "Perform mathematical calculations"
    }

    func (t *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (*ToolResult, error) {
        // Implementation here
        return &ToolResult{Success: true, Data: result}, nil
    }
    ```

---

## The ToolResult Type

ToolResult represents the outcome of tool execution.

=== "Python"

    ```python
    @dataclass(frozen=True)
    class ToolResult:
        success: bool
        data: Any
        error: str | None = None
        metadata: dict[str, Any] = field(default_factory=dict)
    ```

=== "Go"

    ```go
    type ToolResult struct {
        Success  bool
        Data     interface{}
        Error    *string
        Metadata map[string]interface{}
    }
    ```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Did the tool execute successfully? |
| `data` | `Any` | The result data (if successful) |
| `error` | `str \| None` | Error message (if failed) |
| `metadata` | `dict` | Execution details (timing, resource usage, etc.) |

### Design: Explicit Success/Failure

Instead of using exceptions, ToolResult uses explicit success/failure:

```python
# Good - explicit success/failure
result = await tool.execute(query="test")
if result.success:
    print(result.data)
else:
    print(f"Error: {result.error}")

# Bad - exception-based (NOT used)
try:
    result = await tool.execute(query="test")
except ToolExecutionError as e:
    print(f"Error: {e}")
```

**Why?**
- Errors are data, not control flow
- Easier to serialize across network
- Forces callers to handle failures
- No hidden exceptions

---

## Interface Guarantees

### Type Safety

All interfaces are fully typed in both Python and Go:

=== "Python"

    ```python
    # mypy strict mode compliant
    agent: Agent = MyAgent()
    message: Message = Message(role="user", content="test")
    response: Message = await agent.process(message)
    ```

=== "Go"

    ```go
    // Full type checking
    var agent agenkit.Agent = &MyAgent{}
    message := &agenkit.Message{Role: "user", Content: "test"}
    response, err := agent.Process(ctx, message)
    ```

### Performance Characteristics

- **Agent interface overhead:** <5% (benchmarked)
- **Message creation:** Single allocation
- **Hot path:** Direct method call, no dynamic dispatch
- **Tool execution:** No metaclass magic, no reflection

### Backward Compatibility

These interfaces are **stable**. Changes will be:

1. **Additive only** - New optional methods may be added
2. **Deprecated gradually** - Old methods marked deprecated for 2+ versions
3. **Versioned** - Major version bump for breaking changes

---

## Implementation Examples

### Minimal Agent

=== "Python"

    ```python
    class MinimalAgent(Agent):
        @property
        def name(self) -> str:
            return "minimal"

        async def process(self, message: Message) -> Message:
            return Message(role="agent", content="OK")
    ```

=== "Go"

    ```go
    type MinimalAgent struct{}

    func (a *MinimalAgent) Name() string {
        return "minimal"
    }

    func (a *MinimalAgent) Process(ctx context.Context, msg *Message) (*Message, error) {
        return &Message{Role: "agent", Content: "OK"}, nil
    }
    ```

### Stateful Agent

=== "Python"

    ```python
    class StatefulAgent(Agent):
        def __init__(self):
            self.request_count = 0

        @property
        def name(self) -> str:
            return "stateful"

        async def process(self, message: Message) -> Message:
            self.request_count += 1
            return Message(
                role="agent",
                content=f"Request #{self.request_count}",
                metadata={"count": self.request_count}
            )
    ```

=== "Go"

    ```go
    type StatefulAgent struct {
        requestCount int
        mu           sync.Mutex
    }

    func (a *StatefulAgent) Process(ctx context.Context, msg *Message) (*Message, error) {
        a.mu.Lock()
        a.requestCount++
        count := a.requestCount
        a.mu.Unlock()

        return &Message{
            Role:    "agent",
            Content: fmt.Sprintf("Request #%d", count),
            Metadata: map[string]interface{}{"count": count},
        }, nil
    }
    ```

---

## Next Steps

- **[Architecture](architecture.md)** - See how these interfaces compose into layers
- **[Design Principles](design-principles.md)** - Understand the "why" behind these choices
- **[Examples](../examples/index.md)** - See 28+ implementations
