"""
Tool-Use During Reasoning Pattern

Enables interleaved reasoning and tool usage, where tools can be called
DURING the reasoning process rather than only after reasoning completes.

This pattern is inspired by Claude 4 and o3's extended thinking capabilities,
where the model can use tools to refine its reasoning in real-time.

Key differences from ReAct:
- ReAct: Observe → Think → Act → Observe → Think → Act (sequential)
- This: Think ↔ Act (interleaved, tools available during thinking)
- Tools help refine reasoning, not just execute actions
- Supports extended thinking with tool integration

Example:
    >>> agent = ReasoningWithToolsAgent(
    ...     llm=my_llm_agent,
    ...     tools=[calculator, web_search, database],
    ...     max_reasoning_steps=10,
    ...     allow_tool_during_reasoning=True
    ... )
    >>>
    >>> # Agent can use tools WHILE reasoning about the problem
    >>> response = await agent.process(Message(
    ...     role="user",
    ...     content="What's the total cost if I buy 3 items at $15.99 each with 8.5% tax?"
    ... ))
    >>>
    >>> # Agent might:
    >>> # 1. Start reasoning about the problem
    >>> # 2. Call calculator tool: 3 * 15.99 = 47.97
    >>> # 3. Continue reasoning with that result
    >>> # 4. Call calculator tool: 47.97 * 1.085 = 52.05
    >>> # 5. Complete reasoning with final answer
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..interfaces import Agent, Message, Tool


class ReasoningStepType(Enum):
    """Type of reasoning step."""

    THINKING = "thinking"  # Pure reasoning
    TOOL_CALL = "tool_call"  # Tool invocation
    TOOL_RESULT = "tool_result"  # Tool response
    CONCLUSION = "conclusion"  # Final answer


@dataclass
class ReasoningStep:
    """A single step in the reasoning process."""

    step_number: int
    step_type: ReasoningStepType
    content: str
    tool_name: str | None = None
    tool_parameters: dict[str, Any] | None = None
    tool_result: Any | None = None
    confidence: float | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_parameters": self.tool_parameters,
            "tool_result": self.tool_result,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class ReasoningTrace:
    """Complete trace of reasoning process."""

    steps: list[ReasoningStep] = field(default_factory=list)
    total_tools_used: int = 0
    total_thinking_steps: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    def add_step(self, step: ReasoningStep) -> None:
        """Add a step to the trace."""
        self.steps.append(step)

        if step.step_type == ReasoningStepType.THINKING:
            self.total_thinking_steps += 1
        elif step.step_type == ReasoningStepType.TOOL_CALL:
            self.total_tools_used += 1

    def finalize(self) -> None:
        """Mark reasoning as complete."""
        self.end_time = time.time()

    @property
    def duration_seconds(self) -> float:
        """Get total reasoning duration."""
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_tools_used": self.total_tools_used,
            "total_thinking_steps": self.total_thinking_steps,
            "duration_seconds": self.duration_seconds,
        }


class ReasoningWithToolsAgent(Agent):
    """
    Agent that can use tools during reasoning (not just after).

    This pattern enables the model to:
    1. Start reasoning about a problem
    2. Realize it needs information
    3. Call a tool to get that information
    4. Continue reasoning with the new information
    5. Repeat as needed

    This is different from ReAct where:
    - Reasoning happens BEFORE action
    - Action is taken BASED ON completed reasoning
    - New observation triggers NEW reasoning

    Example:
        >>> # Create agent with tools
        >>> agent = ReasoningWithToolsAgent(
        ...     llm=base_llm_agent,
        ...     tools=[calculator, search, database],
        ...     max_reasoning_steps=20,
        ...     tool_use_prompt="You can use tools while thinking"
        ... )
        >>>
        >>> # Agent interleaves thinking and tool use
        >>> response = await agent.process(Message(
        ...     role="user",
        ...     content="Complex multi-step problem..."
        ... ))
        >>>
        >>> # Get reasoning trace
        >>> trace = response.metadata.get("reasoning_trace")
        >>> print(f"Steps: {len(trace['steps'])}")
        >>> print(f"Tools used: {trace['total_tools_used']}")
    """

    def __init__(
        self,
        llm: Agent,
        tools: list[Tool],
        max_reasoning_steps: int = 20,
        tool_use_prompt: str | None = None,
        enable_trace: bool = True,
        confidence_threshold: float = 0.8,
    ):
        """Initialize reasoning with tools agent.

        Args:
            llm: Base LLM agent for reasoning
            tools: Available tools
            max_reasoning_steps: Maximum reasoning steps
            tool_use_prompt: Custom prompt for tool usage
            enable_trace: Whether to generate reasoning trace
            confidence_threshold: Confidence threshold for accepting answer
        """
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.max_reasoning_steps = max_reasoning_steps
        self.tool_use_prompt = tool_use_prompt or self._default_tool_prompt()
        self.enable_trace = enable_trace
        self.confidence_threshold = confidence_threshold

    def _default_tool_prompt(self) -> str:
        """Generate default tool usage prompt."""
        tool_descriptions = "\n".join(
            f"- {name}: {tool.description}" for name, tool in self.tools.items()
        )

        return f"""You can use tools WHILE reasoning about the problem.
