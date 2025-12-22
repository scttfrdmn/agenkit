"""Tests for Reasoning with Tools pattern."""

import pytest

from agenkit.interfaces import Agent, Message, Tool, ToolResult
from agenkit.patterns.reasoning_with_tools import (ReasoningStep,
                                                   ReasoningStepType,
                                                   ReasoningTrace,
                                                   ReasoningWithToolsAgent)


class MockLLM(Agent):
    """Mock LLM for testing."""

    def __init__(self, responses: list[str]):
        """Initialize with pre-defined responses."""
        self.responses = responses
        self.call_count = 0

    @property
    def name(self) -> str:
        """Agent name."""
        return "mock_llm"

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        return ["text_generation"]

    async def process(self, message: Message) -> Message:
        """Return next response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return Message(role="assistant", content=response)
        return Message(role="assistant", content="I don't know")


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str, result: any = "result"):
        """Initialize mock tool."""
        self._name = name
        self._result = result
        self.call_count = 0
        self.last_parameters = None

    @property
    def name(self) -> str:
        """Tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description."""
        return f"Mock tool: {self._name}"

    @property
    def parameters(self) -> dict:
        """Tool parameters schema."""
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool."""
        self.call_count += 1
        self.last_parameters = kwargs
        if isinstance(self._result, Exception):
            raise self._result
        return ToolResult(
            success=True,
            data=self._result,
            error=None,
        )


# Test ReasoningStep


def test_reasoning_step_creation():
    """Test creating a reasoning step."""
    step = ReasoningStep(
        step_number=1,
        step_type=ReasoningStepType.THINKING,
        content="Thinking about the problem",
        confidence=0.9,
    )

    assert step.step_number == 1
    assert step.step_type == ReasoningStepType.THINKING
    assert step.content == "Thinking about the problem"
    assert step.confidence == 0.9
    assert step.tool_name is None


def test_reasoning_step_tool_call():
    """Test reasoning step for tool call."""
    step = ReasoningStep(
        step_number=2,
        step_type=ReasoningStepType.TOOL_CALL,
        content="Calling calculator",
        tool_name="calculator",
        tool_parameters={"operation": "add", "a": 1, "b": 2},
    )

    assert step.step_type == ReasoningStepType.TOOL_CALL
    assert step.tool_name == "calculator"
    assert step.tool_parameters == {"operation": "add", "a": 1, "b": 2}


def test_reasoning_step_to_dict():
    """Test converting reasoning step to dict."""
    step = ReasoningStep(
        step_number=1,
        step_type=ReasoningStepType.THINKING,
        content="Test content",
        tool_name="test_tool",
        confidence=0.8,
    )

    data = step.to_dict()
    assert data["step_number"] == 1
    assert data["step_type"] == "thinking"
    assert data["content"] == "Test content"
    assert data["tool_name"] == "test_tool"
    assert data["confidence"] == 0.8


# Test ReasoningTrace


def test_reasoning_trace_creation():
    """Test creating a reasoning trace."""
    trace = ReasoningTrace()

    assert len(trace.steps) == 0
    assert trace.total_tools_used == 0
    assert trace.total_thinking_steps == 0
    assert trace.end_time is None


def test_reasoning_trace_add_thinking_step():
    """Test adding thinking step to trace."""
    trace = ReasoningTrace()

    step = ReasoningStep(
        step_number=1,
        step_type=ReasoningStepType.THINKING,
        content="Thinking",
    )
    trace.add_step(step)

    assert len(trace.steps) == 1
    assert trace.total_thinking_steps == 1
    assert trace.total_tools_used == 0


def test_reasoning_trace_add_tool_call():
    """Test adding tool call to trace."""
    trace = ReasoningTrace()

    step = ReasoningStep(
        step_number=1,
        step_type=ReasoningStepType.TOOL_CALL,
        content="Calling tool",
        tool_name="calculator",
    )
    trace.add_step(step)

    assert len(trace.steps) == 1
    assert trace.total_tools_used == 1
    assert trace.total_thinking_steps == 0


