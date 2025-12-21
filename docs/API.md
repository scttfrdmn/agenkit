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

    def introspect(self) -> IntrospectionResult:
        """Examine agent's internal state, memory, and capabilities (optional)."""
        return IntrospectionResult(
            timestamp=datetime.now(timezone.utc),
            agent_name=self.name,
            capabilities=self.capabilities,
            memory_state=self._get_memory_state(),
            internal_state=self._get_internal_state(),
            metadata={},
        )

    def _get_memory_state(self) -> dict[str, Any] | None:
        """Get memory state for introspection (optional override)."""
        return None

    def _get_internal_state(self) -> dict[str, Any]:
        """Get agent-specific internal state (optional override)."""
        return {}

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

**`introspect() -> IntrospectionResult`**
- Examine agent's internal state, memory, and capabilities
- Returns snapshot of current state at call time
- Useful for debugging, monitoring, testing, and coordination
- Default implementation uses `_get_memory_state()` and `_get_internal_state()`
- Override for custom introspection behavior

**`_get_memory_state() -> dict[str, Any] | None`** (protected helper)
- Return agent's memory contents for introspection
- Default: `None` (no memory)
- Override if agent has memory state

**`_get_internal_state() -> dict[str, Any]`** (protected helper)
- Return agent-specific internal state for introspection
- Default: empty dict
- Override to expose counters, flags, configuration, etc.

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

**Agent with Introspection:**

```python
class StatefulAgent(Agent):
    def __init__(self):
        self.message_count = 0
        self.memory = []

    @property
    def name(self) -> str:
        return "stateful"

    @property
    def capabilities(self) -> list[str]:
        return ["stateful", "memory"]

    async def process(self, message: Message) -> Message:
        self.message_count += 1
        self.memory.append(message.content)
        return Message(
            role="agent",
            content=f"Processed message #{self.message_count}"
        )

    def _get_memory_state(self) -> dict[str, Any]:
        return {
            "recent_messages": self.memory[-5:],  # Last 5 messages
            "total_stored": len(self.memory)
        }

    def _get_internal_state(self) -> dict[str, Any]:
        return {
            "message_count": self.message_count,
            "has_memory": len(self.memory) > 0
        }

# Using introspection
agent = StatefulAgent()
await agent.process(Message(role="user", content="Hello"))

result = agent.introspect()
print(f"Agent: {result.agent_name}")
print(f"Capabilities: {result.capabilities}")
print(f"Messages processed: {result.internal_state['message_count']}")
print(f"Memory entries: {result.memory_state['total_stored']}")
```

**Introspection for Debugging:**

```python
def debug_agent_state(agent: Agent) -> None:
    """Debug helper to inspect agent state."""
    result = agent.introspect()

    print(f"\n=== Agent: {result.agent_name} ===")
    print(f"Timestamp: {result.timestamp}")
    print(f"Capabilities: {', '.join(result.capabilities)}")

    if result.memory_state:
        print(f"\nMemory State:")
        for key, value in result.memory_state.items():
            print(f"  {key}: {value}")

    if result.internal_state:
        print(f"\nInternal State:")
        for key, value in result.internal_state.items():
            print(f"  {key}: {value}")

    print("=" * 40)

# Use with any agent
debug_agent_state(my_agent)
```

---

### IntrospectionResult

**Data container for agent introspection results.**

```python
@dataclass(frozen=True)
class IntrospectionResult:
    timestamp: datetime
    agent_name: str
    capabilities: list[str]
    memory_state: dict[str, Any] | None
    internal_state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### Attributes

- **timestamp** (`datetime`): When the introspection snapshot was taken (UTC)
- **agent_name** (`str`): Name of the agent that was introspected
- **capabilities** (`list[str]`): List of capabilities this agent supports
- **memory_state** (`dict[str, Any] | None`): Agent's memory contents (None if no memory)
- **internal_state** (`dict[str, Any]`): Agent-specific internal state (counters, flags, config)
- **metadata** (`dict[str, Any]`): Extension point for additional information

#### Validation

- `agent_name` cannot be empty (raises `ValueError`)
- `capabilities` must be a list (raises `TypeError`)
- `internal_state` must be a dict (raises `TypeError`)
- `memory_state` must be dict or None (raises `TypeError`)

#### Use Cases

**Debugging:**
```python
# Inspect agent during development
result = agent.introspect()
print(f"Agent state at {result.timestamp}:")
print(f"  Name: {result.agent_name}")
print(f"  State: {result.internal_state}")
```

**Monitoring:**
```python
# Track agent health in production
def check_agent_health(agent: Agent) -> bool:
    result = agent.introspect()

    # Check if agent has processed recent messages
    if "last_activity" in result.internal_state:
        last_activity = result.internal_state["last_activity"]
        if (datetime.now() - last_activity).seconds > 300:
            return False  # No activity in 5 minutes

    return True
```

**Testing:**
```python
# Verify agent state in tests
async def test_agent_processes_messages():
    agent = MyAgent()

    # Check initial state
    result1 = agent.introspect()
    assert result1.internal_state["message_count"] == 0

    # Process message
    await agent.process(Message(role="user", content="test"))

    # Verify state changed
    result2 = agent.introspect()
    assert result2.internal_state["message_count"] == 1
```

**Coordination:**
```python
# Multi-agent coordination based on capabilities
def route_to_capable_agent(
    message: Message,
    agents: list[Agent]
) -> Agent:
    """Route message to agent with required capability."""
    required_capability = message.metadata.get("requires")

    for agent in agents:
        result = agent.introspect()
        if required_capability in result.capabilities:
            return agent

    raise ValueError(f"No agent has capability: {required_capability}")
```

#### Distinction from Reflection Pattern

**Introspection** (this feature):
- **What it does**: Examines current state ("What do I know?")
- **When to use**: Debugging, monitoring, testing, coordination
- **Returns**: Snapshot of current internal state
- **Example**: `agent.introspect()` → current memory, counters, config

**Reflection** (pattern):
- **What it does**: Analyzes past performance ("How did I do?")
- **When to use**: Self-improvement, quality assessment
- **Returns**: Critique of previous outputs
- **Example**: Reflection agent analyzes response quality and suggests improvements

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

agenkit provides 11 production-ready patterns for agent composition. Patterns are organized into four categories:

**Composition Patterns** (Sequential, Parallel)
- Basic building blocks for agent workflows
- Combine multiple agents into pipelines or concurrent execution

**Enhancement Patterns** (Reflection, ReAct, Planning)
- Improve agent quality and reasoning
- Add self-correction, tool usage, and planning capabilities

**Specialized Patterns** (Task, Conversational, Agents as Tools)
- Purpose-built for specific use cases
- Task execution, dialogue management, agent orchestration

**Advanced Patterns** (Autonomous, Multiagent, Memory Hierarchy)
- Complex multi-agent systems
- Goal-driven behavior, collaboration, long-term memory

---

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

#### ReflectionPattern

**Iterative self-improvement through reflection.**

```python
class ReflectionPattern(Agent):
    def __init__(
        self,
        actor: Agent,
        reflector: Agent,
        max_iterations: int = 3,
        improvement_threshold: float = 0.0,
        name: str = "reflection",
    ) -> None:
