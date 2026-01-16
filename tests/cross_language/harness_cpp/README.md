# C++ Test Harness for Cross-Language Equivalence Testing

This directory contains the C++ implementation of the cross-language test harness for Agenkit pattern equivalence testing.

## Overview

The C++ harness implements the JSON protocol v1.0 for executing pattern tests, enabling cross-language equivalence testing between Python, Go, TypeScript, Rust, Zig, and C++ implementations.

## Building

### Prerequisites

- CMake 3.16 or later
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- nlohmann/json library (auto-fetched if not found)
- Pre-built agenkit-cpp library

### Build Instructions

```bash
# From this directory
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Copy executable to parent directory
cp build/harness_cpp ../harness_cpp
```

Or use the one-liner from the repository root:

```bash
cd tests/cross_language/harness_cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release && \
cmake --build build && \
cp build/harness_cpp ../harness_cpp
```

## Usage

The harness reads JSON requests from stdin and writes JSON responses to stdout.

### Health Check

```bash
echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ./harness_cpp
```

Expected output:
```json
{
  "protocol_version": "1.0",
  "request_id": "test-1",
  "status": "success",
  "result": {
    "healthy": true,
    "uptime_seconds": 0.0
  },
  "error": null
}
```

### Get Info

```bash
echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ./harness_cpp
```

### Execute Pattern Test

```bash
cat <<EOF | ./harness_cpp
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
```

## Supported Patterns

The C++ harness currently supports the following patterns:

- ✅ **Reflection** - Self-improvement through iterative critique
- ✅ **Sequential** - Linear agent pipeline
- ✅ **Parallel** - Concurrent agent execution
- 🚧 **ReAct** - Reasoning + Acting with tools (stub)
- 🚧 **Conversational** - Multi-turn conversations (stub)
- 🚧 **Task** - One-shot task execution (stub)

Additional patterns will be implemented to match the Python reference harness (18 total patterns).

## Architecture

### Components

1. **MockAgent**: Deterministic test agent that returns predictable responses
   - Matches Python harness behavior for equivalence testing
   - Handles pattern-specific scenarios (Reflection, ReAct, Sequential, etc.)
   - Implements the `Agent` interface from `agenkit::core`

2. **Command Handlers**:
   - `handle_health_check()`: Health status
   - `handle_get_info()`: Harness capabilities
   - `handle_execute_test()`: Pattern execution

3. **Pattern Executors**:
   - `execute_reflection()`: Reflection pattern with generator + critic
   - `execute_sequential()`: Sequential agent pipeline
   - `execute_parallel()`: Parallel agent execution with aggregation
   - Additional pattern executors (stubs for future implementation)

### JSON Protocol

The harness implements protocol version 1.0, defined in `../PROTOCOL.md`:

- **Request**: `{protocol_version, request_id, command, payload}`
- **Response**: `{protocol_version, request_id, status, result, error}`
- **Exit Codes**: 0=success, 1=error, 2=protocol error, 4=internal error

## Testing

Run the test suite:

```bash
cd /Users/scttfrdmn/src/agenkit/tests/cross_language
./test_cpp_harness.sh
```

Or run individual tests manually (see examples in `test_cpp_harness.sh`).

## Implementation Notes

### C++17 Features Used

- `std::future` for async operations
- `std::shared_ptr` for agent lifecycle
- `nlohmann::json` for JSON serialization
- `std::chrono` for timing measurements

### Error Handling

- Uses `Result<T, E>` type from `agenkit::core::result.hpp`
- Follows Rust-style error handling (ok/err variants)
- All errors include type, message, and optional details

### Performance

- Compiled with Release optimizations (`-O3`)
- Static linking of agenkit library
- Minimal allocations in hot path
- Typical test execution: <10ms per pattern

## Troubleshooting

### Build Errors

**Problem**: Cannot find agenkit library
```
Solution: Build agenkit-cpp first:
cd ../../../agenkit-cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

**Problem**: Cannot find nlohmann/json
```
Solution: CMake will auto-fetch from GitHub. Ensure internet access.
```

### Runtime Errors

**Problem**: Protocol version mismatch
```json
{"error": {"type": "ProtocolError", "message": "Protocol version mismatch"}}
```
Solution: Update harness to match protocol version in PROTOCOL.md

**Problem**: Pattern not implemented
```json
{"status": "not_implemented", "error": {"type": "NotImplemented"}}
```
Solution: Pattern is stubbed. Implementation coming soon.

## Development

### Adding New Patterns

1. Add pattern-specific logic to `MockAgent::process()`
2. Implement `execute_<pattern>()` function
3. Register in `handle_execute_test()` dispatcher
4. Update `handle_get_info()` patterns list
5. Add test case to `test_cpp_harness.sh`

### Matching Python Behavior

The MockAgent must return identical responses to the Python reference harness for equivalence testing to pass:

- Same output content
- Same metadata keys/values
- Same behavior tracking (turns, tool_calls, sub_agents)

Reference: `/Users/scttfrdmn/src/agenkit/tests/cross_language/harness_python.py`

## References

- **Protocol Spec**: `../PROTOCOL.md`
- **Python Reference**: `../harness_python.py`
- **Test Specs**: `../specs/*.json`
- **Agenkit C++ Docs**: `../../../agenkit-cpp/README.md`

## Version History

- **v1.0.0** (2026-01-13): Initial implementation
  - Core protocol support (health_check, get_info, execute_test)
  - Reflection, Sequential, Parallel patterns
  - MockAgent with deterministic responses
  - CMake build system

## License

Same as Agenkit project (see repository root).