def test_reasoning_trace_finalize():
    """Test finalizing reasoning trace."""
    trace = ReasoningTrace()
    trace.finalize()

    assert trace.end_time is not None
    assert trace.duration_seconds >= 0


def test_reasoning_trace_to_dict():
    """Test converting reasoning trace to dict."""
    trace = ReasoningTrace()
    trace.add_step(
        ReasoningStep(
            step_number=1,
            step_type=ReasoningStepType.THINKING,
            content="Test",
        )
    )
    trace.finalize()

    data = trace.to_dict()
    assert "steps" in data
    assert "total_tools_used" in data
    assert "total_thinking_steps" in data
    assert "duration_seconds" in data
    assert len(data["steps"]) == 1


# Test ReasoningWithToolsAgent


@pytest.mark.asyncio
async def test_agent_creation():
    """Test creating reasoning with tools agent."""
    llm = MockLLM(["response"])
    tool = MockTool("calculator")

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[tool],
        max_reasoning_steps=10,
    )

    assert agent.name == "reasoning_with_tools_mock_llm"
    assert "reasoning_with_tools" in agent.capabilities
    assert agent.max_reasoning_steps == 10


@pytest.mark.asyncio
async def test_simple_reasoning_without_tools():
    """Test simple reasoning without any tool calls."""
    llm = MockLLM(["FINAL ANSWER: 42"])

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[],
        max_reasoning_steps=5,
    )

    response = await agent.process(Message(role="user", content="What is the answer?"))

    assert "42" in response.content
    assert response.metadata is not None
    assert "reasoning_trace" in response.metadata
    trace = response.metadata["reasoning_trace"]
    assert trace["total_tools_used"] == 0


@pytest.mark.asyncio
async def test_reasoning_with_single_tool_call():
    """Test reasoning with a single tool call."""
    llm = MockLLM(
        [
            'I need to calculate this.\nTOOL_CALL: calculator\nPARAMETERS: {"operation": "add", "a": 1, "b": 2}',
            "FINAL ANSWER: The result is 3",
        ]
    )

    calculator = MockTool("calculator", result=3)

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(Message(role="user", content="What is 1 + 2?"))

    assert "3" in response.content
    assert calculator.call_count == 1
    assert calculator.last_parameters == {"operation": "add", "a": 1, "b": 2}

    trace = response.metadata["reasoning_trace"]
    assert trace["total_tools_used"] == 1
    assert len(trace["steps"]) >= 3  # thinking, tool_call, tool_result, conclusion
    assert response.metadata["reasoning_steps"] >= 3


@pytest.mark.asyncio
async def test_reasoning_with_multiple_tool_calls():
    """Test reasoning with multiple tool calls."""
    llm = MockLLM(
        [
            'First, I\'ll calculate 5 + 3.\nTOOL_CALL: calculator\nPARAMETERS: {"a": 5, "b": 3}',
            'Now I\'ll multiply by 2.\nTOOL_CALL: calculator\nPARAMETERS: {"a": 8, "b": 2}',
            "FINAL ANSWER: The result is 16",
        ]
    )

    calculator = MockTool("calculator", result=8)

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(Message(role="user", content="Calculate"))

    assert calculator.call_count == 2
    trace = response.metadata["reasoning_trace"]
    assert trace["total_tools_used"] == 2


@pytest.mark.asyncio
async def test_tool_execution_error():
    """Test handling tool execution errors."""
    llm = MockLLM(
        [
            "TOOL_CALL: calculator\nPARAMETERS: {}",
            "FINAL ANSWER: Could not calculate",
        ]
    )

    calculator = MockTool("calculator", result=ValueError("Invalid operation"))

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(Message(role="user", content="Calculate"))

    # Should handle error gracefully
    assert response.content is not None
    assert calculator.call_count == 1


