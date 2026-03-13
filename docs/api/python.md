# Python API Reference

**Package:** `agenkit`
**Python:** 3.11+

---

## Core Types

### `agenkit.Message`

```python
class Message:
    role: str
    content: str
    metadata: dict[str, Any]

    def __init__(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None: ...
```

`role` is typically `"user"`, `"assistant"`, or `"system"`. `metadata` is an arbitrary dictionary for routing hints, token counts, tool results, etc.

### `agenkit.Agent` (abstract base class)

```python
class Agent(ABC):
    @abstractmethod
    async def process(self, message: Message) -> Message: ...

    def name(self) -> str: ...
    def capabilities(self) -> list[str]: ...
```

All pattern classes, adapters, and middleware wrappers implement this interface. `process` is always a coroutine.

---

## LLM Adapters

### `agenkit.adapters.llm.anthropic.AnthropicClient`

```python
AnthropicClient(
    model: str = "claude-sonnet-4-6",
    api_key: str | None = None,     # falls back to ANTHROPIC_API_KEY env var
    max_tokens: int = 4096,
    temperature: float = 1.0,
)
```

Implements `Agent`. Calls the Anthropic Messages API. Response `metadata` includes `input_tokens`, `output_tokens`, `stop_reason`.

### `agenkit.adapters.llm.openai.OpenAIClient`

```python
OpenAIClient(
    model: str = "gpt-4o",
    api_key: str | None = None,     # falls back to OPENAI_API_KEY env var
    max_tokens: int = 4096,
    temperature: float = 0.7,
)
```

### Additional Adapters

| Class | Module | Notes |
|-------|--------|-------|
| `BedrockClient` | `agenkit.adapters.llm.bedrock` | AWS Bedrock |
| `GeminiClient` | `agenkit.adapters.llm.gemini` | Google Gemini |
| `OllamaClient` | `agenkit.adapters.llm.ollama` | Local Ollama |
| `LiteLLMClient` | `agenkit.adapters.llm.litellm` | LiteLLM proxy |

---

## Patterns

**Module:** `agenkit.patterns`

All pattern constructors accept at minimum an `agent: Agent` (the underlying LLM client or another pattern). Additional parameters are listed below.

| Class | Key Constructor Parameters |
|-------|---------------------------|
| `ReflectionAgent` | `agent`, `max_iterations: int = 3` |
| `ReactAgent` | `agent`, `tools: list[Tool]` |
| `AgentsAsToolsAgent` | `agent`, `sub_agents: list[Agent]` |
| `OrchestrationAgent` | `orchestrator: Agent`, `workers: list[Agent]` |
| `ReasoningWithToolsAgent` | `agent`, `tools: list[Tool]`, `max_steps: int = 10` |
| `ConversationalAgent` | `agent`, `history: Memory | None = None` |
| `TaskAgent` | `agent`, `task_description: str` |
| `MultiagentAgent` | `agents: list[Agent]` |
| `PlanningAgent` | `planner: Agent`, `executor: Agent` |
| `AutonomousAgent` | `agent`, `max_iterations: int = 10`, `stop_condition: Callable | None = None` |
| `SequentialAgent` | `agents: list[Agent]` |
| `ParallelAgent` | `agents: list[Agent]`, `aggregator: Callable | None = None` |
| `RouterAgent` | `router: Agent`, `routes: dict[str, Agent]` |
| `FallbackAgent` | `primary: Agent`, `fallbacks: list[Agent]` |
| `CollaborativeAgent` | `agents: list[Agent]`, `coordinator: Agent` |
| `HumanInLoopAgent` | `agent`, `approval_callback: Callable[[Message], Awaitable[bool]]` |
| `SupervisorAgent` | `supervisor: Agent`, `workers: list[Agent]` |
| `WorkingMemoryAgent` | `agent`, `memory: Memory` |

---

## Middleware

**Module:** `agenkit.middleware`

All middleware classes wrap an `Agent` and implement `Agent` themselves.

### `RetryDecorator`

```python
RetryDecorator(
    agent: Agent,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
)
```

### `TimeoutDecorator`

```python
TimeoutDecorator(
    agent: Agent,
    timeout: float,   # seconds
)
```

### `RateLimiterDecorator`

```python
RateLimiterDecorator(
    agent: Agent,
    requests_per_minute: int,
    burst: int | None = None,
)
```

### `CircuitBreakerDecorator`

```python
CircuitBreakerDecorator(
    agent: Agent,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
)
```

### `BatchingDecorator`

```python
BatchingDecorator(
    agent: Agent,
    max_batch_size: int = 10,
    max_wait_ms: float = 100.0,
)
```

### `CachingDecorator`

```python
CachingDecorator(
    agent: Agent,
    ttl: float | None = None,     # seconds; None = no expiry
    storage: CacheStorage | None = None,
)
```

### `MetricsDecorator`

```python
MetricsDecorator(
    agent: Agent,
    collector: MetricsCollector | None = None,
)
```

---

## Memory

**Module:** `agenkit.memory`

### `EphemeralMemory`

In-process message history. Lost on process exit.

```python
EphemeralMemory(max_messages: int | None = None)
```

Methods: `add(message: Message)`, `get_history() -> list[Message]`, `clear()`.

### `LocalCheckpointStorage`

Persists memory to the local filesystem.

```python
LocalCheckpointStorage(path: str | Path)
```

### `MemoryStorage`

In-memory storage implementing the `CheckpointStorage` protocol; useful for testing.

```python
MemoryStorage()
```

---

## Checkpointing

**Module:** `agenkit.checkpointing`

### `CheckpointManager`

```python
CheckpointManager(
    storage: CheckpointStorage,
    agent_id: str,
    auto_save: bool = True,
)

async def save(state: AgentState) -> str: ...          # returns checkpoint_id
async def load(checkpoint_id: str) -> AgentState: ...
async def list_checkpoints() -> list[CheckpointMeta]: ...
async def delete(checkpoint_id: str) -> None: ...
```

### Storage Backends

| Class | Module | Parameters |
|-------|--------|------------|
| `LocalStorage` | `agenkit.checkpointing.storage` | `path: str` |
| `S3Storage` | `agenkit.checkpointing.storage` | `bucket: str`, `prefix: str`, `region: str` |

---

## Reasoning Techniques

**Module:** `agenkit.techniques.reasoning`

All technique classes wrap an `Agent`.

| Class | Key Parameters |
|-------|---------------|
| `ChainOfThought` | `agent`, `steps: int = 3` |
| `TreeOfThought` | `agent`, `branches: int = 3`, `depth: int = 3`, `evaluator: Agent | None = None` |
| `SelfConsistency` | `agent`, `samples: int = 5`, `aggregation: str = "majority"` |
| `GraphOfThought` | `agent`, `max_nodes: int = 10` |
| `PlanAndSolve` | `planner: Agent`, `solver: Agent` |
| `LeastToMost` | `agent`, `max_subproblems: int = 5` |

---

## Tool Protocol

```python
class Tool(Protocol):
    name: str
    description: str
    async def __call__(self, **kwargs: Any) -> Any: ...
```

Passed to `ReactAgent`, `ReasoningWithToolsAgent`, and similar patterns.

---

## Errors

| Exception | Raised when |
|-----------|-------------|
| `AgentError` | Base class for all Agenkit exceptions |
| `AdapterError` | LLM API call fails |
| `TimeoutError` | Agent exceeds configured timeout |
| `CircuitOpenError` | Circuit breaker is open |
| `CheckpointError` | Save / load fails |
