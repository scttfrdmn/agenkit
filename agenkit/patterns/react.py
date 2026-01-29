"""
ReAct (Reasoning + Acting) Agent Pattern

Implements the ReAct pattern where agents reason about actions and execute tools
in an iterative loop until completing a task.

The ReAct loop:
1. Observation: Current state/input
2. Thought: LLM reasons about what to do next
3. Action: Execute a tool or provide final answer
4. Repeat until task is complete

References:
- ReAct Paper: https://arxiv.org/abs/2210.03629
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from agenkit import Agent, Message


class Tool(Protocol):
    """Protocol for tools that can be used by ReAct agents."""

    name: str
    description: str

    async def execute(self, params: dict[str, Any]) -> Any:
        """Execute the tool with given parameters."""
        ...


@dataclass
class ToolResult:
    """
    Result from tool execution.

    Attributes:
        tool_name: Name of the tool that was executed
        result: The result value from the tool
        error: Error message if execution failed
        execution_time: How long the tool took to execute (seconds)
    """

    tool_name: str
    result: Any = None
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Whether the tool executed successfully."""
        return self.error is None


@dataclass
class ReActStep:
    """
    A single step in the ReAct reasoning loop.

    Attributes:
        thought: The agent's reasoning about what to do
        action: The action to take (tool name or "Final Answer")
        action_input: Parameters for the action
        observation: Result from executing the action
        step_number: Which step this is in the sequence
    """

    thought: str
    action: str
    action_input: Any
    observation: str = ""
    step_number: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class ReActConfig:
    """
    Configuration for ReActAgent.

    This config-based approach provides:
    - Cross-language API consistency (matches Go/C++/Rust/TypeScript/Zig)
    - Better documentation (all parameters in one place)
    - Type safety and IDE autocomplete
    - Extensibility without breaking changes

    Attributes:
        agent: Agent for reasoning (e.g., LLM-based agent)
        tools: List of available tools the agent can use
        max_steps: Maximum reasoning steps before stopping (default: 10)
        system_prompt: Optional custom system prompt to guide behavior
        verbose: Whether to include thought process in response (default: False)

    Example:
        >>> from agenkit.patterns import ReActAgent, ReActConfig
        >>> config = ReActConfig(
        ...     agent=my_llm_agent,
        ...     tools=[calculator_tool, search_tool],
        ...     max_steps=15,
        ...     verbose=True
        ... )
        >>> agent = ReActAgent(config)
    """

    agent: Agent
    tools: list[Tool]
    max_steps: int = 10
    system_prompt: str | None = None
    verbose: bool = False

    def __post_init__(self):
        """Validate configuration."""
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if not self.tools:
            raise ValueError("tools list cannot be empty")


