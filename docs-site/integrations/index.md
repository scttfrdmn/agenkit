# Framework Integrations

Bidirectional integration guides for using Agenkit **with** other agent frameworks.

## Why Integrate?

You don't have to choose one framework! Use Agenkit **with** your existing tools:

- ✅ **Keep** your existing framework investments
- ✅ **Add** Agenkit's middleware and patterns
- ✅ **Combine** strengths of multiple frameworks
- ✅ **Migrate** gradually at your own pace

---

## Available Integrations

### [LangChain ↔ Agenkit](langchain.md)
**Most Popular Integration**

**Use LangChain With Agenkit**:
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

### [CrewAI ↔ Agenkit](crewai.md)
**Team Collaboration**

**Use CrewAI With Agenkit**:
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

### [AutoGen ↔ Agenkit](autogen.md)
**Conversational AI**

**Use AutoGen With Agenkit**:
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
Use framework capabilities as tools in Agenkit agents

### Pattern 2: Agenkit as Component
Use Agenkit agents within framework workflows

### Pattern 3: Hybrid Orchestration
Use both frameworks for their strengths

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

## Migration vs. Integration

**Integration** (recommended): Use Agenkit with your existing framework
- Keep existing code
- Add Agenkit features incrementally
- Combine strengths

**Migration**: Replace framework with Agenkit completely
- See [Migration Guides](../migrations/index.md)
- For when you want to fully adopt Agenkit

---

## Get Started

1. Pick your framework integration guide above
2. Follow the bidirectional examples
3. Start with Pattern 1 (Framework as Tool)
4. Gradually adopt Agenkit features

---

## Related

- [Migration Guides](../migrations/index.md) - Full framework migrations
- [Pattern Library](../patterns/index.md) - Agenkit patterns
- [Examples](../../examples/integrations/) - Working integration code

---

For complete integration guides, see [docs/integrations/](../../docs/integrations/) in the repository.
