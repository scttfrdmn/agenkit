# Cross-Language Pattern Specifications

This directory contains YAML specifications for all 18 agent patterns in Agenkit. These specifications define the expected behavior of each pattern to enable cross-language equivalence testing.

## Purpose

These specifications serve multiple purposes:

1. **Cross-Language Testing**: Validate that all 6 language implementations (Python, Go, TypeScript, Rust, C++, Zig) behave identically
2. **Behavioral Contracts**: Document the expected behavior of each pattern
3. **Test Generation**: Automatically generate test cases for each language
4. **Regression Detection**: Detect when implementations diverge from expected behavior
5. **Documentation**: Serve as reference documentation for pattern behavior

## Directory Structure

```
specs/
├── SCHEMA.md                      # Schema documentation
├── README.md                      # This file
├── reflection.yaml                # Reflection pattern spec
├── sequential.yaml                # Sequential orchestration spec
├── parallel.yaml                  # Parallel orchestration spec
├── router.yaml                    # Router pattern spec
├── react.yaml                     # ReAct (Reasoning + Acting) spec
├── conversational.yaml            # Conversational agent spec
├── agents_as_tools.yaml           # AgentsAsTools pattern spec
├── fallback.yaml                  # Fallback pattern spec
├── supervisor.yaml                # Supervisor pattern spec
├── planning.yaml                  # Planning pattern spec
├── task.yaml                      # Task execution pattern spec
├── collaborative.yaml             # Collaborative agents spec
├── human_in_loop.yaml             # HumanInLoop pattern spec
├── autonomous.yaml                # Autonomous agent spec
├── multiagent.yaml                # Multiagent system spec
├── orchestration.yaml             # Complex orchestration spec
├── memory.yaml                    # Memory hierarchy spec
└── reasoning_with_tools.yaml      # ReasoningWithTools spec
```

## Pattern Categories

Patterns are organized into 5 categories:

### 1. Reasoning Patterns
- **Reflection**: Iterative self-critique and improvement
- **ReAct**: Reasoning and acting in a loop
- **Planning**: Task decomposition and execution
- **ReasoningWithTools**: Advanced reasoning with tool integration

### 2. Orchestration Patterns
- **Sequential**: Linear agent chain
- **Parallel**: Concurrent agent execution
- **Router**: Message routing to specialists
- **AgentsAsTools**: Hierarchical delegation
- **Fallback**: Graceful degradation
- **Supervisor**: Worker management
- **Orchestration**: Complex workflow composition
- **Collaborative**: Shared goal collaboration
- **Multiagent**: Complex multi-agent systems

### 3. Communication Patterns
- **Conversational**: Multi-turn dialogue with memory
- **HumanInLoop**: Human approval and input

### 4. Memory Patterns
- **Memory**: Hierarchical memory with retention strategies

### 5. Specialized Patterns
- **Task**: Well-defined task execution
- **Autonomous**: Long-running with checkpointing

## Specification Format

Each YAML file contains:

```yaml
pattern:
  name: string              # Pattern name
  description: string       # Pattern purpose
  category: string          # Pattern category

test_scenarios:
  - id: string             # Unique test ID
    name: string           # Test name
    description: string    # What test validates
    input: object          # Test input
    expected_output: object  # Expected behavior

edge_cases:
  - condition: string      # Edge case
    expected: string       # Expected behavior

properties:
  deterministic: boolean   # Output determinism
  idempotent: boolean     # Result consistency
  stateful: boolean       # State maintenance
  requires_llm: boolean   # LLM requirement
  supports_streaming: boolean  # Streaming support

performance:
  complexity: string      # Algorithmic complexity
  expected_latency: string  # Typical latency

dependencies:
  patterns: [string]      # Pattern dependencies
  middleware: [string]    # Middleware dependencies
  external: [string]      # External dependencies
```

See [SCHEMA.md](SCHEMA.md) for complete schema documentation.

## Usage

### 1. Manual Review

Read specifications to understand expected pattern behavior:

```bash
cat tests/cross_language/specs/reflection.yaml
```

### 2. Test Generation

Use specifications to generate language-specific tests:

```python
# Python example
from agenkit.testing import SpecificationLoader

spec = SpecificationLoader.load("reflection")
for scenario in spec.test_scenarios:
    # Generate test case from scenario
    test = generate_test_from_scenario(scenario)
    run_test(test)
```

### 3. Cross-Language Validation

Run equivalence tests across all languages:

```bash
# Coming in issue #271 (test harness)
python tests/cross_language/run_equivalence_tests.py
```

### 4. CI Integration

Integrate into CI/CD pipeline:

```yaml
# .github/workflows/cross-language-tests.yml
- name: Cross-Language Equivalence Tests
  run: |
    python tests/cross_language/run_equivalence_tests.py
    if [ $? -ne 0 ]; then
      echo "Cross-language equivalence tests failed!"
      exit 1
    fi
```

