# Migrating from LlamaIndex to Agenkit

**Target Audience**: Developers using LlamaIndex for RAG and agent workflows
**Difficulty**: Intermediate
**Time to Read**: 12-15 minutes

---

## Overview

### Why Migrate to Agenkit?

**Performance**:
- **18x faster** execution in Go for production workloads
- **22x faster** in Rust, **25x faster** in C++
- Sub-millisecond orchestration overhead

**Flexibility**:
- **Cross-language support**: Python, Go, TypeScript, Rust, C++, Zig (100% parity)
- **No vendor lock-in**: Works with any LLM provider, not just OpenAI
- **Framework-agnostic**: Bring your own vector store, LLM, and storage

**Simplicity**:
- **Minimal abstractions**: Explicit, composable patterns
- **Unified API**: Same patterns across 6 languages
- **Production-grade**: OpenTelemetry observability, circuit breakers, retry logic

### Key Conceptual Differences

| LlamaIndex | Agenkit | Notes |
|-----------|---------|-------|
| **Document** | **Document entry** in InMemoryDocumentStore | Same concept |
| **VectorStoreIndex** | **InMemoryDocumentStore** | More flexible storage |
| **QueryEngine** | **retriever + LLM synthesis** | Explicit pipeline |
| **QueryEngineTool** | **Tool wrapping a retriever** | Same pattern |
| **FunctionAgent** | **Agent with tool dispatch** | Simpler API |
| **ReActAgent** | **agenkit.patterns.ReActAgent** | Direct mapping |
| **AgentWorkflow** | **SequentialAgent / custom orchestrator** | More control |
| **ServiceContext** | **LLM adapter** | Cleaner separation |
| **NodeParser** | **Document chunker** | Explicit preprocessing |

### What You Gain

✅ **Multi-language deployment**: Write in Python, deploy in Go for 18x performance
✅ **Production middleware**: Retry, circuit breaker, timeout, rate limiting
✅ **Unified observability**: OpenTelemetry tracing across all agents
✅ **Any LLM**: Not tied to LlamaIndex integrations ecosystem
✅ **Simpler mental model**: No ServiceContext configuration overhead

### What You Lose

❌ **Rich LlamaIndex integrations**: 100+ vector store and data loader connectors
❌ **LlamaCloud**: No built-in managed index service
❌ **LlamaParse**: No PDF/document parsing (use any third-party library)

---

## Pattern Mapping Table

| LlamaIndex | Agenkit Equivalent | Complexity |
|-----------|-------------------|-----------|
| `Document` | Dict or dataclass stored in InMemoryDocumentStore | Same |
| `VectorStoreIndex.from_documents()` | `store.add_documents()` | Simpler |
| `index.as_query_engine()` | `RetrievalTool(store=store, llm=llm)` | Same |
| `QueryEngineTool` | `Tool` wrapping a retrieval function | Same |
| `FunctionAgent` | `Agent` subclass with tool dispatch | Same |
| `FunctionTool` | `Tool` class | Same concept |
| `@function_tool` | `Tool` class or `@tool` decorator | Same |
| `ReActAgent.from_tools()` | `ReActAgent(llm=llm, tools=[...])` | Simpler |
| `AgentWorkflow` | `SequentialAgent([...])` | More explicit |
| `ServiceContext` | LLM adapter constructor | Cleaner |
| `SimpleDirectoryReader` | `open()` + text split | Explicit |

---

## Common Patterns

### Pattern 1: Document Indexing and RAG

**LlamaIndex Code:**
```python
from llama_index.core import VectorStoreIndex, Document

documents = [
    Document(text="Agenkit supports Python, Go, TypeScript, Rust, C++, Zig."),
    Document(text="Agenkit provides 11+ orchestration patterns."),
]
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What languages does Agenkit support?")
print(response)
```

**Agenkit Equivalent:**
```python
from agenkit.memory import InMemoryDocumentStore
from agenkit.tools import RetrievalTool
from agenkit.patterns import ReActAgent

store = InMemoryDocumentStore()
store.add_documents([
    {"id": "doc1", "text": "Agenkit supports Python, Go, TypeScript, Rust, C++, Zig."},
    {"id": "doc2", "text": "Agenkit provides 11+ orchestration patterns."},
])

retrieval_tool = RetrievalTool(store=store, llm=llm)
agent = ReActAgent(llm=llm, tools=[retrieval_tool])
response = await agent.process(Message(role="user", content="What languages does Agenkit support?"))
```

---

### Pattern 2: FunctionAgent with Tools

**LlamaIndex Code:**
```python
from llama_index.core.agent import FunctionCallingAgent
from llama_index.core.tools import FunctionTool

def search(query: str) -> str:
    return f"Results for: {query}"

tool = FunctionTool.from_defaults(fn=search, name="search", description="Search docs")
agent = FunctionCallingAgent.from_tools([tool], llm=llm)
response = agent.chat("Search for Agenkit features")
```

**Agenkit Equivalent:**
```python
from agenkit import Agent, Message
from agenkit.patterns import ReActAgent

class SearchTool:
    name = "search"
    description = "Search docs"

    async def run(self, query: str) -> str:
        return f"Results for: {query}"

agent = ReActAgent(llm=llm, tools=[SearchTool()])
response = await agent.process(Message(role="user", content="Search for Agenkit features"))
```

