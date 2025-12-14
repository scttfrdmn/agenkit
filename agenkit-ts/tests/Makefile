# Makefile for agenkit-ts test harness

.PHONY: build clean test install

# Build the cross-language test harness
build:
	@echo "Building TypeScript cross-language test harness..."
	@cd .. && npx tsc --project tests/tsconfig.json
	@chmod +x cross_language_harness.js
	@echo "✓ Build complete: cross_language_harness.js"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -f cross_language_harness.js
	@echo "✓ Clean complete"

# Test the harness with health check
test: build
	@echo "Testing harness health check..."
	@echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | node cross_language_harness.js
	@echo ""
	@echo "Testing harness info..."
	@echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | node cross_language_harness.js

# Install (copy to bin directory)
install: build
	@echo "Installing harness..."
	@mkdir -p ../../bin
	@cp cross_language_harness.js ../../bin/
	@echo "✓ Installed to ../../bin/cross_language_harness.js"

.DEFAULT_GOAL := build
