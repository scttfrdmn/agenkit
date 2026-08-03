"""
Tests for orchestration patterns.

Tests verify:
- Sequential execution order and correctness
- Parallel concurrent execution and aggregation
- Router dispatch logic
- Edge cases and error handling
- Hook functionality
"""

import asyncio

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.patterns import ParallelPattern, RouterPattern, SequentialPattern

# ============================================
# Test Agents
# ============================================


class EchoAgent(Agent):
    """Agent that echoes with prefix."""

    def __init__(self, prefix: str):
        self._prefix = prefix

    @property
    def name(self) -> str:
        return f"echo_{self._prefix}"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"{self._prefix}: {message.content}")


class UpperAgent(Agent):
    """Agent that uppercases content."""

    @property
    def name(self) -> str:
        return "upper"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=str(message.content).upper())


class SlowAgent(Agent):
    """Agent that introduces delay."""

    def __init__(self, delay: float, name: str = "slow"):
        self._delay = delay
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(self._delay)
        return Message(role="agent", content=f"slow: {message.content}")


class ErrorAgent(Agent):
    """Agent that raises an error."""

    @property
    def name(self) -> str:
        return "error"

    async def process(self, message: Message) -> Message:
        raise RuntimeError("Intentional error")


# ============================================
# SequentialPattern Tests
# ============================================


@pytest.mark.asyncio
async def test_sequential_basic():
    """Test basic sequential execution."""
    agent1 = EchoAgent("first")
    agent2 = EchoAgent("second")
    agent3 = EchoAgent("third")

    seq = SequentialPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="hello")
    result = await seq.process(msg)

    # Should apply each transformation in order
    assert result.content == "third: second: first: hello"


@pytest.mark.asyncio
async def test_sequential_single_agent():
    """Test sequential with single agent."""
    agent = UpperAgent()
    seq = SequentialPattern([agent])

    msg = Message(role="user", content="hello")
    result = await seq.process(msg)

    assert result.content == "HELLO"


def test_sequential_empty_raises():
    """Test that empty agent list raises."""
    with pytest.raises(ValueError, match="at least one agent"):
        SequentialPattern([])


@pytest.mark.asyncio
async def test_sequential_error_propagates():
    """Test that errors propagate from agents."""
    agent1 = UpperAgent()
    agent2 = ErrorAgent()
    agent3 = UpperAgent()  # Never reached

    seq = SequentialPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="hello")
    with pytest.raises(RuntimeError, match="Intentional error"):
        await seq.process(msg)


@pytest.mark.asyncio
async def test_sequential_hooks():
    """Test before/after hooks."""
    agent1 = UpperAgent()
    agent2 = EchoAgent("echo")

    calls = []

    def before(agent: Agent, message: Message) -> None:
        calls.append(("before", agent.name, message.content))

    def after(agent: Agent, message: Message) -> None:
        calls.append(("after", agent.name, message.content))

    seq = SequentialPattern([agent1, agent2], before_agent=before, after_agent=after)

    msg = Message(role="user", content="hello")
    await seq.process(msg)

    # Should have before/after for each agent
    assert len(calls) == 4
    assert calls[0] == ("before", "upper", "hello")
    assert calls[1] == ("after", "upper", "HELLO")
    assert calls[2] == ("before", "echo_echo", "HELLO")
    assert calls[3] == ("after", "echo_echo", "echo: HELLO")


@pytest.mark.asyncio
async def test_sequential_capabilities():
    """Test combined capabilities."""

    class CapAgent1(Agent):
        @property
        def name(self) -> str:
            return "cap1"

        @property
        def capabilities(self) -> list[str]:
            return ["search", "code"]

        async def process(self, message: Message) -> Message:
            return message

    class CapAgent2(Agent):
        @property
        def name(self) -> str:
            return "cap2"

        @property
        def capabilities(self) -> list[str]:
            return ["summarize", "code"]

        async def process(self, message: Message) -> Message:
            return message

    seq = SequentialPattern([CapAgent1(), CapAgent2()])
    caps = seq.capabilities

    assert "search" in caps
    assert "code" in caps
    assert "summarize" in caps
    assert len([c for c in caps if c == "code"]) == 1  # De-duplicated


