# Claude Code Guidelines for Agenkit

**Optimized for efficient AI coding - Essential information only**

---

## Quick Reference

### Project Context
- **Project**: Agenkit - Cross-language AI agent **toolkit** (NOT a framework)
- **Languages**: Python, Go, TypeScript, Rust, C++, Zig (100% feature parity achieved!)
- **Current**: v0.44.0 (3,310+ tests passing, 100% success rate)
- **Next Release**: v0.46.1 (CI/CD fixes, DUE: Jan 9, 2026)
- **Tests**: `make test` (15-30s locally, 100% pass required)

### Core Principle
**Write idiomatic, production-quality code from the start** - not as an afterthought. Every line must pass linting checks and follow language idioms.

---

## Critical Coding Standards

### Go - Idiomatic Patterns

**Always Check Errors:**
```go
// WRONG: defer file.Close()
// CORRECT: defer func() { _ = file.Close() }()

// WRONG: w.Write(data)
// CORRECT: if _, err := w.Write(data); err != nil { log.Printf("Failed: %v", err) }
```

**Printf Format Strings:**
```go
// WRONG: log.Printf("timeout=%.1fs", timeoutConfig.Timeout)  // Timeout is time.Duration!
// CORRECT: log.Printf("timeout=%.1fs", timeoutConfig.Timeout.Seconds())
```

**Switch vs If-Else:**
```go
// WRONG: if state == StateOpen { } else if state == StateClosed { }
// CORRECT: switch state { case StateOpen: case StateClosed: }
```

**Other Rules:**
- No redundant nil checks: `if len(slice) > 0` (not `if slice != nil && len(slice) > 0`)
- Error messages start lowercase: `"failed to start"` (not `"Failed to start"`)
- Build tags: Only `//go:build` format (remove old `// +build` lines)
- Network operations: Always check `SetReadDeadline()` / `SetWriteDeadline()` errors

### Python - Idiomatic Patterns

**Use uv for All Python Operations:**
```bash
# WRONG: python script.py, pytest tests/
# CORRECT: uv run python script.py, uv run pytest tests/
```

**Async Patterns:**
```python
# WRONG: Busy loop with sleep
# CORRECT: Event-based approach with asyncio.Event()
```

**Regex in Tests:**
```python
# WRONG: match="timed out after 0.1s"
# CORRECT: match=r"timed out after 0\.1s"  # Raw string, escaped dots
```

**Exception Handling:**
```python
# Only pass silently with justification
try:
    risky_operation()
except Exception:  # noqa: S110
    pass  # Expected failures - testing retry behavior
```

---

## Development Workflow

### Before Every Commit

```bash
# Fast local validation (15-30 seconds)
make test

# Or format + test
make pre-commit
```

### During Development (Rapid Iteration)

```bash
# Quick tests only (~10 seconds)
make test-quick
```

### Before Push (Full Validation)

```bash
# Full lint + test (matches CI)
make test-lint

# Check cross-language parity
./scripts/test-parity.sh
```

### Multi-Language Testing

| Language   | Command                              | Time  |
|------------|--------------------------------------|-------|
| Python     | `make test`                          | 2:08  |
| Go         | `cd agenkit-go && go test ./...`     | ~10s  |
| TypeScript | `cd agenkit-ts && npm test`          | 4.5s  |
| Rust       | `cd agenkit-rust && cargo test`      | 0.4s  |
| C++        | `cd agenkit-cpp/build && ctest`      | 50s   |
| Zig        | `cd agenkit-zig && zig build test`   | 0.16s |

**Local testing is your primary validation** - CI is slow (15-20 min).

---

## Code Review Checklist

### Go
- [ ] All error returns checked or explicitly ignored with `_ =`
- [ ] `time.Duration` values use `* time.Second` not raw floats
- [ ] Printf format strings match argument types
- [ ] Switch statements used instead of if-else chains
- [ ] Error messages start lowercase
- [ ] Network deadline operations check errors

### Python
- [ ] All operations use `uv run` prefix
- [ ] Regex patterns use raw strings (`r"..."`)
- [ ] Type hints present on function signatures
- [ ] Code passes ruff, black, mypy without warnings
- [ ] Exception handlers include noqa comments explaining why

