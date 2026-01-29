# Migration Guide: v0.49.0 → v0.50.0

**Breaking Changes Required**: Yes
**Impact**: All 6 languages affected
**Release Date**: TBD
**Related Issues**: #502, #503, #504

---

## Overview

Version 0.50.0 introduces breaking changes to standardize timeout units and API signatures across all languages. These changes improve clarity, reduce confusion, and align with language-specific best practices.

**Key Changes**:
1. **Timeout units** standardized to milliseconds (Python changes from seconds)
2. **Parameter naming** clarified to indicate units explicitly
3. **Tool execution** signatures unified (Python changes from `**kwargs` to explicit `params`)

---

## 1. Timeout Units Standardization

### Problem

Timeout units were inconsistent across languages, causing migration pain and confusion:
- **Python**: Used seconds (float) - `TimeoutConfig(timeout=30.0)`
- **TypeScript**: Used milliseconds (number) - `TimeoutConfig { timeout: 30000 }`
- **Go**: Used time.Duration (native) - `TimeoutConfig{Timeout: 30 * time.Second}`
- **Rust**: Used Duration (native) - `TimeoutConfig { timeout: Duration::from_secs(30) }`
- **C++**: Used milliseconds (int) but named field `timeout_seconds` - MISLEADING!
- **Zig**: Used milliseconds (u64) with clear naming - `timeout_ms: 30000`

### Solution

**Languages with primitive types** (Python, TypeScript, C++, Zig) now use milliseconds with clear naming.
**Languages with native Duration types** (Go, Rust) keep their native types (already clear).

---

## Python Migration (BREAKING)

### Timeout Configuration

**Old Code (v0.49.0)**:
```python
from agenkit.middleware import TimeoutConfig, TimeoutMiddleware

# Timeout in SECONDS
config = TimeoutConfig(timeout=30.0)  # 30 seconds
middleware = TimeoutMiddleware(agent, config)
```

**New Code (v0.50.0)**:
```python
from agenkit.middleware import TimeoutConfig, TimeoutMiddleware

# Timeout in MILLISECONDS
config = TimeoutConfig(timeout_ms=30000)  # 30 seconds = 30000ms
middleware = TimeoutMiddleware(agent, config)
```

### All Timeout Parameters

**Changed parameters**:
- `TimeoutConfig.timeout` → `TimeoutConfig.timeout_ms`
- `RateLimiterConfig.max_wait_timeout` → `RateLimiterConfig.max_wait_ms`
- `CircuitBreakerConfig.timeout` → `CircuitBreakerConfig.timeout_ms`
- `CircuitBreakerConfig.recovery_timeout` → `CircuitBreakerConfig.recovery_timeout_ms`
- All LLM adapter `timeout` parameters → `timeout_ms`

### Deprecation Warnings (v0.50.0 → v0.51.0)

Version 0.50.0 accepts both old and new parameters with deprecation warnings:

```python
# v0.50.0: Both work, but old syntax warns
config = TimeoutConfig(timeout=30.0)  # ⚠️  DeprecationWarning
# Warning: The 'timeout' parameter (in seconds) is deprecated and will be removed in v0.51.0.
# Use 'timeout_ms' (in milliseconds) instead. To migrate: timeout_ms=30000

config = TimeoutConfig(timeout_ms=30000)  # ✓ No warning

# v0.51.0: Old syntax removed
config = TimeoutConfig(timeout=30.0)  # ❌ TypeError: unexpected keyword argument
    @deprecated("Use timeout_ms instead. Will be removed in v0.51.0")
    def timeout(self) -> float:
        """Returns timeout in seconds for backward compatibility."""
        return self.timeout_ms / 1000.0
```

**Migration window**: v0.50.0 - v0.51.0 (one release cycle)

### Error Messages

**Old (v0.49.0)**:
```
Request timed out after 30.0s
```

**New (v0.50.0)**:
```
Request timed out after 30000ms
```

---

## TypeScript Migration

### Timeout Configuration

**Old Code (v0.49.0)**:
```typescript
import { TimeoutConfig, TimeoutMiddleware } from 'agenkit';

// Timeout in milliseconds (but unclear naming)
const config: TimeoutConfig = { timeout: 30000 };
const middleware = new TimeoutMiddleware(agent, config);
```

