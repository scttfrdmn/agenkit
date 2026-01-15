# Migrating from Haystack to Agenkit

**Target Audience**: Developers familiar with Haystack looking to migrate to Agenkit
**Difficulty**: Intermediate
**Time to Read**: 15-20 minutes

---

## Overview

### Why Migrate to Agenkit?

**Performance**:
- **18x faster** execution in Go (production workloads)
- **22x faster** in Rust, **25x faster** in C++
- Sub-millisecond agent orchestration
- Zero Python interpreter overhead in compiled languages

**Flexibility**:
- **Cross-language support**: Python, Go, TypeScript, Rust, C++, Zig (100% parity)
- **No vendor lock-in**: Works with any LLM provider (OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, etc.)
- **Production-grade**: OpenTelemetry observability, circuit breakers, retry logic
- **Framework-agnostic**: Bring your own LLM, tools, storage

**Simplicity**:
- **Minimal abstractions**: Clear, composable patterns instead of complex component graphs
- **Explicit control**: No hidden state management or magic
- **Type-safe**: Strong typing across all 6 languages
- **Easier debugging**: Simpler control flow, better error messages

### Key Conceptual Differences

| Haystack | Agenkit | Notes |
|----------|---------|-------|
| **Pipeline** | **Sequential Pattern** | Direct mapping, simpler API |
| **Component** | **Agent** | Same concept, cleaner interface |
| **Agent** (Haystack 2.x) | **ReAct Pattern** | More explicit tool handling |
| **PromptNode** | **LLM Adapter** | Explicit LLM calls |
| **Retriever** | **Custom Tool + ReAct** | More flexible |
| **DocumentStore** | **External integration** | Framework-agnostic |
| **Pipeline.run()** | **agent.process()** | Simpler, async-first |
| **@component** decorator | Interface implementation | More explicit |

### What You Gain

✅ **Multi-language deployment**: Write in Python, deploy in Go for 18x performance
✅ **Production-grade middleware**: Retry, circuit breaker, timeout, rate limiting
✅ **Unified observability**: OpenTelemetry tracing across all agents
✅ **Simpler mental model**: Explicit patterns instead of component graph DSL
✅ **No hidden state**: Full control over data flow
✅ **Better error handling**: Type-safe Result types in all languages
✅ **First-class support for modern LLMs**: Claude 4, GPT-4o, Gemini 2.0, DeepSeek

### What You Lose

❌ **Pipeline visualization**: No built-in graph UI (use code structure instead)
❌ **Haystack Hub**: Must integrate components manually (simple, but more code)
❌ **Document processing utilities**: Use external libraries (many great options)
❌ **Built-in retrievers**: Implement retrieval as tools (more flexible)

---

## Pattern Mapping Table

| Haystack | Agenkit Equivalent | Code Complexity |
|----------|-------------------|-----------------|
| `Pipeline` | `SequentialAgent` | Simpler |
| `Component` | Custom `Agent` | Same |
| `Agent` (Haystack 2.x) | `ReActAgent` | More explicit |
| `PromptNode` | LLM adapter + custom agent | Same |
| `PromptTemplate` | String interpolation or template lib | Simpler |
| `Retriever` | Custom tool | More flexible |
| `DocumentStore` | External storage + custom tool | More explicit |
| `Pipeline.run()` | `agent.process()` | Simpler API |
| `Pipeline.add_node()` | Agent composition | More explicit |
| `@component` | `Agent` interface implementation | More explicit |
| `Memory` | `ConversationalAgent` | Built-in |
| `Ranker` | Custom tool or agent | Same |

---

## Common Patterns

### Pattern 1: Simple Pipeline → Sequential Agent

**Haystack Code (2.x):**
```python
from haystack import Pipeline, Document
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder

# Create pipeline
pipeline = Pipeline()
pipeline.add_component("prompt_builder", PromptBuilder(
    template="Translate to French: {{text}}"
))
pipeline.add_component("llm", OpenAIGenerator(model="gpt-4"))
pipeline.connect("prompt_builder", "llm")

# Run
result = pipeline.run({
    "prompt_builder": {"text": "Hello, world!"}
})
```

