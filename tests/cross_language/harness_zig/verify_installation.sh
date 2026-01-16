#!/bin/bash
# Verification script for Zig harness installation
# This script verifies that the harness is built correctly and working

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Zig Test Harness - Installation Verification                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if executable exists
if [ ! -f "harness_zig" ]; then
    echo "❌ Error: harness_zig executable not found"
    echo "   Run 'zig build' to create the executable"
    exit 1
fi

echo "✅ Executable found: harness_zig"

# Check if executable is actually executable
if [ ! -x "harness_zig" ]; then
    echo "❌ Error: harness_zig is not executable"
    echo "   Run 'chmod +x harness_zig' to fix"
    exit 1
fi

echo "✅ Executable permissions verified"

# Get file info
SIZE=$(ls -lh harness_zig | awk '{print $5}')
echo "✅ Executable size: $SIZE"

# Test health check
echo ""
echo "Testing health check..."
RESPONSE=$(echo '{"protocol_version":"1.0","request_id":"verify-1","command":"health_check","payload":{}}' | ./harness_zig)
if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

# Test get_info
echo ""
echo "Testing get_info..."
RESPONSE=$(echo '{"protocol_version":"1.0","request_id":"verify-2","command":"get_info","payload":{}}' | ./harness_zig)
if echo "$RESPONSE" | grep -q '"language":"zig"'; then
    echo "✅ Get info passed"

    # Extract version
    VERSION=$(echo "$RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "   Version: $VERSION"

    # Count supported patterns
    PATTERN_COUNT=$(echo "$RESPONSE" | grep -o '"patterns_supported":\[[^]]*\]' | tr ',' '\n' | wc -l)
    echo "   Patterns supported: $PATTERN_COUNT"
else
    echo "❌ Get info failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

# Test a simple pattern execution
echo ""
echo "Testing pattern execution (Reflection)..."
REQUEST='{"protocol_version":"1.0","request_id":"verify-3","command":"execute_test","payload":{"pattern":"Reflection","scenario_id":"test","input":{"message":{"role":"user","content":"Test message","metadata":{}},"config":{"max_iterations":2}}}}'
RESPONSE=$(echo "$REQUEST" | ./harness_zig)
if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ Pattern execution passed"
else
    echo "❌ Pattern execution failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   ✅ All verification checks passed!                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "The Zig harness is ready for use."
echo ""
echo "Next steps:"
echo "  • Run './quick_test.py' for comprehensive testing"
echo "  • Run '../run_equivalence_tests.py --language zig' for full equivalence testing"
echo "  • See README.md for more information"
echo ""
