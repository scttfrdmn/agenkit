"""Tests for semantic tool selector."""

import pytest

from agenkit.routing.semantic_selector import (SemanticToolSelector,
                                               ToolDescription, ToolMatch,
                                               cosine_similarity)


# Mock embedding provider for testing
class MockEmbeddingProvider:
    """Mock embedding provider that returns predictable embeddings."""

    async def embed(self, text: str) -> list[float]:
        """Generate mock embedding based on text content."""
        # Simple mock: use word count as vector
        words = text.lower().split()

        # Create vector based on keywords
        vector = [0.0] * 10
        if "weather" in words or "temperature" in words or "forecast" in words:
            vector[0] = 1.0
        if "calculate" in words or "math" in words or "number" in words:
            vector[1] = 1.0
        if "search" in words or "find" in words or "web" in words:
            vector[2] = 1.0
        if "database" in words or "sql" in words or "query" in words:
            vector[3] = 1.0
        if "email" in words or "send" in words or "message" in words:
            vector[4] = 1.0

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate mock embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    return [
        ToolDescription(
            name="weather",
            description="Get weather information for any location",
            category="information",
            examples=["What's the weather?", "Is it raining?", "Check temperature"],
            tags=["weather", "forecast", "temperature"],
        ),
        ToolDescription(
            name="calculator",
            description="Perform mathematical calculations",
            category="computation",
            examples=["Calculate 5 + 3", "What's 20% of 100?"],
            tags=["math", "calculate", "numbers"],
        ),
        ToolDescription(
            name="web_search",
            description="Search the web for current information",
            category="information",
            examples=["Search for Python tutorials", "Find news about AI"],
            tags=["search", "web", "find"],
        ),
        ToolDescription(
            name="database_query",
            description="Query the database for stored information",
            category="data",
            examples=["Find user records", "Get order history"],
            tags=["database", "sql", "query"],
        ),
    ]


@pytest.fixture
def mock_provider():
    """Create mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.mark.asyncio
async def test_selector_initialization(sample_tools, mock_provider):
    """Test selector initialization."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
        cache_embeddings=True,
        min_confidence=0.3,
    )

    assert not selector._initialized
    assert len(selector.tools) == 4
    assert selector.min_confidence == 0.3

    # Initialize
    await selector.initialize()

    assert selector._initialized
    assert len(selector._tool_embeddings) == 4


@pytest.mark.asyncio
async def test_select_weather_tool(sample_tools, mock_provider):
    """Test selecting weather tool."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
        min_confidence=0.3,
    )

    matches = await selector.select("What's the weather like today?", top_k=1)

    assert len(matches) == 1
    assert matches[0].name == "weather"
    assert matches[0].confidence > 0.5


@pytest.mark.asyncio
async def test_select_calculator_tool(sample_tools, mock_provider):
    """Test selecting calculator tool."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
        min_confidence=0.3,
    )

    matches = await selector.select("Calculate 15 * 23", top_k=1)

    assert len(matches) == 1
    assert matches[0].name == "calculator"


@pytest.mark.asyncio
async def test_select_multiple_tools(sample_tools, mock_provider):
    """Test selecting multiple relevant tools."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
        min_confidence=0.3,
    )

    matches = await selector.select("I need information", top_k=3)

    # Should return tools sorted by confidence
    assert len(matches) <= 3
    assert all(isinstance(m, ToolMatch) for m in matches)

    # Check confidence is descending
    for i in range(len(matches) - 1):
        assert matches[i].confidence >= matches[i + 1].confidence


@pytest.mark.asyncio
async def test_select_with_reasoning(sample_tools, mock_provider):
    """Test including reasoning in results."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
    )

    matches = await selector.select(
        "What's the temperature?",
        top_k=1,
        include_reasoning=True,
    )

    assert len(matches) >= 1
    assert matches[0].reasoning is not None
    assert isinstance(matches[0].reasoning, str)
    assert len(matches[0].reasoning) > 0


@pytest.mark.asyncio
async def test_select_batch(sample_tools, mock_provider):
    """Test batch selection."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
    )

    queries = [
        "What's the weather?",
        "Calculate 2+2",
        "Search for tutorials",
    ]

    results = await selector.select_batch(queries, top_k=1)

    assert len(results) == 3
    assert all(len(matches) >= 1 for matches in results)


@pytest.mark.asyncio
async def test_min_confidence_threshold(sample_tools, mock_provider):
    """Test minimum confidence threshold filtering."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
        min_confidence=0.9,  # Very high threshold
    )

    matches = await selector.select("Random unrelated query xyz", top_k=5)

    # Should return no matches if nothing exceeds threshold
    assert len(matches) == 0 or all(m.confidence >= 0.9 for m in matches)


@pytest.mark.asyncio
async def test_add_tool(sample_tools, mock_provider):
    """Test adding a tool dynamically."""
    selector = SemanticToolSelector(
        tools=sample_tools[:2],  # Start with 2 tools
        provider=mock_provider,
    )

    await selector.initialize()
    assert len(selector.tools) == 2

    # Add new tool
    new_tool = ToolDescription(
        name="translator",
        description="Translate text between languages",
    )
    selector.add_tool(new_tool)

    assert len(selector.tools) == 3
    assert not selector._initialized  # Should require re-initialization


@pytest.mark.asyncio
async def test_remove_tool(sample_tools, mock_provider):
    """Test removing a tool."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
    )

    await selector.initialize()

    removed = selector.remove_tool("calculator")

    assert removed is True
    assert len(selector.tools) == 3
    assert selector.get_tool("calculator") is None


@pytest.mark.asyncio
async def test_get_tool(sample_tools, mock_provider):
    """Test getting tool by name."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
    )

    tool = selector.get_tool("weather")

    assert tool is not None
    assert tool.name == "weather"
    assert tool.description == "Get weather information for any location"


@pytest.mark.asyncio
async def test_get_statistics(sample_tools, mock_provider):
    """Test getting selector statistics."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
    )

    stats = selector.get_statistics()

    assert stats["total_tools"] == 4
    assert stats["initialized"] is False
    assert stats["cached_embeddings"] == 0
    assert "information" in stats["categories"]
    assert "computation" in stats["categories"]


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    # Identical vectors
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0

    # Opposite vectors
    similarity = cosine_similarity([1.0, 0.0], [-1.0, 0.0])
    assert 0.0 <= similarity <= 0.1  # Should be close to 0 (normalized range)

    # Orthogonal vectors
    similarity = cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert 0.4 < similarity < 0.6  # Should be around 0.5 (normalized)

    # Zero vector
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cosine_similarity_different_lengths():
    """Test that cosine similarity fails with different vector lengths."""
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


@pytest.mark.asyncio
async def test_tool_to_text(sample_tools):
    """Test tool description to text conversion."""
    tool = sample_tools[0]  # weather tool
    text = tool.to_text()

    assert "Tool: weather" in text
    assert "Description: Get weather information" in text
    assert "Category: information" in text
    assert "Tags: weather, forecast, temperature" in text
    assert "Examples:" in text
    assert "What's the weather?" in text


@pytest.mark.asyncio
async def test_metadata_in_matches(sample_tools, mock_provider):
    """Test that matches include metadata."""
    selector = SemanticToolSelector(
        tools=sample_tools,
        provider=mock_provider,
    )

    matches = await selector.select("What's the weather?", top_k=1)

    assert len(matches) >= 1
    match = matches[0]
    assert "category" in match.metadata
    assert "tags" in match.metadata
