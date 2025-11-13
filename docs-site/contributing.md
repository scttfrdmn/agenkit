# Contributing

Thank you for your interest in contributing to Agenkit!

## Ways to Contribute

There are many ways to contribute:

- **Report bugs** - Found a bug? [Open an issue](https://github.com/scttfrdmn/agenkit/issues/new)
- **Suggest features** - Have an idea? [Start a discussion](https://github.com/scttfrdmn/agenkit/discussions)
- **Improve docs** - Fix typos, add examples, clarify explanations
- **Write code** - Fix bugs, add features, improve performance
- **Share examples** - Show us what you've built!

---

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/agenkit.git
cd agenkit
```

### 2. Set Up Development Environment

=== "Python"

    ```bash
    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # or `venv\Scripts\activate` on Windows

    # Install in development mode
    pip install -e ".[dev]"

    # Run tests
    pytest tests/
    ```

=== "Go"

    ```bash
    cd agenkit-go

    # Download dependencies
    go mod download

    # Run tests
    go test ./...

    # Run linter
    golangci-lint run
    ```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

---

## Development Workflow

### 1. Make Changes

- Write code following our style guidelines (see below)
- Add tests for new functionality
- Update documentation as needed

### 2. Run Tests

=== "Python"

    ```bash
    # Run all tests
    pytest tests/

    # Run specific test file
    pytest tests/test_interfaces.py

    # Run with coverage
    pytest tests/ --cov=agenkit --cov-report=html

    # Type checking
    mypy agenkit/

    # Linting
    ruff check agenkit/ tests/
    black --check agenkit/ tests/
    ```

=== "Go"

    ```bash
    # Run all tests
    go test ./...

    # Run with coverage
    go test ./... -coverprofile=coverage.out
    go tool cover -html=coverage.out

    # Linting
    golangci-lint run

    # Formatting
    gofmt -w .
    ```

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new middleware for X"
```

**Commit message format:**

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create PR on GitHub
```

---

## Code Style Guidelines

### Python

- **PEP 8 compliant** - Use `black` for formatting
- **Type hints** - All public APIs must have type hints
- **Docstrings** - Use Google-style docstrings
- **mypy strict** - Code must pass `mypy --strict`

```python
from typing import Any

class MyAgent(Agent):
    """
    A sample agent that demonstrates style guidelines.

    Args:
        name: The agent name
        config: Optional configuration dict

    Example:
        >>> agent = MyAgent("my-agent")
        >>> response = await agent.process(message)
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self._name = name
        self._config = config or {}

    @property
    def name(self) -> str:
        """Agent identifier."""
        return self._name

    async def process(self, message: Message) -> Message:
        """
        Process a message and return a response.

        Args:
            message: Input message to process

        Returns:
            Response message

        Raises:
            ValueError: If message content is invalid
        """
        # Implementation here
        pass
```

### Go

- **gofmt formatted** - Always run `gofmt`
- **golangci-lint clean** - Must pass linter
- **Idiomatic Go** - Follow effective Go guidelines
- **Comments on exports** - All exported items documented

```go
// MyAgent is a sample agent that demonstrates style guidelines.
//
// Example:
//
//	agent := &MyAgent{name: "my-agent"}
//	response, err := agent.Process(ctx, message)
type MyAgent struct {
    name   string
    config map[string]interface{}
}

// Name returns the agent identifier.
func (a *MyAgent) Name() string {
    return a.name
}

// Process processes a message and returns a response.
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    // Implementation here
    return nil, nil
}
```

---

## Testing Guidelines

### Test Coverage

- **New features:** Must include tests
- **Bug fixes:** Must include regression test
- **Coverage target:** >90% for new code

### Test Structure

=== "Python"

    ```python
    import pytest
    from agenkit import Agent, Message

    class TestMyAgent:
        """Tests for MyAgent."""

        @pytest.fixture
        def agent(self):
            """Create agent instance for testing."""
            return MyAgent("test-agent")

        @pytest.mark.asyncio
        async def test_process_success(self, agent):
            """Test successful message processing."""
            message = Message(role="user", content="test")
            response = await agent.process(message)

            assert response.role == "agent"
            assert "test" in response.content

        @pytest.mark.asyncio
        async def test_process_empty_message(self, agent):
            """Test handling of empty message."""
            message = Message(role="user", content="")

            with pytest.raises(ValueError):
                await agent.process(message)
    ```

=== "Go"

    ```go
    package mypackage_test

    import (
        "context"
        "testing"
        "github.com/stretchr/testify/assert"
        "github.com/stretchr/testify/require"
    )

    func TestMyAgent_Process(t *testing.T) {
        t.Run("success", func(t *testing.T) {
            agent := &MyAgent{name: "test-agent"}
            message := &agenkit.Message{
                Role:    "user",
                Content: "test",
            }

            response, err := agent.Process(context.Background(), message)

            require.NoError(t, err)
            assert.Equal(t, "agent", response.Role)
            assert.Contains(t, response.Content, "test")
        })

        t.Run("empty_message", func(t *testing.T) {
            agent := &MyAgent{name: "test-agent"}
            message := &agenkit.Message{Role: "user", Content: ""}

            _, err := agent.Process(context.Background(), message)

            assert.Error(t, err)
        })
    }
    ```

---

## Documentation Guidelines

- **Code comments:** Explain WHY, not WHAT
- **Docstrings:** Required for all public APIs
- **Examples:** Include usage examples
- **Diagrams:** Use ASCII art or Mermaid for visuals

### Documentation Structure

When updating docs:

```bash
# Documentation site
docs-site/
├── getting-started/    # Tutorials and guides
├── core-concepts/      # Architecture and design
├── features/           # Feature documentation
├── guides/             # How-to guides
├── api/                # API reference
└── examples/           # Example code

# Build and preview
mkdocs serve
# Visit http://localhost:8000
```

---

## Pull Request Process

1. **Describe your changes**
   - What does this PR do?
   - Why is it needed?
   - How does it work?

2. **Link related issues**
   - Fixes #123
   - Relates to #456

3. **Add tests**
   - New features require tests
   - Existing tests must pass

4. **Update documentation**
   - Add/update docstrings
   - Update relevant guides
   - Add examples if applicable

5. **Wait for review**
   - Maintainers will review
   - Address feedback
   - Keep commits clean

---

## Code Review Checklist

Before requesting review, ensure:

- [ ] Tests pass (`pytest tests/` or `go test ./...`)
- [ ] Type checking passes (`mypy` or `go build`)
- [ ] Linting passes (`ruff`, `black` or `golangci-lint`)
- [ ] Documentation updated
- [ ] Examples added/updated if needed
- [ ] Commit messages follow convention
- [ ] PR description is clear

---

## Community Guidelines

- **Be respectful** - Treat everyone with respect
- **Be constructive** - Focus on the code, not the person
- **Be patient** - Maintainers are volunteers
- **Be open** - Consider other perspectives
- **Be helpful** - Help others when you can

---

## Questions?

- **GitHub Discussions:** [Ask a question](https://github.com/scttfrdmn/agenkit/discussions)
- **GitHub Issues:** [Report a problem](https://github.com/scttfrdmn/agenkit/issues)

Thank you for contributing to Agenkit! 🎉
