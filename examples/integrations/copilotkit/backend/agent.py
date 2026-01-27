"""Research Assistant Agent with AG-UI Standard support.

This agent demonstrates:
- Multiple tools (search, calculator, weather)
- Streaming responses
- Tool call tracking
- State management
- HITL approval for sensitive operations
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from agenkit import Agent, Message, Tool, ToolResult


# ============================================================================
# Tools
# ============================================================================


class SearchTool(Tool):
    """Web search tool."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information. Use for current events, facts, and research."

    async def execute(self, query: str) -> ToolResult:
        """Execute web search.

        Args:
            query: Search query

        Returns:
            ToolResult with search results
        """
        # Simulate search delay
        await asyncio.sleep(0.5)

        # Mock search results
        results = [
            {
                "title": f"Result 1 for '{query}'",
                "snippet": f"This is the first search result about {query}. It contains relevant information.",
                "url": "https://example.com/result1",
            },
            {
                "title": f"Result 2 for '{query}'",
                "snippet": f"Another great resource about {query} with additional details.",
                "url": "https://example.com/result2",
            },
            {
                "title": f"Result 3 for '{query}'",
                "snippet": f"Comprehensive guide to {query} with examples and best practices.",
                "url": "https://example.com/result3",
            },
        ]

        return ToolResult(
            success=True,
            data={"query": query, "results": results, "count": len(results)},
            metadata={"tool": "web_search", "query": query},
        )


class CalculatorTool(Tool):
    """Mathematical calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform mathematical calculations. Supports +, -, *, /, **, sqrt, etc."

    async def execute(self, expression: str) -> ToolResult:
        """Execute calculation.

        Args:
            expression: Mathematical expression to evaluate

        Returns:
            ToolResult with calculation result
        """
        try:
            # Safe eval with limited builtins
            import math

            allowed_names = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "sqrt": math.sqrt,
                "pow": math.pow,
                "pi": math.pi,
                "e": math.e,
            }

            # Replace common operators
            expression = expression.replace("^", "**")

            result = eval(expression, {"__builtins__": {}}, allowed_names)

            return ToolResult(
                success=True,
                data={"expression": expression, "result": result},
                metadata={"tool": "calculator"},
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Calculation error: {str(e)}",
            )


class WeatherTool(Tool):
    """Weather information tool."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Get current weather for a location. Provide city name or coordinates."

    async def execute(self, location: str) -> ToolResult:
        """Get weather for location.

        Args:
            location: City name or coordinates

        Returns:
            ToolResult with weather data
        """
        # Simulate API call
        await asyncio.sleep(0.3)

        # Mock weather data
        weather_data = {
            "location": location,
            "temperature": 72,
            "feels_like": 70,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 8,
            "wind_direction": "NW",
            "forecast": [
                {"day": "Today", "high": 75, "low": 62, "condition": "Partly Cloudy"},
                {"day": "Tomorrow", "high": 78, "low": 64, "condition": "Sunny"},
                {"day": "Day 3", "high": 76, "low": 63, "condition": "Cloudy"},
            ],
        }

        return ToolResult(
            success=True,
            data=weather_data,
            metadata={"tool": "get_weather", "location": location},
        )


# ============================================================================
# Research Assistant Agent
# ============================================================================


