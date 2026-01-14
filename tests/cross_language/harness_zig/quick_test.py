#!/usr/bin/env python3
"""Quick test script to verify Zig harness functionality."""

import json
import subprocess
import sys


def run_command_test(name, request):
    """Test a single command."""
    print(f"\n{'=' * 60}")
    print(f"Test: {name}")
    print(f"{'=' * 60}")

    # Run harness
    proc = subprocess.run(
        ["./harness_zig"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
    )

    # Check exit code
    if proc.returncode not in [0, 1]:
        print(f"❌ Unexpected exit code: {proc.returncode}")
        print(f"Stderr: {proc.stderr}")
        return False

    # Parse response
    try:
        response = json.loads(proc.stdout)
        print(f"✅ Status: {response['status']}")
        print(f"Request ID: {response['request_id']}")

        if response["status"] == "success":
            print(f"Result: {json.dumps(response.get('result', {}), indent=2)[:200]}...")
        else:
            print(f"Error: {response.get('error', {})}")

        return response["status"] == "success"
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse response: {e}")
        print(f"Stdout: {proc.stdout}")
        print(f"Stderr: {proc.stderr}")
        return False


def main():
    """Run all tests."""
    tests_passed = 0
    tests_failed = 0

    # Test 1: Health check
    if run_command_test(
        "Health Check",
        {
            "protocol_version": "1.0",
            "request_id": "test-1",
            "command": "health_check",
            "payload": {},
        },
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 2: Get info
    if run_command_test(
        "Get Info",
        {
            "protocol_version": "1.0",
            "request_id": "test-2",
            "command": "get_info",
            "payload": {},
        },
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 3: Execute Reflection pattern
    if run_command_test(
        "Execute Reflection Pattern",
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
                        "content": "Write a short poem",
                        "metadata": {},
                    },
                    "config": {"max_iterations": 3},
                },
            },
        },
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 4: Execute Sequential pattern
    if run_command_test(
        "Execute Sequential Pattern",
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
                        "content": "Process this",
                        "metadata": {},
                    },
                    "config": {
                        "agents": [
                            {"name": "agent1", "type": "echo"},
                            {"name": "agent2", "type": "echo"},
                        ]
                    },
                },
            },
        },
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 5: Execute Parallel pattern
    if run_command_test(
        "Execute Parallel Pattern",
        {
            "protocol_version": "1.0",
            "request_id": "test-5",
            "command": "execute_test",
            "payload": {
                "pattern": "Parallel",
                "scenario_id": "parallel_basic",
                "input": {
                    "message": {
                        "role": "user",
                        "content": "Process in parallel",
                        "metadata": {},
                    },
                    "config": {
                        "agents": [
                            {"name": "agent1", "type": "echo"},
                            {"name": "agent2", "type": "echo"},
                        ]
                    },
                },
            },
        },
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Test Summary")
    print(f"{'=' * 60}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print(f"Total: {tests_passed + tests_failed}")

    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
