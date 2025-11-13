# Architecture

Understanding Agenkit's layered architecture from the ground up.

## Overview

Agenkit has a **layered architecture** where each layer is independent and composable. Every layer implements the same core `Agent` interface, enabling unlimited composability.

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR APPLICATION                         │
│  (Your agents, business logic, AI models)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                 COMPOSITION LAYER                            │
│  Sequential • Parallel • Router • Fallback • Conditional    │
│  (Orchestrate multiple agents into workflows)               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                 MIDDLEWARE LAYER                             │
│  CircuitBreaker • Retry • Timeout • RateLimiter            │
│  Caching • Batching • Tracing • Metrics                     │
│  (Add resilience, observability, performance)               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                 TRANSPORT LAYER                              │
│  HTTP • gRPC • WebSocket • Local                            │
│  (Enable cross-process, cross-language communication)       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                 CORE INTERFACES                              │
│  Agent • Message • Tool • ToolResult                         │
│  (The minimal contract everything implements)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Core Interfaces

**Location:** `agenkit/interfaces.py` (Python), `agenkit-go/agenkit/interfaces.go` (Go)

This is the **minimal contract** that everything builds on. Only 4 primitives:

### The Agent Interface

```python
class Agent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier"""

    @abstractmethod
    async def process(self, message: Message) -> Message:
        """Core method - process input, return output"""
```

**That's it!** An agent is just something with a name that can process messages.

### The Message Data Class

```python
@dataclass(frozen=True)
class Message:
    role: str           # "user", "agent", "system", "tool"
    content: Any        # Flexible - str, dict, list, anything
    metadata: dict      # Extension point for custom data
    timestamp: datetime # For ordering and debugging
```