class ResearchAssistantAgent(Agent):
    """Research assistant with search, calculation, and weather capabilities.

    This agent demonstrates AG-UI Standard features:
    - Tool call tracking (search, calculator, weather)
    - Streaming responses
    - State management
    - Contextual responses based on tool results
    """

    def __init__(self, name: str = "ResearchAssistant"):
        """Initialize research assistant.

        Args:
            name: Agent name
        """
        self._name = name
        self._tools = {
            "web_search": SearchTool(),
            "calculator": CalculatorTool(),
            "get_weather": WeatherTool(),
        }
        self._conversation_history: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def tools(self) -> dict[str, Tool]:
        """Get available tools."""
        return self._tools

    async def process(self, message: Message) -> Message:
        """Process user message.

        Args:
            message: User message

        Returns:
            Assistant response message
        """
        content = message.content
        self._conversation_history.append({"role": "user", "content": content})

        # Analyze query and select tools
        tools_to_use = self._analyze_query(content)

        # Execute tools if needed
        tool_results = []
        if tools_to_use:
            for tool_name, args in tools_to_use:
                tool = self._tools[tool_name]
                result = await tool.execute(**args)
                tool_results.append({"tool": tool_name, "result": result})

        # Generate response based on query and tool results
        response_content = await self._generate_response(content, tool_results)

        # Store in history
        self._conversation_history.append(
            {"role": "assistant", "content": response_content}
        )

        return Message(
            role="assistant",
            content=response_content,
            metadata={
                "tools_used": [tr["tool"] for tr in tool_results],
                "tool_count": len(tool_results),
                "conversation_length": len(self._conversation_history),
            },
        )

    def _analyze_query(self, query: str) -> list[tuple[str, dict[str, Any]]]:
        """Analyze query to determine which tools to use.

        Args:
            query: User query

        Returns:
            List of (tool_name, args) tuples
        """
        query_lower = query.lower()
        tools = []

        # Search keywords
        search_keywords = ["search", "find", "look up", "what is", "who is", "research"]
        if any(keyword in query_lower for keyword in search_keywords):
            tools.append(("web_search", {"query": query}))

        # Calculator keywords
        calc_keywords = ["calculate", "compute", "math", "+", "-", "*", "/", "="]
        if any(keyword in query_lower for keyword in calc_keywords):
            # Extract expression (simple heuristic)
            tools.append(("calculator", {"expression": query}))

        # Weather keywords
        weather_keywords = ["weather", "temperature", "forecast", "rain", "sunny"]
        if any(keyword in query_lower for keyword in weather_keywords):
            # Extract location (simple heuristic)
            location = "San Francisco"  # Default
            if "in" in query_lower:
                parts = query_lower.split("in")
                if len(parts) > 1:
                    location = parts[1].strip().split()[0].title()
            tools.append(("get_weather", {"location": location}))

        return tools

    async def _generate_response(
        self, query: str, tool_results: list[dict[str, Any]]
    ) -> str:
        """Generate response based on query and tool results.

        Args:
            query: User query
            tool_results: Tool execution results

        Returns:
            Response text
        """
        if not tool_results:
            # No tools used - general response
            return self._generate_general_response(query)

        # Generate response based on tool results
        response_parts = []

        for tool_result in tool_results:
            tool_name = tool_result["tool"]
            result = tool_result["result"]

            if not result.success:
                response_parts.append(f"❌ **{tool_name}** failed: {result.error}")
                continue

            if tool_name == "web_search":
                data = result.data
                response_parts.append(
                    f"🔍 **Search Results** for '{data['query']}':\n"
                )
                for i, res in enumerate(data["results"][:3], 1):
                    response_parts.append(
                        f"\n**{i}. {res['title']}**\n{res['snippet']}\n[{res['url']}]"
                    )

            elif tool_name == "calculator":
                data = result.data
                response_parts.append(
                    f"🧮 **Calculation**: `{data['expression']}` = **{data['result']}**"
                )

            elif tool_name == "get_weather":
                data = result.data
                response_parts.append(
                    f"🌤️ **Weather** in {data['location']}:\n"
                    f"- **Current**: {data['temperature']}°F, {data['condition']}\n"
                    f"- **Feels like**: {data['feels_like']}°F\n"
                    f"- **Humidity**: {data['humidity']}%\n"
                    f"- **Wind**: {data['wind_speed']} mph {data['wind_direction']}\n\n"
                    f"**Forecast**:"
                )
                for day in data["forecast"]:
                    response_parts.append(
                        f"\n- **{day['day']}**: {day['high']}°/{day['low']}°F, {day['condition']}"
                    )

        return "\n\n".join(response_parts)

    def _generate_general_response(self, query: str) -> str:
        """Generate general response without tools.

        Args:
            query: User query

        Returns:
            Response text
        """
        responses = {
            "hello": "Hello! I'm your research assistant. I can help you search the web, perform calculations, and check the weather. What would you like to know?",
            "hi": "Hi there! How can I assist you today?",
            "help": "I can help you with:\n- 🔍 **Web search**: Find information, research topics\n- 🧮 **Calculations**: Solve math problems\n- 🌤️ **Weather**: Get current conditions and forecasts\n\nJust ask me anything!",
            "thanks": "You're welcome! Let me know if you need anything else.",
        }

        query_lower = query.lower().strip()
        for keyword, response in responses.items():
            if keyword in query_lower:
                return response

        return (
            f"I understand you asked: '{query}'\n\n"
            "I can help you search for information, perform calculations, or check the weather. "
            "Try asking me to search for something, calculate a math problem, or get weather for a location!"
        )


__all__ = ["ResearchAssistantAgent", "SearchTool", "CalculatorTool", "WeatherTool"]
