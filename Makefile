.PHONY: help test test-quick test-lint security clean coverage check-artifacts check-version sync-version

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test: ## Run all tests (fast, ~15-30s)
	@./scripts/test-local.sh

test-quick: ## Run quick tests only (~10s, skip integration)
	@./scripts/test-local.sh --quick

test-lint: ## Run tests with linting (slower, CI-equivalent)
	@./scripts/test-local.sh --lint

test-verbose: ## Run tests with verbose output
	@./scripts/test-local.sh -v

check-artifacts: ## Fail if compiled binaries or oversize files are tracked (#660)
	@./scripts/check-tracked-artifacts.sh

check-version: ## Fail if any version declaration disagrees with VERSION (#842)
	@python3 scripts/version.py check

sync-version: ## Rewrite every version declaration from the root VERSION file
	@python3 scripts/version.py sync

security: ## Run local security scans (trivy + govulncheck + semgrep)
	@echo "=== Trivy (filesystem: deps, misconfig, secrets) ==="
	@command -v trivy >/dev/null && trivy fs --scanners vuln,misconfig,secret --severity CRITICAL,HIGH --ignore-unfixed . || echo "  ⚠ trivy not installed, skipping"
	@echo ""
	@echo "=== govulncheck (Go) ==="
	@command -v govulncheck >/dev/null && (cd agenkit-go && govulncheck ./...) || echo "  ⚠ govulncheck not installed, skipping (go install golang.org/x/vuln/cmd/govulncheck@latest)"
	@echo ""
	@echo "=== Semgrep (SAST, all languages) ==="
	@command -v semgrep >/dev/null && semgrep scan --config auto --error || echo "  ⚠ semgrep not installed, skipping"

clean: ## Clean build artifacts and coverage files
	@echo "Cleaning build artifacts..."
	@rm -rf .pytest_cache __pycache__ .coverage coverage.xml htmlcov
	@rm -rf agenkit-go/coverage.out agenkit-go/coverage.html
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Clean complete"

coverage: ## Generate coverage reports
	@echo "Generating Python coverage..."
	@pytest tests/ -q --cov=agenkit --cov-report=html --cov-report=term
	@echo ""
	@echo "Python coverage report: htmlcov/index.html"
	@echo ""
	@echo "Generating Go coverage..."
	@cd agenkit-go && go test -coverprofile=coverage.out ./... && go tool cover -html=coverage.out -o coverage.html
	@echo "Go coverage report: agenkit-go/coverage.html"

install: ## Install development dependencies
	@echo "Installing Python dependencies..."
	@pip install -e ".[dev,test]"
	@echo "✓ Python dependencies installed"
	@echo ""
	@echo "Go dependencies are managed by go.mod"

format: ## Format code (Python: ruff format, Go: gofmt)
	@echo "Formatting Python code..."
	@ruff format agenkit/ tests/ examples/
	@echo "Formatting Go code..."
# Whole repo, not just agenkit-go: four Go example trees live outside it
# (examples/deployment/aws-lambda/go, examples/e2e, examples/infrastructure,
# examples/apps). The CI gate tells you to run `make format`, so this must fix
# everything that gate checks or the advice is a dead end (#849).
#
# Dockerfile.go is excluded because it is a Dockerfile, not Go — gofmt tries to
# parse it, reports `illegal character U+0023 '#'` and exits 2, which would fail
# this target. Renaming it is out of scope here (#856).
	@gofmt -s -w $$(git ls-files '*.go' | grep -v '^\.claude/' | grep -v '^Dockerfile\.go$$')
	@echo "✓ Code formatted"

lint: ## Run linters only (no tests)
	@echo "Running Ruff check..."
	@ruff check agenkit/ tests/
	@echo "Running Ruff format check..."
	@ruff format --check agenkit/ tests/
	@echo "Running go fmt check..."
# Must FAIL on unformatted code. This previously ended in
# `| grep -v "^examples/" || echo "✓ Go code formatted"`, which printed the
# offending files and then reported success regardless — grep's non-zero exit on
# no-match triggered the "✓", and a match exited 0, so neither path ever failed
# the target. Mirrors the CI gate in lint.yml (#849).
	@UNFORMATTED=$$(gofmt -s -l $$(git ls-files '*.go' | grep -v '^\.claude/' | grep -v '^Dockerfile\.go$$') 2>/dev/null); \
	 if [ -n "$$UNFORMATTED" ]; then \
	   echo "❌ Go code not formatted. Run 'make format' to fix:"; \
	   echo "$$UNFORMATTED"; exit 1; \
	 else echo "✓ Go code formatted"; fi
	@echo "Running go vet..."
	@cd agenkit-go && go vet $$(go list ./... | grep -v /examples/)
	@echo "✓ All linters passed"

pre-commit: format test ## Format code and run tests (recommended before commit)
	@echo ""
	@echo "✅ Ready to commit!"
