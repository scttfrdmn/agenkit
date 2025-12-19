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

---

## Source of Truth for Planning & Roadmap

**Established**: December 18, 2025 (Rationalization)

### Canonical Sources

There is ONE canonical source for each type of project information:

1. **Scope & Timeline**: `ROADMAP.md` (this repository)
   - What features are committed to which releases
   - Release dates and milestones
   - v1.0.0 scope definition

2. **Issue Tracking**: GitHub Issues + Milestones
   - GitHub Issues are the authoritative task list
   - Milestones prefixed with "Ideas:" are NOT commitments
   - Only numbered milestones (v0.x.x, v1.x.x) are commitments

3. **Strategic Planning**: `/Users/scttfrdmn/src/agenkit-planning/`
   - `EXECUTIVE_SUMMARY.md` - High-level strategy and positioning
   - `CURRENT_STATE_AUDIT_DEC_2025.md` - Most recent state analysis
   - Other docs are advisory or archived

### Policy

**When in conflict, ROADMAP.md wins.**

If there is any discrepancy between planning documents, GitHub milestones, or verbal discussions:
- ROADMAP.md is the source of truth
- Update other documents to match ROADMAP.md
- Do not create parallel planning systems

### Milestone Naming Convention

- **`v0.42.0 - Testing & Documentation`** = Committed work
- **`Ideas: Advanced Patterns`** = Future ideas, NOT commitments
- **`Future/Backlog`** = Parking lot for ideas

If a milestone is not a numbered release (v0.x.x or v1.x.x), it is NOT a commitment.

### Making Changes

To change v1.0.0 scope or timeline:
1. Update ROADMAP.md first
2. Update GitHub milestones to match
3. Update planning docs if needed
4. Document the change in commit message

Do not make changes in planning docs and expect ROADMAP.md to sync - it won't.

### For Claude Code Users

When working on Agenkit:
1. Always read ROADMAP.md before planning work
2. Check GitHub milestones for current assignments
3. Treat "Ideas:" milestones as brainstorming, not commitments
4. If planning docs conflict with ROADMAP.md, trust ROADMAP.md
5. When in doubt, ask: "Is this in ROADMAP.md?"

This prevents scope creep and ensures everyone works from the same plan.
