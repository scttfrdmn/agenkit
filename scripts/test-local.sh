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

    run_step "Black (Python formatter)" \
        black --check agenkit/ tests/

    cd "$REPO_ROOT/agenkit-go"
    run_step "go fmt check" \
        bash -c 'if [ "$(gofmt -s -l . | grep -v "^examples/" | wc -l)" -gt 0 ]; then echo "Code not formatted:"; gofmt -s -l . | grep -v "^examples/"; exit 1; fi'

    run_step "go vet" \
        bash -c 'go vet $(go list ./... | grep -v /examples/)'

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

# C# Tests
echo -e "${BLUE}=== C# / .NET Tests ===${NC}"
cd "$REPO_ROOT"
if command -v dotnet &>/dev/null && [ -f "agenkit-cs/Agenkit.sln" ]; then
    run_step "dotnet test (C#)" \
        dotnet test agenkit-cs/Agenkit.sln --nologo -q
else
    echo -e "${YELLOW}  ⚠ dotnet not found, skipping C# tests${NC}"
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
