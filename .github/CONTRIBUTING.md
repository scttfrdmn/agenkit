# Contributing to Agenkit

Hi! Thanks for your interest in contributing to Agenkit. We're excited to have you here.

Agenkit is a cross-language agent framework (Python + Go) with a focus on minimal abstractions, production readiness, and cross-language interoperability. This guide will help you contribute effectively.

---

## Table of Contents

- [Please do](#please-do)
- [Please do not](#please-do-not)
- [Building the project](#building-the-project)
- [Testing](#testing)
- [Submitting a pull request](#submitting-a-pull-request)
- [Design guidelines](#design-guidelines)
- [Resources](#resources)

---

## Please do

✅ **Open an issue first** for any significant changes or new features. This lets us discuss the approach before you invest time coding.

✅ **Check for existing issues** before creating a new one. Use GitHub's search to avoid duplicates.

✅ **Look for issues labeled**:
- `help wanted` - Community contributions welcome
- `good first issue` - Great for newcomers
- `python` or `go` - Language-specific contributions

✅ **Follow the acceptance criteria** in the issue. If they're unclear, mention `@agenkit/maintainers` to get clarification.

✅ **Write tests** for both Python and Go if you're changing cross-language functionality.

✅ **Update documentation** when adding features or changing behavior.

✅ **Keep pull requests focused**. One issue = one PR. This makes review faster and easier.

---

## Please do not

❌ **Do not open pull requests for issues labeled `core`**. These require additional context from the Agenkit team and are reserved for maintainers.

❌ **Do not expand the scope** of your pull request beyond what the issue describes. If you want to add more, open a separate issue and PR.

❌ **Do not submit PRs without an issue**. Create an issue first so we can discuss the approach.

❌ **Do not skip tests**. All changes must have test coverage in both Python and Go (if applicable).

❌ **Do not modify the API** without extensive discussion. Breaking changes require careful planning.

---

## Building the project

Agenkit has both Python and Go implementations. You'll need to set up both if you're working on cross-language features.

### Python Setup

**Requirements:** Python 3.10+

```bash
# Clone the repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Go Setup

**Requirements:** Go 1.25.12+

```bash
cd agenkit-go

# Download dependencies
go mod download

# Build
go build ./...

# Run tests
go test ./...
```

### Development Tools

**Python:**
- `pytest` - Testing framework
- `ruff` - Linter (fast, replacing flake8/black)
- `mypy` - Type checking
- `pytest-cov` - Coverage reporting

**Go:**
- `go test` - Built-in testing
- `go vet` - Static analysis
- `golangci-lint` - Comprehensive linting

---

## Testing

Agenkit has comprehensive test coverage across both languages. All contributions must maintain or improve test coverage.

### Running Tests

**Python:**
```bash
# All tests
pytest tests/

# Specific module
pytest tests/middleware/

# With coverage
pytest tests/ --cov=agenkit --cov-report=html

# Skip integration tests (faster)
pytest tests/ -m "not integration"
```

**Go:**
```bash
# All tests
go test ./...

# Specific package
go test ./middleware

# With coverage
go test ./... -cover

# Verbose output
go test ./... -v
```

### Cross-Language Integration Tests

For changes affecting both Python and Go:

```bash
# Start Python test server
cd tests/integration
python test_server.py &

# Run Go integration tests
cd agenkit-go/tests/integration
go test -v

# Or use test scripts
./scripts/test-cross-language.sh
```

### Test Requirements

✅ **Unit tests** for all new code (target: 90%+ coverage)

✅ **Integration tests** for cross-language features

✅ **Both languages** for transport/middleware changes

✅ **Documentation** for public APIs

### Writing Good Tests

```python
# Python example
def test_retry_decorator_with_failure():
    """Test retry decorator handles transient failures."""
    agent = FailingAgent(fail_count=2)  # Fails twice, then succeeds
    decorated = RetryDecorator(agent, max_attempts=3)

    result = await decorated.call([Message(...)])

    assert result.content == "success"
    assert agent.call_count == 3  # Called 3 times total
```

```go
// Go example
func TestRetryDecoratorWithFailure(t *testing.T) {
    // Test retry decorator handles transient failures
    agent := NewFailingAgent(2) // Fails twice, then succeeds
    decorated := middleware.NewRetryDecorator(agent, 3)

    result, err := decorated.Call(ctx, messages)

    assert.NoError(t, err)
    assert.Equal(t, "success", result.Content)
    assert.Equal(t, 3, agent.CallCount) // Called 3 times total
}
```

---

## Submitting a pull request

1. **Create a new branch** from `main`:
   ```bash
   git checkout -b my-feature-branch
   ```

2. **Make your changes** following our coding standards

3. **Add tests** for your changes

4. **Run the test suite** to ensure everything passes:
   ```bash
   # Python
   pytest tests/

   # Go
   go test ./...
   ```

5. **Run linters**:
   ```bash
   # Python
   ruff check .
   mypy agenkit/

   # Go
   golangci-lint run
   ```

6. **Commit your changes** with a clear message:
   ```bash
   git commit -m "feat(middleware): Add rate limiter middleware

   - Implements token bucket algorithm
   - Configurable rate and burst capacity
   - Thread-safe with asyncio.Lock
   - Tests for both Python and Go

   Closes #123"
   ```

   **Commit message format:**
   ```
   <type>(<scope>): <subject>

   <body>

   <footer>
   ```

   **Types:** feat, fix, docs, test, refactor, perf, chore

   **Scopes:** middleware, transport, observability, patterns, etc.

7. **Push to your fork**:
   ```bash
   git push origin my-feature-branch
   ```

8. **Open a pull request** on GitHub:
   - Reference the issue number
   - Describe what you changed and why
   - Add screenshots/examples if relevant
   - Check all boxes in the PR template

9. **Respond to review feedback** promptly

10. **Celebrate!** 🎉 Once merged, you're an Agenkit contributor!

---

## Design guidelines

### Python

**1. Type Hints**

Always include type hints:
```python
async def call(
    self,
    messages: list[Message],
    timeout: float | None = None,
    **kwargs: Any
) -> Message:
    """Call agent with messages."""
```

**2. Docstrings**

Use Google style docstrings:
```python
def create_agent(config: dict) -> Agent:
    """Create agent from configuration.

    Args:
        config: Configuration dictionary with keys:
            - model: LLM model name
            - tools: List of available tools
            - memory: Memory configuration

    Returns:
        Configured agent instance.

    Raises:
        ValueError: If configuration is invalid.
    """
```

**3. Async/Await**

All I/O operations must be async:
```python
# Good
async def call_llm(prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"prompt": prompt}) as resp:
            return await resp.text()

# Bad - blocks event loop!
def call_llm(prompt: str) -> str:
    response = requests.post(url, json={"prompt": prompt})
    return response.text
```

**4. Error Handling**

Be explicit about what can fail:
```python
try:
    result = await agent.call(messages)
except TimeoutError:
    logger.error("Agent call timed out")
    raise
except APIError as e:
    logger.error(f"LLM API error: {e}")
    return default_response
```

### Go

**1. Error Handling**

Always check errors explicitly:
```go
// Good
result, err := agent.Call(ctx, messages)
if err != nil {
    return nil, fmt.Errorf("agent call failed: %w", err)
}

// Bad
result, _ := agent.Call(ctx, messages)
```

**2. Context**

Pass context everywhere:
```go
func (a *Agent) Call(ctx context.Context, messages []Message) (*Message, error) {
    // Use ctx for cancellation, timeouts, values
    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    default:
        // Continue processing
    }
}
```

**3. Interfaces**

Keep interfaces small:
```go
// Good - single method
type Agent interface {
    Call(ctx context.Context, messages []Message) (*Message, error)
}

// Bad - too many methods
type Agent interface {
    Call(ctx context.Context, messages []Message) (*Message, error)
    GetConfig() Config
    SetConfig(Config) error
    Reset() error
    // ...10 more methods
}
```

**4. Documentation**

Add comments for exported symbols:
```go
// Agent represents an AI agent that can process messages.
type Agent interface {
    // Call processes messages and returns a response.
    // The context can be used for cancellation and timeouts.
    Call(ctx context.Context, messages []Message) (*Message, error)
}
```

### Cross-Language Considerations

**1. Protocol Compatibility**

Changes to proto definitions must be backward compatible:
```protobuf
// Good - adding optional field
message AgentRequest {
    repeated Message messages = 1;
    optional int32 timeout = 2;  // New field
}

// Bad - changing field type (breaks compatibility)
message AgentRequest {
    repeated Message messages = 1;
    string timeout = 2;  // Was int32!
}
```

**2. Feature Parity**

Features should work the same in both languages:
```python
# Python
agent = RetryDecorator(agent, max_attempts=3, backoff=2.0)
```

```go
// Go - same behavior
agent = middleware.NewRetryDecorator(agent, 3, 2.0)
```

**3. Test Coverage**

Cross-language features need tests in both:
- Python → Go communication
- Go → Python communication
- Error handling in both directions

---

## Resources

### Documentation

- [README](../README.md) - Project overview
- [Agent Patterns Guide](../docs-site/guides/agent-patterns.md) - Comprehensive agent patterns
- [Architecture](../docs-site/core-concepts/architecture.md) - System design
- [Testing Guide](../TESTING.md) - Running tests

### Getting Help

- **Questions?** Open a [GitHub Discussion](https://github.com/scttfrdmn/agenkit/discussions)
- **Bugs?** Open an [issue](https://github.com/scttfrdmn/agenkit/issues/new?template=bug_report.md)
- **Feature ideas?** Open an [issue](https://github.com/scttfrdmn/agenkit/issues/new?template=feature_request.md)
- **Chat?** Join our [Discord](https://discord.gg/agenkit) *(coming soon)*

### Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

### License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Thank you! 🙏

Every contribution, no matter how small, makes Agenkit better. We appreciate your time and effort.

Happy coding!

— The Agenkit Team