**New Code (v0.50.0)**:
```typescript
import { TimeoutConfig, TimeoutMiddleware } from 'agenkit';

// Timeout in milliseconds (CLEAR naming)
const config: TimeoutConfig = { timeoutMs: 30000 };
const middleware = new TimeoutMiddleware(agent, config);
```

### All Timeout Parameters

**Changed parameters**:
- `timeout` → `timeoutMs`
- `initialDelay` → `initialDelayMs`
- `maxWaitTimeout` → `maxWaitMs`

**Note**: TypeScript already used milliseconds - this is just a naming clarification.

---

## C++ Migration

### Timeout Configuration

**Old Code (v0.49.0)**:
```cpp
#include <agenkit/middleware/timeout.hpp>

// MISLEADING: Field named "seconds" but stores milliseconds!
TimeoutConfig config{
    .timeout_seconds = 30000  // Actually 30000 milliseconds!
};
```

**New Code (v0.50.0)**:
```cpp
#include <agenkit/middleware/timeout.hpp>

// CLEAR: Field name matches unit
TimeoutConfig config{
    .timeout_ms = 30000  // 30000 milliseconds
};
```

**Note**: This fixes a critical misleading naming issue where the field was named `timeout_seconds` but actually stored milliseconds.

---

## Go Migration (NO BREAKING CHANGES)

Go already uses idiomatic `time.Duration` type, which is self-documenting:

```go
import "time"

// No changes needed - Duration type is clear
config := middleware.TimeoutConfig{
    Timeout: 30 * time.Second,  // Native Duration type
}
```

**Action**: No migration required for Go code.

---

## Rust Migration (NO BREAKING CHANGES)

Rust already uses native `Duration` type:

```rust
use std::time::Duration;

// No changes needed - Duration type is clear
let config = TimeoutConfig {
    timeout: Duration::from_secs(30),  // Native Duration type
};
```

**Action**: No migration required for Rust code.

---

## Zig Migration (NO BREAKING CHANGES)

Zig already uses clear millisecond naming:

```zig
// No changes needed - already clear
const config = TimeoutConfig{
    .timeout_ms = 30000,  // Already clear naming
};
```

**Action**: No migration required for Zig code.

---

## 2. Tool Execution Signature Changes

### Problem

Python's `Tool.execute()` used `**kwargs` while other languages used explicit parameter dictionaries.

### Python Tool Interface (BREAKING)

**Old Code (v0.49.0)**:
```python
from agenkit import Tool, ToolResult

class MyTool(Tool):
    async def execute(self, **kwargs) -> ToolResult:
        # Access via kwargs
        value = kwargs.get("arg1")
        count = kwargs.get("arg2", 0)

        return ToolResult(output=f"Processed: {value}")
```

**New Code (v0.50.0)**:
```python
from agenkit import Tool, ToolResult
from typing import Any

class MyTool(Tool):
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        # Access via explicit params dict
        value = params.get("arg1")
        count = params.get("arg2", 0)

        return ToolResult(output=f"Processed: {value}")
```

**Why**: Explicit `params` dict aligns with other languages and makes the interface clearer.

### TypeScript Tool Interface (NEW)

Added optional `AbortSignal` for cancellation support:

**Old Code (v0.49.0)**:
```typescript
interface Tool {
    execute(params: Record<string, unknown>): Promise<ToolResult>;
}
```

**New Code (v0.50.0)**:
```typescript
interface Tool {
    execute(
        params: Record<string, unknown>,
        signal?: AbortSignal  // NEW: Optional cancellation support
    ): Promise<ToolResult>;
}
```

**Migration**: Add optional `signal?: AbortSignal` parameter. Existing tools continue to work (parameter is optional).

---

## 3. Parameter Naming Standardization

### Retry Parameters

**Rust** - Renamed for consistency:

**Old**:
```rust
RetryConfig {
    max_attempts: 3,  // Inconsistent with other languages
    initial_delay: Duration::from_millis(100),
}
```

**New**:
```rust
RetryConfig {
    max_retries: 3,  // Consistent with Python/Go/TypeScript
    initial_delay: Duration::from_millis(100),
}
```

