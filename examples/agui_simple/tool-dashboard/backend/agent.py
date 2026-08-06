"""
Research Agent with Tool Visualization

An agent that demonstrates real-time tool execution monitoring through AG-UI.
Uses multiple tools (search, calculator, weather, database) to showcase
tool call streaming and performance metrics.
"""

import asyncio
import random
from datetime import datetime

from agenkit import Agent, Message, Tool


class SearchTool(Tool):
    """Mock web search tool with realistic latency."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information on any topic"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, num_results: int = 5) -> dict:
        """Execute web search with simulated latency."""
        # Simulate network latency
        await asyncio.sleep(random.uniform(0.8, 1.5))

        results = [
            {
                "title": f"Result {i + 1} for '{query}'",
                "url": f"https://example.com/result{i + 1}",
                "snippet": f"This is a relevant snippet about {query}...",
            }
            for i in range(num_results)
        ]

        return {
            "query": query,
            "results_count": num_results,
            "results": results,
            "search_time_ms": random.randint(100, 500),
        }


class CalculatorTool(Tool):
    """Calculator tool for mathematical operations."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform mathematical calculations"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide", "power"],
                },
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand"},
            },
            "required": ["operation", "a", "b"],
        }

    async def execute(self, operation: str, a: float, b: float) -> dict:
        """Execute calculation."""
        # Simulate computation time
        await asyncio.sleep(random.uniform(0.1, 0.3))

        operations = {
            "add": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else "Error: Division by zero",
            "power": a**b,
        }

        result = operations.get(operation, "Unknown operation")

        return {
            "operation": operation,
            "operands": {"a": a, "b": b},
            "result": result,
            "computed_at": datetime.utcnow().isoformat(),
        }


