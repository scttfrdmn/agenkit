# Migrating from DSPy to Agenkit

**Target Audience**: Developers using DSPy for declarative LM programming
**Difficulty**: Intermediate
**Time to Read**: 12-15 minutes

---

## Overview

### Why Migrate to Agenkit?

**Language Support**:
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig (DSPy is Python-only)
- Deploy compiled modules 18x faster in Go
- No Python dependency in production services

**Flexibility**:
- **Any LLM**: Any OpenAI-compatible API, Anthropic, local Ollama
- **Explicit prompts**: Full control without optimizer magic
- **Composable patterns**: ReAct, Sequential, Router — not just forward()

**Operational**:
- **No compilation step**: Agents run directly without `dspy.compile()`
- **No training data**: No need for labeled examples to bootstrap
- **OpenTelemetry**: Industry-standard observability

### Key Conceptual Differences

| DSPy | Agenkit | Notes |
|------|---------|-------|
| **Signature** | **System prompt + Message schema** | Explicit |
| **Predict** | **LLM.complete()** | Direct |
| **ChainOfThought** | **Prompt with reasoning field** | Explicit |
| **ReAct** | **ReActAgent** | Direct mapping |
| **Module** | **Agent** base class | Same concept |
| **dspy.LM** | **LLM adapter** | Explicit |
| **dspy.configure(lm=...)** | **Constructor injection** | No global state |
| **forward()** | **process()** | Async |
| **dspy.compile()** | **Not needed** | No optimizer |

### What You Gain

✅ **No optimizer**: Run directly without labeled examples or compilation
✅ **Explicit prompts**: Full control over what the LLM sees
✅ **Multi-language**: Deploy same logic in Go/Rust for production
✅ **No global state**: No `dspy.configure()` — pass LLM explicitly
✅ **Standard observability**: OpenTelemetry instead of DSPy logging

### What You Lose

❌ **Automatic prompt optimization**: No MIPROv2, BootstrapFewShot, etc.
❌ **Metric-driven optimization**: No automatic few-shot example selection
❌ **Assertions**: No `dspy.Assert()` / `dspy.Suggest()` for self-refinement
❌ **Teleprompters**: No gradient-free prompt tuning

---

## Pattern Mapping Table

| DSPy | Agenkit Equivalent | Notes |
|------|-------------------|-------|
| `class QA(dspy.Signature)` | System prompt string + field names | Explicit |
| `Predict(QA)` | `await llm.complete([Message(...)])` | Direct LLM call |
| `ChainOfThought(QA)` | Prompt with "reasoning" output field | Explicit |
| `ReAct(QA, tools=[...])` | `ReActAgent(llm=llm, tools=[...])` | Direct |
| `class MyModule(dspy.Module)` | `class MyAgent(Agent)` | Same OOP |
| `self.prog = Predict(QA)` | `self.llm = llm` | Simpler |
| `def forward(self, **kwargs)` | `async def process(self, message)` | Async |
| `dspy.configure(lm=dspy.LM(...))` | `llm = OpenAILLM(...)` in constructor | No global |
| `dspy.inspect_history()` | OpenTelemetry traces | Standard |

---

## Common Patterns

### Pattern 1: Signature + Predict

**DSPy Code:**
```python
import dspy

class QASignature(dspy.Signature):
    """Answer questions with short factual answers."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

predictor = dspy.Predict(QASignature)
result = predictor(question="What is the capital of France?")
print(result.answer)
```

**Agenkit Equivalent:**
```python
from agenkit.adapters.llm import OpenAILLM
from agenkit import Message

llm = OpenAILLM(model="gpt-4o-mini", api_key=api_key)

# Signature → system prompt describing input/output schema
system_prompt = """Answer questions with short factual answers.
Input: question (string)
Output: answer (string)
Respond with just the answer."""

response = await llm.complete([
    Message(role="system", content=system_prompt),
    Message(role="user", content="question: What is the capital of France?"),
])
print(response.content)  # "Paris"
```

---

### Pattern 2: ChainOfThought

**DSPy Code:**
```python
class ReasonedQA(dspy.Signature):
    """Answer after thinking step by step."""
    question: str = dspy.InputField()
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning")
    answer: str = dspy.OutputField()

cot = dspy.ChainOfThought(ReasonedQA)
result = cot(question="What is 17 * 24?")
print(result.reasoning)
print(result.answer)
```

**Agenkit Equivalent:**
```python
system_prompt = """Answer questions step by step.
Format your response as:
REASONING: <step-by-step reasoning>
ANSWER: <final answer>"""

response = await llm.complete([
    Message(role="system", content=system_prompt),
    Message(role="user", content="What is 17 * 24?"),
])

# Parse REASONING and ANSWER fields
content = str(response.content)
reasoning = content.split("REASONING:")[1].split("ANSWER:")[0].strip()
answer = content.split("ANSWER:")[1].strip()
print(reasoning)
print(answer)
```

---

### Pattern 3: ReAct

**DSPy Code:**
```python
def search(query: str) -> str:
    return f"Search results for: {query}"

class QAWithSearch(dspy.Signature):
    """Answer questions using search when needed."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

react = dspy.ReAct(QAWithSearch, tools=[search])
result = react(question="What year was Agenkit created?")
print(result.answer)
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ReActAgent

class SearchTool:
    name = "search"
    description = "Search for information on a topic"

    async def run(self, query: str) -> str:
        return f"Search results for: {query}"

agent = ReActAgent(llm=llm, tools=[SearchTool()])
response = await agent.process(
    Message(role="user", content="What year was Agenkit created?")
)
print(response.content)
```

