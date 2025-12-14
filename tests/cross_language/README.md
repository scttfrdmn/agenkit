# Cross-Language Equivalence Testing

This directory contains the cross-language equivalence testing infrastructure for Agenkit. It validates that all 6 language implementations (Python, Go, TypeScript, Rust, C++, Zig) behave identically across all 18 patterns.

## Overview

The testing infrastructure consists of:

1. **Pattern Specifications** (`specs/`) - YAML definitions of expected behavior
2. **Test Runner** (`run_equivalence_tests.py`) - Python orchestrator
3. **Language Harnesses** - Executables implementing the JSON protocol for each language
4. **Result Comparator** - Validates behavioral equivalence
5. **Reporting System** - Generates equivalence reports

## Architecture

```
┌─────────────────────────────────────────┐
│  run_equivalence_tests.py              │
│  (Python Test Runner)                   │
└─────────┬─────────────────────┬─────────┘
          │                     │
          │  JSON Protocol      │
          │  (stdin/stdout)     │
          │                     │
    ┌─────▼─────┐         ┌────▼─────┐
    │  Python   │         │    Go    │  ... (6 languages)
    │  Harness  │         │  Harness │
    └───────────┘         └──────────┘
          │                     │
          ▼                     ▼
    ┌───────────────────────────────┐
    │  Pattern Implementations      │
    │  (18 patterns × 6 languages)  │
    └───────────────────────────────┘
```

## Quick Start

### 1. Build Harnesses

Build the language-specific harness executables:

```bash
# Python (no build needed, interpreted)
chmod +x tests/cross_language/harness_python.py

# Go
cd agenkit-go/tests
go build -o cross_language_harness harness.go

# TypeScript
cd packages/core/tests
npm run build:harness

# Rust
cd agenkit-rust
cargo build --release --bin test_harness

# C++
cd agenkit-cpp
mkdir -p build && cd build
cmake .. && make test_harness

# Zig
cd agenkit-zig
zig build test_harness
```

### 2. Run Tests

Run all equivalence tests:

```bash
python tests/cross_language/run_equivalence_tests.py
```

Run specific patterns:

```bash
python tests/cross_language/run_equivalence_tests.py --patterns reflection sequential
```

Run specific languages:

```bash
python tests/cross_language/run_equivalence_tests.py --languages python go rust
```

### 3. View Report

Test report is saved to `equivalence_report.json`:

```bash
cat equivalence_report.json | jq '.summary'
```

## Components

### Specification Loader (`spec_loader.py`)

Loads and validates YAML pattern specifications.

```python
from spec_loader import SpecificationLoader

loader = SpecificationLoader("specs/")
spec = loader.load_spec("reflection")

# Validate spec
errors = loader.validate_spec(spec)
if errors:
    print("Validation errors:", errors)
```

### Harness Manager (`harness_manager.py`)

Manages communication with language harnesses via JSON protocol.

```python
from harness_manager import HarnessManager, HarnessConfig, TestRequest

# Configure harnesses
configs = [
    HarnessConfig(language="python", executable_path=Path("harness_python.py")),
    HarnessConfig(language="go", executable_path=Path("agenkit-go/tests/cross_language_harness")),
]

manager = HarnessManager(configs)

# Execute test
request = TestRequest(
    pattern="reflection",
    scenario_id="reflection_basic",
    input_data={"message": {...}, "config": {...}}
)

result = manager.execute_test("python", request)
print(result.status, result.output)
```

### Result Comparator (`result_comparator.py`)

Compares and validates test results.

```python
from result_comparator import ResultComparator

comparator = ResultComparator()

# Validate output against expected
validation = comparator.validate_output(actual_output, expected_output)
if not validation.valid:
    print("Validation errors:", validation.errors)

# Compare outputs from two languages
comparison = comparator.compare_outputs(
    python_output, go_output, "python", "go"
)
if not comparison.equivalent:
    print("Differences:", comparison.differences)
```

### Test Runner (`run_equivalence_tests.py`)

Main orchestrator that runs all tests.

```python
from run_equivalence_tests import EquivalenceTestRunner

runner = EquivalenceTestRunner(
    specs_dir=Path("specs/"),
    harness_configs=configs,
    languages=["python", "go"]
)

# Run all tests
results = runner.run_all_tests()

# Generate report
runner.generate_report(results, Path("report.json"))
```

## JSON Protocol

See [PROTOCOL.md](PROTOCOL.md) for complete protocol documentation.

### Request Format

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid",
  "command": "execute_test",
  "payload": {
    "pattern": "reflection",
    "scenario_id": "reflection_basic",
    "input": {
      "message": {"role": "user", "content": "..."},
      "config": {"max_iterations": 3}
    }
  }
}
```

### Response Format

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid",
  "status": "success",
  "result": {
    "output": {
      "message": {"role": "assistant", "content": "..."},
      "behavior": {"turns": 4, "tool_calls": []}
    },
    "execution_info": {"duration_ms": 1250}
  },
  "error": null
}
```

