# Migrating from Pydantic AI to Agenkit

**Target Audience**: Developers using Pydantic AI for type-safe AI agent development
**Difficulty**: Beginner to Intermediate
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Language Support**:
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig (Pydantic AI is Python-only)
- Deploy in Go for 18x performance on the same logic
- TypeScript for frontend-native agents

**Flexibility**:
- **Any LLM provider**: OpenAI, Anthropic, local Ollama, vLLM — not just OpenAI-compatible APIs
- **Composable patterns**: ReAct, Sequential, Router, Parallel, Planning, and more
- **Production middleware**: Circuit breakers, retry, timeout

**Observability**:
- **OpenTelemetry**: Industry-standard (not proprietary tracing)
- **Unified traces**: Across all languages and agent hops

### Key Conceptual Differences

| Pydantic AI | Agenkit | Notes |
|------------|---------|-------|
| **`Agent[T]`** | **Agent** base class | More flexible |
| **`agent.run()`** | **`agent.process()`** | Async |
| **`agent.run_sync()`** | **`asyncio.run(agent.process(...))`** | Explicit |
| **`@agent.tool`** | **Tool class** | Class-based |
| **`RunContext[T]`** | **Message metadata** | Simpler |
| **`SystemPromptFn`** | **system prompt string** | Static or dynamic |
| **Structured output** | **JSON schema prompt** | Explicit |
| **`ModelRetry`** | **Retry middleware** | Infrastructure layer |
| **`UsageLimits`** | **Rate limiting middleware** | Configurable |

### What You Gain

✅ **Multi-language**: Same agent logic in Go, TypeScript, Rust, etc.
✅ **Composable patterns**: Mix ReAct, Sequential, Router without framework constraints
✅ **Production middleware**: Separate concern from agent logic
✅ **OpenTelemetry**: Not tied to Pydantic AI's logfire integration
✅ **Explicit control**: No magic type inference on outputs

### What You Lose

❌ **Type-safe structured outputs**: No automatic Pydantic model validation of LLM output
❌ **Logfire integration**: Use OpenTelemetry exporters instead
❌ **`RunContext` dependency injection**: Pass dependencies explicitly
❌ **Automatic retry on type errors**: Implement retry middleware manually

---

## Pattern Mapping Table

| Pydantic AI | Agenkit Equivalent | Notes |
|------------|-------------------|-------|
| `Agent("openai:gpt-4o-mini")` | `OpenAILLM(model="gpt-4o-mini")` | Explicit adapter |
| `agent.run(prompt)` | `await agent.process(Message(...))` | Async |
| `agent.run_sync(prompt)` | `asyncio.run(agent.process(...))` | Explicit event loop |
| `@agent.tool` | `Tool` class | Class-based |
| `ctx: RunContext[Deps]` | Message metadata or constructor args | Explicit |
| `result.data` | `response.content` | String content |
| `result.usage()` | LLM adapter token tracking | Via metadata |
| `Agent(result_type=MyModel)` | JSON schema prompt + parsing | Explicit |
| `Agent(system_prompt="...")` | `Message(role="system", content="...")` | Standard |

---

## Common Patterns

### Pattern 1: Basic Agent Run

**Pydantic AI Code:**
```python
from pydantic_ai import Agent

agent = Agent("openai:gpt-4o-mini", system_prompt="You are a helpful assistant.")
result = agent.run_sync("What is the capital of France?")
print(result.data)
```

**Agenkit Equivalent:**
```python
from agenkit.adapters.llm import OpenAILLM
from agenkit import Message

llm = OpenAILLM(model="gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])
response = await llm.complete([
    Message(role="system", content="You are a helpful assistant."),
    Message(role="user", content="What is the capital of France?"),
])
print(response.content)
```

---

### Pattern 2: Tool Registration

**Pydantic AI Code:**
```python
from pydantic_ai import Agent

agent = Agent("openai:gpt-4o-mini")

@agent.tool
async def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny"

result = await agent.run("What's the weather in Seattle?")
print(result.data)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ReActAgent
from agenkit import Message
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(model="gpt-4o-mini", api_key=api_key)

class GetWeatherTool:
    name = "get_weather"
    description = "Get current weather for a city"

    async def run(self, city: str) -> str:
        return f"Weather in {city}: Sunny"

agent = ReActAgent(llm=llm, tools=[GetWeatherTool()])
response = await agent.process(
    Message(role="user", content="What's the weather in Seattle?")
)
print(response.content)
```

---

