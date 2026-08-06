#!/usr/bin/env python3
"""
MiniLlamaIndex - LlamaIndex Agent Workflow Built on Agenkit

Demonstrates how LlamaIndex's event-driven agent orchestration patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy for RAG + multi-agent frameworks.

Pattern Mappings:
  LlamaIndex.AgentWorkflow   → Agenkit multi-agent orchestration
  LlamaIndex.FunctionAgent   → Agenkit Agent with tool support
  LlamaIndex.ReActAgent      → Agenkit ReActAgent (patterns package)
  LlamaIndex.VectorStoreIndex → Agenkit InMemoryDocumentStore
  LlamaIndex.QueryEngineTool  → Agenkit Tool wrapping a retriever

Migration guide: docs/migrations/llamaindex-to-agenkit.md

Usage: uv run python examples/frameworks/minillamaindex.py
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


# ---------------------------------------------------------------------------
# Document primitives (mirrors LlamaIndex.Document / TextNode)
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """
    Text document with metadata (mirrors LlamaIndex.Document).
    Pattern: LlamaIndex.Document → Agenkit InMemoryDocumentStore entry
    """

    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# VectorStoreIndex (mirrors LlamaIndex.VectorStoreIndex)
# ---------------------------------------------------------------------------


class VectorStoreIndex:
    """
    In-memory document index with keyword-overlap similarity search.
    Pattern: LlamaIndex.VectorStoreIndex → Agenkit InMemoryDocumentStore

    In production Agenkit you would use:
        from agenkit.memory import InMemoryDocumentStore
        store = InMemoryDocumentStore()
        store.add_documents(documents)
    """

    def __init__(self, documents: list[Document]) -> None:
        """
        Build index from a list of documents.

        Args:
            documents: Documents to index
        """
        self._documents = documents

    @classmethod
    def from_documents(cls, documents: list[Document]) -> "VectorStoreIndex":
        """Build index from documents (mirrors LlamaIndex.VectorStoreIndex.from_documents)."""
        return cls(documents)

    def similarity_search(self, query: str, top_k: int = 3) -> list[Document]:
        """
        Return top-k documents by keyword overlap with query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            Top-k most relevant documents
        """
        query_terms = set(query.lower().split())
        scored: list[tuple[float, Document]] = []
        for doc in self._documents:
            doc_terms = set(doc.text.lower().split())
            score = len(query_terms & doc_terms) / max(len(query_terms), 1)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def as_query_engine(self, llm: LLM | None = None) -> "QueryEngine":
        """
        Create a QueryEngine backed by this index.

        Args:
            llm: Optional LLM for synthesis (required for actual query)

        Returns:
            QueryEngine wrapping this index
        """
        return QueryEngine(index=self, llm=llm)


# ---------------------------------------------------------------------------
# QueryEngine (mirrors LlamaIndex.QueryEngine)
# ---------------------------------------------------------------------------


class QueryEngine:
    """
    Executes retrieval + synthesis over a VectorStoreIndex.
    Pattern: LlamaIndex.QueryEngine → Agenkit retriever + LLM synthesis
    """

    def __init__(self, index: VectorStoreIndex, llm: LLM | None = None) -> None:
        """
        Create query engine.

        Args:
            index: Document index to query
            llm: LLM for answer synthesis
        """
        self._index = index
        self._llm = llm

    async def query(self, question: str) -> str:
        """
        Retrieve relevant documents and synthesize an answer.

        Args:
            question: Natural language question

        Returns:
            Synthesized answer string
        """
        docs = self._index.similarity_search(question, top_k=3)
        context = "\n\n".join(f"[{doc.id}] {doc.text}" for doc in docs)

        if self._llm is None:
            # No LLM: return raw retrieved context
            return f"Retrieved context:\n{context}"

        prompt = (
            f"Answer the question using only the context below.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
        )
        response = await self._llm.complete([Message(role="user", content=prompt)])
        return cast(str, response.content)


# ---------------------------------------------------------------------------
# FunctionTool (mirrors LlamaIndex.FunctionTool)
# ---------------------------------------------------------------------------


class FunctionTool:
    """
    Callable tool that agents can invoke (mirrors LlamaIndex.FunctionTool).
    Pattern: LlamaIndex.FunctionTool → Agenkit Tool class
    """

    def __init__(self, fn: Callable[..., Any], name: str, description: str) -> None:
        """
        Create a tool from a callable.

        Args:
            fn: Underlying function to call (may be async or sync)
            name: Tool name used by the agent
            description: Human-readable description
        """
        self.fn = fn
        self.name = name
        self.description = description

    async def call(self, **kwargs: Any) -> str:
        """
        Invoke the tool.

        Args:
            **kwargs: Tool arguments

        Returns:
            String result
        """
        result = self.fn(**kwargs)
        # Support coroutines returned by async fn
        if asyncio.iscoroutine(result):
            result = await result
        return str(result)


def function_tool(name: str, description: str) -> Callable[[Callable[..., Any]], FunctionTool]:
    """
    Decorator to wrap a function as a FunctionTool (mirrors LlamaIndex @function_tool).
    Pattern: LlamaIndex @function_tool → Agenkit Tool class decorator

    Usage:
        @function_tool(name="search", description="Search documents")
        def search(query: str) -> str:
            return "results"
    """

    def decorator(fn: Callable[..., Any]) -> FunctionTool:
        return FunctionTool(fn=fn, name=name, description=description)

    return decorator


# ---------------------------------------------------------------------------
# FunctionAgent (mirrors LlamaIndex.FunctionAgent)
# ---------------------------------------------------------------------------


class FunctionAgent(Agent):
    """
    Agent with access to a set of FunctionTools (mirrors LlamaIndex.FunctionAgent).
    Pattern: LlamaIndex.FunctionAgent → Agenkit Agent with tool dispatch
    """

    def __init__(
        self,
        name: str,
        llm: LLM,
        tools: list[FunctionTool],
        system_prompt: str = "",
    ) -> None:
        """
        Create a function-calling agent.

        Args:
            name: Agent identifier
            llm: LLM adapter
            tools: Tools available to this agent
            system_prompt: Optional system instructions
        """
        self._name = name
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.system_prompt = system_prompt

    @property
    def name(self) -> str:
        """Return agent name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return declared capabilities."""
        return list(self.tools.keys())

    async def process(self, message: Message) -> Message:
        """
        Process message, optionally using tools, then return final answer.

        Simplified single-turn: build a prompt listing tools, call LLM,
        detect TOOL: / ARGS: markers and dispatch, return final text.
        """
        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())
        preamble = self.system_prompt + "\n\n" if self.system_prompt else ""
        prompt = (
            f"{preamble}"
            f"Available tools:\n{tool_descriptions}\n\n"
            f"To call a tool write: TOOL: <name> ARGS: <key>=<value>\n"
            f"Task: {message.content}"
        )

        response = await self.llm.complete([Message(role="user", content=prompt)])
        content = cast(str, response.content)

        # Dispatch tool if requested
        tool_result: str | None = None
        if "TOOL:" in content and "ARGS:" in content:
            tool_name_raw = content.split("TOOL:")[1].split("ARGS:")[0].strip()
            args_raw = content.split("ARGS:")[1].split("\n")[0].strip()
            if tool_name_raw in self.tools:
                tool_result = await self.tools[tool_name_raw].call(input=args_raw)
                content = f"Tool '{tool_name_raw}' returned: {tool_result}\n\n{content}"

        return Message(
            role="agent",
            content=content,
            metadata={
                "agent_name": self._name,
                "tool_used": tool_result is not None,
            },
        )


# ---------------------------------------------------------------------------
# QueryEngineTool (mirrors LlamaIndex.QueryEngineTool)
# ---------------------------------------------------------------------------


class QueryEngineTool(FunctionTool):
    """
    Wraps a QueryEngine as a FunctionTool (mirrors LlamaIndex.QueryEngineTool).
    Pattern: LlamaIndex.QueryEngineTool → Agenkit Tool wrapping a retriever
    """

    def __init__(self, query_engine: QueryEngine, name: str, description: str) -> None:
        """
        Create a tool backed by a QueryEngine.

        Args:
            query_engine: QueryEngine to wrap
            name: Tool name
            description: Tool description
        """
        self._engine = query_engine

        async def _query(**kwargs: Any) -> str:
            question = kwargs.get("input", kwargs.get("query", ""))
            return await query_engine.query(str(question))

        super().__init__(fn=_query, name=name, description=description)


# ---------------------------------------------------------------------------
# AgentWorkflow (mirrors LlamaIndex.AgentWorkflow)
# ---------------------------------------------------------------------------


class AgentWorkflow:
    """
    Orchestrates multiple FunctionAgents with hand-off routing.
    Pattern: LlamaIndex.AgentWorkflow → Agenkit multi-agent orchestration

    In LlamaIndex, agents emit events to hand off control.  Here we
    simulate that by letting each agent embed "HANDOFF: <agent_name>"
    in its response to transfer to the next agent.
    """

    def __init__(
        self,
        agents: list[FunctionAgent],
        root_agent: str,
        max_steps: int = 5,
    ) -> None:
        """
        Create an agent workflow.

        Args:
            agents: All participating agents
            root_agent: Name of the entry-point agent
            max_steps: Maximum hand-off steps before returning
        """
        self._agents = {a.name: a for a in agents}
        self._root = root_agent
        self._max_steps = max_steps

    async def run(self, task: str) -> str:
        """
        Run the workflow starting from the root agent.

        Args:
            task: Initial task description

        Returns:
            Final response string
        """
        current_agent_name = self._root
        message = Message(role="user", content=task)
        execution_log: list[str] = []

        for step in range(self._max_steps):
            if current_agent_name not in self._agents:
                break

            agent = self._agents[current_agent_name]
            execution_log.append(current_agent_name)
            response = await agent.process(message)
            content = cast(str, response.content)

            # Check for hand-off event (LlamaIndex uses events; we use a marker)
            if "HANDOFF:" in content:
                next_agent = content.split("HANDOFF:")[1].split("\n")[0].strip()
                if next_agent in self._agents:
                    message = Message(
                        role="user",
                        content=content,
                        metadata={"from_agent": current_agent_name},
                    )
                    current_agent_name = next_agent
                    continue

            # No hand-off — workflow complete
            _ = step  # explicitly used in loop
            return f"[Workflow: {' → '.join(execution_log)}]\n\n{content}"

        return f"[Workflow: {' → '.join(execution_log)}]\n\nMax steps reached."


# ---------------------------------------------------------------------------
# Demo examples
# ---------------------------------------------------------------------------


async def example_rag_agent() -> None:
    """Example 1: VectorStoreIndex + QueryEngineTool + FunctionAgent."""
    print("=" * 60)
    print("Example 1: RAG Agent (VectorStoreIndex + QueryEngineTool)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Build a small document corpus
    docs = [
        Document(
            id="doc1",
            text="Agenkit is a cross-language AI agent toolkit supporting Python, Go, TypeScript, Rust, C++, and Zig.",
        ),
        Document(
            id="doc2",
            text="Agenkit supports 11+ orchestration patterns: Sequential, Parallel, Router, ReAct, and more.",
        ),
        Document(
            id="doc3",
            text="Agenkit-runtime provides micro-VM sandboxing for safe agent code execution via Firecracker.",
        ),
    ]

    # LlamaIndex-style: build index, create query engine, wrap as tool
    index = VectorStoreIndex.from_documents(docs)
    engine = index.as_query_engine(llm=llm)
    rag_tool = QueryEngineTool(
        query_engine=engine,
        name="knowledge_base",
        description="Search the Agenkit knowledge base for factual answers",
    )

    agent = FunctionAgent(
        name="research_assistant",
        llm=llm,
        tools=[rag_tool],
        system_prompt="You are a helpful research assistant. Use the knowledge_base tool to answer questions.",
    )

    print("\n   # LlamaIndex-style API:")
    print("   index = VectorStoreIndex.from_documents(docs)")
    print("   engine = index.as_query_engine(llm=llm)")
    print("   rag_tool = QueryEngineTool(query_engine=engine, name='knowledge_base', ...)")
    print("   agent = FunctionAgent(name='research_assistant', llm=llm, tools=[rag_tool])")
    print(
        "   result = await agent.process(Message(role='user', content='What languages does Agenkit support?'))"
    )
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.memory import InMemoryDocumentStore")
    print("   store = InMemoryDocumentStore()")
    print("   store.add_documents(docs)")
    print("   tool = RetrievalTool(store=store, llm=llm)")
    print("   agent = Agent(llm=llm, tools=[tool])")

    print(
        "\n   Pattern: LlamaIndex.VectorStoreIndex + QueryEngineTool → Agenkit InMemoryDocumentStore + RetrievalTool"
    )
    print("   Similarity search: keyword overlap (demo); production uses embedding vectors.")


async def example_react_agent() -> None:
    """Example 2: ReAct-style agent with calculator and search tools."""
    print("\n\n" + "=" * 60)
    print("Example 2: ReActAgent Loop (reason + act + observe)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    @function_tool(name="calculator", description="Evaluate a math expression, e.g. '2 + 2 * 3'")
    def calculator(input: str) -> str:
        """Safe-ish calculator for demo purposes."""
        allowed = set("0123456789+-*/(). ")
        expr = "".join(c for c in input if c in allowed)
        try:
            return str(eval(expr))  # noqa: S307 — demo only, not production
        except Exception as exc:
            return f"Error: {exc}"

    @function_tool(name="web_search", description="Search the web for current information")
    def web_search(input: str) -> str:
        """Simulated web search for demo."""
        return f"[Simulated search results for: {input}]"

    agent = FunctionAgent(
        name="react_agent",
        llm=llm,
        tools=[calculator, web_search],
        system_prompt="Think step-by-step (Thought/Action/Observation) before giving a final answer.",
    )

    print("\n   # LlamaIndex-style API:")
    print("   from llama_index.core.agent import ReActAgent")
    print("   agent = ReActAgent.from_tools([calculator, web_search], llm=llm)")
    print("   response = agent.chat('What is (42 * 3) + 7?')")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import ReActAgent")
    print("   agent = ReActAgent(llm=llm, tools=[calculator, web_search])")
    print("   response = await agent.process(Message(role='user', content='...'))")

    print("\n   Pattern: LlamaIndex.ReActAgent → Agenkit ReActAgent (patterns package)")
    print("   Reason → Tool Call → Observe → Repeat until final answer.")


async def example_agent_workflow() -> None:
    """Example 3: AgentWorkflow with researcher → writer hand-off."""
    print("\n\n" + "=" * 60)
    print("Example 3: AgentWorkflow (multi-agent event-driven hand-off)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    @function_tool(name="search", description="Search for information on a topic")
    def search(input: str) -> str:
        """Simulated search for demo."""
        return f"[Research findings on '{input}': Agenkit supports 6 languages and 11+ patterns.]"

    @function_tool(name="format_report", description="Format raw notes into a polished report")
    def format_report(input: str) -> str:
        """Format raw text into structured report."""
        return f"## Report\n\n{input}\n\n*Formatted by writer agent.*"

    researcher = FunctionAgent(
        name="researcher",
        llm=llm,
        tools=[search],
        system_prompt=(
            "You are a research agent. Use the search tool to gather information, "
            "then emit HANDOFF: writer to pass findings to the writer."
        ),
    )

    writer = FunctionAgent(
        name="writer",
        llm=llm,
        tools=[format_report],
        system_prompt="You are a writing agent. Use format_report to produce a clean output.",
    )

    workflow = AgentWorkflow(
        agents=[researcher, writer],
        root_agent="researcher",
    )

    print("\n   # LlamaIndex-style API (v0.10+):")
    print("   from llama_index.core.workflow import AgentWorkflow")
    print("   workflow = AgentWorkflow(")
    print("       agents=[researcher, writer],")
    print("       root_agent='researcher',")
    print("   )")
    print("   result = await workflow.run(task='Write a report on Agenkit')")
    print()
    print("   # Agenkit equivalent:")
    print("   from agenkit.patterns import SequentialAgent")
    print("   pipeline = SequentialAgent([researcher, writer])")
    print("   result = await pipeline.process(message)")

    print("\n   Pattern: LlamaIndex.AgentWorkflow → Agenkit SequentialAgent / custom orchestrator")
    print("   Hand-off events (LlamaIndex) → HANDOFF marker or SequentialAgent pipe (Agenkit)")


async def main() -> None:
    """Run all MiniLlamaIndex examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 5 + "MiniLlamaIndex - LlamaIndex Built on Agenkit" + " " * 8 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n   Demonstrate: LlamaIndex Agent Workflow patterns on Agenkit")

    await example_rag_agent()
    await example_react_agent()
    await example_agent_workflow()

    print("\n\n" + "=" * 60)
    print("MiniLlamaIndex Examples Complete")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("   Agenkit supports LlamaIndex-style RAG + agent patterns:")
    print("     - VectorStoreIndex     → InMemoryDocumentStore")
    print("     - QueryEngine          → retriever + LLM synthesis")
    print("     - QueryEngineTool      → Tool wrapping a retriever")
    print("     - FunctionAgent        → Agent with tool dispatch")
    print("     - ReActAgent           → agenkit.patterns.ReActAgent")
    print("     - AgentWorkflow        → SequentialAgent / custom orchestrator")
    print("     - Event-driven hand-off → HANDOFF marker or SequentialAgent")

    print("\nMigration guide: docs/migrations/llamaindex-to-agenkit.md")
    print("\nWhy Agenkit over LlamaIndex?")
    print("   6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   18x faster in Go for production workloads")
    print("   11+ orchestration patterns, not just RAG-focused agents")
    print("   Any LLM provider (not tied to LlamaIndex integrations)")
    print("   OpenTelemetry observability built-in")
    print("   Production middleware: retry, circuit breaker, timeout")


if __name__ == "__main__":
    asyncio.run(main())