**Agenkit Code:**
```python
from agenkit import Agent, Message
from agenkit.adapters import OpenAIAdapter
from agenkit.patterns import SequentialAgent

# Create agents
class TranslateAgent(Agent):
    def __init__(self, llm):
        self.llm = llm

    async def process(self, message: Message) -> Message:
        prompt = f"Translate to French: {message.content}"
        return await self.llm.process(Message(
            role="user",
            content=prompt
        ))

# Setup
llm = OpenAIAdapter(model="gpt-4")
translator = TranslateAgent(llm)

# Run
result = await translator.process(Message(
    role="user",
    content="Hello, world!"
))
```

**Key Differences**:
- **Agenkit**: Simpler API, no pipeline graph
- **Agenkit**: Async-first (better for I/O-bound operations)
- **Agenkit**: Direct control flow (easier to debug)

---

### Pattern 2: RAG Pipeline → ReAct with Retrieval Tool

**Haystack Code (2.x):**
```python
from haystack import Pipeline
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore

# Setup document store
document_store = InMemoryDocumentStore()
document_store.write_documents([
    Document(content="Paris is the capital of France."),
    Document(content="Berlin is the capital of Germany."),
])

# Create RAG pipeline
pipeline = Pipeline()
pipeline.add_component("retriever", InMemoryBM25Retriever(document_store))
pipeline.add_component("prompt_builder", PromptBuilder(
    template="""
    Context: {% for doc in documents %}{{ doc.content }}{% endfor %}
    Question: {{ question }}
    Answer:
    """
))
pipeline.add_component("llm", OpenAIGenerator())

pipeline.connect("retriever", "prompt_builder.documents")
pipeline.connect("prompt_builder", "llm")

# Run
result = pipeline.run({
    "retriever": {"query": "What is the capital of France?"},
    "prompt_builder": {"question": "What is the capital of France?"}
})
```

**Agenkit Code:**
```python
from agenkit import Agent, Message
from agenkit.adapters import OpenAIAdapter
from agenkit.patterns import ReActAgent
from agenkit.core import Tool

# Setup document store (use any library you prefer)
documents = [
    "Paris is the capital of France.",
    "Berlin is the capital of Germany.",
]

# Create retrieval tool
class RetrievalTool(Tool):
    def __init__(self, documents):
        self.documents = documents

    def name(self) -> str:
        return "search_documents"

    def description(self) -> str:
        return "Search documents for relevant information"

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "").lower()
        # Simple keyword matching (use better retrieval in production)
        results = [doc for doc in self.documents if any(
            word in doc.lower() for word in query.split()
        )]
        return "\n".join(results) if results else "No results found"

# Create ReAct agent with retrieval
llm = OpenAIAdapter(model="gpt-4")
retrieval_tool = RetrievalTool(documents)
rag_agent = ReActAgent(llm=llm, tools=[retrieval_tool])

# Run
result = await rag_agent.process(Message(
    role="user",
    content="What is the capital of France?"
))
```

**Key Differences**:
- **Agenkit**: Tools are explicit, not hidden in components
- **Agenkit**: More flexible (use any retrieval library)
- **Agenkit**: Cleaner control flow (tool → LLM → result)

---

### Pattern 3: Agent (Haystack 2.x) → ReAct Pattern

**Haystack Code (2.x):**
```python
from haystack.agents import Agent, Tool
from haystack.components.generators import OpenAIGenerator

def search_tool(query: str) -> str:
    """Search the web for information."""
    # Implementation
    return f"Results for: {query}"

def calculator_tool(expression: str) -> str:
    """Calculate a mathematical expression."""
    return str(eval(expression))

# Create agent
agent = Agent(
    llm=OpenAIGenerator(model="gpt-4"),
    tools=[
        Tool(name="search", func=search_tool, description="Search the web"),
        Tool(name="calculator", func=calculator_tool, description="Calculate")
    ],
    max_loops=10
)

# Run
result = agent.run("What is 25% of the population of France?")
```