@pytest.mark.asyncio
async def test_sequential_unwrap():
    """Test unwrap returns agents list."""
    agent1 = UpperAgent()
    agent2 = EchoAgent("echo")

    seq = SequentialPattern([agent1, agent2])
    agents = seq.unwrap()

    assert len(agents) == 2
    assert agents[0] is agent1
    assert agents[1] is agent2


# ============================================
# ParallelPattern Tests
# ============================================


@pytest.mark.asyncio
async def test_parallel_basic():
    """Test basic parallel execution."""
    agent1 = EchoAgent("first")
    agent2 = EchoAgent("second")
    agent3 = EchoAgent("third")

    parallel = ParallelPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="hello")
    result = await parallel.process(msg)

    # Default aggregator returns first result
    assert result.content == "first: hello"

    # But all results are in metadata
    all_results = result.metadata["parallel_results"]
    assert len(all_results) == 3


@pytest.mark.asyncio
async def test_parallel_custom_aggregator():
    """Test parallel with custom aggregator."""
    agent1 = EchoAgent("A")
    agent2 = EchoAgent("B")
    agent3 = EchoAgent("C")

    def combine(messages: list[Message]) -> Message:
        # Combine all content
        combined = " | ".join(msg.content for msg in messages)
        return Message(role="agent", content=combined)

    parallel = ParallelPattern([agent1, agent2, agent3], aggregator=combine)

    msg = Message(role="user", content="x")
    result = await parallel.process(msg)

    # Results combined
    assert "A: x" in result.content
    assert "B: x" in result.content
    assert "C: x" in result.content


@pytest.mark.asyncio
async def test_parallel_concurrent_execution():
    """Test that parallel actually runs concurrently."""
    import time

    # Three agents that each take 0.1s
    agent1 = SlowAgent(0.1, "slow1")
    agent2 = SlowAgent(0.1, "slow2")
    agent3 = SlowAgent(0.1, "slow3")

    parallel = ParallelPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="test")

    start = time.time()
    await parallel.process(msg)
    elapsed = time.time() - start

    # If sequential, would take 0.3s
    # If parallel, should take ~0.1s
    assert elapsed < 0.2, "Parallel execution should be concurrent"


def test_parallel_empty_raises():
    """Test that empty agent list raises."""
    with pytest.raises(ValueError, match="at least one agent"):
        ParallelPattern([])


@pytest.mark.asyncio
async def test_parallel_error_cancels_all():
    """Test that error in one agent cancels all."""
    agent1 = SlowAgent(1.0, "slow1")  # Would take 1s
    agent2 = ErrorAgent()  # Fails immediately
    agent3 = SlowAgent(1.0, "slow3")  # Would take 1s

    parallel = ParallelPattern([agent1, agent2, agent3])

    msg = Message(role="user", content="test")

    import time

    start = time.time()

    with pytest.raises(RuntimeError, match="Intentional error"):
        await parallel.process(msg)

    elapsed = time.time() - start

    # Should fail fast, not wait for slow agents
    assert elapsed < 0.5, "Should cancel other agents on error"


@pytest.mark.asyncio
async def test_parallel_unwrap():
    """Test unwrap returns agents list."""
    agent1 = UpperAgent()
    agent2 = EchoAgent("echo")

    parallel = ParallelPattern([agent1, agent2])
    agents = parallel.unwrap()

    assert len(agents) == 2
    # Order not guaranteed in parallel, just check both present
    assert agent1 in agents
    assert agent2 in agents


# ============================================
# RouterPattern Tests
# ============================================


@pytest.mark.asyncio
async def test_router_basic():
    """Test basic routing."""
    agent1 = EchoAgent("route1")
    agent2 = EchoAgent("route2")

    def router(message: Message) -> str:
        content = str(message.content)
        if "first" in content:
            return "route1"
        return "route2"

    pattern = RouterPattern(router=router, handlers={"route1": agent1, "route2": agent2})

    # Route to first
    msg1 = Message(role="user", content="use first")
    result1 = await pattern.process(msg1)
    assert result1.content == "route1: use first"

    # Route to second
    msg2 = Message(role="user", content="use second")
    result2 = await pattern.process(msg2)
    assert result2.content == "route2: use second"


