# Pattern Behavior Specifications

This directory contains structural specifications for all 18 Agenkit agent patterns.

## Two spec corpora, two different jobs

There are two YAML spec corpora in this repo, and they are **not** duplicates of each
other — each is authoritative for a different question, per #909/#913's design:

| | `specs/patterns/` (this directory) | `tests/cross_language/specs/` |
|---|---|---|
| Answers | "What is this pattern's interface — constructor params, methods?" | "Does this implementation *behave* like the spec says?" |
| Schema | `interface.constructor.parameters`, `interface.methods` | `test_scenarios` with `content_contains`/`content_pattern` fuzzy matchers |
| Tooling | `scripts/parity/spec_conformance.py` (structural, #909 rung 1) | `tests/cross_language/spec_loader.py`'s `SpecificationLoader` (a real parser/validator) |
| Scope | The 18 named patterns | The 18 patterns + 3 reasoning techniques (chain_of_thought, self_consistency, tree_of_thought) |

**This directory (`specs/patterns/`) is authoritative for interface/structural
conformance.** `tests/cross_language/specs/` is authoritative for behavioral scenario
execution. Neither supersedes the other, and merging their schemas was considered and
rejected — one is designed for fuzzy-matching LLM output across nine process harnesses,
the other is a human-authored contract document, and a merged schema would serve both
worse.

**Known naming divergence**: this directory's `memory_hierarchy.yaml` is named
`memory.yaml` in `tests/cross_language/specs/`. For every other of the 17 overlapping
pattern stems, `pattern.name` matches exactly between the two corpora (verified, and
enforced going forward by `tests/parity/test_spec_conformance.py`'s cross-corpus
consistency check).

## What is and isn't executable today

Every file has a `test_cases` section with prose `assertions`, but this is **not**
mechanically executable yet: fixture names referenced in `input`/`config.agents`
(`"uppercase_agent"`, `"echo_agent"`, etc.) exist in no language's registry, expectation
field names vary across files (`expected_output`/`expected_error`/`expected_behavior`/
`expected_trace`/...), and 8 of 18 files have no `input` field at all — pure prose
describing intended behavior. Treat `test_cases` as **documentation of intent**, not a
generator input, until a named-fixture registry and one consistent expectation schema
exist (tracked as future work; not yet filed as its own issue).

What **is** buildable and built today: structural conformance — does a source file
implementing pattern X exist per language (`scripts/parity/spec_conformance.py`, #909
rung 1) — and, as a planned next step, whether each language's constructor actually
matches `interface.constructor.parameters` (#924, rung 2, explicitly non-gating since it
will immediately flag drift in the reference implementation itself).

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

Not every file has every section filled in — 8 of 18 are "stub" files with only
`pattern`/`behavior`/`assertions` prose and no `interface`/`test_cases.input`. The 10
"detailed" files (`agents_as_tools`, `autonomous`, `collaborative`, `fallback`,
`human_in_loop`, `multiagent`, `orchestration`, `parallel`, `sequential`, `supervisor`,
roughly) carry the `interface` section that `spec_conformance.py` and the planned rung-2
checker actually read.

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

### Checking spec-presence conformance (what's built today)

```bash
uv run python scripts/parity/spec_conformance.py
cat spec-conformance.json
```

### For Cross-Language Behavioral Validation

The behavioral scenario runner lives with its own spec corpus, not this one:

```bash
python tests/cross_language/run_equivalence_tests.py --specs tests/cross_language/specs/*.yaml
```

(Currently reachable only via the disabled `.github/workflows/integration.yml.disabled`
— see that file's own header comment for why.)

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
3. If a language's constructor signature and this spec's `interface.constructor.parameters`
   disagree, fix the spec to match the real signature — specs describe what was built, not
   the reverse (see #924's rationale)
4. Update this README if adding new patterns
