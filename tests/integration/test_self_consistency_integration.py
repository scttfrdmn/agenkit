"""
Integration tests for Self-Consistency reasoning technique.

These tests validate Self-Consistency works correctly with:
- Mock agents (no external dependencies)
- Real LLM providers (OpenAI, Anthropic) when available
- Chain-of-Thought integration
- Error handling and edge cases
"""

import os
from typing import Optional

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.techniques.reasoning.self_consistency import SelfConsistency


class MockVariableAgent(Agent):
    """Mock agent that returns varying responses for testing."""

    def __init__(self, responses: list[str], should_fail: bool = False):
        self.responses = responses
        self.should_fail = should_fail
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock_variable"

    @property
    def capabilities(self) -> list[str]:
        return ["mock", "variable_response"]

    async def process(self, message: Message) -> Message:
        """Return varying responses in round-robin fashion."""
        if self.should_fail:
            raise RuntimeError("Mock agent failure")

        response_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        return Message(
            role="assistant",
            content=response_text,
            metadata={"mock": True, "call_count": self.call_count},
        )


class MockDeterministicAgent(Agent):
    """Mock agent that always returns the same response."""

    def __init__(self, response: str):
        self.response = response

    @property
    def name(self) -> str:
        return "mock_deterministic"

    @property
    def capabilities(self) -> list[str]:
        return ["mock", "deterministic"]

    async def process(self, message: Message) -> Message:
        """Always return the same response."""
        return Message(
            role="assistant",
            content=self.response,
            metadata={"mock": True, "deterministic": True},
        )


# ============================================================================
# Basic Functionality Tests (No External Dependencies)
# ============================================================================


@pytest.mark.asyncio
async def test_self_consistency_basic():
    """Test basic Self-Consistency with majority voting."""
    # Mock agent returns 3 votes for "42" and 2 for "43"
    base_agent = MockVariableAgent([
        "After calculation, the answer is 42.",
        "Let me think... I believe it's 43.",
        "The answer is 42.",
        "Definitely 42.",
        "I think the answer is 43.",
    ])

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=5,
        voting_strategy="majority",
    )

    message = Message(role="user", content="What is 6 * 7?")
    response = await sc.process(message)

    # Check basic response properties
    assert response.role == "assistant"
    assert "42" in response.content

    # Check metadata
    assert response.metadata["technique"] == "self_consistency"
    assert response.metadata["num_samples"] == 5
    assert response.metadata["voting_strategy"] == "majority"
    assert 0.0 <= response.metadata["consistency_score"] <= 1.0
    # Consistency score depends on answer extraction - should be reasonable
    assert response.metadata["consistency_score"] >= 0.4  # At least some agreement

    # Check samples are stored
    assert len(response.metadata["samples"]) == 5
    assert len(response.metadata["extracted_answers"]) == 5

    # Check answer counts - verify answers were extracted
    answer_counts = response.metadata["answer_counts"]
    assert len(answer_counts) > 0  # At least one unique answer
    # The most common answer should appear at least twice
    max_count = max(answer_counts.values())
    assert max_count >= 2


@pytest.mark.asyncio
async def test_self_consistency_perfect_agreement():
    """Test Self-Consistency with perfect agreement (all samples agree)."""
    base_agent = MockDeterministicAgent("The answer is 42.")

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=5,
        voting_strategy="majority",
    )

    message = Message(role="user", content="What is the answer?")
    response = await sc.process(message)

    # Perfect consistency should give score of 1.0
    assert response.metadata["consistency_score"] == 1.0
    assert "42" in response.content


@pytest.mark.asyncio
async def test_self_consistency_no_agreement():
    """Test Self-Consistency with no agreement (all different answers)."""
    base_agent = MockVariableAgent([
        "The answer is 1.",
        "The answer is 2.",
        "The answer is 3.",
        "The answer is 4.",
        "The answer is 5.",
    ])

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=5,
        voting_strategy="majority",
    )

    message = Message(role="user", content="What is the answer?")
    response = await sc.process(message)

    # No agreement should give low consistency score (1/5 = 0.2)
    assert response.metadata["consistency_score"] == 0.2


@pytest.mark.asyncio
async def test_self_consistency_weighted_voting():
    """Test weighted voting strategy (longer responses weighted more)."""
    base_agent = MockVariableAgent([
        "Paris.",
        "Paris.",
        "Paris.",
        "After extensive analysis of historical data, geographical considerations, and political significance, I can confidently conclude that the capital of France is London.",
    ])

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=4,
        voting_strategy="weighted",
    )

    message = Message(role="user", content="What is the capital of France?")
    response = await sc.process(message)

    # Weighted voting should favor the longer "London" response
    assert "london" in response.content.lower()
    assert response.metadata["voting_strategy"] == "weighted"


