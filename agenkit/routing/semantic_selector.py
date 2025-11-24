"""
Semantic Tool Selection - Embedding-based Tool Routing

Uses embeddings to semantically match user queries to the most relevant tools,
inspired by AWS AgentCore Gateway's semantic routing capabilities.

Key features:
- Embedding-based similarity matching (not keyword matching)
- Support for multiple embedding providers (OpenAI, Anthropic, local models)
- Caching for performance
- Batch tool selection
- Confidence scores

Example:
    >>> selector = SemanticToolSelector(tools=[
    ...     ToolDescription(
    ...         name="web_search",
    ...         description="Search the web for current information",
    ...         examples=["find recent news", "search for X"]
    ...     ),
    ...     ToolDescription(
    ...         name="calculator",
    ...         description="Perform mathematical calculations",
    ...         examples=["calculate 2+2", "what is 15% of 200"]
    ...     ),
    ... ])
    >>>
    >>> # Semantic matching - no keywords needed!
    >>> matches = await selector.select("I need to find out what's happening today")
    >>> # Returns: [ToolMatch(name="web_search", confidence=0.92, ...)]
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolDescription:
    """Description of a tool for semantic matching."""

    name: str
    description: str
    parameters: dict[str, Any] | None = None
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str | None = None

    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [
            f"Tool: {self.name}",
            f"Description: {self.description}",
        ]

        if self.category:
            parts.append(f"Category: {self.category}")

        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags)}")

        if self.examples:
            parts.append("Examples:")
            for ex in self.examples:
                parts.append(f"  - {ex}")

        return "\n".join(parts)


@dataclass
class ToolMatch:
    """A matched tool with confidence score."""

    name: str
    confidence: float  # 0.0 to 1.0
    description: str
    reasoning: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        ...


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small"):
        """Initialize OpenAI embeddings.

        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
            model: Embedding model to use
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "OpenAI embeddings require the 'openai' package. "
                "Install it with: pip install openai"
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        response = await self.client.embeddings.create(
            input=[text],
            model=self.model,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
        )
        return [item.embedding for item in response.data]


