#!/bin/bash
# Test script for C++ harness

set -e

echo "Testing C++ harness..."
echo

# Test 1: Health Check
echo "Test 1: Health Check"
echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ./harness_cpp/harness_cpp | jq .
echo

# Test 2: Get Info
echo "Test 2: Get Info"
echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ./harness_cpp/harness_cpp | jq .
echo

# Test 3: Reflection Pattern Test
echo "Test 3: Reflection Pattern"
cat <<'EOF' | ./harness_cpp/harness_cpp | jq .
{
  "protocol_version": "1.0",
  "request_id": "test-3",
  "command": "execute_test",
  "payload": {
    "pattern": "Reflection",
    "scenario_id": "reflection_basic",
    "input": {
      "message": {
        "role": "user",
        "content": "Write a short poem about technology",
        "metadata": {}
      },
      "config": {
        "max_iterations": 2
      }
    }
  }
}
EOF
echo

# Test 4: Sequential Pattern Test
echo "Test 4: Sequential Pattern"
cat <<'EOF' | ./harness_cpp/harness_cpp | jq .
{
  "protocol_version": "1.0",
  "request_id": "test-4",
  "command": "execute_test",
  "payload": {
    "pattern": "Sequential",
    "scenario_id": "sequential_basic",
    "input": {
      "message": {
        "role": "user",
        "content": "Process this message",
        "metadata": {}
      },
      "config": {
        "agents": [
          {"name": "agent1", "type": "echo"},
          {"name": "agent2", "type": "echo"}
        ]
      }
    }
  }
}
EOF
echo

echo "All tests completed!"