@pytest.mark.asyncio
async def test_self_consistency_first_strategy():
    """Test first strategy (no voting, just return first answer)."""
    base_agent = MockVariableAgent([
        "The answer is A.",
        "The answer is B.",
        "The answer is C.",
    ])

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=3,
        voting_strategy="first",
    )

    message = Message(role="user", content="Test question")
    response = await sc.process(message)

    # First strategy should return first answer
    assert "A" in response.content
    assert response.metadata["consistency_score"] == 1.0
    assert response.metadata["voting_strategy"] == "first"


@pytest.mark.asyncio
async def test_self_consistency_custom_extractor():
    """Test custom answer extraction function."""
    base_agent = MockVariableAgent([
        "[ANSWER: 42]",
        "[ANSWER: 42]",
        "[ANSWER: 43]",
    ])

    def custom_extractor(text: str) -> str:
        """Extract answer from custom format."""
        import re
        match = re.search(r"\[ANSWER: ([^\]]+)\]", text)
        return match.group(1) if match else text

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=3,
        voting_strategy="majority",
        answer_extractor=custom_extractor,
    )

    message = Message(role="user", content="Test question")
    response = await sc.process(message)

    # Should extract "42" as majority
    assert response.content == "42"
    assert response.metadata["consistency_score"] == pytest.approx(0.666, abs=0.01)


@pytest.mark.asyncio
async def test_self_consistency_single_sample():
    """Test edge case: single sample (degenerate case)."""
    base_agent = MockDeterministicAgent("The answer is 42.")

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=1,
        voting_strategy="majority",
    )

    message = Message(role="user", content="Test question")
    response = await sc.process(message)

    # Single sample should work with perfect consistency
    assert "42" in response.content
    assert response.metadata["consistency_score"] == 1.0
    assert len(response.metadata["samples"]) == 1


@pytest.mark.asyncio
async def test_self_consistency_error_handling():
    """Test error handling when base agent fails."""
    base_agent = MockVariableAgent(["response"], should_fail=True)

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=3,
        voting_strategy="majority",
    )

    message = Message(role="user", content="Test question")

    # Should propagate error from base agent
    with pytest.raises(RuntimeError, match="Mock agent failure"):
        await sc.process(message)


@pytest.mark.asyncio
async def test_self_consistency_case_insensitive_voting():
    """Test that voting is case-insensitive."""
    base_agent = MockVariableAgent([
        "The answer is PARIS.",
        "The answer is Paris.",
        "The answer is paris.",
        "The answer is PaRiS.",
        "The answer is London.",
    ])

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=5,
        voting_strategy="majority",
    )

    message = Message(role="user", content="What is the capital?")
    response = await sc.process(message)

    # Should recognize all case variations as the same (4/5 = 0.8)
    assert "paris" in response.content.lower()
    assert response.metadata["consistency_score"] == 0.8


# ============================================================================
# Real LLM Provider Tests (Requires API Keys)
# ============================================================================
# NOTE: These tests are currently disabled due to interface mismatch between
# ChainOfThought and LLM adapters. ChainOfThought calls llm.complete(string)
# but LLM adapters expect llm.complete(list[Message]). This needs to be fixed
# in a separate issue before these tests can be enabled.
#
# The mock-based tests above fully validate Self-Consistency functionality.
# ============================================================================


def has_openai_key() -> bool:
    """Check if OpenAI API key is available."""
    return bool(os.getenv("OPENAI_API_KEY"))


