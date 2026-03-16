# Migrating from OpenAI Agents SDK to Agenkit

**Target Audience**: Developers using the OpenAI Agents SDK (openai-agents, January 2026)
**Difficulty**: Beginner
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Independence**:
- **Any LLM provider**: Anthropic, Gemini, local Ollama, vLLM — not just OpenAI
- **No OpenAI account required**: Run fully on-premise with local models
- **Stable API**: No dependency on OpenAI's SDK release schedule

**Language Support**:
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig
- Deploy same agent logic 18x faster in Go
- TypeScript for frontend-native agents

**Production**:
- **OpenTelemetry**: Not proprietary tracing
- **Circuit breakers, retry, timeout**: Infrastructure-level resilience
- **Memory hierarchy**: Not just in-context window

### Key Conceptual Differences

| OpenAI Agents SDK | Agenkit | Notes |
|-------------------|---------|-------|
| **`Agent`** | **Agent** base class | Similar |
| **`Runner.run()`** | **`agent.process()`** | Async |
| **`Runner.run_sync()`** | **`asyncio.run(agent.process(...))`** | Explicit |
| **`@function_tool`** | **Tool class** | Class-based |
| **`handoff()`** | **RouterAgent** | Explicit routing |
| **`RunResult`** | **Message** | Same concept |
| **`Agent.instructions`** | **system prompt** | String |
| **`Agent.handoffs`** | **RouterAgent agents dict** | Composable |
| **Streaming via `Runner.run()`** | **`agent.process_stream()`** | Async generator |

### What You Gain

✅ **Any LLM**: GPT-4o, Claude, Gemini, Llama, Mistral — all work the same way
✅ **Multi-language**: 6 languages including Go for 18x performance
✅ **Composable patterns**: 11+ orchestration patterns vs just agents + handoffs
✅ **Production middleware**: Retry, circuit breaker, timeout built-in
✅ **OpenTelemetry**: Standard tracing without proprietary lock-in

### What You Lose

❌ **OpenAI function calling**: Native JSON tool call schema format
❌ **Built-in tracing dashboard**: Use OpenTelemetry with Jaeger/Grafana instead
❌ **Voice (realtime API)**: Not supported in Agenkit
❌ **Computer use tools**: No built-in browser/computer control tools

---

## Pattern Mapping Table

| OpenAI Agents SDK | Agenkit Equivalent | Notes |
|-------------------|-------------------|-------|
| `Agent(name, instructions, tools)` | `Agent` subclass with `process()` | OOP |
| `@function_tool` | `Tool` class | Class-based |
| `function_tool(fn)` | `Tool` wrapping `fn` | Functional |
| `handoff(agent)` | `RouterAgent` routing entry | Composable |
| `Runner.run_sync(agent, input)` | `asyncio.run(agent.process(msg))` | Explicit |
| `await Runner.run(agent, input)` | `await agent.process(message)` | Same |
| `result.final_output` | `response.content` | String |
| `result.new_messages` | Response chain (via orchestrator) | Via tracing |
| `Agent.model` | `OpenAILLM(model=...)` | Explicit |
| `Agent.handoffs = [other]` | `RouterAgent(agents={"other": other})` | Explicit |

---

## Common Patterns

### Pattern 1: Basic Agent with Tools

**OpenAI Agents SDK Code:**
```python
from agents import Agent, Runner, function_tool

@function_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Weather in {city}: Sunny, 22°C"

agent = Agent(
    name="weather_assistant",
    instructions="You are a helpful weather assistant.",
    tools=[get_weather],
)
result = Runner.run_sync(agent, "What's the weather in Seattle?")
print(result.final_output)
```

**Agenkit Equivalent:**
```python
from agenkit.adapters.llm import OpenAILLM
from agenkit.patterns import ReActAgent
from agenkit import Message
import asyncio

llm = OpenAILLM(model="gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])

class GetWeatherTool:
    name = "get_weather"
    description = "Get the current weather for a city"

    async def run(self, city: str) -> str:
        return f"Weather in {city}: Sunny, 22°C"

agent = ReActAgent(llm=llm, tools=[GetWeatherTool()])
response = asyncio.run(agent.process(
    Message(role="user", content="What's the weather in Seattle?")
))
print(response.content)
```

---

### Pattern 2: Agent Handoffs (Triage Pattern)

