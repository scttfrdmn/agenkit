# Testing Patterns for Agenkit Agents

Comprehensive guide to testing AI agents with unit tests, integration tests, and best practices.

## What You'll Learn

1. **Unit Testing** - Test individual agents in isolation
2. **Integration Testing** - Test agent interactions and pipelines
3. **Mock Agents** - Create test doubles for LLMs and external services
4. **Property-Based Testing** - Test invariants with generated data
5. **Cross-Language Testing** - Test agents across Python, Go, TypeScript, etc.
6. **Performance Testing** - Load testing and benchmarking
7. **Best Practices** - Patterns for maintainable test suites

## Prerequisites

- Completed Tutorials 01-03
- Understanding of Python testing (pytest)
- Familiarity with async/await patterns

---

## 1. Unit Testing Agents

### Why Unit Test?

- **Fast feedback**: Catch bugs early
- **Confidence**: Refactor safely
- **Documentation**: Tests show how agents work
- **Regression prevention**: Ensure bugs stay fixed

### Basic Agent Test

```python
import pytest
from agenkit import Agent, Message

class EchoAgent(Agent):
    def name(self) -> str:
        return "echo-agent"

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Echo: {message.content}"
        )

# Test
@pytest.mark.asyncio
async def test_echo_agent_basic():
    """Test that echo agent echoes input."""
    agent = EchoAgent()

    # Test name
    assert agent.name() == "echo-agent"

    # Test processing
    input_msg = Message(role="user", content="Hello")
    output_msg = await agent.process(input_msg)

    assert output_msg.role == "assistant"
    assert "Hello" in output_msg.content
    assert output_msg.content.startswith("Echo:")
```

### Testing with Fixtures

```python
import pytest

@pytest.fixture
def echo_agent():
    """Fixture providing echo agent instance."""
    return EchoAgent()

@pytest.fixture
def sample_message():
    """Fixture providing sample message."""
    return Message(role="user", content="Test message")

@pytest.mark.asyncio
async def test_with_fixtures(echo_agent, sample_message):
    """Test using pytest fixtures."""
    response = await echo_agent.process(sample_message)
    assert response.role == "assistant"
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input_content,expected_prefix", [
    ("Hello", "Echo: Hello"),
    ("Test", "Echo: Test"),
    ("", "Echo: "),
    ("🎉", "Echo: 🎉"),
])
@pytest.mark.asyncio
async def test_echo_agent_parametrized(echo_agent, input_content, expected_prefix):
    """Test echo agent with multiple inputs."""
    message = Message(role="user", content=input_content)
    response = await echo_agent.process(message)
    assert response.content == expected_prefix
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test that agent handles errors gracefully."""
    class FailingAgent(Agent):
        def name(self) -> str:
            return "failing-agent"

        async def process(self, message: Message) -> Message:
            if "error" in message.content.lower():
                raise ValueError("Simulated error")
            return Message(role="assistant", content="OK")

    agent = FailingAgent()

    # Should raise ValueError
    with pytest.raises(ValueError, match="Simulated error"):
        await agent.process(Message(role="user", content="trigger ERROR"))

    # Should work normally
    response = await agent.process(Message(role="user", content="normal"))
    assert response.content == "OK"
```

---

## 2. Integration Testing

### Testing Agent Pipelines

```python
from agenkit.composition import SequentialAgent

@pytest.mark.asyncio
async def test_sequential_pipeline():
    """Test agent pipeline integration."""
    # Create pipeline
    agent1 = EchoAgent()
    agent2 = UppercaseAgent()  # Converts to uppercase
    pipeline = SequentialAgent([agent1, agent2])

    # Test end-to-end
    input_msg = Message(role="user", content="hello")
    output_msg = await pipeline.process(input_msg)

    # Verify pipeline behavior
    assert "ECHO:" in output_msg.content
    assert "HELLO" in output_msg.content
```

### Testing with External Dependencies

```python
import pytest
from unittest.mock import AsyncMock, patch
from agenkit.adapters import OpenAIAdapter

@pytest.mark.asyncio
async def test_llm_agent_with_mock():
    """Test LLM agent with mocked API."""
    # Mock OpenAI API
    with patch('openai.AsyncOpenAI') as mock_openai:
        # Setup mock response
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="Mocked response"))]
        )
        mock_openai.return_value = mock_client

        # Test agent
        adapter = OpenAIAdapter(api_key="test-key")
        # ... test logic
```

### Testing Middleware

