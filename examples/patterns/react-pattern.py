"""
ReAct Agent Example

Demonstrates how to use ReActAgent (Reasoning + Acting) to build agents
that can use tools to accomplish tasks.

The ReAct pattern enables agents to:
- Reason about which tools to use
- Execute tools with appropriate parameters
- Observe results and adjust strategy
- Provide final answers based on tool outputs

This example uses mock implementations for demonstration. In production,
replace with real LLM agents and tools.
"""

import asyncio
from datetime import datetime

from agenkit import Message
from agenkit.patterns import ReActAgent

# ============================================================================
# Mock Tools for Demonstration
# ============================================================================


class Calculator:
    """
    Mock calculator tool for mathematical operations.

    In production, this could be replaced with a real calculator,
    Python eval (with proper sandboxing), or a math API.
    """

    name = "calculator"
    description = (
        "Performs mathematical calculations. Input should be a mathematical expression as a string."
    )

    async def execute(self, input: str) -> str:
        """Execute a calculation using safe AST evaluation."""
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
            if isinstance(node, ast.Constant):
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
            expr = str(input).strip()
            tree = ast.parse(expr, mode="eval")
            result = safe_eval(tree.body)
            return str(result)
        except (SyntaxError, ValueError, ZeroDivisionError, TypeError) as e:
            raise ValueError(f"Invalid expression: {e}")


class WebSearch:
    """
    Mock web search tool.

    In production, replace with real search API (Google, Bing, DuckDuckGo, etc.)
    """

    name = "search"
    description = "Searches the web for information. Input should be a search query string."

    def __init__(self):
        # Mock search results database
        self.mock_results = {
            "python": "Python is a high-level programming language created by Guido van Rossum in 1991.",
            "weather": "The weather is currently sunny with a temperature of 72°F.",
            "eiffel tower": "The Eiffel Tower is a wrought-iron lattice tower in Paris, France. It was completed in 1889 and stands 330 meters tall.",
            "population of france": "The population of France is approximately 67 million people as of 2023.",
        }

    async def execute(self, input: str) -> str:
        """Perform a search."""
        query = input.lower()

        # Find matching mock result
        for key, value in self.mock_results.items():
            if key in query:
                return value

        return f"No results found for '{input}'. (This is a mock search tool)"