```

**Parameters:**
- `actor`: Agent that performs the task
- `reflector`: Agent that critiques and suggests improvements
- `max_iterations`: Maximum reflection iterations (default: 3)
- `improvement_threshold`: Stop if improvement below threshold (default: 0.0)
- `name`: Pattern identifier (default: "reflection")

**Behavior:**
- Actor generates initial response
- Reflector critiques the response
- Actor revises based on critique
- Repeats until max iterations or quality threshold met
- Returns final refined response

**Methods:**
- `process(message)`: Execute reflection loop
- `capabilities`: Combined capabilities of actor and reflector
- `unwrap()`: Returns tuple (actor, reflector)

**Example:**

```python
from agenkit.patterns import ReflectionPattern

# Create reflection agent
reflection = ReflectionPattern(
    actor=writer_agent,      # Generates content
    reflector=critic_agent,  # Provides feedback
    max_iterations=3
)

msg = Message.with_text("user", "Write a product description")
result = await reflection.process(msg)
# result contains refined output after multiple iterations
```

**With Custom Threshold:**

```python
reflection = ReflectionPattern(
    actor=coder_agent,
    reflector=reviewer_agent,
    max_iterations=5,
    improvement_threshold=0.1  # Stop if quality improvement < 10%
)
```

**Performance:**
- Overhead: ~5-10% per iteration
- Latency: N × actor_time (where N = iterations)
- Trade quality for speed by reducing max_iterations

---

#### ReActPattern

**Reasoning and Acting with tool usage.**

```python
class ReActPattern(Agent):
    def __init__(
        self,
        agent: Agent,
        tools: list[Tool],
        max_iterations: int = 5,
        name: str = "react",
    ) -> None:
```

**Parameters:**
- `agent`: LLM agent that reasons and decides actions
- `tools`: Available tools for the agent to use
- `max_iterations`: Maximum reasoning steps (default: 5)
- `name`: Pattern identifier (default: "react")

**Behavior:**
- Agent receives task and available tools
- Iteratively: thinks → acts → observes
- Can call tools to gather information or perform actions
- Stops when agent decides task is complete or max iterations reached
- Returns final answer with reasoning trace

**Methods:**
- `process(message)`: Execute ReAct loop
- `capabilities`: Agent capabilities plus tool names
- `unwrap()`: Returns tuple (agent, tools)

**Example:**

```python
from agenkit.patterns import ReActPattern
from agenkit import Tool

# Create tools
search = SearchTool()
calculator = CalculatorTool()

# Create ReAct agent
react = ReActPattern(
    agent=llm_agent,
    tools=[search, calculator],
    max_iterations=5
)

msg = Message.with_text("user", "What is the population of Tokyo times 2?")
result = await react.process(msg)
# Agent will: search for population → use calculator → answer
```

**Tool Schema:**

```python
class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web"

    async def execute(self, query: str) -> ToolResult:
        results = await web_search(query)
        return ToolResult(success=True, data=results)

react = ReActPattern(
    agent=llm_agent,
    tools=[SearchTool(), CalculatorTool(), WeatherTool()],
    max_iterations=10
)
```

**Performance:**
- Overhead: ~3-7% per iteration
- Latency depends on number of tool calls
- Each iteration includes LLM call + optional tool execution

---

#### PlanningPattern

**Multi-step task decomposition and execution.**

```python
class PlanningPattern(Agent):
    def __init__(
        self,
        planner: Agent,
        executor: Agent,
        max_steps: int = 10,
        replan_on_failure: bool = True,
        name: str = "planning",
    ) -> None:
```

**Parameters:**
- `planner`: Agent that creates execution plans
- `executor`: Agent that executes individual steps
- `max_steps`: Maximum plan steps (default: 10)
- `replan_on_failure`: Replan if step fails (default: True)
- `name`: Pattern identifier (default: "planning")

**Behavior:**
- Planner analyzes task and creates step-by-step plan
- Executor performs each step sequentially
- If step fails and replan_on_failure=True, planner adjusts plan
- Continues until all steps complete or max_steps reached
- Returns final result with execution trace

**Methods:**
- `process(message)`: Execute planning cycle
- `capabilities`: Combined capabilities of planner and executor
- `unwrap()`: Returns tuple (planner, executor)

**Example:**

```python
from agenkit.patterns import PlanningPattern

# Create planning agent
planning = PlanningPattern(
    planner=strategic_agent,  # Creates plans
    executor=action_agent,    # Executes steps
    max_steps=10,
    replan_on_failure=True
)

msg = Message.with_text("user", "Research and summarize AI developments in 2024")
result = await planning.process(msg)
# Planner creates: 1. Search for AI news 2. Filter 2024 3. Summarize
# Executor performs each step
```

**Plan Structure:**

```python
# Planner should return structured plan
class Planner(Agent):
    async def process(self, message: Message) -> Message:
        plan = {
            "steps": [
                {"action": "search", "params": {"query": "..."}},
                {"action": "filter", "params": {"year": 2024}},
                {"action": "summarize", "params": {}}
            ]
        }
        return Message.with_data("agent", plan)
```

**Performance:**
- Overhead: ~5-10%
- Latency: planning_time + (N × step_time)
- Replanning adds overhead but increases success rate

---

#### TaskPattern

**Execute specific, well-defined tasks.**

```python
class TaskPattern(Agent):
    def __init__(
        self,
        task_fn: Callable[[Message], Awaitable[Message]],
        name: str = "task",
        timeout: Optional[float] = None,
    ) -> None:
```

**Parameters:**
- `task_fn`: Async function that performs the task
- `name`: Task identifier (default: "task")
- `timeout`: Maximum execution time in seconds (optional)

**Behavior:**
- Wraps an async function as an Agent
- Executes function with timeout if specified
- Raises `TimeoutError` if execution exceeds timeout
- Simplest pattern for converting functions to agents

**Methods:**
- `process(message)`: Execute task function
- `capabilities`: Empty list (can be set via property)
- `unwrap()`: Returns task function

**Example:**

```python
from agenkit.patterns import TaskPattern

# Define task function
async def fetch_data(message: Message) -> Message:
    url = message.content["url"]
    data = await http_get(url)
    return Message.with_data("agent", data)

# Wrap as agent
task = TaskPattern(
    task_fn=fetch_data,
    name="data_fetcher",
    timeout=30.0
)

msg = Message.with_data("user", {"url": "https://api.example.com/data"})
result = await task.process(msg)
```

**Multiple Tasks:**

```python
# Create task agents for different operations
fetch_task = TaskPattern(fetch_data, name="fetcher")
process_task = TaskPattern(process_data, name="processor")
save_task = TaskPattern(save_data, name="saver")

