# Makefile for agenkit-cpp test harness

.PHONY: build clean test

# Build the cross-language test harness
build:
	@echo "Building C++ cross-language test harness..."
	@mkdir -p ../build
	@cd ../build && cmake .. && cmake --build . --target cross_language_harness
	@echo "✓ Build complete: ../build/cross_language_harness"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf ../build
	@echo "✓ Clean complete"

# Test the harness with health check
test: build
	@echo "Testing harness health check..."
	@echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ../build/cross_language_harness
	@echo ""
	@echo "Testing harness info..."
	@echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ../build/cross_language_harness

# Install (copy to bin directory)
install: build
	@echo "Installing harness..."
	@mkdir -p ../../bin
	@cp ../build/cross_language_harness ../../bin/
	@echo "✓ Installed to ../../bin/cross_language_harness"

.DEFAULT_GOAL := build
