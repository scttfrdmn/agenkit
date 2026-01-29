# Getting Started with Agenkit (Python)

**Target audience**: Python developers new to Agenkit
**Time to first agent**: 15-30 minutes
**Prerequisites**: Python 3.10+

---

## Installation

### Option 1: Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new project
uv init my-agent-project
cd my-agent-project

# Add agenkit
uv add agenkit

# Install LLM providers (optional)
uv add anthropic openai
```

### Option 2: Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install agenkit
pip install agenkit

# Install LLM providers (optional)
pip install anthropic openai
```

### Option 3: From Source

```bash
git clone https://github.com/yourusername/agenkit.git
cd agenkit
uv pip install -e .
```

---

## Your First Agent

Let's create a simple greeting agent that processes messages:

```python
import asyncio
from agenkit import Agent, Message


class GreetingAgent(Agent):
    """A simple agent that greets users."""

    @property
    def name(self) -> str:
        return "greeting-agent"

    async def process(self, message: Message) -> Message:
        """Process a user message and return a greeting."""
        user_content = message.content
        greeting = f"Hello! You said: {user_content}"

        return Message(
            role="assistant",
            content=greeting,
            metadata={"processed_by": self.name}
        )


async def main():
    # Create the agent
    agent = GreetingAgent()

    # Create a user message
    user_message = Message(role="user", content="Hi there!")

    # Process the message
    response = await agent.process(user_message)

    print(f"Agent: {response.content}")
    # Output: Agent: Hello! You said: Hi there!


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
uv run python greeting_agent.py
```

---

## Production-Ready Agent with Middleware

Add resilience with retry, circuit breaker, and timeout middleware:

```python
import asyncio
from agenkit import Agent, Message
from agenkit.middleware import (
    RetryDecorator,
    CircuitBreakerDecorator,
    TimeoutDecorator,
)


class ProductionAgent(Agent):
    @property
    def name(self) -> str:
        return "production-agent"

    async def process(self, message: Message) -> Message:
        # Simulate some processing
        await asyncio.sleep(0.1)
        return Message(
            role="assistant",
            content=f"Processed: {message.content}",
            metadata={"agent": self.name}
        )


async def main():
    # Create base agent
    base_agent = ProductionAgent()

    # Wrap with middleware (v0.50.0 parameter names)
    agent = RetryDecorator(
        agent=base_agent,
        max_attempts=3,  # Retry up to 3 times
        initial_delay_ms=100,  # Start with 100ms delay
    )

    agent = CircuitBreakerDecorator(
        agent=agent,
        failure_threshold=5,  # Open after 5 failures
        recovery_timeout_ms=30000,  # 30 seconds
    )

    agent = TimeoutDecorator(
        agent=agent,
        timeout_ms=5000,  # 5 second timeout
    )

    # Use the wrapped agent
    message = Message(role="user", content="Hello production!")
    response = await agent.process(message)
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
```

**Note**: v0.50.0 uses milliseconds for all timeout parameters (`timeout_ms`, not `timeout`).

---

## Using LLM Adapters

### OpenAI Example

```python
import asyncio
from agenkit import Message
from agenkit.adapters.llm import OpenAILLM


async def main():
    # Initialize LLM (validates parameters at construction)
    llm = OpenAILLM(
        api_key="your-api-key",  # Or set OPENAI_API_KEY env var
        model="gpt-4-turbo",
        temperature=0.7,  # Validated: must be 0-2
        max_tokens=1024,  # Validated: must be > 0
    )

    # Create conversation
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is Agenkit?"),
    ]

    # Get completion
    response = await llm.complete(messages)
    print(response.content)

    # Stream response
    async for chunk in llm.stream(messages):
        print(chunk.content, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

### Anthropic Example

```python
from agenkit.adapters.llm import AnthropicLLM

llm = AnthropicLLM(
    api_key="your-api-key",  # Or set ANTHROPIC_API_KEY env var
    model="claude-3-5-sonnet-20241022",
    temperature=1.0,
    max_tokens=4096,
)
```

**Parameter Validation** (v0.50.0):
- `temperature`: 0.0 - 2.0 (validated at construction)
- `max_tokens`: > 0 (validated at construction)
- `top_p`: 0.0 - 1.0 (validated at construction)

Invalid values raise `ValueError` immediately.

---

## Common Patterns

Agenkit provides 18 core patterns for building AI agents. Here are three essential ones to get started:

### 1. Reflection Pattern

Agent reviews and improves its own output:

```python
from agenkit.patterns import ReflectionAgent
from agenkit.adapters.llm import OpenAILLM

async def main():
    llm = OpenAILLM(model="gpt-4-turbo")

    agent = ReflectionAgent(
        llm=llm,
        max_iterations=3,
        reflection_prompt="Review and improve this response:"
    )

    message = Message(role="user", content="Explain async/await")
    response = await agent.process(message)
    print(response.content)
```

### 2. ReAct Pattern

Agent reasons and acts iteratively:

```python
from agenkit.patterns import ReActAgent
from agenkit.tools import Tool, ToolResult

