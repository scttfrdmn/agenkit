"""
Simple vector store implementation for RAG (Retrieval-Augmented Generation).

This is a simplified in-memory implementation for demonstration purposes.
In production, you would use:
- Pinecone, Weaviate, Qdrant for managed vector databases
- pgvector for PostgreSQL-based storage
- ChromaDB for local/embedded use cases
"""

import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Document:
    """A document in the knowledge base."""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate document."""
        if not self.id:
            raise ValueError("Document ID cannot be empty")
        if not self.content:
            raise ValueError("Document content cannot be empty")


class VectorStore:
    """
    Simple in-memory vector store with cosine similarity search.

    Features:
    - Add/remove documents
    - Generate simple embeddings (bag-of-words)
    - Similarity search
    - Metadata filtering

    Example:
        ```python
        store = VectorStore()

        # Add documents
        store.add_document(Document(
            id="doc1",
            content="How to reset your password",
            metadata={"category": "account", "priority": "high"}
        ))

        # Search
        results = store.search("password reset", top_k=5)
        ```
    """

    def __init__(self):
        """Initialize vector store."""
        self.documents: Dict[str, Document] = {}
        self.vocabulary: Dict[str, int] = {}  # word -> index
        self.idf: Dict[str, float] = {}  # word -> inverse document frequency

    def add_document(self, document: Document) -> None:
        """
        Add a document to the store.

        Args:
            document: Document to add

        Raises:
            ValueError: If document with same ID already exists
        """
        if document.id in self.documents:
            raise ValueError(f"Document with ID '{document.id}' already exists")

        # Generate embedding if not provided
        if document.embedding is None:
            document.embedding = self._generate_embedding(document.content)

        self.documents[document.id] = document
        self._update_vocabulary(document.content)
        self._update_idf()

    def add_documents(self, documents: List[Document]) -> None:
        """Add multiple documents."""
        for doc in documents:
            self.add_document(doc)

    def remove_document(self, document_id: str) -> None:
        """
        Remove a document from the store.

        Args:
            document_id: ID of document to remove
        """
        if document_id in self.documents:
            del self.documents[document_id]
            self._update_idf()

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.documents.get(document_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.0,
    ) -> List[tuple[Document, float]]:
        """
        Search for similar documents.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters (must match exactly)
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (document, similarity_score) tuples, sorted by score descending
        """
        if not self.documents:
            return []

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Calculate similarities
        results = []
        for doc_id, doc in self.documents.items():
            # Apply metadata filters
            if filters:
                if not self._matches_filters(doc, filters):
                    continue

            # Calculate similarity
            similarity = self._cosine_similarity(query_embedding, doc.embedding)

            # Apply threshold
            if similarity >= threshold:
                results.append((doc, similarity))

        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def list_documents(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        List all documents, optionally filtered by metadata.

        Args:
            filters: Metadata filters (must match exactly)

        Returns:
            List of documents matching filters
        """
        if filters is None:
            return list(self.documents.values())

        return [
            doc
            for doc in self.documents.values()
            if self._matches_filters(doc, filters)
        ]

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents, optionally filtered."""
        return len(self.list_documents(filters))

    def clear(self) -> None:
        """Remove all documents."""
        self.documents.clear()
        self.vocabulary.clear()
        self.idf.clear()

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate a simple TF-IDF embedding for text.

        In production, use:
        - OpenAI embeddings (text-embedding-ada-002)
        - Sentence transformers (sentence-transformers library)
        - Cohere embeddings
        """
        words = self._tokenize(text)

        # Calculate term frequency
        tf: Dict[str, float] = {}
        for word in words:
            tf[word] = tf.get(word, 0) + 1

        # Normalize by document length
        if words:
            for word in tf:
                tf[word] /= len(words)

        # Create embedding vector (TF-IDF)
        embedding = []
        for word, idx in sorted(self.vocabulary.items(), key=lambda x: x[1]):
            tf_score = tf.get(word, 0)
            idf_score = self.idf.get(word, 0)
            embedding.append(tf_score * idf_score)

        return embedding if embedding else [0.0]

    def _update_vocabulary(self, text: str) -> None:
        """Update vocabulary with new words."""
        words = self._tokenize(text)
        for word in set(words):
            if word not in self.vocabulary:
                self.vocabulary[word] = len(self.vocabulary)

    def _update_idf(self) -> None:
        """Update inverse document frequency for all words."""
        if not self.documents:
            self.idf.clear()
            return

        # Count documents containing each word
        doc_freq: Dict[str, int] = {}
        for doc in self.documents.values():
            words = set(self._tokenize(doc.content))
            for word in words:
                doc_freq[word] = doc_freq.get(word, 0) + 1

        # Calculate IDF
        num_docs = len(self.documents)
        for word in self.vocabulary:
            df = doc_freq.get(word, 0)
            if df > 0:
                self.idf[word] = math.log(num_docs / df)
            else:
                self.idf[word] = 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        # Ensure vectors are same length
        max_len = max(len(vec1), len(vec2))
        vec1 = vec1 + [0.0] * (max_len - len(vec1))
        vec2 = vec2 + [0.0] * (max_len - len(vec2))

        # Calculate dot product and magnitudes
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization (lowercase + split on whitespace)."""
        # In production, use proper tokenization (nltk, spacy, etc.)
        return text.lower().split()

    def _matches_filters(self, document: Document, filters: Dict[str, Any]) -> bool:
        """Check if document matches metadata filters."""
        for key, value in filters.items():
            if document.metadata.get(key) != value:
                return False
        return True


def create_sample_knowledge_base() -> VectorStore:
    """
    Create a sample knowledge base with common customer support documents.

    Returns:
        VectorStore populated with sample documents
    """
    store = VectorStore()

    sample_docs = [
        Document(
            id="kb001",
            content="To reset your password, go to the login page and click 'Forgot Password'. Enter your email address and you'll receive a reset link.",
            metadata={"category": "account", "priority": "high", "topic": "password"},
        ),
        Document(
            id="kb002",
            content="You can update your billing information in Account Settings under the Billing tab. Click 'Update Payment Method' to change your credit card.",
            metadata={"category": "billing", "priority": "high", "topic": "payment"},
        ),
        Document(
            id="kb003",
            content="To cancel your subscription, navigate to Account Settings > Subscription and click 'Cancel Subscription'. Your access will continue until the end of the current billing period.",
            metadata={
                "category": "billing",
                "priority": "high",
                "topic": "subscription",
            },
        ),
        Document(
            id="kb004",
            content="Our Premium plan includes unlimited storage, priority support, advanced analytics, and API access. Pricing starts at $29/month.",
            metadata={"category": "pricing", "priority": "medium", "topic": "plans"},
        ),
        Document(
            id="kb005",
            content="To export your data, go to Settings > Data Export. Select the format (CSV, JSON, or PDF) and click 'Export'. The export will be emailed to you within 24 hours.",
            metadata={"category": "data", "priority": "medium", "topic": "export"},
        ),
        Document(
            id="kb006",
            content="Two-factor authentication adds an extra layer of security. Enable it in Security Settings. You'll need an authenticator app like Google Authenticator or Authy.",
            metadata={"category": "security", "priority": "high", "topic": "2fa"},
        ),
        Document(
            id="kb007",
            content="To share files with team members, use the 'Share' button on any file. You can set permissions (view, edit, or admin) for each user or create a shareable link.",
            metadata={
                "category": "collaboration",
                "priority": "medium",
                "topic": "sharing",
            },
        ),
        Document(
            id="kb008",
            content="If you're experiencing slow performance, try clearing your browser cache, disabling browser extensions, or using a different browser. Contact support if issues persist.",
            metadata={
                "category": "troubleshooting",
                "priority": "medium",
                "topic": "performance",
            },
        ),
        Document(
            id="kb009",
            content="Our mobile app is available for iOS and Android. Download it from the App Store or Google Play. Sign in with your existing account credentials.",
            metadata={"category": "mobile", "priority": "low", "topic": "app"},
        ),
        Document(
            id="kb010",
            content="API documentation is available at docs.example.com/api. You'll need an API key from Account Settings > API Access. Rate limits apply based on your plan.",
            metadata={
                "category": "developer",
                "priority": "low",
                "topic": "api",
            },
        ),
    ]

    store.add_documents(sample_docs)
    return store
