"""Basic MiniPydantic example with type-safe tools."""

import asyncio

from pydantic import BaseModel, Field

from minipydantic import TypeSafeAgent, tool


# ============================================================================
# Define Data Models
# ============================================================================


class SearchResult(BaseModel):
    """Search result with validation."""

    title: str = Field(description="Result title")
    snippet: str = Field(description="Result snippet")
    url: str = Field(pattern=r"^https?://")  # URL validation


class WeatherData(BaseModel):
    """Weather data with validation."""

    location: str
    temperature: float = Field(ge=-100, le=100)  # Reasonable temperature range
    condition: str
    humidity: int = Field(ge=0, le=100)  # Percentage validation


# ============================================================================
# Define Type-Safe Tools
# ============================================================================


@tool(description="Search the web for information")
def web_search(query: str, limit: int = 5) -> dict:
    """Search with validated inputs."""
    # Validate limit is reasonable
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be between 1 and 10")

    # Mock search results
    results = [
        SearchResult(
            title=f"Result {i} for '{query}'",
            snippet=f"This is result {i} about {query}",
            url=f"https://example.com/result{i}",
        )
        for i in range(1, min(limit + 1, 4))
    ]

    return {"query": query, "results": [r.model_dump() for r in results]}


@tool(description="Get weather for a location")
def get_weather(location: str) -> WeatherData:
    """Get weather with structured output."""
    # Return validated WeatherData
    return WeatherData(
        location=location,
        temperature=72.5,
        condition="Partly Cloudy",
        humidity=65,
    )


# ============================================================================
# Create Agent and Register Tools
# ============================================================================


async def main():
    """Run basic MiniPydantic example."""
    # Create type-safe agent
    agent = TypeSafeAgent(
        name="AssistantBot",
        system_prompt="You are a helpful assistant with search and weather tools.",
    )

    # Register tools
    agent.register_tool(web_search)
    agent.register_tool(get_weather)

    # Test 1: Search tool with validation
    print("=" * 60)
    print("Test 1: Web Search")
    print("=" * 60)

    response = await agent.run("Search for Python async patterns")
    print(f"Response: {response}\n")

    # Test 2: Weather tool with structured output
    print("=" * 60)
    print("Test 2: Weather Query")
    print("=" * 60)

    response = await agent.run("Get weather for San Francisco")
    print(f"Response: {response}\n")

    # Test 3: Direct tool execution with validation
    print("=" * 60)
    print("Test 3: Direct Tool Call (Type-Safe)")
    print("=" * 60)

    search_tool = agent.tools["web_search"]
    result = await search_tool.execute(query="AI agents", limit=3)

    print(f"Success: {result.success}")
    print(f"Data: {result.data}")
    print(f"Metadata: {result.metadata}\n")

    # Test 4: Validation error handling
    print("=" * 60)
    print("Test 4: Validation Error (Limit Too High)")
    print("=" * 60)

    result = await search_tool.execute(query="test", limit=100)  # Invalid
    print(f"Success: {result.success}")
    print(f"Error: {result.error}\n")

    # Test 5: Weather tool returns structured Pydantic model
    print("=" * 60)
    print("Test 5: Structured Weather Output")
    print("=" * 60)

    weather_tool = agent.tools["get_weather"]
    result = await weather_tool.execute(location="New York")

    if result.success:
        # Data is validated against WeatherData model
        weather = WeatherData(**result.data)
        print(f"Location: {weather.location}")
        print(f"Temperature: {weather.temperature}°F")
        print(f"Condition: {weather.condition}")
        print(f"Humidity: {weather.humidity}%")


if __name__ == "__main__":
    asyncio.run(main())
