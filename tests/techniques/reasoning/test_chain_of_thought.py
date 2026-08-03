"""Tests for Chain-of-Thought reasoning technique."""

from typing import Any

import pytest

from agenkit import Message
from agenkit.techniques.reasoning import ChainOfThought


class MockLLM:
    """Mock LLM for testing CoT."""

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        prompt = "\n".join(m.content for m in messages)
        return Message(role="agent", content=self._respond(prompt))

    def _respond(self, prompt: str) -> str:
        """Return mock response based on prompt."""
        if "step by step" in prompt.lower() or "solve" in prompt.lower():
            # Return numbered steps format
            return """1. First, multiply 15 by 20 to get 300
2. Then, multiply 15 by 4 to get 60
3. Add 300 + 60 = 360
Therefore, 15 * 24 = 360"""
        return "Response without steps"


class MockLLMWithBullets:
    """Mock LLM that returns bullet-point format."""

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        prompt = "\n".join(m.content for m in messages)
        return Message(role="agent", content=self._respond(prompt))

    def _respond(self, prompt: str) -> str:
        """Return bullet-point formatted response."""
        return """- First step is to analyze the problem
- Second step is to break it down
- Third step is to solve each part
- Finally, combine the results"""


class MockLLMAgent:
    """Mock LLM that uses Agent.process() interface."""

    async def process(self, message: Message) -> Message:
        """Return message with mock response."""
        return Message(
            role="assistant",
            content="""1. Analyze the input
2. Process the data
3. Return the result""",
        )


@pytest.mark.asyncio
async def test_cot_basic():
    """Test basic CoT functionality."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="What is 15 * 24?"))

    # Check response content
    assert "360" in response.content
    assert "First" in response.content

    # Check metadata
    assert "reasoning_steps" in response.metadata
    assert "num_steps" in response.metadata
    assert response.metadata["technique"] == "chain_of_thought"

    # Check steps were parsed
    steps = response.metadata["reasoning_steps"]
    assert len(steps) >= 3
    assert "multiply 15 by 20" in steps[0].lower()


@pytest.mark.asyncio
async def test_cot_custom_template():
    """Test custom prompt template."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm, prompt_template="Solve carefully:\n{query}")

    response = await cot.process(Message(role="user", content="Calculate something"))

    assert response is not None
    assert response.content
    assert "reasoning_steps" in response.metadata


@pytest.mark.asyncio
async def test_cot_no_parsing():
    """Test CoT without step parsing."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm, parse_steps=False)

    response = await cot.process(Message(role="user", content="Question"))

    # Should not have reasoning_steps when parsing disabled
    assert "reasoning_steps" not in response.metadata
    assert "num_steps" not in response.metadata

    # But should still have technique marker
    assert response.metadata["technique"] == "chain_of_thought"


@pytest.mark.asyncio
async def test_cot_max_steps():
    """Test max_steps limiting."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm, max_steps=2)

    response = await cot.process(Message(role="user", content="What is 15 * 24?"))

    # Should limit to 2 steps even though response has more
    steps = response.metadata["reasoning_steps"]
    assert len(steps) == 2
    assert response.metadata["num_steps"] == 2


@pytest.mark.asyncio
async def test_cot_bullet_points():
    """Test parsing bullet-point formatted steps."""
    llm = MockLLMWithBullets()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="Question"))

    steps = response.metadata["reasoning_steps"]
    assert len(steps) == 4
    assert "analyze the problem" in steps[0].lower()
    assert "finally" in steps[3].lower()


@pytest.mark.asyncio
async def test_cot_with_agent_interface():
    """Test CoT with LLM that uses Agent.process() interface."""
    llm = MockLLMAgent()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="Question"))

    assert response.content
    assert "reasoning_steps" in response.metadata
    steps = response.metadata["reasoning_steps"]
    assert len(steps) == 3


@pytest.mark.asyncio
async def test_cot_delimiter_fallback():
    """Test fallback to delimiter-based parsing."""

    class SimpleLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            # Response without numbers or bullets
            return "First thought\nSecond thought\nThird thought"

    llm = SimpleLLM()
    cot = ChainOfThought(llm=llm, step_delimiter="\n")

    response = await cot.process(Message(role="user", content="Question"))

    steps = response.metadata["reasoning_steps"]
    assert len(steps) == 3
    assert "First thought" in steps
    assert "Second thought" in steps


@pytest.mark.asyncio
async def test_cot_empty_response():
    """Test handling of empty/whitespace response."""

    class EmptyLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            return "   \n  \n   "

    llm = EmptyLLM()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="Question"))

    # Should handle gracefully
    assert response.metadata["reasoning_steps"] == []
    assert response.metadata["num_steps"] == 0


@pytest.mark.asyncio
async def test_cot_single_step():
    """Test response with only one step."""

    class SingleStepLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            return "1. This is the only step"

    llm = SingleStepLLM()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="Question"))

    # Should still parse single step (falls back to delimiter)
    assert len(response.metadata["reasoning_steps"]) >= 1


@pytest.mark.asyncio
async def test_cot_capabilities():
    """Test agent capabilities reporting."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm)

    caps = cot.capabilities

    assert "reasoning" in caps
    assert "step_by_step" in caps
    assert "chain_of_thought" in caps
    assert "explainable_ai" in caps


@pytest.mark.asyncio
async def test_cot_name():
    """Test agent name."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm)

    assert cot.name == "chain_of_thought"


@pytest.mark.asyncio
async def test_cot_with_parentheses_numbers():
    """Test parsing numbered steps with parentheses (1) 2) 3))."""

    class ParenLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            return """1) First step with parenthesis
2) Second step
3) Third step"""

    llm = ParenLLM()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="Question"))

    steps = response.metadata["reasoning_steps"]
    assert len(steps) == 3
    assert "First step" in steps[0]


@pytest.mark.asyncio
async def test_cot_mixed_format():
    """Test response with mixed formatting."""

    class MixedLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            return """Let me think about this:
1. First numbered step
2. Second numbered step
Some text in between
3. Third numbered step
Final conclusion"""

    llm = MixedLLM()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(role="user", content="Question"))

    # Should extract numbered steps
    steps = response.metadata["reasoning_steps"]
    assert len(steps) == 3


@pytest.mark.asyncio
async def test_cot_invalid_llm():
    """Test error handling for LLM without required methods."""

    class InvalidLLM:
        """LLM without complete(), process(), or chat()."""

        pass

    llm = InvalidLLM()
    cot = ChainOfThought(llm=llm)

    # The error must name every contract the caller could implement. Since #805
    # that is three, not two — dispatch is shared with the patterns, which also
    # accept the deprecated chat().
    with pytest.raises(
        AttributeError, match=r"complete\(messages.*process\(message\).*chat\(messages\)"
    ):
        await cot.process(Message(role="user", content="Question"))


@pytest.mark.asyncio
async def test_cot_template_with_missing_key():
    """Test error handling for template with undefined placeholder."""

    class SimpleLLM:
        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            return "Response"

    llm = SimpleLLM()
    # Template has {missing} which we don't provide in format()
    cot = ChainOfThought(llm=llm, prompt_template="Question: {missing}")

    with pytest.raises(KeyError):
        await cot.process(Message(role="user", content="Question"))
