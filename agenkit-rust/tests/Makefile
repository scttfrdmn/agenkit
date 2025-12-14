# Makefile for agenkit-rust test harness

.PHONY: build clean test install

# Build the cross-language test harness
build:
	@echo "Building Rust cross-language test harness..."
	@cd .. && cargo build --bin cross_language_harness --release
	@echo "✓ Build complete: ../target/release/cross_language_harness"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@cd .. && cargo clean
	@echo "✓ Clean complete"

# Test the harness with health check
test: build
	@echo "Testing harness health check..."
	@echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ../target/release/cross_language_harness
	@echo ""
	@echo "Testing harness info..."
	@echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ../target/release/cross_language_harness

# Install (copy to bin directory)
install: build
	@echo "Installing harness..."
	@mkdir -p ../../bin
	@cp ../target/release/cross_language_harness ../../bin/
	@echo "✓ Installed to ../../bin/cross_language_harness"

.DEFAULT_GOAL := build
