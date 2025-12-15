"""
Example 4: Router Pattern

This example shows how to route messages to different agents based on content.
"""

import asyncio

from agenkit import Agent, Message, RouterPattern


class WeatherAgent(Agent):
    """Handles weather queries."""

    @property
    def name(self) -> str:
        return "weather"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="🌤️ The weather is sunny and 72°F")


class NewsAgent(Agent):
    """Handles news queries."""

    @property
    def name(self) -> str:
        return "news"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content="📰 Breaking: Python 4.0 released!")


class CalculatorAgent(Agent):
    """Handles math queries."""

    @property
    def name(self) -> str:
        return "calculator"

    async def process(self, message: Message) -> Message:
        # Safe calculator using ast module (no arbitrary code execution)
        import ast
        import operator

        # Safe operations mapping
        safe_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def safe_eval(node):
            """Safely evaluate a math expression AST node."""
            if isinstance(node, ast.Constant):  # Python 3.8+
                return node.value
            elif isinstance(node, ast.BinOp):
                left = safe_eval(node.left)
                right = safe_eval(node.right)
                op = safe_ops.get(type(node.op))
                if op is None:
                    raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
                return op(left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = safe_eval(node.operand)
                op = safe_ops.get(type(node.op))
                if op is None:
                    raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
                return op(operand)
            else:
                raise ValueError(f"Unsupported expression: {type(node).__name__}")

        try:
            # Parse and evaluate safely
            expr = str(message.content).strip()
            tree = ast.parse(expr, mode="eval")
            result = safe_eval(tree.body)
            return Message(role="agent", content=f"🔢 Result: {result}")
        except (SyntaxError, ValueError, ZeroDivisionError, TypeError) as e:
            return Message(role="agent", content=f"❌ Invalid calculation: {e}")


class GeneralAgent(Agent):
    """Handles general queries."""

    @property
    def name(self) -> str:
        return "general"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"💭 You said: {message.content}")


def route_by_intent(message: Message) -> str:
    """Determine which agent should handle the message."""
    content = str(message.content).lower()

    # Check for weather keywords
    if any(word in content for word in ["weather", "temperature", "forecast", "rain"]):
        return "weather"

    # Check for news keywords
    if any(word in content for word in ["news", "headlines", "latest", "breaking"]):
        return "news"

    # Check for math keywords or operators
    if any(char in content for char in ["+", "-", "*", "/", "="]) or "calculate" in content:
        return "calculator"

    # Default to general
    return "general"


async def main():
    """Run the example."""
    # Create router
    router = RouterPattern(
        router=route_by_intent,
        handlers={
            "weather": WeatherAgent(),
            "news": NewsAgent(),
            "calculator": CalculatorAgent(),
            "general": GeneralAgent(),
        },
    )

    # Test different queries
    queries = [
        "What's the weather like?",
        "Show me the latest news",
        "Calculate 15 * 3",
        "Hello, how are you?",
    ]

    for query in queries:
        msg = Message(role="user", content=query)
        response = await router.process(msg)

        print(f"Query: {query}")
        print(f"Response: {response.content}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
