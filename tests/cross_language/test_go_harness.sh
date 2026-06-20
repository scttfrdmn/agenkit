#!/bin/bash
# Test script for Go harness

set -e

cd "$(dirname "$0")"

# Build the harness binary (no longer committed — see .gitignore).
echo "Building Go harness..."
( cd harness_go && go build -o ../harness_go_bin . )
echo ""

# Health check
echo "Testing health_check..."
echo '{"protocol_version":"1.0","request_id":"test1","command":"health_check","payload":{}}' | ./harness_go_bin
echo ""

# Get info
echo "Testing get_info..."
echo '{"protocol_version":"1.0","request_id":"test2","command":"get_info","payload":{}}' | ./harness_go_bin
echo ""

# Simple reflection test
echo "Testing reflection pattern..."
cat <<'EOF' | ./harness_go_bin
{"protocol_version":"1.0","request_id":"test3","command":"execute_test","payload":{"pattern":"Reflection","scenario_id":"reflection_basic","input":{"message":{"role":"user","content":"Write a poem about technology","metadata":{}},"config":{"max_iterations":3}}}}
EOF