### The Tool Interface

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier"""

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
```

### The ToolResult Data Class

```python
@dataclass(frozen=True)
class ToolResult:
    success: bool       # Did it work?
    data: Any          # The result
    error: str | None  # Error message if failed
```

### Design Principle: Minimalism

These interfaces are **minimal** - just enough for interoperability, nothing more. No framework opinions leak in. You can implement them with any LLM library, any framework, any infrastructure.

---

## Layer 2: Transport Layer

**Location:** `agenkit/adapters/python/` (Python), `agenkit-go/adapter/` (Go)

Enables agents to communicate **across processes** and **across languages** (Python ↔ Go).

### Transport Types

#### 1. Local Transport

Same process, no serialization:

```python
from agenkit.adapters.python.local_agent import LocalAgent

local_agent = LocalAgent(my_agent)
response = await local_agent.process(message)
```

#### 2. HTTP Transport

Remote agent over HTTP/1.1, HTTP/2, or HTTP/3:

```python
from agenkit.adapters.python.remote_agent import RemoteAgent

remote_agent = RemoteAgent(
    name="python-agent",
    endpoint="http://localhost:8080"
)
response = await remote_agent.process(message)
```

#### 3. gRPC Transport

High-performance binary protocol:

```python
remote_agent = RemoteAgent(
    name="go-agent",
    endpoint="grpc://localhost:50051"
)
```

#### 4. WebSocket Transport

Bidirectional streaming:

```python
remote_agent = RemoteAgent(
    name="streaming-agent",
    endpoint="ws://localhost:8080"
)
```

### How Transports Work

The `RemoteAgent` class implements the same `Agent` interface but **forwards calls** to a remote server:

```python
class RemoteAgent(Agent):
    def __init__(self, name: str, endpoint: str):
        self._transport = self._create_transport(endpoint)

    async def process(self, message: Message) -> Message:
        # 1. Serialize message
        request_bytes = encode_message(message)

        # 2. Send over transport (HTTP/gRPC/WebSocket)
        response_bytes = await self._transport.send(request_bytes)

        # 3. Deserialize response
        return decode_message(response_bytes)
```

**Key Point:** From the caller's perspective, local and remote agents are **identical** - same interface!

### Cross-Language Communication

=== "Python → Go"

    ```python
    # Python calling Go agent
    go_agent = RemoteAgent(
        name="go-text-processor",
        endpoint="grpc://localhost:50051"
    )
    response = await go_agent.process(message)
    ```

=== "Go → Python"

    ```go
    // Go calling Python agent
    pythonAgent := http.NewHTTPAgent(
        "python-analyzer",
        "http://localhost:8080",
    )
    response, _ := pythonAgent.Process(ctx, message)
    ```

---

## Layer 3: Middleware Layer

**Location:** `agenkit/middleware/` (Python), `agenkit-go/middleware/` (Go)

Middleware **wraps agents** to add cross-cutting concerns like error handling, metrics, caching, etc.

### The Middleware Pattern

Every middleware implements the `Agent` interface and wraps another agent:

```python
class RetryDecorator(Agent):
    def __init__(self, agent: Agent, config: RetryConfig):
        self._agent = agent  # Wrap the inner agent
        self._config = config

    @property
    def name(self) -> str:
        return self._agent.name  # Delegate to inner agent

    async def process(self, message: Message) -> Message:
        # Add retry logic AROUND the inner agent
        for attempt in range(self._config.max_attempts):
            try:
                return await self._agent.process(message)
            except Exception as e:
                if attempt == self._config.max_attempts - 1:
                    raise
                await asyncio.sleep(backoff)
```

### Available Middleware

| Middleware | Purpose | Example |
|------------|---------|---------|
| **RetryDecorator** | Exponential backoff with jitter | `RetryDecorator(agent, RetryConfig(max_attempts=3))` |
| **CircuitBreaker** | Fail-fast pattern | `CircuitBreaker(agent, CircuitBreakerConfig())` |
| **TimeoutDecorator** | Request deadline enforcement | `TimeoutDecorator(agent, timeout=10.0)` |
| **RateLimiter** | Token bucket algorithm | `RateLimiter(agent, requests_per_second=10)` |
| **CachingDecorator** | LRU cache with TTL | `CachingDecorator(agent, max_size=1000, ttl=300)` |
| **BatchingDecorator** | Request aggregation | `BatchingDecorator(agent, max_batch_size=10)` |
| **TracingMiddleware** | OpenTelemetry tracing | `TracingMiddleware(agent)` |
| **MetricsMiddleware** | Prometheus metrics | `MetricsMiddleware(agent)` |

### Stacking Middleware

Middleware is **composable** - you can stack them:

```python
# Start with base agent
agent = MyAgent()

# Add caching
agent = CachingDecorator(agent, max_size=1000)

# Add retry logic
agent = RetryDecorator(agent, RetryConfig(max_attempts=3))

# Add circuit breaker
agent = CircuitBreaker(agent, CircuitBreakerConfig())

# Add timeout
agent = TimeoutDecorator(agent, timeout=30.0)

# Add metrics
agent = MetricsMiddleware(agent, service_name="my-service")

# Now use it - all middleware applies automatically!
response = await agent.process(message)
```

### Request Flow Through Middleware Stack

```
Your Call
    ↓
MetricsMiddleware (records metrics)
    ↓
TimeoutDecorator (enforces deadline)
    ↓
CircuitBreaker (checks if circuit is open)
    ↓
RetryDecorator (retries on failure)
    ↓
CachingDecorator (checks cache first)
    ↓
MyAgent (your actual logic)
    ↓
Response flows back up
```

---

## Layer 4: Composition Layer

**Location:** `agenkit/composition/` (Python), `agenkit-go/composition/` (Go)

Combine multiple agents into **workflows**. All composition patterns **implement the Agent interface** - so composed agents look like single agents!

### 1. Sequential Pattern (Pipeline)

Output of one agent becomes input of the next:

```python
from agenkit.composition import SequentialAgent

# Output of agent1 → input of agent2 → input of agent3
pipeline = SequentialAgent([agent1, agent2, agent3])
result = await pipeline.process(message)  # Flows through all 3
```

**Use cases:** Data pipelines, multi-stage processing, validation → processing → formatting

### 2. Parallel Pattern (Fan-out)

All agents process the SAME input concurrently:

```python
from agenkit.composition import ParallelAgent

# All agents process the SAME input concurrently
parallel = ParallelAgent([sentiment_agent, summary_agent, translate_agent])
result = await parallel.process(message)  # All 3 run in parallel
# result.content contains list of all responses
```

**Use cases:** Ensemble methods, multi-perspective analysis, redundant processing

### 3. Fallback Pattern (High Availability)

Try primary, fall back to secondary if it fails:

```python
from agenkit.composition import FallbackAgent

# Try primary, fall back to secondary if it fails
ha_agent = FallbackAgent([primary_agent, backup_agent, last_resort_agent])
result = await ha_agent.process(message)  # Uses first one that succeeds
```

**Use cases:** High availability, graceful degradation, multi-model fallback

### 4. Conditional Pattern (Router)

Route to different agents based on condition:

```python
from agenkit.composition import ConditionalAgent

def route(message: Message) -> int:
    if "weather" in message.content:
        return 0  # weather_agent
    elif "news" in message.content:
        return 1  # news_agent
    else:
        return 2  # general_agent

router = ConditionalAgent(
    agents=[weather_agent, news_agent, general_agent],
    condition=route
)
```

**Use cases:** Intent routing, load balancing, A/B testing

### Composing Compositions

Since compositions are agents, you can **nest them**:

```python
# Parallel analysis, then sequential refinement
analysis_parallel = ParallelAgent([sentiment, topics, entities])
refinement_sequential = SequentialAgent([analysis_parallel, summarizer, formatter])

# Add retry + circuit breaker
production_agent = CircuitBreaker(
    RetryDecorator(refinement_sequential)
)
```

---

## Layer 5: Observability

**Location:** `agenkit/observability/` (Python), `agenkit-go/observability/` (Go)

Built-in distributed tracing, metrics, and logging using OpenTelemetry.

### Distributed Tracing

```python
from agenkit.observability import init_tracing, TracingMiddleware

# Initialize OpenTelemetry
init_tracing(
    service_name="my-service",
    otlp_endpoint="http://jaeger:4317"
)

# Wrap agent with tracing
traced_agent = TracingMiddleware(my_agent)

# Every call now creates spans!
response = await traced_agent.process(message)
```

Traces propagate **across languages** (Python → Go → Python) using W3C Trace Context!

### Prometheus Metrics

```python
from agenkit.observability import init_metrics, MetricsMiddleware

# Start Prometheus endpoint on :8001
init_metrics(service_name="my-service", port=8001)

# Wrap agent
metered_agent = MetricsMiddleware(my_agent)

# Automatic metrics:
# - agenkit_requests_total{agent="...", status="..."}
# - agenkit_request_duration_seconds{agent="..."}
# - agenkit_message_size_bytes{agent="..."}
```

### Structured Logging

```python
from agenkit.observability import configure_logging

configure_logging(
    level=logging.INFO,
    structured=True,  # JSON logs
    include_trace_context=True  # Auto-inject trace_id, span_id
)
```

---

## Key Design Principles

### 1. Everything is an Agent

- Middleware wraps agents and exposes Agent interface
- Compositions combine agents and expose Agent interface
- Remote agents proxy agents and expose Agent interface
- **This means everything is composable!**

### 2. Minimal Interfaces

- Agent only needs `name` + `process()`
- Message is just 4 fields
- No framework opinions, maximum flexibility

### 3. Decorator Pattern

- Middleware uses decorators (wrapping)
- Stack as many as you need
- Each adds one concern (Single Responsibility)

### 4. Language Agnostic

- Python and Go have **identical APIs**
- Full cross-language compatibility
- Same patterns, same behavior

### 5. Production Ready

- All 137 tests passing
- Comprehensive error handling
- Security hardened (non-root containers)
- Fully observable (traces, metrics, logs)

---

## Complete Example

Putting it all together:

```python
from agenkit import Agent, Message
from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.middleware import RetryDecorator, CircuitBreaker, TimeoutDecorator
from agenkit.observability import TracingMiddleware, MetricsMiddleware
from agenkit.composition import ParallelAgent, SequentialAgent

# Your custom agent
class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        # Your logic here
        return Message(role="agent", content="Response")

# Remote Go agent (cross-language!)
go_agent = RemoteAgent(name="go-agent", endpoint="grpc://localhost:50051")

# Parallel analysis
analysis = ParallelAgent([MyAgent(), go_agent])

# Sequential pipeline
pipeline = SequentialAgent([analysis, MyAgent()])

# Add production middleware
production_agent = TracingMiddleware(      # Distributed tracing
    MetricsMiddleware(                     # Prometheus metrics
        TimeoutDecorator(                  # 30s timeout
            CircuitBreaker(                # Fail-fast
                RetryDecorator(            # 3 retries
                    pipeline
                )
            ),
            timeout=30.0
        )
    )
)

# Use it!
response = await production_agent.process(
    Message(role="user", content="Hello!")
)
```

This gives you:

- ✅ Cross-language communication (Python ↔ Go)
- ✅ Parallel + Sequential composition
- ✅ Automatic retries with exponential backoff
- ✅ Circuit breaker protection
- ✅ 30-second timeout enforcement
- ✅ Prometheus metrics collection
- ✅ Distributed tracing with Jaeger

All with **one simple interface**: `await agent.process(message)`!

---

## Next Steps

- **[Interfaces](interfaces.md)** - Deep dive into the core contracts
- **[Features](../features/index.md)** - Explore each layer in detail
- **[Examples](../examples/index.md)** - See 28+ practical examples
- **[Guides](../guides/index.md)** - Build production systems
