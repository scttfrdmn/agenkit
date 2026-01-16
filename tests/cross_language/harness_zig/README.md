# Zig Test Harness for Cross-Language Equivalence Testing

This directory contains the Zig implementation of the cross-language test harness, which implements the JSON protocol for executing pattern tests.

## Building

Build the harness executable:

```bash
cd tests/cross_language/harness_zig
zig build
```

This will create the `harness_zig` executable in the current directory.

## Usage

The harness reads JSON requests from stdin and writes JSON responses to stdout.

### Health Check

```bash
echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | ./harness_zig
```

Expected output:
```json
{"protocol_version":"1.0","request_id":"test-1","status":"success","result":{"healthy":true,"uptime_seconds":0.0},"error":null}
```

### Get Info

```bash
echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | ./harness_zig
```

Expected output:
```json
{"protocol_version":"1.0","request_id":"test-2","status":"success","result":{"language":"zig","version":"0.29.2","patterns_supported":[...],"capabilities":{...}},"error":null}
```

### Execute Test

```bash
echo '{"protocol_version":"1.0","request_id":"test-3","command":"execute_test","payload":{"pattern":"Reflection","scenario_id":"reflection_basic","input":{"message":{"role":"user","content":"Write a short poem","metadata":{}},"config":{"max_iterations":3}}}}' | ./harness_zig
```

## Testing

Run the test script to verify the harness works correctly:

```bash
chmod +x test_harness.sh
./test_harness.sh
```

## Supported Patterns

The harness currently supports all 18 patterns implemented in Agenkit:

1. **Reflection** - Iterative self-improvement
2. **Sequential** - Pipeline of agents
3. **Parallel** - Concurrent execution
4. **Router** - Dynamic agent selection
5. **ReAct** - Reasoning + Acting
6. **Conversational** - Multi-turn dialogue
7. **AgentsAsTools** - Agents wrapped as tools
8. **Fallback** - Cascading fallbacks
9. **Supervisor** - Task decomposition
10. **Planning** - Multi-step planning
11. **Task** - One-shot execution
12. **Collaborative** - Consensus building
13. **HumanInLoop** - Human approval
14. **Autonomous** - Goal-driven execution
15. **Multiagent** - Multi-agent coordination
16. **Orchestration** - Workflow orchestration
17. **Memory** - Hierarchical memory
18. **ReasoningWithTools** - Enhanced reasoning

## Protocol

The harness implements the JSON protocol v1.0 as defined in `../PROTOCOL.md`.

### Request Format

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid-v4",
  "command": "execute_test",
  "payload": {
    "pattern": "reflection",
    "scenario_id": "reflection_basic",
    "input": {
      "message": {...},
      "config": {...}
    }
  }
}
```

### Response Format

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid-v4",
  "status": "success",
  "result": {
    "output": {
      "message": {...},
      "behavior": {...}
    },
    "execution_info": {...}
  },
  "error": null
}
```

## Exit Codes

- **0**: Success (valid JSON response written)
- **1**: Error (error JSON response written)
- **2**: Invalid protocol
- **3**: Timeout
- **4**: Internal error (no JSON response)

## Implementation Details

The harness uses:
- `std.json` for JSON parsing and serialization
- `std.io` for stdin/stdout communication
- Mock implementations for deterministic testing

All pattern implementations return predictable outputs that match the Python reference harness for equivalence testing.

## Development

### File Structure

```
harness_zig/
├── build.zig           # Build configuration
├── src/
│   └── main.zig        # Main harness implementation
├── test_harness.sh     # Test script
└── README.md           # This file
```

### Building for Release

```bash
zig build -Doptimize=ReleaseFast
```

### Debugging

Build in debug mode to get better error messages:

```bash
zig build -Doptimize=Debug
```

## Integration with Test Runner

The Python test runner (`../run_equivalence_tests.py`) automatically invokes this harness when testing the Zig implementation. The harness manager handles process lifecycle and communication.

## Version

Current version: **0.44.0**

Protocol version: **1.0**

Last updated: January 13, 2026