---

### Pattern 3: ReActAgent

**LlamaIndex Code:**
```python
from llama_index.core.agent import ReActAgent

agent = ReActAgent.from_tools(
    tools=[calculator_tool, search_tool],
    llm=llm,
    verbose=True,
)
response = agent.chat("What is (42 * 3) + 7?")
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import ReActAgent

agent = ReActAgent(llm=llm, tools=[calculator_tool, search_tool])
response = await agent.process(
    Message(role="user", content="What is (42 * 3) + 7?")
)
```

---

### Pattern 4: AgentWorkflow (Multi-Agent)

**LlamaIndex Code:**
```python
from llama_index.core.workflow import AgentWorkflow

workflow = AgentWorkflow(
    agents=[researcher_agent, writer_agent],
    root_agent="researcher",
)
result = await workflow.run(task="Write a report on Agenkit")
```

**Agenkit Equivalent:**
```python
from agenkit.patterns import SequentialAgent

pipeline = SequentialAgent([researcher_agent, writer_agent])
result = await pipeline.process(
    Message(role="user", content="Write a report on Agenkit")
)
```

---

### Pattern 5: QueryEngineTool

**LlamaIndex Code:**
```python
from llama_index.core.tools import QueryEngineTool

rag_tool = QueryEngineTool.from_defaults(
    query_engine=query_engine,
    name="knowledge_base",
    description="Search product documentation",
)
agent = FunctionCallingAgent.from_tools([rag_tool], llm=llm)
```

**Agenkit Equivalent:**
```python
from agenkit.tools import RetrievalTool
from agenkit.patterns import ReActAgent

retrieval_tool = RetrievalTool(
    store=document_store,
    llm=llm,
    name="knowledge_base",
    description="Search product documentation",
)
agent = ReActAgent(llm=llm, tools=[retrieval_tool])
```

---

## Step-by-Step Migration

### Step 1: Replace ServiceContext / Settings

**Before (LlamaIndex):**
```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

Settings.llm = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
```

**After (Agenkit):**
```python
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(model="gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])
# Embeddings: use your preferred library directly
```

### Step 2: Replace VectorStoreIndex

**Before:**
```python
index = VectorStoreIndex.from_documents(documents)
```

**After:**
```python
from agenkit.memory import InMemoryDocumentStore

store = InMemoryDocumentStore()
store.add_documents([{"id": d.doc_id, "text": d.text} for d in documents])
```

### Step 3: Replace QueryEngine

**Before:**
```python
query_engine = index.as_query_engine(llm=llm)
response = query_engine.query("my question")
```

**After:**
```python
from agenkit.tools import RetrievalTool

retrieval_tool = RetrievalTool(store=store, llm=llm)
agent = ReActAgent(llm=llm, tools=[retrieval_tool])
response = await agent.process(Message(role="user", content="my question"))
```

### Step 4: Replace Agents

**Before:**
```python
from llama_index.core.agent import ReActAgent
agent = ReActAgent.from_tools([tool1, tool2], llm=llm)
response = agent.chat("task description")
```

**After:**
```python
from agenkit.patterns import ReActAgent
agent = ReActAgent(llm=llm, tools=[tool1, tool2])
response = await agent.process(Message(role="user", content="task description"))
```

---

## Testing Your Migration

```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_rag_agent():
    store = InMemoryDocumentStore()
    store.add_documents([{"id": "1", "text": "Agenkit supports 6 languages."}])

    retrieval_tool = RetrievalTool(store=store, llm=mock_llm)
    agent = ReActAgent(llm=mock_llm, tools=[retrieval_tool])

    response = await agent.process(Message(role="user", content="How many languages?"))
    assert response.content is not None
```

---

## Common Pitfalls

1. **Async/await**: LlamaIndex has sync `.chat()` methods; Agenkit is fully async — always `await`
2. **Embeddings**: Agenkit's InMemoryDocumentStore uses keyword search by default; bring your own embedding model for semantic search
3. **ServiceContext**: No global settings object in Agenkit — pass LLM explicitly to each component
4. **Document IDs**: Agenkit requires explicit document IDs; LlamaIndex auto-generates them

---

## FAQ

**Q: Does Agenkit support streaming responses?**
A: Yes, use `agent.process_stream()` which returns an async generator of Message chunks.

**Q: Can I use Pinecone/Weaviate/Qdrant with Agenkit?**
A: Yes, implement the `DocumentStore` interface wrapping any vector database.

**Q: Does Agenkit support multi-modal (images, PDFs)?**
A: Agenkit handles the agent orchestration layer; pass pre-processed content as message text.

**Q: How do I migrate LlamaIndex pipelines (IngestionPipeline)?**
A: Replace with explicit Python: load documents, transform, store. No pipeline abstraction needed.

---

## Reference

- Example: `examples/frameworks/minillamaindex.py`
- Go equivalent: `agenkit-go/examples/frameworks/minillamaindex/main.go`
- Agenkit patterns: `docs/PATTERNS.md`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