### All Languages
- [ ] Passes linters without exceptions
- [ ] Follows existing patterns in codebase
- [ ] Includes proper error handling
- [ ] Has tests (unit + integration if applicable)
- [ ] Examples are production-quality (if applicable)

---

## Project Structure

```
agenkit/
├── agenkit/              # Python implementation (core)
├── agenkit-go/           # Go implementation
├── agenkit-ts/           # TypeScript implementation
├── agenkit-rust/         # Rust implementation
├── agenkit-cpp/          # C++ implementation
├── agenkit-zig/          # Zig implementation
├── docs/                 # Architecture & pattern docs
├── examples/             # 27+ examples (all languages)
├── tests/                # Python tests
├── benchmarks/           # Performance benchmarks
├── scripts/              # Development scripts
└── deploy/               # Docker + Kubernetes configs
```

**Key Files:**
- `ROADMAP.md` - Single source of truth for planning (authoritative)
- `ARCHITECTURE.md` - Design principles and patterns
- `CHANGELOG.md` - Release history
- `.github/CONTRIBUTING.md` - Contribution guidelines

---

## Important Policies

### Planning & Roadmap

**When in conflict, ROADMAP.md wins.**

- **Scope & Timeline**: `ROADMAP.md` is authoritative
- **Issue Tracking**: GitHub Issues + Milestones
- **Strategic Planning**: See ROADMAP.md and docs/

**Never create parallel planning systems.** If documents conflict, trust ROADMAP.md and update others to match.

### Milestone Naming
- `v0.46.0 - Production Hardening` = Committed work
- `Ideas: Advanced Patterns` = Future ideas, NOT commitments
- `Future/Backlog` = Parking lot

### Making Scope Changes
1. Update ROADMAP.md first
2. Update GitHub milestones to match
3. Document the change in commit message

---

## When In Doubt

1. **Check existing code** - Find similar patterns that pass linting
2. **Run the linter** - `golangci-lint`/`ruff` will tell you exactly what's wrong
3. **Read the error** - Linters provide specific guidance
4. **Ask for help** - Don't guess and create technical debt

---

## Why This Matters

**Token Cost:** Fixing non-idiomatic code after the fact costs 10-100x more tokens than writing it correctly initially.

**Quality:** Code written idiomatically from the start:
- Has fewer bugs
- Is easier to maintain
- Passes code review faster
- Teaches users correct patterns

**Process:**
1. Write code using patterns from this guide
2. Verify against checklist above
3. Test locally with linters before committing
4. Iterate if issues found - don't disable linters

---

## Examples Are Documentation

Examples in this codebase teach users how to use the toolkit. Non-idiomatic examples teach bad habits and create support burden.

**Every example must:**
- Pass all linters without exceptions
- Follow all patterns in this guide
- Be production-ready code quality
- Include proper error handling
- Use idiomatic patterns for the language

---

## References (Keep Separate)

- **Roadmap**: `ROADMAP.md` - Release planning and scope
- **Architecture**: `ARCHITECTURE.md` - Design principles
- **Contributing**: `.github/CONTRIBUTING.md` - How to contribute
- **Testing**: `TESTING.md` - Test strategy and guidelines
- **Security**: `SECURITY.md` - Vulnerability reporting
- **Compatibility**: `COMPATIBILITY.md` - Language/platform support

**Don't duplicate content here** - reference these docs instead.

---

## Current Release Status (Jan 2026)

**v0.44.0 (Released):**
- ✅ 100% test pass rate (3,310+ tests)
- ✅ 100% feature parity across 6 languages
- ✅ Historic milestone: First AI agent toolkit with 6-language parity!

**v0.46.1 (In Progress, DUE: Jan 9, 2026):**
- 🔧 CI/CD performance fixes
- 🔧 Language version updates
- 🔧 Test optimization (Python 11+ min → target <2 min)

**v0.47.0 (Planned, DUE: May 16, 2026):**
- 📚 Framework migration guides
- 📚 Complete API reference docs
- 🧪 Cross-language test parity expansion

See `ROADMAP.md` for complete release schedule.

---

**Last Updated:** January 9, 2026 (v0.44.0 current)
**Token Count:** ~200 lines (vs 435 in previous version - 54% reduction)
