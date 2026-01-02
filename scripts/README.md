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
make format        # Format code (Python: black, Go: gofmt)
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
- **lint.yml**: Basic formatting check (Black + gofmt)

Purpose: Catch obvious regressions, not primary validation.

**Local testing is your primary validation.**
