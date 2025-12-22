"""Knowledge base components for customer support system."""

from knowledge_base.vector_store import (Document, VectorStore,
                                         create_sample_knowledge_base)

__all__ = ["Document", "VectorStore", "create_sample_knowledge_base"]
