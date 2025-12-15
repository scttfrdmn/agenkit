#!/bin/bash
# Build agenkit-rust for WebAssembly
set -e

echo "=== Building agenkit-rust for WASM ==="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# IMPORTANT: Must use rustup's toolchain, not Homebrew rust
# Homebrew rust doesn't have wasm32-unknown-unknown target support
export PATH="$HOME/.cargo/bin:$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin:/usr/bin:/bin"

# Verify target is installed
if ! rustup target list --installed | grep -q "wasm32-unknown-unknown"; then
    echo -e "${YELLOW}Installing wasm32-unknown-unknown target...${NC}"
    rustup target add wasm32-unknown-unknown
fi

# Build for WASM
echo -e "${GREEN}Building library...${NC}"
cargo build --target wasm32-unknown-unknown \
    --no-default-features \
    --features wasm \
    --lib \
    --release

# Check output
WASM_FILE="target/wasm32-unknown-unknown/release/agenkit.wasm"
if [ -f "$WASM_FILE" ]; then
    SIZE=$(du -h "$WASM_FILE" | cut -f1)
    echo ""
    echo -e "${GREEN}✓ Build successful!${NC}"
    echo -e "  File: $WASM_FILE"
    echo -e "  Size: $SIZE"
else
    echo -e "${RED}✗ Build failed - no WASM output${NC}"
    exit 1
fi

echo ""
echo "=== Build complete ==="