# Compose into pipeline
pipeline = SequentialPattern([fetch_task, process_task, save_task])
```

**Performance:**
- Overhead: <1% (minimal wrapping)
- Timeout adds negligible overhead
- Direct function call performance

---

#### ConversationalPattern

**Multi-turn dialogue with context tracking.**

```python
class ConversationalPattern(Agent):
    def __init__(
        self,
        agent: Agent,
        max_history: int = 10,
        system_prompt: Optional[str] = None,
        name: str = "conversational",
    ) -> None:
```

**Parameters:**
- `agent`: Underlying agent for generating responses
- `max_history`: Maximum messages to keep in history (default: 10)
- `system_prompt`: Initial system message (optional)
- `name`: Pattern identifier (default: "conversational")

**Behavior:**
- Maintains conversation history across turns
- Appends user message to history
- Passes history to underlying agent
- Stores agent response in history
- Limits history to max_history messages (FIFO)

**Methods:**
- `process(message)`: Process message with context
- `get_history()`: Retrieve conversation history
- `clear_history()`: Reset conversation
- `capabilities`: Underlying agent capabilities
- `unwrap()`: Returns underlying agent

**Example:**

```python
from agenkit.patterns import ConversationalPattern

# Create conversational agent
chatbot = ConversationalPattern(
    agent=llm_agent,
    max_history=10,
    system_prompt="You are a helpful assistant."
)

# Multi-turn conversation
msg1 = Message.with_text("user", "What is Python?")
response1 = await chatbot.process(msg1)
print(response1.text)  # "Python is a programming language..."

msg2 = Message.with_text("user", "What are its main features?")
response2 = await chatbot.process(msg2)
# Agent has context from previous turn
print(response2.text)  # "Python's main features include..."

# Check history
history = chatbot.get_history()
print(f"Conversation has {len(history)} messages")

# Reset conversation
chatbot.clear_history()
```

**With System Prompt:**

```python
chatbot = ConversationalPattern(
    agent=llm_agent,
    max_history=20,
    system_prompt="""You are a Python expert.
    Provide concise, accurate answers with code examples."""
)
```

**Performance:**
- Overhead: ~2-5%
- Memory: O(max_history) messages
- History management is constant time

---

#### AgentsAsToolsPattern

**Use agents as tools for other agents.**

```python
class AgentsAsToolsPattern(Agent):
    def __init__(
        self,
        orchestrator: Agent,
        specialist_agents: dict[str, Agent],
        name: str = "agents_as_tools",
    ) -> None:
```

**Parameters:**
- `orchestrator`: Main agent that delegates tasks
- `specialist_agents`: Map of tool names to specialist agents
- `name`: Pattern identifier (default: "agents_as_tools")

**Behavior:**
- Orchestrator receives task
- Decides which specialist agent(s) to invoke
- Specialists are presented as "tools" to orchestrator
- Orchestrator delegates subtasks to specialists
- Combines specialist results into final answer

**Methods:**
- `process(message)`: Orchestrate task delegation
- `capabilities`: "orchestration" + all specialist capabilities
- `unwrap()`: Returns dict of specialist agents

**Example:**

```python
from agenkit.patterns import AgentsAsToolsPattern

# Create specialist agents
code_agent = CodeGeneratorAgent()
search_agent = SearchAgent()
calc_agent = CalculatorAgent()

# Create orchestrator
orchestrator = AgentsAsToolsPattern(
    orchestrator=coordinator_agent,
    specialist_agents={
        "code_generator": code_agent,
        "web_search": search_agent,
        "calculator": calc_agent
    }
)

msg = Message.with_text("user", "Find Python's release date and calculate years since")
result = await orchestrator.process(msg)
# Orchestrator will:
# 1. Use search_agent to find Python release date (1991)
# 2. Use calculator to compute 2024 - 1991 = 33 years
```

**Specialist as Tool Adapter:**

```python
# Specialists are wrapped as tools automatically
class SpecialistTool(Tool):
    def __init__(self, agent: Agent):
        self.agent = agent

    @property
    def name(self) -> str:
        return self.agent.name

    @property
    def description(self) -> str:
        # Generated from agent capabilities
        return f"Agent with capabilities: {self.agent.capabilities}"

    async def execute(self, **kwargs) -> ToolResult:
        msg = Message.with_data("orchestrator", kwargs)
        result = await self.agent.process(msg)
        return ToolResult(success=True, data=result.content)
```

**Performance:**
- Overhead: ~5-10%
- Latency depends on specialist complexity
- Efficient delegation avoids redundant work

---

#### AutonomousPattern

**Goal-driven autonomous agent.**

```python
class AutonomousPattern(Agent):
    def __init__(
        self,
        agent: Agent,
        tools: list[Tool],
        goal_evaluator: Callable[[Message, Message], float],
        max_iterations: int = 10,
        goal_threshold: float = 0.9,
        name: str = "autonomous",
    ) -> None:
```

**Parameters:**
- `agent`: LLM agent for reasoning and action selection
- `tools`: Available tools
- `goal_evaluator`: Function to evaluate progress (0.0-1.0)
- `max_iterations`: Maximum autonomous steps (default: 10)
- `goal_threshold`: Success threshold (default: 0.9)
- `name`: Pattern identifier (default: "autonomous")

**Behavior:**
- Agent pursues goal autonomously
- Each iteration: evaluates progress, plans next action, executes
- Uses tools to interact with environment
- Stops when goal_evaluator returns score ≥ goal_threshold
- Falls back to max_iterations if goal not achieved

**Methods:**
- `process(message)`: Execute autonomous goal pursuit
- `capabilities`: "autonomous" + agent capabilities + tool names
- `unwrap()`: Returns tuple (agent, tools)

**Example:**

```python
from agenkit.patterns import AutonomousPattern

def evaluate_goal(initial: Message, current: Message) -> float:
    """Evaluate how close we are to the goal."""
    goal = initial.metadata.get("goal")
    result = current.content
    # Custom evaluation logic
    if goal_achieved(result):
        return 1.0
    elif partial_progress(result):
        return 0.5
    else:
        return 0.0

autonomous = AutonomousPattern(
    agent=reasoning_agent,
    tools=[search, calculator, file_reader],
    goal_evaluator=evaluate_goal,
    max_iterations=10,
    goal_threshold=0.9
)

msg = Message.with_text(
    "user",
    "Research top 5 AI companies and create summary report",
    metadata={"goal": "comprehensive_report"}
)
result = await autonomous.process(msg)
# Agent autonomously:
# 1. Searches for AI companies
# 2. Gathers information on each
# 3. Creates structured report
# 4. Evaluates completeness
# 5. Continues until report is comprehensive
```

**Custom Goal Evaluator:**

```python
def research_evaluator(initial: Message, current: Message) -> float:
    """Evaluate research completeness."""
    required_sections = ["introduction", "methodology", "results", "conclusion"]
    result = current.content

    if not isinstance(result, dict):
        return 0.0

    completed = sum(1 for section in required_sections if section in result)
    return completed / len(required_sections)
