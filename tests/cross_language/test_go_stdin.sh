#!/bin/bash
# Simple test to verify Go harness works with stdin

set -e

cd "$(dirname "$0")"

# Build the harness binary (no longer committed — see .gitignore).
echo "Building Go harness..."
( cd harness_go && go build -o ../harness_go_bin . )
echo ""

echo "Testing Go harness with stdin..."
echo ""

# Test 1: Health check
echo "1. Health Check:"
result=$(cat <<'EOF' | ./harness_go_bin
{"protocol_version":"1.0","request_id":"test1","command":"health_check","payload":{}}
EOF
)
echo "$result" | python3 -m json.tool
echo ""

# Test 2: Get info
echo "2. Get Info:"
result=$(cat <<'EOF' | ./harness_go_bin
{"protocol_version":"1.0","request_id":"test2","command":"get_info","payload":{}}
EOF
)
echo "$result" | python3 -m json.tool
echo ""

# Test 3: Simple reflection test
echo "3. Reflection Pattern:"
result=$(cat <<'EOF' | ./harness_go_bin
{"protocol_version":"1.0","request_id":"test3","command":"execute_test","payload":{"pattern":"Reflection","scenario_id":"reflection_basic","input":{"message":{"role":"user","content":"Write a poem about technology","metadata":{}},"config":{"max_iterations":3}}}}
EOF
)
echo "$result" | python3 -m json.tool | head -30
echo ""

echo "✅ All tests completed successfully!"
