# Testing Guide

## Running Tests

Agenkit has comprehensive test coverage for all LLM adapters with both unit tests (mocked) and integration tests (real APIs).

### Quick Start

```bash
# Run all tests (unit tests only, no API keys needed)
pytest tests/adapters/llm/ -m "not integration"

# Run all tests including integration tests (requires API keys)
pytest tests/adapters/llm/
```

## Test Types

### Unit Tests (Fast, No API Keys)
- Mocked API responses
- Test message conversion, configuration, etc.
- Run in < 1 second
- Great for development

```bash
pytest tests/adapters/llm/ -m "not integration"
```

### Integration Tests (Real APIs)
- Test with real Anthropic, OpenAI, Gemini, Bedrock, Ollama, LiteLLM APIs
- Require API keys
- Run in ~20 seconds
- Automatically skip if API keys not present

```bash
pytest tests/adapters/llm/ -m "integration"
```

## API Key Setup

### 1. Create `.env` file

```bash
cp .env.example .env
```

### 2. Add your API keys

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-...

# Gemini
GEMINI_API_KEY=...

# AWS (for Bedrock)
AWS_PROFILE=aws
# or
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1
```

### 3. Verify API keys

```bash
python test_api_keys.py
```

## Testing with Ollama

Ollama requires a running server. You can use Docker:

### Option 1: Docker Compose (Recommended)

```bash
# Start Ollama
docker-compose -f docker-compose.test.yml up -d

# Pull a model
docker exec agenkit-ollama-test ollama pull llama2

# Run Ollama tests
pytest tests/adapters/llm/test_ollama.py -v

# Stop Ollama
docker-compose -f docker-compose.test.yml down
```

### Option 2: Manual Docker

```bash
# Start Ollama container
docker run -d --name ollama-test -p 11434:11434 ollama/ollama

# Pull a model
docker exec ollama-test ollama pull llama2

# Run tests
pytest tests/adapters/llm/test_ollama.py -v

# Clean up
docker stop ollama-test && docker rm ollama-test
```

### Option 3: Brew Install

```bash
# Install Ollama
brew install ollama

# Start Ollama service
ollama serve &

# Pull a model
ollama pull llama2

# Run tests
pytest tests/adapters/llm/test_ollama.py -v
```

## Running Specific Tests

```bash
# Test specific adapter
pytest tests/adapters/llm/test_anthropic.py -v

# Test specific function
pytest tests/adapters/llm/test_anthropic.py::test_complete_success -v

# Test with output
pytest tests/adapters/llm/test_openai.py -v -s
```

## Test Coverage

To check test coverage:

```bash
pytest tests/adapters/llm/ --cov=agenkit/adapters/llm --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

Our CI pipeline runs:
1. All unit tests (fast)
2. Integration tests with encrypted API keys (for maintainers)
3. Docker-based Ollama tests

## Troubleshooting

### Tests are skipped

**Cause:** API keys not found or dependencies not installed

**Solution:**
```bash
# Check .env file exists
ls .env

# Install all LLM dependencies
pip install -e ".[llm]"

# Verify API keys load
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Anthropic:', bool(os.getenv('ANTHROPIC_API_KEY')))"
```

### Ollama tests fail

**Cause:** Ollama server not running

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/

# If not, start with Docker
docker-compose -f docker-compose.test.yml up -d
```

### Bedrock tests fail

**Cause:** AWS credentials not configured

**Solution:**
```bash
# Configure AWS CLI
aws configure --profile aws

# Or set environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
```

## Test Structure

```
tests/adapters/llm/
├── conftest.py              # Shared fixtures, mocks, API key loading
├── test_base.py             # LLM interface tests (5 tests)
├── test_anthropic.py        # Anthropic tests (10 tests: 7 unit + 3 integration)
├── test_openai.py           # OpenAI tests (8 tests: 6 unit + 2 integration)
├── test_gemini.py           # Gemini tests (7 tests: 5 unit + 2 integration)
├── test_bedrock.py          # Bedrock tests (8 tests: 6 unit + 2 integration)
├── test_ollama.py           # Ollama tests (7 tests: 5 unit + 2 integration)
└── test_litellm.py          # LiteLLM tests (8 tests: 6 unit + 2 integration)
```

**Total: 53 tests**
- 30 unit tests (mocked, fast)
- 23 integration tests (real APIs)

## Best Practices

1. **Always run unit tests first** - They're fast and catch most issues
2. **Use `.env` for API keys** - Never commit API keys to git
3. **Test with Docker for Ollama** - Consistent environment
4. **Run integration tests before PR** - Ensure real API compatibility
5. **Check coverage regularly** - Aim for >90% coverage

## Adding New Tests

When adding a new LLM adapter:

1. Create `tests/adapters/llm/test_<adapter>.py`
2. Add unit tests with mocks
3. Add integration tests marked with `@pytest.mark.integration`
4. Update fixtures in `conftest.py` if needed
5. Document API key setup in `.env.example`
6. Run full test suite to ensure compatibility
