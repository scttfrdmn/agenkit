# Makefile for agenkit-zig test harness

.PHONY: build clean test install

# Build the cross-language test harness
build:
	@echo "Building Zig cross-language test harness..."
	@cd .. && zig build build-harness
	@echo "✓ Build complete: ../zig-out/bin/cross_language_harness"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf ../zig-out ../zig-cache
	@echo "✓ Clean complete"

# Test the harness with health check
test: build
	@echo "Testing harness health check..."
	@echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ../zig-out/bin/cross_language_harness
	@echo ""
	@echo "Testing harness info..."
	@echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ../zig-out/bin/cross_language_harness

# Install (copy to bin directory)
install: build
	@echo "Installing harness..."
	@mkdir -p ../../bin
	@cp ../zig-out/bin/cross_language_harness ../../bin/
	@echo "✓ Installed to ../../bin/cross_language_harness"

.DEFAULT_GOAL := build
