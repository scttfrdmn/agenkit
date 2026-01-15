# Getting Started with Agenkit - Python

**Complete guide to building AI agents with Agenkit in Python**

## Table of Contents

1. [Installation](#installation)
2. [Your First Agent](#your-first-agent)
3. [Core Concepts](#core-concepts)
4. [Using Patterns](#using-patterns)
5. [Adding Middleware](#adding-middleware)
6. [Working with LLMs](#working-with-llms)
7. [Testing Your Agents](#testing-your-agents)
8. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Install with pip

```bash
pip install agenkit
```

### Install with uv (Recommended)

```bash
uv pip install agenkit
```

### Verify Installation

```bash
python -c "import agenkit; print(agenkit.__version__)"
# Should print: 0.46.0
```

---

## Your First Agent

Let's create a simple agent that processes messages:

### Step 1: Create Your Agent

Create a file `my_agent.py`:

```python
from agenkit import Agent, Message

class GreetingAgent(Agent):
    """A simple agent that greets users."""

    @property
    def name(self) -> str:
        return "greeting-agent"

    async def process(self, message: Message) -> Message:
        """Process a message and return a greeting."""
        user_message = message.content

        return Message(
            role="assistant",
            content=f"Hello! You said: '{user_message}'. How can I help you today?"
        )
```

### Step 2: Use Your Agent

```python
import asyncio
from my_agent import GreetingAgent

async def main():
    # Create agent instance
    agent = GreetingAgent()

    # Create a user message
    user_msg = Message(role="user", content="Hi there!")

    # Process the message
    response = await agent.process(user_msg)

    # Print the response
    print(f"{agent.name}: {response.content}")

# Run the agent
if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Run It

```bash
python my_agent.py
# Output: greeting-agent: Hello! You said: 'Hi there!'. How can I help you today?
```

**🎉 Congratulations!** You've created your first Agenkit agent.

---

## Core Concepts

### The Agent Interface

Every agent in Agenkit implements two things:

1. **`name`** - A unique identifier (property)
2. **`process(message) -> Message`** - Processes messages (async method)

```python
from agenkit import Agent, Message

class Agent:
    @property
    def name(self) -> str:
        """Return the agent's unique identifier."""
        ...

    async def process(self, message: Message) -> Message:
        """Process a message and return a response."""
        ...
```

**That's the entire interface.** Everything else is optional.

### Messages

Messages are the unit of communication:

```python
from agenkit import Message, createMessage

# Create a message
msg = Message(
    role="user",              # Who sent it: "user", "assistant", "system"
    content="Hello!",         # The message content (string or dict)
    metadata={"source": "web"}  # Optional metadata
)

# Or use the helper
msg = createMessage("user", "Hello!", metadata={"source": "web"})

# Access message properties
print(msg.role)      # "user"
print(msg.content)   # "Hello!"
print(msg.metadata)  # {"source": "web"}
```

### Tools

Tools let agents take actions:

```python
from agenkit import Tool, ToolResult

class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Performs basic arithmetic operations"

    async def execute(self, **params) -> ToolResult:
        """Execute the calculation."""
        operation = params.get("operation")
        a = params.get("a")
        b = params.get("b")

        if operation == "add":
            result = a + b
        elif operation == "multiply":
            result = a * b
        else:
            return ToolResult(
                output=None,
                error=f"Unknown operation: {operation}"
            )

        return ToolResult(output=result)
```

---

## Using Patterns

Agenkit includes 18 pre-built patterns for common agent architectures.

### Reflection Pattern

Iteratively improve outputs through self-critique:

```python
from agenkit.patterns import ReflectionAgent, ReflectionConfig
from my_agents import Generator, Critic  # Your custom agents

# Configure reflection
config = ReflectionConfig(
    max_iterations=3,           # Maximum improvement cycles
    quality_threshold=0.8,      # Stop when quality is good enough
    stop_on_repeat=True        # Stop if output doesn't change
)

# Create reflection agent
agent = ReflectionAgent(
    generator=Generator(),      # Generates initial output
    critic=Critic(),           # Critiques and suggests improvements
    config=config
)

# Use it
response = await agent.process(Message(
    role="user",
    content="Write a haiku about coding"
))

# Response includes iteration metadata
print(response.metadata["iterations"])  # Number of improvement cycles
print(response.metadata["final_quality_score"])  # Quality of final output
```

### Sequential Pattern

Chain multiple agents in sequence:

```python
from agenkit.patterns import SequentialPattern

# Create a pipeline: research → summarize → format
pipeline = SequentialPattern([
    ResearchAgent(),      # Gathers information
    SummaryAgent(),       # Summarizes findings
    FormatterAgent()      # Formats final output
])

# Input flows through each agent in order
response = await pipeline.process(Message(
    role="user",
    content="Research quantum computing"
))
```

### Parallel Pattern

Run multiple agents concurrently and aggregate results:

```python
from agenkit.patterns import ParallelPattern

# Run multiple specialized agents in parallel
parallel = ParallelPattern(
    agents=[
        TechnicalAgent(),     # Technical perspective
        BusinessAgent(),      # Business perspective
        UserAgent()          # User perspective
    ],
    aggregation="merge"      # How to combine results: "merge", "vote", "first"
)

# All agents process simultaneously
response = await parallel.process(Message(
    role="user",
    content="Analyze this product idea"
))
```

### ReAct Pattern

Reasoning + Acting with tool use:

```python
from agenkit.patterns import ReActAgent, ReActConfig
from my_agents import ReasoningAgent
from my_tools import SearchTool, CalculatorTool

# Configure ReAct
config = ReActConfig(
    max_steps=5,              # Maximum reasoning steps
    tools=[
        SearchTool(),         # Web search capability
        CalculatorTool()      # Math calculations
    ]
)

# Create ReAct agent
agent = ReActAgent(
    agent=ReasoningAgent(),   # Your reasoning agent
    config=config
)

# Agent will alternate between thinking and acting
response = await agent.process(Message(
    role="user",
    content="What's the population of Tokyo divided by the population of NYC?"
))

# Response includes reasoning trace
print(response.metadata["steps"])          # List of reasoning steps
print(response.metadata["tool_calls"])     # Tools used
```

### More Patterns

Agenkit includes 18 patterns total. See the [Pattern Guide](../patterns/README.md) for:

- **Conversational** - Multi-turn conversations with history
- **Task** - Goal-oriented task execution
- **Multiagent** - Coordinate multiple agents
- **Planning** - Plan-then-execute workflows
- **Autonomous** - Self-directed agent behavior
- **Memory** - Working, short-term, and long-term memory
- **Router** - Route messages to specialized agents
- **Fallback** - Try alternatives when agents fail
- **Collaborative** - Agents work together on complex tasks
- **Human-in-Loop** - Request human approval/input
- **Supervisor** - Manage and coordinate specialist agents

---

## Adding Middleware

Middleware adds production features without changing your agent code.

### Retry Logic

Automatically retry failed operations:

```python
from agenkit.middleware import RetryMiddleware, RetryConfig

# Configure retries
config = RetryConfig(
    max_attempts=3,              # Try up to 3 times
    backoff_factor=2.0,          # Exponential backoff
    initial_delay=1.0,           # Start with 1 second
    max_delay=30.0               # Cap at 30 seconds
)

# Wrap your agent
resilient_agent = RetryMiddleware(my_agent, config)

# Now handles transient failures automatically
response = await resilient_agent.process(message)
```

### Circuit Breaker

Prevent cascading failures:

```python
from agenkit.middleware import CircuitBreakerMiddleware, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,          # Open after 5 failures
    timeout=60.0,                # Stay open for 60 seconds
    success_threshold=2          # Close after 2 successes
)

# Wrap your agent
protected_agent = CircuitBreakerMiddleware(my_agent, config)

# Fails fast when circuit is open (avoids overwhelming failing service)
try:
    response = await protected_agent.process(message)
except CircuitBreakerError:
    print("Circuit is open - service unavailable")
```

### Timeout

Set maximum execution time:

```python
from agenkit.middleware import TimeoutMiddleware, TimeoutConfig

# Configure timeout
config = TimeoutConfig(
    timeout=30.0,                # 30 second timeout
    grace_period=5.0            # 5 second grace for cleanup
)

# Wrap your agent
timed_agent = TimeoutMiddleware(my_agent, config)

# Will cancel after 30 seconds
try:
    response = await timed_agent.process(message)
except TimeoutError:
    print("Agent took too long to respond")
```

### Rate Limiting

Control request rate:

```python
from agenkit.middleware import RateLimiterMiddleware, RateLimiterConfig

# Configure rate limiter
config = RateLimiterConfig(
    max_requests=100,            # 100 requests
    window_seconds=60.0,         # Per minute
    strategy="sliding_window"    # Fair distribution
)

# Wrap your agent
limited_agent = RateLimiterMiddleware(my_agent, config)

# Will block if rate limit exceeded
response = await limited_agent.process(message)
```

### Stacking Middleware

Combine multiple middleware layers:

```python
from agenkit.middleware import (
    RetryMiddleware,
    CircuitBreakerMiddleware,
    TimeoutMiddleware,
    RateLimiterMiddleware
)

# Stack middleware (innermost to outermost)
agent = my_agent
agent = TimeoutMiddleware(agent)        # 1. Enforce timeout
agent = CircuitBreakerMiddleware(agent) # 2. Prevent cascading failures
agent = RetryMiddleware(agent)          # 3. Retry on failure
agent = RateLimiterMiddleware(agent)    # 4. Control rate

# Now has full production resilience
response = await agent.process(message)
```

---

## Working with LLMs

### OpenAI Integration

```python
from agenkit.adapters import OpenAIAdapter

# Create OpenAI agent
agent = OpenAIAdapter(
    model="gpt-4",
    api_key="your-api-key"  # Or set OPENAI_API_KEY env var
)

# Use it like any agent
response = await agent.process(Message(
    role="user",
    content="Explain quantum computing"
))
```

### Anthropic (Claude) Integration

```python
from agenkit.adapters import AnthropicAdapter

# Create Claude agent
agent = AnthropicAdapter(
    model="claude-3-opus-20240229",
    api_key="your-api-key"  # Or set ANTHROPIC_API_KEY env var
)

response = await agent.process(Message(
    role="user",
    content="Write a function to calculate Fibonacci numbers"
))
```

### Custom LLM Integration

```python
from agenkit import Agent, Message
import httpx

class CustomLLMAgent(Agent):
    def __init__(self, api_url: str, api_key: str):
        self._api_url = api_url
        self._api_key = api_key
        self._client = httpx.AsyncClient()

    @property
    def name(self) -> str:
        return "custom-llm"

    async def process(self, message: Message) -> Message:
        # Call your LLM API
        response = await self._client.post(
            self._api_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"prompt": message.content}
        )

        result = response.json()

        return Message(
            role="assistant",
            content=result["completion"]
        )
```

---

## Testing Your Agents

### Unit Testing

```python
import pytest
from agenkit import Message
from my_agent import GreetingAgent

@pytest.mark.asyncio
async def test_greeting_agent():
    """Test that GreetingAgent responds correctly."""
    agent = GreetingAgent()

    # Test basic greeting
    response = await agent.process(Message(
        role="user",
        content="Hello"
    ))

    assert response.role == "assistant"
    assert "Hello" in response.content

@pytest.mark.asyncio
async def test_agent_name():
    """Test that agent has correct name."""
    agent = GreetingAgent()
    assert agent.name == "greeting-agent"
```

### Integration Testing with Mock Agents

```python
from agenkit import Agent, Message
from agenkit.patterns import SequentialPattern

class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self, response: str):
        self._response = response

    @property
    def name(self) -> str:
        return "mock-agent"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=self._response)

@pytest.mark.asyncio
async def test_sequential_pattern():
    """Test sequential pattern with mocks."""
    pipeline = SequentialPattern([
        MockAgent("Step 1 complete"),
        MockAgent("Step 2 complete"),
        MockAgent("Step 3 complete")
    ])

    response = await pipeline.process(Message(
        role="user",
        content="Start pipeline"
    ))

    assert "Step 3 complete" in response.content
```

### Performance Testing

```python
import time
from agenkit.evaluation import Benchmark

# Create benchmark suite
benchmark = Benchmark(
    agent=my_agent,
    test_cases=[
        {"input": "Test 1", "expected": "Response 1"},
        {"input": "Test 2", "expected": "Response 2"},
    ]
)

# Run benchmarks
results = await benchmark.run()

print(f"Average latency: {results.avg_latency_ms}ms")
print(f"Success rate: {results.success_rate * 100}%")
```

---

## Next Steps

### Learn More

- **[Pattern Guide](../patterns/README.md)** - Detailed guide to all 18 patterns
- **[API Reference](../api/python/README.md)** - Complete API documentation
- **[Best Practices](../best-practices/PYTHON.md)** - Production deployment tips
- **[Examples](../../examples/python/)** - 50+ working examples

### Deploy to Production

- **[Docker Deployment](../deployment/DOCKER.md)** - Containerize your agents
- **[Kubernetes Guide](../deployment/KUBERNETES.md)** - Scale with K8s
- **[Monitoring & Observability](../observability/README.md)** - Track agent performance

### Migrate to Other Languages

Need better performance? Migrate to compiled languages:

- **[Python → Go Migration](../migration/PYTHON_TO_GO.md)** - 18x faster
- **[Python → TypeScript Migration](../migration/PYTHON_TO_TYPESCRIPT.md)** - Browser support
- **[Python → Rust Migration](../migration/PYTHON_TO_RUST.md)** - Maximum performance

### Join the Community

- **[GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)** - Ask questions
- **[Discord](https://discord.gg/agenkit)** - Chat with other developers
- **[Contributing Guide](../../CONTRIBUTING.md)** - Help improve Agenkit

---

## Quick Reference

### Installation
```bash
pip install agenkit
```

### Minimal Agent
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="Response")
```

### Common Imports
```python
# Core
from agenkit import Agent, Message, Tool, ToolResult

# Patterns
from agenkit.patterns import (
    ReflectionAgent, ReActAgent, SequentialPattern,
    ParallelPattern, ConversationalAgent
)

# Middleware
from agenkit.middleware import (
    RetryMiddleware, CircuitBreakerMiddleware,
    TimeoutMiddleware, RateLimiterMiddleware
)

# Adapters
from agenkit.adapters import OpenAIAdapter, AnthropicAdapter
```

---

**Ready to build?** Check out the [examples](../../examples/python/) for working code you can run right now.
