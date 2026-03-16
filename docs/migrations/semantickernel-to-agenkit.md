# Migrating from Semantic Kernel to Agenkit

**Target Audience**: Developers using Microsoft Semantic Kernel for enterprise AI orchestration
**Difficulty**: Intermediate
**Time to Read**: 12-15 minutes

---

## Overview

### Why Migrate to Agenkit?

**Performance**:
- **18x faster** in Go vs Python-based SK for production workloads
- Sub-millisecond plugin invocation overhead
- True parallelism in Go (no GIL)

**Simplicity**:
- **No plugin XML/YAML metadata**: Functions are plain Python classes
- **No `Kernel` singleton**: Compose agents directly
- **Unified API**: Same patterns in Python, Go, TypeScript, Rust, C++, Zig

**Flexibility**:
- **Any LLM**: Not tied to Azure OpenAI or OpenAI API
- **No .NET runtime**: Pure Python/Go/TypeScript — no cross-runtime complexity
- **Explicit orchestration**: No hidden planner magic

### Key Conceptual Differences

| Semantic Kernel | Agenkit | Notes |
|----------------|---------|-------|
| **Kernel** | **Agent registry + LLM adapter** | Lighter |
| **KernelPlugin** | **Tool collection** | Same concept |
| **KernelFunction (native)** | **Tool class** | Cleaner API |
| **KernelFunction (semantic)** | **Agent with prompt template** | Explicit |
| **KernelArguments** | **Message content + metadata** | Simpler |
| **ChatHistory** | **ConversationalAgent history** | Built-in |
| **ChatCompletionService** | **LLM adapter** | Same concept |
| **SequentialPlanner** | **SequentialAgent** | Direct mapping |
| **kernel.invoke()** | **agent.process()** | Async |
| **kernel.invoke_prompt()** | **LLM.complete()** | Direct |

### What You Gain

✅ **Multi-language**: Python, Go, TypeScript, Rust, C++, Zig (SK is primarily .NET/Python)
✅ **Simpler setup**: No Kernel configuration, plugin registration overhead
✅ **Production middleware**: Circuit breakers, retry, timeout
✅ **OpenTelemetry**: Industry-standard observability
✅ **No XML/YAML skill files**: All configuration in code

### What You Lose

❌ **Azure integration**: No native Azure AI Foundry, Azure OpenAI, Azure Cognitive Search
❌ **Enterprise SK ecosystem**: No SK Hub community plugins
❌ **Memory stores**: No built-in Azure AI Search or Pinecone plugin
❌ **Process Framework**: No SK Process orchestration for long-running workflows

---

## Pattern Mapping Table

| Semantic Kernel | Agenkit Equivalent | Notes |
|----------------|-------------------|-------|
| `Kernel()` | `OpenAILLM(...)` + agent composition | Lighter |
| `kernel.add_service(ChatCompletionService)` | `llm = OpenAILLM(...)` | Direct |
| `KernelPlugin(name, functions)` | Group of `Tool` objects | Same concept |
| `@kernel_function(name, description)` | `Tool` class with `name`/`description` | Same |
| `kernel.invoke(fn, KernelArguments(...))` | `await tool.run(...)` | Async |
| `kernel.invoke_prompt(template, args)` | `await llm.complete([Message(...)])` | Direct |
| `ChatHistory()` | `ConversationalAgent` built-in | Automatic |
| `history.add_user_message(text)` | `Message(role="user", content=text)` | Same |
| `history.add_assistant_message(text)` | `Message(role="assistant", content=text)` | Same |
| `SequentialPlanner` | `SequentialAgent([...])` | Simpler |
| `FunctionChoiceBehavior.Auto()` | `ReActAgent` tool dispatch | Built-in |

---

## Common Patterns

### Pattern 1: Kernel Setup + Plugin Registration

**Semantic Kernel Code:**
```python
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(
    service_id="gpt4",
    ai_model_id="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
))

class MathPlugin:
    @kernel_function(name="add", description="Add two numbers")
    def add(self, a: float, b: float) -> float:
        return a + b

kernel.add_plugin(MathPlugin(), plugin_name="math")
result = await kernel.invoke(
    kernel.get_function("math", "add"),
    KernelArguments(a=3, b=4)
)
```

**Agenkit Equivalent:**
```python
from agenkit.adapters.llm import OpenAILLM
from agenkit.patterns import ReActAgent
from agenkit import Message

llm = OpenAILLM(model="gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])

class AddTool:
    name = "add"
    description = "Add two numbers"

    async def run(self, a: float, b: float) -> float:
        return a + b

agent = ReActAgent(llm=llm, tools=[AddTool()])
result = await agent.process(Message(role="user", content="Add 3 and 4"))
```

---