---

## Migration Timeline

### v0.50.0 (Current Release)

- **Breaking changes introduced** with deprecation warnings
- Python: `timeout` property deprecated, use `timeout_ms`
- Python: `**kwargs` in Tool.execute deprecated, use `params`
- All deprecated APIs still functional with warnings

### v0.51.0 (Next Release)

- **Deprecated APIs removed**
- Python: `timeout` property removed
- Must use new APIs exclusively

**Recommendation**: Migrate during v0.50.0 to avoid breaking changes in v0.51.0.

---

## Quick Migration Checklist

### Python Developers

- [ ] Replace `timeout=` with `timeout_ms=` (multiply by 1000)
- [ ] Replace `max_wait_timeout=` with `max_wait_ms=` (multiply by 1000)
- [ ] Update all timeout error handling (messages now show milliseconds)
- [ ] Change Tool.execute() from `**kwargs` to `params: dict[str, Any]`
- [ ] Update tool implementations to access `params` instead of `kwargs`
- [ ] Run tests to catch any missed conversions

### TypeScript Developers

- [ ] Rename `timeout` → `timeoutMs` in all configs
- [ ] Rename `initialDelay` → `initialDelayMs`
- [ ] Rename `maxWaitTimeout` → `maxWaitMs`
- [ ] Add optional `signal?: AbortSignal` to tool implementations
- [ ] Run type checker to find remaining issues

### C++ Developers

- [ ] Rename `timeout_seconds` → `timeout_ms` in all configs
- [ ] Verify values are in milliseconds (no conversion needed)
- [ ] Update comments/documentation referencing seconds

### Rust Developers

- [ ] Rename `max_attempts` → `max_retries` in retry configs
- [ ] No other changes required (Duration type is self-documenting)

### Go Developers

- [ ] No changes required (time.Duration is idiomatic)

### Zig Developers

- [ ] No changes required (already uses `timeout_ms`)

---

## Testing Your Migration

### Python

```bash
# Run tests with deprecation warnings visible
uv run pytest tests/ -W default::DeprecationWarning

# Check for any remaining uses of old API
rg "timeout=" agenkit/ --type py
rg "\*\*kwargs" agenkit/ --type py
```

### TypeScript

```bash
# Type checker will catch most issues
npm run type-check

# Search for old patterns
grep -r "timeout:" src/ --include="*.ts"
grep -r "initialDelay:" src/ --include="*.ts"
```

### C++

```bash
# Search for misleading old naming
grep -r "timeout_seconds" include/ --include="*.hpp"
```

---

## Getting Help

- **GitHub Issues**: https://github.com/scttfrdmn/agenkit/issues
  - Issue #502: Timeout standardization
  - Issue #503: Parameter naming
  - Issue #504: Tool signatures

- **Documentation**: See `ARCHITECTURE.md` for design rationale

- **Migration Support**: Create an issue with `migration-help` label

---

## Appendix: Complete Timeout Parameter Mapping

### Python

| Old (v0.49.0) | New (v0.50.0) | Conversion |
|---------------|---------------|------------|
| `timeout=30.0` (seconds) | `timeout_ms=30000` (milliseconds) | `* 1000` |
| `max_wait_timeout=5.0` | `max_wait_ms=5000` | `* 1000` |
| `recovery_timeout=60.0` | `recovery_timeout_ms=60000` | `* 1000` |

### TypeScript

| Old (v0.49.0) | New (v0.50.0) | Conversion |
|---------------|---------------|------------|
| `timeout: 30000` | `timeoutMs: 30000` | None (clarity only) |
| `initialDelay: 100` | `initialDelayMs: 100` | None (clarity only) |
| `maxWaitTimeout: 5000` | `maxWaitMs: 5000` | None (clarity only) |

### C++

| Old (v0.49.0) | New (v0.50.0) | Conversion |
|---------------|---------------|------------|
| `timeout_seconds: 30000` (MISLEADING!) | `timeout_ms: 30000` | None (fix naming) |

**Note**: Go, Rust, and Zig have no breaking changes.

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026
**Supersedes**: N/A (First major breaking change release)