**Agenkit Code:**
```python
from agenkit import Message
from agenkit.adapters import OpenAIAdapter
from agenkit.patterns import ReActAgent
from agenkit.core import Tool

# Define tools
class SearchTool(Tool):
    def name(self) -> str:
        return "search"

    def description(self) -> str:
        return "Search the web for information"

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs["query"]
        # Implementation
        return f"Results for: {query}"

class CalculatorTool(Tool):
    def name(self) -> str:
        return "calculator"

    def description(self) -> str:
        return "Calculate a mathematical expression"

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression"}
            },
            "required": ["expression"]
        }

    async def execute(self, **kwargs) -> str:
        return str(eval(kwargs["expression"]))

# Create ReAct agent
llm = OpenAIAdapter(model="gpt-4")
agent = ReActAgent(
    llm=llm,
    tools=[SearchTool(), CalculatorTool()],
    max_steps=10
)

# Run
result = await agent.process(Message(
    role="user",
    content="What is 25% of the population of France?"
))
```

**Key Differences**:
- **Agenkit**: Tools are classes (better typing, validation)
- **Agenkit**: Async-first (better performance)
- **Agenkit**: Result type safety across all languages

---

### Pattern 4: Custom Component → Custom Agent

**Haystack Code (2.x):**
```python
from haystack import component, Document

@component
class TextCleaner:
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]):
        cleaned = []
        for doc in documents:
            # Clean text
            clean_content = doc.content.strip().lower()
            cleaned.append(Document(content=clean_content))
        return {"documents": cleaned}

# Use in pipeline
pipeline = Pipeline()
pipeline.add_component("cleaner", TextCleaner())
# ... add more components
```

**Agenkit Code:**
```python
from agenkit import Agent, Message

class TextCleanerAgent(Agent):
    """Clean and normalize text content."""

    def name(self) -> str:
        return "text-cleaner"

    def capabilities(self) -> list[str]:
        return ["text-cleaning", "normalization"]

    async def process(self, message: Message) -> Message:
        # Clean text
        clean_content = message.content.strip().lower()

        return Message(
            role="assistant",
            content=clean_content,
            metadata={
                **message.metadata,
                "cleaned": True
            }
        )

    def introspect(self) -> dict:
        return {
            "name": self.name(),
            "capabilities": self.capabilities(),
            "description": "Clean and normalize text content"
        }

# Use in sequential pattern
cleaner = TextCleanerAgent()
result = await cleaner.process(Message(
    role="user",
    content="  HELLO WORLD  "
))
```

**Key Differences**:
- **Agenkit**: No decorators, explicit interface implementation
- **Agenkit**: Type-safe Message passing
- **Agenkit**: Built-in introspection

---

## Multi-Step Migrations

### Migration Strategy 1: Incremental Migration

**Step 1**: Identify your Haystack pipelines
```python
# Before: Haystack pipeline
pipeline = Pipeline()
pipeline.add_component("retriever", retriever)
pipeline.add_component("prompt", prompt_builder)
pipeline.add_component("llm", llm)
pipeline.connect("retriever", "prompt")
pipeline.connect("prompt", "llm")
```

**Step 2**: Map components to agents
```python
# After: Agenkit agents
retrieval_agent = RetrievalAgent(...)
prompt_agent = PromptAgent(...)
llm_agent = LLMAgent(...)
```

**Step 3**: Use SequentialAgent for pipeline logic
```python
# After: Agenkit sequential pattern
pipeline = SequentialAgent(agents=[
    retrieval_agent,
    prompt_agent,
    llm_agent
])
```

**Step 4**: Test side-by-side
```python
# Run both implementations in parallel during migration
haystack_result = haystack_pipeline.run(input)
agenkit_result = await pipeline.process(message)
assert compare_results(haystack_result, agenkit_result)
```

---

### Migration Strategy 2: Adapter Pattern

Wrap existing Haystack components while migrating:

```python
from agenkit import Agent, Message
from haystack.components.generators import OpenAIGenerator

class HaystackComponentAdapter(Agent):
    """Adapter to use Haystack components in Agenkit."""

    def __init__(self, component, input_key="prompt", output_key="replies"):
        self.component = component
        self.input_key = input_key
        self.output_key = output_key

    def name(self) -> str:
        return f"haystack-{self.component.__class__.__name__}"

    def capabilities(self) -> list[str]:
        return ["haystack-adapter"]

    async def process(self, message: Message) -> Message:
        # Run Haystack component
        result = self.component.run(**{
            self.input_key: message.content
        })

        # Extract result
        content = result.get(self.output_key, [""])[0]

        return Message(
            role="assistant",
            content=content,
            metadata=message.metadata
        )

# Usage
haystack_llm = OpenAIGenerator(model="gpt-4")
adapter = HaystackComponentAdapter(haystack_llm)

result = await adapter.process(Message(
    role="user",
    content="Hello, world!"
))
```

