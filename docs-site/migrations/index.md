# Migration Guides

Complete guides for migrating from other frameworks to Agenkit.

## Available Migration Guides

### [LangChain → Agenkit](langchain-to-agenkit.md)
**Most Common Migration**

Migrate from LangChain/LangGraph to Agenkit for:
- Better performance (18x faster in Go)
- Simpler architecture
- Cross-language support
- Production-ready patterns

**Covers**:
- Chains → Sequential agents
- LangGraph → Orchestration
- Tools → Agenkit tools
- Memory → Memory patterns

---

### [CrewAI → Agenkit](crewai-to-agenkit.md)
**Team-Based Migration**

Migrate from CrewAI for:
- More flexible agent patterns
- Better middleware support
- Cross-language capabilities
- Production observability

**Covers**:
- Crews → Multiagent pattern
- Tasks → Task pattern
- Roles → Agent specialization

---

### [AutoGen → Agenkit](autogen-to-agenkit.md)
**Conversation Migration**

Migrate from AutoGen for:
- Production readiness
- Better error handling
- Middleware stack
- Cross-language support

**Covers**:
- Group chats → Conversational pattern
- Code execution → Tool integration
- Agents → Agenkit agents

---

### [AWS Strands → Agenkit](strands-to-agenkit.md)
**AWS Migration**

Migrate from AWS Strands for:
- Cloud-agnostic deployment
- More agent patterns
- Better observability
- Open source

**Covers**:
- A2A protocol → Agents-as-Tools
- AWS services → Generic adapters
- Orchestration → Orchestration pattern

---

### [smolagents → Agenkit](smolagents-to-agenkit.md)
**Hugging Face Migration**

Migrate from smolagents for:
- Enterprise features
- Production patterns
- Cross-language support
- Better scaling

**Covers**:
- Code agents → ReAct pattern
- Tools → Agenkit tools
- Simple agents → Pattern library

---

## Migration Strategy

### Step 1: Integrate (Don't Replace)
```python
# Keep using your framework
existing_system = YourFrameworkSystem()

# Add Agenkit benefits
from agenkit.middleware import RetryMiddleware, TracingMiddleware
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

## Or: Use Both (Integration)

Don't want to migrate? Use [Framework Integrations](../integrations/index.md) instead!

**Integration** keeps your existing framework and adds Agenkit features.

---

## Cross-Language Migration

Migrating to a different language? See [Cross-Language Migration](cross-language.md):

- Python → Go (18x performance)
- Python → TypeScript (browser support)
- Python → Rust (memory safety)
- Any → Any (unified API)

---

## Why Migrate to Agenkit?

**Performance**:
- Go: 18x faster than Python
- Rust: Memory-safe with zero-cost abstractions
- C++: Maximum performance

**Patterns**:
- 11 production-tested patterns
- 6 advanced reasoning techniques
- Composable and reusable

**Production**:
- Full middleware stack
- OpenTelemetry observability
- Production-grade error handling

**Cross-Language**:
- Python, Go, TypeScript, Rust, C++, Zig
- Interoperable across languages
- Shared protocols

---

## Get Started

1. Pick your framework migration guide
2. Follow the step-by-step examples
3. Start with integration (Step 1)
4. Migrate gradually (Steps 2-3)

---

## Related

- [Framework Integrations](../integrations/index.md) - Use both frameworks
- [Pattern Library](../patterns/index.md) - Agenkit patterns
- [Tutorials](../tutorials/index.md) - Learn Agenkit

---

For complete migration guides, see [docs/migrations/](../../docs/migrations/) in the repository.
