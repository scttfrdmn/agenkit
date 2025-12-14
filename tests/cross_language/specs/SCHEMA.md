# Cross-Language Pattern Specification Schema

## Overview

This schema defines the format for pattern behavior specifications used in cross-language equivalence testing. Each pattern has a YAML specification that describes its expected behavior across all language implementations.

## Schema Structure

```yaml
pattern:
  name: string              # Pattern name (e.g., "Reflection", "ReAct")
  description: string       # Brief description of pattern purpose
  category: string          # Pattern category (e.g., "reasoning", "orchestration", "communication")

test_scenarios:
  - id: string             # Unique test scenario identifier
    name: string           # Human-readable test name
    description: string    # What this test validates

    input:
      message:
        role: string       # Message role: "user", "assistant", "system"
        content: string    # Message content
        metadata: object   # Optional metadata (key-value pairs)

      config: object       # Pattern-specific configuration

    expected_output:
      message:
        role: string       # Expected output role
        content_pattern: string  # Regex pattern for content matching
        content_contains: [string]  # Strings that must appear in output
        content_not_contains: [string]  # Strings that must NOT appear
        metadata: object   # Expected metadata

      behavior:
        min_turns: int     # Minimum interaction turns (for iterative patterns)
        max_turns: int     # Maximum interaction turns
        tool_calls: [string]  # Expected tool calls (for tool-using patterns)
        sub_agents: [string]  # Expected sub-agent invocations

    edge_cases:
      - condition: string  # Edge case condition
        expected: string   # Expected behavior

properties:
  deterministic: boolean   # Whether output is deterministic
  idempotent: boolean     # Whether repeated calls produce same result
  stateful: boolean       # Whether pattern maintains state
  requires_llm: boolean   # Whether pattern requires LLM calls
  supports_streaming: boolean  # Whether pattern supports streaming

performance:
  complexity: string      # Time complexity (O notation)
  expected_latency: string  # Expected latency range

dependencies:
  patterns: [string]      # Other patterns this depends on
  middleware: [string]    # Required middleware
  external: [string]      # External dependencies (LLM providers, etc.)
```

## Field Descriptions

### Pattern Metadata

- **name**: The canonical pattern name matching implementation
- **description**: 1-2 sentence description of pattern purpose
- **category**: One of: `reasoning`, `orchestration`, `communication`, `memory`, `specialized`

### Test Scenarios

Each test scenario represents a specific behavior to validate across languages.

#### Input

- **message**: The input message to the pattern
  - **role**: "user", "assistant", or "system"
  - **content**: The actual message content
  - **metadata**: Optional key-value metadata
- **config**: Pattern-specific configuration (e.g., max_iterations, temperature)

#### Expected Output

- **message**: Expected output structure
  - **role**: Expected message role
  - **content_pattern**: Regex for flexible matching
  - **content_contains**: Required substrings
  - **content_not_contains**: Forbidden substrings
  - **metadata**: Expected metadata fields
- **behavior**: Expected behavioral characteristics
  - **min_turns/max_turns**: For iterative patterns
  - **tool_calls**: For tool-using patterns (ReAct, ReasoningWithTools)
  - **sub_agents**: For orchestration patterns

### Properties

Describe intrinsic pattern properties:

- **deterministic**: Same input → same output (always)
- **idempotent**: Repeated execution doesn't change result
- **stateful**: Maintains state across invocations
- **requires_llm**: Needs LLM API access
- **supports_streaming**: Can stream responses

### Performance

- **complexity**: Algorithmic complexity (O(n), O(n²), etc.)
- **expected_latency**: Typical latency range

### Dependencies

- **patterns**: Other patterns required (e.g., Sequential needs base agents)
- **middleware**: Required middleware (e.g., timeout, retry)
- **external**: External services (OpenAI, Anthropic, databases)

## Example Specification

```yaml
pattern:
  name: "Reflection"
  description: "Agent that iteratively critiques and improves its own outputs through self-reflection"
  category: "reasoning"

test_scenarios:
  - id: "reflection_basic"
    name: "Basic reflection with improvement"
    description: "Agent should iterate and show improvement over initial response"

    input:
      message:
        role: "user"
        content: "Write a haiku about AI"
        metadata: {}
      config:
        max_iterations: 3
        improvement_threshold: 0.1

    expected_output:
      message:
        role: "assistant"
        content_contains:
          - "haiku"
        content_pattern: ".*\\n.*\\n.*"  # 3 lines (haiku structure)
        metadata:
          iterations: { min: 1, max: 3 }
          improved: true

      behavior:
        min_turns: 2  # Initial + at least one reflection
        max_turns: 6  # Max iterations * 2 (response + critique)

  - id: "reflection_convergence"
    name: "Early convergence when satisfied"
    description: "Should stop iterating when improvement threshold not met"

    input:
      message:
        role: "user"
        content: "Say hello"
        metadata: {}
      config:
        max_iterations: 5
        improvement_threshold: 0.5

    expected_output:
      behavior:
        max_turns: 4  # Should converge early on simple task

properties:
  deterministic: false  # LLM-based, non-deterministic
  idempotent: false    # Different reflection paths each time
  stateful: true       # Maintains iteration history
  requires_llm: true   # Needs LLM for critique and improvement
  supports_streaming: true

performance:
  complexity: "O(n)"    # Linear in max_iterations
  expected_latency: "2-10s"  # Multiple LLM calls

dependencies:
  patterns: []
  middleware: ["retry", "timeout"]
  external: ["llm_provider"]
```

## Usage

1. **Test Harness**: Reads YAML specs and generates test cases
2. **Language Implementations**: Each language reads specs and validates behavior
3. **CI Integration**: Automated cross-language equivalence testing
4. **Documentation**: Specifications serve as behavioral contracts

## Validation

Specifications should be validated for:

- YAML syntax correctness
- All required fields present
- Regex patterns compile
- Test IDs are unique
- Referenced patterns/dependencies exist

## Version

Schema Version: 1.0
Last Updated: December 13, 2025
