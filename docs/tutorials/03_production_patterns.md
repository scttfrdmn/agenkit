# Tutorial 3: Production Patterns — Retry, Circuit Breaker, and Observability

An agent that works on a laptop is not production-ready. Real deployments need:

- **Retry** — survive transient LLM API errors without crashing the caller.
- **Circuit breaker** — stop hammering a failing service and give it time to recover.
- **Metrics** — know your error rate and latency at a glance.
- **Tracing** — follow a single request end-to-end across microservices.

All three middleware decorators wrap an `Agent` transparently — your business logic
does not change at all.

---

## Architecture: decorator layering

Middleware decorators stack. Each layer adds one concern:

```
Request
  │
  ▼
MetricsDecorator       ← record latency and error rate
  │
  ▼
CircuitBreakerDecorator ← fail fast when service is unhealthy
  │
  ▼
RetryDecorator          ← retry transient failures with backoff
  │
  ▼
YourAgent               ← actual business logic (unchanged)
```

---

## Python

### Step 1 — RetryDecorator

```python
import asyncio
from agenkit import Agent, Message
from agenkit.middleware import RetryConfig, RetryDecorator

# Imagine this wraps a real LLM client.
class LLMAgent(Agent):
    def __init__(self) -> None:
        self._call_count = 0

    @property
    def name(self) -> str:
        return "llm_agent"

    async def process(self, message: Message) -> Message:
        self._call_count += 1
        # Simulate a transient error on the first two calls
        if self._call_count < 3:
            raise ConnectionError("upstream timeout")
        return Message(role="agent", content=f"Answer to: {message.content}")


async def main() -> None:
    raw_agent = LLMAgent()

    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=0.1,   # 100 ms
        max_delay=2.0,        # cap at 2 s
        multiplier=2.0,       # 100 ms → 200 ms → 400 ms
    )
    agent = RetryDecorator(raw_agent, retry_config)

    msg = Message(role="user", content="What is the capital of France?")

    try:
        response = await agent.process(msg)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"All retries exhausted: {e}")

    m = agent.metrics
    print(f"\nRetry metrics:")
    print(f"  Total attempts       : {m.total_attempts}")
    print(f"  Succeeded on retry   : {m.successful_on_retry}")
    print(f"  Failed after retries : {m.failed_after_retries}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**

```
Response: Answer to: What is the capital of France?

Retry metrics:
  Total attempts       : 3
  Succeeded on retry   : 1
  Failed after retries : 0
```

---

### Step 2 — CircuitBreakerDecorator

```python
import asyncio
from agenkit import Agent, Message
from agenkit.middleware import (
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    CircuitBreakerError,
    CircuitState,
)


class UnreliableAgent(Agent):
    """Always fails — for demonstration."""

    @property
    def name(self) -> str:
        return "unreliable_agent"

    async def process(self, message: Message) -> Message:
        raise RuntimeError("service unavailable")


