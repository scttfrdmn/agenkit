"""
Example 5: Tool Usage

This example shows how to create and use tools with agents.
"""

import asyncio
from typing import Any
from agenkit import Agent, Message, Tool, ToolResult


class SearchTool(Tool):
    """Simulates a web search tool."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web for information"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }

    async def execute(self, query: str, limit: int = 5) -> ToolResult:
        """Execute search (simulated)."""
        # In reality, this would call a search API
        results = [
            f"Result {i+1} for '{query}'"
            for i in range(limit)
        ]

        return ToolResult(
            success=True,
            data={"query": query, "results": results, "count": len(results)}
        )


class CalculatorTool(Tool):
    """Simple calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform basic arithmetic operations"

    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        """Execute calculation."""
        try:
            operations = {
                "add": lambda x, y: x + y,
                "subtract": lambda x, y: x - y,
                "multiply": lambda x, y: x * y,
                "divide": lambda x, y: x / y if y != 0 else None
            }

            if operation not in operations:
                return ToolResult(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )

            result = operations[operation](a, b)

            if result is None:
                return ToolResult(
                    success=False,
                    error="Division by zero"
                )

            return ToolResult(
                success=True,
                data={"operation": operation, "result": result}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ToolUsingAgent(Agent):
    """Agent that uses tools to accomplish tasks."""

    def __init__(self):
        self.search_tool = SearchTool()
        self.calc_tool = CalculatorTool()

    @property
    def name(self) -> str:
        return "tool_agent"

    @property
    def capabilities(self) -> list[str]:
        return ["search", "calculator", "tool_use"]

    async def process(self, message: Message) -> Message:
        """Process message using appropriate tool."""
        content = str(message.content).lower()

        # Route to appropriate tool
        if "search" in content:
            query = content.replace("search", "").strip()
            result = await self.search_tool.execute(query=query, limit=3)

            if result.success:
                response = f"Search results for '{query}':\n"
                for i, res in enumerate(result.data["results"], 1):
                    response += f"{i}. {res}\n"
            else:
                response = f"Search failed: {result.error}"

        elif any(op in content for op in ["add", "multiply", "subtract", "divide"]):
            # Parse simple commands like "add 5 and 3"
            words = content.split()
            try:
                operation = words[0]
                a = float(words[1])
                b = float(words[3])  # Skip "and"

                result = await self.calc_tool.execute(operation=operation, a=a, b=b)

                if result.success:
                    response = f"{a} {operation} {b} = {result.data['result']}"
                else:
                    response = f"Calculation failed: {result.error}"
            except (IndexError, ValueError):
                response = "Invalid calculation format. Use: 'add 5 and 3'"

        else:
            response = "I can search or calculate. Try:\n- 'search python'\n- 'add 5 and 3'"

        return Message(
            role="agent",
            content=response,
            metadata={"tools_used": self.capabilities}
        )


async def main():
    """Run the example."""
    agent = ToolUsingAgent()

    # Test search
    print("Test 1: Search")
    msg1 = Message(role="user", content="search agenkit")
    response1 = await agent.process(msg1)
    print(response1.content)
    print()

    # Test calculator
    print("Test 2: Calculator")
    msg2 = Message(role="user", content="multiply 7 and 6")
    response2 = await agent.process(msg2)
    print(response2.content)
    print()

    # Test error handling
    print("Test 3: Error Handling")
    msg3 = Message(role="user", content="divide 10 and 0")
    response3 = await agent.process(msg3)
    print(response3.content)


if __name__ == "__main__":
    asyncio.run(main())
