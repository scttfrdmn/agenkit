# What is Agenkit? (And What It's Not)

## The Elevator Pitch

**Agenkit is infrastructure, not a framework.**

Think of it like Express.js for Node or Flask for Python - it provides the foundational building blocks for building agent systems, but **you** decide what to build on top of it.

## What Agenkit IS

### 1. **A Minimal Interface Standard**

```python
class Agent:
    name: str
    async def process(message: Message) -> Message
```

**That's the entire core interface.** Everything else is optional.

**What this means:**
- Write agents that conform to this interface
- They'll work with any Agenkit middleware or transport
- You can swap implementations without changing code
- Cross-language compatibility (Python ↔ Go ↔ Rust)

### 2. **Production Infrastructure Components**

Agenkit provides **optional, modular** production infrastructure:

```python
# Use what you need, ignore the rest
from agenkit.middleware import RetryMiddleware      # Optional
from agenkit.middleware import CircuitBreaker       # Optional
from agenkit.observability import TracingMiddleware # Optional
from agenkit.adapters import HTTPServer             # Optional
```

**Each component is independent:**
- Works standalone
- <200 lines of code
- Easy to understand, modify, or replace
- No hidden dependencies

### 3. **A Foundation for Building Frameworks**

Agenkit is designed to be the **foundation layer** that frameworks build on:

```
Your Framework (LangChain, CrewAI, AutoGPT, etc.)
    ↓
Agenkit Core Interfaces
    ↓
Your Application
```

**What this enables:**
- Build your own opinionated framework
- Mix and match components from different frameworks
- Gradually adopt features as you need them
- Not locked into "all or nothing"

### 4. **A Path from Prototype to Production**

```
Day 1: Simple Agent
┌──────────────────────────┐
│ agent = MyAgent()        │
│ response = agent.process │
└──────────────────────────┘

Day 30: Add Resilience
┌──────────────────────────────────────┐
│ agent = RetryMiddleware(MyAgent())  │
│ agent = CircuitBreaker(agent)       │
└──────────────────────────────────────┘

Day 90: Deploy Distributed
┌─────────────────────────────────────────────┐
│ HTTPServer(agent).start()  # Service A     │
│ GRPCServer(agent).start()  # Service B     │
│ # Kubernetes autoscaling, metrics, traces  │
└─────────────────────────────────────────────┘
```

**Key insight:** You don't rewrite your agents. You add infrastructure around them.

## What Agenkit IS NOT

### ❌ Not a Complete Framework

Agenkit does **not** provide:
- Pre-built agents
- Prompt templates
- Vector database integrations
- LLM provider APIs
- RAG pipelines
- Memory management strategies (beyond the optional packages)
- Tool calling conventions

**Why?** Because these are opinionated choices that belong in frameworks built **on top** of Agenkit.

### ❌ Not Opinionated About Agent Design

Agenkit doesn't care:
- How you structure your agent's logic
- Which LLM provider you use
- How you manage context/memory
- What tools you integrate
- How you parse responses

**Why?** Because you know your use case better than we do.

### ❌ Not a Batteries-Included Solution

If you want:
- Pre-configured agent templates → Use LangChain
- Autonomous agent behaviors → Use AutoGPT
- Multi-agent orchestration → Use CrewAI

Agenkit is the infrastructure layer these frameworks can build on.

### ❌ Not Trying to Replace Existing Frameworks

**Agenkit complements existing frameworks, it doesn't compete with them.**

```python
# Use LangChain for agent logic
from langchain import ConversationalAgent

# Use Agenkit for infrastructure
from agenkit.middleware import RetryMiddleware
from agenkit.observability import TracingMiddleware

# Wrap LangChain agent with Agenkit infrastructure
agent = TracingMiddleware(
    RetryMiddleware(
        ConversationalAgent(...)
    )
)
```

## How You Should Use Agenkit

### Path 1: Keep It Simple

```python
from agenkit import Agent, Message

# Just implement the interface
class MyAgent(Agent):
    async def process(self, message):
        return call_llm(message)

# Use it directly
agent = MyAgent()
response = await agent.process(message)
```

**Perfect for:**
- Prototypes
- Internal tools
- Simple applications
- Learning

### Path 2: Add Production Features As Needed

```python
from agenkit.middleware import RetryMiddleware, CircuitBreaker, TimeoutMiddleware

# Start simple
agent = MyAgent()

# Add features when you need them
agent = TimeoutMiddleware(agent, timeout=30.0)
agent = RetryMiddleware(agent, max_attempts=3)
agent = CircuitBreaker(agent)
```

**Perfect for:**
- Growing applications
- Adding resilience incrementally
- Production deployments

### Path 3: Build a Framework on Top

