#!/usr/bin/env python3
"""
MiniHaystack - Haystack Equivalent Built on Agenkit

Demonstrates how Haystack's pipeline-based architecture can be built
ON TOP of Agenkit primitives, showing toolkit philosophy.

Pattern Mappings: Haystack Pipeline → SequentialAgent,
Component → Agent, PromptNode → LLM adapter

Migration guide: docs/migrations/haystack-to-agenkit.md

Usage: uv run python examples/frameworks/minihaystack.py
"""

import asyncio
from typing import Any, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


class Component(Agent):
    """
    Base component interface (mirrors Haystack.Component).
    Pattern: Haystack.Component → Agenkit Agent
    """

    @property
    def name(self) -> str:
        """Return component's name."""
        return self.__class__.__name__.lower().replace("component", "")

    @property
    def capabilities(self) -> list[str]:
        """Return component capabilities."""
        return ["pipeline_component"]


class Pipeline:
    """
    Sequential component pipeline (mirrors Haystack.Pipeline).
    Pattern: Haystack.Pipeline → Sequential composition of agents
    """

    def __init__(self) -> None:
        """Create empty pipeline."""
        self.components: list[Component] = []

    def add_component(self, name: str, component: Component) -> None:
        """Add component to pipeline."""
        self.components.append(component)

    async def run(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Run pipeline with input data.

        Args:
            data: Input data dictionary

        Returns:
            Output data dictionary
        """
        current_message = Message(role="user", content=data.get("input", ""), metadata=data)

        # Execute components sequentially
        for component in self.components:
            current_message = await component.process(current_message)

        return {"output": current_message.content, "metadata": current_message.metadata}


class PromptBuilder(Component):
    """
    Template-based prompt builder (mirrors Haystack.PromptBuilder).
    Pattern: Haystack.PromptBuilder → Agent with template interpolation
    """

    def __init__(self, template: str) -> None:
        """
        Create prompt builder with template.

        Args:
            template: Prompt template with {{variable}} placeholders
        """
        self.template = template

    async def process(self, message: Message) -> Message:
        """Build prompt from template and message data."""
        # Extract variables from metadata or content
        variables = message.metadata.copy()
        variables["input"] = message.content

        # Simple template substitution (Haystack uses Jinja2, we use simple {{var}})
        prompt = self.template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        return Message(
            role="user",
            content=prompt,
            metadata={**message.metadata, "template": self.template},
        )


class Generator(Component):
    """
    LLM generation component (mirrors Haystack generators).
    Pattern: Haystack.OpenAIGenerator → Agenkit LLM adapter
    """

    def __init__(self, llm: LLM) -> None:
        """
        Create generator with LLM.

        Args:
            llm: LLM adapter to use for generation
        """
        self.llm = llm

    async def process(self, message: Message) -> Message:
        """Generate response using LLM."""
        response = await self.llm.complete([message])

        return Message(
            role="agent",
            content=cast("str", response.content),
            metadata={**message.metadata, "generator": "llm"},
        )


class Document:
    """Simple document class (mirrors Haystack.Document)."""

    def __init__(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Create document."""
        self.content = content
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Document(content={self.content[:50]}...)"


class InMemoryDocumentStore:
    """
    Simple in-memory document storage (mirrors Haystack.InMemoryDocumentStore).
    Pattern: Haystack.DocumentStore → Simple list storage
    """

    def __init__(self) -> None:
        """Create empty document store."""
        self.documents: list[Document] = []

    def write_documents(self, documents: list[Document]) -> None:
        """Write documents to store."""
        self.documents.extend(documents)

    def search(self, query: str, top_k: int = 5) -> list[Document]:
        """
        Simple keyword-based search.
        Note: Real Haystack uses BM25, embeddings, etc. This is simplified for demo.
        """
        # Simple keyword matching
        query_lower = query.lower()
        results = [doc for doc in self.documents if query_lower in doc.content.lower()]
        return results[:top_k]


class Retriever(Component):
    """
    Document retrieval component (mirrors Haystack retrievers).
    Pattern: Haystack.Retriever → Agent with document store search
    """

    def __init__(self, document_store: InMemoryDocumentStore, top_k: int = 3) -> None:
        """
        Create retriever.

        Args:
            document_store: Document store to search
            top_k: Number of documents to retrieve
        """
        self.document_store = document_store
        self.top_k = top_k

    async def process(self, message: Message) -> Message:
        """Retrieve documents based on query."""
        query = message.content

        # Search documents
        documents = self.document_store.search(query, top_k=self.top_k)

        # Format documents as context
        context = "\n".join(f"- {doc.content}" for doc in documents)

        return Message(
            role="user",
            content=f"Context:\n{context}\n\nQuery: {query}",
            metadata={
                **message.metadata,
                "retrieved_docs": len(documents),
                "documents": [doc.content for doc in documents],
            },
        )


async def example_simple_pipeline() -> None:
    """Example: Simple QA pipeline (prompt builder → generator)."""
    print("=" * 60)
    print("Example 1: Simple QA Pipeline")
    print("=" * 60)

    # Create LLM (using test key for demo)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create pipeline components
    prompt_builder = PromptBuilder(template="Translate to French: {{input}}")
    generator = Generator(llm=llm)

    # Create pipeline
    pipeline = Pipeline()
    pipeline.add_component("prompt_builder", prompt_builder)
    pipeline.add_component("generator", generator)

    print("\n📝 Haystack-style API:")
    print("   pipeline = Pipeline()")
    print("   pipeline.add_component('prompt_builder', PromptBuilder(...))")
    print("   pipeline.add_component('generator', Generator(...))")
    print("   result = await pipeline.run({'input': 'Hello, world!'})")

    print("\n✅ Pattern: Haystack.Pipeline → Sequential component composition")
    print("   Components process data in order, passing output to next component")


async def example_rag_pipeline() -> None:
    """Example: RAG pipeline (retriever → prompt builder → generator)."""
    print("\n\n" + "=" * 60)
    print("Example 2: RAG Pipeline")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create document store
    document_store = InMemoryDocumentStore()
    document_store.write_documents(
        [
            Document(content="Paris is the capital of France."),
            Document(content="Berlin is the capital of Germany."),
            Document(content="London is the capital of the United Kingdom."),
            Document(content="Rome is the capital of Italy."),
        ]
    )

    # Create RAG pipeline
    retriever = Retriever(document_store=document_store, top_k=2)
    prompt_builder = PromptBuilder(
        template="""Using the context below, answer the question.

{{input}}

Provide a clear, concise answer."""
    )
    generator = Generator(llm=llm)

    # Assemble pipeline
    pipeline = Pipeline()
    pipeline.add_component("retriever", retriever)
    pipeline.add_component("prompt_builder", prompt_builder)
    pipeline.add_component("generator", generator)

    print("\n📝 Haystack-style RAG:")
    print("   document_store = InMemoryDocumentStore()")
    print("   document_store.write_documents([...])")
    print("   ")
    print("   pipeline.add_component('retriever', Retriever(document_store))")
    print("   pipeline.add_component('prompt_builder', PromptBuilder(...))")
    print("   pipeline.add_component('generator', Generator(...))")
    print("   ")
    print("   result = await pipeline.run({'input': 'What is the capital of France?'})")

    print("\n✅ Pattern: Haystack RAG → Retriever + PromptBuilder + Generator")
    print("   Retriever finds relevant documents, prompt builder formats context,")
    print("   generator produces final answer")


async def example_custom_component() -> None:
    """Example: Custom component implementation."""
    print("\n\n" + "=" * 60)
    print("Example 3: Custom Component")
    print("=" * 60)

    class TextCleanerComponent(Component):
        """Custom component for text cleaning."""

        async def process(self, message: Message) -> Message:
            """Clean and normalize text."""
            # Simple cleaning: lowercase, strip whitespace
            cleaned = message.content.strip().lower()

            return Message(
                role="user",
                content=cleaned,
                metadata={**message.metadata, "cleaned": True},
            )

    print("\n📝 Haystack Pattern:")
    print("   @component")
    print("   class TextCleanerComponent:")
    print("       @component.output_types(text=str)")
    print("       def run(self, text: str):")
    print("           return {'text': text.lower().strip()}")

    print("\n✅ Agenkit Equivalent:")
    print("   class TextCleanerComponent(Component):")
    print("       async def process(self, message: Message) -> Message:")
    print("           cleaned = message.content.strip().lower()")
    print("           return Message(role='user', content=cleaned)")

    print("\n💡 Why it's better:")
    print("   • No decorator magic - explicit interface")
    print("   • Standard Agent interface - composable with all patterns")
    print("   • Type-safe with Message objects")
    print("   • Async-first for better I/O handling")


async def main() -> None:
    """Run all examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 9 + "MiniHaystack - Haystack Built on Agenkit" + " " * 8 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n🎯 Demonstrate: Haystack pipeline patterns on Agenkit")

    await example_simple_pipeline()
    await example_rag_pipeline()
    await example_custom_component()

    print("\n\n" + "=" * 60)
    print("✅ MiniHaystack Examples Complete")
    print("=" * 60)
    print("\n🔑 Key Takeaways:")
    print("   • Agenkit is a TOOLKIT for building pipeline-based systems")
    print("   • Haystack patterns map to Agenkit primitives:")
    print("     - Pipeline → Sequential component composition")
    print("     - Component → Agent interface")
    print("     - PromptBuilder → Template interpolation")
    print("     - Generator → LLM adapter")
    print("     - Retriever → Search + Agent")
    print("     - DocumentStore → External storage")

    print("\n📚 Migration guide: docs/migrations/haystack-to-agenkit.md")
    print("\n💡 Why Agenkit over Haystack?")
    print("   ✓ 6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   ✓ 18x faster (Go) for production deployments")
    print("   ✓ Simpler mental model (no component graph DSL)")
    print("   ✓ Explicit control (no hidden pipeline orchestration)")
    print("   ✓ Production middleware (retry, circuit breaker, timeout)")


if __name__ == "__main__":
    asyncio.run(main())
