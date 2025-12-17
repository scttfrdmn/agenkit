# Pattern Behavior Specifications

This directory contains formal specifications for all 18 Agenkit agent patterns. These specifications enable automated cross-language equivalence testing.

## Purpose

- **Cross-Language Testing**: Verify that pattern implementations behave identically across Python, Go, TypeScript, Rust, C++, and Zig
- **Contract Definition**: Define expected inputs, outputs, state transitions, and error conditions
- **Test Generation**: Automatically generate test cases from specifications
- **Documentation**: Serve as authoritative reference for pattern behavior

## Specification Format

Each pattern has a YAML specification file with the following structure:

```yaml
pattern:
  name: "Pattern Name"
  category: "composition|enhancement|specialized|advanced"
  description: "What the pattern does"
  version: "1.0.0"

interface:
  constructor:
    parameters:
      - name: "param_name"
        type: "Agent|Agent[]|number|string"
        required: true|false
        default: null
        description: "Parameter purpose"

  methods:
    process:
      input: "Message"
      output: "Message"
      async: true
      description: "Process a message"

behavior:
  state:
    - name: "state_variable"
      type: "string|number|object"
      description: "What this state tracks"

  execution:
    - step: 1
      action: "What happens"
      preconditions: ["Conditions that must be true"]
      postconditions: ["Conditions guaranteed after"]

  invariants:
    - "Property that always holds true"

error_handling:
  - condition: "When error occurs"
    error_type: "ErrorClassName"
    behavior: "What the pattern does"

test_cases:
  - name: "Test case name"
    description: "What this tests"
    input:
      message: { role: "user", content: "..." }
      config: { param: value }
    expected_output:
      message: { role: "assistant", content: "..." }
      metadata: { key: value }
    assertions:
      - "Property to verify"
```

## Pattern Categories

### Composition (2 patterns)
- **sequential**: Process messages through multiple agents in order
- **parallel**: Execute multiple agents concurrently and aggregate results

### Enhancement (3 patterns)
- **reflection**: Agent reviews and improves its own output iteratively
- **react**: Reasoning and Acting with tool usage
- **planning**: Create plan before execution, then execute step-by-step

### Specialized (6 patterns)
- **task**: Single-purpose agent for specific tasks
- **conversational**: Multi-turn dialogue with history
- **agents_as_tools**: Wrap agents as tools for other agents
- **orchestration**: Coordinate multiple agents with routing
- **router**: Route messages to appropriate specialist agents
- **reasoning_with_tools**: Enhanced reasoning combined with tool usage

### Advanced (7 patterns)
- **autonomous**: Self-directed goal pursuit
- **multiagent**: Multiple agents collaborate
- **memory_hierarchy**: Efficient memory management with multi-tier storage
- **supervisor**: Oversee and coordinate agent execution
- **collaborative**: Agents work together on shared tasks
- **fallback**: Try primary agent, fall back to alternatives on failure
- **human_in_loop**: Include human approval/feedback in execution

## Usage

### For Testing

```python
# Load specification
import yaml
with open('specs/patterns/sequential.yaml') as f:
    spec = yaml.safe_load(f)

# Run test cases
for test_case in spec['test_cases']:
    result = pattern.process(test_case['input']['message'])
    assert result.content == test_case['expected_output']['message']['content']
```

### For Documentation Generation

```bash
# Generate pattern documentation from specs
python scripts/generate_docs.py specs/patterns/*.yaml > docs/PATTERNS_REFERENCE.md
```

### For Cross-Language Validation

```bash
# Run equivalence tests across all languages
python tests/cross_language/test_equivalence.py --specs specs/patterns/*.yaml
```

## Pattern List

1. **agents_as_tools.yaml** - Wrap agents as tools
2. **autonomous.yaml** - Self-directed goal pursuit
3. **collaborative.yaml** - Shared task collaboration
4. **conversational.yaml** - Multi-turn dialogue
5. **fallback.yaml** - Primary with fallback alternatives
6. **human_in_loop.yaml** - Human approval integration
7. **memory_hierarchy.yaml** - Multi-tier memory management
8. **multiagent.yaml** - Multi-agent collaboration
9. **orchestration.yaml** - Agent coordination and routing
10. **parallel.yaml** - Concurrent execution
11. **planning.yaml** - Plan-then-execute
12. **react.yaml** - Reasoning and Acting
13. **reasoning_with_tools.yaml** - Enhanced reasoning with tools
14. **reflection.yaml** - Iterative self-improvement
15. **router.yaml** - Message routing to specialists
16. **sequential.yaml** - Ordered pipeline execution
17. **supervisor.yaml** - Execution oversight and coordination
18. **task.yaml** - Single-purpose focused execution

## Versioning

Specifications follow semantic versioning:
- **Major**: Breaking changes to pattern interface or behavior
- **Minor**: Backward-compatible additions
- **Patch**: Documentation clarifications

## Contributing

When modifying patterns:
1. Update the specification first
2. Update implementations across all languages
3. Run cross-language equivalence tests
4. Update this README if adding new patterns