class ReActAgent(Agent):
    """
    Agent that uses the ReAct pattern to reason and act.

    The agent maintains a thought process, deciding which tools to use
    and when to provide a final answer.

    Example (recommended config-based API):
        ```python
        from agenkit.patterns import ReActAgent, ReActConfig

        # Setup tools
        tools = [calculator_tool, search_tool]

        # Create configuration
        config = ReActConfig(
            agent=base_agent,
            tools=tools,
            max_steps=10
        )

        # Create agent with config
        agent = ReActAgent(config)

        # Process a task
        result = await agent.process(
            Message(role="user", content="What is 15% of 240?")
        )
        # Agent will reason about using calculator tool and provide answer
        ```

    Example (deprecated direct parameters):
        ```python
        # This API is deprecated and will be removed in v2.0
        agent = ReActAgent(
            agent=base_agent,
            tools=tools,
            max_steps=10
        )
        ```

    Args:
        config: Configuration object (recommended, matches other languages)
        agent: (Deprecated) Agent for reasoning (e.g., LLM-based agent)
        tools: (Deprecated) List of available tools
        max_steps: (Deprecated) Maximum reasoning steps before stopping
        system_prompt: (Deprecated) Optional system prompt to guide behavior
        verbose: (Deprecated) Whether to include thought process in response
    """

    def __init__(
        self,
        config: ReActConfig | None = None,
        *,
        # Deprecated parameters (kept for backward compatibility)
        agent: Agent | None = None,
        tools: list[Tool] | None = None,
        max_steps: int = 10,
        system_prompt: str | None = None,
        verbose: bool = False,
    ):
        """
        Initialize ReActAgent.

        Args:
            config: Configuration object (recommended, matches other languages)
            agent: (Deprecated) Agent for reasoning
            tools: (Deprecated) List of available tools
            max_steps: (Deprecated) Maximum reasoning steps
            system_prompt: (Deprecated) Optional system prompt
            verbose: (Deprecated) Whether to include thought process

        Examples:
            >>> # Recommended: config-based (matches all other languages)
            >>> config = ReActConfig(agent=my_agent, tools=my_tools)
            >>> agent = ReActAgent(config)
            >>>
            >>> # Deprecated: direct parameters (will be removed in v2.0)
            >>> agent = ReActAgent(agent=my_agent, tools=my_tools)

        Migration:
            Old code:
                agent = ReActAgent(
                    agent=my_agent,
                    tools=my_tools,
                    max_steps=15,
                    verbose=True
                )

            New code:
                config = ReActConfig(
                    agent=my_agent,
                    tools=my_tools,
                    max_steps=15,
                    verbose=True
                )
                agent = ReActAgent(config)
        """
        import warnings

        if config is not None:
            # New config-based API (recommended)
            self.agent = config.agent
            self.tools = config.tools
            self.max_steps = config.max_steps
            self.system_prompt = config.system_prompt or self._default_system_prompt()
            self.verbose = config.verbose
        elif agent is not None and tools is not None:
            # Old direct-parameter API (deprecated)
            warnings.warn(
                "Direct parameters for ReActAgent are deprecated and will be removed in v2.0. "
                "Use ReActConfig instead: "
                "ReActAgent(ReActConfig(agent=..., tools=...)). "
                "See migration guide for details.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.agent = agent
            self.tools = tools
            self.max_steps = max_steps
            self.system_prompt = system_prompt or self._default_system_prompt()
            self.verbose = verbose
        else:
            raise ValueError(
                "Either 'config' or both 'agent' and 'tools' must be provided. "
                "Recommended: Use ReActConfig for cross-language API consistency."
            )

        self.steps: list[ReActStep] = []

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return "ReActAgent"

    def _default_system_prompt(self) -> str:
        """Generate default system prompt with tool descriptions."""
        tools_desc = self._get_tools_description()
        return f"""You are a helpful assistant that uses tools to answer questions.

{tools_desc}

You should use the following format:

Thought: Think about what you need to do
Action: The tool to use (or "Final Answer" if you can answer)
Action Input: The input for the tool
Observation: The result from the tool

Repeat Thought/Action/Observation until you have enough information, then:

Thought: I now know the final answer
Action: Final Answer
Action Input: [your final answer here]

Begin!"""

    def _get_tools_description(self) -> str:
        """
        Get formatted description of all tools for LLM prompt.

        Returns:
            Formatted string describing all available tools
        """
        if not self.tools:
            return "No tools available."

        lines = ["Available tools:"]
        for tool in self.tools:
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    async def _execute_tool(self, tool_name: str, params: dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool

        Returns:
            ToolResult containing the execution result or error
        """
        # Find tool in list
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        if tool is None:
            return ToolResult(tool_name=tool_name, error=f"Tool '{tool_name}' not found")

        start_time = asyncio.get_event_loop().time()
        try:
            result = await tool.execute(params)
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult(tool_name=tool_name, result=result, execution_time=execution_time)
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult(tool_name=tool_name, error=str(e), execution_time=execution_time)

    async def process(self, message: Message) -> Message:
        """
        Process a message using the ReAct loop.

        Args:
            message: The user's question/task

        Returns:
            Message containing the final answer (and optionally the thought process)
        """
        self.steps = []  # Reset steps for new task

        # Build initial prompt with system message
        Message(role="system", content=self.system_prompt)

        # Combine system prompt with user message for initial call
        combined_content = f"{self.system_prompt}\n\nUser: {message.content}"
        current_message = Message(role="user", content=combined_content)

        for iteration in range(self.max_steps):
            # Get agent reasoning
            response = await self.agent.process(current_message)

            # Parse response into thought, action, and action_input
            step = self._parse_response(response.content, iteration)

            if step.action.lower() == "final answer":
                # Agent has finished reasoning
                return self._format_final_response(step.action_input)

            # Execute the action (tool)
            tool_result = await self._execute_tool(step.action, step.action_input)

            if tool_result.success:
                step.observation = str(tool_result.result)
            else:
                step.observation = f"Error: {tool_result.error}"

            self.steps.append(step)

            # Build next message with observation
            observation_msg = f"Observation: {step.observation}\n\nWhat's your next thought/action?"
            current_message = Message(role="user", content=observation_msg)

        # Max steps reached
        return Message(
            role="assistant",
            content="I couldn't complete the task within the maximum number of steps. Please try rephrasing your question or breaking it into smaller parts.",
        )

    def _parse_response(self, response: str, step_number: int) -> ReActStep:
        """
        Parse LLM response into a ReActStep.

        Expected format:
        Thought: <reasoning>
        Action: <tool_name or "Final Answer">
        Action Input: <input for tool>
        """
        lines = response.strip().split("\n")

        thought = ""
        action = ""
        action_input: Any = {}

        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                thought = line[8:].strip()
            elif line.startswith("Action:"):
                action = line[7:].strip()
            elif line.startswith("Action Input:"):
                action_input_str = line[13:].strip()
                # Try to parse as dict, otherwise use as string
                try:
                    # Simple parsing for dict-like input
                    if action_input_str.startswith("{"):
                        import json

                        action_input = json.loads(action_input_str)
                    else:
                        action_input = {"input": action_input_str}
                except Exception:
                    action_input = {"input": action_input_str}

        return ReActStep(
            thought=thought,
            action=action,
            action_input=action_input,
            step_number=step_number,
        )

    def _format_final_response(self, answer: Any) -> Message:
        """Format the final response, optionally including thought process."""
        if self.verbose:
            # Include reasoning steps
            thought_process = "\n\n".join(
                [
                    f"Step {s.step_number + 1}:\nThought: {s.thought}\nAction: {s.action}\nObservation: {s.observation}"
                    for s in self.steps
                ]
            )
            content = f"{thought_process}\n\nFinal Answer: {answer}"
        # Just the answer
        elif isinstance(answer, dict) and "input" in answer:
            content = str(answer["input"])
        else:
            content = str(answer)

        # Add metadata about tool usage and iterations
        tool_calls_made = len(self.steps)  # Each step involves a tool call
        unique_tools = list({s.action for s in self.steps if s.action.lower() != "final answer"})

        metadata = {
            "tool_calls_made": tool_calls_made,
            "iterations": len(self.steps) + 1,  # +1 for final answer step
            "react_steps": [
                {"thought": s.thought, "action": s.action, "observation": s.observation}
                for s in self.steps
            ],
            "tools_used": unique_tools,
        }

        return Message(role="assistant", content=content, metadata=metadata)

    def get_steps(self) -> list[ReActStep]:
        """
        Get the reasoning steps from the last execution.

        Returns:
            List of ReActStep objects showing the thought process
        """
        return self.steps.copy()

    def clear_steps(self) -> None:
        """Clear the stored reasoning steps."""
        self.steps = []