```

**Performance:**
- Overhead: ~5-10% per iteration
- Highly variable latency (depends on goal complexity)
- Goal evaluator should be fast (< 1ms)

---

#### MultiagentPattern

**Collaborative multi-agent system.**

```python
class MultiagentPattern(Agent):
    def __init__(
        self,
        agents: list[Agent],
        collaboration_strategy: str = "sequential",
        aggregator: Optional[Callable[[list[Message]], Message]] = None,
        name: str = "multiagent",
    ) -> None:
```

**Parameters:**
- `agents`: List of agents in the system
- `collaboration_strategy`: How agents collaborate ("sequential", "parallel", "debate")
- `aggregator`: Function to combine agent outputs (optional)
- `name`: Pattern identifier (default: "multiagent")

**Collaboration Strategies:**
- **"sequential"**: Agents process in order (pipeline)
- **"parallel"**: All agents process simultaneously
- **"debate"**: Agents discuss and reach consensus

**Behavior:**
- Multiple agents work together on a task
- Strategy determines interaction pattern
- Aggregator combines results (if provided)
- Returns consolidated response

**Methods:**
- `process(message)`: Execute collaboration
- `capabilities`: Combined capabilities of all agents
- `unwrap()`: Returns list of agents

**Example - Parallel Collaboration:**

```python
from agenkit.patterns import MultiagentPattern

# Create expert agents
finance_expert = FinanceAgent()
legal_expert = LegalAgent()
tech_expert = TechAgent()

def combine_expert_opinions(messages: list[Message]) -> Message:
    """Combine insights from all experts."""
    opinions = [msg.content for msg in messages]
    consolidated = {
        "finance": opinions[0],
        "legal": opinions[1],
        "tech": opinions[2],
        "summary": synthesize(opinions)
    }
    return Message.with_data("agent", consolidated)

multiagent = MultiagentPattern(
    agents=[finance_expert, legal_expert, tech_expert],
    collaboration_strategy="parallel",
    aggregator=combine_expert_opinions
)

msg = Message.with_text("user", "Analyze this startup investment opportunity")
result = await multiagent.process(msg)
# All experts analyze simultaneously, results combined
```

**Example - Debate Strategy:**

```python
def debate_aggregator(messages: list[Message]) -> Message:
    """Agents debate until consensus."""
    # Implementation of debate logic
    # Agents exchange arguments iteratively
    # Continue until agreement threshold reached
    pass

multiagent = MultiagentPattern(
    agents=[agent1, agent2, agent3],
    collaboration_strategy="debate",
    aggregator=debate_aggregator
)
```

**Performance:**
- Sequential: Sum of agent latencies
- Parallel: Max of agent latencies
- Debate: Highly variable (depends on consensus time)

---

#### MemoryHierarchyPattern

**Multi-tiered memory management.**

```python
class MemoryHierarchyPattern(Agent):
    def __init__(
        self,
        agent: Agent,
        short_term_size: int = 10,
        long_term_size: int = 100,
        memory_strategy: str = "importance",
        name: str = "memory_hierarchy",
    ) -> None:
```

**Parameters:**
- `agent`: Underlying agent
- `short_term_size`: Short-term memory capacity (default: 10)
- `long_term_size`: Long-term memory capacity (default: 100)
- `memory_strategy`: How to manage memory ("importance", "recency", "semantic")
- `name`: Pattern identifier (default: "memory_hierarchy")

**Memory Tiers:**
- **Short-term**: Recent messages (FIFO)
- **Long-term**: Important/relevant messages (scored)
- **Working**: Current conversation context

**Behavior:**
- Maintains hierarchical memory system
- Short-term memory stores recent interactions
- Important messages promoted to long-term memory
- Memory retrieval based on relevance and recency
- Agent processes with appropriate memory context

**Methods:**
- `process(message)`: Process with memory context
- `get_short_term_memory()`: Retrieve recent memory
- `get_long_term_memory()`: Retrieve important memory
- `clear_memory()`: Reset all memory tiers
- `capabilities`: Underlying agent capabilities
- `unwrap()`: Returns underlying agent

**Example:**

```python
from agenkit.patterns import MemoryHierarchyPattern

# Create agent with memory hierarchy
memory_agent = MemoryHierarchyPattern(
    agent=llm_agent,
    short_term_size=10,
    long_term_size=100,
    memory_strategy="importance"
)

# Conversation with memory
msg1 = Message.with_text("user", "My name is Alice")
await memory_agent.process(msg1)  # Stored in short-term

msg2 = Message.with_text("user", "What's the weather?")
await memory_agent.process(msg2)

# Many messages later...
msg_n = Message.with_text("user", "What's my name?")
response = await memory_agent.process(msg_n)
# Agent retrieves "My name is Alice" from long-term memory
print(response.text)  # "Your name is Alice"
```

**Memory Strategies:**

```python
# Importance-based: Score messages and keep important ones
memory_agent = MemoryHierarchyPattern(
    agent=llm_agent,
    memory_strategy="importance"
)

# Recency-based: Keep most recent messages
memory_agent = MemoryHierarchyPattern(
    agent=llm_agent,
    memory_strategy="recency"
)

# Semantic-based: Keep semantically relevant messages
memory_agent = MemoryHierarchyPattern(
    agent=llm_agent,
    memory_strategy="semantic"
)
```

**Custom Importance Scoring:**

```python
def custom_importance_scorer(message: Message) -> float:
    """Score message importance (0.0-1.0)."""
    content = str(message.content).lower()

    # High importance: personal information, preferences
    if any(word in content for word in ["my name", "i am", "i like"]):
        return 0.9

    # Medium importance: questions, commands
    if "?" in content or any(word in content for word in ["please", "can you"]):
        return 0.6

    # Low importance: small talk
    return 0.3

memory_agent = MemoryHierarchyPattern(
    agent=llm_agent,
    memory_strategy="importance",
    importance_scorer=custom_importance_scorer
)
```

**Performance:**
- Overhead: ~3-7%
- Memory retrieval: O(log n) with indexing
- Space: O(short_term_size + long_term_size)

---

#### FallbackPattern

**Sequential retry with automatic failover.**

```python
class FallbackPattern(Agent):
    def __init__(
        self,
        agents: list[Agent],
        name: str = "fallback",
    ) -> None:
```

**Parameters:**
- `agents`: List of agents to try in order (primary, fallback1, fallback2, ...)
- `name`: Pattern identifier (default: "fallback")

**Behavior:**
- Tries agents sequentially until one succeeds
- Returns first successful response immediately
- If all agents fail, raises error with all failure details
- Adds metadata about which agent succeeded and attempts made

**Methods:**
- `process(message)`: Try agents until success
- `capabilities`: Combined capabilities of all agents
- `unwrap()`: Returns list of agents

**Example:**

```python
from agenkit.patterns import FallbackPattern

# Multi-provider LLM fallback
fallback = FallbackPattern([
    openai_agent,      # Try first (fastest/best)
    anthropic_agent,   # Fallback if OpenAI fails
    ollama_agent       # Last resort (local/free)
])

result = await fallback.process(message)

# Check which agent was used
print(result.metadata["fallback_success_agent"])  # "anthropic_agent"
print(result.metadata["fallback_attempts"])  # 2
```

**With Recovery Function:**

```python
from agenkit.patterns import WithRecovery

# Add graceful error handling
agent_with_recovery = WithRecovery(
    agent=primary_agent,
    recovery=lambda ctx, msg, err: Message.with_text(
        "assistant",
        "Service temporarily unavailable. Please try again."
    )
)

result = await agent_with_recovery.process(message)
# Always returns a response, even if agent fails
```

**Performance:**
- Best case: O(first agent) - immediate success
- Worst case: O(sum of all agents) - all fail
- Early termination on first success

---

#### SupervisorPattern

**Oversee worker execution with quality control.**

```python
class SupervisorPattern(Agent):
    def __init__(
        self,
        supervisor: Agent,
        workers: list[Agent],
        require_approval: bool = False,
        max_revisions: int = 3,
        name: str = "supervisor",
    ) -> None:
```

**Parameters:**
- `supervisor`: Agent that delegates and reviews work
- `workers`: List of worker agents
- `require_approval`: Whether supervisor must approve all outputs (default: False)
- `max_revisions`: Maximum revision cycles (default: 3)
- `name`: Pattern identifier (default: "supervisor")

**Behavior:**
- Supervisor analyzes task and delegates to workers
- Workers execute assigned subtasks
- Supervisor reviews worker outputs
- Can request revisions if quality insufficient
- Returns final approved result

**Methods:**
- `process(message)`: Supervised execution
- `get_workers()`: Get worker agents
- `get_supervisor()`: Get supervisor agent
- `capabilities`: Combined worker capabilities

**Example:**

```python
from agenkit.patterns import SupervisorPattern

# Quality-controlled workflow
supervisor = SupervisorPattern(
    supervisor=qa_agent,
    workers=[analyst_agent, writer_agent],
    require_approval=True,
    max_revisions=2
)

result = await supervisor.process(task)

# Metadata shows supervision details
print(result.metadata["supervisor_delegations"])  # Which workers used
print(result.metadata["supervisor_revisions"])  # Revision count
print(result.metadata["supervisor_approved"])  # True/False
```

**Performance:**
- Latency: supervisor_time + worker_times + review_time
- Overhead: ~20-40% due to review process
- Quality improvement: Significant

---

#### HumanInLoopPattern

**Human approval for safety-critical decisions.**

```python
class HumanInLoopPattern(Agent):
    def __init__(
        self,
        agent: Agent,
        approval_callback: Callable[[str, dict], tuple[bool, str]],
        require_approval_for: list[str] = ["all"],
        timeout: Optional[float] = None,
        name: str = "human_in_loop",
    ) -> None:
```

**Parameters:**
- `agent`: Underlying agent
- `approval_callback`: Function to request human approval
- `require_approval_for`: Actions requiring approval (["all"], ["tool_calls"], ["final_answer"])
- `timeout`: Approval timeout in seconds (default: None)
- `name`: Pattern identifier (default: "human_in_loop")

**Approval Callback Signature:**
```python
def approval_callback(action: str, context: dict) -> tuple[bool, str]:
    """
    Args:
        action: Proposed action description
        context: Action context and details

    Returns:
        (approved: bool, feedback: str)
    """
```

**Behavior:**
- Agent proposes action
- System requests human approval via callback
- Execution blocks until approval received
- If approved, action executes
- If rejected, agent revises or cancels

**Methods:**
- `process(message)`: Process with human gates
- `capabilities`: Underlying agent capabilities plus "human-approval"
- `unwrap()`: Returns underlying agent

**Example:**

```python
from agenkit.patterns import HumanInLoopPattern

def financial_approval(action: str, context: dict) -> tuple[bool, str]:
    """Human reviews financial transactions."""
    print(f"Approval required: {action}")
    print(f"Details: {context}")

    response = input("Approve? (y/n): ")
    if response.lower() == 'y':
        return True, "Approved"
    else:
        reason = input("Rejection reason: ")
        return False, f"Rejected: {reason}"

# Wrap financial agent with human approval
safe_agent = HumanInLoopPattern(
    agent=financial_agent,
    approval_callback=financial_approval,
    require_approval_for=["all"],
    timeout=300.0  # 5-minute timeout
)

# Every action requires human approval
result = await safe_agent.process(task)
```

**Performance:**
- Latency: agent_time + human_response_time
- Throughput: Limited by human availability
- Use cases: Compliance, safety-critical, high-stakes decisions

---

#### OrchestrationPattern

**Complex workflow coordination with conditional routing.**

```python
class OrchestrationPattern(Agent):
    def __init__(
        self,
        agents: dict[str, Agent],
        workflow: WorkflowDefinition,
        name: str = "orchestration",
    ) -> None:
```

**Parameters:**
- `agents`: Dictionary mapping agent names to agent instances
- `workflow`: Workflow definition (stages, conditions, routing)
- `name`: Pattern identifier (default: "orchestration")

**Workflow Definition:**
```python
workflow = WorkflowDefinition({
    "stages": [
        {
            "name": "stage_name",
            "agents": ["agent1", "agent2"],  # From agents dict
            "execution": "parallel",  # or "sequential"
            "aggregation": "merge",  # How to combine results
            "condition": "prev_stage.result == 'success'",  # Optional
            "inputs": ["prev_stage1", "prev_stage2"]  # Optional
        }
    ]
})
```

**Behavior:**
- Executes workflow stages in order
- Supports parallel and sequential execution per stage
- Conditional routing based on previous results
- Sophisticated result aggregation
- State machine-like coordination

**Methods:**
- `process(message)`: Execute workflow
- `get_workflow()`: Get workflow definition
- `get_agents()`: Get agent dictionary
- `capabilities`: Combined agent capabilities

**Example:**

```python
from agenkit.patterns import OrchestrationPattern, WorkflowDefinition

# Define content moderation workflow
workflow = WorkflowDefinition({
    "stages": [
        # Stage 1: Parallel screening
        {
            "name": "screening",
            "agents": ["spam_detector", "toxicity_detector"],
            "execution": "parallel",
            "aggregation": "any_flag"
        },
        # Stage 2: Conditional deep analysis
        {
            "name": "analysis",
            "agents": ["context_analyzer"],
            "condition": "screening.flagged == true",
            "execution": "sequential"
        },
        # Stage 3: Final decision
        {
            "name": "decision",
            "agents": ["decision_maker"],
            "inputs": ["screening", "analysis"],
            "aggregation": "consensus"
        }
    ]
})

