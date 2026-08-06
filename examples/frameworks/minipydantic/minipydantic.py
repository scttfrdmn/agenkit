"""MiniPydantic: Pydantic AI reimplemented on Agenkit (~250 LOC).

Demonstrates how to build Pydantic AI's type-safe agent patterns using
Agenkit's minimal primitives.

Key Features Implemented:
- Type-safe tool registration with Pydantic models
- Structured outputs with validation
- Dependency injection pattern
- Function-as-tool decorator
- Automatic schema generation

Not Implemented (out of scope):
- Streaming (use Agenkit's AG-UI protocol)
- Multi-agent systems (use Agenkit's composition patterns)
- Advanced memory (use Agenkit's memory systems)
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, TypeVar, get_type_hints

from pydantic import BaseModel, ValidationError, create_model

from agenkit import Agent, Message, Tool, ToolResult

T = TypeVar("T", bound=BaseModel)


# ============================================================================
# Type-Safe Tool Wrapper
# ============================================================================


class TypeSafeTool(Tool):
    """Tool wrapper with Pydantic validation."""

    def __init__(
        self,
        name: str,
        func: Callable,
        input_model: type[BaseModel],
        output_model: type[BaseModel] | None = None,
        description: str | None = None,
    ):
        """Initialize type-safe tool.

        Args:
            name: Tool name
            func: Function to wrap
            input_model: Pydantic model for input validation
            output_model: Pydantic model for output validation (optional)
            description: Tool description
        """
        self._name = name
        self._func = func
        self._input_model = input_model
        self._output_model = output_model
        self._description = description or func.__doc__ or name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        """Get JSON schema for input validation."""
        return self._input_model.model_json_schema()

    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool with input validation.

        Args:
            **kwargs: Tool arguments

        Returns:
            ToolResult with validated output
        """
        try:
            # Validate input
            validated_input = self._input_model(**kwargs)

            # Execute function
            if inspect.iscoroutinefunction(self._func):
                result = await self._func(**validated_input.model_dump())
            else:
                result = self._func(**validated_input.model_dump())

            # Validate output if schema provided
            if self._output_model:
                if isinstance(result, dict):
                    validated_output = self._output_model(**result)
                elif isinstance(result, BaseModel):
                    validated_output = self._output_model(**result.model_dump())
                else:
                    validated_output = self._output_model(value=result)
                data = validated_output.model_dump()
            else:
                data = result if isinstance(result, dict) else {"result": result}

            return ToolResult(
                success=True,
                data=data,
                metadata={"tool": self.name, "validated": True},
            )

        except ValidationError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Validation error: {e}",
                metadata={"validation_errors": e.errors()},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Execution error: {str(e)}",
            )


# ============================================================================
# Tool Decorator
# ============================================================================


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable:
    """Decorator to register a function as a type-safe tool.

    Automatically generates Pydantic models from type hints.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring)

    Returns:
        Decorated function

    Example:
        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b
    """

    def decorator(func: Callable) -> TypeSafeTool:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or tool_name

        # Get type hints
        type_hints = get_type_hints(func)
        return_type = type_hints.pop("return", None)

        # Create input model from parameters
        input_fields = {}
        for param_name, param_type in type_hints.items():
            input_fields[param_name] = (param_type, ...)

        input_model = create_model(
            f"{tool_name.title()}Input",
            **input_fields,
        )

        # Create output model if return type specified
        output_model = None
        if return_type and return_type != type(None):  # noqa: E721
            if isinstance(return_type, type) and issubclass(return_type, BaseModel):
                output_model = return_type
            else:
                output_model = create_model(
                    f"{tool_name.title()}Output",
                    value=(return_type, ...),
                )

        return TypeSafeTool(
            name=tool_name,
            func=func,
            input_model=input_model,
            output_model=output_model,
            description=tool_description,
        )

    return decorator


# ============================================================================
# Type-Safe Agent
# ============================================================================


