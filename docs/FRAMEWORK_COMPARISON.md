# Framework Comparison Matrix

Comprehensive comparison of the 15 frameworks covered by Agenkit mini-examples.
Use this to choose the right tool and understand migration tradeoffs.

Last updated: v0.65.0 (2026-03-15)

---

## Quick Selection Guide

| If you need... | Use... | Agenkit equivalent |
|----------------|--------|--------------------|
| Graph-based state machines | LangGraph | `RouterAgent` + `SequentialAgent` |
| Multi-agent role collaboration | CrewAI | `MultiagentOrchestrator` |
| Declarative prompt optimization | DSPy | Explicit prompts + `ReActAgent` |
| RAG pipelines | LlamaIndex | `InMemoryDocumentStore` + `RetrievalTool` |
| TypeScript-native workflows | Mastra / Vercel AI SDK | `SequentialAgent` / `process_stream()` |
| Enterprise .NET/Python agents | Semantic Kernel | `Agent` + `Tool` classes |
| Google Cloud / Gemini | Google ADK | `Agent` + any LLM adapter |
| Type-safe Python agents | Pydantic AI | `Agent` + Pydantic validation |
| OpenAI-native agents | OpenAI Agents SDK | `ReActAgent` + `RouterAgent` |
| React AI chat UI | CopilotKit | `AGUIAdapter` + streaming |

---

## Full Comparison Table

| Framework | Languages | Paradigm | LLM Lock-in | Streaming | Memory / State | Tool Use | Migration Guide | Agenkit Pattern |
|-----------|-----------|----------|-------------|-----------|----------------|----------|-----------------|-----------------|
| **LangChain** | Python, JS/TS | Chain / LCEL pipe | None | ✅ | ChatMessageHistory, VectorStore | Tool / AgentExecutor | [guide](migrations/langchain-to-agenkit.md) | `SequentialAgent`, `ReActAgent` |
| **LangGraph** | Python, JS/TS | Stateful graph (nodes + edges) | None | ✅ | MemorySaver (checkpointing) | ToolNode | [guide](migrations/langgraph-to-agenkit.md) | `RouterAgent`, `ReActAgent`, `ConversationalAgent` |
| **AutoGen** | Python | Multi-agent conversation | None | ✅ | Built-in history | FunctionCall | [guide](migrations/autogen-to-agenkit.md) | `MultiagentOrchestrator`, `ConversationalAgent` |
| **CrewAI** | Python | Role-based agents + Crew | None | ✅ | Agent memory (episodic) | Tool class | [guide](migrations/crewai-to-agenkit.md) | `MultiagentOrchestrator`, `Planning` |
| **OpenAI Agents SDK** | Python, TS | Agent + handoffs | OpenAI | ✅ | In-context window | `@function_tool` | [guide](migrations/openaiagents-to-agenkit.md) | `ReActAgent`, `RouterAgent` |
| **DSPy** | Python | Declarative LM programs | None | ❌ | No built-in | Module.forward() | [guide](migrations/dspy-to-agenkit.md) | Explicit prompts + `ReActAgent` |
| **LlamaIndex** | Python, TS | RAG + agent workflows | None | ✅ | VectorStoreIndex | FunctionTool | [guide](migrations/llamaindex-to-agenkit.md) | `InMemoryDocumentStore`, `ReActAgent` |
| **Haystack** | Python | NLP pipelines | None | ✅ | DocumentStore | Component | [guide](migrations/haystack-to-agenkit.md) | `SequentialAgent`, `RetrievalTool` |
| **SmolagAgents** | Python | Minimal code agents | None | ✅ | Minimal (in-context) | Tool class | [guide](migrations/smolagents-to-agenkit.md) | `ReActAgent`, `Tool` |
| **Strands** | Python | Event-driven streaming | None | ✅ | Minimal | Tool decorator | [guide](migrations/strands-to-agenkit.md) | `ReActAgent`, streaming |
| **Semantic Kernel** | Python, .NET | Plugin + kernel orchestration | Azure/OpenAI preferred | ✅ | ChatHistory | KernelFunction | [guide](migrations/semantickernel-to-agenkit.md) | `Agent` + `Tool`, `SequentialAgent` |
| **Google ADK** | Python | Multi-agent composition | Gemini preferred | ✅ | InMemorySessionService | `@tool` | [guide](migrations/googleadk-to-agenkit.md) | `SequentialAgent`, `ParallelAgent` |
| **Pydantic AI** | Python | Type-safe agents | None | ✅ | In-context only | `@agent.tool` | [guide](migrations/pydanticai-to-agenkit.md) | `Agent` + Pydantic validation |
| **Mastra** | TypeScript | Typed step workflows | None | ✅ | MastraContext | Step.execute() | [guide](migrations/mastra-to-agenkit.md) | `SequentialAgent`, `RouterAgent` |
| **Vercel AI SDK** | TypeScript | Streaming text/objects | OpenAI preferred | ✅ | None built-in | `tool()` | *(see minivercel example)* | `process_stream()`, `Tool` |
| **CopilotKit** | TypeScript/React | AI chat UI + actions | OpenAI preferred | ✅ | CopilotKitContext | CopilotAction | [guide](migrations/copilotkit-to-agenkit.md) | `AGUIAdapter`, `Tool` |

---

## Paradigm Deep Dive

### Chain-Based (LangChain)
Linear pipeline of components (LLM, retriever, output parser). Good for simple, sequential workflows.
- **Agenkit**: `SequentialAgent([step1, step2, step3])`