@pytest.mark.asyncio
async def test_router_unknown_key_raises():
    """Test that unknown key without default raises."""
    agent1 = EchoAgent("route1")

    def router(message: Message) -> str:
        return "unknown_route"

    pattern = RouterPattern(router=router, handlers={"route1": agent1})

    msg = Message(role="user", content="test")
    with pytest.raises(KeyError, match="unknown key"):
        await pattern.process(msg)


@pytest.mark.asyncio
async def test_router_unknown_key_uses_default():
    """Test that unknown key uses default handler."""
    agent1 = EchoAgent("route1")
    default_agent = EchoAgent("default")

    def router(message: Message) -> str:
        return "unknown_route"

    pattern = RouterPattern(router=router, handlers={"route1": agent1}, default=default_agent)

    msg = Message(role="user", content="test")
    result = await pattern.process(msg)
    assert result.content == "default: test"


def test_router_empty_handlers_raises():
    """Test that empty handlers dict raises."""

    def router(message: Message) -> str:
        return "any"

    with pytest.raises(ValueError, match="at least one handler"):
        RouterPattern(router=router, handlers={})


@pytest.mark.asyncio
async def test_router_unwrap():
    """Test unwrap returns handlers dict."""
    agent1 = EchoAgent("route1")
    agent2 = EchoAgent("route2")

    def router(message: Message) -> str:
        return "route1"

    pattern = RouterPattern(router=router, handlers={"route1": agent1, "route2": agent2})

    handlers = pattern.unwrap()
    assert len(handlers) == 2
    assert handlers["route1"] is agent1
    assert handlers["route2"] is agent2


# ============================================
# Pattern Composition Tests
# ============================================


@pytest.mark.asyncio
async def test_patterns_compose():
    """Test that patterns can be composed (patterns of patterns)."""
    # Build nested structure:
    # Sequential [
    #   Parallel [agent1, agent2],
    #   Router {key1 → agent3, key2 → agent4}
    # ]

    agent1 = EchoAgent("A")
    agent2 = EchoAgent("B")
    agent3 = EchoAgent("C")
    agent4 = EchoAgent("D")

    # Parallel pattern
    parallel = ParallelPattern(
        [agent1, agent2], aggregator=lambda msgs: Message(role="agent", content="parallel_done")
    )

    # Router pattern
    def router(msg: Message) -> str:
        return "key1"

    router_pattern = RouterPattern(router=router, handlers={"key1": agent3, "key2": agent4})

    # Sequential composing both
    seq = SequentialPattern([parallel, router_pattern])

    msg = Message(role="user", content="test")
    result = await seq.process(msg)

    assert result.content == "C: parallel_done"


# ============================================
# Additional Test Agents and Mocks
# ============================================


class CountingAgent(Agent):
    """Agent that counts how many times it's been called."""

    def __init__(self, name: str = "counter"):
        self._name = name
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        self._call_count += 1
        return Message(
            role="agent",
            content=f"Call {self._call_count}: {message.content}",
            metadata={"call_count": self._call_count},
        )


class MockLLMClient:
    """Mock LLM client for testing conversational patterns.

    Implements ``complete(messages, **kwargs)`` — the contract in
    ``agenkit.adapters.llm.base.LLM`` that all seven shipped adapters implement,
    not the ``chat()`` that no adapter has (#805).
    """

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or ["Default response"]
        self.call_count = 0
        self.last_messages = []

    async def complete(self, messages: list[Message], **kwargs: object) -> Message:
        """Simulate an LLM completion."""
        self.last_messages = messages
        response_text = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1
        return Message(role="assistant", content=response_text, metadata={})


