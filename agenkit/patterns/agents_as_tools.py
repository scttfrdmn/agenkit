"""
Agents-as-Tools Pattern - Hierarchical Agent Delegation

The Agents-as-Tools pattern enables agents to call other agents as tools,
creating hierarchical multi-agent systems where specialized agents can be
invoked by supervisor agents.

Key Concepts:
- AgentTool: Wrapper that exposes an agent as a tool
- Hierarchical Delegation: Supervisor delegates to specialist agents
- Tool Interface: Agents expose standard tool interface (name, description, execute)
- Transparent Integration: Works with existing ReAct and tool-calling infrastructure

Use Cases:
- Supervisor agent delegating to specialist agents
- Domain-specific agent routing
- Hierarchical multi-agent systems
- Agent composition and orchestration

Example:
    >>> from agenkit.patterns import agent_as_tool
    >>> from agenkit.patterns import ReActAgent
    >>>
    >>> # Create specialist agents
    >>> code_agent = CodeSpecialistAgent()
    >>> data_agent = DataSpecialistAgent()
    >>>
    >>> # Wrap as tools
    >>> code_tool = agent_as_tool(
    ...     agent=code_agent,
    ...     name="code_specialist",
    ...     description="Expert in programming, code review, and debugging"
    ... )
    >>> data_tool = agent_as_tool(
    ...     agent=data_agent,
    ...     name="data_specialist",
    ...     description="Expert in data analysis, SQL, and visualization"
    ... )
    >>>
    >>> # Create supervisor with agent tools
    >>> supervisor = ReActAgent(llm_client=llm, tool_registry=registry)
    >>> supervisor.tools.register(code_tool)
    >>> supervisor.tools.register(data_tool)
    >>>
    >>> # Supervisor can delegate to specialists
    >>> result = await supervisor.process(
    ...     Message(role="user", content="Write a Python function to parse CSV files")
    ... )
    >>> # Supervisor decides to use code_specialist tool
    >>> # -> Delegates to code_agent
    >>> # -> Returns result to supervisor
    >>> # -> Supervisor formulates final answer

References:
- LangChain: Agents-as-Tools pattern
- AutoGPT: Hierarchical agent architecture
- Multi-Agent Systems literature
"""

from typing import Any

from agenkit.interfaces import Agent, Message

__all__ = [
    "AgentTool",
    "agent_as_tool",
]


class AgentTool:
    """
    Wrapper that exposes an agent as a tool.

    Allows agents to call other agents as tools, enabling hierarchical
    delegation and specialization. Compatible with existing tool infrastructure
    (e.g., ReActAgent, ToolRegistry).

    Performance Characteristics:
    - Latency: Same as underlying agent
    - Enables hierarchical composition
    - Maintains full observability (traces preserved)

    Args:
        agent: The agent to wrap as a tool
        name: Tool name for identification and routing
        description: Description for LLM to understand when to use this tool
        input_key: Parameter name for input (default: "query")
        output_format: How to format agent output (default: "str")
        include_metadata: Whether to include agent metadata in output (default: False)

    Example:
        >>> specialist = CodeSpecialistAgent()
        >>> tool = AgentTool(
        ...     agent=specialist,
        ...     name="code_specialist",
        ...     description="Expert in Python programming and code review",
        ...     input_key="task",
        ...     output_format="str"
        ... )
        >>>
        >>> result = await tool.execute(task="Write a function to reverse a string")
        >>> print(result)
        "def reverse_string(s: str) -> str:
            return s[::-1]"
    """

    def __init__(
        self,
        agent: Agent,
        name: str,
        description: str,
        input_key: str = "query",
        output_format: str = "str",
        include_metadata: bool = False,
    ):
        if not name:
            raise ValueError("Tool name cannot be empty")
        if not description:
            raise ValueError("Tool description cannot be empty")

        self.agent = agent
        self.name = name
        self.description = description
        self.input_key = input_key
        self.output_format = output_format
        self.include_metadata = include_metadata

    async def execute(self, **kwargs: Any) -> Any:
        """
        Execute the wrapped agent.

        Args:
            **kwargs: Parameters passed to the tool. Must include self.input_key.

        Returns:
            Agent output, formatted according to output_format

        Raises:
            ValueError: If required input_key parameter is missing
        """
        # Extract input
        query = kwargs.get(self.input_key)
        if query is None:
            raise ValueError(
                f"Missing required parameter '{self.input_key}'. "
                f"Available parameters: {list(kwargs.keys())}"
            )

        # Create message
        message = Message(role="user", content=str(query))

        # Call agent
        response = await self.agent.process(message)

        # Format output
        return self._format_output(response)

    def _format_output(self, response: Message) -> Any:
        """
        Format agent response based on output_format.

        Args:
            response: Agent response message

        Returns:
            Formatted output
        """
        if self.output_format == "str":
            return response.content

        elif self.output_format == "dict":
            result = {"content": response.content}
            if self.include_metadata:
                result["metadata"] = response.metadata
            return result

        elif self.output_format == "message":
            return response

        else:
            # Default: return string content
            return response.content

    def __repr__(self) -> str:
        """String representation."""
        return f"AgentTool(name='{self.name}', agent={self.agent.name})"