class DateTimeTool:
    """
    Tool for getting current date and time information.
    """

    name = "datetime"
    description = "Gets the current date and time. No input required."

    async def execute(self, **kwargs) -> str:
        """Get current datetime."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# Mock Agent
# ============================================================================


class MockReActAgent:
    """
    Mock Agent that simulates ReAct-style reasoning.

    In production, replace with real LLM-based agent:
    - OpenAI: from openai import AsyncOpenAI
    - Anthropic: from anthropic import AsyncAnthropic
    - LiteLLM: from litellm import acompletion
    """

    def __init__(self):
        self.call_count = 0
        self.name = "MockReActAgent"

    async def process(self, message: Message) -> Message:
        """Generate mock ReAct-style responses."""
        self.call_count += 1

        content = message.content.lower()

        # Check if this is an observation (tool result)
        if content.startswith("observation:"):
            # We have a tool result, decide on next action
            if "error" in content:
                return Message(
                    role="assistant",
                    content="Thought: The tool encountered an error\nAction: Final Answer\nAction Input: I encountered an error while processing your request.",
                )
            else:
                # Tool succeeded, provide final answer
                observation = content.replace("observation:", "").strip()
                return Message(
                    role="assistant",
                    content=f"Thought: I have the information I need\nAction: Final Answer\nAction Input: Based on the information, {observation}",
                )

        # Initial reasoning based on user query
        if "calculate" in content or "%" in content or "+" in content or "*" in content:
            # Extract math expression
            if "15% of 240" in content:
                return Message(
                    role="assistant",
                    content="Thought: I need to calculate 15% of 240\nAction: calculator\nAction Input: 240 * 0.15",
                )
            elif "what is" in content and ("+" in content or "*" in content):
                # Try to extract expression
                parts = content.split("what is")
                if len(parts) > 1:
                    expr = parts[1].strip().rstrip("?")
                    return Message(
                        role="assistant",
                        content=f"Thought: I need to calculate this expression\nAction: calculator\nAction Input: {expr}",
                    )

        elif "search" in content or "find" in content or "what is python" in content:
            # Extract search query
            if "python" in content:
                return Message(
                    role="assistant",
                    content="Thought: I should search for information about Python\nAction: search\nAction Input: python",
                )
            elif "eiffel tower" in content:
                return Message(
                    role="assistant",
                    content="Thought: I should search for information about the Eiffel Tower\nAction: search\nAction Input: eiffel tower",
                )

        elif "time" in content or "date" in content:
            return Message(
                role="assistant",
                content="Thought: I need to get the current date and time\nAction: datetime\nAction Input: {}",
            )

        # Default: provide a simple answer
        return Message(
            role="assistant",
            content="Thought: I can answer this directly\nAction: Final Answer\nAction Input: I understand your question, but I'm a demo agent with limited capabilities.",
        )


# ============================================================================
# Example Functions
# ============================================================================


async def basic_tool_usage_example():
    """Demonstrate basic tool usage with ReActAgent."""
    print("=" * 60)
    print("Example 1: Basic Tool Usage")
    print("=" * 60)

    # Setup tools
    tools = [Calculator(), WebSearch(), DateTimeTool()]

    # Create agent
    mock_agent = MockReActAgent()
    agent = ReActAgent(agent=mock_agent, tools=tools, max_steps=5)

    # Test calculation
    print("\nUser: What is 15% of 240?")
    response = await agent.process(Message(role="user", content="What is 15% of 240?"))
    print(f"Agent: {response.content}")

    # Show reasoning steps
    print(f"\nReasoning steps: {len(agent.get_steps())}")
    for step in agent.get_steps():
        print(f"  Step {step.step_number + 1}: {step.action} -> {step.observation}")


async def multiple_tools_example():
    """Demonstrate using multiple different tools."""
    print("\n" + "=" * 60)
    print("Example 2: Multiple Tools")
    print("=" * 60)

    tools = [Calculator(), WebSearch(), DateTimeTool()]

    mock_agent = MockReActAgent()
    agent = ReActAgent(agent=mock_agent, tools=tools, max_steps=5)

    queries = [
        "What is Python?",
        "What time is it?",
        "Tell me about the Eiffel Tower",
    ]

    for query in queries:
        print(f"\nUser: {query}")
        response = await agent.process(Message(role="user", content=query))
        print(f"Agent: {response.content}")


async def verbose_mode_example():
    """Demonstrate verbose mode that shows thought process."""
    print("\n" + "=" * 60)
    print("Example 3: Verbose Mode (Show Reasoning)")
    print("=" * 60)

    tools = [Calculator()]

    mock_agent = MockReActAgent()
    agent = ReActAgent(agent=mock_agent, tools=tools, max_steps=5, verbose=True)

    print("\nUser: Calculate 123 + 456")
    response = await agent.process(Message(role="user", content="Calculate 123 + 456"))
    print(f"Agent:\n{response.content}")


async def error_handling_example():
    """Demonstrate error handling when tools fail."""
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)

    tools = [Calculator()]

    mock_agent = MockReActAgent()
    agent = ReActAgent(agent=mock_agent, tools=tools, max_steps=3)

    # This will cause the calculator to error
    print("\nUser: Calculate invalid expression")
    response = await agent.process(Message(role="user", content="Calculate 2 + + 3"))
    print(f"Agent: {response.content}")

    # Check if any errors occurred in steps
    for step in agent.get_steps():
        if "error" in step.observation.lower():
            print(f"\n✗ Step {step.step_number + 1} had an error:")
            print(f"  Action: {step.action}")
            print(f"  Error: {step.observation}")


async def custom_system_prompt_example():
    """Demonstrate using a custom system prompt."""
    print("\n" + "=" * 60)
    print("Example 5: Custom System Prompt")
    print("=" * 60)

    tools = [Calculator()]

    custom_prompt = """You are a friendly math tutor that helps students learn.

Available tools:
- calculator: Performs mathematical calculations

When solving problems:
1. Explain your reasoning clearly
2. Show the calculation steps
3. Provide the final answer

Use this format:
Thought: [your reasoning]
Action: [tool name or "Final Answer"]
Action Input: [tool input or final answer]
"""

    mock_agent = MockReActAgent()
    agent = ReActAgent(
        agent=mock_agent,
        tools=tools,
        max_steps=5,
        system_prompt=custom_prompt,
    )

    print("\nUser: Help me calculate 25 * 4")
    response = await agent.process(Message(role="user", content="Help me calculate 25 * 4"))
    print(f"Agent: {response.content}")


async def main():
    """Run all examples."""
    await basic_tool_usage_example()
    await multiple_tools_example()
    await verbose_mode_example()
    await error_handling_example()
    await custom_system_prompt_example()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. ReActAgent uses a Thought->Action->Observation loop")
    print("2. Tools are provided as a list to the agent")
    print("3. Agent automatically decides which tools to use")
    print("4. Reasoning steps can be inspected with get_steps()")
    print("5. Verbose mode shows the thought process")
    print("6. Tool errors are handled gracefully")
    print("\nNext Steps:")
    print("- Replace MockReActAgent with real LLM-based agent (OpenAI, Anthropic, etc.)")
    print("- Add real tools (APIs, databases, file systems)")
    print("- Implement custom tools for your use case")
    print("- Add retry logic for failed tool executions")
    print("- Combine with ConversationalAgent for multi-turn tool use")


if __name__ == "__main__":
    asyncio.run(main())