### Graph-Based (LangGraph, Mastra)
Nodes + edges with typed state passed between nodes. Supports cycles, conditional routing.
- **Agenkit**: `RouterAgent` for branching, `SequentialAgent` for linear, `ReActAgent` for cycles

### Multi-Agent Conversation (AutoGen, CrewAI)
Multiple agents with roles that exchange messages. Suited for collaborative problem-solving.
- **Agenkit**: `MultiagentOrchestrator`, `Planning` pattern

### Declarative LM Programming (DSPy)
Define I/O signatures; optimizer selects prompts and few-shot examples automatically.
- **Agenkit**: Explicit prompts + `ReActAgent` (no optimizer, but full control)

### RAG-Focused (LlamaIndex, Haystack)
Document ingestion, indexing, retrieval, synthesis. Built for question-answering over corpora.
- **Agenkit**: `InMemoryDocumentStore` + `RetrievalTool` + `ReActAgent`

### Type-Safe Agents (Pydantic AI)
Agents with typed inputs/outputs validated by Pydantic. Python-specific.
- **Agenkit**: `Agent` + manual Pydantic validation of `response.content`

### Event-Driven Streaming (Strands, Vercel AI SDK)
Stream tokens and tool events in real-time. First-class streaming support.
- **Agenkit**: `agent.process_stream()` returns async generator of `Message` chunks

### Workflow/Step (Mastra)
Typed `Step<I, O>` pipeline with compile-time type checking. TypeScript-native.
- **Agenkit TypeScript**: `SequentialAgent`, `RouterAgent`

### UI-Integrated (CopilotKit)
React hooks + components for AI chat UI. Tight frontend-backend coupling.
- **Agenkit**: `AGUIAdapter` provides AG-UI streaming protocol for any frontend

---

## LLM Provider Support

| Framework | OpenAI | Anthropic | Gemini | Azure OpenAI | Local (Ollama) | Any OpenAI-compat |
|-----------|--------|-----------|--------|--------------|----------------|-------------------|
| LangChain | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LangGraph | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AutoGen | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CrewAI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OpenAI Agents SDK | ✅ | ❌ | ❌ | ✅ | ❌ | Partial |
| DSPy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LlamaIndex | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Haystack | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SmolagAgents | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Strands | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Semantic Kernel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Google ADK | ✅ | ❌ | ✅ (native) | ❌ | ✅ (LiteLlm) | Via LiteLlm |
| Pydantic AI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mastra | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Vercel AI SDK | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CopilotKit | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Agenkit** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** |

---

## Performance Comparison

When migrating to Agenkit, deploying in Go or Rust provides significant speedups:

| Agenkit Language | Relative Speed | Use Case |
|-----------------|----------------|----------|
| Python | 1x (baseline) | Prototyping, data science, ML |
| TypeScript | ~2x | Frontend integration, serverless |
| Go | **18x** | Production APIs, high-throughput |
| Rust | **22x** | Systems integration, low-latency |
| C++ | **25x** | Embedded, real-time, latency-critical |
| Zig | **23x** | Systems programming, WASM |

All Python frameworks run at ~1x. Migrating to Agenkit + Go gives 18x speedup for the same logic.

---

## Mini-Examples Reference

| Framework | Python | Go | TypeScript |
|-----------|--------|-----|------------|
| LangChain | `examples/frameworks/minichain.py` | `agenkit-go/examples/frameworks/minichain/` | `agenkit-ts/examples/frameworks/minichain.ts` |
| LangGraph | `examples/frameworks/minilanggraph.py` | `agenkit-go/examples/frameworks/minilanggraph/` | `agenkit-ts/examples/frameworks/minilanggraph.ts` |
| AutoGen | `examples/frameworks/miniautogen.py` | `agenkit-go/examples/frameworks/miniautogen/` | — |
| CrewAI | `examples/frameworks/minicrew.py` | `agenkit-go/examples/frameworks/minicrew/` | — |
| OpenAI Agents SDK | `examples/frameworks/miniopenaiagents.py` | `agenkit-go/examples/frameworks/miniopenaiagents/` | `agenkit-ts/examples/frameworks/miniopenaiagents.ts` |
| DSPy | `examples/frameworks/minidspy.py` | `agenkit-go/examples/frameworks/minidspy/` | — |
| LlamaIndex | `examples/frameworks/minillamaindex.py` | `agenkit-go/examples/frameworks/minillamaindex/` | — |
| Haystack | `examples/frameworks/minihaystack.py` | `agenkit-go/examples/frameworks/minihaystack/` | — |
| SmolagAgents | `examples/frameworks/minismolagents.py` | `agenkit-go/examples/frameworks/minismolagents/` | — |
| Strands | `examples/frameworks/ministrands.py` | `agenkit-go/examples/frameworks/ministrands/` | — |
| Semantic Kernel | `examples/frameworks/minisemantickernel.py` | `agenkit-go/examples/frameworks/minisemantickernel/` | — |
| Google ADK | `examples/frameworks/minigoogleadk.py` | `agenkit-go/examples/frameworks/minigoogleadk/` | — |
| Pydantic AI | `examples/frameworks/minipydantic/` | — | — |
| Mastra | — | — | `agenkit-ts/examples/frameworks/minimastra.ts` |
| Vercel AI SDK | — | — | `agenkit-ts/examples/frameworks/miniverscel.ts` |
| CopilotKit | `examples/frameworks/minicopilotkit/` | — | — |
