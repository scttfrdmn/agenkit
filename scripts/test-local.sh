#!/bin/bash
# Local test runner - matches CI exactly
# Run this before pushing to catch failures early

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

echo "🧪 Running Local Tests (Identical to CI)"
echo "========================================"
echo ""

# Track failures
FAILED=0

# Function to run a test step
run_step() {
    local name="$1"
    shift
    echo -e "${YELLOW}→ $name${NC}"
    if "$@"; then
        echo -e "${GREEN}  ✓ Passed${NC}"
    else
        echo -e "${RED}  ✗ Failed${NC}"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# Python Linting (from .github/workflows/lint.yml lines 34-54)
echo "=== Python Linting ==="
run_step "Ruff (linter)" \
    ruff check agenkit/ tests/ examples/ --output-format=github

run_step "Black (formatter check)" \
    black --check agenkit/ tests/ examples/

run_step "MyPy (type checking)" \
    mypy agenkit/ --ignore-missing-imports

# Python Tests (from .github/workflows/test.yml lines 48-49)
echo "=== Python Tests ==="
run_step "pytest with coverage" \
    pytest tests/ -v --cov=agenkit --cov-report=xml --cov-report=term

# Go Linting (from .github/workflows/lint.yml lines 71-96)
echo "=== Go Linting ==="
cd "$REPO_ROOT/agenkit-go"

run_step "golangci-lint" \
    golangci-lint run --timeout=5m

run_step "go vet" \
    go vet ./...

run_step "go fmt check" \
    bash -c 'if [ "$(gofmt -s -l . | wc -l)" -gt 0 ]; then echo "Code not formatted:"; gofmt -s -l .; exit 1; fi'

run_step "staticcheck" \
    bash -c 'command -v staticcheck >/dev/null 2>&1 || go install honnef.co/go/tools/cmd/staticcheck@latest; staticcheck ./...'

# Go Tests (from .github/workflows/test.yml lines 89-98)
echo "=== Go Tests ==="
cd "$REPO_ROOT/agenkit-go"

run_step "go test with race detector and coverage" \
    go test -v -race -coverprofile=coverage.out -covermode=atomic ./...

run_step "go coverage report" \
    bash -c 'go tool cover -html=coverage.out -o coverage.html; go tool cover -func=coverage.out'

# Summary
cd "$REPO_ROOT"
echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Safe to push.${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILED test(s) failed. Fix before pushing.${NC}"
    exit 1
fi