**OpenAI Agents SDK Code:**
```python
from agents import Agent, handoff

billing_agent = Agent(
    name="billing",
    instructions="You handle billing questions.",
)

tech_agent = Agent(
    name="tech_support",
    instructions="You handle technical support questions.",
)

triage_agent = Agent(
    name="triage",
    instructions="Route questions to the right specialist.",
    handoffs=[handoff(billing_agent), handoff(tech_agent)],
)

result = await Runner.run(triage_agent, "My invoice is wrong")
print(result.final_output)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import RouterAgent, RouterConfig
from agenkit import Message

def classify(message: Message) -> str:
    content = message.content.lower()
    if any(w in content for w in ("invoice", "billing", "payment", "charge")):
        return "billing"
    return "tech_support"

router = RouterAgent(RouterConfig(
    classifier=classify,
    agents={
        "billing": billing_agent,
        "tech_support": tech_agent,
    }
))
response = await router.process(Message(role="user", content="My invoice is wrong"))
print(response.content)
```

---

### Pattern 3: Streaming

**OpenAI Agents SDK Code:**
```python
from agents import Runner

async with Runner.run_streamed(agent, "Tell me about Agenkit") as stream:
    async for event in stream:
        if hasattr(event, "delta"):
            print(event.delta, end="", flush=True)
```

**Agenkit Equivalent:**
```python
async for chunk in agent.process_stream(
    Message(role="user", content="Tell me about Agenkit")
):
    print(chunk.content, end="", flush=True)
```

---

### Pattern 4: Multi-Agent Pipeline

**OpenAI Agents SDK Code:**
```python
# Handoff chain: researcher → writer → reviewer
researcher = Agent(name="researcher", instructions="Research topics thoroughly.", tools=[search_tool])
writer = Agent(name="writer", instructions="Write clear summaries.", handoffs=[handoff(researcher)])
reviewer = Agent(name="reviewer", instructions="Review and improve writing.", handoffs=[handoff(writer)])

result = await Runner.run(reviewer, "Write a report on Agenkit")
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import SequentialAgent

# Explicit sequential pipeline — no handoff magic
pipeline = SequentialAgent([researcher_agent, writer_agent, reviewer_agent])
result = await pipeline.process(
    Message(role="user", content="Write a report on Agenkit")
)
```

---

## Step-by-Step Migration

### Step 1: Replace @function_tool with Tool class

```python
# Before
@function_tool
def search_docs(query: str) -> str:
    """Search the documentation."""
    return do_search(query)

# After
class SearchDocsTool:
    name = "search_docs"
    description = "Search the documentation"

    async def run(self, query: str) -> str:
        return do_search(query)
```

### Step 2: Replace Agent constructor with Agent subclass

```python
# Before
agent = Agent(
    name="assistant",
    instructions="Be helpful.",
    tools=[search_tool],
    model="gpt-4o-mini",
)

# After
from agenkit.patterns import ReActAgent
llm = OpenAILLM(model="gpt-4o-mini", api_key=key)
agent = ReActAgent(llm=llm, tools=[search_tool])
# For system prompt: pass as first Message(role="system", ...) in process()
```

### Step 3: Replace Runner.run() with agent.process()

```python
# Before
result = await Runner.run(agent, "user input")
print(result.final_output)

# After
response = await agent.process(Message(role="user", content="user input"))
print(response.content)
```

### Step 4: Replace handoffs with RouterAgent

```python
# Before
agent = Agent(name="triage", handoffs=[handoff(agent_a), handoff(agent_b)])

# After
router = RouterAgent(RouterConfig(
    classifier=my_classifier_fn,
    agents={"a": agent_a, "b": agent_b},
))
```

---

## Testing Your Migration

```python
@pytest.mark.asyncio
async def test_basic_agent():
    agent = ReActAgent(llm=mock_llm, tools=[WeatherTool()])
    response = await agent.process(
        Message(role="user", content="What's the weather in Seattle?")
    )
    assert response.content is not None
    assert response.role == "assistant"

@pytest.mark.asyncio
async def test_routing():
    router = RouterAgent(RouterConfig(
        classifier=lambda m: "billing" if "invoice" in m.content else "support",
        agents={"billing": billing_agent, "support": support_agent},
    ))
    response = await router.process(Message(role="user", content="My invoice is wrong"))
    assert response.content is not None
```

---

## Common Pitfalls

1. **`result.final_output` vs `response.content`**: Agenkit returns a `Message` with `.content` string
2. **Handoffs vs RouterAgent**: OAI handoffs are implicit (agent decides); Agenkit RouterAgent uses an explicit classifier function
3. **Model string**: OAI SDK takes `"gpt-4o-mini"` as `Agent.model`; Agenkit takes it as `OpenAILLM(model="gpt-4o-mini")`
4. **Sync runner**: `Runner.run_sync()` → wrap with `asyncio.run()`

---

## Reference

- Python example: `examples/frameworks/miniopenaiagents.py`
- Go equivalent: `agenkit-go/examples/frameworks/miniopenaiagents/main.go`
- TypeScript equivalent: `agenkit-ts/examples/frameworks/miniopenaiagents.ts`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
