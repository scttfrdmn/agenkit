# Middleware Patterns

## Table of Contents
- [Philosophy](#philosophy)
- [Core Concepts](#core-concepts)
- [Design Patterns](#design-patterns)
- [When to Write Custom Middleware](#when-to-write-custom-middleware)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Philosophy

Middleware in agenkit follows the **decorator pattern** from Gang of Four. The core philosophy is:

1. **Separation of Concerns**: Cross-cutting concerns (logging, metrics, retry) separate from business logic
2. **Composability**: Stack multiple middleware layers without modification
3. **Transparency**: Middleware should be invisible to the wrapped agent
4. **Zero Overhead**: When not triggered, add minimal latency

### Why Middleware?

```python
# Without middleware (cross-cutting concerns mixed with logic)
class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Metrics collection
        start = time.time()
        self.request_count += 1

        # Retry logic
        for attempt in range(3):
            try:
                # Actual logic (buried in noise)
                result = await self._do_work(message)
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

        # More metrics
        self.latency += time.time() - start
        return result

# With middleware (clean separation)
class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        return await self._do_work(message)  # Pure business logic

# Compose with middleware
agent = RetryDecorator(
    MetricsDecorator(MyAgent()),
    config=RetryConfig(max_attempts=3)
)
```

**Benefits:**
- Business logic is clear and testable
- Cross-cutting concerns are reusable
- Easy to add/remove/reorder middleware
- Each middleware is independently testable

## Core Concepts

### The Middleware Contract

All middleware must implement the `Agent` interface:

```python
from agenkit.interfaces import Agent, Message

class MyMiddleware(Agent):
    def __init__(self, agent: Agent):
        self._agent = agent  # Wrapped agent

    @property
    def name(self) -> str:
        return self._agent.name  # Delegate to wrapped agent

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities  # Delegate to wrapped agent

    async def process(self, message: Message) -> Message:
        # Before: Pre-processing logic
        message = self._before_process(message)

        # Delegate: Call wrapped agent
        result = await self._agent.process(message)

        # After: Post-processing logic
        result = self._after_process(result)

        return result
```

### Middleware Lifecycle

```
Request → Middleware 1 → Middleware 2 → Agent → Middleware 2 → Middleware 1 → Response
          [before]       [before]        [process]  [after]      [after]
```

Example with metrics and retry:

```
Request → MetricsDecorator → RetryDecorator → Agent
          [start timer]       [try attempt 1]  [process]
                              [retry on error]
          [record latency]    [success]
```

### Composition Order Matters

```python
# Metrics outside retry: Measures total time including retries
MetricsDecorator(RetryDecorator(agent))
# Result: Latency includes all retry attempts

# Retry outside metrics: Metrics only for successful attempt
RetryDecorator(MetricsDecorator(agent))
# Result: Latency only for final successful call
```

**Rule of thumb:** Order from outermost concern to innermost:
1. Authentication (outermost - verify first)
2. Metrics (measure everything)
3. Retry (after metrics capture failures)
4. Caching (after retry, closest to agent)
5. Agent (innermost - business logic)

## Design Patterns

### 1. Decorator Pattern (Core Pattern)

**Intent:** Add responsibilities to objects dynamically.

```python
class LoggingMiddleware(Agent):
    """Logs all requests and responses."""

    def __init__(self, agent: Agent, logger: logging.Logger):
        self._agent = agent
        self._logger = logger

    async def process(self, message: Message) -> Message:
        self._logger.info(f"Request to {self._agent.name}: {message.content}")
        result = await self._agent.process(message)
        self._logger.info(f"Response from {self._agent.name}: {result.content}")
        return result
```

**When to use:** All middleware (it's the foundation)

### 2. Chain of Responsibility

**Intent:** Pass request along chain of handlers.

```python
class MiddlewareChain(Agent):
    """Execute multiple middleware in order."""

    def __init__(self, agent: Agent, middleware: list[type]):
        self._agent = agent
        # Build chain from innermost to outermost
        for mw_class in reversed(middleware):
            self._agent = mw_class(self._agent)

    async def process(self, message: Message) -> Message:
        return await self._agent.process(message)

# Usage
agent = MiddlewareChain(
    MyAgent(),
    middleware=[
        AuthMiddleware,
        MetricsMiddleware,
        RetryMiddleware
    ]
)
```

**When to use:** Multiple middleware with common configuration

### 3. Strategy Pattern (Configurable Behavior)

**Intent:** Define family of algorithms, make them interchangeable.

```python
class RetryDecorator(Agent):
    """Retry with configurable strategy."""

    def __init__(self, agent: Agent, config: RetryConfig):
        self._agent = agent
        self._should_retry = config.should_retry  # Strategy!
        self._max_attempts = config.max_attempts

    async def process(self, message: Message) -> Message:
        for attempt in range(self._max_attempts):
            try:
                return await self._agent.process(message)
            except Exception as e:
                # Strategy decides whether to retry
                if not self._should_retry(e):
                    raise
                if attempt == self._max_attempts - 1:
                    raise

# Different strategies
def retry_transient_only(error: Exception) -> bool:
    return "timeout" in str(error).lower()

def retry_all_errors(error: Exception) -> bool:
    return True

agent1 = RetryDecorator(agent, RetryConfig(should_retry=retry_transient_only))
agent2 = RetryDecorator(agent, RetryConfig(should_retry=retry_all_errors))
```

**When to use:** Middleware behavior needs to be configurable

### 4. Observer Pattern (Event Notification)

**Intent:** Notify observers of state changes.

```python
class ObservableMiddleware(Agent):
    """Notify listeners of agent events."""

    def __init__(self, agent: Agent):
        self._agent = agent
        self._listeners: list[Callable] = []

    def add_listener(self, listener: Callable):
        self._listeners.append(listener)

    async def process(self, message: Message) -> Message:
        # Notify before
        for listener in self._listeners:
            listener("before", self._agent, message)

        result = await self._agent.process(message)

        # Notify after
        for listener in self._listeners:
            listener("after", self._agent, result)

        return result

# Usage
def log_events(phase: str, agent: Agent, msg: Message):
    print(f"{phase}: {agent.name} - {msg.content}")

agent = ObservableMiddleware(MyAgent())
agent.add_listener(log_events)
```

**When to use:** Need to monitor agent behavior from outside

## When to Write Custom Middleware

### ✅ Write Middleware For:

1. **Cross-Cutting Concerns**
   - Logging, metrics, tracing
   - Authentication, authorization
   - Rate limiting, throttling
   - Caching, memoization

2. **Infrastructure Patterns**
   - Retry, circuit breaker, bulkhead
   - Timeout, deadline enforcement
   - Request/response transformation
   - Error handling, sanitization

3. **Observability**
   - Performance monitoring
   - Error tracking
   - Audit logging
   - Distributed tracing

4. **Quality of Service**
   - Load shedding
   - Priority queuing
   - Backpressure
   - Resource limiting

### ❌ Don't Write Middleware For:

1. **Business Logic**
   - Domain-specific transformations
   - Application-specific validation
   - Use agents or tools instead

2. **One-Off Operations**
   - Single-use transformations
   - Just write a function

3. **Complex State Management**
   - Middleware should be stateless or use simple state
   - Use agents for complex state

4. **Agent-Specific Behavior**
   - If it only applies to one agent, put it in the agent

### Decision Tree

```
Need cross-cutting concern?
├─ Yes → Applies to multiple agents?
│  ├─ Yes → Write middleware ✅
│  └─ No → Put in agent class
└─ No → Is it infrastructure?
   ├─ Yes → Write middleware ✅
   └─ No → Use agent or tool
```

## Performance Considerations

### Latency Impact

**Measurement methodology:**
```python
import time

async def measure_middleware_overhead():
    # Baseline: Direct agent call
    agent = MyAgent()
    start = time.perf_counter()
    await agent.process(message)
    baseline = time.perf_counter() - start

    # With middleware
    wrapped = MyMiddleware(agent)
    start = time.perf_counter()
    await wrapped.process(message)
    with_middleware = time.perf_counter() - start

    overhead = (with_middleware - baseline) / baseline * 100
    print(f"Overhead: {overhead:.1f}%")
```

**Typical overheads:**
- MetricsDecorator: 1-2% (time.time() calls)
- RetryDecorator: 0% if no retry, 100%+ per retry
- CacheDecorator: 5-10% (hash computation, lookup)
- LoggingDecorator: 2-5% (string formatting, I/O)

### Optimization Strategies

#### 1. Minimize Allocations

```python
# ❌ Slow: Creates new dict every call
async def process(self, message: Message) -> Message:
    metadata = {**message.metadata, "middleware": self.name}
    message = Message(role=message.role, content=message.content, metadata=metadata)
    return await self._agent.process(message)

# ✅ Fast: Reuse objects when possible
async def process(self, message: Message) -> Message:
    if self._needs_metadata:
        message.metadata["middleware"] = self.name
    return await self._agent.process(message)
```

#### 2. Cache Attribute Lookups

```python
# ❌ Slow: Repeated attribute lookups
async def process(self, message: Message) -> Message:
    for attempt in range(self._config.max_attempts):
        try:
            if self._config.should_retry:  # Lookup on each iteration
                return await self._agent.process(message)
        except Exception:
            pass

# ✅ Fast: Cache in local
async def process(self, message: Message) -> Message:
    max_attempts = self._config.max_attempts  # Cache once
    should_retry = self._config.should_retry

    for attempt in range(max_attempts):
        try:
            if should_retry:
                return await self._agent.process(message)
        except Exception:
            pass
```

#### 3. Lazy Initialization

```python
# ✅ Only create expensive objects when needed
class MetricsMiddleware(Agent):
    def __init__(self, agent: Agent):
        self._agent = agent
        self._metrics: Optional[Metrics] = None  # Lazy

    async def process(self, message: Message) -> Message:
        if self._metrics is None:
            self._metrics = Metrics()  # Create on first use

        self._metrics.record_start()
        result = await self._agent.process(message)
        self._metrics.record_end()
        return result
```

#### 4. Batch Operations

```python
class BatchMetricsMiddleware(Agent):
    """Buffer metrics and flush periodically."""

    def __init__(self, agent: Agent, buffer_size: int = 100):
        self._agent = agent
        self._buffer = []
        self._buffer_size = buffer_size

    async def process(self, message: Message) -> Message:
        start = time.time()
        result = await self._agent.process(message)

        # Buffer instead of immediate write
        self._buffer.append({
            "latency": time.time() - start,
            "timestamp": start
        })

        # Flush when buffer full
        if len(self._buffer) >= self._buffer_size:
            await self._flush()

        return result
```

### Memory Considerations

**Be careful with:**
- Long-lived references (memory leaks)
- Large buffers (unbounded growth)
- Per-request objects (GC pressure)

```python
# ❌ Memory leak: Never clears
class LeakyMiddleware(Agent):
    def __init__(self, agent: Agent):
        self._agent = agent
        self._all_requests = []  # Grows forever!

    async def process(self, message: Message) -> Message:
        self._all_requests.append(message)
        return await self._agent.process(message)

# ✅ Bounded memory
class BoundedMiddleware(Agent):
    def __init__(self, agent: Agent, max_history: int = 1000):
        self._agent = agent
        self._requests = deque(maxlen=max_history)  # Bounded

    async def process(self, message: Message) -> Message:
        self._requests.append(message)
        return await self._agent.process(message)
```

## Best Practices

### 1. Single Responsibility

Each middleware should do **one thing well**.

```python
# ❌ Bad: Multiple responsibilities
class MegaMiddleware(Agent):
    async def process(self, message: Message) -> Message:
        # Logs
        logger.info(f"Request: {message}")

        # Metrics
        start = time.time()

        # Retry
        for attempt in range(3):
            try:
                result = await self._agent.process(message)
                break
            except Exception:
                pass

        # More metrics
        duration = time.time() - start
        metrics.record(duration)

        # More logging
        logger.info(f"Response: {result}")

        return result

# ✅ Good: Separate middleware
agent = LoggingMiddleware(
    MetricsMiddleware(
        RetryMiddleware(agent)
    )
)
```

### 2. Configuration Objects

Use configuration objects instead of many parameters.

```python
# ❌ Bad: Parameter explosion
class RetryMiddleware(Agent):
    def __init__(
        self,
        agent: Agent,
        max_attempts: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_multiplier: float = 2.0,
        should_retry: Callable = None,
        jitter: bool = True,
        # ... more parameters
    ):
        pass

# ✅ Good: Configuration object
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 60.0
    backoff_multiplier: float = 2.0
    should_retry: Callable = lambda e: True
    jitter: bool = True

class RetryMiddleware(Agent):
    def __init__(self, agent: Agent, config: RetryConfig = None):
        self._agent = agent
        self._config = config or RetryConfig()
```

### 3. Transparent Delegation

Middleware should be invisible to callers.

```python
class TransparentMiddleware(Agent):
    """Delegates name and capabilities to wrapped agent."""

    def __init__(self, agent: Agent):
        self._agent = agent

    @property
    def name(self) -> str:
        return self._agent.name  # Transparent

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities  # Transparent

    async def process(self, message: Message) -> Message:
        # Do middleware work
        return await self._agent.process(message)  # Delegate
```

### 4. Preserve Metadata

Don't lose information from wrapped agent.

```python
# ❌ Bad: Loses metadata
async def process(self, message: Message) -> Message:
    result = await self._agent.process(message)
    return Message(
        role="agent",
        content=result.content
        # Oops, lost result.metadata!
    )

# ✅ Good: Preserves and extends
async def process(self, message: Message) -> Message:
    result = await self._agent.process(message)
    result.metadata["middleware_applied"] = self.name
    return result
```

### 5. Error Handling

Be explicit about error handling strategy.

```python
class ErrorHandlingMiddleware(Agent):
    """Template for error handling in middleware."""

    async def process(self, message: Message) -> Message:
        try:
            # Before
            self._before_process(message)

            # Delegate
            result = await self._agent.process(message)

            # After (success path)
            self._after_success(result)

            return result

        except Exception as e:
            # After (error path)
            self._after_error(e)

            # Decide: reraise, transform, or handle
            raise  # Usually reraise to preserve stack trace

        finally:
            # Cleanup always runs
            self._cleanup()
```

### 6. Testing Strategy

Test middleware in isolation and composition.

```python
# Test in isolation
async def test_retry_middleware():
    # Mock agent that fails twice then succeeds
    mock_agent = FailingAgent(fail_count=2)

    # Test retry middleware
    retry_agent = RetryMiddleware(mock_agent, RetryConfig(max_attempts=3))

    result = await retry_agent.process(Message(role="user", content="test"))
    assert result is not None
    assert mock_agent.attempt_count == 3

# Test composition
async def test_middleware_stack():
    agent = MyAgent()
    wrapped = MetricsMiddleware(
        RetryMiddleware(
            LoggingMiddleware(agent)
        )
    )

    result = await wrapped.process(Message(role="user", content="test"))

    # Verify each middleware did its job
    assert metrics.total_requests > 0
    assert len(log_buffer) > 0
```

## Examples

See the `/examples/middleware/` directory for complete, runnable examples:

- **`retry_example.py`**: Exponential backoff, custom retry logic
- **`metrics_example.py`**: Observability, monitoring, capacity planning

### Quick Reference: Common Middleware

```python
# Metrics: Collect latency, error rate, throughput
agent = MetricsMiddleware(agent)
metrics = agent.get_metrics()

# Retry: Handle transient failures
agent = RetryMiddleware(
    agent,
    RetryConfig(
        max_attempts=3,
        initial_backoff=1.0,
        should_retry=lambda e: "timeout" in str(e)
    )
)

# Caching: Memoize expensive operations
agent = CacheMiddleware(
    agent,
    cache_key=lambda msg: hash(msg.content),
    ttl=300  # 5 minutes
)

# Timeout: Enforce deadlines
agent = TimeoutMiddleware(
    agent,
    timeout=30.0  # seconds
)

# Logging: Debug and audit
agent = LoggingMiddleware(
    agent,
    logger=logging.getLogger(__name__)
)

# Rate Limiting: Throttle requests
agent = RateLimitMiddleware(
    agent,
    max_requests=100,
    window=60  # per minute
)
```

### Middleware Composition Examples

```python
# Reliability stack
agent = RetryMiddleware(
    TimeoutMiddleware(
        CircuitBreakerMiddleware(agent)
    )
)

# Observability stack
agent = LoggingMiddleware(
    MetricsMiddleware(
        TracingMiddleware(agent)
    )
)

# Full production stack
agent = AuthMiddleware(            # 1. Verify identity
    RateLimitMiddleware(           # 2. Enforce limits
        MetricsMiddleware(         # 3. Collect metrics
            LoggingMiddleware(     # 4. Log for debugging
                RetryMiddleware(   # 5. Handle failures
                    CacheMiddleware(  # 6. Optimize performance
                        agent      # 7. Business logic
                    )
                )
            )
        )
    )
)
```

---

## Summary

**Middleware is essential for:**
- Separation of concerns (clean code)
- Reusability (write once, use everywhere)
- Composition (stack behaviors)
- Production readiness (metrics, retry, etc.)

**Key principles:**
- Single responsibility
- Transparent delegation
- Configuration over parameters
- Preserve metadata
- Test in isolation

**Performance:**
- Typical overhead: 1-5%
- Optimize hot paths
- Use lazy initialization
- Batch where possible

**Next:** See [COMPOSITION.md](./COMPOSITION.md) for agent composition patterns.
