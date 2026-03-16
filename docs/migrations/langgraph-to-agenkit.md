# Migrating from LangGraph to Agenkit

**Target Audience**: Developers using LangGraph for stateful, graph-based agent workflows
**Difficulty**: Intermediate
**Time to Read**: 12-15 minutes

---

## Overview

### Why Migrate to Agenkit?

**Performance**:
- **18x faster** in Go for production agent workloads
- Sub-millisecond node-to-node routing
- No Python GIL limitations when deployed in Go/Rust

**Simplicity**:
- **No LangChain dependency**: Agenkit is a standalone toolkit
- **Explicit control**: No compiled graph DSL — plain functions and composition
- **Cleaner mental model**: Sequential, Router, ReAct patterns replace StateGraph boilerplate

**Production**:
- **OpenTelemetry** observability without LangSmith
- **Circuit breakers, retry, timeout** middleware built-in
- **6 languages**: Deploy the same logic in Python, Go, TypeScript, Rust, C++, or Zig

### Key Conceptual Differences

| LangGraph | Agenkit | Notes |
|-----------|---------|-------|
| **StateGraph** | **Custom graph or SequentialAgent** | More explicit |
| **MessagesState** | **GraphState / message list** | Simpler state |
| **add_node()** | **Agent subclass or function** | Explicit wiring |
| **add_edge()** | **SequentialAgent pipeline** | Same concept |
| **add_conditional_edges()** | **RouterAgent** | Function-based routing |
| **ToolNode** | **Agenkit Tool executor** | Same concept |
| **MemorySaver** | **ConversationalAgent (built-in history)** | Baked in |
| **CompiledGraph.invoke()** | **agent.process()** | Direct call |
| **END sentinel** | **Pipeline termination** | Implicit |

### What You Gain

✅ **No LangChain dependency**: Smaller footprint, faster install
✅ **Multi-language deployment**: 18x faster in Go
✅ **Simpler API**: `await agent.process(message)` instead of graph DSL
✅ **Built-in memory**: `ConversationalAgent` handles history automatically
✅ **Production middleware**: Retry, circuit breaker, timeout built-in

### What You Lose

❌ **Graph visualization**: No built-in node graph UI
❌ **LangSmith integration**: Use OpenTelemetry exporters instead
❌ **Parallel node execution**: Use `ParallelAgent` pattern instead

---

## Pattern Mapping Table

| LangGraph | Agenkit Equivalent | Notes |
|-----------|-------------------|-------|
| `StateGraph()` | Custom orchestrator or `SequentialAgent` | More explicit |
| `graph.add_node("name", fn)` | Agent class with `process()` method | OOP |
| `graph.add_edge("a", "b")` | `SequentialAgent([a, b])` | Simpler |
| `graph.add_conditional_edges(...)` | `RouterAgent(classifier, agents)` | Cleaner |
| `graph.set_entry_point("node")` | First agent in `SequentialAgent` | Implicit |
| `graph.compile()` | No compile step needed | Direct |
| `app.invoke({"messages": [...]})` | `await agent.process(message)` | Async |
| `ToolNode(tools)` | `ReActAgent(tools=[...])` | Same pattern |
| `MemorySaver()` | `ConversationalAgent` built-in | No setup |
| `HumanMessage(content=...)` | `Message(role="user", content=...)` | Same |
| `AIMessage(content=...)` | `Message(role="assistant", content=...)` | Same |

---

## Common Patterns

### Pattern 1: Simple Linear Graph

**LangGraph Code:**
```python
from langgraph.graph import StateGraph, MessagesState, END

def preprocess(state):
    # normalize input
    return state

def generate(state):
    # call LLM
    return state

graph = StateGraph(MessagesState)
graph.add_node("preprocess", preprocess)
graph.add_node("generate", generate)
graph.add_edge("preprocess", "generate")
graph.add_edge("generate", END)
graph.set_entry_point("preprocess")
app = graph.compile()

result = app.invoke({"messages": [HumanMessage(content="Hello")]})
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Message

pipeline = SequentialAgent([preprocess_agent, generate_agent])
result = await pipeline.process(Message(role="user", content="Hello"))
```

---

### Pattern 2: Conditional Routing

**LangGraph Code:**
```python
def classify_intent(state):
    content = state["messages"][-1].content
    if "?" in content:
        state["next"] = "factual"
    else:
        state["next"] = "creative"
    return state

def route(state):
    return state["next"]

graph.add_conditional_edges(
    "classify_intent",
    route,
    {"factual": "answer_factual", "creative": "answer_creative", END: END}
)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import RouterAgent, RouterConfig

def classify(message: Message) -> str:
    return "factual" if "?" in message.content else "creative"

router = RouterAgent(RouterConfig(
    classifier=classify,
    agents={
        "factual": factual_agent,
        "creative": creative_agent,
    }
))
result = await router.process(message)
```

---

