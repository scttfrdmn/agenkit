# Framework Integration Guides

Bidirectional integration guides for using Agenkit with other agent frameworks.

## Why Integrate?

You don't have to choose one framework! Use Agenkit **with** your existing tools:

- ✅ **Keep** your existing framework investments
- ✅ **Add** Agenkit's middleware and patterns
- ✅ **Combine** strengths of multiple frameworks
- ✅ **Migrate** gradually at your own pace

---

## Available Integrations

### [LangChain + Agenkit](./langchain-integration.md)
**Most Popular Integration**

**Use Agenkit With**:
- LangChain chains and agents
- LangGraph state machines
- Vectorstores and document loaders

**Get From Agenkit**:
- Middleware (retry, circuit breaker, caching)
- Better observability
- Cross-language support

**Example**:
```python
# Use LangChain vectorstore with Agenkit orchestration
vectorstore = Chroma.from_documents(docs, embeddings)  # LangChain
orchestrator = OrchestrationAgent(llm=llm)              # Agenkit

# Best of both!
```

---

### [CrewAI + Agenkit](./crewai-integration.md)
**Team Collaboration**

**Use Agenkit With**:
- CrewAI role-based teams
- Delegation and collaboration
- Task management

**Get From Agenkit**:
- Orchestration patterns
- Middleware stack
- Enhanced observability

**Example**:
```python
# CrewAI for teams, Agenkit for orchestration
crew = Crew(agents=[writer, editor], tasks=tasks)  # CrewAI
orchestrator = OrchestrationAgent(llm=llm)          # Agenkit

# Orchestrate multiple crews!
```

---

### [AutoGen + Agenkit](./autogen-integration.md)
**Conversational AI**

**Use Agenkit With**:
- AutoGen multi-agent conversations
- Code execution capabilities
- Group chats

**Get From Agenkit**:
- Pattern library
- Middleware and error handling
- Production readiness

**Example**:
```python
# AutoGen for conversations, Agenkit for patterns
group_chat = GroupChat(agents=autogen_agents)  # AutoGen
orchestrator = OrchestrationAgent(llm=llm)     # Agenkit

# Orchestrate conversations!
```

---

## Integration Patterns

### Pattern 1: Framework as Tool
Use framework capabilities as tools in Agenkit:

```python
# Example: LangChain vectorstore as Agenkit tool
class RAGAgent(Agent):
    def __init__(self, vectorstore):  # LangChain
        self.vectorstore = vectorstore

    async def process(self, message):
        docs = self.vectorstore.similarity_search(message.content)
        # Process with Agenkit patterns...
```

### Pattern 2: Agenkit as Component
Use Agenkit agents within framework workflows:

```python
# Example: Agenkit agent in LangChain chain
from langchain.tools import BaseTool

class AgenkitTool(BaseTool):
    def __init__(self, agent):  # Agenkit
        self.agent = agent

    def _run(self, query):
        return asyncio.run(self.agent.process(Message(...)))
```

### Pattern 3: Hybrid Orchestration
Use both frameworks for their strengths:

```python
# Example: Framework for specialty, Agenkit for orchestration
class HybridSystem:
    def __init__(self, langchain_rag, crewai_team):
        self.rag = langchain_rag          # LangChain specialty
        self.team = crewai_team           # CrewAI specialty
        self.orchestrator = OrchestrationAgent()  # Agenkit orchestration

    async def process(self, query):
        # Agenkit orchestrates both!
```

---

## Quick Comparison

| Framework | Best For | Integrate With Agenkit For |
|-----------|----------|----------------------------|
| **LangChain** | RAG, chains, vectorstores | Middleware, observability, patterns |
| **CrewAI** | Role-based teams, delegation | Orchestration, cross-language |
| **AutoGen** | Conversations, code execution | Patterns, production readiness |
| **Strands** | AWS native, A2A protocol | Unified interface, middleware |
| **smolagents** | Hugging Face models, lightweight | Enterprise patterns, scaling |

---

## Migration Strategy