class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for information"

    @property
    def parameters(self) -> dict:
        return {
            "query": {"type": "string", "description": "Search query"}
        }

    async def execute(self, params: dict) -> ToolResult:  # v0.50.0: explicit params dict
        query = params["query"]
        # Simulate search
        return ToolResult(
            success=True,
            result=f"Search results for: {query}"
        )

async def main():
    llm = OpenAILLM(model="gpt-4-turbo")
    tools = [SearchTool()]

    agent = ReActAgent(llm=llm, tools=tools, max_iterations=5)

    message = Message(role="user", content="What's the weather in Paris?")
    response = await agent.process(message)
    print(response.content)
```

**Breaking Change (v0.50.0)**: `Tool.execute()` now takes explicit `params: dict` instead of `**kwargs`.

### 3. Sequential Pattern

Chain multiple agents:

```python
from agenkit.patterns import SequentialAgent

async def main():
    # Create agent pipeline
    agent = SequentialAgent(agents=[
        ResearchAgent(),
        SummarizerAgent(),
        EditorAgent(),
    ])

    message = Message(role="user", content="Research AI safety")
    final_response = await agent.process(message)
    print(final_response.content)
```

**See all 18 patterns**: Refer to the accompanying book and `docs/PATTERNS.md`

---

## Observability

### Basic Tracing with OpenTelemetry

```python
from agenkit.observability import configure_observability

# Configure OpenTelemetry
configure_observability(
    service_name="my-agent-service",
    exporter_type="jaeger",
    jaeger_endpoint="http://localhost:14268/api/traces",
)

# Your agent automatically gets:
# - Span creation for each process() call
# - W3C Trace Context propagation
# - LLM call tracing
# - Error tracking
```

### View Traces in Jaeger

```bash
# Start Jaeger (Docker)
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest

# Open UI
open http://localhost:16686
```

---

## Advanced Features

### 1. Memory Hierarchy

```python
from agenkit.memory import MemoryHierarchy, WorkingMemory, LongTermMemory

memory = MemoryHierarchy(
    working=WorkingMemory(capacity=10),
    long_term=LongTermMemory(storage_path="./memory.db"),
)

agent = ConversationalAgent(memory=memory)
```

### 2. Budget Tracking

```python
from agenkit.budget import BudgetTracker

tracker = BudgetTracker(max_cost_usd=10.0)

agent = BudgetAwareAgent(llm=llm, budget=tracker)
```

### 3. Safety Framework

```python
from agenkit.safety import ContentFilter, RateLimiter

agent = SafeAgent(
    llm=llm,
    content_filter=ContentFilter(block_pii=True),
    rate_limiter=RateLimiter(rate=10, max_wait_ms=30000),
)
```

---

## Common Pitfalls

### 1. Timeout Units (v0.50.0 Breaking Change)

```python
# WRONG (v0.49.0):
TimeoutDecorator(agent=agent, timeout=30.0)  # seconds

# CORRECT (v0.50.0):
TimeoutDecorator(agent=agent, timeout_ms=30000)  # milliseconds
```

### 2. Tool Execution Signature (v0.50.0 Breaking Change)

```python
# WRONG (v0.49.0):
async def execute(self, **kwargs) -> ToolResult:
    query = kwargs.get("query")

# CORRECT (v0.50.0):
async def execute(self, params: dict) -> ToolResult:
    query = params["query"]
```

### 3. Parameter Validation

```python
# This raises ValueError immediately (v0.50.0):
llm = OpenAILLM(temperature=3.0)  # ❌ ValueError: temperature must be 0-2

# Valid range:
llm = OpenAILLM(temperature=0.7)  # ✅ OK
```

### 4. Using uv for All Operations

```bash
# WRONG:
python script.py
pytest tests/

# CORRECT:
uv run python script.py
uv run pytest tests/
```

---

## Next Steps

1. **Explore Patterns**: See the accompanying book and `docs/PATTERNS.md` for all 18 patterns
2. **Read Architecture**: `ARCHITECTURE.md` explains design principles
3. **Check Examples**: `examples/python/` has 27+ production examples
4. **API Reference**: Coming soon in `docs/api-reference/python/`
5. **Migration Guide**: See `docs/MIGRATION_v0.50.0.md` for breaking changes

---

## Quick Reference

```python
# Core imports
from agenkit import Agent, Message

# Middleware
from agenkit.middleware import (
    RetryDecorator,
    TimeoutDecorator,
    CircuitBreakerDecorator,
    RateLimiterDecorator,
)

# LLM adapters
from agenkit.adapters.llm import OpenAILLM, AnthropicLLM, OllamaLLM

# Patterns
from agenkit.patterns import (
    ReflectionAgent,
    ReActAgent,
    SequentialAgent,
    ParallelAgent,
)

# Tools
from agenkit.tools import Tool, ToolResult

# Observability
from agenkit.observability import configure_observability

# Memory
from agenkit.memory import MemoryHierarchy, WorkingMemory

# Safety
from agenkit.safety import ContentFilter, RateLimiter
```

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026

For help: Open an issue at https://github.com/yourusername/agenkit/issues