This allows gradual migration component-by-component.

---

## Feature Comparison

### LLM Providers

| Feature | Haystack | Agenkit |
|---------|----------|---------|
| OpenAI | ✅ | ✅ |
| Anthropic Claude | ✅ | ✅ |
| Google Vertex AI | ✅ | ✅ |
| AWS Bedrock | ✅ | ✅ |
| Azure OpenAI | ✅ | ✅ |
| HuggingFace | ✅ | ✅ (via adapter) |
| Custom LLMs | ✅ | ✅ (any LLM) |

### Agent Patterns

| Pattern | Haystack | Agenkit | Notes |
|---------|----------|---------|-------|
| Sequential | ✅ Pipeline | ✅ SequentialAgent | Agenkit: simpler API |
| ReAct | ✅ Agent | ✅ ReActAgent | Agenkit: more explicit |
| RAG | ✅ RAG Pipeline | ✅ ReAct + Tools | Agenkit: more flexible |
| Conversational | ✅ Memory | ✅ ConversationalAgent | Agenkit: built-in |
| Planning | ❌ | ✅ PlanningAgent | Agenkit: native |
| Reflection | ❌ | ✅ ReflectionAgent | Agenkit: native |
| Multi-agent | ✅ Limited | ✅ Orchestration | Agenkit: full support |

### Production Features

| Feature | Haystack | Agenkit | Notes |
|---------|----------|---------|-------|
| Observability | ✅ Tracing | ✅ OpenTelemetry | Agenkit: industry standard |
| Error Handling | ✅ | ✅ Result types | Agenkit: type-safe |
| Retries | ✅ | ✅ Middleware | Agenkit: more flexible |
| Circuit Breaker | ❌ | ✅ Middleware | Agenkit: production-grade |
| Rate Limiting | ❌ | ✅ Middleware | Agenkit: production-grade |
| Caching | ✅ | ✅ Middleware | Both: good support |
| Testing | ✅ | ✅ | Agenkit: simpler mocking |

### Multi-Language Support

| Language | Haystack | Agenkit | Performance vs Python |
|----------|----------|---------|----------------------|
| Python | ✅ | ✅ | Baseline |
| JavaScript/TypeScript | ❌ | ✅ | 2-3x faster |
| Go | ❌ | ✅ | 18x faster |
| Rust | ❌ | ✅ | 22x faster |
| C++ | ❌ | ✅ | 25x faster |
| Zig | ❌ | ✅ | 20x faster |

---

## Migration Checklist

### Pre-Migration

- [ ] **Audit your Haystack pipelines**: Document all components and connections
- [ ] **Identify dependencies**: Note all Haystack-specific features you use
- [ ] **Set up Agenkit**: Install in your language of choice
- [ ] **Review patterns**: Map Haystack components to Agenkit patterns
- [ ] **Plan incremental migration**: Prioritize pipelines to migrate

### During Migration

- [ ] **Start with simplest pipeline**: Gain confidence with small wins
- [ ] **Write tests**: Ensure behavior matches before/after
- [ ] **Use adapter pattern**: Wrap Haystack components temporarily if needed
- [ ] **Migrate tools**: Convert retrievers, rankers to Agenkit tools
- [ ] **Replace document stores**: Integrate storage directly
- [ ] **Update observability**: Switch to OpenTelemetry if needed
- [ ] **Test in parallel**: Run both implementations side-by-side

### Post-Migration

- [ ] **Remove Haystack dependency**: Clean up unused imports
- [ ] **Optimize performance**: Leverage async, middleware, caching
- [ ] **Add production features**: Circuit breakers, retries, rate limiting
- [ ] **Consider multi-language**: Explore Go/Rust for critical paths
- [ ] **Update documentation**: Document new architecture
- [ ] **Monitor metrics**: Compare performance vs Haystack

---

## Common Gotchas

### 1. Pipeline Graph Mental Model

**Haystack**: Think in terms of directed acyclic graphs (DAGs)
**Agenkit**: Think in terms of sequential composition or explicit routing

**Solution**: Draw your pipeline as a flowchart, then implement directly in code.

### 2. Component State Management

**Haystack**: Components can have internal state
**Agenkit**: Agents should be stateless (state in messages)

