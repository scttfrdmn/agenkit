# Claude Code Guidelines for Agenkit

**Optimized for efficient AI coding - Essential information only**

---

## 🚨 Critical Rule: Project Tracking

**ALL project status, progress, plans, and milestones ONLY go in GitHub:**
- Issues: Track specific work items
- Milestones: Track releases and phases
- Project boards: Optional for sprint planning

**❌ NEVER create these files:**
- `docs/PARITY_STATUS.md`
- `docs/v0.47.0_EXECUTION_PLAN.md`
- `docs/SPRINT_*.md`
- `docs/PROGRESS_*.md`
- Any status/progress/planning documents

**✅ GitHub is the single source of truth for:**
- Release planning
- Feature status
- Parity tracking
- Issue management
- Work prioritization

**Exception:** ROADMAP.md exists for high-level strategy only.

---

## Quick Reference

### Project Context
- **Project**: Agenkit - Cross-language AI agent **toolkit** (NOT a framework)
- **Languages**: Python, Go, TypeScript, Rust, C++, Zig, C#, Java, Scala (100% feature parity achieved!)
- **Current**: v0.73.0 (Scala Implementation — agenkit-scala, sbt `io.agenkit:agenkit-scala_3`)
- **Tests**: `make test` (15-30s locally, 100% pass required)

### 🚨 Testing Policy
**LOCAL TESTING IS PRIMARY — CI IS A SAFETY NET, NOT THE GATE**

- **Primary validation**: `make test` (fast, reliable, 15-30s). Always run it
  locally and make it pass **before** committing — do not push and wait on CI.
- **All validation must pass locally before committing.**

Quick commands:
```bash
make test         # Fast validation (15-30s)
make test-quick   # Quick smoke tests (~10s)
make pre-commit   # Format + test
make test-lint    # Full lint + test (optional)
make security     # Local security scan (trivy/govulncheck/semgrep) — optional
```

#### CI policy (updated)
CI **is** enabled, but it is supplementary to local testing, not a substitute.
- **Self-hosted runners**: functional CI + security scans run on the
  `[self-hosted, Linux]` runners (janus.local, Rocky 9 — 6 runners) for
  `push`/`schedule`. Linux is required because container jobs (Semgrep, Trivy,
  CodeQL build) only run on Linux runners — the macOS `orion` runners cannot
  run `container:` jobs and serve as overflow for non-container work only.
  **Pull requests (incl. forks) run on GitHub-hosted runners** so untrusted
  code never executes on the LAN runners — this split is encoded in every
  workflow's `runs-on:` (`pull_request ? ubuntu-latest : [self-hosted, Linux]`)
  and must be preserved.
- **Security scanning is the sanctioned exception** to "minimal CI": CodeQL,
  Trivy, govulncheck, and Semgrep run in `.github/workflows/security.yml`, and
  SBOM generation + Sigstore signing run on release in
  `release-security.yml`. These only deliver value in CI (SARIF → Security tab,
  release attestation), so they live there by design.
- Dependabot (alerts + automated security fixes + grouped version updates) and
  GitHub secret scanning + push protection are enabled at the repo level.

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
# Full lint + test (optional, more thorough)
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
| Rust       | `cd agenkit-rust && cargo test --all-targets` | ~11s |
| C++        | `cd agenkit-cpp/build && ctest`      | 50s   |
| Zig        | `cd agenkit-zig && zig build test`   | 0.16s |
| C#         | `cd agenkit-cs && dotnet test`       | ~5s   |
| Java       | `cd agenkit-java && mvn test`        | ~15s  |
| Scala      | `cd agenkit-scala && sbt test`       | ~20s  |

For Rust use `--all-targets`, not a bare `cargo test`: `--lib` alone skips
everything in `agenkit-rust/tests/` (#773). Doctests need their own run —
`cargo test --doc --features opentelemetry`; `--all-targets` excludes them.

**Local testing is your ONLY validation** - No CI/CD available currently.

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
- [ ] Code passes ruff (check + format), mypy without warnings
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
├── examples/             # 40+ examples (all languages, 14+ frameworks)
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

## Current Release Status (March 2026)

**v0.73.0 (Released March 17, 2026):**
- ✅ `agenkit-scala/` — Scala 3.4.2 full-parity implementation (Issue #540, Milestone #81)
- ✅ 18 patterns (15 + 3 composition), 8 middleware, memory, safety, observability, adapters, budget, evaluation, checkpointing
- ✅ sbt artifact: `io.agenkit:agenkit-scala_3:0.73.0`
- ✅ `scripts/test-local.sh` updated with `sbt test` step
- ✅ `feature-manifest.json` updated with Scala entry
- ✅ Scala 3 idioms: `given`/`using` ExecutionContext, extension methods, enums, case classes

**v0.72.0 (Released March 17, 2026):**
- ✅ `agenkit-java/` — Java 17 full-parity implementation (Issue #230, Milestone #78)
- ✅ 18 patterns (15 + 3 composition), 8 middleware, memory, safety, observability, adapters, budget, evaluation, checkpointing
- ✅ Maven artifact: `io.agenkit:agenkit:0.72.0`
- ✅ `scripts/test-local.sh` updated with `mvn test` step
- ✅ `feature-manifest.json` updated with C# and Java entries

**v0.71.0 (Released March 17, 2026):**
- ✅ `agenkit-cs/` — C#/.NET 10 full-parity implementation (Issue #229, Milestone #77)
- ✅ 18 patterns (15 + 3 composition), 8 middleware, memory, safety, observability, adapters, budget, evaluation, checkpointing
- ✅ 241 C# tests passing (0 failed); NuGet package `Agenkit` v0.71.0
- ✅ `scripts/test-local.sh` updated with `dotnet test` step

**v0.70.0 (Released March 16, 2026):**
- ✅ Go `parseToolCall` returns `*string` — eliminates sentinel empty-string pattern (Issue #429)
- ✅ `docs/TYPE_VALIDATION.md` — per-language type checking patterns + equivalence analysis (Issue #428)
- ✅ `docs/DEFAULTS.md` — added TTL expiration semantics section (Issue #442)
- ✅ 1989 tests passing (0 failed)

**Next Focus:**
- v0.74.0 (see GitHub milestone)
- Maintain 100% local test pass rate
- `docs/` refresh: tutorials (#16), cross-language examples

See `ROADMAP.md` for complete release schedule.

---

**Last Updated:** March 17, 2026 (v0.73.0 current)
**Token Count:** ~200 lines
