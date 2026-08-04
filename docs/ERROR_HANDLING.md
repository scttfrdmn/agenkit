# Error Handling Guide

Cross-language error type equivalence and handling patterns for agenkit.

---

## Error Type Mapping

| Concept | Python | Go | TypeScript | Rust | C++ | Zig |
|---|---|---|---|---|---|---|
| Base agent error | `AgentError` | `error` interface | `Error` | `AgentError` enum | `AgentError` class | `AgentError` error union |
| LLM / API error | `LLMError` | `*LLMError` | `LLMError extends Error` | `AgentError::LLMError` | `AgentError(LLM_ERROR)` | `AgentError.LLMError` |
| Rate limit error | `RateLimitError` | `*RateLimitError` | `RateLimitError extends Error` | `AgentError::RateLimitError` | `RateLimitError` (middleware) | `AgentError.RateLimitExceeded` |
| Timeout error | `TimeoutError` | `context.DeadlineExceeded` | `TimeoutError extends Error` | `AgentError::Timeout` | `TimeoutError` (middleware) | `AgentError.Timeout` |
| Budget exceeded | `BudgetExceededError` | `*BudgetExceededError` | `BudgetExceededError extends Error` | `AgentError::BudgetExceeded` | — (planned) | — (planned) |
| Validation error | `ValueError` | `fmt.Errorf("...")` | `Error` | `AgentError::InvalidInput` | `AgentError(INVALID_INPUT)` | `AgentError.InvalidInput` |
| Processing failed | `AgentError` | `AgentError` (custom) | `Error` | `AgentError::ProcessingFailed` | `AgentError(PROCESSING_ERROR)` | `AgentError.ProcessingFailed` |
| Not implemented | `NotImplementedError` | `errors.ErrUnsupported` | `Error` | `AgentError::NotImplemented` | — | `AgentError.NotImplemented` |

---

## Common Error Types

### AgentError (base)

Represents any failure during agent processing. All other errors in this guide
are specializations of this concept.

### LLMError

Signals a failure in communicating with or getting a valid response from an LLM
provider. Causes include network failure, authentication errors, and malformed
responses.

### RateLimitError

The LLM provider or a middleware rate limiter has rejected the request due to
excessive throughput. Typically retryable after a backoff delay.

### TimeoutError

A configured time limit was exceeded before the agent returned a response.

### BudgetExceededError

The configured cost budget (session, agent, or global) was exhausted.

### ValidationError / InvalidInput

The input message or parameters did not meet the contract required by the agent.

---

## Language-Specific Patterns

### Python

```python
from agenkit import AgentError, LLMError, RateLimitError, TimeoutError

try:
    response = await agent.process(message)
except BudgetExceededError as e:
    print(f"Over budget: {e}")
except RateLimitError as e:
    await asyncio.sleep(e.retry_after or 60)
    response = await agent.process(message)  # retry
except TimeoutError as e:
    print(f"Timed out: {e}")
except LLMError as e:
    print(f"LLM failure: {e}")
except AgentError as e:
    print(f"Agent error: {e}")
```

**When to use raise vs return:**
- `raise` for errors that are exceptional conditions the caller must decide about.
- Use `Result`-style returns (or `Optional`) only for expected alternate paths.

### Go

```go
import "errors"

response, err := agent.Process(ctx, message)
if err != nil {
    var budgetErr *budget.BudgetExceededError
    var rateErr *middleware.RateLimitError

    switch {
    case errors.As(err, &budgetErr):
        log.Printf("over budget: %v", budgetErr)
    case errors.As(err, &rateErr):
        time.Sleep(rateErr.RetryAfter)
        response, err = agent.Process(ctx, message) // retry
    case errors.Is(err, context.DeadlineExceeded):
        log.Printf("timeout: %v", err)
    default:
        log.Printf("agent error: %v", err)
    }
}
```

**Key Go idioms:**
- Always check errors; never use `_` to discard them without justification.
- Use `errors.Is` for sentinel errors (e.g., `context.DeadlineExceeded`).
- Use `errors.As` for typed error inspection.
- Wrap errors with `fmt.Errorf("operation: %w", err)` to preserve the chain.
- Error messages start lowercase: `"failed to start"` not `"Failed to start"`.

### TypeScript

