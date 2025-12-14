# Cross-Language Test Harness Protocol

## Overview

This document defines the JSON-based communication protocol between the Python test runner and language-specific test harnesses.

## Architecture

```
┌─────────────────────┐
│  Python Test Runner │
│  (Orchestrator)     │
└──────────┬──────────┘
           │
           │ JSON over stdin/stdout
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐   ┌────────┐
│   Go   │   │  Rust  │  ... (6 languages)
│Harness │   │Harness │
└────────┘   └────────┘
```

## Communication Flow

1. **Runner** sends test request as JSON to harness stdin
2. **Harness** executes test using language implementation
3. **Harness** returns result as JSON to stdout
4. **Runner** compares results across languages

## Message Format

### Request Message

Sent from runner to harness:

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid-v4",
  "command": "execute_test",
  "payload": {
    "pattern": "reflection",
    "scenario_id": "reflection_basic",
    "input": {
      "message": {
        "role": "user",
        "content": "Write a short poem",
        "metadata": {}
      },
      "config": {
        "max_iterations": 3
      }
    }
  }
}
```

#### Request Fields

- **protocol_version**: Protocol version (semantic versioning)
- **request_id**: Unique identifier for request tracing
- **command**: Command to execute
  - `execute_test` - Run a test scenario
  - `get_info` - Get harness information
  - `health_check` - Check harness health
- **payload**: Command-specific data

### Response Message

Sent from harness to runner:

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid-v4",
  "status": "success",
  "result": {
    "output": {
      "message": {
        "role": "assistant",
        "content": "Roses are red...",
        "metadata": {
          "iterations": 2,
          "improved": true
        }
      },
      "behavior": {
        "turns": 4,
        "tool_calls": [],
        "sub_agents": []
      }
    },
    "execution_info": {
      "duration_ms": 1250,
      "llm_calls": 4,
      "tokens_used": 850
    }
  },
  "error": null
}
```

#### Response Fields

- **protocol_version**: Protocol version (must match request)
- **request_id**: Matching request ID
- **status**: Execution status
  - `success` - Test executed successfully
  - `error` - Test execution failed
  - `timeout` - Test timed out
  - `not_implemented` - Pattern not implemented
- **result**: Test results (when status = success)
- **error**: Error details (when status = error)

### Error Response

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid-v4",
  "status": "error",
  "result": null,
  "error": {
    "type": "ValidationError",
    "message": "Invalid configuration: max_iterations must be positive",
    "details": {
      "field": "max_iterations",
      "value": -1
    },
    "stack_trace": "..."
  }
}
```

## Commands

### 1. execute_test

Execute a test scenario for a specific pattern.

**Request**:
```json
{
  "command": "execute_test",
  "payload": {
    "pattern": "sequential",
    "scenario_id": "sequential_basic",
    "input": {
      "message": {...},
      "config": {...}
    }
  }
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "output": {
      "message": {...},
      "behavior": {...}
    },
    "execution_info": {...}
  }
}
```

### 2. get_info

Get harness information and capabilities.

**Request**:
```json
{
  "command": "get_info",
  "payload": {}
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "language": "rust",
    "version": "0.41.0",
    "patterns_supported": [
      "reflection",
      "sequential",
      "parallel",
      ...
    ],
    "capabilities": {
      "streaming": true,
      "async": true,
      "llm_providers": ["openai", "anthropic"]
    }
  }
}
```

### 3. health_check

Verify harness is responsive.

**Request**:
```json
{
  "command": "health_check",
  "payload": {}
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "healthy": true,
    "uptime_seconds": 125.3
  }
}
```

## Data Types

### Message

```typescript
interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, any>;
}
```

### Behavior

Observable behavioral characteristics:

```typescript
interface Behavior {
  turns?: number;              // Number of interaction turns
  tool_calls?: string[];       // Tools called during execution
  sub_agents?: string[];       // Sub-agents invoked
  iterations?: number;         // Iterations performed (for iterative patterns)
  checkpoints?: string[];      // Checkpoints created (for autonomous)
  [key: string]: any;         // Pattern-specific behavior
}
```

### ExecutionInfo

Runtime execution metrics:

```typescript
interface ExecutionInfo {
  duration_ms: number;         // Execution time
  llm_calls?: number;          // Number of LLM API calls
  tokens_used?: number;        // Total tokens consumed
  memory_bytes?: number;       // Memory used
  [key: string]: any;         // Additional metrics
}
```

### Error

```typescript
interface Error {
  type: string;               // Error type/class
  message: string;            // Human-readable message
  details?: Record<string, any>;  // Additional error context
  stack_trace?: string;       // Stack trace (optional)
}
```

## Pattern-Specific Payloads

Some patterns require additional fields:

### Reflection Pattern

```json
{
  "pattern": "reflection",
  "input": {
    "config": {
      "max_iterations": 3,
      "improvement_threshold": 0.1
    }
  }
}
```

### Sequential Pattern

```json
{
  "pattern": "sequential",
  "input": {
    "config": {
      "agents": [
        {"name": "agent1", "type": "echo"},
        {"name": "agent2", "type": "echo"}
      ]
    }
  }
}
```

### ReAct Pattern

```json
{
  "pattern": "react",
  "input": {
    "config": {
      "tools": [
        {
          "name": "calculator",
          "description": "Performs arithmetic"
        }
      ],
      "max_iterations": 5
    }
  }
}
```

## Implementation Requirements

### Harness Requirements

Each language harness must:

1. **Read JSON from stdin**: Parse request messages
2. **Execute tests**: Instantiate and run pattern implementations
3. **Write JSON to stdout**: Serialize response messages
4. **Handle errors gracefully**: Catch and report errors
5. **Timeout handling**: Respect test timeouts
6. **Clean shutdown**: Handle SIGTERM/SIGINT

### Example Harness Execution

```bash
# Python test runner invokes harness
echo '{"command":"execute_test",...}' | ./harness_executable