### Pattern 2: Semantic Functions (Prompt Templates)

**Semantic Kernel Code:**
```python
prompt_template = """
You are a helpful assistant.
User: {{$input}}
Assistant:"""

semantic_fn = kernel.create_function_from_prompt(
    function_name="chat",
    plugin_name="ChatPlugin",
    prompt=prompt_template,
)
result = await kernel.invoke(semantic_fn, KernelArguments(input="Hello!"))
print(result)
```

**Agenkit Equivalent:**
```python
from agenkit import Message
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(model="gpt-4o-mini", api_key=api_key)
system_prompt = "You are a helpful assistant."

response = await llm.complete([
    Message(role="system", content=system_prompt),
    Message(role="user", content="Hello!"),
])
print(response.content)
```

---

### Pattern 3: ChatHistory (Conversational Memory)

**Semantic Kernel Code:**
```python
from semantic_kernel.contents.chat_history import ChatHistory

chat_history = ChatHistory()
chat_history.add_system_message("You are a helpful assistant.")
chat_history.add_user_message("My name is Alex")

service = kernel.get_service("gpt4")
result = await service.get_chat_message_content(chat_history, settings)
chat_history.add_assistant_message(str(result))

chat_history.add_user_message("What is my name?")
result2 = await service.get_chat_message_content(chat_history, settings)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ConversationalAgent

# History managed automatically — no manual ChatHistory tracking
agent = ConversationalAgent(llm_client=llm, max_history=20)
await agent.process(Message(role="user", content="My name is Alex"))
response = await agent.process(Message(role="user", content="What is my name?"))
```

---

### Pattern 4: Sequential Planner

**Semantic Kernel Code:**
```python
from semantic_kernel.planners import SequentialPlanner

planner = SequentialPlanner(kernel)
plan = await planner.create_plan("Research and summarize Agenkit features")
result = await plan.invoke(kernel)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import SequentialAgent

pipeline = SequentialAgent([research_agent, summarize_agent])
result = await pipeline.process(
    Message(role="user", content="Research and summarize Agenkit features")
)
```

---

### Pattern 5: Function Choice (Auto Tool Dispatch)

**Semantic Kernel Code:**
```python
from semantic_kernel.connectors.ai import FunctionChoiceBehavior

settings = kernel.get_prompt_execution_settings_from_service_id("gpt4")
settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

result = await kernel.invoke_prompt(
    "What is the weather in Seattle?",
    KernelArguments(settings=settings),
)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ReActAgent

# ReActAgent automatically selects and calls tools
agent = ReActAgent(llm=llm, tools=[weather_tool])
result = await agent.process(
    Message(role="user", content="What is the weather in Seattle?")
)
```

---

## Step-by-Step Migration

### Step 1: Replace Kernel initialization

```python
# Before
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(ai_model_id="gpt-4o-mini", api_key=key))

# After
from agenkit.adapters.llm import OpenAILLM
llm = OpenAILLM(model="gpt-4o-mini", api_key=key)
```

### Step 2: Replace KernelPlugins with Tool classes

```python
# Before
class EmailPlugin:
    @kernel_function(name="send_email", description="Send an email")
    async def send_email(self, recipient: str, subject: str, body: str) -> str:
        ...
kernel.add_plugin(EmailPlugin(), plugin_name="email")

# After
class SendEmailTool:
    name = "send_email"
    description = "Send an email"
    async def run(self, recipient: str, subject: str, body: str) -> str:
        ...
```

### Step 3: Replace kernel.invoke() with agent.process()

```python
# Before
result = await kernel.invoke(kernel.get_function("email", "send_email"),
                              KernelArguments(recipient="...", subject="...", body="..."))

# After
agent = ReActAgent(llm=llm, tools=[SendEmailTool()])
result = await agent.process(Message(role="user", content="Send email to ..."))
```

### Step 4: Replace ChatHistory with ConversationalAgent

```python
# Before
chat_history = ChatHistory()
chat_history.add_user_message(text)
result = await service.get_chat_message_content(chat_history, settings)

# After
agent = ConversationalAgent(llm_client=llm)
result = await agent.process(Message(role="user", content=text))
```

---

## Common Pitfalls

1. **`KernelArguments`**: Agenkit passes arguments directly or through message content — no typed argument container
2. **Plugin XML files**: Agenkit has no equivalent — all metadata is in Python/Go code
3. **Service IDs**: Agenkit doesn't use service registration — construct LLM adapters directly
4. **Sync invoke**: SK has async `.invoke()` like Agenkit but also sync paths — Agenkit is always async

---

## Reference

- Example: `examples/frameworks/minisemantickernel.py`
- Go equivalent: `agenkit-go/examples/frameworks/minisemantickernel/main.go`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
