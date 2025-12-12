"""
Learning from Feedback Composition

A simple composition that stores past interactions in memory and retrieves
similar ones to provide context for future interactions. This demonstrates
basic learning from experience.

This composition shows that "learning from feedback" is just:
1. Storing interactions in memory
2. Retrieving similar past interactions
3. Using them as context

For production learning systems with sophisticated memory management,
embeddings, and adaptive behavior, build a custom pattern or use the
MemoryHierarchyAgent pattern.

This composition is perfect for:
- Simple experience-based learning
- Quick prototypes with memory
- Learning basic feedback patterns
- Non-critical personalization

References:
    Pattern: MemoryHierarchyAgent in agenkit.patterns.memory_hierarchy
    Related: Retrieval-Augmented Generation (RAG)

Example:
    Basic usage::

        from agenkit.techniques.compositions import LearningFromFeedback
        from agenkit import Message

        learner = LearningFromFeedback(
            agent=my_base_agent,
            similarity_fn=cosine_similarity,
            max_context_examples=3
        )

        # First interaction - no context
        response1 = await learner.process(
            Message(role="user", content="How do I sort a list?")
        )

        # Provide feedback
        learner.add_feedback(response1, score=0.8)

        # Second interaction - uses first as context
        response2 = await learner.process(
            Message(role="user", content="How do I sort a dictionary?")
        )
"""

from typing import Callable, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from agenkit import Agent, Message