# Create orchestrator
orchestrator = OrchestrationPattern(
    agents={
        "spam_detector": SpamDetector(),
        "toxicity_detector": ToxicityDetector(),
        "context_analyzer": ContextAnalyzer(),
        "decision_maker": DecisionMaker()
    },
    workflow=workflow
)

result = await orchestrator.process(content)

# Metadata shows workflow execution
print(result.metadata["workflow_stages_executed"])
print(result.metadata["workflow_decisions"])
```

**Performance:**
- Latency: Depends on workflow structure
- Complex workflows: Higher overhead
- Optimization: Parallel stages reduce latency

---

#### ReasoningWithToolsPattern

**Enhanced reasoning (CoT/ToT/Self-Consistency) with tools.**

```python
class ReasoningWithToolsPattern(Agent):
    def __init__(
        self,
        llm: Agent,
        tools: list[Tool],
        reasoning_strategy: str = "chain-of-thought",
        max_iterations: int = 10,
        **strategy_params,
    ) -> None:
```

**Parameters:**
- `llm`: Language model for reasoning
- `tools`: Available tools for execution
- `reasoning_strategy`: Strategy to use
  - `"chain-of-thought"`: Sequential reasoning steps
  - `"tree-of-thought"`: Explore multiple reasoning branches
  - `"self-consistency"`: Generate multiple solutions and vote
- `max_iterations`: Maximum reasoning steps (default: 10)
- `**strategy_params`: Strategy-specific parameters
  - Chain of Thought: None
  - Tree of Thought: `branches=3`, `max_depth=5`
  - Self-Consistency: `num_samples=5`

**Behavior:**
- Applies reasoning strategy to problem
- Generates explicit reasoning trace
- Identifies and executes tools with justification
- Synthesizes results with reasoning
- Returns answer with full reasoning explanation

**Methods:**
- `process(message)`: Reason and solve problem
- `get_reasoning_trace()`: Get reasoning steps
- `capabilities`: Tool capabilities plus reasoning types

**Example:**

```python
from agenkit.patterns import ReasoningWithToolsPattern

# Chain of Thought reasoning
cot_agent = ReasoningWithToolsPattern(
    llm=my_llm,
    tools=[search_tool, calculator_tool],
    reasoning_strategy="chain-of-thought",
    max_iterations=10
)

problem = Message.with_text("user", "Complex multi-step problem")
result = await cot_agent.process(problem)

# Reasoning trace available
for step in result.metadata["reasoning_trace"]:
    print(f"Thought: {step['thought']}")
    if step.get("tool_call"):
        print(f"  Tool: {step['tool_call']}")
        print(f"  Result: {step['tool_result']}")
```

**Tree of Thought:**

```python
# Explore multiple reasoning paths
tot_agent = ReasoningWithToolsPattern(
    llm=my_llm,
    tools=[search_tool, calculator_tool],
    reasoning_strategy="tree-of-thought",
    branches=3,  # Explore 3 paths
    max_depth=5  # 5 reasoning steps per path
)

result = await tot_agent.process(problem)

# Multiple reasoning branches explored
for branch in result.metadata["reasoning_branches"]:
    print(f"Path: {branch['approach']}")
    print(f"Score: {branch['score']}")
print(f"Best path: {result.metadata['best_branch']}")
```

**Self-Consistency:**

```python
# Generate multiple solutions and vote
consistency_agent = ReasoningWithToolsPattern(
    llm=my_llm,
    tools=[calculator_tool],
    reasoning_strategy="self-consistency",
    num_samples=5  # Generate 5 independent solutions
)

result = await consistency_agent.process(problem)

# Consensus answer
print(f"Consensus: {result.text}")
print(f"Samples: {result.metadata['reasoning_samples']}")
```

**Performance:**
- Chain of Thought: Medium latency, single path
- Tree of Thought: High latency, explores branches
- Self-Consistency: Very high latency, multiple samples
- Cost: Multiple LLM calls (expensive)

---

#### CollaborativePattern

**Multi-agent team collaboration with shared workspace.**

```python
class CollaborativePattern(Agent):
    def __init__(
        self,
        agents: list[Agent],
        collaboration_strategy: str = "shared-workspace",
        max_rounds: int = 5,
        shared_context: bool = True,
        name: str = "collaborative",
    ) -> None:
```

**Parameters:**
- `agents`: List of collaborating agents
- `collaboration_strategy`: How agents collaborate
  - `"shared-workspace"`: Common workspace for all agents
  - `"sequential-refinement"`: Each agent refines previous work
  - `"debate"`: Agents debate to reach consensus
  - `"voting"`: Agents vote on solutions
- `max_rounds`: Maximum collaboration rounds (default: 5)
- `shared_context`: Whether agents see all previous work (default: True)
- `name`: Pattern identifier (default: "collaborative")

**Behavior:**
- Initializes shared workspace
- Agents contribute sequentially or concurrently
- Bidirectional communication enabled
- Shared context accessible to all agents
- Synthesizes collaborative result

**Methods:**
- `process(message)`: Collaborative execution
- `get_agents()`: Get collaborating agents
- `get_workspace()`: Get shared workspace state
- `capabilities`: Combined agent capabilities

**Example:**

```python
from agenkit.patterns import CollaborativePattern

# Collaborative writing team
team = CollaborativePattern(
    agents=[
        outliner_agent,    # Creates structure
        researcher_agent,  # Gathers information
        writer_agent,      # Writes content
        editor_agent       # Refines output
    ],
    collaboration_strategy="sequential-refinement",
    max_rounds=3,
    shared_context=True
)

task = Message.with_text("user", "Write comprehensive market analysis")
result = await team.process(task)

# Collaboration details in metadata
print(result.metadata["collaboration_rounds"])
for contribution in result.metadata["agent_contributions"]:
    print(f"{contribution['agent']}: {contribution['summary']}")
```

**Debate Strategy:**

```python
# Agents debate to reach consensus
debate_team = CollaborativePattern(
    agents=[optimist_agent, pessimist_agent, realist_agent],
    collaboration_strategy="debate",
    max_rounds=5
)

# Agents debate pros/cons
decision = await debate_team.process(strategic_question)
print(decision.metadata["debate_rounds"])
print(decision.metadata["consensus_reached"])
```

**Performance:**
- Latency: Multiple agent interactions (slower)
- Quality: Higher due to multiple perspectives
- Best for: Complex, multifaceted problems

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

### Example 7: ReAct Pattern with Custom Tools

```python
from agenkit import Tool, ToolResult, Message
from agenkit.patterns import ReActPattern

