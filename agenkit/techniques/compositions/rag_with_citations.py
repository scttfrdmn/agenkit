"""
RAG with Citations Composition

Extends basic RAG to track source attribution and generate citations.
This is critical for domains where source attribution matters (legal, medical, research).

This composition adds citation tracking to basic RAG by:
1. Retrieving documents with metadata
2. Generating answer with citation markers
3. Tracking which documents were cited

For production systems, consider implementing proper citation formats
(APA, MLA, Chicago, etc.) and verification of citation accuracy.

This composition is perfect for:
- Research assistants
- Legal document analysis
- Medical literature review
- Academic question answering

References:
    Source: Rothman "Context Engineering for Multi-Agent Systems" Ch. 7 (2025)
    Related: SimpleRAG composition

Example:
    Basic usage::

        from agenkit.techniques.compositions import CitedRAG
        from agenkit import Message

        rag = CitedRAG(
            retriever=my_vector_store_with_metadata,
            answerer=my_llm_agent
        )

        response = await rag.process(Message(
            role="user",
            content="What are the side effects of aspirin?"
        ))

        # Answer includes citations like [1], [2]
        print(response.content)
        # Access source documents
        print(response.metadata['sources'])
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agenkit import Agent, Message


@dataclass
class Document:
    """
    Document with metadata for citation tracking.

    Attributes:
        content: The document text
        source: Source identifier (e.g., "Smith et al. 2020")
        metadata: Additional metadata (page, section, etc.)
    """
    content: str
    source: str
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CitedRAG(Agent):
    """
    RAG with citation tracking composition.

    Extends basic RAG to track which documents were used and generate
    proper citation markers in the response.

    This is particularly important for:
    - Medical/legal domains requiring source attribution
    - Research and academic applications
    - Fact-checking and verification workflows

    Attributes:
        name: Agent name (always "cited_rag")
        retriever: Function that retrieves documents with metadata
        answerer: Agent that generates cited answers
        max_docs: Maximum documents to retrieve
        citation_format: Citation format ("numeric" or "author_year")
    """

    def __init__(
        self,
        retriever: Callable[[str], list[Document]],
        answerer: Agent,
        max_docs: int = 5,
        citation_format: str = "numeric"
    ):
        """
        Initialize cited RAG composition.

        Args:
            retriever: Function that takes query and returns List[Document].
                Each document should have content, source, and metadata.
            answerer: Agent that generates answers with citations.
            max_docs: Maximum number of documents to retrieve. Default 5.
            citation_format: Format for citations:
                - "numeric": [1], [2], [3]
                - "author_year": (Smith 2020), (Jones 2021)
                Default: "numeric"

        Example:
            >>> def my_retriever(query: str) -> List[Document]:
            ...     # Your retrieval with metadata
            ...     return [
            ...         Document(
            ...             content="Aspirin reduces fever",
            ...             source="Smith et al. 2020",
            ...             metadata={"page": 42}
            ...         )
            ...     ]
            >>>
            >>> rag = CitedRAG(
            ...     retriever=my_retriever,
            ...     answerer=my_llm_agent
            ... )
        """
        self.retriever = retriever
        self.answerer = answerer
        self.max_docs = max_docs
        self.citation_format = citation_format

    @property
    def name(self) -> str:
        """Return agent name."""
        return "cited_rag"

    async def process(self, message: Message) -> Message:
        """
        Process query with cited RAG: retrieve, generate with citations.

        Args:
            message: Input message with query

        Returns:
            Message with cited answer. Metadata includes:
                - sources: List of source documents
                - citations: List of citation strings
                - num_sources: Number of documents retrieved
                - technique: Always "cited_rag"

        Example:
            >>> response = await rag.process(Message(
            ...     role="user",
            ...     content="What are the benefits of exercise?"
            ... ))
            >>> print(response.content)
            "Exercise improves health [1] and reduces stress [2]."
            >>> print(response.metadata['citations'])
            ["[1] Smith et al. 2020", "[2] Jones et al. 2021"]
        """
        query = message.content

        # Step 1: Retrieve documents with metadata
        documents = self.retriever(query)[:self.max_docs]

        if not documents:
            return Message(
                role="assistant",
                content="No relevant sources found to answer this question.",
                metadata={
                    "technique": "cited_rag",
                    "num_sources": 0,
                    "sources": [],
                    "citations": []
                }
            )

        # Step 2: Build citation mapping
        citations = self._build_citations(documents)

        # Step 3: Build context with citation instructions
        context = self._build_context_with_citations(query, documents, citations)

        # Step 4: Generate cited answer
        response = await self.answerer.process(
            Message(role="user", content=context)
        )

        # Step 5: Add metadata
        metadata = {
            "technique": "cited_rag",
            "num_sources": len(documents),
            "sources": [doc.source for doc in documents],
            "citations": list(citations.values()),
            "full_documents": documents  # Include full documents for reference
        }

        if response.metadata:
            metadata.update(response.metadata)

        return Message(
            role=response.role,
            content=response.content,
            metadata=metadata
        )

    def _build_citations(self, documents: list[Document]) -> dict[int, str]:
        """
        Build citation mapping from document index to citation string.

        Args:
            documents: List of documents

        Returns:
            Dictionary mapping index to citation string
        """
        citations = {}

        for i, doc in enumerate(documents, 1):
            if self.citation_format == "numeric":
                citations[i] = f"[{i}] {doc.source}"
            elif self.citation_format == "author_year":
                citations[i] = f"({doc.source})"
            else:
                citations[i] = f"[{i}] {doc.source}"

        return citations

    def _build_context_with_citations(
        self,
        query: str,
        documents: list[Document],
        citations: dict[int, str]
    ) -> str:
        """
        Build context with citation instructions.

        Args:
            query: Original query
            documents: Retrieved documents
            citations: Citation mapping

        Returns:
            Formatted context for LLM
        """
        # Format documents with citation numbers
        docs_text = ""
        for i, doc in enumerate(documents, 1):
            docs_text += f"\n[{i}] {doc.source}\n{doc.content}\n"

        # Build instruction prompt
        if self.citation_format == "numeric":
            citation_instruction = "Use [1], [2], etc. to cite sources"
        else:
            citation_instruction = "Use (Author Year) format to cite sources"

        context = f"""Answer the following question using ONLY the provided documents.
{citation_instruction} for every factual claim.

Question: {query}

Sources:
{docs_text}

Instructions:
- Cite sources for every claim using the format shown above
- Only use information from the provided documents
- If documents don't contain enough information, state what's missing

Answer:"""

        return context

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return [
            "retrieval",
            "question_answering",
            "rag",
            "citation",
            "source_attribution"
        ]
