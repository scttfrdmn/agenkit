# API Reference

**Comprehensive API documentation for Agenkit**

---

## Table of Contents

- [Core Interfaces](#core-interfaces)
  - [Agent](#agent)
  - [Message](#message)
  - [Tool](#tool)
- [Middleware](#middleware)
  - [RetryDecorator](#retrydecorator)
  - [CircuitBreakerDecorator](#circuitbreakerdecorator)
  - [TimeoutDecorator](#timeoutdecorator)
  - [RateLimiterDecorator](#ratelimiterdecorator)
- [LLM Adapters](#llm-adapters)
  - [OpenAI](#openai-llm)
  - [Anthropic](#anthropic-llm)
- [Patterns](#patterns)
- [Observability](#observability)

For language-specific guides, see [Getting Started](getting-started/).  
For patterns, see the [Agent Patterns Book](../../agent-patterns-book).

---

## Core Interfaces

### Agent

The fundamental interface for all agents in Agenkit. Minimal by design - just one method.

#### Interface

**Python:**
```python
from agenkit import Agent, Message
from abc import ABC, abstractmethod

class Agent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        pass
    
    @abstractmethod
    async def process(self, message: Message) -> Message:
        """Process a message and return a response."""
        pass
```

**Go:**
```go
type Agent interface {
    Name() string
    Process(ctx context.Context, message *Message) (*Message, error)
}
```

**TypeScript:**
```typescript
interface Agent {
  readonly name: string;
  process(message: Message): Promise<Message>;
}
```

**Rust:**
```rust
#[async_trait]
pub trait Agent: Send + Sync {
    fn name(&self) -> &str;
    async fn process(&self, message: Message) -> Result<Message, AgentError>;
}
```

#### Example Implementation

**Python:**
```python
class GreetingAgent(Agent):
    @property
    def name(self) -> str:
        return "greeting-agent"
    
    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Hello! You said: {message.content}",
            metadata={"processed_by": self.name}
        )
```

**Go:**
```go
type GreetingAgent struct{}

func (a *GreetingAgent) Name() string {
    return "greeting-agent"
}

func (a *GreetingAgent) Process(ctx context.Context, msg *Message) (*Message, error) {
    return &Message{
        Role:    "assistant",
        Content: fmt.Sprintf("Hello! You said: %s", msg.Content),
        Metadata: map[string]interface{}{
            "processed_by": a.Name(),
        },
    }, nil
}
```

---

### Message

Represents a message exchanged between agents, users, or systems.

#### Structure

**Python:**
```python
from dataclasses import dataclass
from typing import Any

@dataclass
class Message:
    role: str                    # "user", "assistant", "system", "tool"
    content: str                 # Message text content
    metadata: dict[str, Any]     # Optional metadata
    
    def __post_init__(self):
        # Validates role and content length
        allowed_roles = {"user", "assistant", "system", "tool", "agent"}
        if self.role not in allowed_roles:
            raise ValueError(f"Invalid role: {self.role}")
```

**Go:**
```go
type Message struct {
    Role     string                 `json:"role"`
    Content  string                 `json:"content"`
    Metadata map[string]interface{} `json:"metadata,omitempty"`
}
```

**TypeScript:**
```typescript
interface Message {
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  metadata?: Record<string, unknown>;
}
```

**Rust:**
```rust
pub struct Message {
    pub role: String,
    pub content: String,
    pub metadata: HashMap<String, serde_json::Value>,
}
```

#### Usage

**Creating messages:**
```python
# User message
msg = Message(role="user", content="Hello", metadata={})

# Assistant response
response = Message(
    role="assistant",
    content="Hi there!",
    metadata={"model": "gpt-4-turbo"}
)

# System message
system = Message(
    role="system",
    content="You are a helpful assistant.",
    metadata={}
)
```

---

### Tool

Represents a tool that agents can invoke for deterministic operations.

#### Interface

**Python:**
```python
from abc import ABC, abstractmethod

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON schema for parameters."""
        pass
    
    @abstractmethod
    async def execute(self, params: dict) -> ToolResult:
        """Execute tool with parameters."""
        pass
```

**Go:**
```go
type Tool interface {
    Name() string
    Description() string
    Parameters() map[string]interface{}
    Execute(ctx context.Context, params map[string]interface{}) (*ToolResult, error)
}
```

**TypeScript:**
```typescript
interface Tool {
  readonly name: string;
  readonly description: string;
  readonly parameters: Record<string, unknown>;
  execute(params: Record<string, unknown>): Promise<ToolResult>;
}
```

#### Example Implementation

**Python:**
```python
class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return "Search for information"
    
    @property
    def parameters(self) -> dict:
        return {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        }
    
    async def execute(self, params: dict) -> ToolResult:
        query = params["query"]
        # Perform search...
        return ToolResult(
            success=True,
            result=f"Search results for: {query}"
        )
```

---

## Middleware

Middleware wraps agents to add cross-cutting functionality like retries, timeouts, and circuit breakers.

### RetryDecorator

Automatically retries failed operations with exponential backoff.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | Agent | required | Agent to wrap |
| `max_attempts` | int | 3 | Maximum retry attempts |
| `initial_delay_ms` | int | 100 | Initial delay in milliseconds |
| `max_delay_ms` | int | 10000 | Maximum delay in milliseconds |
| `exponential_base` | float | 2.0 | Exponential backoff multiplier |

#### Usage

**Python:**
```python
from agenkit.middleware import RetryDecorator

agent = RetryDecorator(
    agent=base_agent,
    max_attempts=3,
    initial_delay_ms=100,
    max_delay_ms=10000
)

# Automatically retries on failure
result = await agent.process(message)
```

**Go:**
```go
import "github.com/yourusername/agenkit-go/middleware"

agent := middleware.NewRetryDecorator(
    baseAgent,
    middleware.WithMaxAttempts(3),
    middleware.WithInitialDelay(100*time.Millisecond),
)

result, err := agent.Process(ctx, message)
```

**TypeScript:**
```typescript
import { RetryDecorator } from 'agenkit/middleware';

const agent = new RetryDecorator(baseAgent, {
  maxAttempts: 3,
  initialDelayMs: 100,
  maxDelayMs: 10000
});

const result = await agent.process(message);
```

#### Behavior

1. Attempts operation
2. On failure, waits `initial_delay_ms`
3. Retries with exponential backoff: delay × exponential_base
4. Caps delay at `max_delay_ms`
5. Stops after `max_attempts`

---

### CircuitBreakerDecorator

Prevents cascading failures by opening circuit after repeated failures.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | Agent | required | Agent to wrap |
| `failure_threshold` | int | 5 | Failures before opening |
| `recovery_timeout_ms` | int | 60000 | Time before retry (ms) |
| `success_threshold` | int | 2 | Successes to close circuit |

#### States

- **Closed** (normal): Requests pass through
- **Open** (failing): Requests fail immediately
- **Half-Open** (testing): Limited requests allowed

#### Usage

**Python:**
```python
from agenkit.middleware import CircuitBreakerDecorator

agent = CircuitBreakerDecorator(
    agent=base_agent,
    failure_threshold=5,
    recovery_timeout_ms=60000,
    success_threshold=2
)

try:
    result = await agent.process(message)
except CircuitBreakerError:
    print("Circuit breaker open - service unavailable")
```

**Go:**
```go
agent := middleware.NewCircuitBreakerDecorator(
    baseAgent,
    middleware.WithFailureThreshold(5),
    middleware.WithRecoveryTimeout(60*time.Second),
)

result, err := agent.Process(ctx, message)
if errors.Is(err, middleware.ErrCircuitOpen) {
    // Circuit is open
}
```

#### Behavior

1. Tracks consecutive failures
2. Opens after `failure_threshold` failures
3. Rejects requests while open
4. Transitions to half-open after `recovery_timeout_ms`
5. Closes after `success_threshold` successes

---

### TimeoutDecorator

Enforces request deadlines to prevent hanging operations.

#### Parameters (v0.50.0)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | Agent | required | Agent to wrap |
| `timeout_ms` | int | 30000 | Timeout in milliseconds |

**Note:** v0.50.0 uses `timeout_ms` (milliseconds) for clarity. Python v0.49.0 used `timeout` (seconds).

#### Usage

**Python:**
```python
from agenkit.middleware import TimeoutDecorator

agent = TimeoutDecorator(
    agent=base_agent,
    timeout_ms=30000  # 30 seconds
)

try:
    result = await agent.process(message)
except TimeoutError:
    print("Request timed out after 30 seconds")
```

**Go:**
```go
agent := middleware.NewTimeoutDecorator(
    baseAgent,
    middleware.WithTimeout(30*time.Second),  // Native duration
)

result, err := agent.Process(ctx, message)
if errors.Is(err, context.DeadlineExceeded) {
    // Request timed out
}
```

**TypeScript:**
```typescript
import { TimeoutDecorator } from 'agenkit/middleware';

const agent = new TimeoutDecorator(baseAgent, {
  timeoutMs: 30000  // 30 seconds
});

try {
  const result = await agent.process(message);
} catch (error) {
  if (error instanceof TimeoutError) {
    console.log('Request timed out');
  }
}
```

---

### RateLimiterDecorator

Limits request rate using token bucket algorithm.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | Agent | required | Agent to wrap |
| `rate` | float | 10 | Tokens per second |
| `capacity` | int | 10 | Bucket capacity |
| `max_wait_ms` | int | 30000 | Max wait time (ms) |

#### Usage

**Python:**
```python
from agenkit.middleware import RateLimiterDecorator

agent = RateLimiterDecorator(
    agent=base_agent,
    rate=10,  # 10 requests/second
    capacity=10,
    max_wait_ms=30000
)

# Automatically rate-limited
result = await agent.process(message)
```

**Go:**
```go
agent := middleware.NewRateLimiterDecorator(
    baseAgent,
    middleware.WithRate(10.0),
    middleware.WithCapacity(10),
    middleware.WithMaxWait(30*time.Second),
)

result, err := agent.Process(ctx, message)
```

#### Behavior

1. Maintains token bucket with `capacity` tokens
2. Refills at `rate` tokens/second
3. Consumes 1 token per request
4. Waits if no tokens available (up to `max_wait_ms`)
5. Fails if wait exceeds `max_wait_ms`

---

## LLM Adapters

### OpenAI LLM

Adapter for OpenAI GPT models.

#### Initialization

**Python:**
```python
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(
    api_key="sk-...",  # or env: OPENAI_API_KEY
    model="gpt-4-turbo",
    temperature=0.7,  # 0.0-2.0 (validated)
    max_tokens=1024,  # >0 (validated)
    top_p=0.9,        # 0.0-1.0 (validated)
)
```

**Go:**
```go
import "github.com/yourusername/agenkit-go/adapter/llm"

llm, err := llm.NewOpenAI(
    llm.WithAPIKey(os.Getenv("OPENAI_API_KEY")),
    llm.WithModel("gpt-4-turbo"),
    llm.WithTemperature(0.7),
    llm.WithMaxTokens(1024),
)
```

**TypeScript:**
```typescript
import { OpenAILLM } from 'agenkit/llm';

const llm = new OpenAILLM({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4-turbo',
  temperature: 0.7,
  maxTokens: 1024,
});
```

#### Methods

**complete(messages)** - Single completion

```python
messages = [
    Message(role="system", content="You are helpful."),
    Message(role="user", content="Hello"),
]

response = await llm.complete(messages)
print(response.content)
```

**stream(messages)** - Streaming completion

```python
# Python
async for chunk in llm.stream(messages):
    print(chunk.content, end="", flush=True)

# TypeScript
for await (const chunk of llm.stream(messages)) {
  process.stdout.write(chunk.content);
}

# Go (dual channels)
messageChan, errorChan := llm.Stream(ctx, messages)
for msg := range messageChan {
    fmt.Print(msg.Content)
}
```

#### Parameter Validation (v0.50.0)

All parameters validated at construction:

```python
# ✅ Valid
llm = OpenAILLM(temperature=0.7, max_tokens=1024, top_p=0.9)

# ❌ Invalid - raises ValueError
llm = OpenAILLM(temperature=3.0)  # temperature must be 0-2
llm = OpenAILLM(max_tokens=0)      # max_tokens must be >0
llm = OpenAILLM(top_p=1.5)         # top_p must be 0-1
```

---

### Anthropic LLM

Adapter for Anthropic Claude models.

#### Initialization

**Python:**
```python
from agenkit.adapters.llm import AnthropicLLM

llm = AnthropicLLM(
    api_key="sk-ant-...",  # or env: ANTHROPIC_API_KEY
    model="claude-3-5-sonnet-20241022",
    temperature=1.0,
    max_tokens=4096,
)
```

**Go:**
```go
llm, err := llm.NewAnthropic(
    llm.WithAPIKey(os.Getenv("ANTHROPIC_API_KEY")),
    llm.WithModel("claude-3-5-sonnet-20241022"),
    llm.WithTemperature(1.0),
)
```

**TypeScript:**
```typescript
import { AnthropicLLM } from 'agenkit/llm';

const llm = new AnthropicLLM({
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: 'claude-3-5-sonnet-20241022',
  temperature: 1.0,
  maxTokens: 4096,
});
```

#### Methods

Same as OpenAI: `complete(messages)` and `stream(messages)`.

---

## Patterns

Agenkit includes 18 core patterns for agent orchestration. For comprehensive documentation, see the **[Agent Patterns Book](../../agent-patterns-book)**.

### Quick Reference

**Core Patterns:**
- **Task** - One-shot execution with cleanup
- **Conversational** - Multi-turn conversations
- **ReAct** - Reasoning + Acting with tools
- **Planning** - Upfront planning, deterministic execution
- **Reflection** - Iterative self-improvement

**Composition Patterns:**
- **Sequential** - Execute agents in order
- **Parallel** - Execute agents concurrently
- **Router** - Route to specialist agents
- **Fallback** - Automatic failover
- **Supervisor** - Hierarchical coordination

### Example: ReAct Pattern

**Python:**
```python
from agenkit.patterns import ReActAgent

agent = ReActAgent(
    llm=llm,
    tools=[SearchTool(), CalculatorTool()],
    max_iterations=5
)

result = await agent.process(Message(
    role="user",
    content="What's 15% of the GDP of France?"
))
```

**See:** [Agent Patterns Book](../../agent-patterns-book) for all 18 patterns.

---

## Observability

### Configure Tracing

**Python:**
```python
from agenkit.observability import configure_observability

configure_observability(
    service_name="my-agent-service",
    exporter_type="jaeger",
    jaeger_endpoint="http://localhost:14268/api/traces"
)

# All agent.process() calls automatically traced
```

**Go:**
```go
import "github.com/yourusername/agenkit-go/observability"

shutdown, err := observability.Configure(
    observability.WithServiceName("my-agent-service"),
    observability.WithJaegerExporter("http://localhost:14268/api/traces"),
)
defer shutdown(context.Background())
```

### View Traces

Open Jaeger UI: http://localhost:16686

Features:
- Request/response traces
- LLM call timing
- Error tracking
- W3C Trace Context propagation

---

## Language-Specific APIs

For detailed language-specific APIs, see:

- **[Python Guide](getting-started/python.md)**
- **[Go Guide](getting-started/go.md)**
- **[TypeScript Guide](getting-started/typescript.md)**
- **[Rust Guide](getting-started/rust.md)**
- **[C++ Guide](getting-started/cpp.md)**
- **[Zig Guide](getting-started/zig.md)**

---

## Version Notes

**v0.50.0 Changes:**
- ✅ Parameter validation enforced at construction
- ✅ Timeout parameters renamed: `timeout` → `timeout_ms` (Python, TypeScript, C++, Zig)
- ✅ Go nullable patterns: `func(*Message) string` → `func(*Message) *string`
- ✅ Tool signatures: `**kwargs` → `params: dict` (Python)

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for migration help.

---

**Version**: v0.50.0  
**Last Updated**: January 28, 2026

For more information:
- [Getting Started Guides](getting-started/)
- [Agent Patterns Book](../../agent-patterns-book)
- [Advanced Architectures](ADVANCED_ARCHITECTURES.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [FAQ](FAQ.md)
