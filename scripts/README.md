# Local Testing Scripts

This directory contains scripts for local development and testing.

## test-local.sh

Fast local test runner optimized for solo development. **Use this instead of waiting for CI!**

### Quick Start

```bash
# Run all tests (15-30 seconds)
./scripts/test-local.sh

# Or use Makefile
make test
```

### Options

```bash
./scripts/test-local.sh --quick    # Skip integration tests (~10s)
./scripts/test-local.sh --lint     # Full lint + test (CI-equivalent)
./scripts/test-local.sh -v         # Verbose output
./scripts/test-local.sh -h         # Show help
```

### Makefile Targets

```bash
make test          # Run all tests (fast, ~15-30s)
make test-quick    # Run quick tests only (~10s, skip integration)
make test-lint     # Run tests with linting (slower, CI-equivalent)
make format        # Format code (Python: ruff format, Go: gofmt)
make lint          # Run linters only (no tests)
make pre-commit    # Format + test (recommended before commit)
make coverage      # Generate coverage reports
make clean         # Clean build artifacts
```

## Workflow

### Before Every Commit

```bash
make test          # Fast, 15-30 seconds
# or
make pre-commit    # Formats code then runs tests
```

### During Development (rapid iteration)

```bash
make test-quick    # ~10 seconds, perfect for TDD
```

### Before Push (full validation)

```bash
make test-lint     # Slower but thorough, matches CI
```

## Why Local-First?

**GitHub Actions is slow for solo development:**
- 15-20 minutes per run (21 jobs across 9 OS/version combinations)
- Can't see detailed output or debug easily
- Integration tests struggle in CI environment
- Expensive feedback loop for simple fixes

**Local testing is fast:**
- 15-30 seconds for full test suite (with pytest-xdist parallel execution)
- 10 seconds for quick tests
- Real-time output and easy debugging
- Integration tests work perfectly (Go servers start locally)

## CI Status

CI now runs minimal smoke tests only:
- **test.yml**: Quick unit tests (Python + Go, no integration)
- **lint.yml**: Basic formatting check (ruff format + gofmt)

Purpose: Catch obvious regressions, not primary validation.

**Local testing is your primary validation.**

---

## Multi-Language Test Status

This project includes implementations in **6 languages**. All should be tested locally:

| Language | Status | Tests | Command |
|----------|--------|-------|---------|
| Python | ✅ 1739/1741 | 2:08 | `make test` |
| Go | ✅ All Pass | ~10s | `cd agenkit-go && go test ./...` |
| Rust | ✅ 276 Pass | 0.4s | `cd agenkit-rust && cargo test` |
| TypeScript | ✅ 1039/1039 | 4.5s | `cd agenkit-ts && npm test` |
| Zig | ✅ 214/214 | 0.16s | `cd agenkit-zig && zig build test` |
| C++ | ✅ 42/42 | 50s | `cd agenkit-cpp/build && ctest` |

### Quick Test All Languages

```bash
# Python (primary)
make test

# Go
(cd agenkit-go && go test ./...)

# Rust
(cd agenkit-rust && cargo test)

# TypeScript
(cd agenkit-ts && npm test)

# Zig
(cd agenkit-zig && zig build test)

# C++ (already built)
(cd agenkit-cpp/build && ctest)
```

### Cross-Language Integration Tests

Python tests can spawn Go/other language servers for integration testing:

```bash
# Ensure Go servers are built first
(cd agenkit-go/tests/integration && go build test_server.go && go build test_grpc_server.go)

# Run cross-language tests
uv run pytest tests/cross_language/ -v
```

See each language's README for detailed testing instructions.