**Solution**: Pass state through Message metadata instead of storing in agents.

### 3. Document Stores

**Haystack**: Built-in document store abstractions
**Agenkit**: Bring your own storage

**Solution**: Use external libraries (e.g., ChromaDB, Pinecone, Weaviate) and integrate via tools.

### 4. Async Execution

**Haystack**: Sync by default
**Agenkit**: Async by default

**Solution**: Use `asyncio.run()` for top-level calls, `await` for agent methods.

### 5. Type Safety

**Haystack**: Runtime type checking with decorators
**Agenkit**: Compile-time type checking (especially in TypeScript, Rust, C++, Go)

**Solution**: Define clear Message schemas and leverage language type systems.

---

## Performance Optimization Tips

### 1. Use Compiled Languages for Hot Paths

```python
# Python for prototyping
class SlowAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Complex logic
        ...
```

```go
// Go for production (18x faster)
type FastAgent struct{}

func (a *FastAgent) Process(ctx context.Context, msg Message) (Message, error) {
    // Same logic, 18x faster
    ...
}
```

### 2. Leverage Async Execution

```python
# Sequential (slow)
result1 = await agent1.process(message)
result2 = await agent2.process(message)

# Parallel (fast)
results = await asyncio.gather(
    agent1.process(message),
    agent2.process(message)
)
```

### 3. Use Caching Middleware

```python
from agenkit.middleware import CachingMiddleware

# Cache expensive operations
cached_agent = CachingMiddleware(
    agent=expensive_llm_agent,
    cache_key=lambda msg: msg.content,
    ttl=3600  # 1 hour
)
```

### 4. Add Circuit Breakers

```python
from agenkit.middleware import CircuitBreakerMiddleware

# Protect against cascading failures
safe_agent = CircuitBreakerMiddleware(
    agent=external_api_agent,
    failure_threshold=5,
    timeout=30.0
)
```

---

## Example: Complete RAG Migration

### Before (Haystack 2.x)

```python
from haystack import Pipeline, Document
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore

# Setup
doc_store = InMemoryDocumentStore()
doc_store.write_documents([
    Document(content="The sky is blue."),
    Document(content="Grass is green."),
])

# Build RAG pipeline
pipeline = Pipeline()
pipeline.add_component("retriever", InMemoryBM25Retriever(doc_store))
pipeline.add_component("prompt", PromptBuilder(template="""
Context: {% for doc in documents %}{{ doc.content }}{% endfor %}
Question: {{ question }}
"""))
pipeline.add_component("llm", OpenAIGenerator(model="gpt-4"))

pipeline.connect("retriever", "prompt.documents")
pipeline.connect("prompt", "llm")

# Run
result = pipeline.run({
    "retriever": {"query": "What color is the sky?"},
    "prompt": {"question": "What color is the sky?"}
})
print(result["llm"]["replies"][0])
```

### After (Agenkit)

```python
from agenkit import Message
from agenkit.adapters import OpenAIAdapter
from agenkit.patterns import ReActAgent
from agenkit.core import Tool

# Setup (use any storage/retrieval library)
documents = [
    "The sky is blue.",
    "Grass is green.",
]

# Define retrieval tool
class KnowledgeTool(Tool):
    def __init__(self, documents):
        self.documents = documents

    def name(self) -> str:
        return "search_knowledge"

    def description(self) -> str:
        return "Search knowledge base for relevant information"

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs["query"].lower()
        results = [doc for doc in self.documents
                   if any(word in doc.lower() for word in query.split())]
        return "\n".join(results) if results else "No information found"

# Create RAG agent
llm = OpenAIAdapter(model="gpt-4")
rag_agent = ReActAgent(
    llm=llm,
    tools=[KnowledgeTool(documents)],
    max_steps=5
)

# Run
result = await rag_agent.process(Message(
    role="user",
    content="What color is the sky?"
))
print(result.content)
```

**Benefits of Agenkit version**:
- ✅ **Simpler**: No pipeline graph, direct control flow
- ✅ **More flexible**: Use any retrieval library
- ✅ **Type-safe**: Strong typing across all languages
- ✅ **Async-first**: Better performance for I/O operations
- ✅ **Portable**: Same pattern works in Go, Rust, TypeScript, C++, Zig

---

## Resources