```typescript
import { BudgetExceededError } from './budget';

try {
  const response = await agent.process(message);
} catch (error: unknown) {
  if (error instanceof BudgetExceededError) {
    console.error(`Over budget (${error.level}): ${error.message}`);
  } else if (error instanceof RateLimitError) {
    await sleep(error.retryAfter ?? 60_000);
    // retry...
  } else if (error instanceof Error) {
    console.error('Agent error:', error.message);
  } else {
    console.error('Unknown error:', error);
  }
}
```

**Key TS idioms:**
- Always type caught errors as `unknown`, not `any`.
- Use `instanceof` guards to narrow the error type safely.
- Prefer `Error` subclasses with structured fields over plain string errors.

### Rust

```rust
use agenkit::{AgentError, Agent};

match agent.process(message).await {
    Ok(response) => { /* use response */ }
    Err(AgentError::RateLimitError { retry_after }) => {
        tokio::time::sleep(retry_after).await;
        // retry...
    }
    Err(AgentError::Timeout) => {
        eprintln!("Request timed out");
    }
    Err(AgentError::BudgetExceeded { limit, current }) => {
        eprintln!("Budget ${limit:.2} exceeded (${current:.4} spent)");
    }
    Err(e) => {
        eprintln!("Agent error: {e}");
    }
}
```

**Key Rust idioms:**
- Use `match` on the `Result` return; never `unwrap()` in production code.
- Use `?` to propagate errors with added context (`map_err` if needed).
- Implement `std::error::Error` for custom types.

### C++

```cpp
#include "agenkit/core/errors.hpp"

auto result = agent->process(message).get();
if (result.is_err()) {
    const auto& error = result.error();
    if (error.code() == "rate_limit_exceeded") {
        std::this_thread::sleep_for(std::chrono::seconds(60));
        // retry...
    } else if (error.code() == "timeout") {
        std::cerr << "Request timed out\n";
    } else if (error.code() == "budget_exceeded") {
        std::cerr << "Budget exceeded: " << error.message() << "\n";
    } else {
        std::cerr << "Agent error: " << error.message() << "\n";
    }
}
```

**Key C++ idioms:**
- Use `Result<T, E>` (the agenkit result type) — do not throw from agent code.
- Check `result.is_ok()` / `result.is_err()` before accessing the value/error.
- Middleware errors (timeout, circuit breaker, rate limit) carry specific `code()` strings.

### Zig

```zig
const result = agent.process(message) catch |err| switch (err) {
    error.RateLimitExceeded => {
        std.time.sleep(60 * std.time.ns_per_s);
        // retry...
        return;
    },
    error.Timeout => {
        std.debug.print("Request timed out\n", .{});
        return;
    },
    else => return err,
};
var response = try result.unwrap();
defer response.deinit();
```

**Key Zig idioms:**
- Use `catch` or `try` — never ignore errors.
- `catch |err| switch (err)` enables per-error branching at the call site.
- Every allocated value must be paired with `defer x.deinit()`.
- Error unions (`AgentError!Result`) are the canonical error-propagation mechanism.

---

## Decision Guide: Error vs Panic vs Result

| Situation | Recommended approach |
|---|---|
| Expected failure that caller should handle (LLM timeout, rate limit) | Return error / `Result::Err` |
| Programming bug / invariant violation | Panic (Go: `panic`, Zig: `unreachable`, Rust: `unreachable!`) |
| Unknown / propagated upstream error | Wrap and return |
| Budget enforcement | Throw/return `BudgetExceededError` |
| Validation at system boundary (user input) | Return validation error |
| Internal, well-tested invariant | Assertion (test-only) |

---

## Retry Guidance

Rate-limit and transient LLM errors are typically retryable. Use the built-in
`RetryMiddleware` / `RetryDecorator` (all languages) rather than implementing
custom retry loops:

```python
# Python
from agenkit.middleware import RetryMiddleware
agent = RetryMiddleware(base_agent, max_retries=3, initial_delay=1.0)
```

```go
// Go
import "github.com/scttfrdmn/agenkit-go/middleware"
agent = middleware.NewRetryMiddleware(baseAgent, middleware.RetryConfig{
    MaxAttempts:    3,
    InitialBackoff: time.Second,
})
```

```typescript
// TypeScript
import { RetryMiddleware } from 'agenkit/middleware';
const agent = new RetryMiddleware(baseAgent, { maxRetries: 3, initialDelay: 1000 });
```

---

## See Also

- `ARCHITECTURE.md` — design decisions behind the error model
- `TESTING.md` — testing error paths
- Per-language middleware docs for `RetryMiddleware`, `TimeoutMiddleware`, etc.