@pytest.mark.asyncio
async def test_unknown_tool():
    """Test handling unknown tool calls."""
    llm = MockLLM(
        [
            "TOOL_CALL: unknown_tool\nPARAMETERS: {}",
            "FINAL ANSWER: Done",
        ]
    )

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[],
        max_reasoning_steps=5,
    )

    response = await agent.process(Message(role="user", content="Test"))

    # Should continue despite unknown tool
    assert response.content is not None


@pytest.mark.asyncio
async def test_max_reasoning_steps():
    """Test reaching max reasoning steps limit."""
    # LLM never provides final answer
    llm = MockLLM(["Thinking step 1"] * 20)

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[],
        max_reasoning_steps=3,
    )

    response = await agent.process(Message(role="user", content="Think"))

    # Should stop at max steps
    assert llm.call_count == 3
    assert response.content is not None


@pytest.mark.asyncio
async def test_conclusion_detection():
    """Test detection of various conclusion markers."""
    conclusion_responses = [
        "FINAL ANSWER: 42",
        "CONCLUSION: The answer is 42",
        "Therefore, the answer is 42",
        "In conclusion, 42 is correct",
        "The answer is 42",
    ]

    for conclusion in conclusion_responses:
        llm = MockLLM([conclusion])
        agent = ReasoningWithToolsAgent(llm=llm, tools=[], max_reasoning_steps=5)

        response = await agent.process(Message(role="user", content="Test"))

        assert "42" in response.content
        # Should stop on first conclusion
        assert llm.call_count == 1


@pytest.mark.asyncio
async def test_trace_disabled():
    """Test reasoning with trace disabled."""
    llm = MockLLM(["FINAL ANSWER: Done"])

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[],
        max_reasoning_steps=5,
        enable_trace=False,
    )

    response = await agent.process(Message(role="user", content="Test"))

    # Should not have trace in metadata
    assert response.metadata is None or "reasoning_trace" not in response.metadata


@pytest.mark.asyncio
async def test_custom_tool_prompt():
    """Test using custom tool usage prompt."""
    custom_prompt = "CUSTOM PROMPT: Use tools wisely"

    llm = MockLLM(["FINAL ANSWER: OK"])

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[],
        max_reasoning_steps=5,
        tool_use_prompt=custom_prompt,
    )

    await agent.process(Message(role="user", content="Test"))

    # Custom prompt should be used (would need to inspect llm calls to verify)
    assert agent.tool_use_prompt == custom_prompt


@pytest.mark.asyncio
async def test_tool_management():
    """Test adding, getting, and removing tools."""
    llm = MockLLM(["Done"])
    tool1 = MockTool("tool1")
    tool2 = MockTool("tool2")

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[tool1],
        max_reasoning_steps=5,
    )

    # Get tool
    assert agent.get_tool("tool1") is not None
    assert agent.get_tool("tool1").name == "tool1"
    assert agent.get_tool("nonexistent") is None

    # Add tool
    agent.add_tool(tool2)
    assert agent.get_tool("tool2") is not None

    # Remove tool
    assert agent.remove_tool("tool1") is True
    assert agent.get_tool("tool1") is None
    assert agent.remove_tool("nonexistent") is False


def test_parse_tool_call():
    """Test parsing tool calls from text."""
    llm = MockLLM([])
    agent = ReasoningWithToolsAgent(llm=llm, tools=[], max_reasoning_steps=5)

    # Valid tool call
    text = 'I need to calculate.\nTOOL_CALL: calculator\nPARAMETERS: {"a": 1, "b": 2}'
    tool_name, params, remaining = agent._parse_tool_call(text)

    assert tool_name == "calculator"
    assert params == {"a": 1, "b": 2}
    assert "I need to calculate" in remaining

    # No tool call
    text = "Just thinking about it"
    tool_name, params, remaining = agent._parse_tool_call(text)

    assert tool_name is None
    assert params == {}
    assert remaining == text