When you need information or computation, use a tool immediately.
Don't wait until you finish reasoning - use tools as needed.

Available tools:
{tool_descriptions}

To use a tool, output:
TOOL_CALL: <tool_name>
PARAMETERS: {{"param1": "value1", ...}}

Continue reasoning after you get the tool result."""

    @property
    def name(self) -> str:
        """Agent name."""
        return f"reasoning_with_tools_{self.llm.name}"

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        caps = self.llm.capabilities.copy()
        caps.extend(["reasoning_with_tools", "extended_thinking", "tool_integration"])
        return caps

    async def process(self, message: Message) -> Message:
        """Process message with reasoning and tool use.

        Args:
            message: Input message

        Returns:
            Response with reasoning trace
        """
        trace = ReasoningTrace() if self.enable_trace else None

        # Enhance message with tool instructions
        enhanced_content = f"""{self.tool_use_prompt}

USER QUESTION:
{message.content}

Begin reasoning. Use tools as needed while thinking."""

        Message(role=message.role, content=enhanced_content, metadata=message.metadata or {})

        # Reasoning loop
        current_context = enhanced_content
        final_answer = None

        for step_num in range(self.max_reasoning_steps):
            # Get next reasoning step from LLM
            response = await self.llm.process(Message(role="user", content=current_context))

            response_text = str(response.content)

            # Check if this is a tool call
            if "TOOL_CALL:" in response_text:
                tool_name, parameters, remaining_text = self._parse_tool_call(response_text)

                if tool_name and tool_name in self.tools:
                    # Record thinking before tool call
                    if trace and remaining_text.strip():
                        trace.add_step(
                            ReasoningStep(
                                step_number=step_num,
                                step_type=ReasoningStepType.THINKING,
                                content=remaining_text.strip(),
                            )
                        )

                    # Execute tool
                    tool = self.tools[tool_name]
                    try:
                        tool_result = await tool.execute(**parameters)

                        # Record tool call and result
                        if trace:
                            trace.add_step(
                                ReasoningStep(
                                    step_number=step_num,
                                    step_type=ReasoningStepType.TOOL_CALL,
                                    content=f"Called {tool_name}",
                                    tool_name=tool_name,
                                    tool_parameters=parameters,
                                )
                            )
                            trace.add_step(
                                ReasoningStep(
                                    step_number=step_num,
                                    step_type=ReasoningStepType.TOOL_RESULT,
                                    content=str(tool_result.data),
                                    tool_name=tool_name,
                                    tool_result=tool_result.data,
                                )
                            )

                        # Update context with tool result
                        current_context = f"""Previous reasoning: {current_context}

TOOL RESULT from {tool_name}:
{tool_result.data}

Continue reasoning with this information."""

                    except Exception as e:
                        # Tool execution failed
                        error_msg = f"Tool {tool_name} failed: {e!s}"
                        if trace:
                            trace.add_step(
                                ReasoningStep(
                                    step_number=step_num,
                                    step_type=ReasoningStepType.TOOL_RESULT,
                                    content=error_msg,
                                    tool_name=tool_name,
                                )
                            )
                        current_context = f"""{current_context}

ERROR: {error_msg}

