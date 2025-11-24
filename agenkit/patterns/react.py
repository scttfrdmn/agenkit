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

    async def execute(self, **kwargs) -> Any:
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


class ToolRegistry:
    """
    Registry for managing available tools.

    Example:
        ```python
        registry = ToolRegistry()
        registry.register(calculator_tool)
        registry.register(search_tool)

        # Get tool description for LLM prompt
        tools_desc = registry.get_tools_description()

        # Execute a tool
        result = await registry.execute("calculator", expression="2+2")
        ```
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Args:
            tool: The tool to register

        Raises:
            ValueError: If a tool with the same name already exists
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to remove
        """
        self._tools.pop(tool_name, None)

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())

    def get_tools_description(self) -> str:
        """
        Get formatted description of all tools for LLM prompt.

        Returns:
            Formatted string describing all available tools
        """
        if not self._tools:
            return "No tools available."

        lines = ["Available tools:"]
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters to pass to the tool

        Returns:
            ToolResult containing the execution result or error
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return ToolResult(tool_name=tool_name, error=f"Tool '{tool_name}' not found")

        start_time = asyncio.get_event_loop().time()
        try:
            result = await tool.execute(**kwargs)
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult(tool_name=tool_name, result=result, execution_time=execution_time)
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult(tool_name=tool_name, error=str(e), execution_time=execution_time)


class LLMClient(Protocol):
    """Protocol for LLM clients that can be used with ReActAgent."""

    async def chat(self, messages: list[Message]) -> Message:
        """Generate a response given conversation history."""
        ...


class ReActAgent(Agent):
    """
    Agent that uses the ReAct pattern to reason and act.

    The agent maintains a thought process, deciding which tools to use
    and when to provide a final answer.

    Example:
        ```python
        from agenkit.patterns import ReActAgent, ToolRegistry

        # Setup tools
        registry = ToolRegistry()
        registry.register(calculator_tool)
        registry.register(search_tool)

        # Create agent
        agent = ReActAgent(
            llm_client=llm,
            tool_registry=registry,
            max_iterations=10
        )

        # Process a task
        result = await agent.process(
            Message(role="user", content="What is 15% of 240?")
        )
        # Agent will reason about using calculator tool and provide answer
        ```

    Args:
        llm_client: LLM client for reasoning
        tool_registry: Registry of available tools
        max_iterations: Maximum reasoning steps before stopping (default: 10)
        system_prompt: Optional system prompt to guide behavior
        verbose: Whether to include thought process in response (default: False)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        max_iterations: int = 10,
        system_prompt: str | None = None,
        verbose: bool = False,
    ):
        self.llm = llm_client
        self.tools = tool_registry
        self.max_iterations = max_iterations
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.verbose = verbose
        self.steps: list[ReActStep] = []

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return "ReActAgent"

    def _default_system_prompt(self) -> str:
        """Generate default system prompt with tool descriptions."""
        tools_desc = self.tools.get_tools_description()
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

    async def process(self, message: Message) -> Message:
        """
        Process a message using the ReAct loop.

        Args:
            message: The user's question/task

        Returns:
            Message containing the final answer (and optionally the thought process)
        """
        self.steps = []  # Reset steps for new task

        # Build initial prompt
        messages = [
            Message(role="system", content=self.system_prompt),
            message,
        ]

        for iteration in range(self.max_iterations):
            # Get LLM reasoning
            response = await self.llm.chat(messages)

            # Parse response into thought, action, and action_input
            step = self._parse_response(response.content, iteration)

            if step.action.lower() == "final answer":
                # Agent has finished reasoning
                return self._format_final_response(step.action_input)

            # Execute the action (tool)
            tool_result = await self.tools.execute(step.action, **step.action_input)

            if tool_result.success:
                step.observation = str(tool_result.result)
            else:
                step.observation = f"Error: {tool_result.error}"

            self.steps.append(step)

            # Add observation to conversation
            observation_msg = f"Observation: {step.observation}"
            messages.append(Message(role="assistant", content=response.content))
            messages.append(Message(role="user", content=observation_msg))

        # Max iterations reached
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
                except:
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

        return Message(role="assistant", content=content)

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