class TypeSafeAgent(Agent):
    """Pydantic AI-style type-safe agent.

    Features:
    - Automatic input/output validation
    - Type-safe tool registration
    - Structured data handling
    - Dependency injection

    Example:
        agent = TypeSafeAgent(name="MyAgent")

        @agent.tool
        def search(query: str) -> dict:
            return {"results": [...]}

        response = await agent.run("Search for AI agents")
    """

    def __init__(self, name: str, system_prompt: str | None = None):
        """Initialize type-safe agent.

        Args:
            name: Agent name
            system_prompt: System prompt for LLM
        """
        self._name = name
        self._system_prompt = system_prompt
        self._tools: dict[str, TypeSafeTool] = {}
        self._dependencies: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def tools(self) -> dict[str, Tool]:
        """Get registered tools."""
        return self._tools

    def register_tool(self, tool_obj: TypeSafeTool) -> None:
        """Register a type-safe tool.

        Args:
            tool_obj: TypeSafeTool instance
        """
        self._tools[tool_obj.name] = tool_obj

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable:
        """Decorator to register a tool.

        Args:
            name: Tool name
            description: Tool description

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            tool_obj = tool(name=name, description=description)(func)
            self.register_tool(tool_obj)
            return func

        return decorator

    def inject(self, name: str, value: Any) -> None:
        """Register a dependency for injection.

        Args:
            name: Dependency name
            value: Dependency value
        """
        self._dependencies[name] = value

    async def process(self, message: Message) -> Message:
        """Process message with type safety.

        Args:
            message: Input message

        Returns:
            Response message
        """
        # Simple implementation for demonstration
        # In production, this would call an LLM with tool schemas
        content = message.content

        # Select tools based on keywords (simplified)
        selected_tools = self._select_tools(content)

        # Execute tools with validation
        results = []
        for tool_name, args in selected_tools:
            if tool_name in self._tools:
                tool = self._tools[tool_name]
                result = await tool.execute(**args)
                results.append({"tool": tool_name, "result": result})

        # Format response
        response_content = self._format_response(content, results)

        return Message(
            role="assistant",
            content=response_content,
            metadata={
                "tools_used": [r["tool"] for r in results],
                "validated": True,
            },
        )

    async def run(self, input_data: str | BaseModel) -> str | BaseModel:
        """Run agent with structured I/O.

        Args:
            input_data: Input string or Pydantic model

        Returns:
            Response string or Pydantic model
        """
        # Convert input to message
        if isinstance(input_data, BaseModel):
            content = input_data.model_dump_json()
        else:
            content = input_data

        message = Message(role="user", content=content)

        # Process
        response = await self.process(message)

        return response.content

    def _select_tools(self, content: str) -> list[tuple[str, dict[str, Any]]]:
        """Select tools based on content (simplified).

        Args:
            content: Message content

        Returns:
            List of (tool_name, args) tuples
        """
        # Simplified tool selection for demonstration
        # In production, LLM would choose tools and extract args
        tools = []
        content_lower = content.lower()

        for tool_name, tool_obj in self._tools.items():
            if tool_name in content_lower:
                # Extract basic args (very simplified)
                tools.append((tool_name, {}))

        return tools

    def _format_response(self, query: str, results: list[dict[str, Any]]) -> str:
        """Format response from tool results.

        Args:
            query: Original query
            results: Tool execution results

        Returns:
            Formatted response
        """
        if not results:
            return f"Processed query: {query}"

        parts = []
        for result in results:
            tool_name = result["tool"]
            tool_result = result["result"]

            if tool_result.success:
                parts.append(f"✅ {tool_name}: {tool_result.data}")
            else:
                parts.append(f"❌ {tool_name}: {tool_result.error}")

        return "\n".join(parts)


__all__ = [
    "TypeSafeTool",
    "TypeSafeAgent",
    "tool",
]