Continue reasoning without this tool."""

                else:
                    # Unknown tool, continue with regular thinking
                    if trace:
                        trace.add_step(
                            ReasoningStep(
                                step_number=step_num,
                                step_type=ReasoningStepType.THINKING,
                                content=response_text,
                            )
                        )
                    current_context = f"""{current_context}

{response_text}

Continue."""

            else:
                # Regular thinking step
                if trace:
                    trace.add_step(
                        ReasoningStep(
                            step_number=step_num,
                            step_type=ReasoningStepType.THINKING,
                            content=response_text,
                        )
                    )

                # Check if we have a final answer
                if self._is_conclusion(response_text):
                    final_answer = self._extract_answer(response_text)
                    if trace:
                        trace.add_step(
                            ReasoningStep(
                                step_number=step_num,
                                step_type=ReasoningStepType.CONCLUSION,
                                content=final_answer,
                            )
                        )
                    break

                # Update context for next iteration
                current_context = f"""{current_context}

{response_text}

Continue reasoning or provide final answer."""

        # Finalize trace
        if trace:
            trace.finalize()

        # If no answer found, use last response
        if final_answer is None:
            final_answer = response_text

        # Create response with trace
        metadata = {}
        if trace:
            metadata["reasoning_trace"] = trace.to_dict()
            metadata["reasoning_steps"] = trace.total_thinking_steps
            metadata["tools_used"] = trace.total_tools_used

        response_message = Message(
            role="assistant",
            content=final_answer,
            metadata=metadata if metadata else None,
        )

        return response_message

    def _parse_tool_call(self, text: str) -> tuple[str | None, dict[str, Any], str]:
        """Parse tool call from text.

        Args:
            text: Text containing tool call

        Returns:
            Tuple of (tool_name, parameters, remaining_text)
        """
        try:
            # Extract tool name
            if "TOOL_CALL:" not in text:
                return None, {}, text

            parts = text.split("TOOL_CALL:", 1)
            before = parts[0]
            after = parts[1]

            # Get tool name (first line after TOOL_CALL:)
            lines = after.split("\n")
            tool_name = lines[0].strip()

            # Extract parameters
            parameters = {}
            if "PARAMETERS:" in after:
                param_parts = after.split("PARAMETERS:", 1)
                param_text = param_parts[1].strip()

                # Try to parse JSON
                try:
                    # Find JSON object
                    start = param_text.find("{")
                    if start != -1:
                        # Find matching closing brace
                        depth = 0
                        end = start
                        for i, char in enumerate(param_text[start:], start):
                            if char == "{":
                                depth += 1
                            elif char == "}":
                                depth -= 1
                                if depth == 0:
                                    end = i + 1
                                    break

                        json_str = param_text[start:end]
                        parameters = json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            return tool_name, parameters, before

        except Exception:
            return None, {}, text

    def _is_conclusion(self, text: str) -> bool:
        """Check if text contains a final conclusion.

        Args:
            text: Text to check

        Returns:
            True if this looks like a final answer
        """
        conclusion_markers = [
            "FINAL ANSWER:",
            "CONCLUSION:",
            "Therefore,",
            "In conclusion,",
            "The answer is",
        ]

        text_upper = text.upper()
        return any(marker.upper() in text_upper for marker in conclusion_markers)

    def _extract_answer(self, text: str) -> str:
        """Extract final answer from conclusion text.

        Args:
            text: Text containing conclusion

        Returns:
            Extracted answer
        """
        # Try to extract text after conclusion marker
        for marker in ["FINAL ANSWER:", "CONCLUSION:", "The answer is"]:
            if marker.upper() in text.upper():
                idx = text.upper().find(marker.upper())
                return text[idx + len(marker) :].strip()

        return text

    def get_tool(self, name: str) -> Tool | None:
        """Get tool by name.

        Args:
            name: Tool name

        Returns:
            Tool or None if not found
        """
        return self.tools.get(name)

    def add_tool(self, tool: Tool) -> None:
        """Add a tool.

        Args:
            tool: Tool to add
        """
        self.tools[tool.name] = tool

    def remove_tool(self, name: str) -> bool:
        """Remove a tool.

        Args:
            name: Tool name

        Returns:
            True if tool was removed
        """
        if name in self.tools:
            del self.tools[name]
            return True
        return False