### Pattern 3: Dependency Injection via RunContext

**Pydantic AI Code:**
```python
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

@dataclass
class DatabaseConn:
    user_id: int

agent = Agent("openai:gpt-4o-mini", deps_type=DatabaseConn)

@agent.tool
async def get_user_info(ctx: RunContext[DatabaseConn]) -> str:
    return f"User ID: {ctx.deps.user_id}"

result = await agent.run("Get my info", deps=DatabaseConn(user_id=42))
```

**Agenkit Equivalent:**
```python
# Pass dependencies explicitly via constructor or closure
class GetUserInfoTool:
    name = "get_user_info"
    description = "Get information about the current user"

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    async def run(self) -> str:
        return f"User ID: {self.user_id}"

agent = ReActAgent(llm=llm, tools=[GetUserInfoTool(user_id=42)])
response = await agent.process(Message(role="user", content="Get my info"))
```

---

### Pattern 4: Structured Output

**Pydantic AI Code:**
```python
from pydantic import BaseModel
from pydantic_ai import Agent

class WeatherReport(BaseModel):
    city: str
    temperature: float
    condition: str

agent = Agent("openai:gpt-4o-mini", result_type=WeatherReport)
result = await agent.run("Get weather for Seattle")
report: WeatherReport = result.data
print(f"{report.city}: {report.temperature}°C, {report.condition}")
```

**Agenkit Equivalent:**
```python
import json
from pydantic import BaseModel

class WeatherReport(BaseModel):
    city: str
    temperature: float
    condition: str

schema = WeatherReport.model_json_schema()
response = await llm.complete([
    Message(role="system", content=f"Respond ONLY with valid JSON matching: {json.dumps(schema)}"),
    Message(role="user", content="Get weather for Seattle"),
])
report = WeatherReport.model_validate_json(str(response.content))
print(f"{report.city}: {report.temperature}°C, {report.condition}")
```

---

### Pattern 5: Retry on Validation Error

**Pydantic AI Code:**
```python
from pydantic_ai import Agent, ModelRetry

agent = Agent("openai:gpt-4o-mini", result_type=MyModel, retries=3)

@agent.result_validator
async def validate_result(ctx: RunContext, result: MyModel) -> MyModel:
    if not result.is_valid():
        raise ModelRetry("Result validation failed, try again")
    return result
```

**Agenkit Equivalent:**
```python
from agenkit.middleware import RetryMiddleware
from agenkit.patterns import ReActAgent

# Retry at the infrastructure level, not the agent level
agent = ReActAgent(
    llm=llm,
    tools=[tool],
    middleware=[RetryMiddleware(max_retries=3, retry_on=[ValueError])],
)
```

---

## Step-by-Step Migration

### Step 1: Replace Agent constructor

```python
# Before
agent = Agent("openai:gpt-4o-mini", system_prompt="Be helpful.")

# After
from agenkit.adapters.llm import OpenAILLM
llm = OpenAILLM(model="gpt-4o-mini", api_key=key)
system_message = Message(role="system", content="Be helpful.")
```

### Step 2: Replace @agent.tool with Tool class

```python
# Before
@agent.tool
async def my_tool(ctx: RunContext, input: str) -> str:
    return do_something(input)

# After
class MyTool:
    name = "my_tool"
    description = "Does something useful"
    async def run(self, input: str) -> str:
        return do_something(input)
```

### Step 3: Replace agent.run() with agent.process()

```python
# Before
result = await agent.run("user prompt")
output = result.data

# After
response = await agent.process(Message(role="user", content="user prompt"))
output = response.content
```

### Step 4: Add middleware for retries/rate limiting

```python
# Before (implicit in Pydantic AI)
agent = Agent(..., retries=3)

# After (explicit middleware)
from agenkit.middleware import RetryMiddleware
agent = ReActAgent(llm=llm, tools=tools,
                   middleware=[RetryMiddleware(max_retries=3)])
```

---

## Common Pitfalls

1. **`result.data` vs `response.content`**: Pydantic AI returns typed `result.data`; Agenkit returns `response.content` as a string — parse JSON if needed
2. **Sync vs async**: `agent.run_sync()` → wrap with `asyncio.run()`
3. **`RunContext` dependencies**: Explicit constructor arguments in Agenkit, no injection magic
4. **Type validation**: Agenkit doesn't auto-validate LLM output — validate the response string with Pydantic manually

---

## Reference

- Example: `examples/frameworks/minipydantic/minipydantic.py`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
