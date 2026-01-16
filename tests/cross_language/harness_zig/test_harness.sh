#!/bin/bash
# Test script for Zig harness

set -e

HARNESS="./harness_zig"

echo "Testing Zig harness..."

# Test 1: Health check
echo "Test 1: Health check"
echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | $HARNESS
echo ""

# Test 2: Get info
echo "Test 2: Get info"
echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | $HARNESS
echo ""

# Test 3: Execute Reflection pattern
echo "Test 3: Execute Reflection pattern"
echo '{"protocol_version":"1.0","request_id":"test-3","command":"execute_test","payload":{"pattern":"Reflection","scenario_id":"reflection_basic","input":{"message":{"role":"user","content":"Write a short poem","metadata":{}},"config":{"max_iterations":3}}}}' | $HARNESS
echo ""

echo "All tests completed!"