def test_is_conclusion():
    """Test conclusion detection."""
    llm = MockLLM([])
    agent = ReasoningWithToolsAgent(llm=llm, tools=[], max_reasoning_steps=5)

    # Should detect conclusions
    assert agent._is_conclusion("FINAL ANSWER: 42")
    assert agent._is_conclusion("CONCLUSION: The answer is 42")
    assert agent._is_conclusion("Therefore, the answer is 42")
    assert agent._is_conclusion("In conclusion, we get 42")
    assert agent._is_conclusion("The answer is clearly 42")

    # Should not detect as conclusion
    assert not agent._is_conclusion("I'm still thinking")
    assert not agent._is_conclusion("Let me calculate this")


def test_extract_answer():
    """Test extracting answer from conclusion."""
    llm = MockLLM([])
    agent = ReasoningWithToolsAgent(llm=llm, tools=[], max_reasoning_steps=5)

    # Extract from FINAL ANSWER
    answer = agent._extract_answer("FINAL ANSWER: 42")
    assert answer == "42"

    # Extract from CONCLUSION
    answer = agent._extract_answer("CONCLUSION: The result is 100")
    assert answer == "The result is 100"

    # Extract from "The answer is"
    answer = agent._extract_answer("The answer is clearly 42")
    assert answer == "clearly 42"

    # No marker - return full text
    answer = agent._extract_answer("Just some text")
    assert answer == "Just some text"


@pytest.mark.asyncio
async def test_complex_multi_step_reasoning():
    """Test complex multi-step reasoning with interleaved tool use."""
    llm = MockLLM(
        [
            'Let me break this down. First, I\'ll get the base price.\nTOOL_CALL: database\nPARAMETERS: {"query": "price"}',
            'The base is $100. Now I\'ll calculate tax.\nTOOL_CALL: calculator\nPARAMETERS: {"operation": "multiply", "a": 100, "b": 0.08}',
            'Tax is $8. Now I\'ll get the total.\nTOOL_CALL: calculator\nPARAMETERS: {"operation": "add", "a": 100, "b": 8}',
            "FINAL ANSWER: The total cost is $108",
        ]
    )

    database = MockTool("database", result="$100")
    calculator = MockTool("calculator", result=108)

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[database, calculator],
        max_reasoning_steps=15,
    )

    response = await agent.process(Message(role="user", content="Calculate total cost"))

    assert "108" in response.content
    assert database.call_count == 1
    assert calculator.call_count == 2

    trace = response.metadata["reasoning_trace"]
    assert trace["total_tools_used"] == 3
    assert trace["total_thinking_steps"] >= 3


@pytest.mark.asyncio
async def test_reasoning_trace_structure():
    """Test the structure and content of reasoning trace."""
    llm = MockLLM(
        [
            'I\'ll use the calculator.\nTOOL_CALL: calculator\nPARAMETERS: {"x": 5}',
            "FINAL ANSWER: Result is 5",
        ]
    )

    calculator = MockTool("calculator", result=5)

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(Message(role="user", content="Calculate"))

    trace = response.metadata["reasoning_trace"]

    # Check trace structure
    assert "steps" in trace
    assert "total_tools_used" in trace
    assert "total_thinking_steps" in trace
    assert "duration_seconds" in trace

    # Check steps
    steps = trace["steps"]
    assert len(steps) > 0

    # Should have thinking, tool_call, tool_result, conclusion
    step_types = [s["step_type"] for s in steps]
    assert "thinking" in step_types or "tool_call" in step_types
    assert "tool_call" in step_types
    assert "tool_result" in step_types
    assert "conclusion" in step_types

    # Check duration
    assert trace["duration_seconds"] >= 0


@pytest.mark.asyncio
async def test_metadata_propagation():
    """Test that input metadata is accessible."""
    llm = MockLLM(["FINAL ANSWER: Done"])

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[],
        max_reasoning_steps=5,
    )

    input_message = Message(
        role="user",
        content="Test",
        metadata={"session_id": "test-123", "user_id": "user-456"},
    )

    response = await agent.process(input_message)

    # Response should have its own metadata (trace)
    assert response.metadata is not None
    assert "reasoning_trace" in response.metadata
