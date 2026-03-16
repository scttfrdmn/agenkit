# Migrating from Google ADK to Agenkit

**Target Audience**: Developers using Google Agent Development Kit for multi-agent systems
**Difficulty**: Beginner to Intermediate
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Language Support**:
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig (ADK is Python-only)
- Deploy the same logic 18x faster in Go
- TypeScript for frontend-native agents

**Independence**:
- **Any LLM**: Not tied to Gemini or Google AI APIs
- **No Google Cloud required**: Run fully on-premise or any cloud
- **Stable API**: No dependency on Google's SDK release schedule

**Production**:
- **OpenTelemetry**: Industry-standard tracing (not proprietary)
- **Circuit breakers, retry, timeout**: Production resilience built-in
- **Memory hierarchy**: Working, episodic, semantic memory types

### Key Conceptual Differences

| Google ADK | Agenkit | Notes |
|------------|---------|-------|
| **Agent** | **Agent** base class | Same concept |
| **SequentialAgent** | **SequentialAgent** | Direct mapping |
| **ParallelAgent** | **ParallelAgent** | Direct mapping |
| **LoopAgent** | **Agent loop** | Explicit loop |
| **@tool** | **Tool class** | Simpler |
| **InMemorySessionService** | **ConversationalAgent** | Built-in |
| **Content(parts=[Part(text=...)])** | **Message(role=..., content=...)** | Simpler |
| **Runner** | **agent.process()** | Direct call |
| **LiteLlm(model="gemini/...")** | **OpenAILLM(model="...")** | Any provider |

### What You Gain

✅ **Any LLM**: Gemini, OpenAI, Anthropic, local Ollama, vLLM, etc.
✅ **6 languages**: Same agent logic in Go/Rust for production performance
✅ **No Google Cloud**: Run anywhere without Google dependencies
✅ **Simpler message format**: `Message` vs `Content(parts=[Part(text=...)])`
✅ **Production middleware**: Retry, circuit breaker, timeout

### What You Lose

❌ **Gemini native integration**: No direct Gemini function-calling support
❌ **Vertex AI agent engine**: No Google Cloud managed agent hosting
❌ **ADK Web UI**: No built-in local testing web interface

---

## Pattern Mapping Table

| Google ADK | Agenkit Equivalent | Notes |
|------------|-------------------|-------|
| `Agent(name, model, instruction, tools)` | `Agent` subclass | More explicit |
| `SequentialAgent(sub_agents=[...])` | `SequentialAgent([...])` | Same |
| `ParallelAgent(sub_agents=[...])` | `ParallelAgent([...])` | Same |
| `LoopAgent(sub_agents, max_iterations)` | Loop with `agent.process()` | Explicit |
| `@tool` / `tool` decorator | `Tool` class | Class-based |
| `InMemorySessionService()` | `ConversationalAgent` | Built-in |
| `Content(parts=[Part(text=x)])` | `Message(role="user", content=x)` | Simpler |
| `runner.run(agent, user_id, session_id, msg)` | `await agent.process(message)` | Async |
| `LiteLlm(model="gemini/gemini-2.0-flash")` | `OpenAILLM(model="gpt-4o-mini")` | Any model |

---

## Common Patterns

### Pattern 1: Basic Agent with Tools

**Google ADK Code:**
```python
from google.adk.agents import Agent
from google.adk.tools import tool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content, Part

@tool
def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny, 22°C"

agent = Agent(
    name="weather_assistant",
    model=LiteLlm(model="gemini/gemini-2.0-flash"),
    instruction="You are a weather assistant. Use the get_weather tool.",
    tools=[get_weather],
)

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="demo", session_service=session_service)

user_id = "user-1"
session_id = session_service.create_session(app_name="demo", user_id=user_id).id
new_message = Content(parts=[Part(text="What is the weather in Seattle?")])

for event in runner.run(agent=agent, user_id=user_id,
                         session_id=session_id, new_message=new_message):
    if event.is_final_response():
        print(event.response.text)
```

**Agenkit Equivalent:**
```python
from agenkit.adapters.llm import OpenAILLM
from agenkit.patterns import ReActAgent
from agenkit import Message

llm = OpenAILLM(model="gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])

class GetWeatherTool:
    name = "get_weather"
    description = "Get current weather for a city"

    async def run(self, city: str) -> str:
        return f"Weather in {city}: Sunny, 22°C"

agent = ReActAgent(llm=llm, tools=[GetWeatherTool()])
response = await agent.process(
    Message(role="user", content="What is the weather in Seattle?")
)
print(response.content)
```