class VoyageEmbeddingProvider:
    """Voyage AI embedding provider."""

    def __init__(self, api_key: str | None = None, model: str = "voyage-3"):
        """Initialize Voyage embeddings.

        Args:
            api_key: Voyage API key (uses VOYAGE_API_KEY env var if not provided)
            model: Embedding model to use
        """
        try:
            import voyageai
        except ImportError:
            raise ImportError(
                "Voyage embeddings require the 'voyageai' package. "
                "Install it with: pip install voyageai"
            )

        self.client = voyageai.AsyncClient(api_key=api_key)
        self.model = model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        result = await self.client.embed([text], model=self.model)
        return result.embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        result = await self.client.embed(texts, model=self.model)
        return result.embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Similarity score (0.0 to 1.0)
    """
    import math

    if len(a) != len(b):
        raise ValueError("Vectors must have same length")

    dot_product = sum(x * y for x, y in zip(a, b, strict=False))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    similarity = dot_product / (magnitude_a * magnitude_b)
    # Normalize to 0-1 range (cosine similarity is -1 to 1)
    return (similarity + 1.0) / 2.0


class SemanticToolSelector:
    """
    Semantic tool selector using embeddings.

    Matches user queries to tools based on semantic similarity rather than
    keyword matching. This enables more natural and flexible tool selection.

    Example:
        >>> # Create selector with tools
        >>> selector = SemanticToolSelector(
        ...     tools=[
        ...         ToolDescription(
        ...             name="weather",
        ...             description="Get weather information for any location",
        ...             examples=["What's the weather?", "Is it raining?"]
        ...         ),
        ...         ToolDescription(
        ...             name="calculator",
        ...             description="Perform mathematical calculations",
        ...             examples=["Calculate 5 + 3", "What's 20% of 100?"]
        ...         ),
        ...     ],
        ...     provider=OpenAIEmbeddingProvider()
        ... )
        >>>
        >>> # Select tools for a query
        >>> matches = await selector.select(
        ...     "I need to know if I should bring an umbrella today",
        ...     top_k=1
        ... )
        >>> print(matches[0].name)  # "weather"
        >>> print(matches[0].confidence)  # 0.87
    """

    def __init__(
        self,
        tools: list[ToolDescription],
        provider: EmbeddingProvider,
        cache_embeddings: bool = True,
        min_confidence: float = 0.3,
    ):
        """Initialize semantic tool selector.

        Args:
            tools: List of tool descriptions
            provider: Embedding provider (OpenAI, Voyage, etc.)
            cache_embeddings: Whether to cache tool embeddings
            min_confidence: Minimum confidence threshold for matches
        """
        self.tools = tools
        self.provider = provider
        self.cache_embeddings = cache_embeddings
        self.min_confidence = min_confidence

        self._tool_embeddings: dict[str, list[float]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Pre-compute and cache tool embeddings."""
        if self._initialized:
            return

        # Generate embeddings for all tools
        tool_texts = [tool.to_text() for tool in self.tools]
        embeddings = await self.provider.embed_batch(tool_texts)

        # Cache embeddings
        for tool, embedding in zip(self.tools, embeddings, strict=False):
            self._tool_embeddings[tool.name] = embedding

        self._initialized = True

    async def select(
        self,
        query: str,
        top_k: int = 3,
        include_reasoning: bool = False,
    ) -> list[ToolMatch]:
        """Select most relevant tools for a query.

        Args:
            query: User query
            top_k: Number of tools to return
            include_reasoning: Whether to include reasoning for matches

        Returns:
            List of tool matches sorted by confidence (highest first)
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()

        # Generate query embedding
        query_embedding = await self.provider.embed(query)

        # Calculate similarities
        similarities = []
        for tool in self.tools:
            tool_embedding = self._tool_embeddings[tool.name]
            similarity = cosine_similarity(query_embedding, tool_embedding)

            if similarity >= self.min_confidence:
                reasoning = None
                if include_reasoning:
                    reasoning = self._generate_reasoning(query, tool, similarity)

                similarities.append(
                    ToolMatch(
                        name=tool.name,
                        confidence=similarity,
                        description=tool.description,
                        reasoning=reasoning,
                        metadata={
                            "category": tool.category,
                            "tags": tool.tags,
                        },
                    )
                )

        # Sort by confidence and return top_k
        similarities.sort(key=lambda x: x.confidence, reverse=True)
        return similarities[:top_k]

    async def select_batch(
        self,
        queries: list[str],
        top_k: int = 3,
    ) -> list[list[ToolMatch]]:
        """Select tools for multiple queries efficiently.

        Args:
            queries: List of user queries
            top_k: Number of tools to return per query

        Returns:
            List of tool matches for each query
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()

        # Generate embeddings for all queries
        query_embeddings = await self.provider.embed_batch(queries)

        # Calculate similarities for each query
        results = []
        for query_embedding in query_embeddings:
            similarities = []
            for tool in self.tools:
                tool_embedding = self._tool_embeddings[tool.name]
                similarity = cosine_similarity(query_embedding, tool_embedding)

                if similarity >= self.min_confidence:
                    similarities.append(
                        ToolMatch(
                            name=tool.name,
                            confidence=similarity,
                            description=tool.description,
                            metadata={
                                "category": tool.category,
                                "tags": tool.tags,
                            },
                        )
                    )

            # Sort and take top_k
            similarities.sort(key=lambda x: x.confidence, reverse=True)
            results.append(similarities[:top_k])

        return results

    def _generate_reasoning(self, query: str, tool: ToolDescription, similarity: float) -> str:
        """Generate human-readable reasoning for why a tool was selected.

        Args:
            query: User query
            tool: Selected tool
            similarity: Similarity score

        Returns:
            Reasoning string
        """
        confidence_level = "high" if similarity > 0.7 else "moderate" if similarity > 0.5 else "low"

        reasoning = (
            f"Selected '{tool.name}' with {confidence_level} confidence ({similarity:.2f}). "
        )

        # Add category if available
        if tool.category:
            reasoning += f"This is a {tool.category} tool. "

        # Find most similar example if available
        if tool.examples:
            reasoning += f"Similar to: '{tool.examples[0]}'"

        return reasoning

    def get_tool(self, name: str) -> ToolDescription | None:
        """Get tool description by name.

        Args:
            name: Tool name

        Returns:
            Tool description or None if not found
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def add_tool(self, tool: ToolDescription) -> None:
        """Add a tool to the selector.

        Args:
            tool: Tool to add

        Note:
            This will invalidate the cache and require re-initialization.
        """
        self.tools.append(tool)
        self._initialized = False

    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the selector.

        Args:
            name: Tool name

        Returns:
            True if tool was removed, False if not found
        """
        for i, tool in enumerate(self.tools):
            if tool.name == name:
                self.tools.pop(i)
                if name in self._tool_embeddings:
                    del self._tool_embeddings[name]
                return True
        return False

    def get_statistics(self) -> dict[str, Any]:
        """Get selector statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_tools": len(self.tools),
            "initialized": self._initialized,
            "cached_embeddings": len(self._tool_embeddings),
            "min_confidence": self.min_confidence,
            "categories": list({t.category for t in self.tools if t.category}),
        }
