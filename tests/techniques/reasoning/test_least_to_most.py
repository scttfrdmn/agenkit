"""Tests for Least-to-Most prompting technique."""

from typing import Any

import pytest

from agenkit import Message
from agenkit.techniques.reasoning import LeastToMost, Subproblem


class MockLLM:
    """Mock LLM for testing Least-to-Most."""

    def __init__(self, responses=None):
        """Initialize with predefined responses."""
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        prompt = "\n".join(m.content for m in messages)
        return Message(role="agent", content=self._respond(prompt))

    def _respond(self, prompt: str) -> str:
        """Return mock response based on call count."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return "Default response"


@pytest.mark.asyncio
async def test_ltm_basic():
    """Test basic Least-to-Most functionality."""
    llm = MockLLM(
        responses=["1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results", "12", "10", "22"]
    )

    ltm = LeastToMost(llm=llm)
    response = await ltm.process(Message(role="user", content="Calculate 3*4 + 2*5"))

    assert response.content == "22"
    assert response.metadata["technique"] == "least_to_most"
    assert response.metadata["num_subproblems"] == 3


@pytest.mark.asyncio
async def test_ltm_decomposition():
    """Test problem decomposition."""
    llm = MockLLM(
        responses=[
            "1. First step\n2. Second step\n3. Final step",
            "Solution 1",
            "Solution 2",
            "Final solution",
        ]
    )

    ltm = LeastToMost(llm=llm, max_subproblems=3)
    response = await ltm.process(Message(role="user", content="Complex problem"))

    metadata = response.metadata
    assert len(metadata["subproblems"]) == 3
    assert metadata["subproblems"][0] == "First step"
    assert metadata["subproblems"][1] == "Second step"
    assert metadata["subproblems"][2] == "Final step"


@pytest.mark.asyncio
async def test_ltm_sequential_solving():
    """Test that subproblems are solved sequentially."""
    llm = MockLLM(responses=["1. Step A\n2. Step B", "Answer A", "Answer B using A"])

    ltm = LeastToMost(llm=llm, compose_solutions=True)
    response = await ltm.process(Message(role="user", content="Problem"))

    solutions = response.metadata["subproblem_solutions"]
    assert len(solutions) == 2
    assert solutions[0] == "Answer A"
    assert solutions[1] == "Answer B using A"


@pytest.mark.asyncio
async def test_ltm_custom_decomposer():
    """Test with custom decomposer function."""

    def custom_decomposer(problem: str) -> list[str]:
        # Simple splitting on "then"
        return problem.split(" then ")

    llm = MockLLM(responses=["Result 1", "Result 2"])

    ltm = LeastToMost(llm=llm, decomposer=custom_decomposer)
    response = await ltm.process(Message(role="user", content="Do A then Do B"))

    assert response.metadata["num_subproblems"] == 2
    assert "Do A" in response.metadata["subproblems"][0]
    assert "Do B" in response.metadata["subproblems"][1]


@pytest.mark.asyncio
async def test_ltm_max_subproblems():
    """Test max_subproblems limiting."""
    llm = MockLLM(
        responses=[
            "1. One\n2. Two\n3. Three\n4. Four\n5. Five\n6. Six",  # 6 subproblems
            "1",
            "2",
            "3",  # Solutions (only 3 needed)
        ]
    )

    ltm = LeastToMost(llm=llm, max_subproblems=3)
    response = await ltm.process(Message(role="user", content="Problem"))

    # Should limit to 3 subproblems
    assert response.metadata["num_subproblems"] == 3


@pytest.mark.asyncio
async def test_ltm_composition_enabled():
    """Test solution composition (using previous solutions as context)."""
    call_history = []

    class TrackingLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            call_history.append(prompt)
            if "Break down" in prompt:
                return "1. Sub A\n2. Sub B"
            return "Solution"

    llm = TrackingLLM()
    ltm = LeastToMost(llm=llm, compose_solutions=True)

    await ltm.process(Message(role="user", content="Problem"))

    # Second solving call should include previous solution in context
    assert len(call_history) >= 3
    assert "Previous solution" in call_history[2]


@pytest.mark.asyncio
async def test_ltm_composition_disabled():
    """Test without solution composition."""
    call_history = []

    class TrackingLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            call_history.append(prompt)
            if "Break down" in prompt:
                return "1. Sub A\n2. Sub B"
            return "Solution"

    llm = TrackingLLM()
    ltm = LeastToMost(llm=llm, compose_solutions=False)

    await ltm.process(Message(role="user", content="Problem"))

    # Solving calls should NOT include previous solutions
    for call in call_history[1:]:  # Skip decomposition call
        assert "Previous solution" not in call


@pytest.mark.asyncio
async def test_ltm_atomic_problem():
    """Test handling of atomic (non-decomposable) problems."""
    llm = MockLLM(
        responses=[
            "",  # Empty decomposition response
            "Direct answer",
        ]
    )

    ltm = LeastToMost(llm=llm)
    response = await ltm.process(Message(role="user", content="Simple question"))

    # Should treat as single subproblem
    assert response.metadata["num_subproblems"] >= 1
    assert response.content == "Direct answer"


@pytest.mark.asyncio
async def test_ltm_metadata():
    """Test metadata completeness."""
    llm = MockLLM(responses=["1. Part 1\n2. Part 2", "Solution 1", "Solution 2"])

    ltm = LeastToMost(llm=llm)
    response = await ltm.process(Message(role="user", content="Problem"))

    metadata = response.metadata

    # Check all required metadata fields
    assert "technique" in metadata
    assert "num_subproblems" in metadata
    assert "subproblems" in metadata
    assert "subproblem_solutions" in metadata
    assert "compose_solutions" in metadata

    # Check types and lengths
    assert isinstance(metadata["subproblems"], list)
    assert isinstance(metadata["subproblem_solutions"], list)
    assert len(metadata["subproblems"]) == metadata["num_subproblems"]
    assert len(metadata["subproblem_solutions"]) == metadata["num_subproblems"]


@pytest.mark.asyncio
async def test_ltm_capabilities():
    """Test agent capabilities reporting."""
    llm = MockLLM()
    ltm = LeastToMost(llm=llm)

    caps = ltm.capabilities

    assert "reasoning" in caps
    assert "decomposition" in caps
    assert "least_to_most" in caps
    assert "compositional_reasoning" in caps


@pytest.mark.asyncio
async def test_ltm_name():
    """Test agent name."""
    llm = MockLLM()
    ltm = LeastToMost(llm=llm)

    assert ltm.name == "least_to_most"


@pytest.mark.asyncio
async def test_ltm_with_agent_interface():
    """Test LTM with LLM that uses Agent.process() interface."""

    class MockLLMAgent:
        async def process(self, message: Message) -> Message:
            if "Break down" in message.content:
                return Message(role="assistant", content="1. A\n2. B")
            return Message(role="assistant", content="Solution")

    llm = MockLLMAgent()
    ltm = LeastToMost(llm=llm)

    response = await ltm.process(Message(role="user", content="Problem"))

    assert response.content
    assert response.metadata["num_subproblems"] >= 1


@pytest.mark.asyncio
async def test_subproblem_dataclass():
    """Test Subproblem dataclass."""
    sp = Subproblem(content="Test problem", difficulty=2)

    assert sp.content == "Test problem"
    assert sp.difficulty == 2
    assert sp.dependencies == []


@pytest.mark.asyncio
async def test_ltm_numbering_formats():
    """Test parsing various numbering formats in decomposition."""
    llm = MockLLM(
        responses=[
            "1) First\n2) Second\n3) Third",  # Parentheses
            "1",
            "2",
            "3",
        ]
    )

    ltm = LeastToMost(llm=llm)
    response = await ltm.process(Message(role="user", content="Problem"))

    subproblems = response.metadata["subproblems"]
    assert len(subproblems) == 3
    assert "First" in subproblems[0]
    assert "Second" in subproblems[1]
    assert "Third" in subproblems[2]