def agent_as_tool(
    agent: Agent,
    name: str,
    description: str,
    input_key: str = "query",
    output_format: str = "str",
    include_metadata: bool = False,
) -> AgentTool:
    """
    Convenience function to wrap an agent as a tool.

    This is the primary API for creating agent tools. Use this function
    rather than instantiating AgentTool directly.

    Args:
        agent: The agent to wrap
        name: Tool name (used for routing and identification)
        description: Tool description (helps LLM decide when to use)
        input_key: Parameter name for input (default: "query")
        output_format: Output format - "str", "dict", or "message" (default: "str")
        include_metadata: Include agent metadata in output (default: False)

    Returns:
        AgentTool instance ready to be registered

    Example:
        >>> from agenkit.patterns import agent_as_tool
        >>> from agenkit.patterns import ReActAgent
        >>>
        >>> # Create specialists
        >>> code_agent = CodeSpecialistAgent()
        >>> math_agent = MathSpecialistAgent()
        >>>
        >>> # Wrap as tools
        >>> code_tool = agent_as_tool(
        ...     agent=code_agent,
        ...     name="code_expert",
        ...     description="Expert programmer for code-related tasks"
        ... )
        >>> math_tool = agent_as_tool(
        ...     agent=math_agent,
        ...     name="math_expert",
        ...     description="Expert mathematician for math problems"
        ... )
        >>>
        >>> # Create supervisor
        >>> supervisor = ReActAgent(llm_client=llm, tool_registry=registry)
        >>> supervisor.tools.register(code_tool)
        >>> supervisor.tools.register(math_tool)
        >>>
        >>> # Supervisor delegates to specialists
        >>> result = await supervisor.process(
        ...     Message(role="user", content="Calculate the factorial of 10")
        ... )
        >>> # Supervisor routes to math_expert tool automatically

    Integration with ReActAgent:
        >>> from agenkit.patterns import ReActAgent, ToolRegistry, agent_as_tool
        >>>
        >>> # Setup
        >>> registry = ToolRegistry()
        >>> registry.register(agent_as_tool(specialist1, "specialist1", "..."))
        >>> registry.register(agent_as_tool(specialist2, "specialist2", "..."))
        >>>
        >>> # Create supervisor
        >>> supervisor = ReActAgent(
        ...     llm_client=llm,
        ...     tool_registry=registry,
        ...     max_iterations=10
        ... )
        >>>
        >>> # Supervisor automatically selects appropriate specialist
        >>> result = await supervisor.process(user_message)

    Best Practices:
        1. Clear Names: Use descriptive, unique names (e.g., "python_expert" not "agent1")
        2. Good Descriptions: Help LLM understand when to use the tool
        3. Specialist Focus: Each agent should have clear domain expertise
        4. Error Handling: Specialist agents should handle their own errors gracefully
        5. Observability: Use tracing to understand delegation patterns

    Performance:
        - Latency: Supervisor + Specialist(s)
        - Cost: N× calls (supervisor + each specialist invocation)
        - Benefit: Specialization often improves quality despite higher cost
    """
    return AgentTool(
        agent=agent,
        name=name,
        description=description,
        input_key=input_key,
        output_format=output_format,
        include_metadata=include_metadata,
    )