```python
from agenkit.middleware import RetryMiddleware
import pytest

@pytest.mark.asyncio
async def test_retry_middleware():
    """Test that retry middleware retries on failure."""
    call_count = 0

    class UnreliableAgent(Agent):
        def name(self) -> str:
            return "unreliable"

        async def process(self, message: Message) -> Message:
            nonlocal call_count
            call_count += 1

            # Fail first 2 times
            if call_count < 3:
                raise Exception("Simulated failure")

            return Message(role="assistant", content="Success")

    # Wrap with retry middleware
    agent = UnreliableAgent()
    retry_agent = RetryMiddleware(agent, max_retries=3)

    # Should succeed on 3rd attempt
    response = await retry_agent.process(Message(role="user", content="test"))

    assert response.content == "Success"
    assert call_count == 3  # Verify it retried
```

---

## 3. Mock Agents

### Creating Mock Agents

```python
class MockLLMAgent(Agent):
    """Mock LLM for testing without API calls."""

    def __init__(self, responses: dict[str, str]):
        self.responses = responses

    def name(self) -> str:
        return "mock-llm"

    async def process(self, message: Message) -> Message:
        # Return pre-configured response
        response_text = self.responses.get(
            message.content,
            "Default mock response"
        )
        return Message(role="assistant", content=response_text)

# Usage
@pytest.mark.asyncio
async def test_with_mock_llm():
    """Test agent using mock LLM."""
    mock_llm = MockLLMAgent(responses={
        "What is 2+2?": "4",
        "Hello": "Hi there!",
    })

    # Test deterministic responses
    response = await mock_llm.process(Message(role="user", content="What is 2+2?"))
    assert response.content == "4"

    response = await mock_llm.process(Message(role="user", content="Hello"))
    assert response.content == "Hi there!"
```

### Mock Agent with State

```python
class StatefulMockAgent(Agent):
    """Mock agent that tracks state."""

    def __init__(self):
        self.call_count = 0
        self.last_message = None

    def name(self) -> str:
        return "stateful-mock"

    async def process(self, message: Message) -> Message:
        self.call_count += 1
        self.last_message = message

        return Message(
            role="assistant",
            content=f"Call #{self.call_count}",
            metadata={"call_count": self.call_count}
        )

# Test
@pytest.mark.asyncio
async def test_stateful_mock():
    """Test mock agent tracks state."""
    agent = StatefulMockAgent()

    # First call
    response1 = await agent.process(Message(role="user", content="first"))
    assert agent.call_count == 1
    assert response1.metadata["call_count"] == 1

    # Second call
    response2 = await agent.process(Message(role="user", content="second"))
    assert agent.call_count == 2
    assert agent.last_message.content == "second"
```

---

## 4. Property-Based Testing

### What is Property-Based Testing?

Instead of writing individual test cases, you define **properties** (invariants) that should always hold, and the framework generates random test data.

### Using Hypothesis

```python
import pytest
from hypothesis import given, strategies as st

@given(content=st.text())
@pytest.mark.asyncio
async def test_echo_agent_property(content):
    """Property: Echo agent always includes input in output."""
    agent = EchoAgent()
    message = Message(role="user", content=content)
    response = await agent.process(message)

    # Property: Output should contain input
    assert content in response.content or content == ""
    # Property: Output should start with "Echo:"
    assert response.content.startswith("Echo:")
```

### Testing Agent Invariants

```python
from hypothesis import given
import hypothesis.strategies as st

@given(
    content=st.text(min_size=1, max_size=1000),
    role=st.sampled_from(["user", "assistant", "system"])
)
@pytest.mark.asyncio
async def test_agent_invariants(agent, content, role):
    """Test properties that should always hold."""
    message = Message(role=role, content=content)
    response = await agent.process(message)

    # Invariant: Response should be a Message
    assert isinstance(response, Message)

    # Invariant: Response role should be assistant
    assert response.role == "assistant"

    # Invariant: Response should have content
    assert isinstance(response.content, str)
```

---

## 5. Cross-Language Testing

### Testing Python Agents from Go

```go
// Go test calling Python agent over HTTP
package main

import (
    "testing"
    "github.com/agenkit/agenkit-go/transports"
)

func TestPythonAgentFromGo(t *testing.T) {
    // Connect to Python agent
    agent, err := transports.NewHTTPAgent("http://localhost:8000")
    if err != nil {
        t.Fatal(err)
    }

    // Send message
    message := &Message{
        Role:    "user",
        Content: "Hello from Go!",
    }

    response, err := agent.Process(context.Background(), message)
    if err != nil {
        t.Fatal(err)
    }

    // Verify response
    if response.Role != "assistant" {
        t.Errorf("Expected role 'assistant', got '%s'", response.Role)
    }
}
```

