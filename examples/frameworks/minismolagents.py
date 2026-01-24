#!/usr/bin/env python3
"""
MiniSmolagents - Smolagents Equivalent Built on Agenkit

Demonstrates how HuggingFace Smolagents' lightweight tool-using patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy works for small frameworks.

Pattern Mappings: Smolagents ToolCallingAgent → ReActAgent,
CodeAgent → ReActAgent with code execution, @tool → Tool class

Migration guide: docs/migrations/smolagents-to-agenkit.md

Usage: uv run python examples/frameworks/minismolagents.py
"""

import asyncio
from collections.abc import Callable
from typing import Any, cast

from agenkit import Agent, Message, Tool, ToolResult
from agenkit.adapters.llm import LLM, OpenAILLM


class ToolCallingAgent(Agent):
    """
    Tool-calling agent (mirrors Smolagents.ToolCallingAgent).
    Pattern: Smolagents.ToolCallingAgent → Simple agent with tool execution
    """

    def __init__(self, llm: LLM, tools: list[Tool], max_iterations: int = 5) -> None:
        """
        Create tool-calling agent.

        Args:
            llm: LLM adapter to use
            tools: List of tools available to agent
            max_iterations: Maximum tool-calling iterations
        """
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations

    @property
    def name(self) -> str:
        """Return agent's name."""
        return "tool_calling_agent"

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["tool_calling", "problem_solving"]

    async def process(self, message: Message) -> Message:
        """
        Process message with tool-calling loop.

        This is a simplified version of ReActAgent pattern.
        """
        conversation_history = [message]
        thought_process = []

        for iteration in range(self.max_iterations):
            # Get LLM response
            response = await self.llm.complete(conversation_history)

            # Check if LLM wants to use a tool
            content = cast("str", response.content)

            # Simple tool parsing (Smolagents uses special format, we use simple check)
            if "TOOL:" in content and "ARGS:" in content:
                # Extract tool call
                tool_name = self._extract_tool_name(content)
                tool_args = self._extract_tool_args(content)

                # Execute tool
                if tool_name in self.tools:
                    tool = self.tools[tool_name]
                    result = await tool.execute(**tool_args)

                    thought_process.append(f"Used tool: {tool_name}")
                    thought_process.append(f"Result: {result.data}")

                    # Add tool result to conversation
                    tool_message = Message(
                        role="user",
                        content=f"Tool result: {result.data}",
                        metadata={"tool": tool_name},
                    )
                    conversation_history.append(tool_message)
                else:
                    # Tool not found
                    conversation_history.append(
                        Message(
                            role="user",
                            content=f"Error: Tool '{tool_name}' not found",
                        )
                    )
            else:
                # No tool call, agent has final answer
                return Message(
                    role="agent",
                    content=content,
                    metadata={
                        "iterations": iteration + 1,
                        "thought_process": thought_process,
                    },
                )

        # Max iterations reached
        return Message(
            role="agent",
            content="Max iterations reached without final answer",
            metadata={"iterations": self.max_iterations, "thought_process": thought_process},
        )

    def _extract_tool_name(self, content: str) -> str:
        """Extract tool name from LLM response."""
        # Simple extraction: TOOL: tool_name
        if "TOOL:" in content:
            parts = content.split("TOOL:")[1].split("\n")[0]
            return parts.strip()
        return ""

    def _extract_tool_args(self, content: str) -> dict[str, Any]:
        """Extract tool arguments from LLM response."""
        # Simple extraction: ARGS: {"key": "value"}
        if "ARGS:" in content:
            args_str = content.split("ARGS:")[1].split("\n")[0].strip()
            # In real implementation, use JSON parsing
            return {"query": args_str.strip('"')}
        return {}


class CodeAgent(Agent):
    """
    Code generation and execution agent (mirrors Smolagents.CodeAgent).
    Pattern: Smolagents.CodeAgent → Agent with code execution capability
    """

    def __init__(self, llm: LLM, tools: list[Tool] | None = None) -> None:
        """
        Create code agent.

        Args:
            llm: LLM adapter to use
            tools: Optional tools (converted to code functions)
        """
        self.llm = llm
        self.tools = tools or []

    @property
    def name(self) -> str:
        """Return agent's name."""
        return "code_agent"

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["code_generation", "code_execution", "problem_solving"]

    async def process(self, message: Message) -> Message:
        """
        Process message by generating and executing code.

        Smolagents' key innovation: agents write Python code instead of JSON tool calls.
        """
        # Build prompt for code generation
        system_prompt = """You are a code-writing agent. Solve tasks by writing Python code.

Available tools:
"""
        for tool in self.tools:
            system_prompt += f"- {tool.name}: {tool.description}\n"

        system_prompt += """
Write Python code to solve the task. The code will be executed and results returned.

Example:
```python
result = search_tool(query="Paris weather")
print(result)
```
"""

        prompt = f"{system_prompt}\n\nTask: {message.content}\n\nYour code:"

        # Get code from LLM
        response = await self.llm.complete([Message(role="user", content=prompt)])
        code = cast("str", response.content)

        # Extract code from markdown if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        # Note: In production, execute in sandbox (Docker, E2B, Modal, etc.)
        execution_result = f"[Code would be executed here]\nGenerated code:\n{code}"

        return Message(
            role="agent",
            content=execution_result,
            metadata={"generated_code": code, "execution": "simulated"},
        )


