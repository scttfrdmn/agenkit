# TypeScript Test Harness for Cross-Language Equivalence Testing

This is the TypeScript implementation of the cross-language test harness for Agenkit.

## Overview

The TypeScript harness implements the JSON protocol v1.0 for executing pattern tests and comparing behavior across languages. It provides deterministic test responses through MockAgent implementations.

## Structure

```
harness_ts/
├── index.ts          # Main harness implementation
├── package.json      # Package configuration
├── tsconfig.json     # TypeScript configuration
├── dist/
│   └── index.js      # Compiled JavaScript (executable)
└── README.md         # This file
```

## Setup

1. Install dependencies:
```bash
cd harness_ts
npm install
```

2. Build TypeScript:
```bash
npm run build
```

This will compile `index.ts` to `dist/index.js` with the shebang preserved.

## Usage

### Direct Execution

The harness reads JSON from stdin and writes JSON to stdout:

```bash
echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | node dist/index.js
```

### Supported Commands

1. **health_check** - Verify harness is responsive
2. **get_info** - Get harness information and capabilities
3. **execute_test** - Execute a pattern test

### Supported Patterns

Currently implements 6 core patterns:

- **Reflection** - Self-critique and iterative refinement
- **Sequential** - Pipeline-style agent composition
- **Parallel** - Concurrent agent execution with aggregation
- **ReAct** - Reasoning and acting with tools
- **Conversational** - Multi-turn conversation with history
- **Task** - One-shot execution with lifecycle management

## Implementation Details

### MockAgent

The `MockAgent` class provides deterministic responses for testing:

- Implements both `Agent` and `LLMClient` interfaces
- Pattern-specific responses for ReAct, Reflection, Task patterns
- Email extraction, poetry generation, and other test scenarios
- Compatible with ConversationalAgent via `chat()` method

### Mock Tools

- `MockCalculator` - Returns "360" for calculations
- `MockSearch` - Returns "Temperature in Paris: 20°C"
- `MockUnitConverter` - Returns "68°F"
- `GenericTool` - Returns "mock result"

### JSON Protocol

The harness strictly follows the protocol spec at `../PROTOCOL.md`:

- **Request format**: `{protocol_version, request_id, command, payload}`
- **Response format**: `{protocol_version, request_id, status, result, error}`
- **Exit codes**: 0 (success), 1 (error), 2 (protocol error), 4 (internal error)

### Behavior Tracking

The harness extracts and reports behavioral characteristics:

- **turns** - Number of interaction turns
- **tool_calls** - Tools called during execution (ReAct)
- **sub_agents** - Sub-agents invoked (Sequential, Parallel)

These are used for cross-language equivalence validation.

## Testing

### Health Check

```bash
echo '{"protocol_version":"1.0","request_id":"test-1","command":"health_check","payload":{}}' | node dist/index.js
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
echo '{"protocol_version":"1.0","request_id":"test-2","command":"get_info","payload":{}}' | node dist/index.js
```

### Execute Pattern Test

Example Reflection pattern test:

```bash
echo '{
  "protocol_version": "1.0",
  "request_id": "test-3",
  "command": "execute_test",
  "payload": {
    "pattern": "Reflection",
    "scenario_id": "reflection_basic",
    "input": {
      "message": {
        "role": "user",
        "content": "Write a poem about technology"
      },
      "config": {
        "max_iterations": 3
      }
    }
  }
}' | node dist/index.js
```

## Development

### Adding New Patterns

1. Import pattern from `agenkit`:
```typescript
import { NewPattern } from 'agenkit';
```

2. Add to `PATTERNS` registry:
```typescript
const PATTERNS = {
  // ...
  NewPattern: 'NewPattern',
};
```

3. Add case to `executeTest()` switch:
```typescript
case 'NewPattern': {
  const config = { /* ... */ };
  agent = new NewPattern(config);
  outputMessage = await agent.process(message);
  break;
}
```

4. Update MockAgent if pattern needs specific responses

### Code Quality

The TypeScript code follows Agenkit standards:

- **Type safety** - Full TypeScript types, no `any`
- **Error handling** - Try-catch with proper error responses
- **Protocol compliance** - Strict adherence to JSON protocol v1.0
- **Idiomatic** - Uses TypeScript/Node.js best practices

## Troubleshooting

### Import errors

If you see "Cannot find module 'agenkit'":
```bash
cd harness_ts
npm install
```

### Build errors

If TypeScript compilation fails:
```bash
npx tsc --version  # Should be 5.3.0+
npm run build
```

### Runtime errors

Check that:
1. Node.js version is 18.0.0 or higher
2. All dependencies are installed
3. TypeScript has been compiled to JavaScript
4. Input JSON is valid and follows protocol spec

## Version

- **Protocol Version**: 1.0
- **Harness Version**: 0.44.0
- **Node.js**: >=18.0.0
- **TypeScript**: ^5.3.0

## References

- Protocol spec: `../PROTOCOL.md`
- Python reference harness: `../harness_python.py`
- Test specs: `../specs/`
- Agenkit TypeScript: `../../../agenkit-ts/`
