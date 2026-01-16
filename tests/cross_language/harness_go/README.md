# Go Test Harness for Cross-Language Equivalence Testing

This is the Go implementation of the cross-language test harness for Agenkit pattern testing.

## Overview

The Go harness implements the JSON protocol v1.0 specification for executing pattern tests. It provides identical behavior to the Python reference harness for equivalence testing.

## Structure

```
harness_go/
├── main.go          - Main harness implementation
├── main_test.go     - Unit tests for harness
├── go.mod           - Go module file with dependencies
├── go.sum           - Dependency checksums
└── README.md        - This file
```

## Building

From the `harness_go` directory:

```bash
# Build executable in parent directory
go build -o ../harness_go_bin main.go

# Or build in current directory
go build -o harness_go main.go
```

## Testing

Run unit tests:

```bash
# Run all tests
go test -v

# Run specific test
go test -v -run TestHealthCheck
go test -v -run TestReflectionPattern
```

## Usage

The harness reads JSON requests from stdin and writes JSON responses to stdout.

### Health Check

```bash
echo '{"protocol_version":"1.0","request_id":"test1","command":"health_check","payload":{}}' | ./harness_go_bin
```

### Get Info

```bash
echo '{"protocol_version":"1.0","request_id":"test2","command":"get_info","payload":{}}' | ./harness_go_bin
```

### Execute Test

```bash
cat <<'EOF' | ./harness_go_bin
{
  "protocol_version": "1.0",
  "request_id": "test3",
  "command": "execute_test",
  "payload": {
    "pattern": "Reflection",
    "scenario_id": "reflection_basic",
    "input": {
      "message": {
        "role": "user",
        "content": "Write a poem about technology",
        "metadata": {}
      },
      "config": {
        "max_iterations": 3
      }
    }
  }
}
EOF
```

## Supported Patterns

The Go harness currently supports these patterns:

1. **Reflection** - Iterative self-improvement through generation and critique
2. **Sequential** - Pipeline-style agent composition
3. **Parallel** - Concurrent execution with result aggregation
4. **ReAct** - Reasoning + Acting with tool use
5. **Conversational** - Context-aware multi-turn conversations
6. **Task** - One-shot task execution with retries

## Implementation Details

### MockAgent

The harness includes a `MockAgent` that provides deterministic responses for testing. It handles:

- ReAct pattern scenarios (calculation, multi-step, factual questions)
- Reflection pattern (poetry generation, critique)
- Task pattern (email extraction, impossible tasks)
- Conversational pattern (name recall from history)
- Default responses for generic scenarios

### Protocol Compliance

The harness fully implements the JSON protocol v1.0:

- **Request format**: `protocol_version`, `request_id`, `command`, `payload`
- **Response format**: `protocol_version`, `request_id`, `status`, `result`, `error`
- **Exit codes**:
  - 0 = Success
  - 1 = Error
  - 2 = Protocol error (invalid JSON)
  - 4 = Internal error

### Error Handling

All errors are caught and returned as proper JSON error responses:

```json
{
  "protocol_version": "1.0",
  "request_id": "test1",
  "status": "error",
  "error": {
    "type": "ExecutionError",
    "message": "Task cannot be completed",
    "details": {}
  }
}
```

## Mock Tools

The harness includes mock tools for ReAct pattern testing:

- **MockCalculator** - Returns "360" for calculations
- **MockSearch** - Returns "Temperature in Paris: 20°C"
- **MockUnitConverter** - Returns "68°F" for temperature conversions
- **GenericMockTool** - Returns "mock result" for other tools

## Dependencies

- **agenkit-go** - Core agenkit Go library (via local replace directive)
- **github.com/google/uuid** - UUID generation (indirect dependency)

## Testing with Python Test Runner

The harness is designed to work with the Python test runner:

```bash
# From tests/cross_language directory
python run_equivalence_tests.py --languages python go
```

## Development

To add support for additional patterns:

1. Add pattern case to `executeTest()` function
2. Implement pattern-specific execution function (e.g., `executeNewPattern()`)
3. Add pattern name to supported patterns list in `getInfo()`
4. Add MockAgent responses for pattern-specific scenarios
5. Add unit tests in `main_test.go`

## Performance

The Go harness is designed for:

- **Fast startup** - Compiled binary starts quickly
- **Low latency** - Direct pattern execution without interpretation overhead
- **Deterministic behavior** - MockAgent provides consistent responses
- **Small memory footprint** - Efficient resource usage

## Exit Codes

- **0**: Success - test executed successfully
- **1**: Error - test execution failed
- **2**: Protocol error - invalid JSON or protocol version mismatch
- **4**: Internal error - unexpected error in harness

## Troubleshooting

### Build errors

```bash
# Clean and rebuild dependencies
go clean
go mod tidy
go build -o ../harness_go_bin main.go
```

### Test failures

```bash
# Run tests with verbose output
go test -v

# Run specific test
go test -v -run TestName
```

### Protocol errors

Ensure JSON input is valid and includes all required fields:
- `protocol_version` (must be "1.0")
- `request_id` (unique identifier)
- `command` (one of: health_check, get_info, execute_test)
- `payload` (command-specific data)

## Version

- **Harness Version**: 0.44.0
- **Protocol Version**: 1.0
- **Go Version**: 1.24.0 (minimum)

## License

Same as parent Agenkit project.

## See Also

- [PROTOCOL.md](../PROTOCOL.md) - JSON protocol specification
- [harness_python.py](../harness_python.py) - Python reference implementation
- [README.md](../README.md) - Cross-language testing overview