# Define custom tools
class DatabaseTool(Tool):
    @property
    def name(self) -> str:
        return "query_database"

    @property
    def description(self) -> str:
        return "Query the customer database"

    async def execute(self, query: str) -> ToolResult:
        # Simulate database query
        results = await db.execute(query)
        return ToolResult(success=True, data=results)

class EmailTool(Tool):
    @property
    def name(self) -> str:
        return "send_email"

    @property
    def description(self) -> str:
        return "Send email to a customer"

    async def execute(self, to: str, subject: str, body: str) -> ToolResult:
        await email_service.send(to, subject, body)
        return ToolResult(success=True, data={"sent": True})

# Create ReAct agent with tools
react = ReActPattern(
    agent=llm_agent,
    tools=[DatabaseTool(), EmailTool()],
    max_iterations=10
)

# Complex task requiring tool usage
task = Message.with_text(
    "user",
    "Find all customers from California and send them a promotion email"
)

result = await react.process(task)
# Agent will:
# 1. Think: "I need to query the database for CA customers"
# 2. Act: Use query_database tool
# 3. Observe: Get list of customers
# 4. Think: "Now I need to send emails"
# 5. Act: Use send_email tool for each customer
# 6. Observe: Confirm emails sent
# 7. Return: Final status
```

### Example 8: Reflection Pattern for Quality Improvement

```python
from agenkit.patterns import ReflectionPattern

# Actor writes code
class CodeWriter(Agent):
    @property
    def name(self) -> str:
        return "code_writer"

    async def process(self, message: Message) -> Message:
        requirement = message.content
        code = await self.generate_code(requirement)
        return Message.with_data("agent", {"code": code})

# Reflector reviews code
class CodeReviewer(Agent):
    @property
    def name(self) -> str:
        return "code_reviewer"

    async def process(self, message: Message) -> Message:
        code = message.content.get("code")
        issues = await self.review(code)

        if not issues:
            return Message.with_data("agent", {
                "approved": True,
                "code": code
            })

        suggestions = await self.generate_improvements(issues)
        return Message.with_data("agent", {
            "approved": False,
            "suggestions": suggestions,
            "code": code
        })

# Create reflection pattern
reflection = ReflectionPattern(
    actor=CodeWriter(),
    reflector=CodeReviewer(),
    max_iterations=3,
    improvement_threshold=0.1
)

task = Message.with_text("user", "Create a function to validate email addresses")
result = await reflection.process(task)
# Iterative improvement:
# Iteration 1: Writer creates basic regex
# Iteration 2: Reviewer finds edge cases, writer improves
# Iteration 3: Reviewer approves or suggests final tweaks
```

### Example 9: Planning Pattern for Multi-Step Tasks

```python
from agenkit.patterns import PlanningPattern

# Strategic planner creates execution plan
class ResearchPlanner(Agent):
    @property
    def name(self) -> str:
        return "research_planner"

    async def process(self, message: Message) -> Message:
        topic = message.content
        plan = {
            "steps": [
                {
                    "action": "search_academic",
                    "params": {"query": f"{topic} research papers"},
                    "description": "Find academic papers"
                },
                {
                    "action": "search_news",
                    "params": {"query": f"{topic} latest news"},
                    "description": "Find recent news"
                },
                {
                    "action": "synthesize",
                    "params": {"sources": ["academic", "news"]},
                    "description": "Combine insights"
                },
                {
                    "action": "create_report",
                    "params": {"format": "markdown"},
                    "description": "Generate final report"
                }
            ]
        }
        return Message.with_data("agent", plan)

# Executor performs each step
class ResearchExecutor(Agent):
    @property
    def name(self) -> str:
        return "research_executor"

    async def process(self, message: Message) -> Message:
        step = message.content
        action = step["action"]

        if action == "search_academic":
            results = await self.search_academic(**step["params"])
        elif action == "search_news":
            results = await self.search_news(**step["params"])
        elif action == "synthesize":
            results = await self.synthesize(**step["params"])
        elif action == "create_report":
            results = await self.create_report(**step["params"])
        else:
            raise ValueError(f"Unknown action: {action}")

        return Message.with_data("agent", {
            "step_result": results,
            "completed": True
        })

# Create planning pattern
planning = PlanningPattern(
    planner=ResearchPlanner(),
    executor=ResearchExecutor(),
    max_steps=10,
    replan_on_failure=True
)

task = Message.with_text("user", "Research quantum computing applications in finance")
result = await planning.process(task)
# Planner creates 4-step plan, executor performs each step
# If any step fails, planner creates adjusted plan
```

### Example 10: Conversational Pattern for Chatbots

```python
from agenkit.patterns import ConversationalPattern

# Create chatbot with conversation memory
chatbot = ConversationalPattern(
    agent=llm_agent,
    max_history=20,
    system_prompt="""You are a helpful customer service agent.
    Be friendly, concise, and always try to solve the customer's problem."""
)

# Simulate multi-turn conversation
conversations = [
    "Hello, I have a problem with my order",
    "Order number is 12345",
    "It hasn't arrived yet",
    "I ordered it 2 weeks ago",
    "Can you check the status?",
    "Yes, please expedite it",
    "Thank you!"
]

for user_input in conversations:
    msg = Message.with_text("user", user_input)
    response = await chatbot.process(msg)
    print(f"User: {user_input}")
    print(f"Bot: {response.content}")
    print()

# Check conversation history
history = chatbot.get_history()
print(f"Total messages in history: {len(history)}")

# Save/restore conversation
history_data = chatbot.get_history()
# ... later ...
chatbot.clear_history()
for msg in history_data:
    await chatbot.process(msg)
```

### Example 11: Autonomous Agent for Research Tasks

```python
from agenkit.patterns import AutonomousPattern

def evaluate_research_progress(initial: Message, current: Message) -> float:
    """Evaluate research task completion."""
    goal = initial.metadata.get("required_sources", 5)
    result = current.content

    if not isinstance(result, dict):
        return 0.0

    sources_found = len(result.get("sources", []))
    completeness = result.get("report_complete", False)

    score = min(sources_found / goal, 1.0) * 0.7
    if completeness:
        score += 0.3

    return score

# Create autonomous research agent
researcher = AutonomousPattern(
    agent=research_agent,
    tools=[web_search, academic_search, citation_tool, summarizer],
    goal_evaluator=evaluate_research_progress,
    max_iterations=15,
    goal_threshold=0.9
)

task = Message.with_text(
    "user",
    "Research the impact of AI on healthcare and create a comprehensive report",
    metadata={"required_sources": 10, "depth": "comprehensive"}
)

result = await researcher.process(task)
# Agent autonomously:
# 1. Searches for AI healthcare information
# 2. Evaluates source quality
# 3. Gathers sufficient citations
# 4. Synthesizes findings
# 5. Creates structured report
# 6. Checks completeness (goal_evaluator)
# 7. Continues until goal_threshold (0.9) reached
```

### Example 12: Memory Hierarchy for Long Conversations

```python
from agenkit.patterns import MemoryHierarchyPattern