```python
# Your framework's main abstraction
class MyFrameworkAgent:
    def __init__(self, llm, tools, memory):
        self.llm = llm
        self.tools = tools
        self.memory = memory

    # Implement Agenkit interface
    async def process(self, message):
        # Your framework's logic
        context = self.memory.get_context()
        tool_results = await self.use_tools(message)
        response = await self.llm.generate(context, tool_results)
        return response
```

**Perfect for:**
- Framework builders
- Opinionated solutions
- Domain-specific abstractions

## The Agenkit Philosophy

### 1. **Start Simple, Add Complexity Only When Needed**

```python
# Day 1 - Works perfectly
agent = MyAgent()

# Month 6 - Still the same agent, now production-ready
agent = TimeoutMiddleware(
    RetryMiddleware(
        CircuitBreaker(
            TracingMiddleware(MyAgent())
        )
    )
)
```

### 2. **Own Your Abstractions**

```python
# Don't like our retry logic? Write your own.
class MyCustomRetry:
    async def process(self, message):
        # Your custom logic here
        pass

# Still works with everything else
agent = CircuitBreaker(MyCustomRetry(base_agent))
```

### 3. **No Lock-In**

```python
# Use Agenkit interfaces
class Agent:
    async def process(message) -> Message

# Your agent implements this
# Agenkit provides infrastructure for this
# But you can replace any part
```

## Decision Tree: Should You Use Agenkit?

### ✅ Use Agenkit If:

- You're building a custom agent system
- You need production infrastructure (retries, circuit breakers, tracing)
- You want language flexibility (Python ↔ Go ↔ Rust)
- You're building a framework on top
- You want modular, replaceable components

### ⚠️ Consider Alternatives If:

- You want pre-built agents → Try **LangChain**
- You want autonomous agents → Try **AutoGPT** or **BabyAGI**
- You want multi-agent crews → Try **CrewAI**
- You want RAG out-of-the-box → Try **LlamaIndex**
- You want UI builders → Try **Flowise** or **LangFlow**

### ❌ Don't Use Agenkit If:

- You're building a simple one-off script
- You need a complete solution TODAY
- You're not comfortable with "build your own" philosophy
- You need hand-holding and pre-made templates

## Comparison with Existing Tools

### Agenkit vs. LangChain

**LangChain:**
- Opinionated framework with pre-built components
- Rich ecosystem of integrations
- Batteries-included approach
- Can be complex for simple use cases

**Agenkit:**
- Minimal infrastructure layer
- Bring your own components
- Start simple, add complexity as needed
- Can be used WITH LangChain

**Use both:** Agenkit for infrastructure, LangChain for agent logic

### Agenkit vs. AutoGPT/BabyAGI

**AutoGPT/BabyAGI:**
- Pre-built autonomous agent behaviors
- Specific agent architectures
- Research-focused

**Agenkit:**
- Infrastructure for building ANY agent architecture
- Production-focused
- No opinion on agent behavior

**Use both:** Build AutoGPT-style agents on Agenkit infrastructure

### Agenkit vs. CrewAI

**CrewAI:**
- Multi-agent orchestration framework
- Role-based agent systems
- Opinionated about agent collaboration

**Agenkit:**
- Single/multi-agent infrastructure
- No opinion on collaboration patterns
- Build your own orchestration

**Use both:** Implement CrewAI patterns on Agenkit infrastructure

## The Vision: Where Can You Go?

### With Agenkit, You Can Build:

1. **Simple Tools**
   ```python
   # A single agent, no complexity
   agent = MyAgent()
   ```

2. **Production Services**
   ```python
   # Add infrastructure as you scale
   agent = TracingMiddleware(
       RetryMiddleware(MyAgent())
   )
   HTTPServer(agent).start()
   ```

3. **Custom Frameworks**
   ```python
   # Build your own opinionated framework
   class MyFramework:
       def __init__(self):
           self.agents = []
       def add_agent(self, agent: Agent):
           # Your framework logic
           pass
   ```

4. **Hybrid Systems**
   ```python
   # Mix different agent frameworks
   from langchain import LangChainAgent
   from autogpt import AutoGPTAgent

   # All work with Agenkit infrastructure
   agent1 = TracingMiddleware(LangChainAgent())
   agent2 = TracingMiddleware(AutoGPTAgent())
   ```

## Summary

**Agenkit is:**
- ✅ Infrastructure for building agent systems
- ✅ A minimal, stable interface
- ✅ Optional, modular production features
- ✅ A foundation for frameworks
- ✅ Language-agnostic

**Agenkit is not:**
- ❌ A complete framework
- ❌ Opinionated about agent design
- ❌ Batteries-included
- ❌ Replacing existing frameworks

**Use Agenkit when you want:**
- Control over your architecture
- Production infrastructure without bloat
- Gradual adoption of features
- Cross-language compatibility
- To build your own framework

**Use something else when you want:**
- Pre-built agents and templates
- Quick start with minimal code
- Opinionated best practices
- Domain-specific solutions

---

**The bottom line:** Agenkit gives you the tools. You decide what to build.
