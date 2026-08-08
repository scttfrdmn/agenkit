# Contributing to Agenkit

Hi! Thanks for your interest in contributing to Agenkit. We're excited to have you here.

Agenkit is a cross-language toolkit for building agent frameworks and runtimes (Python, Go, TypeScript, Rust, C++, Zig, C#, Java, and Scala) with a focus on minimal abstractions, production readiness, and cross-language interoperability. This guide will help you contribute effectively.

Most contributions fall into one of three shapes, and each has a different setup:

- **Working in one language port** — fixing a bug or adding a feature inside `agenkit/` (Python) or one `agenkit-<lang>/` directory. Set up only that language; see [Working in a single language](#working-in-a-single-language) below.
- **Changing a cross-language spec or contract** — a pattern definition, wire protocol, or anything that all 9 ports must implement identically. See [Cross-language specification changes](#cross-language-specification-changes).
- **Adding or extending a whole language port** — see [Adding to an existing language port](#adding-to-an-existing-language-port).

---

## Table of Contents

- [Please do](#please-do)
- [Please do not](#please-do-not)
- [Working in a single language](#working-in-a-single-language)
- [Cross-language specification changes](#cross-language-specification-changes)
- [Adding to an existing language port](#adding-to-an-existing-language-port)
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
- A language label (`lang:go`, `lang:typescript`, `lang:rust`, `lang:cpp`, `lang:zig`, `language:dotnet`, `language:java`, or `python`) - Language-specific contributions
- `phase:language-parity` or `cross-language` - Work spanning multiple ports

✅ **Follow the acceptance criteria** in the issue. If they're unclear, mention `@agenkit/maintainers` to get clarification.

✅ **Write tests** for every language you touch. If your change affects a shared spec or contract (see [Cross-language specification changes](#cross-language-specification-changes)), add or update tests in all affected ports — not just the one you're most comfortable in.

✅ **Update documentation** when adding features or changing behavior.

✅ **Keep pull requests focused**. One issue = one PR. This makes review faster and easier.

---

## Please do not

❌ **Do not open pull requests for issues labeled `core`**. These require additional context from the Agenkit team and are reserved for maintainers.

❌ **Do not expand the scope** of your pull request beyond what the issue describes. If you want to add more, open a separate issue and PR.

❌ **Do not submit PRs without an issue**. Create an issue first so we can discuss the approach.

❌ **Do not skip tests**. All changes must have test coverage in every language affected by the change.

❌ **Do not modify a shared contract** (pattern spec, wire protocol, public interface) in only one language. If a change belongs in the spec, every port that implements it needs the matching update — see [Cross-language specification changes](#cross-language-specification-changes).

❌ **Do not modify the API** without extensive discussion. Breaking changes require careful planning.

---

## Working in a single language

Agenkit has 9 implementations: the Python core (`agenkit/`) plus 8 language ports
(`agenkit-go/`, `agenkit-ts/`, `agenkit-rust/`, `agenkit-cpp/`, `agenkit-zig/`,
`agenkit-cs/`, `agenkit-java/`, `agenkit-scala/`). You only need to set up the
language(s) you're actually changing — you do **not** need every language installed
to fix a bug in one of them.

Each port documents its own setup, build, and test commands in its own
`README.md` (and, where present, its own `CONTRIBUTING.md`):

| Language   | Setup docs |
|------------|------------|
| Python (core) | see below |
| Go | [`agenkit-go/README.md`](../agenkit-go/README.md) |
| TypeScript | [`agenkit-ts/README.md`](../agenkit-ts/README.md) |
| Rust | [`agenkit-rust/README.md`](../agenkit-rust/README.md) |
| C++ | [`agenkit-cpp/README.md`](../agenkit-cpp/README.md) |
| Zig | [`agenkit-zig/README.md`](../agenkit-zig/README.md) |
| C# | [`agenkit-cs/README.md`](../agenkit-cs/README.md) |
| Java | [`agenkit-java/README.md`](../agenkit-java/README.md) |
| Scala | [`agenkit-scala/README.md`](../agenkit-scala/README.md) |

### Python (core) setup

**Requirements:** Python 3.12+ (see `requires-python` in `pyproject.toml`)

```bash
# Clone the repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Install uv if you don't have it: https://docs.astral.sh/uv/
# All Python operations in this repo go through uv, not bare python/pip/pytest.

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/
```

**Python dev tools:** `pytest` (testing), `ruff` (lint + format), `mypy` (type
checking), `pytest-cov` (coverage) — all invoked via `uv run`.

### Quick command reference by language

| Language   | Test command                                  |
|------------|------------------------------------------------|
| Python     | `uv run pytest tests/`                         |
| Go         | `cd agenkit-go && go test ./...`               |
| TypeScript | `cd agenkit-ts && npm test`                    |
| Rust       | `cd agenkit-rust && cargo test --all-targets`  |
| C++        | `cd agenkit-cpp/build && ctest`                |
| Zig        | `cd agenkit-zig && zig build test`             |
| C#         | `cd agenkit-cs && dotnet test`                 |
| Java       | `cd agenkit-java && mvn test`                  |
| Scala      | `cd agenkit-scala && sbt test`                 |

From the repo root, `make test` runs the fast Python validation used before
every commit (see [Testing](#testing)); `./scripts/test-parity.sh` runs (or
reports) test counts across all 9 languages.

---

## Cross-language specification changes

Some changes aren't local to one port — they define a contract every language
must honor identically:

- **Agent patterns** are specified once, in `specs/patterns/*.yaml` (18
  patterns: `react.yaml`, `reflection.yaml`, `planning.yaml`, etc.). If you're
  changing pattern behavior, update the spec first, then bring every affected
  port's implementation in line with it.
- **Wire protocols** (gRPC/protobuf, HTTP, WebSocket, MCP) are defined in
  `proto/agent.proto` and the adapter code in each port. A protocol change
  must stay backward compatible (see [Protocol Compatibility](#1-protocol-compatibility)
  below) and needs matching updates in every port that speaks that protocol.
- **Public interfaces** (the `Agent` contract, `CallOptions`, middleware
  signatures) are defined once per language but must mean the same thing
  everywhere. Check `agenkit/interfaces.py` (Python) and the equivalent
  `interfaces` file in each port before changing shape or semantics.

For this category of change:

1. Open an issue describing the contract change and which ports it touches.
2. Update the spec/proto/interface first.
3. Update every affected language's implementation to match.
4. Add or update cross-language equivalence tests (see
   [Cross-Language Integration Tests](#cross-language-integration-tests)) so a
   future regression in any one language is caught automatically.
5. Update `docs/parity/FEATURE_MATRIX.md` / `feature-manifest.json` if the
   change affects tracked feature parity (see `docs/parity/README.md`).

---

## Adding to an existing language port

If you're deepening one language's implementation (a new middleware, adapter,
or pattern that other ports already have), treat the existing ports as the
spec: read the same feature in at least one other language first, then match
its observable behavior (not necessarily its internal structure) in idiomatic
code for your target language. Add the language-specific setup from its own
README (table above), write tests in that language, and note the parity gap
you closed in your PR description so `docs/parity/FEATURE_MATRIX.md` can be
regenerated.

---

## Testing

Agenkit maintains test coverage across all 9 languages. All contributions
must maintain or improve test coverage for the language(s) they touch.

### Running tests locally

Use each language's own test command from the [quick reference table](#quick-command-reference-by-language)
above. From the repo root:

```bash
make test         # Fast Python validation (~15-30s) — run before every commit
make test-quick   # Quick Python smoke tests (~10s)
make test-lint    # Full Python lint + test (optional, more thorough)
```

**Python:**
```bash
# All tests
uv run pytest tests/

# Specific module
uv run pytest tests/middleware/

# With coverage
uv run pytest tests/ --cov=agenkit --cov-report=html

# Skip integration tests (faster)
uv run pytest tests/ -m "not integration"
```

See `docs/TESTING.md` for the full breakdown of pytest markers
(`integration`, `cross_language`, `llm_api`, `slow`, `chaos`, `property`).

**Go:**
```bash
go test ./...              # All tests
go test ./middleware        # Specific package
go test ./... -cover        # With coverage
go test ./... -v            # Verbose output
```

Other languages follow the same pattern with their native test runner —
see the [quick reference table](#quick-command-reference-by-language).

### Cross-Language Integration Tests

Two separate suites verify behavior across languages (details in `docs/TESTING.md`):

- **`tests/integration/`** — Python ↔ Go wire-level tests over HTTP/gRPC/WebSocket.
  Requires the Go runtime and compiled servers:
  ```bash
  cd agenkit-go
  go build -o bin/http-server ./cmd/http-server
  go build -o bin/grpc-server ./cmd/grpc-server
  cd ..
  uv run pytest tests/integration/ -m "cross_language" -v
  ```

- **`tests/cross_language/`** — 9-language equivalence tests driven by YAML
  scenario specs (`tests/cross_language/specs/`), comparing per-language
  harness binaries' outputs for message serialization, retry/timeout/circuit-breaker/
  rate-limiter behavior, and pattern execution:
  ```bash
  ./scripts/build-harnesses.sh   # build harnesses once, or after source changes
  uv run pytest tests/cross_language/ -m "cross_language" -v
  ```

For a change affecting multiple languages, run the equivalence suite for
every language you touched, not just the pair you're most familiar with.

### Test Requirements

✅ **Unit tests** for all new code (target: 90%+ coverage)

✅ **Integration tests** for cross-language features

✅ **Every affected language** for shared transport/middleware/pattern changes

✅ **Documentation** for public APIs

### Writing Good Tests

```python
# Python example
async def test_retry_decorator_with_failure():
    """Test retry decorator handles transient failures."""
    agent = FailingAgent(fail_count=2)  # Fails twice, then succeeds
    decorated = RetryDecorator(agent, RetryConfig(max_retries=3))

    result = await decorated.process(Message(role="user", content="hello"))

    assert result.content == "success"
    assert agent.call_count == 3  # Called 3 times total
```

```go
// Go example
func TestRetryDecoratorWithFailure(t *testing.T) {
    // Test retry decorator handles transient failures
    agent := NewFailingAgent(2) // Fails twice, then succeeds
    decorated := middleware.NewRetryDecorator(agent, middleware.RetryConfig{MaxRetries: 3})

    result, err := decorated.Process(ctx, message)

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

3. **Add tests** for your changes, in every language your change touches

4. **Run the test suite** for each language you changed, to ensure everything passes:
   ```bash
   # Python
   uv run pytest tests/

   # Go
   go test ./...

   # (and so on for whichever other languages you touched — see the
   # quick reference table under "Working in a single language")
   ```

5. **Run linters** for each language you changed:
   ```bash
   # Python
   uv run ruff check .
   uv run mypy agenkit/

   # Go
   golangci-lint run
   ```

6. **Commit your changes** with a clear message:
   ```bash
   git commit -m "feat(middleware): Add rate limiter middleware

   - Implements token bucket algorithm
   - Configurable rate and burst capacity
   - Thread-safe with asyncio.Lock (Python) / sync.Mutex (Go)
   - Tests added for every language touched

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
   - Note which language(s) you touched and which you did not
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
async def process(
    self,
    message: Message,
    **kwargs: Any,
) -> Message:
    """Process a message and return a response."""
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
    result = await agent.process(message)
except TimeoutError:
    logger.error("Agent processing timed out")
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
result, err := agent.Process(ctx, message)
if err != nil {
    return nil, fmt.Errorf("agent processing failed: %w", err)
}

// Bad
result, _ := agent.Process(ctx, message)
```

**2. Context**

Pass context everywhere:
```go
func (a *Agent) Process(ctx context.Context, message *Message) (*Message, error) {
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
    Process(ctx context.Context, message *Message) (*Message, error)
}

// Bad - too many methods
type Agent interface {
    Process(ctx context.Context, message *Message) (*Message, error)
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
    // Process handles a message and returns a response.
    // The context can be used for cancellation and timeouts.
    Process(ctx context.Context, message *Message) (*Message, error)
}
```

Every other language port follows the same idioms for its own ecosystem
(idiomatic error handling, small interfaces, documented public symbols) — see
`CLAUDE.md`'s per-language checklists and each port's own README for details
specific to that language.

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

Features should work the same across every port. The core `process(message)`
contract is identical in spirit everywhere, with idiomatic naming per language:

```python
# Python
agent = RetryDecorator(agent, RetryConfig(max_retries=3))
result = await agent.process(message)
```

```go
// Go - same behavior
agent = middleware.NewRetryDecorator(agent, middleware.RetryConfig{MaxRetries: 3})
result, err := agent.Process(ctx, message)
```

Adding a capability to only one or two languages without a tracked plan for
the rest creates parity debt — check `docs/parity/FEATURE_MATRIX.md` and open
issues for the ports you can't cover yourself.

**3. Test Coverage**

Cross-language features need tests that verify equivalence, not just that
each language works in isolation:
- Wire-level Python ↔ Go communication (`tests/integration/`)
- 9-language behavioral equivalence (`tests/cross_language/`)
- Error handling equivalence across languages

---

## Resources

### Documentation

- [README](../README.md) - Project overview
- [Agent Patterns Guide](../docs-site/guides/agent-patterns.md) - Comprehensive agent patterns
- [Architecture](../docs-site/core-concepts/architecture.md) - System design
- [Testing Guide](../docs/TESTING.md) - Running tests, including cross-language suites
- [Feature Parity](../docs/parity/README.md) - Cross-language parity tracking

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
