#!/bin/bash
# Fast local test runner optimized for solo development
# Run this before committing to catch failures early

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Parse arguments
QUICK=false
LINT=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK=true
            shift
            ;;
        --lint)
            LINT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick    Skip integration tests (faster)"
            echo "  --lint     Run linters (slower but thorough)"
            echo "  -v         Verbose output"
            echo "  -h         Show this help"
            echo ""
            echo "Examples:"
            echo "  $0              # Run all tests (fast, ~15-30s)"
            echo "  $0 --quick      # Skip integration tests (~10s)"
            echo "  $0 --lint       # Full lint + test (slower, CI-equivalent)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1. Use -h for help."
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🧪 Running Local Tests (Fast Mode)${NC}"
echo "========================================"
echo ""

# Track failures
FAILED=0
START_TIME=$(date +%s)

# Function to run a test step
run_step() {
    local name="$1"
    shift
    echo -e "${YELLOW}→ $name${NC}"
    local step_start=$(date +%s)
    if "$@"; then
        local step_end=$(date +%s)
        local duration=$((step_end - step_start))
        echo -e "${GREEN}  ✓ Passed${NC} (${duration}s)"
    else
        echo -e "${RED}  ✗ Failed${NC}"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# Linting (optional, with --lint flag)
if [ "$LINT" = true ]; then
    echo -e "${BLUE}=== Linting ===${NC}"

    run_step "Ruff (Python linter)" \
        ruff check agenkit/ tests/

    run_step "ruff format (Python formatter)" \
        ruff format --check agenkit/ tests/

    cd "$REPO_ROOT/agenkit-go"
    run_step "go fmt check" \
        bash -c 'if [ "$(gofmt -s -l . | grep -v "^examples/" | wc -l)" -gt 0 ]; then echo "Code not formatted:"; gofmt -s -l . | grep -v "^examples/"; exit 1; fi'

    run_step "go vet" \
        bash -c 'go vet $(go list ./... | grep -v /examples/)'

    # Rust lint (#773). --all-targets matters: without it clippy skips tests/ and
    # examples/, which is exactly where the six deny-by-default errors found in
    # #773 had accumulated unseen. No `-D warnings` yet — 365 unique warnings
    # remain; the sweep and the flip are tracked in #778. Keep this in step with
    # the clippy invocation in .github/workflows/test.yml.
    if command -v cargo &>/dev/null; then
        cd "$REPO_ROOT/agenkit-rust"
        run_step "cargo fmt --check (Rust formatter)" \
            cargo fmt --check
        run_step "cargo clippy (Rust linter)" \
            cargo clippy --all-targets
    else
        echo -e "${YELLOW}  ⚠ cargo not found, skipping Rust lint${NC}"
        echo ""
    fi

    cd "$REPO_ROOT"
fi

# Python Tests
echo -e "${BLUE}=== Python Tests ===${NC}"

PYTEST_ARGS=()
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v")
else
    PYTEST_ARGS+=("-q")
fi

# pytest-xdist settings are now in pyproject.toml
# (-n auto --dist loadfile --max-worker-restart 0)

# Add coverage
PYTEST_ARGS+=("--cov=agenkit" "--cov-report=term-missing:skip-covered")

if [ "$QUICK" = true ]; then
    # Skip integration and cross-language tests
    PYTEST_ARGS+=("-m" "not integration and not cross_language")
    run_step "pytest (quick: unit tests only)" \
        uv run pytest tests/ -n auto "${PYTEST_ARGS[@]}"
else
    # Run all tests including integration
    run_step "pytest (all tests with parallel execution)" \
        uv run pytest tests/ -n auto "${PYTEST_ARGS[@]}"
fi

# Go Tests
echo -e "${BLUE}=== Go Tests ===${NC}"
cd "$REPO_ROOT/agenkit-go"

GO_TEST_ARGS=("-coverprofile=coverage.out" "-covermode=atomic")

if [ "$VERBOSE" = true ]; then
    GO_TEST_ARGS+=("-v")
fi

# Exclude examples directory
PACKAGES=$(go list ./... | grep -v /examples/)

if [ "$QUICK" = true ]; then
    # Skip race detector for speed
    run_step "go test (quick: no race detector)" \
        go test "${GO_TEST_ARGS[@]}" $PACKAGES
else
    # Full test with race detector
    run_step "go test (with race detector)" \
        go test -race "${GO_TEST_ARGS[@]}" $PACKAGES
fi

# Rust Tests
echo -e "${BLUE}=== Rust Tests ===${NC}"
cd "$REPO_ROOT"
if command -v cargo &>/dev/null && [ -f "agenkit-rust/Cargo.toml" ]; then
    cd "$REPO_ROOT/agenkit-rust"
    # --all-targets, NOT --lib. `--lib` runs only the unit tests inside src/ and
    # never builds tests/, so the 40+ integration files there (every
    # cross_language_*.rs, every observability test) went unexecuted by any gate
    # until #773. ~11s warm, ~60s from cold.
    run_step "cargo test (Rust, all targets)" \
        cargo test --all-targets --quiet
    # Doctests are a separate invocation because --all-targets excludes them.
    # Skipped under --quick: they rebuild against the public API surface, which is
    # the slowest part of the Rust leg.
    if [ "$QUICK" = false ]; then
        run_step "cargo test --doc (Rust doctests)" \
            cargo test --doc --features opentelemetry --quiet
    fi
    cd "$REPO_ROOT"
else
    echo -e "${YELLOW}  ⚠ cargo not found or agenkit-rust missing, skipping Rust tests${NC}"
    echo ""
fi

# C# Tests
echo -e "${BLUE}=== C# / .NET Tests ===${NC}"
cd "$REPO_ROOT"
if command -v dotnet &>/dev/null && [ -f "agenkit-cs/Agenkit.sln" ]; then
    # Use `-v q`, not `-q`. `-q` is not a valid `dotnet test` switch: the .NET 10
    # CLI forwards it to MSBuild, which surfaces the benign MSB3492 "could not
    # read existing file ... Overwriting it" incremental-build notice as a hard
    # error and fails the step. Reproducible 100% of the time; `-v q` is the
    # documented spelling and is quiet and green.
    run_step "dotnet test (C#)" \
        dotnet test agenkit-cs/Agenkit.sln --nologo -v q
else
    echo -e "${YELLOW}  ⚠ dotnet not found, skipping C# tests${NC}"
    echo ""
fi

# Java Tests
echo -e "${BLUE}=== Java Tests ===${NC}"
cd "$REPO_ROOT"
if command -v mvn &>/dev/null && [ -d "agenkit-java" ]; then
    cd "$REPO_ROOT/agenkit-java"
    run_step "mvn test (Java)" \
        mvn test -q
    cd "$REPO_ROOT"
else
    echo -e "${YELLOW}  ⚠ mvn not found or agenkit-java missing, skipping Java tests${NC}"
    echo ""
fi

# Scala Tests
echo -e "${BLUE}=== Scala / sbt Tests ===${NC}"
cd "$REPO_ROOT"
if command -v sbt &>/dev/null && [ -f "agenkit-scala/build.sbt" ]; then
    cd "$REPO_ROOT/agenkit-scala"
    run_step "sbt test (Scala)" \
        sbt -batch test
    cd "$REPO_ROOT"
else
    echo -e "${YELLOW}  ⚠ sbt not found or agenkit-scala missing, skipping Scala tests${NC}"
    echo ""
fi

# Summary
cd "$REPO_ROOT"
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC} (${TOTAL_DURATION}s total)"
    echo ""
    if [ "$QUICK" = true ]; then
        echo "Ran quick tests. For full validation, run: $0"
    else
        echo "Safe to commit and push! 🚀"
    fi
    exit 0
else
    echo -e "${RED}❌ $FAILED test(s) failed.${NC}"
    echo ""
    echo "Tips:"
    echo "  • Run with -v for verbose output"
    echo "  • Run with --quick for faster iteration"
    echo "  • Check logs above for specific failures"
    exit 1
fi