async def main() -> None:
    raw_agent = UnreliableAgent()

    config = CircuitBreakerConfig(
        failure_threshold=3,        # open after 3 consecutive failures
        recovery_timeout_ms=5000,   # wait 5 s before half-open probe
        success_threshold=2,        # need 2 successes to close again
        timeout_ms=1000,            # per-request timeout
    )
    agent = CircuitBreakerDecorator(raw_agent, config)

    # Drive the circuit open
    for i in range(5):
        msg = Message(role="user", content=f"Request {i + 1}")
        try:
            await agent.process(msg)
        except CircuitBreakerError as e:
            print(f"Request {i + 1}: REJECTED — {e}")
        except Exception as e:
            print(f"Request {i + 1}: FAILED   — {e}")

    m = agent.metrics
    print(f"\nCircuit breaker state : {agent.state.value}")
    print(f"Total requests        : {m.total_requests}")
    print(f"Failed requests       : {m.failed_requests}")
    print(f"Rejected (fast-fail)  : {m.rejected_requests}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**

```
Request 1: FAILED   — service unavailable
Request 2: FAILED   — service unavailable
Request 3: FAILED   — service unavailable
Request 4: REJECTED — Circuit breaker is OPEN (failed 3 times)
Request 5: REJECTED — Circuit breaker is OPEN (failed 3 times)

Circuit breaker state : open
Total requests        : 5
Failed requests       : 3
Rejected (fast-fail)  : 2
```

---

### Step 3 — MetricsDecorator

```python
import asyncio
from agenkit import Agent, Message
from agenkit.middleware import MetricsDecorator


class FastAgent(Agent):
    @property
    def name(self) -> str:
        return "fast_agent"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Done: {message.content}")


async def main() -> None:
    agent = MetricsDecorator(FastAgent())

    for i in range(10):
        msg = Message(role="user", content=f"task {i}")
        await agent.process(msg)

    m = agent.get_metrics()
    print(f"Total requests   : {m.total_requests}")
    print(f"Successful        : {m.success_requests}")
    print(f"Errors            : {m.error_requests}")
    print(f"Error rate        : {m.error_rate():.1%}")
    print(f"Avg latency       : {m.average_latency() * 1000:.2f} ms")
    print(f"Min latency       : {m.min_latency * 1000:.2f} ms")
    print(f"Max latency       : {m.max_latency * 1000:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### Step 4 — Full production stack

Combine all three decorators. The order matters: metrics wraps the outside so it
captures circuit-breaker rejections; retry is innermost so metrics sees aggregated
behaviour.

```python
import asyncio
from agenkit import Agent, Message
from agenkit.middleware import (
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    MetricsDecorator,
    RetryConfig,
    RetryDecorator,
)


class ProductionAgent(Agent):
    @property
    def name(self) -> str:
        return "production_agent"

    async def process(self, message: Message) -> Message:
        # Replace with real LLM call
        return Message(role="agent", content=f"Processed: {message.content}")


def build_production_agent(inner: Agent) -> MetricsDecorator:
    """Wrap an agent with the standard production middleware stack."""
    with_retry = RetryDecorator(
        inner,
        RetryConfig(max_retries=3, initial_delay=0.1, max_delay=5.0, multiplier=2.0),
    )
    with_cb = CircuitBreakerDecorator(
        with_retry,
        CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout_ms=60_000,  # 1 minute
            success_threshold=2,
            timeout_ms=30_000,           # 30 seconds
        ),
    )
    return MetricsDecorator(with_cb)


async def main() -> None:
    agent = build_production_agent(ProductionAgent())

    for i in range(5):
        msg = Message(role="user", content=f"Production request {i + 1}")
        response = await agent.process(msg)
        print(f"Response: {response.content}")

    m = agent.get_metrics()
    print(f"\nTotal requests : {m.total_requests}")
    print(f"Error rate     : {m.error_rate():.1%}")
    print(f"Avg latency    : {m.average_latency() * 1000:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Go

### RetryDecorator

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "time"

    "github.com/scttfrdmn/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit-go/middleware"
)

// LLMAgent simulates a flaky upstream service.
type LLMAgent struct{ callCount int }

func (a *LLMAgent) Name() string { return "llm_agent" }
func (a *LLMAgent) Capabilities() []string { return nil }
func (a *LLMAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *LLMAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    a.callCount++
    if a.callCount < 3 {
        return nil, errors.New("upstream timeout")
    }
    return agenkit.NewMessage("agent", "Answer to: "+msg.ContentString()), nil
}

func main() {
    raw := &LLMAgent{}

    agent := middleware.NewRetryDecorator(raw, middleware.RetryConfig{
        MaxRetries:        3,
        InitialRetryDelay: 100 * time.Millisecond,
        MaxRetryDelay:     2 * time.Second,
        RetryMultiplier:   2.0,
    })

    ctx := context.Background()
    msg := agenkit.NewMessage("user", "What is the capital of France?")

    response, err := agent.Process(ctx, msg)
    if err != nil {
        fmt.Printf("All retries exhausted: %v\n", err)
        return
    }
    fmt.Printf("Response: %s\n", response.Content)

    m := agent.GetMetrics().Snapshot()
    fmt.Printf("\nRetry metrics:\n")
    fmt.Printf("  Total attempts     : %d\n", m.TotalAttempts)
    fmt.Printf("  Succeeded on retry : %d\n", m.SuccessfulOnRetry)
    fmt.Printf("  Failed after max   : %d\n", m.FailedAfterRetries)
}
```

### Full production stack with OpenTelemetry tracing

```go
package main

