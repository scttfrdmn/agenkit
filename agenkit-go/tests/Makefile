# Makefile for agenkit-go test harness

.PHONY: build clean test

# Build the cross-language test harness
build:
	@echo "Building Go cross-language test harness..."
	go build -o cross_language_harness cross_language_harness.go
	@echo "✓ Build complete: cross_language_harness"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f cross_language_harness
	@echo "✓ Clean complete"

# Test the harness with health check
test: build
	@echo "Testing harness health check..."
	@echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ./cross_language_harness
	@echo ""
	@echo "Testing harness info..."
	@echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ./cross_language_harness

# Install (copy to bin directory)
install: build
	@echo "Installing harness..."
	@mkdir -p ../bin
	@cp cross_language_harness ../bin/
	@echo "✓ Installed to ../bin/cross_language_harness"

.DEFAULT_GOAL := build