## Implementing a Language Harness

Each language must implement a harness executable that:

1. Reads JSON request from stdin
2. Executes the test using language-specific pattern implementations
3. Writes JSON response to stdout
4. Exits with appropriate exit code

### Exit Codes

- **0**: Success (valid JSON response)
- **1**: Error (error JSON response)
- **2**: Invalid protocol
- **3**: Timeout
- **4**: Internal error

### Example Harness (Python)

See [harness_python.py](harness_python.py) for reference implementation.

### Creating a New Harness

1. **Implement Protocol Handler**: Parse JSON requests, dispatch commands
2. **Implement Pattern Execution**: Execute patterns with configuration
3. **Implement Response Serialization**: Convert results to JSON
4. **Add Error Handling**: Catch and report errors
5. **Test Harness**: Run `health_check` and `get_info` commands

```bash
# Test harness
echo '{"protocol_version":"1.0","request_id":"test","command":"health_check","payload":{}}' | ./your_harness
```

## Pattern Specifications

See [specs/README.md](specs/README.md) for specification format.

Each pattern has:
- Test scenarios with input/output
- Expected behavioral characteristics
- Edge cases
- Pattern properties (determinism, statefulness, etc.)

## Equivalence Criteria

Two implementations are equivalent if:

1. **Same Status**: Both succeed or fail with same error type
2. **Content Match**: Output content matches patterns/contains rules
3. **Metadata Consistency**: Required metadata fields present and match
4. **Behavior Match**: Behavioral characteristics align (turns, tool calls, etc.)
5. **Edge Cases**: Same edge case handling

### Tolerance Configuration

Some variance is acceptable:

```python
tolerance = {
    "float_epsilon": 1e-6,        # Floating point comparison
    "timestamp_ignore": True,     # Ignore timestamp differences
    "llm_content_exact": False,   # Don't require exact LLM output
    "metadata_strict": False,     # Allow extra metadata fields
}
```

## CI Integration

Add to GitHub Actions workflow:

```yaml
name: Cross-Language Equivalence Tests

on: [push, pull_request]

jobs:
  equivalence-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      # Set up other languages...

      - name: Build Harnesses
        run: |
          # Build all harnesses
          make build-harnesses

      - name: Run Equivalence Tests
        run: |
          python tests/cross_language/run_equivalence_tests.py

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: equivalence-report
          path: equivalence_report.json
```

## Troubleshooting

### Harness Not Found

```
ERROR: No harnesses found!
```

Solution: Build the harness executables first (see Quick Start).

### Protocol Version Mismatch

```
ERROR: Protocol version mismatch
```

Solution: Update harness to use protocol version 1.0.

### Pattern Not Implemented

```
status: "not_implemented"
```

Solution: Implement the pattern in the harness's language implementation.

### Validation Errors

```
ERROR: Content missing required substring
```

Solution: Check pattern implementation - output doesn't match specification.

## Development

### Adding New Test Scenarios

1. Edit pattern specification in `specs/{pattern}.yaml`
2. Add new scenario with id, input, expected output
3. Run tests to validate

### Updating Protocol

1. Update `PROTOCOL.md` with changes
2. Increment protocol version (major for breaking changes)
3. Update all harnesses to support new version
4. Update `harness_manager.py` protocol version

### Running Single Language

```bash
# Test only Python implementation
python tests/cross_language/run_equivalence_tests.py --languages python
```

### Debugging Harness

```bash
# Send test request manually
echo '{"protocol_version":"1.0","request_id":"debug","command":"get_info","payload":{}}' | \
  ./harness_python.py | jq
```

## Performance

### Parallel Execution

Tests can run in parallel across languages:

```python
# Execute test on all languages in parallel
results = manager.execute_test_parallel(["python", "go", "rust"], request)
```

### Timeouts

Default timeout: 60 seconds per test
Configure per-pattern or per-language:

```python
config = HarnessConfig(
    language="rust",
    executable_path=...,
    timeout=120  # 2 minutes for slow patterns
)
```

## Roadmap

### v0.42.0 (Current)
- ✅ Pattern specifications (#270)
- 🚧 Test harness infrastructure (#271 - THIS ISSUE)
- ⏳ Execute equivalence tests (#272)

### Future Enhancements
- Parallel harness execution (multiprocessing)
- Streaming test support
- Performance benchmarking integration
- Interactive debugging mode
- Web-based report viewer

## References

- **Issue #270**: Pattern behavior specifications
- **Issue #271**: Test harness implementation (this)
- **Issue #272**: Run equivalence tests
- **PROTOCOL.md**: JSON protocol specification
- **specs/SCHEMA.md**: Specification schema

---

**Created**: December 13, 2025
**Status**: In Development
**Protocol Version**: 1.0
**Patterns**: 18
**Languages**: 6 (Python, Go, TypeScript, Rust, C++, Zig)
