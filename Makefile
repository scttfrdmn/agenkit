.PHONY: help test test-quick test-lint clean coverage

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

format: ## Format code (Python: black, Go: gofmt)
	@echo "Formatting Python code..."
	@black agenkit/ tests/ examples/
	@echo "Formatting Go code..."
	@cd agenkit-go && gofmt -s -w .
	@echo "✓ Code formatted"

lint: ## Run linters only (no tests)
	@echo "Running Ruff..."
	@ruff check agenkit/ tests/
	@echo "Running Black check..."
	@black --check agenkit/ tests/
	@echo "Running go fmt check..."
	@cd agenkit-go && gofmt -s -l . | grep -v "^examples/" || echo "✓ Go code formatted"
	@echo "Running go vet..."
	@cd agenkit-go && go vet $$(go list ./... | grep -v /examples/)
	@echo "✓ All linters passed"

pre-commit: format test ## Format code and run tests (recommended before commit)
	@echo ""
	@echo "✅ Ready to commit!"
