# Claude Coding Guidelines

## Core Principle

**Write idiomatic, production-quality code from the start - not as an afterthought.**

Every line of code you write should pass linting checks and follow language idioms. This document provides specific patterns to use and anti-patterns to avoid. Follow these guidelines proactively when writing new code to avoid costly remediation cycles.

## Go: Idiomatic Error Handling

### Always Check Errors

**WRONG:**
```go
defer file.Close()
resp.Body.Close()
w.Write(data)
http2.ConfigureServer(server, &http2.Server{})
```

**CORRECT:**
```go
// For defer operations where you can't handle the error
defer func() { _ = file.Close() }()

// For operations where errors matter
if _, err := w.Write(data); err != nil {
    log.Printf("Failed to write: %v", err)
}

// For configuration operations
if err := http2.ConfigureServer(server, &http2.Server{}); err != nil {
    log.Printf("Failed to configure HTTP/2: %v", err)
}
```

### Test Code Error Handling

**WRONG:**
```go
// In tests - ignoring errors silently
server.Stop()
client.Close()
agent.Process(ctx, msg)
```

**CORRECT:**
```go
// Explicitly ignore with _ = to show intent
defer func() { _ = server.Stop() }()
defer func() { _ = client.Close() }()
_, _ = agent.Process(ctx, msg)  // When testing metrics/behavior, not result
```

### Printf Format Strings

**WRONG:**
```go
timeoutConfig := &TimeoutConfig{
    Timeout: 30.0,  // This is wrong - Timeout is time.Duration, not float64!
}
log.Printf("timeout=%.1fs", timeoutConfig.Timeout)  // Wrong type!
```

**CORRECT:**
```go
timeoutConfig := &TimeoutConfig{
    Timeout: 30 * time.Second,  // Proper time.Duration
}
log.Printf("timeout=%.1fs", timeoutConfig.Timeout.Seconds())  // Convert to float64
```

### Switch vs If-Else Chains

**WRONG:**
```go
if state == StateOpen {
    // ...
} else if state == StateClosed {
    // ...
} else if state == StateHalfOpen {
    // ...
}
```

**CORRECT:**
```go
switch state {
case StateOpen:
    // ...
case StateClosed:
    // ...
case StateHalfOpen:
    // ...
}
```

### Nil Checks

**WRONG:**
```go
if details != nil && len(details) > 0 {  // Redundant nil check
    // ...
}
```

**CORRECT:**
```go
if len(details) > 0 {  // len() returns 0 for nil slices/maps
    // ...
}
```

### Error Messages

**WRONG:**
```go
return fmt.Errorf("Server failed to start: %w", err)  // Capitalized
```

**CORRECT:**
```go
return fmt.Errorf("server failed to start: %w", err)  // Lowercase
```

### Build Tags

**WRONG:**
```go
//go:build ignore
// +build ignore  // Obsolete format - remove this line!
```

**CORRECT:**
```go
//go:build ignore  // Only the new format
```

### Network Operations

**WRONG:**
```go
conn.SetReadDeadline(deadline)
conn.SetWriteDeadline(deadline)
```

**CORRECT:**
```go
if err := conn.SetReadDeadline(deadline); err != nil {
    return fmt.Errorf("failed to set read deadline: %w", err)
}
if err := conn.SetWriteDeadline(deadline); err != nil {
    return fmt.Errorf("failed to set write deadline: %w", err)
}
```

## Python: Idiomatic Patterns

### Async Patterns

**WRONG:**
```python
# Busy loop with sleep
while True:
    await asyncio.sleep(1)
    if should_stop:
        break
```

**CORRECT:**
```python
# Event-based approach
stop_event = asyncio.Event()
await stop_event.wait()
```

### Regex in Tests

**WRONG:**
```python
with pytest.raises(TimeoutError, match="timed out after 0.1s"):  # Unescaped special chars
```

**CORRECT:**
```python
with pytest.raises(TimeoutError, match=r"timed out after 0\.1s"):  # Raw string with escaped .
```

### Exception Handling

**WRONG:**
```python
# Silent failures without justification
try:
    risky_operation()
except Exception:
    pass
```

**CORRECT:**
```python
# In tests where failures are expected - justify with comment
try:
    risky_operation()
except Exception:  # noqa: S110
    pass  # Expected failures - testing retry behavior
```

## Proactive Code Review Checklist

**Before submitting code, verify:**

### Go Checklist
- [ ] All error returns are checked or explicitly ignored with `_ =`
- [ ] `defer Close()` operations use `defer func() { _ = x.Close() }()`
- [ ] `time.Duration` values use `* time.Second` not raw floats
- [ ] Printf format strings match argument types (use `.Seconds()` for Duration)
- [ ] Switch statements used instead of if-else chains on same variable
- [ ] No redundant nil checks before `len()`
- [ ] Error messages start with lowercase
- [ ] Build tags use only `//go:build` format (not `// +build`)
- [ ] Network deadline operations check errors
- [ ] HTTP write operations check errors and log failures

### Python Checklist
- [ ] Regex patterns in pytest.raises use raw strings
- [ ] Special regex characters are escaped
- [ ] Async code uses Event/Queue patterns, not busy loops with sleep
- [ ] Exception handlers include noqa comments explaining why
- [ ] Type hints are present on function signatures
- [ ] Code passes ruff, black, and mypy without warnings

## Why This Matters

**Token Cost:** Fixing non-idiomatic code after the fact costs 10-100x more tokens than writing it correctly initially.

**Quality:** Code written idiomatically from the start:
- Has fewer bugs
- Is easier to maintain
- Serves as better documentation
- Passes code review faster
- Teaches users correct patterns

**Process:** Follow this workflow:
1. **Write** code using patterns from this guide
2. **Verify** against the checklist above
3. **Test** locally with linters before committing
4. **Iterate** if issues found - don't disable linters

## Examples Are Production Code

Examples in this codebase are documentation. They teach users how to use the framework. Non-idiomatic examples teach bad habits and create support burden.

**Every example must:**
- Pass all linters without exceptions
- Follow all patterns in this guide
- Be production-ready code quality
- Include proper error handling
- Use idiomatic patterns for the language

## When In Doubt

1. **Check existing code** - Find similar patterns in the codebase that pass linting
2. **Run the linter** - golangci-lint/ruff will tell you exactly what's wrong
3. **Read the error** - Linters provide specific guidance (e.g., "S1009: should omit nil check")
4. **Ask for help** - If truly unsure, ask rather than guess

## Philosophy

**CI/CD exists to catch issues before they reach production.** Lint errors are not suggestions - they're problems that will cause bugs, confusion, or maintenance burden. Fix them properly, don't work around them.

**Write code as if you're teaching** - because you are. Every line of code in this repository is an example for users and future contributors.
