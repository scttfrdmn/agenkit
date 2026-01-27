# MiniChain - LangChain/LangGraph Patterns on Agenkit

**~350 LOC demonstration of how to build LangChain-like abstractions ON TOP of Agenkit primitives.**

## Key Insight

LangChain's abstractions are just **composition patterns** over basic LLM calls. You don't need a framework - just function composition + agents.

## What is MiniChain?

MiniChain demonstrates that popular framework features can be built as **lightweight patterns** using Agenkit's minimal interface:

- **Chain**: Base interface for composable components
- **LLMChain**: Prompt template + LLM execution
- **ConversationChain**: Memory-aware chat with context management
- **RunnablePassthrough**: Pass data through unchanged
- **RunnableLambda**: Wrap any function as a chain
- **Pipe operator** (`|`): LCEL-style composition

## Architecture Comparison

### LangChain Way
```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI()
prompt = PromptTemplate(template="Explain {topic}")
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(topic="AI")
```

### MiniChain Way
```python
from agenkit.adapters.llm import OpenAILLM
from minichain import LLMChain

llm = OpenAILLM()
chain = LLMChain(agent=llm, prompt_template="Explain {topic}")
result = await chain.invoke({"topic": "AI"})
```

**Differences:**
- ✅ Simpler - Just agents + composition
- ✅ No framework lock-in - You own the patterns
- ✅ Explicit - Clear what's happening
- ✅ Minimal - ~350 LOC vs thousands in LangChain

## Core Components

### 1. Chain Interface

```python
class Chain(ABC):
    @abstractmethod
    async def invoke(self, input_data: Any) -> Any:
        pass

    def __or__(self, other: "Chain") -> "Chain":
        return SequenceChain([self, other])
```

Every component is a `Chain` with:
- `invoke()` - Process input → output
- `|` operator - Compose chains together

### 2. LLMChain

```python
chain = LLMChain(
    agent=openai_agent,
    prompt_template="Summarize this: {text}",
    system_message="You are a helpful assistant"
)

result = await chain.invoke({"text": "..."})
```

**What it does:**
1. Formats prompt with variables
2. Sends to LLM
3. Returns response

### 3. ConversationChain

```python
chat = ConversationChain(
    agent=openai_agent,
    system_message="You are a coding tutor",
    max_history=10  # Context window management
)

# Multi-turn conversation
await chat.invoke("Explain variables")
await chat.invoke("Can you show an example?")  # Remembers context
```

**Features:**
- Maintains conversation history
- Context window management (keeps last N messages)
- Automatic memory cleanup

### 4. Composition with Pipe Operator

```python
# Research → Write → Edit pipeline
pipeline = (
    research_chain
    | RunnableLambda(transform)
    | write_chain
    | RunnableLambda(transform)
    | edit_chain
)

result = await pipeline.invoke({"topic": "AI"})
```

**Just like LCEL!** But simpler - it's just function composition.

## Examples

### Example 1: Basic Chain ([01_basic_chain.py](01_basic_chain.py))

```python
# Simple LLM call
chain = LLMChain(
    agent=llm,
    prompt_template="Explain {topic} in one sentence"
)
result = await chain.invoke({"topic": "quantum computing"})

# With transformations
chain = (
    RunnableLambda(uppercase)
    | LLMChain(agent=llm, prompt_template="Define {topic}")
    | RunnableLambda(add_emoji)
)
```

**Demonstrates:**
- Basic prompt → LLM → output
- Pipe operator composition
- Pre/post-processing transformations

### Example 2: Multi-Step Pipeline ([02_multistep_pipeline.py](02_multistep_pipeline.py))

```python
# Research → Write → Edit
pipeline = (
    research_chain
    | RunnableLambda(prepare_writing)
    | write_chain
    | RunnableLambda(prepare_editing)
    | edit_chain
)

result = await pipeline.invoke({"topic": "AI"})
```

**Demonstrates:**
- Real-world content generation
- Multiple specialized chains
- Data transformation between steps

### Example 3: Conversation Chain ([03_conversation_chain.py](03_conversation_chain.py))

```python
chat = ConversationChain(
    agent=llm,
    system_message="You are a coding tutor",
    max_history=10
)

# Multi-turn with memory
await chat.invoke("Explain variables")
await chat.invoke("Show me an example")  # Remembers previous
await chat.invoke("How do I use them in functions?")  # Full context
```

**Demonstrates:**
- Memory-aware conversations
- Context window management
- History clearing
- Specialized personalities

## Why MiniChain?

### 1. **Educational**
Shows that "frameworks" are often just patterns. You can build them yourself when needed.

### 2. **No Lock-In**
You own the code. Extend it, modify it, or replace it as your needs evolve.

### 3. **Transparent**
~350 LOC you can read and understand in an afternoon. No magic, no surprises.

### 4. **Production-Ready**
These patterns are used in production systems. They're not toys.

## When to Use MiniChain Patterns

✅ **Use these patterns when:**
- You need sequential pipelines (research → write → edit)
- You want conversational memory
- You need simple LLM chaining
- You value code clarity over framework features

❌ **Use LangChain when:**
- You need their extensive integrations
- You want their pre-built agents
- You need LangSmith tracing
- Team is already familiar with it

## Performance

**Zero overhead** vs calling Agenkit agents directly:
- Chains are simple wrappers
- Pipe operator creates flat sequences
- No dynamic dispatch on hot path

## Migration from LangChain

### LLMChain
```python
# LangChain
from langchain.chains import LLMChain
chain = LLMChain(llm=llm, prompt=prompt)

# MiniChain
from minichain import LLMChain
chain = LLMChain(agent=agent, prompt_template="...")
```

### ConversationChain
```python
# LangChain
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(k=10)
chain = ConversationChain(llm=llm, memory=memory)

# MiniChain
from minichain import ConversationChain
chain = ConversationChain(agent=agent, max_history=10)
```

### LCEL Pipe Operator
```python
# LangChain LCEL
chain = prompt | llm | parser

# MiniChain
chain = prompt_chain | llm_chain | parser_chain
```

**Same patterns, simpler implementation.**

## Files

- `minichain.py` - Core implementation (~350 LOC)
- `01_basic_chain.py` - Basic patterns (~100 LOC)
- `02_multistep_pipeline.py` - Multi-step workflows (~150 LOC)
- `03_conversation_chain.py` - Memory-aware chat (~150 LOC)
- `README.md` - This file

**Total: ~750 LOC** (including examples)

## Running Examples

```bash
# Set API key
export OPENAI_API_KEY=your-key-here

# Run examples
python 01_basic_chain.py
python 02_multistep_pipeline.py
python 03_conversation_chain.py
```

## Key Takeaways

1. **Frameworks are patterns** - You can build them when needed
2. **Composition > Framework** - Simple patterns compose better
3. **Read the code** - ~350 LOC is easy to understand
4. **You own it** - Extend, modify, or replace as needed

## Next Steps

- Try the examples
- Read the source (`minichain.py`)
- Build your own patterns
- Compare with LangChain's implementation

**Remember:** This is a demonstration, not a production framework. Use these patterns as inspiration for building exactly what you need.