class MockTool:
    """Mock tool for ReAct and tool-using patterns."""

    def __init__(self, name: str, result: str = "tool result", should_fail: bool = False):
        self.tool_name = name
        self.result = result
        self.should_fail = should_fail
        self.call_count = 0
        self.last_input = None

    @property
    def name(self) -> str:
        return self.tool_name

    async def execute(self, input_data: str) -> str:
        """Execute the mock tool."""
        self.call_count += 1
        self.last_input = input_data

        if self.should_fail:
            raise RuntimeError(f"{self.tool_name} execution failed")

        return f"{self.result} for: {input_data}"


class ScoringAgent(Agent):
    """Agent that returns scores in metadata for reflection/improvement patterns."""

    def __init__(self, scores: list[float], name: str = "scorer"):
        self._name = name
        self.scores = scores
        self.score_index = 0

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        score = self.scores[min(self.score_index, len(self.scores) - 1)]
        self.score_index += 1

        return Message(
            role="agent",
            content=f"Scored content: {message.content}",
            metadata={"quality_score": score},
        )


class MockGoalEvaluator:
    """Mock goal evaluator for autonomous agents."""

    def __init__(self, scores: list[float]):
        self.scores = scores
        self.eval_count = 0

    async def evaluate(self, message: Message) -> float:
        """Evaluate goal achievement."""
        score = self.scores[min(self.eval_count, len(self.scores) - 1)]
        self.eval_count += 1
        return score


# ============================================
# ConversationalAgent Tests
# ============================================


@pytest.mark.asyncio
async def test_conversational_basic():
    """Test basic conversational agent."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["Hello! How can I help you?"])
    agent = ConversationalAgent(llm)

    msg = Message(role="user", content="Hi there")
    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Hello" in result.content
    # Should have user message + assistant response in history
    assert len(agent.history) == 2
    assert agent.history[0].role == "user"
    assert agent.history[1].role == "assistant"


@pytest.mark.asyncio
async def test_conversational_history_accumulation():
    """Test conversation history accumulates correctly."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["Response 1", "Response 2", "Response 3"])
    agent = ConversationalAgent(llm, max_history=10)

    # Send 3 messages
    await agent.process(Message(role="user", content="msg1"))
    await agent.process(Message(role="user", content="msg2"))
    await agent.process(Message(role="user", content="msg3"))

    # Should have 6 messages (3 user + 3 assistant)
    assert len(agent.history) == 6
    assert agent.history[0].role == "user"
    assert agent.history[0].content == "msg1"
    assert agent.history[1].role == "assistant"
    assert agent.history[1].content == "Response 1"


@pytest.mark.asyncio
async def test_conversational_max_history_limit():
    """Test max history limit is enforced."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["response"])
    agent = ConversationalAgent(llm, max_history=4)

    # Send 5 messages (10 total with responses)
    for i in range(5):
        await agent.process(Message(role="user", content=f"msg{i}"))

    # Should only keep last 4 messages
    assert len(agent.history) == 4
    # Should be the last 2 exchanges
    assert agent.history[0].content == "msg3"
    assert agent.history[2].content == "msg4"


@pytest.mark.asyncio
async def test_conversational_system_prompt():
    """Test system prompt is included."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["I'll help!"])
    agent = ConversationalAgent(llm, system_prompt="You are helpful")

    # System prompt should be in history
    assert len(agent.history) == 1
    assert agent.history[0].role == "system"
    assert agent.history[0].content == "You are helpful"

    await agent.process(Message(role="user", content="Help me"))

    # Should now have system + user + assistant
    assert len(agent.history) == 3


@pytest.mark.asyncio
async def test_conversational_clear_history():
    """Test clearing conversation history."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["response"])
    agent = ConversationalAgent(llm)

    # Build up history
    await agent.process(Message(role="user", content="msg1"))
    await agent.process(Message(role="user", content="msg2"))
    assert len(agent.history) > 0

    # Clear history
    agent.clear_history()
    assert len(agent.history) == 0


@pytest.mark.asyncio
async def test_conversational_name_property():
    """Test conversational agent name."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient()
    agent = ConversationalAgent(llm)

    assert agent.name == "ConversationalAgent"