### Step 1: Integrate (Don't Replace)
```python
# Keep using your framework
existing_system = YourFrameworkSystem()

# Add Agenkit benefits
from agenkit.middleware import RetryMiddleware, TracingMiddleware

# Wrap with Agenkit
enhanced = TracingMiddleware(adapt(existing_system))
```

### Step 2: Add Patterns
```python
# Use Agenkit patterns alongside framework
from agenkit.patterns import OrchestrationAgent

orchestrator = OrchestrationAgent()
# Orchestrates your existing framework components
```

### Step 3: Gradually Adopt
```python
# Replace components one at a time
pipeline = SequentialAgent([
    legacy_component_1,        # Still using framework
    new_agenkit_agent,         # New Agenkit component
    legacy_component_2,        # Still using framework
])
```

---

## Best Practices

### ✅ DO:
- Start with integration, not replacement
- Use each framework for its strengths
- Add Agenkit middleware gradually
- Test hybrid systems thoroughly

### ❌ DON'T:
- Force migration before you're ready
- Duplicate functionality unnecessarily
- Ignore framework-specific best practices
- Skip integration testing

---

## Common Patterns

### Pattern: RAG with Multiple Frameworks

```python
"""
Use best RAG tools from any framework:
- LangChain: Document loaders, text splitters
- Agenkit: Orchestration, middleware
"""

from langchain.document_loaders import DirectoryLoader
from langchain.vectorstores import Chroma
from agenkit.patterns import OrchestrationAgent

class HybridRAG:
    def __init__(self):
        # LangChain for RAG components
        self.loader = DirectoryLoader('./docs')
        self.vectorstore = Chroma.from_documents(...)

        # Agenkit for orchestration
        self.orchestrator = OrchestrationAgent(...)

    async def query(self, question):
        # Retrieve with LangChain
        docs = self.vectorstore.similarity_search(question)

        # Orchestrate with Agenkit
        response = await self.orchestrator.process(...)

        return response
```

### Pattern: Team Collaboration with Middleware

```python
"""
Use CrewAI teams with Agenkit middleware:
- CrewAI: Role-based collaboration
- Agenkit: Retry, caching, tracing
"""

from crewai import Crew
from agenkit.middleware import RetryMiddleware, CachingMiddleware

class EnhancedCrew(Agent):
    def __init__(self, crew: Crew):
        self.crew = crew

    async def process(self, message):
        # Execute crew
        result = self.crew.kickoff()
        return Message(content=result)

# Add Agenkit middleware
crew = Crew(agents=[...], tasks=[...])
enhanced = EnhancedCrew(crew)
enhanced = CachingMiddleware(enhanced)     # Add caching
enhanced = RetryMiddleware(enhanced)       # Add retries
```

---

## Framework Compatibility Matrix

| Feature | LangChain | CrewAI | AutoGen | Agenkit |
|---------|-----------|--------|---------|---------|
| RAG/Vectorstores | ✅✅✅ | ❌ | ❌ | ⚠️ |
| Role-based Teams | ❌ | ✅✅✅ | ⚠️ | ⚠️ |
| Conversations | ⚠️ | ⚠️ | ✅✅✅ | ✅ |
| Middleware | ❌ | ❌ | ❌ | ✅✅✅ |
| Observability | ⚠️ | ⚠️ | ⚠️ | ✅✅✅ |
| Cross-language | ❌ | ❌ | ❌ | ✅✅✅ |
| Patterns | ⚠️ | ⚠️ | ⚠️ | ✅✅✅ |

**✅✅✅** = Excellent | **✅** = Good | **⚠️** = Limited | **❌** = Not Available

---

## Getting Help

- **Questions?** [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- **Issues?** [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- **Examples?** [Integration Examples](../../examples/integrations/)

---

## Related Documentation

- [Migration Guides](../migrations/) - Full framework migrations
- [Pattern Library](../patterns/) - All Agenkit patterns
- [Tutorials](../../tutorials/) - Step-by-step guides
- [API Reference](https://agenkit.dev/api/) - Complete API docs

---

**Remember**: You don't have to choose! Use the best tool for each job. 🎯