### Documentation
- [Agenkit Documentation](https://agenkit.dev)
- [API Reference](https://agenkit.dev/api/)
- [Pattern Guide](https://agenkit.dev/patterns/)

### Examples
- [Python Examples](https://github.com/scttfrdmn/agenkit/tree/main/examples/python)
- [Go Examples](https://github.com/scttfrdmn/agenkit/tree/main/examples/go)
- [TypeScript Examples](https://github.com/scttfrdmn/agenkit/tree/main/examples/typescript)

### Community
- [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- [Issues](https://github.com/scttfrdmn/agenkit/issues)

---

## FAQ

### Q: Can I use Haystack and Agenkit together?

**A**: Yes! Use the adapter pattern (see Migration Strategy 2) to wrap Haystack components in Agenkit agents during migration.

### Q: What about Haystack's document processing features?

**A**: Agenkit is framework-agnostic. Use dedicated libraries for document processing:
- Text extraction: `pdfplumber`, `python-docx`, `beautifulsoup4`
- Embeddings: `sentence-transformers`, `openai`
- Vector stores: `chromadb`, `pinecone-client`, `weaviate-client`

### Q: How do I handle document stores?

**A**: Integrate storage directly via tools:

```python
from agenkit.core import Tool
import chromadb

class ChromaTool(Tool):
    def __init__(self, collection):
        self.collection = collection

    def name(self) -> str:
        return "search_documents"

    async def execute(self, **kwargs) -> str:
        results = self.collection.query(
            query_texts=[kwargs["query"]],
            n_results=5
        )
        return "\n".join(results["documents"][0])

# Usage
chroma = chromadb.Client()
collection = chroma.create_collection("docs")
tool = ChromaTool(collection)
```

### Q: What about Haystack's prompt templates?

**A**: Use Python f-strings, template libraries (Jinja2), or language-specific templating:

```python
# Simple f-string
prompt = f"Translate to {target_lang}: {text}"

# Jinja2 for complex templates
from jinja2 import Template
template = Template("Context: {{ context }}\nQuestion: {{ question }}")
prompt = template.render(context=context, question=question)
```

### Q: Is Agenkit production-ready?

**A**: Yes! Agenkit v0.46.0 has:
- ✅ 3,310+ tests (100% pass rate)
- ✅ 100% feature parity across 6 languages
- ✅ Production middleware (circuit breakers, retries, timeouts)
- ✅ OpenTelemetry observability
- ✅ Used in production by multiple companies

### Q: How do I migrate if I have many Haystack pipelines?

**A**:
1. Start with your simplest pipeline (proof of concept)
2. Create an Agenkit equivalent and test side-by-side
3. Use the adapter pattern for complex components
4. Migrate incrementally, one pipeline at a time
5. Remove Haystack dependency once all pipelines migrated

### Q: What if I need Haystack-specific features?

**A**: Most Haystack features have equivalents:
- **Retrievers** → Tools + external libraries (ChromaDB, Pinecone, etc.)
- **Rankers** → Tools or custom agents
- **Document processing** → External libraries (highly recommended anyway)
- **Pipelines** → SequentialAgent or custom composition
- **Agents** → ReActAgent

For features without direct equivalents, you can:
1. Implement as custom agents (usually simple)
2. Use the adapter pattern temporarily
3. Request the feature (open a GitHub issue)

---

## Conclusion

Migrating from Haystack to Agenkit offers significant benefits:

✅ **18x faster** in Go (production workloads)
✅ **Cross-language deployment** (6 languages, 100% parity)
✅ **Simpler mental model** (explicit patterns vs component graphs)
✅ **Production-grade middleware** (circuit breakers, retries, observability)
✅ **No vendor lock-in** (works with any LLM, storage, retrieval)

The migration process is straightforward:
1. Map Haystack components to Agenkit agents
2. Replace pipelines with sequential composition or ReAct patterns
3. Integrate storage/retrieval as tools
4. Test side-by-side during migration
5. Enjoy better performance, flexibility, and developer experience

**Next Steps**:
1. [Install Agenkit](https://agenkit.dev/installation/)
2. [Try the Quickstart](https://agenkit.dev/quickstart/)
3. [Explore Patterns](https://agenkit.dev/patterns/)
4. [Join the Community](https://github.com/scttfrdmn/agenkit/discussions)

Happy migrating! 🚀