### Cross-Language Integration Tests

```python
import pytest
import subprocess
import time

@pytest.fixture(scope="module")
def go_agent_server():
    """Start Go agent server for testing."""
    # Start Go server
    process = subprocess.Popen(
        ["go", "run", "main.go"],
        cwd="../agenkit-go/examples/http"
    )

    # Wait for server to start
    time.sleep(2)

    yield "http://localhost:8080"

    # Cleanup
    process.terminate()
    process.wait()

@pytest.mark.asyncio
async def test_python_calls_go_agent(go_agent_server):
    """Test Python agent calling Go agent."""
    from agenkit.transports import HTTPClient

    # Connect to Go agent
    go_agent = HTTPClient(go_agent_server)

    # Call Go agent from Python
    message = Message(role="user", content="Hello from Python")
    response = await go_agent.process(message)

    assert response.role == "assistant"
    assert len(response.content) > 0
```

---

## 6. Performance Testing

### Load Testing with pytest-benchmark

```python
import pytest

@pytest.mark.benchmark
def test_agent_performance(benchmark):
    """Benchmark agent performance."""
    agent = EchoAgent()
    message = Message(role="user", content="test")

    # Benchmark
    result = benchmark(lambda: asyncio.run(agent.process(message)))

    # Assertions on result
    assert result.content.startswith("Echo:")

# Run: pytest test_performance.py --benchmark-only
```

### Concurrent Load Testing

```python
import asyncio
import pytest
from agenkit.transports import HTTPClient

@pytest.mark.asyncio
async def test_concurrent_load():
    """Test agent under concurrent load."""
    agent = HTTPClient("http://localhost:8000")

    async def make_request(i):
        message = Message(role="user", content=f"Request {i}")
        return await agent.process(message)

    # Send 100 concurrent requests
    tasks = [make_request(i) for i in range(100)]
    responses = await asyncio.gather(*tasks)

    # Verify all succeeded
    assert len(responses) == 100
    assert all(r.role == "assistant" for r in responses)
```

### Profiling with cProfile

```python
import cProfile
import pstats
import asyncio

def profile_agent():
    """Profile agent execution."""
    agent = MyAgent()

    async def run():
        for _ in range(100):
            await agent.process(Message(role="user", content="test"))

    asyncio.run(run())

# Run profiler
cProfile.run('profile_agent()', 'agent_profile.stats')

# Analyze results
stats = pstats.Stats('agent_profile.stats')
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest functions
```

---

## 7. Best Practices

### Test Organization

```
tests/
├── unit/
│   ├── test_agents.py          # Individual agent tests
│   ├── test_middleware.py      # Middleware tests
│   └── test_patterns.py        # Pattern tests
├── integration/
│   ├── test_pipelines.py       # Pipeline integration
│   ├── test_http_transport.py  # HTTP transport
│   └── test_cross_language.py  # Cross-language tests
├── performance/
│   ├── test_benchmarks.py      # Benchmark tests
│   └── test_load.py            # Load tests
├── fixtures/
│   ├── agents.py               # Agent fixtures
│   └── data.py                 # Test data
└── conftest.py                 # Shared pytest config
```

### Conftest.py Setup

```python
# tests/conftest.py
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_llm():
    """Fixture providing mock LLM."""
    return MockLLMAgent(responses={
        "test": "test response"
    })

@pytest.fixture
async def agent_with_cleanup():
    """Fixture with setup and teardown."""
    agent = MyAgent()
    await agent.initialize()

    yield agent

    # Cleanup
    await agent.cleanup()
```

### Markers for Test Organization

```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast)
    integration: Integration tests (slower)
    slow: Slow tests (run separately)
    llm: Tests requiring LLM API (may cost money)
    cross_language: Cross-language integration tests

# Use markers
@pytest.mark.unit
@pytest.mark.asyncio
async def test_fast_unit():
    """Fast unit test."""
    pass

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_slow_integration():
    """Slow integration test."""
    pass

# Run specific tests:
# pytest -m unit                # Only unit tests
# pytest -m "not slow"          # Skip slow tests
# pytest -m "not llm"           # Skip tests requiring API
```

### Assertion Helpers

```python
def assert_valid_message(msg: Message):
    """Helper to assert message is valid."""
    assert isinstance(msg, Message)
    assert msg.role in ["user", "assistant", "system", "tool"]
    assert isinstance(msg.content, str)
    assert len(msg.content) > 0

def assert_agent_response_time(agent, message, max_seconds=1.0):
    """Assert agent responds within time limit."""
    import time

    start = time.time()
    response = await agent.process(message)
    duration = time.time() - start

    assert duration < max_seconds, f"Agent took {duration:.2f}s (max: {max_seconds}s)"
    return response
```