### Pattern 3: Agent ↔ ToolNode Loop (ReAct)

**LangGraph Code:**
```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools=[calculator, search])

def should_continue(state):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "continue"
    return "end"

graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_conditional_edges(
    "agent", should_continue,
    {"continue": "tools", "end": END}
)
graph.add_edge("tools", "agent")
graph.set_entry_point("agent")
app = graph.compile()
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ReActAgent

# ReActAgent implements the exact same agent → tool → agent loop
agent = ReActAgent(llm=llm, tools=[calculator, search])
result = await agent.process(Message(role="user", content="What is 144/12?"))
```

---

### Pattern 4: MemorySaver (Conversation History)

**LangGraph Code:**
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)
config = {"configurable": {"thread_id": "user-42"}}

# First turn
app.invoke({"messages": [HumanMessage("My name is Alex")]}, config)
# Second turn — resumes from saved state
app.invoke({"messages": [HumanMessage("What is my name?")]}, config)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ConversationalAgent

# ConversationalAgent maintains history automatically — no checkpoint setup
agent = ConversationalAgent(llm_client=llm, max_history=20)

await agent.process(Message(role="user", content="My name is Alex"))
response = await agent.process(Message(role="user", content="What is my name?"))
# History maintained across calls — returns "Alex"
```

---

## Step-by-Step Migration

### Step 1: Replace StateGraph with SequentialAgent

```python
# Before
graph = StateGraph(MessagesState)
graph.add_node("step1", fn1)
graph.add_node("step2", fn2)
graph.add_edge("step1", "step2")
app = graph.compile()
result = app.invoke({"messages": [HumanMessage(task)]})

# After
from agenkit.patterns import SequentialAgent
pipeline = SequentialAgent([agent1, agent2])
result = await pipeline.process(Message(role="user", content=task))
```

### Step 2: Replace Conditional Edges with RouterAgent

```python
# Before
graph.add_conditional_edges("node", condition_fn, mapping)

# After
from agenkit.patterns import RouterAgent
router = RouterAgent(RouterConfig(classifier=condition_fn, agents=mapping))
```

### Step 3: Replace ToolNode Loop with ReActAgent

```python
# Before: complex graph wiring for agent+tool loop
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.add_conditional_edges("agent", should_continue, ...)
graph.add_edge("tools", "agent")

# After: one line
agent = ReActAgent(llm=llm, tools=tools)
```

### Step 4: Replace MemorySaver with ConversationalAgent

```python
# Before
memory = MemorySaver()
app = graph.compile(checkpointer=memory)
config = {"configurable": {"thread_id": "42"}}
app.invoke(state, config)

# After
agent = ConversationalAgent(llm_client=llm, max_history=20)
await agent.process(message)  # history managed automatically
```

---

## Testing Your Migration

```python
import pytest
from agenkit import Message
from agenkit.patterns import ReActAgent, RouterAgent, ConversationalAgent

@pytest.mark.asyncio
async def test_router_agent():
    router = RouterAgent(RouterConfig(
        classifier=lambda m: "factual" if "?" in m.content else "creative",
        agents={"factual": factual_agent, "creative": creative_agent},
    ))
    response = await router.process(Message(role="user", content="What is Agenkit?"))
    assert response.content is not None

@pytest.mark.asyncio
async def test_conversation_memory():
    agent = ConversationalAgent(llm_client=mock_llm, max_history=10)
    await agent.process(Message(role="user", content="My name is Alex"))
    response = await agent.process(Message(role="user", content="What is my name?"))
    assert "Alex" in str(response.content)
```

---

## Common Pitfalls

1. **Compile step**: LangGraph requires `graph.compile()` before use — Agenkit agents are ready immediately
2. **State dict**: LangGraph passes state as dicts; Agenkit uses typed `Message` objects
3. **END sentinel**: No need for explicit END in Agenkit — pipeline terminates naturally
4. **Thread IDs**: Agenkit `ConversationalAgent` manages history per instance; for multi-user use multiple agent instances

---

## FAQ

**Q: Does Agenkit support parallel node execution?**
A: Yes, use `ParallelAgent` to run multiple agents concurrently and merge results.

**Q: Can I visualize Agenkit agent graphs?**
A: No built-in visualization; structure is explicit in code. Use OpenTelemetry traces for runtime visibility.

**Q: How do I migrate LangGraph streaming?**
A: Use `agent.process_stream()` which returns an async generator of Message chunks.

**Q: Can I use LangGraph alongside Agenkit?**
A: Yes, wrap a LangGraph app as an Agenkit Tool or Agent for incremental migration.

---

## Reference

- Example: `examples/frameworks/minilanggraph.py`
- TypeScript equivalent: `agenkit-ts/examples/frameworks/minilanggraph.ts`
- Go equivalent: `agenkit-go/examples/frameworks/minilanggraph/main.go`
- Agenkit patterns: `docs/PATTERNS.md`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