# Create agent with hierarchical memory
assistant = MemoryHierarchyPattern(
    agent=llm_agent,
    short_term_size=5,
    long_term_size=50,
    memory_strategy="importance"
)

# User shares important information
await assistant.process(Message.with_text("user", "My name is Alice"))
await assistant.process(Message.with_text("user", "I'm allergic to peanuts"))
await assistant.process(Message.with_text("user", "I work as a software engineer"))

# Many casual messages
for i in range(20):
    await assistant.process(Message.with_text("user", f"Small talk message {i}"))

# Later: assistant remembers important facts
response = await assistant.process(Message.with_text("user", "What's my name?"))
# "Your name is Alice" - retrieved from long-term memory

response = await assistant.process(Message.with_text("user", "Can I eat this cookie?"))
# Agent checks long-term memory for allergies
# "Let me check the ingredients for peanuts first, since you're allergic"

# Check memory tiers
short_term = assistant.get_short_term_memory()
long_term = assistant.get_long_term_memory()

print(f"Short-term: {len(short_term)} messages")
print(f"Long-term: {len(long_term)} messages")
```

### Example 13: Multi-Agent Collaboration System

```python
from agenkit.patterns import MultiagentPattern

# Create specialized expert agents
class DataAnalyst(Agent):
    @property
    def name(self) -> str:
        return "data_analyst"

    async def process(self, message: Message) -> Message:
        data = message.content
        analysis = await self.analyze(data)
        return Message.with_data("agent", {
            "insights": analysis,
            "visualizations": await self.create_charts(data)
        })

class Strategist(Agent):
    @property
    def name(self) -> str:
        return "strategist"

    async def process(self, message: Message) -> Message:
        data = message.content
        strategy = await self.develop_strategy(data)
        return Message.with_data("agent", {
            "recommendations": strategy,
            "action_plan": await self.create_action_plan(strategy)
        })

class Writer(Agent):
    @property
    def name(self) -> str:
        return "writer"

    async def process(self, message: Message) -> Message:
        data = message.content
        report = await self.write_report(data)
        return Message.with_data("agent", {
            "report": report,
            "executive_summary": await self.summarize(report)
        })

# Aggregator combines all expert outputs
def combine_expert_analysis(messages: list[Message]) -> Message:
    """Combine insights from all experts."""
    analysis = messages[0].content
    strategy = messages[1].content
    report = messages[2].content

    combined = {
        "data_insights": analysis["insights"],
        "visualizations": analysis["visualizations"],
        "strategic_recommendations": strategy["recommendations"],
        "action_plan": strategy["action_plan"],
        "full_report": report["report"],
        "executive_summary": report["executive_summary"]
    }

    return Message.with_data("agent", combined)

# Create multi-agent system
expert_team = MultiagentPattern(
    agents=[DataAnalyst(), Strategist(), Writer()],
    collaboration_strategy="parallel",
    aggregator=combine_expert_analysis
)

# Complex business analysis task
task = Message.with_data("user", {
    "sales_data": sales_df,
    "market_data": market_df,
    "task": "Analyze Q4 performance and create strategic plan for Q1"
})

result = await expert_team.process(task)
# All experts work simultaneously:
# - Data analyst analyzes sales/market data
# - Strategist develops strategy based on data
# - Writer creates comprehensive report
# Results combined into unified output
```

### Example 14: Agent-as-Tools Orchestration

```python
from agenkit.patterns import AgentsAsToolsPattern

# Create specialized agents
class TranslationAgent(Agent):
    @property
    def name(self) -> str:
        return "translator"

    async def process(self, message: Message) -> Message:
        text = message.content["text"]
        target_lang = message.content["language"]
        translated = await self.translate(text, target_lang)
        return Message.with_data("agent", {"translated": translated})

class SummarizationAgent(Agent):
    @property
    def name(self) -> str:
        return "summarizer"

    async def process(self, message: Message) -> Message:
        text = message.content["text"]
        max_length = message.content.get("max_length", 100)
        summary = await self.summarize(text, max_length)
        return Message.with_data("agent", {"summary": summary})

class SentimentAgent(Agent):
    @property
    def name(self) -> str:
        return "sentiment_analyzer"

    async def process(self, message: Message) -> Message:
        text = message.content["text"]
        sentiment = await self.analyze_sentiment(text)
        return Message.with_data("agent", {"sentiment": sentiment})

# Orchestrator decides which specialists to use
orchestrator = AgentsAsToolsPattern(
    orchestrator=coordinator_llm,
    specialist_agents={
        "translator": TranslationAgent(),
        "summarizer": SummarizationAgent(),
        "sentiment_analyzer": SentimentAgent()
    }
)

# Complex task requiring multiple specialists
task = Message.with_text(
    "user",
    """I received customer feedback in Spanish. Please translate it to English,
    analyze the sentiment, and provide a brief summary."""
)

result = await orchestrator.process(task)
# Orchestrator:
# 1. Recognizes need for translation
# 2. Calls translator specialist
# 3. Recognizes need for sentiment analysis
# 4. Calls sentiment_analyzer specialist
# 5. Recognizes need for summary
# 6. Calls summarizer specialist
# 7. Combines results into final response
```

### Example 15: Complex Pattern Composition

```python
from agenkit.patterns import (
    SequentialPattern,
    ParallelPattern,
    ReflectionPattern,
    ReActPattern,
    ConversationalPattern
)

# Build a sophisticated agent system by composing patterns

# Step 1: Conversational wrapper for context
conversational = ConversationalPattern(
    agent=base_llm,
    max_history=10,
    system_prompt="You are an AI assistant specialized in research and analysis"
)

# Step 2: Reflection for quality improvement
reflection = ReflectionPattern(
    actor=conversational,
    reflector=critic_agent,
    max_iterations=2
)

# Step 3: ReAct for tool usage
react = ReActPattern(
    agent=reflection,
    tools=[search_tool, calculator_tool, database_tool],
    max_iterations=5
)

# Step 4: Parallel fact-checking
fact_checker = ParallelPattern(
    agents=[source_verifier, fact_validator, citation_checker],
    aggregator=lambda msgs: msgs[0]  # Use first (fastest) result
)

# Step 5: Sequential pipeline combining all patterns
research_pipeline = SequentialPattern([
    react,          # Research with tools
    fact_checker,   # Verify facts
    formatter       # Format final output
])

# Use the composed system
query = Message.with_text(
    "user",
    "Research the environmental impact of electric vehicles compared to gasoline cars"
)

result = await research_pipeline.process(query)
# The message flows through:
# 1. ReAct: Uses tools to gather information
# 2. Reflection: Improves research quality
# 3. Conversational: Maintains context
# 4. Parallel fact-checking: Verifies claims
# 5. Formatter: Creates final report
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
