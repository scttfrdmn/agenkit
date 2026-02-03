# Testing Guide

This document explains how to run the Agenkit test suite and work with different test categories.

## Quick Start

```bash
# Run all unit tests (default - excludes integration tests)
make test

# Run quick smoke tests
make test-quick

# Format code and run tests
make pre-commit
```

## Test Categories

Agenkit uses pytest markers to organize tests into categories:

| Marker | Description | Requirements |
|--------|-------------|--------------|
| `integration` | Integration tests requiring external services | Go servers, infrastructure setup |
| `cross_language` | Cross-language integration tests (Python ↔ Go) | Go runtime, compiled servers |
| `llm_api` | Tests requiring LLM API keys | API keys (OPENAI_API_KEY, GEMINI_API_KEY, etc.) |
| `slow` | Slow-running tests | Extra time |
| `chaos` | Chaos engineering tests | Special setup |
| `property` | Property-based tests with Hypothesis | - |
| `flaky` | Tests that may be flaky due to timing | Auto-retry enabled |

## Running Specific Test Categories

### Unit Tests Only (Default)

```bash
# Excludes integration, llm_api, and cross_language tests
pytest tests/
```

### Include Integration Tests

```bash
# Run integration tests (requires external services)
pytest tests/ -m "integration"

# Run all tests including integration
pytest tests/ -m ""
```

### Exclude Specific Categories

```bash
# Exclude LLM API tests
pytest tests/ -m "not llm_api"

# Exclude both integration and LLM API tests
pytest tests/ -m "not integration and not llm_api"

# Exclude slow tests
pytest tests/ -m "not slow"
```

### Run Only Specific Categories

```bash
# Only integration tests
pytest tests/ -m "integration"

# Only cross-language tests
pytest tests/ -m "cross_language"

# Only LLM API tests (requires API keys)
pytest tests/ -m "llm_api"
```

## LLM API Integration Tests

LLM integration tests require API keys. Tests are automatically skipped if keys are not present.

### Required Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY=your-key-here

# Gemini (Google)
export GEMINI_API_KEY=your-key-here
# OR
export GOOGLE_API_KEY=your-key-here

# Anthropic Claude
export ANTHROPIC_API_KEY=your-key-here

# AWS Bedrock
export AWS_PROFILE=your-profile
# OR
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Ollama (local)
# Ensure Ollama is running on localhost:11434
ollama serve
```

### Running LLM Tests

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Run LLM API tests
pytest tests/adapters/llm/ -m "llm_api" -v

# Run all LLM tests (unit + integration)
pytest tests/adapters/llm/
```

Tests will automatically skip if API keys are not set:
```
tests/adapters/llm/test_openai.py::test_openai_integration SKIPPED (OPENAI_API_KEY not set)
```

## Cross-Language Integration Tests

Cross-language tests verify Python ↔ Go communication. Requires Go runtime and compiled servers.

### Setup

```bash
# Build Go test servers (if needed)
cd agenkit-go
go build -o bin/http-server ./cmd/http-server
go build -o bin/grpc-server ./cmd/grpc-server
```

### Running

```bash
# Run cross-language tests
pytest tests/integration/ -m "cross_language" -v

# Run all integration tests
pytest tests/integration/ -v
```

## Test Performance

### Parallel Execution

Tests run in parallel by default using `pytest-xdist`:

```bash
# Auto-detect CPU count
pytest tests/  # Uses -n auto

# Specify worker count
pytest tests/ -n 4

# Disable parallel execution
pytest tests/ -n 0
```

### Timeout

Tests have a 30-second timeout by default (configured via `pytest-timeout`):

```bash
# Increase timeout for slow tests
pytest tests/ --timeout=60

# Disable timeout
pytest tests/ --timeout=0
```

## Debugging

### Verbose Output

```bash
# Show test names and results
pytest tests/ -v

# Show more details
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show slowest tests
pytest tests/ --durations=10
```

### Run Specific Tests

```bash
# Run a specific test file
pytest tests/adapters/llm/test_openai.py

# Run a specific test
pytest tests/adapters/llm/test_openai.py::test_complete_success

# Run tests matching a pattern
pytest tests/ -k "test_openai"
```

### Debug on Failure

```bash
# Drop into debugger on failure
pytest tests/ --pdb

# Drop into debugger on first failure
pytest tests/ -x --pdb

# Show local variables on failure
pytest tests/ -l
```

## CI/CD Considerations

### Fast Local Development

```bash
# Default: unit tests only (~2-3 minutes)
make test

# Quick smoke tests (~10 seconds)
make test-quick
```

### Full Validation

```bash
# Format + lint + test
make test-lint

# Cross-language parity checks
./scripts/test-parity.sh
```

### Coverage

```bash
# Generate coverage report
pytest tests/ --cov=agenkit --cov-report=html

# View report
open htmlcov/index.html
```

## Troubleshooting

### Tests Failing Due to Missing Dependencies

**Symptom**: Tests fail with import errors or skip messages

**Solution**:
```bash
# Install all optional dependencies
uv pip install -e ".[all]"

# Or install specific groups
uv pip install -e ".[llm]"  # LLM adapters
uv pip install -e ".[test]"  # Test dependencies
```

### Cross-Language Tests Failing

**Symptom**: Tests fail with connection errors or "Go server not running"

**Solution**:
1. Check Go is installed: `go version`
2. Build Go test servers (see "Cross-Language Integration Tests" above)
3. Check ports are not in use: `lsof -i :8080`

### LLM Tests Failing with API Errors

**Symptom**: "RateLimitError", "AuthenticationError", or quota exceeded

**Solution**:
1. Verify API key is set: `echo $OPENAI_API_KEY`
2. Check API quota/billing at provider's dashboard
3. Use different model (e.g., `gpt-4o-mini` instead of `gpt-4`)
4. Skip LLM tests: `pytest tests/ -m "not llm_api"`

### Tests Hanging or Timing Out

**Symptom**: Tests exceed 30-second timeout

**Solution**:
1. Increase timeout: `pytest tests/ --timeout=60`
2. Check for deadlocks in async code
3. Disable parallel execution: `pytest tests/ -n 0`
4. Check external services are responding

## Best Practices

### For Contributors

1. **Run tests before committing**:
   ```bash
   make pre-commit
   ```

2. **Add markers to new tests**:
   ```python
   @pytest.mark.integration  # If requires external services
   @pytest.mark.llm_api  # If requires API keys
   @pytest.mark.slow  # If takes >5 seconds
   ```

3. **Use fixtures for API keys**:
   ```python
   async def test_my_integration(openai_api_key, simple_test_message):
       # Test automatically skips if API key not present
       llm = OpenAILLM(api_key=openai_api_key)
       ...
   ```

4. **Mock external services in unit tests**:
   ```python
   async def test_complete(mock_openai_client):
       llm = OpenAILLM(api_key="test-key")
       llm._client = mock_openai_client
       ...
   ```

### For Local Development

- **Fast feedback**: Use `make test-quick` during development
- **Pre-commit validation**: Use `make pre-commit` before committing
- **Skip integration tests**: Tests skip automatically without external services
- **Use markers**: Run only relevant tests with `-m` flag

### For CI/CD

- **Separate stages**: Run unit tests (fast) and integration tests (slow) separately
- **Conditional execution**: Run LLM tests only when API keys are available
- **Parallel execution**: Leverage `-n auto` for faster execution
- **Fail fast**: Use `-x` flag to stop on first failure

## See Also

- [Contributing Guide](../.github/CONTRIBUTING.md)
- [Development Setup](../README.md#development)
- [CI/CD Configuration](../.github/workflows/)