class WeatherTool(Tool):
    """Mock weather information tool."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Get current weather information for a location"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or coordinates"},
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                },
            },
            "required": ["location"],
        }

    async def execute(self, location: str, units: str = "celsius") -> dict:
        """Get weather information."""
        # Simulate API call latency
        await asyncio.sleep(random.uniform(0.5, 1.0))

        temp_c = random.uniform(15, 30)
        temp_f = (temp_c * 9 / 5) + 32

        return {
            "location": location,
            "temperature": temp_c if units == "celsius" else temp_f,
            "units": units,
            "conditions": random.choice(["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]),
            "humidity": random.randint(40, 80),
            "wind_speed": random.randint(5, 25),
            "timestamp": datetime.utcnow().isoformat(),
        }


class DatabaseTool(Tool):
    """Mock database query tool."""

    @property
    def name(self) -> str:
        return "query_database"

    @property
    def description(self) -> str:
        return "Query the database for information"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Table name"},
                "filters": {
                    "type": "object",
                    "description": "Query filters",
                    "default": {},
                },
                "limit": {"type": "integer", "description": "Result limit", "default": 10},
            },
            "required": ["table"],
        }

    async def execute(self, table: str, filters: dict | None = None, limit: int = 10) -> dict:
        """Execute database query."""
        filters = filters or {}

        # Simulate query execution time
        await asyncio.sleep(random.uniform(0.2, 0.7))

        # Mock results
        rows = [
            {
                "id": i,
                "data": f"Record {i} from {table}",
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(min(limit, random.randint(1, 10)))
        ]

        return {
            "table": table,
            "filters": filters,
            "rows_returned": len(rows),
            "rows": rows,
            "query_time_ms": random.randint(50, 300),
        }


class ResearchAgent(Agent):
    """
    Research agent that uses multiple tools to answer user questions.

    Demonstrates real-time tool execution monitoring through AG-UI protocol.
    Each tool call is streamed with timing and result information.
    """

    def __init__(self, name: str = "ResearchAgent"):
        self._name = name
        self._tools = {
            "web_search": SearchTool(),
            "calculator": CalculatorTool(),
            "get_weather": WeatherTool(),
            "query_database": DatabaseTool(),
        }
        self._request_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["research", "calculation", "weather", "database", "tool_execution"]

    async def process(self, message: Message) -> Message:
        """
        Process user message and execute appropriate tools.

        Args:
            message: User message with query

        Returns:
            Message with results from tool execution
        """
        self._request_count += 1
        content = str(message.content).lower().strip()

        # Determine which tools to use based on content
        tools_to_execute = self._select_tools(content)

        # Execute tools and collect results
        results = []
        for tool_name, params in tools_to_execute:
            tool = self._tools[tool_name]
            start_time = datetime.utcnow()

            try:
                result = await tool.execute(**params)
                execution_time = (datetime.utcnow() - start_time).total_seconds()

                results.append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "result": result,
                        "execution_time": execution_time,
                        "status": "success",
                    }
                )
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                results.append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "error": str(e),
                        "execution_time": execution_time,
                        "status": "error",
                    }
                )

        # Format response
        response_text = self._format_results(content, results)

        return Message(
            role="assistant",
            content=response_text,
            metadata={
                "request_count": self._request_count,
                "tools_used": [r["tool"] for r in results],
                "total_execution_time": sum(r["execution_time"] for r in results),
                "tool_results": results,
            },
        )

    def _select_tools(self, content: str) -> list[tuple[str, dict]]:
        """Select appropriate tools based on user query."""
        tools = []

        # Search queries
        if any(word in content for word in ["search", "find", "look up", "what is", "who is"]):
            query = content.replace("search", "").replace("find", "").strip()
            tools.append(("web_search", {"query": query or "general query", "num_results": 3}))

        # Math operations
        if any(word in content for word in ["calculate", "math", "+", "-", "*", "/", "compute"]):
            # Extract numbers if possible, otherwise use defaults
            tools.append(("calculator", {"operation": "multiply", "a": 12, "b": 15}))

        # Weather queries
        if any(word in content for word in ["weather", "temperature", "forecast"]):
            # Extract location or use default
            location = "San Francisco"
            if "in" in content:
                location = content.split("in")[-1].strip()
            tools.append(("get_weather", {"location": location, "units": "celsius"}))

        # Database queries
        if any(word in content for word in ["database", "query", "records", "data"]):
            tools.append(("query_database", {"table": "users", "limit": 5}))

        # Default: use search if no specific tool matched
        if not tools:
            tools.append(("web_search", {"query": content, "num_results": 3}))

        return tools

    def _format_results(self, query: str, results: list[dict]) -> str:
        """Format tool execution results into readable response."""
        response_parts = [f'# Results for: "{query}"\n']

        for result in results:
            tool = result["tool"]
            status = result["status"]
            exec_time = result["execution_time"]

            response_parts.append(f"\n## Tool: {tool} ({status})")
            response_parts.append(f"**Execution Time**: {exec_time:.2f}s\n")

            if status == "success":
                result_data = result["result"]
                response_parts.append("**Result**:")

                if tool == "web_search":
                    response_parts.append(
                        f"- Found {result_data['results_count']} results "
                        f"in {result_data['search_time_ms']}ms"
                    )
                    for r in result_data["results"][:2]:
                        response_parts.append(f"  - {r['title']}")

                elif tool == "calculator":
                    response_parts.append(
                        f"- {result_data['operation'].title()}: "
                        f"{result_data['operands']['a']} and {result_data['operands']['b']} "
                        f"= {result_data['result']}"
                    )

                elif tool == "get_weather":
                    response_parts.append(
                        f"- Location: {result_data['location']}\n"
                        f"- Temperature: {result_data['temperature']:.1f}° {result_data['units']}\n"
                        f"- Conditions: {result_data['conditions']}\n"
                        f"- Humidity: {result_data['humidity']}%"
                    )

                elif tool == "query_database":
                    response_parts.append(
                        f"- Table: {result_data['table']}\n"
                        f"- Rows returned: {result_data['rows_returned']}\n"
                        f"- Query time: {result_data['query_time_ms']}ms"
                    )
            else:
                response_parts.append(f"**Error**: {result['error']}")

        response_parts.append(
            f"\n---\n**Total Execution Time**: {sum(r['execution_time'] for r in results):.2f}s"
        )

        return "\n".join(response_parts)