---

### Pattern 2: SequentialAgent

**Google ADK Code:**
```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="research_pipeline",
    sub_agents=[research_agent, summarize_agent, format_agent],
)
# runner.run(agent=pipeline, ...)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import SequentialAgent

pipeline = SequentialAgent([research_agent, summarize_agent, format_agent])
result = await pipeline.process(Message(role="user", content="Research task"))
```

---

### Pattern 3: ParallelAgent

**Google ADK Code:**
```python
from google.adk.agents import ParallelAgent

parallel = ParallelAgent(
    name="multi_search",
    sub_agents=[news_agent, wiki_agent, docs_agent],
)
# All three run concurrently, results merged
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent([news_agent, wiki_agent, docs_agent])
results = await parallel.process(Message(role="user", content="Search for Agenkit"))
# results contains merged output from all three agents
```

---

### Pattern 4: LoopAgent

**Google ADK Code:**
```python
from google.adk.agents import LoopAgent

loop = LoopAgent(
    name="retry_loop",
    sub_agents=[validation_agent],
    max_iterations=3,
)
```

**Agenkit Equivalent:**
```python
async def loop_agent(message: Message, max_iterations: int = 3) -> Message:
    result = message
    for _ in range(max_iterations):
        result = await validation_agent.process(result)
        if is_valid(result):
            break
    return result
```

---

### Pattern 5: Session-Based Memory

**Google ADK Code:**
```python
session_service = InMemorySessionService()
session = session_service.create_session(app_name="my_app", user_id="user-1")

# First turn
runner.run(agent=agent, user_id="user-1", session_id=session.id,
           new_message=Content(parts=[Part(text="My name is Alex")]))

# Second turn — session resumed automatically
runner.run(agent=agent, user_id="user-1", session_id=session.id,
           new_message=Content(parts=[Part(text="What is my name?")]))
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ConversationalAgent

# ConversationalAgent maintains history automatically per instance
agent = ConversationalAgent(llm_client=llm, max_history=20)

await agent.process(Message(role="user", content="My name is Alex"))
response = await agent.process(Message(role="user", content="What is my name?"))
```

---

## Step-by-Step Migration

### Step 1: Replace Content/Part with Message

```python
# Before
from google.genai.types import Content, Part
new_message = Content(parts=[Part(text="Hello!")])

# After
from agenkit import Message
message = Message(role="user", content="Hello!")
```

### Step 2: Replace @tool with Tool class

```python
# Before
from google.adk.tools import tool

@tool
def search(query: str) -> str:
    return f"Results: {query}"

# After
class SearchTool:
    name = "search"
    description = "Search for information"

    async def run(self, query: str) -> str:
        return f"Results: {query}"
```

### Step 3: Replace Runner with agent.process()

```python
# Before
runner = Runner(agent=agent, app_name="demo", session_service=session_service)
for event in runner.run(agent=agent, user_id=uid, session_id=sid, new_message=msg):
    if event.is_final_response():
        print(event.response.text)

# After
response = await agent.process(message)
print(response.content)
```

### Step 4: Replace LiteLlm with Agenkit LLM adapter

```python
# Before
from google.adk.models.lite_llm import LiteLlm
model = LiteLlm(model="gemini/gemini-2.0-flash")

# After
from agenkit.adapters.llm import OpenAILLM
llm = OpenAILLM(model="gpt-4o-mini", api_key=api_key)
# Or use OllamaLLM for local models
```

---

## Common Pitfalls

1. **Event streaming**: ADK uses event-based `runner.run()` iteration; Agenkit uses `await agent.process()` or `agent.process_stream()` async generator
2. **Session/User IDs**: Agenkit `ConversationalAgent` is per-instance; for multi-user scenarios create one agent per user or use `InMemoryStorage` with explicit keys
3. **Content vs Message**: ADK's `Content(parts=[Part(text=...)])` maps to `Message(role=..., content=...)` — much simpler

---

## Reference

- Example: `examples/frameworks/minigoogleadk.py`
- Go equivalent: `agenkit-go/examples/frameworks/minigoogleadk/main.go`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