def tool(func: Callable[..., Any]) -> Tool:
    """
    Decorator to convert function to Tool (mirrors Smolagents @tool).
    Pattern: Smolagents @tool → Agenkit Tool class wrapper
    """

    class FunctionTool(Tool):
        """Tool wrapping a Python function."""

        def __init__(self, function: Callable[..., Any]) -> None:
            """Create tool from function."""
            self.function = function
            self._name = function.__name__
            self._description = function.__doc__ or "No description"

        @property
        def name(self) -> str:
            """Return tool name."""
            return self._name

        @property
        def description(self) -> str:
            """Return tool description."""
            return self._description

        async def execute(self, **kwargs: Any) -> ToolResult:
            """Execute the wrapped function."""
            try:
                # Call function with params
                result = self.function(**kwargs)
                return ToolResult(success=True, data=result)
            except Exception as e:
                return ToolResult(success=False, data=None, error=str(e))

    return FunctionTool(func)


# Example tools (like Smolagents' built-in tools)
@tool
def search_tool(query: str) -> str:
    """Search the web for information."""
    # Simplified for demo
    return f"Search results for: {query}"


@tool
def calculator_tool(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        # Note: Use safe eval in production
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


async def example_tool_calling() -> None:
    """Example: Simple tool-calling agent."""
    print("=" * 60)
    print("Example 1: Tool-Calling Agent (Smolagents-style)")
    print("=" * 60)

    # Create LLM (using test key for demo)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create agent with tools
    agent = ToolCallingAgent(llm=llm, tools=[search_tool, calculator_tool], max_iterations=5)

    print("\n📝 Smolagents-style API:")
    print("   agent = ToolCallingAgent(llm=llm, tools=[search, calculator])")
    print("   result = await agent.process(message)")

    print("\n✅ Pattern: Smolagents.ToolCallingAgent → Simple tool execution loop")
    print("   Agent uses tools to solve problems step-by-step")


async def example_code_agent() -> None:
    """Example: Code generation agent."""
    print("\n\n" + "=" * 60)
    print("Example 2: Code Agent (Code-First Approach)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create code agent
    agent = CodeAgent(llm=llm, tools=[search_tool, calculator_tool])

    print("\n📝 Smolagents-style API:")
    print("   agent = CodeAgent(llm=llm, tools=[...])")
    print("   result = await agent.process(message)")

    print("\n✅ Pattern: Smolagents.CodeAgent → Code generation + execution")
    print("   Agent writes Python code instead of JSON tool calls")
    print("   More flexible but requires sandboxed execution")


async def example_tool_decorator() -> None:
    """Example: @tool decorator for creating tools."""
    print("\n\n" + "=" * 60)
    print("Example 3: @tool Decorator")
    print("=" * 60)

    print("\n📝 Smolagents Pattern:")
    print("   @tool")
    print("   def my_tool(query: str) -> str:")
    print('       """Tool description."""')
    print("       return results")

    print("\n✅ Agenkit Equivalent:")
    print("   @tool  # Same decorator!")
    print("   def my_tool(query: str) -> str:")
    print('       """Tool description."""')
    print("       return results")
    print()
    print("   # Or explicit Tool class:")
    print("   class MyTool(Tool):")
    print("       def name(self) -> str: return 'my_tool'")
    print("       def description(self) -> str: return 'Tool description'")
    print("       async def execute(self, params): ...")

    print("\n💡 Why explicit is better:")
    print("   • Type-safe with full IDE support")
    print("   • Async execution built-in")
    print("   • Error handling standardized")
    print("   • Easier to test and mock")


async def main() -> None:
    """Run all examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 6 + "MiniSmolagents - Smolagents Built on Agenkit" + " " * 7 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n🎯 Demonstrate: HuggingFace Smolagents patterns on Agenkit")

    await example_tool_calling()
    await example_code_agent()
    await example_tool_decorator()

    print("\n\n" + "=" * 60)
    print("✅ MiniSmolagents Examples Complete")
    print("=" * 60)
    print("\n🔑 Key Takeaways:")
    print("   • Agenkit supports lightweight, code-first agent patterns")
    print("   • Smolagents patterns map to Agenkit primitives:")
    print("     - ToolCallingAgent → Simple ReActAgent-style tool loop")
    print("     - CodeAgent → Code generation + execution")
    print("     - @tool → Tool class wrapper")
    print("     - ToolBox → List[Tool]")

    print("\n📚 Migration guide: docs/migrations/smolagents-to-agenkit.md")
    print("\n💡 Why Agenkit over Smolagents?")
    print("   ✓ 6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   ✓ 11+ patterns (not just code-first agents)")
    print("   ✓ Production middleware (retry, circuit breaker, timeout)")
    print("   ✓ OpenTelemetry observability")
    print("   ✓ Any LLM provider (not just HuggingFace)")
    print("   ✓ 18x faster in Go for production")


if __name__ == "__main__":
    asyncio.run(main())