@dataclass
class Interaction:
    """
    Stored interaction for learning.

    Attributes:
        query: Original query
        response: Agent's response
        feedback_score: User feedback (0-1 scale)
        timestamp: When interaction occurred
        metadata: Additional metadata
    """
    query: str
    response: str
    feedback_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningFromFeedback(Agent):
    """
    Learning from feedback composition.

    Stores past interactions and retrieves similar ones to provide
    context for future queries. This is a simple composition (~80 LOC)
    showing basic experience-based learning.

    For production learning systems, use MemoryHierarchyAgent pattern
    which provides:
    - Multi-level memory (short-term, long-term, episodic)
    - Sophisticated retrieval (embeddings, reranking)
    - Memory consolidation
    - Adaptive weighting

    Attributes:
        name: Agent name (always "learning_feedback")
        agent: Base agent to wrap
        memory: List of stored interactions
        similarity_fn: Function to compute query similarity
        max_context_examples: Maximum examples to include as context
    """

    def __init__(
        self,
        agent: Agent,
        similarity_fn: Optional[Callable[[str, str], float]] = None,
        max_context_examples: int = 3,
        min_similarity: float = 0.3
    ):
        """
        Initialize learning from feedback composition.

        Args:
            agent: Base agent to wrap with learning
            similarity_fn: Function to compute similarity between queries.
                Takes two strings, returns similarity score (0-1).
                If None, uses simple word overlap.
            max_context_examples: Maximum past examples to include as context.
                Default: 3
            min_similarity: Minimum similarity to include an example.
                Default: 0.3

        Example:
            >>> def my_similarity(query1: str, query2: str) -> float:
            ...     # Your similarity logic (cosine, embeddings, etc.)
            ...     return 0.5
            >>>
            >>> learner = LearningFromFeedback(
            ...     agent=my_agent,
            ...     similarity_fn=my_similarity,
            ...     max_context_examples=5
            ... )
        """
        self.agent = agent
        self.similarity_fn = similarity_fn or self._default_similarity
        self.max_context_examples = max_context_examples
        self.min_similarity = min_similarity

        # Memory storage
        self.memory: List[Interaction] = []

    @property
    def name(self) -> str:
        """Return agent name."""
        return "learning_feedback"

    def _default_similarity(self, query1: str, query2: str) -> float:
        """
        Default similarity function using word overlap.

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score (0-1)
        """
        # Simple word overlap (Jaccard similarity)
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def retrieve_similar_interactions(
        self,
        query: str,
        k: Optional[int] = None
    ) -> List[Tuple[Interaction, float]]:
        """
        Retrieve similar past interactions.

        Args:
            query: Query to find similar interactions for
            k: Number of interactions to retrieve (default: max_context_examples)

        Returns:
            List of (interaction, similarity_score) tuples, sorted by similarity
        """
        if k is None:
            k = self.max_context_examples

        # Compute similarities
        similarities = []
        for interaction in self.memory:
            similarity = self.similarity_fn(query, interaction.query)

            if similarity >= self.min_similarity:
                similarities.append((interaction, similarity))

        # Sort by similarity (descending) and feedback score (if available)
        similarities.sort(
            key=lambda x: (x[1], x[0].feedback_score or 0.0),
            reverse=True
        )

        return similarities[:k]

    def add_feedback(
        self,
        response: Message,
        score: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add feedback for a past interaction.

        Args:
            response: Response message from previous interaction
            score: Feedback score (0-1 scale, higher = better)
            metadata: Optional additional metadata

        Example:
            >>> response = await learner.process(message)
            >>> learner.add_feedback(response, score=0.9)
        """
        # Extract original query from metadata
        query = response.metadata.get("original_query", "")

        # Create interaction
        interaction = Interaction(
            query=query,
            response=response.content,
            feedback_score=score,
            metadata=metadata or {}
        )

        self.memory.append(interaction)

    def _build_context_from_examples(
        self,
        examples: List[Tuple[Interaction, float]]
    ) -> str:
        """
        Build context string from retrieved examples.

        Args:
            examples: List of (interaction, similarity) tuples

        Returns:
            Formatted context string
        """
        if not examples:
            return ""

        context = "Here are similar past interactions for reference:\n\n"

        for i, (interaction, similarity) in enumerate(examples, 1):
            feedback_note = ""
            if interaction.feedback_score is not None:
                feedback_note = f" (feedback: {interaction.feedback_score:.1f}/1.0)"

            context += f"Example {i} (similarity: {similarity:.2f}{feedback_note}):\n"
            context += f"Query: {interaction.query}\n"
            context += f"Response: {interaction.response}\n\n"

        return context

    async def process(self, message: Message) -> Message:
        """
        Process message with learning from feedback.

        Retrieves similar past interactions and includes them as context.

        Args:
            message: Input message

        Returns:
            Message from agent. Metadata includes:
                - technique: Always "learning_feedback"
                - similar_examples: Number of examples used
                - examples_used: List of similar interactions
                - original_query: Original query for feedback tracking

        Example:
            >>> response = await learner.process(Message(
            ...     role="user",
            ...     content="How do I reverse a string?"
            ... ))
            >>> print(f"Used {response.metadata['similar_examples']} examples")
            >>> learner.add_feedback(response, score=0.85)
        """
        query = message.content

        # Retrieve similar past interactions
        similar = self.retrieve_similar_interactions(query)

        # Build context from examples
        context = self._build_context_from_examples(similar)

        # Enhance message with context
        if context:
            enhanced_content = f"{context}Current Query: {query}"
        else:
            enhanced_content = query

        enhanced_message = Message(
            role=message.role,
            content=enhanced_content,
            metadata=message.metadata
        )

        # Process with agent
        response = await self.agent.process(enhanced_message)

        # Build metadata
        metadata = {
            "technique": "learning_feedback",
            "similar_examples": len(similar),
            "examples_used": [
                {
                    "query": interaction.query,
                    "similarity": similarity,
                    "feedback_score": interaction.feedback_score
                }
                for interaction, similarity in similar
            ],
            "original_query": query,  # Store for feedback tracking
            "total_memory_size": len(self.memory)
        }

        if response.metadata:
            metadata.update(response.metadata)

        return Message(
            role=response.role,
            content=response.content,
            metadata=metadata
        )

    def clear_memory(self):
        """Clear all stored interactions."""
        self.memory.clear()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored memory.

        Returns:
            Dictionary with memory statistics
        """
        with_feedback = sum(1 for i in self.memory if i.feedback_score is not None)
        avg_feedback = (
            sum(i.feedback_score for i in self.memory if i.feedback_score is not None) / with_feedback
            if with_feedback > 0 else 0.0
        )

        return {
            "total_interactions": len(self.memory),
            "with_feedback": with_feedback,
            "average_feedback": avg_feedback
        }

    @property
    def capabilities(self) -> List[str]:
        """Return agent capabilities."""
        base_caps = self.agent.capabilities if hasattr(self.agent, 'capabilities') else []
        return base_caps + [
            "learning",
            "feedback",
            "memory",
            "experience_based"
        ]