# Harness reads stdin, executes test, writes stdout
{"status":"success","result":{...}}
```

### Harness Exit Codes

- **0**: Success (valid JSON response written)
- **1**: Error (error JSON response written)
- **2**: Invalid protocol
- **3**: Timeout
- **4**: Internal error (no JSON response)

## Validation

### Request Validation

Harness must validate:
- Protocol version compatibility
- Required fields present
- Pattern is supported
- Config is valid for pattern

### Response Validation

Runner must validate:
- Protocol version matches
- Request ID matches
- Status is valid enum
- Result structure is correct

## Versioning

Protocol uses semantic versioning:

- **Major**: Breaking changes to message format
- **Minor**: Backward-compatible additions
- **Patch**: Bug fixes, clarifications

**Current Version**: 1.0.0

### Compatibility Rules

- Harnesses must support their protocol version
- Runner checks version in first message
- Mismatched major versions = error
- Minor version differences = backward compatible

## Testing Protocol

Test the protocol implementation:

```bash
# 1. Start harness
./harness_go &
HARNESS_PID=$!

# 2. Send health check
echo '{"command":"health_check","protocol_version":"1.0","request_id":"test-1","payload":{}}' | \
  ./harness_go

# 3. Send test execution
cat test_request.json | ./harness_go

# 4. Kill harness
kill $HARNESS_PID
```

## Error Handling

### Common Errors

| Error Type | Description | Example |
|------------|-------------|---------|
| `ValidationError` | Invalid input | "max_iterations must be positive" |
| `PatternNotFound` | Pattern not implemented | "Pattern 'xyz' not found" |
| `ExecutionError` | Runtime error | "Agent failed during execution" |
| `TimeoutError` | Execution timeout | "Test timed out after 30s" |
| `ProtocolError` | Protocol violation | "Invalid JSON format" |

### Error Recovery

Runner should:
1. Log error details
2. Mark test as failed
3. Continue with next test
4. Include in final report

## Performance Considerations

### Throughput

- Runner can execute tests in parallel across languages
- Each harness handles one test at a time
- Use process pool for parallel execution

### Memory

- Harness should clean up after each test
- Runner monitors harness memory usage
- Restart harness if memory exceeds threshold

### Timeouts

Default timeouts:
- `health_check`: 5 seconds
- `get_info`: 10 seconds
- `execute_test`: 60 seconds (configurable per pattern)

## Security

### Sandboxing

- Harnesses should run in isolated environment
- Limit file system access
- Restrict network access (except LLM APIs)
- Resource limits (CPU, memory, time)

### Input Validation

- Sanitize all inputs
- Validate JSON schema
- Check for injection attacks
- Limit payload sizes

## Future Extensions

Potential protocol enhancements:

- Streaming support for long-running tests
- Binary protocol for performance
- WebSocket transport for persistent connections
- Distributed execution across machines
- Caching of LLM responses

---

**Version**: 1.0.0
**Last Updated**: December 13, 2025
**Status**: Draft for Implementation
