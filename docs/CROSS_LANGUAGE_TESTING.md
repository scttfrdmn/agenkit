# Cross-Language API Consistency Testing

**Version**: 1.0
**Last Updated**: January 30, 2026
**Status**: In Development

## Overview

This document specifies the cross-language API consistency test suite for Agenkit. The goal is to ensure that APIs behave consistently across all 6 languages while respecting idiomatic patterns.

## Test Categories

### 1. Interface Signature Consistency

Verify that core interfaces have equivalent signatures across languages (accounting for idioms).

#### Tool Interface
- **Method**: `execute(params) -> Result`
- **Parameters**: Dictionary/Map of string keys to values
- **Context**: Go has explicit `context.Context`, TypeScript has optional `AbortSignal`
- **Return**: 
  - Python: `ToolResult` (exceptions for errors)
  - Go: `(*ToolResult, error)` tuple
  - TypeScript: `Promise<ToolResult>` (throws for errors)
  - Rust: `Result<ToolResult, AgentError>`
  - C++: `std::future<Result<ToolResult, AgentError>>`
  - Zig: `ToolError!ToolResult`

**Test**: Verify each language has these components in their Tool interface.

#### Agent Interface
- **Method**: `process(message) -> Response`
- **Parameters**: Message object
- **Optional**: Streaming support via `processStream` or `Stream`
- **Return**: Similar pattern to Tool (language-specific error handling)

**Test**: Verify each language has process method with Message parameter.

#### Message Structure
All languages should have:
- `role`: string (user/assistant/system/tool)
- `content`: string
- `metadata`: optional dictionary/map

**Test**: Serialize Message to JSON in each language, verify structure matches.

### 2. Parameter Naming Consistency

#### Timeout Parameters
- **Go/Rust**: Use `timeout: Duration` (native types, self-documenting)
- **Python**: Should use `timeout_ms: int` or `timeout: timedelta`
- **TypeScript**: Should use `timeoutMs: number`
- **C++**: Uses `std::chrono::milliseconds` (type-safe)
- **Zig**: Uses `timeout_ms: u64` (clear naming)

**Test**: Verify parameter names include unit indicators (except for Duration types).

#### Retry Parameters
All languages should use:
- `max_retries` (NOT max_attempts) - **Now consistent!**
- `initial_delay` or `initial_delay_ms`
- `max_delay` or `max_delay_ms`
- `multiplier` (backoff multiplier)

**Test**: Verify parameter names in RetryConfig/Builder across all languages.

### 3. Default Value Consistency

#### Timeout Middleware
- Default timeout: **30 seconds** (30000ms or 30*time.Second or Duration::from_secs(30))

#### Retry Middleware
- `max_retries`: **3**
- `initial_delay`: **100ms**
- `max_delay`: **10 seconds**
- `multiplier`: **2.0**

#### Rate Limiter
- `rate`: Varies by use case (document if different)
- `capacity`: Varies by use case (document if different)

**Test**: Create default configs in each language, verify values match.

### 4. Error Handling Patterns

Verify each language uses its idiomatic error handling:

#### Python
```python
try:
    result = tool.execute(params)
except AgentError as e:
    # Handle error
```

#### Go
```go
result, err := tool.Execute(ctx, params)
if err != nil {
    // Handle error
}
```

#### TypeScript
```typescript
try {
    const result = await tool.execute(params);
} catch (error) {
    // Handle error
}
```

#### Rust
```rust
match tool.execute(params).await {
    Ok(result) => { /* Use result */ }
    Err(e) => { /* Handle error */ }
}
```

#### C++
```cpp
auto future = tool->execute(params);
auto result = future.get();
if (result.is_err()) {
    // Handle error
}
```

#### Zig
```zig
const result = tool.execute(params, allocator) catch |err| {
    // Handle error
};
```

**Test**: Verify error handling follows documented patterns.

### 5. Serialization Compatibility

#### Message Serialization
All languages should produce compatible JSON:

```json
{
  "role": "user",
  "content": "Hello, world!",
  "metadata": {
    "source": "test"
  }
}
```

**Test**: 
1. Create Message in each language
2. Serialize to JSON
3. Verify JSON structure matches
4. Deserialize in different language
5. Verify round-trip works

#### Tool Result Serialization
```json
{
  "success": true,
  "data": { "result": "value" },
  "error": null
}
```

**Test**: Similar round-trip test for ToolResult.

### 6. Behavior Consistency

#### Retry Behavior
Given same config and failure pattern, all languages should:
- Retry same number of times
- Use same delay calculations
- Produce similar timing (within 10% variance)

**Test**: Mock failing agent, verify retry attempts and delays.

#### Timeout Behavior
Given same timeout config:
- All languages timeout at approximately same time (within 100ms variance)
- All produce timeout errors with similar messages

**Test**: Mock slow agent, verify timeout occurs correctly.

#### Rate Limiting Behavior
Given same rate limit config:
- All languages enforce same rate
- All handle burst capacity similarly
- All produce similar wait times

**Test**: Send burst of requests, verify rate limiting behavior.

## Test Implementation Plan

### Phase 1: Interface Tests (High Priority)
Create tests that verify:
- ✅ Tool interface signatures
- ✅ Agent interface signatures  
- ✅ Message structure
- ✅ Parameter names

**Location**: `tests/cross_language/test_interfaces.py` (Python driver)

### Phase 2: Default Value Tests
Create tests that verify:
- Default configuration values match
- Config builders produce expected defaults

**Location**: `tests/cross_language/test_defaults.py`

### Phase 3: Serialization Tests
Create tests that verify:
- Message serialization compatibility
- ToolResult serialization compatibility
- Cross-language round-trips work

**Location**: `tests/cross_language/test_serialization.py`

### Phase 4: Behavior Tests
Create tests that verify:
- Retry behavior consistency
- Timeout behavior consistency
- Rate limiting behavior consistency

**Location**: `tests/cross_language/test_behavior.py`

## Test Execution Strategy

### Approach 1: Python as Test Driver
- Python test suite spawns subprocesses for each language
- Each language implements a test harness CLI
- Python collects and validates results
- **Pros**: Centralized, easy to add new tests
- **Cons**: Requires CLI harness in each language

### Approach 2: Shared JSON Test Specs
- Define tests in JSON format
- Each language implements test runner
- Results compared manually or via script
- **Pros**: Language-independent
- **Cons**: More complex, harder to maintain

**Recommended**: Approach 1 (Python driver) for faster development.

## Test Harness Requirements

Each language needs a CLI that can:
1. Report interface signatures (as JSON)
2. Report default config values (as JSON)
3. Serialize/deserialize Message and ToolResult
4. Run behavior tests (retry, timeout, rate limit)

Example CLI interface:
```bash
# Get interface info
agenkit-test interfaces --format json

# Get default values
agenkit-test defaults --component retry --format json

# Test serialization
agenkit-test serialize --type message --data '{"role":"user","content":"hello"}'

# Run behavior test
agenkit-test behavior --type retry --config '{"max_retries":3}' --failures 2
```

## Success Criteria

- [ ] All 6 languages have test harness CLIs
- [ ] Interface consistency tests pass (Phase 1)
- [ ] Default value tests pass (Phase 2)
- [ ] Serialization tests pass (Phase 3)
- [ ] Behavior tests pass (Phase 4)
- [ ] Tests run in CI/CD (once infrastructure ready)
- [ ] Documentation complete

## Timeline

**Phase 1** (Interface Tests): 1 day
**Phase 2** (Default Values): 0.5 day
**Phase 3** (Serialization): 1 day
**Phase 4** (Behavior): 1.5 days

**Total**: ~4 days

## Related Issues

- #445 - API Alignment Phase 2 Implementation
- #438 - This tracking issue
- #412 - Related issue (if any)

---

**Next Steps**: Start with Phase 1 (Interface Tests)
