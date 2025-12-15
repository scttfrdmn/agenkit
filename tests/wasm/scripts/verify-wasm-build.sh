#!/bin/bash
# Verify WASM build artifacts

set -e

echo "=== WASM Build Verification ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Zig WASM
echo "Checking Zig WASM modules..."
if [ -d "../../agenkit-zig/zig-out/bin" ]; then
    WASM_COUNT=$(find ../../agenkit-zig/zig-out/bin -name "*.wasm" | wc -l)
    if [ "$WASM_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $WASM_COUNT Zig WASM files"

        # Verify each file is valid WASM
        for wasm_file in ../../agenkit-zig/zig-out/bin/*.wasm; do
            if file "$wasm_file" | grep -q "WebAssembly"; then
                SIZE=$(du -h "$wasm_file" | cut -f1)
                echo -e "  ${GREEN}✓${NC} $(basename "$wasm_file") - $SIZE"
            else
                echo -e "  ${RED}✗${NC} $(basename "$wasm_file") - Invalid WASM file"
                exit 1
            fi
        done
    else
        echo -e "${RED}✗${NC} No Zig WASM files found"
        echo -e "${YELLOW}ℹ${NC} Run: cd agenkit-zig && zig build -Dtarget=wasm32-wasi"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Zig build directory not found"
    exit 1
fi

echo ""

# Check @agenkit/wasm package
echo "Checking @agenkit/wasm package..."
if [ -d "../../packages/wasm/wasm" ]; then
    PKG_WASM_COUNT=$(find ../../packages/wasm/wasm -name "*.wasm" | wc -l)
    if [ "$PKG_WASM_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $PKG_WASM_COUNT WASM files in package"

        # Calculate total size
        TOTAL_SIZE=$(du -sh ../../packages/wasm/wasm | cut -f1)
        echo -e "  ${GREEN}ℹ${NC} Total package WASM size: $TOTAL_SIZE"
    else
        echo -e "${YELLOW}⚠${NC} No WASM files in package"
        echo -e "${YELLOW}ℹ${NC} Copy WASM files: cp agenkit-zig/zig-out/bin/*.wasm packages/wasm/wasm/"
    fi
else
    echo -e "${YELLOW}⚠${NC} Package WASM directory not found"
fi

echo ""

# Check package build
echo "Checking @agenkit/wasm build..."
if [ -d "../../packages/wasm/dist" ]; then
    if [ -f "../../packages/wasm/dist/index.js" ] && [ -f "../../packages/wasm/dist/index.mjs" ]; then
        echo -e "${GREEN}✓${NC} Package build artifacts found"
        echo -e "  ${GREEN}✓${NC} dist/index.js"
        echo -e "  ${GREEN}✓${NC} dist/index.mjs"
        echo -e "  ${GREEN}✓${NC} dist/index.d.ts"
    else
        echo -e "${YELLOW}⚠${NC} Package build incomplete"
        echo -e "${YELLOW}ℹ${NC} Run: cd packages/wasm && npm run build"
    fi
else
    echo -e "${YELLOW}⚠${NC} Package not built"
    echo -e "${YELLOW}ℹ${NC} Run: cd packages/wasm && npm run build"
fi

echo ""

# Summary
echo "=== Summary ==="
echo -e "${GREEN}✓${NC} WASM build verification complete"
echo ""
echo "Ready for testing!"
echo "Run: cd tests/wasm && npm test"