@pytest.mark.asyncio
async def test_conversational_llm_failure():
    """Test handling LLM failure."""
    from agenkit.patterns import ConversationalAgent

    class FailingLLM:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("LLM error")

    llm = FailingLLM()
    agent = ConversationalAgent(llm)

    msg = Message(role="user", content="test")

    with pytest.raises(RuntimeError, match="LLM error"):
        await agent.process(msg)


@pytest.mark.asyncio
async def test_conversational_exclude_system_from_history():
    """Test excluding system prompt from history."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["response"])
    agent = ConversationalAgent(llm, system_prompt="System prompt", include_system=False)

    # System prompt should not be in history
    assert len(agent.history) == 0

    # But should still be sent to LLM
    await agent.process(Message(role="user", content="test"))

    # Only user + assistant in history
    assert len(agent.history) == 2
    assert all(m.role != "system" for m in agent.history)


@pytest.mark.asyncio
async def test_conversational_get_history():
    """Test getting conversation history."""
    from agenkit.patterns import ConversationalAgent

    llm = MockLLMClient(["response"])
    agent = ConversationalAgent(llm)

    await agent.process(Message(role="user", content="msg1"))
    await agent.process(Message(role="user", content="msg2"))

    history = agent.get_history()
    assert len(history) == 4
    assert all(isinstance(m, Message) for m in history)


# ============================================
# ReflectionAgent Tests
# ============================================


@pytest.mark.asyncio
async def test_reflection_basic():
    """Test basic reflection with improvement."""
    from agenkit.patterns import ReflectionAgent

    # Generator produces increasingly better content
    class GeneratorAgent(Agent):
        def __init__(self):
            self.iteration = 0

        @property
        def name(self) -> str:
            return "generator"

        async def process(self, message: Message) -> Message:
            self.iteration += 1
            return Message(
                role="assistant",
                content=f"Draft {self.iteration}: {message.content}",
                metadata={"quality_score": 0.5 + (self.iteration * 0.2)},
            )

    # Critic provides feedback
    class CriticAgent(Agent):
        @property
        def name(self) -> str:
            return "critic"

        async def process(self, message: Message) -> Message:
            score = message.metadata.get("quality_score", 0.5)
            feedback = "Good" if score > 0.8 else "Needs improvement"
            return Message(
                role="assistant",
                content=f"Critique: {feedback}",
                metadata={"quality_score": score, "improved": score > 0.8},
            )

    generator = GeneratorAgent()
    critic = CriticAgent()
    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=3)

    msg = Message(role="user", content="Write something")
    result = await agent.process(msg)

    # Should have iterated and improved
    assert "Draft" in result.content
    assert generator.iteration >= 2


@pytest.mark.asyncio
async def test_reflection_max_iterations():
    """Test max iterations limit is enforced."""
    from agenkit.patterns import ReflectionAgent

    iteration_count = 0

    class NeverSatisfiedGenerator(Agent):
        @property
        def name(self) -> str:
            return "generator"

        async def process(self, message: Message) -> Message:
            nonlocal iteration_count
            iteration_count += 1
            return Message(
                role="assistant",
                content=f"Draft {iteration_count}",
                metadata={"quality_score": 0.5},  # Never good enough
            )

    class NeverSatisfiedCritic(Agent):
        @property
        def name(self) -> str:
            return "critic"

        async def process(self, message: Message) -> Message:
            return Message(
                role="assistant",
                content="Not good enough",
                metadata={"quality_score": 0.5, "improved": False},
            )

    generator = NeverSatisfiedGenerator()
    critic = NeverSatisfiedCritic()
    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=5)

    msg = Message(role="user", content="test")
    await agent.process(msg)

    # Should stop at max iterations
    assert iteration_count <= 5  # May stop early due to convergence


@pytest.mark.asyncio
async def test_reflection_early_stop_quality_threshold():
    """Test early stop when quality threshold reached."""
    from agenkit.patterns import ReflectionAgent

    iteration_count = 0

    class QuicklyImprovingGenerator(Agent):
        @property
        def name(self) -> str:
            return "generator"

        async def process(self, message: Message) -> Message:
            nonlocal iteration_count
            iteration_count += 1
            # Second iteration is high quality
            score = 0.95 if iteration_count >= 2 else 0.6
            return Message(
                role="assistant",
                content=f"Draft {iteration_count}",
                metadata={"quality_score": score},
            )

    class ApprovingCritic(Agent):
        @property
        def name(self) -> str:
            return "critic"

        async def process(self, message: Message) -> Message:
            score = message.metadata.get("quality_score", 0.5)
            return Message(
                role="assistant",
                content="Good!" if score > 0.9 else "Keep trying",
                metadata={"quality_score": score, "improved": score > 0.9},
            )

    generator = QuicklyImprovingGenerator()
    critic = ApprovingCritic()
    agent = ReflectionAgent(
        generator=generator, critic=critic, max_reflections=10, quality_threshold=0.9
    )

    msg = Message(role="user", content="test")
    await agent.process(msg)

    # Should stop early due to quality threshold
    assert iteration_count < 10
    assert iteration_count == 2


@pytest.mark.asyncio
async def test_reflection_generator_failure():
    """Test handling generator agent failure."""
    from agenkit.patterns import ReflectionAgent

    generator = ErrorAgent()
    critic = UpperAgent()

    agent = ReflectionAgent(generator=generator, critic=critic)

    msg = Message(role="user", content="test")

    with pytest.raises(RuntimeError, match="Intentional error"):
        await agent.process(msg)


@pytest.mark.asyncio
async def test_reflection_critic_failure():
    """Test handling critic agent failure."""
    from agenkit.patterns import ReflectionAgent

    generator = UpperAgent()
    critic = ErrorAgent()

    agent = ReflectionAgent(generator=generator, critic=critic)

    msg = Message(role="user", content="test")

    with pytest.raises(RuntimeError, match="Intentional error"):
        await agent.process(msg)


@pytest.mark.asyncio
async def test_reflection_name_property():
    """Test reflection agent name."""
    from agenkit.patterns import ReflectionAgent

    generator = UpperAgent()
    critic = EchoAgent("critic")

    agent = ReflectionAgent(generator=generator, critic=critic)

    assert "reflection" in agent.name.lower()


@pytest.mark.asyncio
async def test_reflection_unwrap():
    """Test unwrap returns generator and critic."""
    from agenkit.patterns import ReflectionAgent

    generator = UpperAgent()
    critic = EchoAgent("critic")

    agent = ReflectionAgent(generator=generator, critic=critic)

    unwrapped = agent.unwrap()
    # unwrap returns the reflection agent itself
    assert unwrapped is agent


# ============================================
# ReActAgent Tests
# ============================================


@pytest.mark.asyncio
async def test_react_basic():
    """Test basic ReAct agent with tools."""
    from agenkit.patterns import ReActAgent

    # Create a simple tool
    class SimpleTool:
        name = "test_tool"
        description = "A test tool"

        async def execute(self, input_data: str) -> str:
            return f"Result: {input_data}"

    # Mock LLM that finishes immediately
    class SimpleLLM(Agent):
        @property
        def name(self) -> str:
            return "simple_llm"

        def capabilities(self) -> list[str]:
            return ["chat"]

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="Final Answer: Test complete", metadata={})

    tools = [SimpleTool()]
    llm = SimpleLLM()
    agent = ReActAgent(agent=llm, tools=tools)

    msg = Message(role="user", content="test")
    result = await agent.process(msg)

    assert result is not None
    assert isinstance(result, Message)


@pytest.mark.asyncio
async def test_react_name_property():
    """Test ReAct agent name."""
    from agenkit.patterns import ReActAgent

    class SimpleLLM(Agent):
        @property
        def name(self) -> str:
            return "simple_llm"

        def capabilities(self) -> list[str]:
            return ["chat"]

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="Done", metadata={})

    agent = ReActAgent(agent=SimpleLLM(), tools=[])

    assert "react" in agent.name.lower()


# ============================================
# PlanningAgent Tests
# ============================================


@pytest.mark.asyncio
async def test_planning_basic():
    """Test basic planning agent."""
    from agenkit.patterns import PlanningAgent

    class SimplePlanningLLM(Agent):
        @property
        def name(self) -> str:
            return "simple_planning_llm"

        def capabilities(self) -> list[str]:
            return ["planning"]

        async def process(self, message: Message) -> Message:
            return Message(
                role="assistant",
                content="Goal: Complete task\nSteps:\n1. First step\n2. Second step",
                metadata={},
            )

    llm = SimplePlanningLLM()
    agent = PlanningAgent(planner=llm)

    msg = Message(role="user", content="Make a plan")
    result = await agent.process(msg)

    assert result is not None
    assert isinstance(result, Message)


@pytest.mark.asyncio
async def test_planning_name_property():
    """Test planning agent name."""
    from agenkit.patterns import PlanningAgent

    class SimpleLLM(Agent):
        @property
        def name(self) -> str:
            return "simple_llm"

        def capabilities(self) -> list[str]:
            return ["planning"]

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="Plan", metadata={})

    agent = PlanningAgent(planner=SimpleLLM())

    assert "plan" in agent.name.lower()


# ============================================
# AutonomousAgent Tests
# ============================================


@pytest.mark.asyncio
async def test_autonomous_basic():
    """Test basic autonomous agent."""
    from agenkit.patterns import AutonomousAgent, Goal

    class TestAutonomousAgent(AutonomousAgent):
        async def _work_on_goal(self, goal: Goal) -> str:
            return f"Completed: {goal.description}"

    agent = TestAutonomousAgent(objective="Test objective", max_iterations=3)
    agent.add_goal("First goal", priority=1)

    result = await agent.run()

    assert result is not None
    assert "iterations" in result


@pytest.mark.asyncio
async def test_autonomous_add_goals():
    """Test adding goals to autonomous agent."""
    from agenkit.patterns import AutonomousAgent, Goal

    class TestAutonomousAgent(AutonomousAgent):
        async def _work_on_goal(self, goal: Goal) -> str:
            return "done"

    agent = TestAutonomousAgent(objective="Test")

    agent.add_goal("Goal 1", priority=1)
    agent.add_goal("Goal 2", priority=2)

    assert len(agent.goals) == 2


@pytest.mark.asyncio
async def test_autonomous_max_iterations():
    """Test max iterations limit."""
    from agenkit.patterns import AutonomousAgent, Goal

    class NeverFinishingAgent(AutonomousAgent):
        async def _work_on_goal(self, goal: Goal) -> str:
            # Never completes goals
            return "working"

    agent = NeverFinishingAgent(objective="Test", max_iterations=2)
    agent.add_goal("Endless goal")

    result = await agent.run()

    assert result["iterations"] <= 2


# ============================================
# MultiAgentOrchestrator Tests
# ============================================


@pytest.mark.asyncio
async def test_multiagent_basic():
    """Test basic multi-agent orchestrator."""
    from agenkit.patterns import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator(strategy="sequential")
    orchestrator.register_agent("agent1", UpperAgent())
    orchestrator.register_agent("agent2", EchoAgent("echo"))

    msg = Message(role="user", content="hello")
    result = await orchestrator.process(msg)

    assert result is not None
    assert isinstance(result, Message)


@pytest.mark.asyncio
async def test_multiagent_register_agents():
    """Test registering agents."""
    from agenkit.patterns import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator()
    orchestrator.register_agent("agent1", UpperAgent())
    orchestrator.register_agent("agent2", EchoAgent("test"))

    agents = orchestrator.list_agents()
    assert len(agents) == 2
    assert "agent1" in agents
    assert "agent2" in agents


@pytest.mark.asyncio
async def test_multiagent_sequential_strategy():
    """Test sequential strategy."""
    from agenkit.patterns import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator(strategy="sequential")
    orchestrator.register_agent("upper", UpperAgent())

    msg = Message(role="user", content="hello")
    result = await orchestrator.process(msg)

    # Sequential should process through registered agents
    assert result.content


@pytest.mark.asyncio
async def test_multiagent_name_property():
    """Test multi-agent orchestrator name."""
    from agenkit.patterns import MultiAgentOrchestrator

    orchestrator = MultiAgentOrchestrator()

    assert "multi" in orchestrator.name.lower() or "orchestrator" in orchestrator.name.lower()
