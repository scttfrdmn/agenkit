"""
RAG (Retrieval-Augmented Generation) Composition

A simple composition that combines retrieval + generation for question answering.
This demonstrates that "RAG" is just Sequential + RetrievalAgent + AnswerAgent.

For production RAG systems with caching, reranking, and optimization,
consider building a full pattern with proper error handling.

This composition is perfect for:
- Quick prototypes
- Learning RAG fundamentals
- Simple question-answering systems
- MVP implementations

References:
    Source: Gulli "Agentic Design Patterns" (2025)
    Pattern: Sequential pattern in agenkit.patterns.sequential

Example:
    Basic usage::

        from agenkit.techniques.compositions import SimpleRAG
        from agenkit import Message

        rag = SimpleRAG(
            retriever=my_vector_store,
            answerer=my_llm_agent
        )

        response = await rag.process(Message(
            role="user",
            content="What is quantum computing?"
        ))
"""

from collections.abc import Callable

from agenkit import Agent, Message


class SimpleRAG(Agent):
    """
    Simple Retrieval-Augmented Generation composition.

    This is a minimal RAG implementation that:
    1. Retrieves relevant documents for a query
    2. Passes documents as context to LLM
    3. Generates an answer

    It's intentionally simple (~40 LOC) to show that RAG is just
    retrieval + generation. For production systems with reranking,
    caching, and optimization, build a custom pattern.

    Attributes:
        name: Agent name (always "simple_rag")
        retriever: Function that retrieves documents for a query
        answerer: Agent that generates answers from context
        max_docs: Maximum documents to retrieve
        include_sources: Whether to include source docs in metadata
    """

    def __init__(
        self,
        retriever: Callable[[str], list[str]],
        answerer: Agent,
        max_docs: int = 5,
        include_sources: bool = True,
    ):
        """
        Initialize simple RAG composition.

        Args:
            retriever: Function that takes a query string and returns
                list of relevant document strings. Could be a vector store,
                keyword search, or any retrieval mechanism.
            answerer: Agent that generates answers. Should accept
                messages with context in the content.
            max_docs: Maximum number of documents to retrieve. Default 5.
            include_sources: Whether to include retrieved docs in
                response metadata. Default True.

        Example:
            >>> def my_retriever(query: str) -> List[str]:
            ...     # Your retrieval logic
            ...     return ["doc1", "doc2"]
            >>>
            >>> rag = SimpleRAG(
            ...     retriever=my_retriever,
            ...     answerer=my_llm_agent,
            ...     max_docs=3
            ... )
        """
        self.retriever = retriever
        self.answerer = answerer
        self.max_docs = max_docs
        self.include_sources = include_sources

    @property
    def name(self) -> str:
        """Return agent name."""
        return "simple_rag"

    async def process(self, message: Message) -> Message:
        """
        Process query with RAG: retrieve documents, then generate answer.

        Args:
            message: Input message with query

        Returns:
            Message with answer. Metadata includes:
                - sources: Retrieved documents (if include_sources=True)
                - num_sources: Number of documents retrieved
                - technique: Always "simple_rag"

        Example:
            >>> response = await rag.process(Message(
            ...     role="user",
            ...     content="What is machine learning?"
            ... ))
            >>> print(response.content)
            >>> print(response.metadata['num_sources'])
        """
        query = message.content

        # Step 1: Retrieve relevant documents
        documents = self.retriever(query)[: self.max_docs]

        # Step 2: Build context from documents
        context = self._build_context(query, documents)

        # Step 3: Generate answer using answerer agent
        response = await self.answerer.process(Message(role="user", content=context))

        # Add metadata
        metadata = {"technique": "simple_rag", "num_sources": len(documents)}

        if self.include_sources:
            metadata["sources"] = documents

        # Preserve existing metadata if any
        if response.metadata:
            metadata.update(response.metadata)

        return Message(role=response.role, content=response.content, metadata=metadata)

    def _build_context(self, query: str, documents: list[str]) -> str:
        """
        Build context string from query and retrieved documents.

        Args:
            query: Original query
            documents: Retrieved documents

        Returns:
            Formatted context string for LLM
        """
        if not documents:
            return f"Question: {query}\n\nNo relevant documents found. Please answer based on your knowledge."

        # Format documents
        docs_text = "\n\n".join([f"Document {i + 1}:\n{doc}" for i, doc in enumerate(documents)])

        # Build prompt
        context = f"""Answer the following question using the provided documents.

Question: {query}

Retrieved Documents:
{docs_text}

Answer:"""

        return context

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["retrieval", "question_answering", "rag", "context_augmentation"]