import (
    "context"
    "fmt"
    "time"

    "github.com/scttfrdmn/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit-go/middleware"
    "github.com/scttfrdmn/agenkit-go/observability"
)

type ProductionAgent struct{}

func (a *ProductionAgent) Name() string { return "production_agent" }
func (a *ProductionAgent) Capabilities() []string { return nil }
func (a *ProductionAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *ProductionAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    return agenkit.NewMessage("agent", "Processed: "+msg.ContentString()), nil
}

func buildProductionAgent(inner agenkit.Agent) *middleware.MetricsDecorator {
    withRetry := middleware.NewRetryDecorator(inner, middleware.RetryConfig{
        MaxRetries:        3,
        InitialRetryDelay: 100 * time.Millisecond,
        MaxRetryDelay:     5 * time.Second,
        RetryMultiplier:   2.0,
    })

    withCB := middleware.NewCircuitBreakerDecorator(
        withRetry,
        middleware.CircuitBreakerConfig{
            FailureThreshold: 5,
            RecoveryTimeout:  60 * time.Second,
            SuccessThreshold: 2,
            Timeout:          30 * time.Second,
        },
    )

    return middleware.NewMetricsDecorator(withCB)
}

func main() {
    ctx := context.Background()

    // Initialize OpenTelemetry tracing.
    //   - Development: 100% sampling, console output
    //   - Production:  set otlpEndpoint to "localhost:4317", consoleExport to false,
    //                  and sampleRate to 0.01 (1%)
    tp, err := observability.InitTracing("my-service", "", true, 1.0)
    if err != nil {
        panic(err)
    }
    defer func() { _ = observability.Shutdown(ctx) }()
    _ = tp

    inner := &ProductionAgent{}

    // Wrap with metrics + circuit breaker + retry
    agent := buildProductionAgent(inner)

    // Add distributed tracing on top
    traced := observability.NewTracingMiddleware(agent, "")

    for i := 1; i <= 5; i++ {
        msg := agenkit.NewMessage("user", fmt.Sprintf("Production request %d", i))
        response, err := traced.Process(ctx, msg)
        if err != nil {
            fmt.Printf("Request %d failed: %v\n", i, err)
            continue
        }
        fmt.Printf("Response: %s\n", response.Content)
    }

    m := agent.GetMetrics().Snapshot()
    fmt.Printf("\nTotal requests : %d\n", m.TotalRequests)
    fmt.Printf("Error rate     : %.1f%%\n", m.ErrorRate()*100)
    fmt.Printf("Avg latency    : %v\n", agent.GetMetrics().AverageLatency())
}
```

---

## Tuning guide

### RetryConfig

| Parameter | Default | Recommendation |
|---|---|---|
| `max_retries` | 3 | 3 for LLMs; 1 for non-idempotent calls |
| `initial_delay` | 100 ms | Keep short; backoff handles the rest |
| `max_delay` | 10 s | Match your SLA budget |
| `multiplier` | 2.0 | Standard exponential backoff |

Use `should_retry` (Python) / `ShouldRetry` (Go) to skip retries for 4xx errors
that will never succeed:

```python
def is_transient(exc: Exception) -> bool:
    # Don't retry bad-request errors from the LLM API
    return "invalid_request_error" not in str(exc)

config = RetryConfig(max_retries=3, should_retry=is_transient)
```

### CircuitBreakerConfig

| Parameter | Default | Recommendation |
|---|---|---|
| `failure_threshold` | 5 | Lower (3) for critical paths |
| `recovery_timeout_ms` | 60 000 | Matches most LLM API SLAs |
| `success_threshold` | 2 | Conservative; prevents premature close |
| `timeout_ms` | 30 000 | Set to your 99th-percentile latency × 2 |

### OpenTelemetry (Go)

```go
// Development — 100% sampling, console output
tp, _ := observability.InitTracing("my-service", "", true, 1.0)

// Staging — 10% sampling, send to local collector
tp, _ := observability.InitTracing("my-service", "localhost:4317", false, 0.10)

// Production — 1% sampling, send to hosted collector
tp, _ := observability.InitTracing("my-service", "otel-collector:4317", false, 0.01)
```

---

## Next Steps

Continue to **[Tutorial 4: Long-Running Agents and Checkpointing](./04_long_running_agents.md)**
to learn how to build agents that survive process restarts and run for hours or days.
