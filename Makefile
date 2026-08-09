.PHONY: help test test-quick test-lint security clean coverage check-artifacts check-version sync-version check-tool-pins check-release-gate check-docs-facts

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

check-tool-pins: ## Fail if ruff is pinned inconsistently or invoked bare (#793)
	@./scripts/check-tool-pins.sh

check-release-gate: ## Fail if release.sh could tag a release with a red suite (#863)
	@./scripts/check-release-gate.sh

check-docs-facts: ## Fail if generated docs/parity/*.md or README.md blocks are stale (#902)
	@uv run python scripts/parity/matrix_generator.py --check
	@uv run python scripts/docs_facts.py check

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
# `uv run --extra dev` rather than a bare `ruff`, so this uses the pinned 0.14.4 and
# not whatever is on $PATH. A bare `ruff` here could reformat the tree with a
# different version than the CI gate checks with, producing a diff CI then rejects
# (#793). Keep the path set in step with lint.yml and test-local.sh.
	@uv run --extra dev ruff format agenkit/ tests/ examples/
	@echo "Formatting Go code..."
# Whole repo, not just agenkit-go: four Go example trees live outside it
# (examples/deployment/aws-lambda/go, examples/e2e, examples/infrastructure,
# examples/apps). The CI gate tells you to run `make format`, so this must fix
# everything that gate checks or the advice is a dead end (#849).
	@gofmt -s -w $$(git ls-files '*.go' | grep -v '^\.claude/')
	@echo "✓ Code formatted"

lint: ## Run linters only (no tests)
	@echo "Running Ruff check..."
	@uv run --extra dev ruff check agenkit/ tests/
	@echo "Running Ruff format check..."
	@uv run --extra dev ruff format --check agenkit/ tests/ examples/
	@echo "Running go fmt check..."
# Must FAIL on unformatted code. This previously ended in
# `| grep -v "^examples/" || echo "✓ Go code formatted"`, which printed the
# offending files and then reported success regardless — grep's non-zero exit on
# no-match triggered the "✓", and a match exited 0, so neither path ever failed
# the target. The 300-file floor guards the guard: `gofmt -s -l` with no arguments
# reads stdin and exits 0, so an empty list would report success on nothing.
# Mirrors the CI gate in lint.yml (#849).
	@FILES=$$(git ls-files '*.go' | grep -v '^\.claude/'); \
	 COUNT=$$(printf '%s\n' "$$FILES" | grep -c . || true); \
	 if [ "$$COUNT" -lt 300 ]; then \
	   echo "❌ gofmt check found only $$COUNT Go files (expected 300+); fix this check"; exit 1; \
	 fi; \
	 UNFORMATTED=$$(gofmt -s -l $$FILES); \
	 if [ -n "$$UNFORMATTED" ]; then \
	   echo "❌ Go code not formatted. Run 'make format' to fix:"; \
	   echo "$$UNFORMATTED"; exit 1; \
	 else echo "✓ Go code formatted ($$COUNT files)"; fi
	@echo "Running go vet..."
	@cd agenkit-go && go vet $$(go list ./... | grep -v /examples/)
	@echo "✓ All linters passed"

pre-commit: format test ## Format code and run tests (recommended before commit)
	@echo ""
	@echo "✅ Ready to commit!"
