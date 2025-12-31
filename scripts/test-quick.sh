#!/bin/bash
# Quick test runner - just core tests (no linting)
# Use for fast iteration during development

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

echo "⚡ Quick Test Run (Core Tests Only)"
echo "===================================="
echo ""

# Python core tests (exact CI command)
echo "→ Python tests..."
pytest tests/ -v --cov=agenkit --cov-report=term

# Go core tests (exact CI command)
echo ""
echo "→ Go tests..."
cd agenkit-go
go test -v -race -coverprofile=coverage.out -covermode=atomic ./...

echo ""
echo "✅ Core tests passed! Run './scripts/test-local.sh' for full CI check."
