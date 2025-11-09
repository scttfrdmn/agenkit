# agenkit API Documentation

**Version:** 0.1.0
**Status:** Week 1 - Core Implementation

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
  - [Message](#message)
  - [ToolResult](#toolresult)
  - [Agent](#agent)
  - [Tool](#tool)
  - [Patterns](#patterns)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

agenkit is the foundation layer for AI agents. It provides minimal, perfect primitives for agent communication and composition.

**Design Philosophy:**
- Interfaces, not implementations
- Primitives, not opinions
- Extensible, not prescriptive
- Foundation, not solution

## Installation

```bash
pip install -e ".[dev]"
```

## Core Concepts

### 1. Messages

Messages are immutable data containers for agent communication. They use a flexible `content` field that can hold any type.

```python
from agenkit import Message

msg = Message(
    role="user",
    content="What's the weather?",
    metadata={"source": "web"}
)
```

### 2. Agents

Agents are async functions wrapped in an interface. The only required method is `process()`.

```python
from agenkit import Agent, Message

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my_agent"

    async def process(self, message: Message) -> Message:
        # Your logic here
        return Message(role="agent", content="response")
```

### 3. Tools

Tools are capabilities that agents can use. They execute actions and return results.

```python
from agenkit import Tool, ToolResult

class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web"

    async def execute(self, query: str) -> ToolResult:
        results = await search_api(query)
        return ToolResult(success=True, data=results)
```

### 4. Patterns

Patterns compose agents into workflows. Three core patterns:
- **Sequential**: Pipeline (agent1 → agent2 → agent3)
- **Parallel**: Fan-out (all agents process same input)
- **Router**: Conditional dispatch (route to one agent)

---

## API Reference

### Message

**Immutable data container for agent communication.**

```python
@dataclass(frozen=True)
class Message:
    role: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

#### Attributes

- **role** (`str`): Who sent the message ("user", "agent", "system", etc.)
- **content** (`Any`): Message payload (string, dict, list, or any type)
- **metadata** (`dict[str, Any]`): Extension point for custom data
- **timestamp** (`datetime`): When the message was created (UTC)

#### Validation

- `role` cannot be empty (raises `ValueError`)
- Messages are immutable (frozen dataclass)

#### Examples

```python
# Simple text message
msg = Message(role="user", content="Hello")

# Structured content
msg = Message(
    role="agent",
    content={"text": "response", "confidence": 0.95}
)

# With metadata
msg = Message(
    role="user",
    content="query",
    metadata={"source": "api", "session_id": "123"}
)
```

---

### ToolResult

**Result container for tool execution.**

```python
@dataclass(frozen=True)
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### Attributes

- **success** (`bool`): Whether execution succeeded
- **data** (`Any`): Result data (if successful)
- **error** (`Optional[str]`): Error message (if failed)
- **metadata** (`dict[str, Any]`): Extension point

#### Validation

- Failed results (`success=False`) **must** have an `error` message

#### Examples

```python
# Success
result = ToolResult(
    success=True,
    data={"results": [1, 2, 3]}
)

# Failure
result = ToolResult(
    success=False,
    error="Connection timeout"
)

# With metadata
result = ToolResult(
    success=True,
    data=response,
    metadata={"cache_hit": True, "latency_ms": 45}
)
```

---

### Agent

**Abstract base class for agents.**

```python
class Agent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        pass

    @abstractmethod
    async def process(self, message: Message) -> Message:
        """Process a message and return a response."""
        pass

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream response messages (optional)."""
        raise NotImplementedError

    @property
    def capabilities(self) -> list[str]:
        """What this agent can do (optional)."""
        return []

    def unwrap(self) -> Any:
        """Return native object for interop (optional)."""
        return self
```

#### Required Methods

**`name`** (property)
- Returns unique identifier for the agent
- Used for logging, debugging, and routing

**`process(message: Message) -> Message`** (async)
- Core processing method
- Takes input message, returns output message
- Can raise exceptions (caller handles errors)

#### Optional Methods

**`stream(message: Message) -> AsyncIterator[Message]`** (async generator)
- For streaming responses (e.g., LLM streaming)
- Default implementation raises `NotImplementedError`
- Override if your agent supports streaming

**`capabilities`** (property)
- Returns list of capability strings
- Used for introspection and routing
- Default: empty list

**`unwrap() -> Any`**
- Return native object for framework interop
- Default: returns `self`
- Override if wrapping external agents

#### Examples

**Basic Agent:**

```python
class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"Echo: {message.content}"
        )
```

**Agent with Capabilities:**

```python
class SearchAgent(Agent):
    @property
    def name(self) -> str:
        return "search"

    @property
    def capabilities(self) -> list[str]:
        return ["web_search", "knowledge_retrieval"]

    async def process(self, message: Message) -> Message:
        query = str(message.content)
        results = await self.search(query)
        return Message(role="agent", content=results)

    async def search(self, query: str) -> dict:
        # Implementation
        pass
```

**Streaming Agent:**

```python
class LLMAgent(Agent):
    @property
    def name(self) -> str:
        return "llm"

    async def process(self, message: Message) -> Message:
        # Non-streaming response
        full_response = await self.generate(message.content)
        return Message(role="agent", content=full_response)

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        # Streaming response
        async for chunk in self.generate_stream(message.content):
            yield Message(role="agent", content=chunk)
```

---

### Tool

**Abstract base class for tools.**

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this tool does."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        pass

    @property
    def parameters_schema(self) -> Optional[dict[str, Any]]:
        """JSON Schema for parameters (optional)."""
        return None

    async def validate(self, **kwargs: Any) -> bool:
        """Validate parameters before execution (optional)."""
        return True
```

#### Required Methods

**`name`** (property)
- Unique tool identifier
- Used by agents to call tools

**`description`** (property)
- Human-readable description
- Used for LLM tool selection

**`execute(**kwargs) -> ToolResult`** (async)
- Execute the tool with given parameters
- Returns `ToolResult` (success or failure)

#### Optional Methods

**`parameters_schema`** (property)
- JSON Schema describing parameters
- Used for validation and documentation
- Default: `None`

**`validate(**kwargs) -> bool`** (async)
- Pre-execution validation
- Default: always returns `True`

#### Examples

**Simple Tool:**

```python
class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform basic math operations"

    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        try:
            if operation == "add":
                result = a + b
            elif operation == "multiply":
                result = a * b
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )

            return ToolResult(success=True, data={"result": result})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

**Tool with Schema:**

```python
class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web for information"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }

    async def validate(self, **kwargs: Any) -> bool:
        query = kwargs.get("query", "")
        return len(query) > 0

    async def execute(self, query: str, limit: int = 10) -> ToolResult:
        if not await self.validate(query=query, limit=limit):
            return ToolResult(success=False, error="Invalid query")

        results = await self._search_api(query, limit)
        return ToolResult(success=True, data=results)
```

---

### Patterns

#### SequentialPattern

**Execute agents in sequence (pipeline).**

```python
class SequentialPattern(Agent):
    def __init__(
        self,
        agents: list[Agent],
        name: str = "sequential",
        before_agent: Optional[Callable[[Agent, Message], None]] = None,
        after_agent: Optional[Callable[[Agent, Message], None]] = None,
    ) -> None:
```

**Parameters:**
- `agents`: List of agents to execute in order
- `name`: Pattern identifier (default: "sequential")
- `before_agent`: Hook called before each agent (optional)
- `after_agent`: Hook called after each agent (optional)

**Behavior:**
- Executes agents one after another
- Output of agent N becomes input of agent N+1
- Short-circuits on error (stops at first failure)
- Hooks called for each agent if provided

**Methods:**
- `process(message)`: Execute the pipeline
- `capabilities`: Combined capabilities of all agents
- `unwrap()`: Returns list of agents

**Example:**

```python
from agenkit import SequentialPattern

# Create pipeline: validate → process → format
pipeline = SequentialPattern([
    validator_agent,
    processor_agent,
    formatter_agent
])

result = await pipeline.process(message)
```

**With Hooks:**

```python
def log_before(agent: Agent, message: Message) -> None:
    print(f"Starting {agent.name}")

def log_after(agent: Agent, message: Message) -> None:
    print(f"Finished {agent.name}")

pipeline = SequentialPattern(
    agents=[agent1, agent2, agent3],
    before_agent=log_before,
    after_agent=log_after
)
```

**Performance:**
- Overhead: ~3-8% (microsecond-level)
- No parallelism (sequential by design)

---

#### ParallelPattern

**Execute agents concurrently (fan-out).**

```python
class ParallelPattern(Agent):
    def __init__(
        self,
        agents: list[Agent],
        aggregator: Optional[Callable[[list[Message]], Message]] = None,
        name: str = "parallel",
    ) -> None:
```

**Parameters:**
- `agents`: List of agents to execute concurrently
- `aggregator`: Function to combine results (optional)
- `name`: Pattern identifier (default: "parallel")

**Behavior:**
- All agents receive the **same** input message
- Executes concurrently using `asyncio.gather`
- If any agent fails, all are cancelled
- Results combined using aggregator function

**Default Aggregator:**
- Returns first result
- Stores all results in `metadata["parallel_results"]`

**Methods:**
- `process(message)`: Execute all agents in parallel
- `capabilities`: Combined capabilities of all agents
- `unwrap()`: Returns list of agents

**Example:**

```python
from agenkit import ParallelPattern

# Run multiple agents concurrently
parallel = ParallelPattern([
    search_agent,
    knowledge_agent,
    memory_agent
])

result = await parallel.process(message)

# Access all results
all_results = result.metadata["parallel_results"]
```

**Custom Aggregator:**

```python
def combine_results(messages: list[Message]) -> Message:
    # Combine content from all messages
    combined = "\n".join(msg.content for msg in messages)
    return Message(role="agent", content=combined)

parallel = ParallelPattern(
    agents=[agent1, agent2, agent3],
    aggregator=combine_results
)
```

**Performance:**
- Overhead: ~2-4% (microsecond-level)
- True parallelism (bounded by slowest agent)
- Memory: O(n) where n = number of agents

---

#### RouterPattern

**Route to one agent based on condition.**

```python
class RouterPattern(Agent):
    def __init__(
        self,
        router: Callable[[Message], str],
        handlers: dict[str, Agent],
        default: Optional[Agent] = None,
        name: str = "router",
    ) -> None:
```

**Parameters:**
- `router`: Function that returns handler key for a message
- `handlers`: Map of handler keys to agents
- `default`: Default agent if router returns unknown key (optional)
- `name`: Pattern identifier (default: "router")

**Behavior:**
- Router function inspects message and returns key
- Looks up agent in handlers dict
- If key not found, uses default (if provided)
- If no default, raises `KeyError`

**Methods:**
- `process(message)`: Route and execute
- `capabilities`: Combined capabilities of all handlers
- `unwrap()`: Returns handlers dict

**Example:**

```python
from agenkit import RouterPattern

def route_by_content(message: Message) -> str:
    content = str(message.content).lower()
    if "code" in content:
        return "code_agent"
    elif "search" in content:
        return "search_agent"
    else:
        return "general_agent"

router = RouterPattern(
    router=route_by_content,
    handlers={
        "code_agent": code_specialist,
        "search_agent": search_specialist,
        "general_agent": general_agent
    }
)

result = await router.process(message)
```

**With Default:**

```python
router = RouterPattern(
    router=route_function,
    handlers={"handler1": agent1, "handler2": agent2},
    default=fallback_agent  # Used for unknown keys
)
```

**Performance:**
- Overhead: ~8-12% (microsecond-level)
- Only one agent executes
- O(1) routing decision

---

## Examples

### Example 1: Simple Agent

```python
from agenkit import Agent, Message

class GreetingAgent(Agent):
    @property
    def name(self) -> str:
        return "greeting"

    async def process(self, message: Message) -> Message:
        name = message.content
        greeting = f"Hello, {name}!"
        return Message(role="agent", content=greeting)

# Usage
agent = GreetingAgent()
msg = Message(role="user", content="Alice")
response = await agent.process(msg)
print(response.content)  # "Hello, Alice!"
```

### Example 2: Sequential Pipeline

```python
from agenkit import Agent, Message, SequentialPattern

class UppercaseAgent(Agent):
    @property
    def name(self) -> str:
        return "uppercase"

    async def process(self, message: Message) -> Message:
        upper = str(message.content).upper()
        return Message(role="agent", content=upper)

class ExclamationAgent(Agent):
    @property
    def name(self) -> str:
        return "exclamation"

    async def process(self, message: Message) -> Message:
        excited = f"{message.content}!"
        return Message(role="agent", content=excited)

# Create pipeline
pipeline = SequentialPattern([
    UppercaseAgent(),
    ExclamationAgent()
])

msg = Message(role="user", content="hello")
result = await pipeline.process(msg)
print(result.content)  # "HELLO!"
```

### Example 3: Parallel Processing

```python
from agenkit import ParallelPattern, Message

# Run multiple analyzers concurrently
def combine_analyses(messages: list[Message]) -> Message:
    results = {}
    for msg in messages:
        results.update(msg.content)
    return Message(role="agent", content=results)

parallel = ParallelPattern(
    agents=[
        sentiment_analyzer,
        entity_extractor,
        topic_classifier
    ],
    aggregator=combine_analyses
)

msg = Message(role="user", content="Analyze this text")
result = await parallel.process(msg)
# result.content contains combined analysis
```

### Example 4: Content-Based Routing

```python
from agenkit import RouterPattern, Message

def route_by_intent(message: Message) -> str:
    content = str(message.content).lower()

    if any(word in content for word in ["weather", "forecast"]):
        return "weather"
    elif any(word in content for word in ["news", "headlines"]):
        return "news"
    else:
        return "general"

router = RouterPattern(
    router=route_by_intent,
    handlers={
        "weather": weather_agent,
        "news": news_agent,
        "general": general_agent
    }
)

# Routes to weather_agent
msg1 = Message(role="user", content="What's the weather?")
response1 = await router.process(msg1)

# Routes to news_agent
msg2 = Message(role="user", content="Latest headlines")
response2 = await router.process(msg2)
```

### Example 5: Tool Usage

```python
from agenkit import Tool, ToolResult

class WeatherTool(Tool):
    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Get current weather for a location"

    async def execute(self, location: str) -> ToolResult:
        try:
            weather_data = await fetch_weather(location)
            return ToolResult(success=True, data=weather_data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

# Usage in agent
class WeatherAgent(Agent):
    def __init__(self):
        self.tool = WeatherTool()

    @property
    def name(self) -> str:
        return "weather_agent"

    async def process(self, message: Message) -> Message:
        location = message.content
        result = await self.tool.execute(location=location)

        if result.success:
            content = f"Weather: {result.data}"
        else:
            content = f"Error: {result.error}"

        return Message(role="agent", content=content)
```

### Example 6: Pattern Composition

```python
from agenkit import SequentialPattern, ParallelPattern, RouterPattern

# Compose patterns of patterns
# Sequential [ Parallel [ ... ], Router { ... } ]

# Parallel analysis step
analysis = ParallelPattern(
    agents=[sentiment_agent, entity_agent],
    aggregator=combine_results
)

# Router for next step
def route_by_sentiment(msg: Message) -> str:
    sentiment = msg.metadata.get("sentiment", "neutral")
    return "positive" if sentiment > 0.5 else "negative"

router = RouterPattern(
    router=route_by_sentiment,
    handlers={
        "positive": positive_handler,
        "negative": negative_handler
    }
)

# Combine into pipeline
pipeline = SequentialPattern([analysis, router])

result = await pipeline.process(message)
```

---

## Best Practices

### 1. Message Content

**Use structured content for complex data:**

```python
# Good: Structured content
Message(
    role="agent",
    content={
        "answer": "Paris",
        "confidence": 0.95,
        "sources": ["wiki", "britannica"]
    }
)

# Also good: Simple content for simple cases
Message(role="user", content="What is the capital of France?")
```

### 2. Metadata Usage

**Use metadata for cross-cutting concerns:**

```python
# Good: Metadata for tracing, monitoring
Message(
    role="user",
    content="query",
    metadata={
        "trace_id": "abc123",
        "user_id": "user_456",
        "session_id": "sess_789"
    }
)
```

### 3. Error Handling

**Let errors propagate, handle at boundaries:**

```python
# Good: Let exceptions propagate
class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        result = await risky_operation()  # May raise
        return Message(role="agent", content=result)

# Handle at call site
try:
    result = await agent.process(message)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    # Handle appropriately
```

### 4. Tool Design

**Tools should be focused and composable:**

```python
# Good: Focused tool
class SearchTool(Tool):
    """Does one thing well: searches"""
    async def execute(self, query: str) -> ToolResult:
        ...

# Bad: Kitchen sink tool
class MegaTool(Tool):
    """Does everything: search, fetch, parse, analyze..."""
    async def execute(self, **kwargs: Any) -> ToolResult:
        ...
```

### 5. Streaming

**Only implement streaming if you need it:**

```python
# Good: Don't override stream() if not needed
class SimpleAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="response")
    # stream() raises NotImplementedError by default

# Good: Override when you have streaming
class LLMAgent(Agent):
    async def stream(self, message: Message) -> AsyncIterator[Message]:
        async for chunk in llm.stream(message.content):
            yield Message(role="agent", content=chunk)
```

### 6. Capabilities

**Use capabilities for routing and introspection:**

```python
class SpecializedAgent(Agent):
    @property
    def capabilities(self) -> list[str]:
        return ["code_generation", "python", "async"]

    async def process(self, message: Message) -> Message:
        ...

# Route based on capabilities
def find_agent(required: str, agents: list[Agent]) -> Optional[Agent]:
    for agent in agents:
        if required in agent.capabilities:
            return agent
    return None
```

### 7. Testing

**Test agents like pure functions:**

```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_echo_agent():
    agent = EchoAgent()

    msg = Message(role="user", content="test")
    result = await agent.process(msg)

    assert result.role == "agent"
    assert "test" in result.content
```

### 8. Performance

**Remember: microsecond overhead, negligible in production:**

```python
# Don't micro-optimize agent code
# The overhead is 0.0001-0.001ms per operation
# Your LLM calls are 100-1000ms
# Focus on correctness, not nanoseconds

class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Clear, correct code is better than premature optimization
        result = await llm.complete(message.content)  # ~100ms
        return Message(role="agent", content=result)
```

### 9. Unwrap for Interop

**Use unwrap() when integrating other frameworks:**

```python
class LangChainWrapper(Agent):
    def __init__(self, langchain_agent):
        self._agent = langchain_agent

    @property
    def name(self) -> str:
        return "langchain_wrapper"

    async def process(self, message: Message) -> Message:
        # Adapt agenkit → LangChain
        result = await self._agent.invoke(message.content)
        return Message(role="agent", content=result)

    def unwrap(self):
        # Return native LangChain agent
        return self._agent
```

---

## Type Safety

agenkit uses strict type checking (mypy strict mode):

```python
from agenkit import Agent, Message

# Type hints are enforced
class TypedAgent(Agent):
    @property
    def name(self) -> str:  # Must return str
        return "typed"

    async def process(self, message: Message) -> Message:  # Must return Message
        return Message(role="agent", content="response")

# IDE autocomplete and type checking work perfectly
msg: Message = Message(role="user", content="test")
result: Message = await agent.process(msg)
```

---

## Next Steps

- **Phase 2:** Protocol adapters (Python, Go, Rust)
- **Phase 3:** Framework reimplementations
- **Phase 4:** Documentation & tools
- **Phase 5:** Launch

For more information:
- [Vision Document](../AGENKIT_VISION.md)
- [Architecture](../ARCHITECTURE.md)
- [Examples](../examples/)
- [Benchmarks](../benchmarks/test_overhead.py)