---

### Pattern 4: Module Composition

**DSPy Code:**
```python
class MultiHopQA(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.generate_query = dspy.ChainOfThought("context, question -> search_query")
        self.generate_answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question: str) -> dspy.Prediction:
        context = self.retrieve(question).passages
        search_query = self.generate_query(context=context, question=question)
        new_context = self.retrieve(search_query.search_query).passages
        answer = self.generate_answer(context=new_context, question=question)
        return answer

qa = MultiHopQA()
result = qa(question="What framework uses Agenkit patterns?")
```

**Agenkit Equivalent:**
```python
from agenkit import Agent, Message
from agenkit.patterns import SequentialAgent

class MultiHopQA(Agent):
    def __init__(self, llm, retrieval_tool):
        self.llm = llm
        self.retrieval_tool = retrieval_tool

    @property
    def name(self) -> str:
        return "multi_hop_qa"

    @property
    def capabilities(self) -> list[str]:
        return ["multi_hop_question_answering"]

    async def process(self, message: Message) -> Message:
        # Step 1: Retrieve initial context
        context = await self.retrieval_tool.run(query=message.content)

        # Step 2: Generate follow-up query
        query_response = await self.llm.complete([
            Message(role="system", content="Generate a follow-up search query."),
            Message(role="user", content=f"Context: {context}\nQuestion: {message.content}"),
        ])

        # Step 3: Retrieve with refined query
        refined_context = await self.retrieval_tool.run(query=str(query_response.content))

        # Step 4: Generate final answer
        answer = await self.llm.complete([
            Message(role="system", content="Answer the question using the context."),
            Message(role="user", content=f"Context: {refined_context}\nQuestion: {message.content}"),
        ])
        return answer

agent = MultiHopQA(llm=llm, retrieval_tool=retrieval_tool)
response = await agent.process(Message(role="user", content="What framework uses Agenkit patterns?"))
```

---

## Step-by-Step Migration

### Step 1: Replace dspy.configure() with constructor injection

```python
# Before (global state)
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini", api_key=key))

# After (explicit, testable)
from agenkit.adapters.llm import OpenAILLM
llm = OpenAILLM(model="gpt-4o-mini", api_key=key)
```

### Step 2: Replace Signature with system prompt

```python
# Before
class MySig(dspy.Signature):
    """Classify sentiment."""
    text: str = dspy.InputField()
    sentiment: str = dspy.OutputField(desc="positive, negative, or neutral")

# After
system_prompt = "Classify the sentiment of the text. Respond with: positive, negative, or neutral"
```

### Step 3: Replace Predict with llm.complete()

```python
# Before
predictor = dspy.Predict(MySig)
result = predictor(text="I love Agenkit!")
print(result.sentiment)

# After
response = await llm.complete([
    Message(role="system", content=system_prompt),
    Message(role="user", content="text: I love Agenkit!"),
])
print(response.content)
```

### Step 4: Replace ReAct with ReActAgent

```python
# Before
react = dspy.ReAct(QA, tools=[search_fn, calc_fn])
result = react(question="task")

# After
agent = ReActAgent(llm=llm, tools=[SearchTool(), CalcTool()])
result = await agent.process(Message(role="user", content="task"))
```

### Step 5: Replace Module with Agent subclass

```python
# Before
class MyModule(dspy.Module):
    def forward(self, **kwargs):
        ...

# After
class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        ...
```

---

## Testing Your Migration

```python
@pytest.mark.asyncio
async def test_chain_of_thought():
    response = await llm.complete([
        Message(role="system", content="Think step by step. Format: REASONING: ...\nANSWER: ..."),
        Message(role="user", content="What is 6 * 7?"),
    ])
    assert "REASONING" in str(response.content) or "42" in str(response.content)

@pytest.mark.asyncio
async def test_react_agent():
    agent = ReActAgent(llm=mock_llm, tools=[CalcTool()])
    response = await agent.process(Message(role="user", content="What is 6 * 7?"))
    assert "42" in str(response.content)
```

---

## Common Pitfalls

1. **No `dspy.compile()`**: Agenkit runs directly — prompts are static strings, not compiled
2. **Global LM state**: Agenkit has no `dspy.configure()` — always pass LLM explicitly
3. **Output parsing**: DSPy auto-parses structured output fields; Agenkit returns raw strings — parse manually
4. **Assertions**: `dspy.Assert()` and `dspy.Suggest()` have no direct equivalent; implement validation in the agent's `process()` method

---

## FAQ

**Q: Can I use DSPy optimizers (MIPROv2, BootstrapFewShot) with Agenkit prompts?**
A: Yes, optimize prompts externally with DSPy then use the optimized system prompt string in Agenkit.

**Q: Does Agenkit support structured prediction?**
A: Pass a JSON schema in the system prompt and parse the response with Pydantic.

**Q: Is ChainOfThought built into Agenkit?**
A: Add "think step by step" to any system prompt — no special class needed.

---

## Reference

- Python example: `examples/frameworks/minidspy.py`
- Go equivalent: `agenkit-go/examples/frameworks/minidspy/main.go`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
