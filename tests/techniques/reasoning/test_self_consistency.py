"""Tests for Self-Consistency reasoning technique."""

from typing import Any

import pytest

from agenkit import Message
from agenkit.techniques.reasoning import SelfConsistency


class MockAgent:
    """Mock agent for testing Self-Consistency."""

    def __init__(self, responses=None):
        """
        Initialize with predefined responses.

        Args:
            responses: List of responses to cycle through
        """
        self.responses = responses or [
            "The answer is 42",
            "Therefore, 42",
            "The answer is 42",
            "Thus, 42",
            "So, 42",
        ]
        self.call_count = 0
        self.name = "mock_agent"

    async def process(self, message: Message) -> Message:
        """Return mock response based on call count."""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return Message(role="assistant", content=response)


@pytest.mark.asyncio
async def test_sc_basic():
    """Test basic Self-Consistency functionality."""
    agent = MockAgent()
    sc = SelfConsistency(agent=agent, num_samples=5)

    response = await sc.process(Message(role="user", content="Test query"))

    # Check response
    assert response.content == "42"  # Consensus answer
    assert response.metadata["technique"] == "self_consistency"
    assert response.metadata["num_samples"] == 5
    assert "consistency_score" in response.metadata


@pytest.mark.asyncio
async def test_sc_majority_voting():
    """Test majority voting strategy."""
    agent = MockAgent(
        responses=[
            "The answer is A",
            "The answer is B",
            "The answer is A",
            "The answer is A",
            "The answer is B",
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=5, voting_strategy="majority")

    response = await sc.process(Message(role="user", content="Test query"))

    # "A" appears 3 times, "B" appears 2 times
    assert response.content == "A"
    assert response.metadata["consistency_score"] == 0.6  # 3/5
    assert response.metadata["voting_strategy"] == "majority"


@pytest.mark.asyncio
async def test_sc_weighted_voting():
    """Test weighted voting strategy."""
    agent = MockAgent(
        responses=[
            "Short answer: A",  # ~15 chars
            "Very detailed and comprehensive explanation leading to answer: B",  # ~65 chars
            "Answer: A",  # ~9 chars
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=3, voting_strategy="weighted")

    response = await sc.process(Message(role="user", content="Test query"))

    # B has highest weight (longer response)
    assert response.content == "B"
    assert response.metadata["voting_strategy"] == "weighted"


@pytest.mark.asyncio
async def test_sc_first_strategy():
    """Test first answer strategy (no voting)."""
    agent = MockAgent(
        responses=["The answer is First", "The answer is Second", "The answer is Third"]
    )
    sc = SelfConsistency(agent=agent, num_samples=3, voting_strategy="first")

    response = await sc.process(Message(role="user", content="Test query"))

    # Should always use first answer
    assert response.content == "First"
    assert response.metadata["consistency_score"] == 1.0


@pytest.mark.asyncio
async def test_sc_custom_extractor():
    """Test custom answer extractor."""

    def custom_extractor(text: str) -> str:
        # Extract number from text
        import re

        match = re.search(r"\d+", text)
        return match.group(0) if match else text

    agent = MockAgent(
        responses=[
            "The result is 100 units",
            "We get 100 as the answer",
            "Answer: 100",
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=3, answer_extractor=custom_extractor)

    response = await sc.process(Message(role="user", content="Test query"))

    # All should extract to "100"
    assert response.content == "100"
    assert response.metadata["consistency_score"] == 1.0  # Perfect agreement


@pytest.mark.asyncio
async def test_sc_answer_extraction():
    """Test default answer extraction patterns."""
    agent = MockAgent(
        responses=[
            "Therefore, the capital is Paris",
            "The answer is Paris",
            "Calculation: 2 + 2 = 4",
            "Conclusion: Paris",
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=4)

    response = await sc.process(Message(role="user", content="Test query"))

    # Should extract "Paris" from most responses
    assert "paris" in response.content.lower()


@pytest.mark.asyncio
async def test_sc_metadata():
    """Test metadata completeness."""
    agent = MockAgent(
        responses=[
            "Answer: X",
            "Answer: Y",
            "Answer: X",
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=3)

    response = await sc.process(Message(role="user", content="Test query"))

    metadata = response.metadata

    # Check all required metadata fields
    assert "technique" in metadata
    assert "num_samples" in metadata
    assert "voting_strategy" in metadata
    assert "consistency_score" in metadata
    assert "samples" in metadata
    assert "extracted_answers" in metadata
    assert "answer_counts" in metadata
    assert "base_agent" in metadata

    # Check types
    assert isinstance(metadata["samples"], list)
    assert isinstance(metadata["extracted_answers"], list)
    assert isinstance(metadata["answer_counts"], dict)
    assert len(metadata["samples"]) == 3
    assert len(metadata["extracted_answers"]) == 3


@pytest.mark.asyncio
async def test_sc_consistency_score():
    """Test consistency score calculation."""
    # Perfect consistency
    agent = MockAgent(responses=["Answer: A"] * 5)
    sc = SelfConsistency(agent=agent, num_samples=5)
    response = await sc.process(Message(role="user", content="Test"))
    assert response.metadata["consistency_score"] == 1.0

    # No consistency (all different)
    agent = MockAgent(responses=[f"Answer: {i}" for i in range(5)])
    sc = SelfConsistency(agent=agent, num_samples=5)
    response = await sc.process(Message(role="user", content="Test"))
    assert response.metadata["consistency_score"] == 0.2  # 1/5


@pytest.mark.asyncio
async def test_sc_num_samples():
    """Test different numbers of samples."""
    for num_samples in [1, 3, 5, 10]:
        agent = MockAgent()
        sc = SelfConsistency(agent=agent, num_samples=num_samples)

        response = await sc.process(Message(role="user", content="Test"))

        assert response.metadata["num_samples"] == num_samples
        assert len(response.metadata["samples"]) == num_samples


@pytest.mark.asyncio
async def test_sc_capabilities():
    """Test agent capabilities reporting."""
    agent = MockAgent()
    sc = SelfConsistency(agent=agent)

    caps = sc.capabilities

    assert "reasoning" in caps
    assert "self_consistency" in caps
    assert "majority_voting" in caps
    assert "consensus" in caps


@pytest.mark.asyncio
async def test_sc_name():
    """Test agent name."""
    agent = MockAgent()
    sc = SelfConsistency(agent=agent)

    assert sc.name == "self_consistency"


@pytest.mark.asyncio
async def test_sc_invalid_strategy():
    """Test error handling for invalid voting strategy."""
    agent = MockAgent()
    sc = SelfConsistency(agent=agent, voting_strategy="invalid")

    with pytest.raises(ValueError, match="Invalid voting strategy"):
        await sc.process(Message(role="user", content="Test"))


@pytest.mark.asyncio
async def test_sc_answer_counts():
    """Test answer frequency counting."""
    agent = MockAgent(
        responses=[
            "Answer: A",
            "Answer: B",
            "Answer: A",
            "Answer: C",
            "Answer: A",
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=5)

    response = await sc.process(Message(role="user", content="Test"))

    counts = response.metadata["answer_counts"]
    # Answers normalized to lowercase
    assert counts["a"] == 3
    assert counts["b"] == 1
    assert counts["c"] == 1


@pytest.mark.asyncio
async def test_sc_case_insensitive_voting():
    """Test that voting is case-insensitive."""
    agent = MockAgent(
        responses=[
            "Answer: Paris",
            "Answer: PARIS",
            "Answer: paris",
            "Answer: PaRiS",
        ]
    )
    sc = SelfConsistency(agent=agent, num_samples=4)

    response = await sc.process(Message(role="user", content="Test"))

    # All should be counted as same answer
    assert response.metadata["consistency_score"] == 1.0
    # Response should keep original case from one of the answers
    assert response.content.lower() == "paris"


@pytest.mark.asyncio
async def test_sc_with_cot():
    """Test Self-Consistency wrapping Chain-of-Thought."""
    from agenkit.techniques.reasoning import ChainOfThought

    class MockLLM:
        def __init__(self):
            self.responses = [
                "1. Calculate 2*2 = 4\nTherefore, 4",
                "Step 1: 2+2 = 4\nAnswer: 4",
                "Let me think: 2*2 equals 4",
            ]
            self.call_count = 0

        async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
            prompt = "\n".join(m.content for m in messages)
            return Message(role="agent", content=self._respond(prompt))

        def _respond(self, prompt: str) -> str:
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return response

    llm = MockLLM()
    cot = ChainOfThought(llm=llm)
    sc = SelfConsistency(agent=cot, num_samples=3)

    response = await sc.process(Message(role="user", content="What is 2*2?"))

    # Should reach consensus on "4"
    assert "4" in response.content
    assert response.metadata["base_agent"] == "chain_of_thought"


@pytest.mark.asyncio
async def test_sc_parallel_execution():
    """Test that samples are generated in parallel (indirectly via timing)."""
    import asyncio
    import time

    class SlowAgent:
        def __init__(self):
            self.name = "slow_agent"

        async def process(self, message: Message) -> Message:
            # Simulate slow operation
            await asyncio.sleep(0.1)
            return Message(role="assistant", content="Answer: X")

    agent = SlowAgent()
    sc = SelfConsistency(agent=agent, num_samples=5)

    start = time.time()
    await sc.process(Message(role="user", content="Test"))
    elapsed = time.time() - start

    # If parallel, should take ~0.1s (not 0.5s)
    # Allow some overhead
    assert elapsed < 0.3, f"Expected parallel execution but took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_sc_empty_responses():
    """Test handling of empty responses."""
    agent = MockAgent(responses=[""] * 3)
    sc = SelfConsistency(agent=agent, num_samples=3)

    response = await sc.process(Message(role="user", content="Test"))

    # Should handle gracefully
    assert response.content == ""
    assert response.metadata["consistency_score"] >= 0.0