## Test Scenario Structure

Each test scenario includes:

### Input

Defines the input message and configuration:

```yaml
input:
  message:
    role: "user"
    content: "Your request"
    metadata: {}
  config:
    max_iterations: 3
    # Pattern-specific config
```

### Expected Output

Defines expected behavior:

```yaml
expected_output:
  message:
    role: "assistant"
    content_contains: ["keyword"]  # Required substrings
    content_pattern: "regex"       # Regex match
    metadata:
      iterations: 2                # Expected metadata

  behavior:
    min_turns: 2                   # Minimum interactions
    tool_calls: ["tool_name"]      # Expected tool usage
```

### Edge Cases

Documents edge case behavior:

```yaml
edge_cases:
  - condition: "max_iterations = 0"
    expected: "Returns initial response without reflection"
  - condition: "Empty input"
    expected: "Raises validation error"
```

## Pattern Properties

Each specification documents intrinsic properties:

### Determinism

```yaml
properties:
  deterministic: false  # LLM-based, non-deterministic output
```

- **true**: Same input always produces same output
- **false**: Output may vary (typically LLM-based)

### Idempotence

```yaml
properties:
  idempotent: true  # Repeated execution doesn't change result
```

- **true**: Repeated calls produce same result
- **false**: Results may differ

### Statefulness

```yaml
properties:
  stateful: true  # Maintains state between calls
```

- **true**: Maintains state across invocations
- **false**: Stateless operation

### LLM Requirement

```yaml
properties:
  requires_llm: true  # Needs LLM API access
```

- **true**: Requires LLM provider
- **false**: Can operate without LLM

### Streaming Support

```yaml
properties:
  supports_streaming: true  # Can stream responses
```

- **true**: Supports streaming responses
- **false**: Returns complete results only

## Validation

Before using specifications, validate them:

```bash
# Validate all specs
python tests/cross_language/validate_specs.py

# Validate single spec
python tests/cross_language/validate_specs.py reflection.yaml
```

Validation checks:
- YAML syntax correctness
- Required fields present
- Regex patterns compile
- Test IDs are unique
- Referenced patterns exist

## Contributing

### Adding New Test Scenarios

1. Identify missing edge cases or behaviors
2. Add scenario to appropriate pattern spec
3. Follow existing scenario structure
4. Update this README if adding new patterns

### Modifying Existing Specs

1. Discuss changes in GitHub issue first
2. Ensure backwards compatibility
3. Update all affected language implementations
4. Run full cross-language test suite

### Pattern-Specific Notes

#### Reflection Pattern
- Tests self-critique iteration
- Validates improvement over iterations
- Checks convergence behavior

#### Sequential Pattern
- Tests agent chaining
- Validates message propagation
- Checks metadata preservation

#### Parallel Pattern
- Tests concurrent execution
- Validates result aggregation
- Checks partial failure handling

#### Router Pattern
- Tests routing logic
- Validates keyword matching
- Checks classification-based routing

#### ReAct Pattern
- Tests reasoning loop
- Validates tool integration
- Checks thought-action-observation cycles

...and so on for all 18 patterns.

## Cross-Language Test Harness

The test harness (issue #271) will:

1. **Load Specifications**: Read YAML specs
2. **Generate Tests**: Create language-specific test cases
3. **Execute Tests**: Run tests across all 6 languages
4. **Compare Results**: Validate behavioral equivalence
5. **Generate Reports**: Document any divergence

### Equivalence Criteria

Two implementations are equivalent if:

1. **Output Structure**: Same message structure
2. **Content Match**: Content matches pattern/contains rules
3. **Metadata Consistency**: Required metadata present
4. **Behavior Compliance**: Behavioral properties match
5. **Edge Cases**: Same edge case handling

### Tolerance

Some variance is acceptable:

- **LLM Output**: Exact content may differ (use patterns/contains)
- **Timestamps**: Expect different values
- **Floating Point**: Allow small numerical differences
- **Ordering**: Unordered collections may differ

## Roadmap

### v0.42.0 (Feb 2026)
- ✅ Pattern specifications complete (this directory)
- 🚧 Test harness implementation (issue #271)
- 🚧 Cross-language equivalence tests (issue #272)

### Future Enhancements
- Interactive specification validator
- Visual specification editor
- Automated test case generation
- Performance benchmarking integration
- Specification versioning

## References

- **Schema Documentation**: [SCHEMA.md](SCHEMA.md)
- **Issue #270**: Create pattern behavior specifications
- **Issue #271**: Build test harness
- **Issue #272**: Run equivalence tests
- **ROADMAP.md**: v0.42.0 Testing & Documentation milestone

---

**Created**: December 13, 2025
**Version**: 1.0
**Patterns**: 18/18 specified
**Languages**: Python, Go, TypeScript, Rust, C++, Zig