### Test Data Management

```python
# tests/fixtures/data.py
SAMPLE_MESSAGES = [
    Message(role="user", content="Hello"),
    Message(role="user", content="What is 2+2?"),
    Message(role="user", content="Tell me a joke"),
]

EXPECTED_RESPONSES = {
    "Hello": ["Hi", "Hello", "Hey"],
    "What is 2+2?": ["4", "The answer is 4"],
}

# Usage
@pytest.mark.parametrize("message", SAMPLE_MESSAGES)
@pytest.mark.asyncio
async def test_with_sample_data(agent, message):
    """Test agent with sample messages."""
    response = await agent.process(message)
    assert_valid_message(response)
```

---

## Testing Checklist

### Unit Tests

- [ ] Test agent name and capabilities
- [ ] Test basic message processing
- [ ] Test edge cases (empty input, special characters, etc.)
- [ ] Test error handling
- [ ] Test with parametrized inputs
- [ ] Test metadata handling

### Integration Tests

- [ ] Test agent pipelines
- [ ] Test middleware integration
- [ ] Test transport layer (HTTP, WebSocket)
- [ ] Test with real dependencies (when safe)
- [ ] Test cross-language interop

### Performance Tests

- [ ] Benchmark single request latency
- [ ] Test under concurrent load
- [ ] Profile for bottlenecks
- [ ] Test memory usage
- [ ] Test resource cleanup

### Coverage

- [ ] Aim for >80% code coverage
- [ ] Cover error paths
- [ ] Cover edge cases
- [ ] Test public API surface

---

## Common Testing Patterns

### Pattern 1: AAA (Arrange, Act, Assert)

```python
@pytest.mark.asyncio
async def test_agent_aaa_pattern():
    """Test using AAA pattern."""
    # Arrange
    agent = EchoAgent()
    message = Message(role="user", content="test")

    # Act
    response = await agent.process(message)

    # Assert
    assert response.content == "Echo: test"
```

### Pattern 2: Given-When-Then (BDD)

```python
@pytest.mark.asyncio
async def test_agent_bdd_pattern():
    """Test using BDD pattern."""
    # Given an echo agent
    agent = EchoAgent()

    # When I send a message
    message = Message(role="user", content="hello")
    response = await agent.process(message)

    # Then I should receive an echoed response
    assert "hello" in response.content
    assert response.role == "assistant"
```

### Pattern 3: Test Factories

```python
def create_test_agent(**kwargs):
    """Factory for creating test agents."""
    defaults = {
        "name": "test-agent",
        "timeout": 30.0,
    }
    defaults.update(kwargs)
    return TestAgent(**defaults)

@pytest.mark.asyncio
async def test_with_factory():
    """Test using factory pattern."""
    agent1 = create_test_agent(name="agent-1")
    agent2 = create_test_agent(name="agent-2", timeout=60.0)
    # ... test logic
```

---

## Tools and Libraries

### Essential Testing Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-benchmark**: Performance benchmarking
- **hypothesis**: Property-based testing
- **faker**: Generate fake test data

### Install Testing Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov pytest-benchmark hypothesis faker
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agenkit --cov-report=html

# Run only unit tests
pytest -m unit

# Run specific test file
pytest tests/unit/test_agents.py

# Run with verbose output
pytest -v

# Run in parallel (faster)
pytest -n auto

# Run and stop on first failure
pytest -x

# Re-run failed tests
pytest --lf

# Run benchmarks
pytest --benchmark-only
```

---

## Summary

You've learned comprehensive testing patterns! ✅

✅ **Unit Testing** - Fast, isolated agent tests
✅ **Integration Testing** - Test agent interactions
✅ **Mock Agents** - Test without external dependencies
✅ **Property-Based Testing** - Test invariants
✅ **Cross-Language Testing** - Test polyglot systems
✅ **Performance Testing** - Benchmark and load test
✅ **Best Practices** - Maintainable test suites

## Next Steps

- **[Deployment Guide](04-deployment/)** - Deploy tested agents to production
- **[Examples Directory](https://github.com/scttfrdmn/agenkit/tree/main/examples)** - See testing in real examples
- **[CI/CD Guide](04-deployment/.github/workflows/deploy.yml)** - Automate testing in pipelines

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

Ready to build reliable, well-tested agents! 🧪✅