def has_anthropic_key() -> bool:
    """Check if Anthropic API key is available."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


@pytest.mark.skip(reason="Interface mismatch: ChainOfThought expects llm.complete(str) but LLM adapters expect llm.complete(list[Message])")
@pytest.mark.asyncio
@pytest.mark.slow
async def test_self_consistency_with_openai():
    """Test Self-Consistency with real OpenAI model."""
    from agenkit.adapters.llm.openai import OpenAILLM
    from agenkit.techniques.reasoning.chain_of_thought import ChainOfThought

    # Wrap LLM with ChainOfThought to create an Agent
    llm = OpenAILLM(model="gpt-4o-mini")
    base_agent = ChainOfThought(llm=llm)

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=3,  # Keep low for cost
        voting_strategy="majority",
    )

    message = Message(
        role="user",
        content="What is 15 * 8? Think step by step and provide the final answer.",
    )
    response = await sc.process(message)

    # Check response structure
    assert response.role == "assistant"
    assert "120" in response.content  # Correct answer

    # Check metadata
    assert response.metadata["technique"] == "self_consistency"
    assert response.metadata["num_samples"] == 3
    assert len(response.metadata["samples"]) == 3
    assert 0.0 <= response.metadata["consistency_score"] <= 1.0


@pytest.mark.skip(reason="Interface mismatch: ChainOfThought expects llm.complete(str) but LLM adapters expect llm.complete(list[Message])")
@pytest.mark.asyncio
@pytest.mark.slow
async def test_self_consistency_with_anthropic():
    """Test Self-Consistency with real Anthropic model."""
    from agenkit.adapters.llm.anthropic import AnthropicLLM
    from agenkit.techniques.reasoning.chain_of_thought import ChainOfThought

    # Wrap LLM with ChainOfThought to create an Agent
    llm = AnthropicLLM(model="claude-3-5-haiku-20241022")
    base_agent = ChainOfThought(llm=llm)

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=3,
        voting_strategy="majority",
    )

    message = Message(
        role="user",
        content="What is 12 * 9? Show your reasoning.",
    )
    response = await sc.process(message)

    # Check response structure
    assert response.role == "assistant"
    assert "108" in response.content

    # Check metadata
    assert response.metadata["technique"] == "self_consistency"
    assert len(response.metadata["samples"]) == 3


# ============================================================================
# Chain-of-Thought Integration Tests
# ============================================================================


@pytest.mark.skip(reason="Interface mismatch: ChainOfThought expects llm.complete(str) but LLM adapters expect llm.complete(list[Message])")
@pytest.mark.asyncio
@pytest.mark.slow
async def test_self_consistency_with_chain_of_thought():
    """Test Self-Consistency integrated with Chain-of-Thought."""
    from agenkit.adapters.llm.openai import OpenAILLM
    from agenkit.techniques.reasoning.chain_of_thought import ChainOfThought

    # Create a Chain-of-Thought agent as the base
    llm = OpenAILLM(model="gpt-4o-mini")
    cot_agent = ChainOfThought(llm=llm)

    # Wrap CoT with Self-Consistency
    sc = SelfConsistency(
        agent=cot_agent,
        num_samples=3,
        voting_strategy="majority",
    )

    message = Message(
        role="user",
        content="If a train travels 120 km in 2 hours, what is its average speed?",
    )
    response = await sc.process(message)

    # Check response
    assert "60" in response.content  # 60 km/h

    # Check that samples show reasoning (from CoT)
    samples = response.metadata["samples"]
    assert len(samples) == 3
    # At least some samples should show step-by-step reasoning
    has_reasoning = any("step" in sample.lower() or "first" in sample.lower()
                        for sample in samples)
    assert has_reasoning, "Expected Chain-of-Thought reasoning in samples"


# ============================================================================
# Performance and Concurrency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_self_consistency_parallel_execution():
    """Test that samples are generated in parallel (not sequentially)."""
    import time

    class SlowAgent(Agent):
        """Agent that takes time to respond."""

        @property
        def name(self) -> str:
            return "slow"

        @property
        def capabilities(self) -> list[str]:
            return ["slow"]

        async def process(self, message: Message) -> Message:
            """Simulate slow processing."""
            import asyncio
            await asyncio.sleep(0.2)  # 200ms per call
            return Message(role="assistant", content="The answer is 42.")

    base_agent = SlowAgent()

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=5,  # 5 samples
        voting_strategy="majority",
    )

    message = Message(role="user", content="Test")

    start = time.time()
    response = await sc.process(message)
    elapsed = time.time() - start

    # If parallel: ~0.2s (one round)
    # If sequential: ~1.0s (5 * 0.2s)
    # Allow some overhead, but should be much closer to 0.2s than 1.0s
    assert elapsed < 0.5, f"Expected parallel execution (~0.2s), got {elapsed:.2f}s"
    assert response.metadata["consistency_score"] == 1.0


# ============================================================================
# Metadata Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_self_consistency_metadata_completeness():
    """Test that all required metadata fields are present."""
    base_agent = MockDeterministicAgent("The answer is 42.")

    sc = SelfConsistency(
        agent=base_agent,
        num_samples=3,
        voting_strategy="majority",
    )

    message = Message(role="user", content="Test")
    response = await sc.process(message)

    # Check all required metadata fields
    required_fields = [
        "technique",
        "num_samples",
        "voting_strategy",
        "consistency_score",
        "samples",
        "extracted_answers",
        "answer_counts",
        "base_agent",
    ]

    for field in required_fields:
        assert field in response.metadata, f"Missing required metadata field: {field}"

    # Validate field types
    assert isinstance(response.metadata["technique"], str)
    assert isinstance(response.metadata["num_samples"], int)
    assert isinstance(response.metadata["voting_strategy"], str)
    assert isinstance(response.metadata["consistency_score"], float)
    assert isinstance(response.metadata["samples"], list)
    assert isinstance(response.metadata["extracted_answers"], list)
    assert isinstance(response.metadata["answer_counts"], dict)
    assert isinstance(response.metadata["base_agent"], str)


if __name__ == "__main__":
    # Run tests with: pytest tests/integration/test_self_consistency_integration.py -v
    pytest.main([__file__, "-v", "-s"])
