"""
QA Agent - Answers questions using the knowledge base (RAG pattern).
"""

from knowledge_base import VectorStore

from agenkit import Agent, Message


class QAAgent(Agent):
    """
    Question-answering agent using RAG (Retrieval-Augmented Generation).

    Searches the knowledge base for relevant documents and formulates answers.
    """

    def __init__(self, knowledge_base: VectorStore, top_k: int = 3):
        """
        Initialize QA agent.

        Args:
            knowledge_base: Vector store with support documents
            top_k: Number of relevant documents to retrieve
        """
        self.knowledge_base = knowledge_base
        self.top_k = top_k

    @property
    def name(self) -> str:
        return "QAAgent"

    async def process(self, message: Message) -> Message:
        """
        Answer a question using knowledge base.

        Args:
            message: User question

        Returns:
            Message with answer and sources
        """
        query = message.content

        # Search knowledge base
        results = self.knowledge_base.search(query=query, top_k=self.top_k, threshold=0.1)

        if not results:
            return Message(
                role="assistant",
                content="I don't have specific information about that in our knowledge base. Let me escalate this to a human agent.",
                metadata={"confidence": 0.0, "sources": []},
            )

        # Extract relevant information
        sources = []
        context_parts = []

        for doc, score in results:
            sources.append(
                {
                    "id": doc.id,
                    "similarity": round(score, 3),
                    "category": doc.metadata.get("category", "unknown"),
                }
            )
            context_parts.append(doc.content)

        # Formulate answer (in production, use LLM here)
        answer = self._formulate_answer(query, context_parts, results[0][1])

        return Message(
            role="assistant",
            content=answer,
            metadata={
                "confidence": round(results[0][1], 3),
                "sources": sources,
                "num_sources": len(sources),
            },
        )

    def _formulate_answer(self, query: str, context_parts: list, confidence: float) -> str:
        """
        Formulate answer from retrieved context.

        In production, use an LLM (GPT-4, Claude, etc.) to generate natural answers.
        This is a simplified version for demonstration.
        """
        if confidence < 0.3:
            return "I found some potentially relevant information, but I'm not confident it answers your question. Let me connect you with a human agent."

        # Use the most relevant context
        primary_context = context_parts[0] if context_parts else ""

        if confidence >= 0.6:
            return f"Based on our documentation: {primary_context}"
        else:
            return f"Here's what I found: {primary_context}\n\nIf this doesn't fully answer your question, I can escalate to a human agent."
