"""
Tests for Reflection Pattern.

Coverage:
- ReflectionAgent basic operation
- Quality threshold stopping
- Improvement threshold stopping
- Max reflections stopping
- Perfect score stopping
- Critique parsing (structured and free-form)
- Reflection history
- Metadata structure
- Error handling
"""

import json

import pytest

from agenkit.interfaces import Message
from agenkit.patterns import CritiqueFormat, ReflectionAgent, ReflectionStep, StopReason


# Mock agents for testing
class MockGeneratorAgent:
    """Mock generator that improves output each iteration."""

    def __init__(self, outputs: list[str] | None = None):
        self.outputs = outputs or [
            "Output iteration 1",
            "Output iteration 2 (improved)",
            "Output iteration 3 (more improved)",
        ]
        self.call_count = 0
        self.name = "MockGenerator"
        self.capabilities = ["generation"]

    async def process(self, message: Message) -> Message:
        """Return next output from list."""
        if self.call_count < len(self.outputs):
            output = self.outputs[self.call_count]
            self.call_count += 1
        else:
            output = self.outputs[-1]  # Repeat last

        return Message(role="assistant", content=output)


class MockCriticAgent:
    """Mock critic that returns scores."""

    def __init__(self, scores: list[float] | None = None, feedback: list[str] | None = None):
        self.scores = scores or [0.6, 0.8, 0.95]
        self.feedback = feedback or [
            "Needs improvement",
            "Better but not perfect",
            "Excellent!",
        ]
        self.call_count = 0
        self.name = "MockCritic"
        self.capabilities = ["critique"]
        self.format = "structured"

    async def process(self, message: Message) -> Message:
        """Return next score and feedback."""
        if self.call_count < len(self.scores):
            score = self.scores[self.call_count]
            feedback = self.feedback[self.call_count]
            self.call_count += 1
        else:
            # Repeat last
            score = self.scores[-1]
            feedback = self.feedback[-1]

        if self.format == "structured":
            content = json.dumps({"score": score, "feedback": feedback})
        else:  # free_form
            content = f"Score: {score}\n\n{feedback}"

        return Message(role="assistant", content=content)


# Tests


@pytest.mark.asyncio
async def test_reflection_basic():
    """Test basic reflection loop."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    agent = ReflectionAgent(
        generator=generator, critic=critic, max_reflections=3, quality_threshold=0.9
    )

    result = await agent.process(Message(role="user", content="Write a function"))

    assert result.role == "assistant"
    assert "metadata" in result.__dict__
    assert result.metadata["reflection_iterations"] <= 3
    assert "final_quality_score" in result.metadata
    assert "stop_reason" in result.metadata


@pytest.mark.asyncio
async def test_reflection_quality_threshold_met():
    """Test stopping when quality threshold is met."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.7, 0.85, 0.95])  # Reaches 0.95 on iteration 3

    agent = ReflectionAgent(
        generator=generator, critic=critic, max_reflections=10, quality_threshold=0.9
    )

    result = await agent.process(Message(role="user", content="Test"))

    assert result.metadata["reflection_iterations"] == 3
    assert result.metadata["final_quality_score"] >= 0.9
    assert result.metadata["stop_reason"] == "quality_threshold_met"


@pytest.mark.asyncio
async def test_reflection_minimal_improvement():
    """Test stopping when improvement is too small."""
    generator = MockGeneratorAgent()
    # Small improvements: 0.6 -> 0.62 -> 0.63
    critic = MockCriticAgent(scores=[0.6, 0.62, 0.63])

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_reflections=10,
        quality_threshold=0.9,
        improvement_threshold=0.05,  # Requires 5% improvement
    )

    result = await agent.process(Message(role="user", content="Test"))

    # Should stop after iteration 3 (improvement 0.01 < 0.05)
    assert result.metadata["reflection_iterations"] <= 3
    assert result.metadata["stop_reason"] == "minimal_improvement"


@pytest.mark.asyncio
async def test_reflection_max_reflections():
    """Test stopping at max reflections."""
    # Provide enough outputs for all iterations (initial + 4 refinements)
    generator = MockGeneratorAgent(
        outputs=[
            "Output 1",
            "Output 2 (refined)",
            "Output 3 (refined)",
            "Output 4 (refined)",
            "Output 5 (refined)",
        ]
    )
    # Never reaches threshold, good improvements (>0.04 each)
    critic = MockCriticAgent(
        scores=[0.5, 0.6, 0.7, 0.77, 0.83],
        feedback=[
            "Needs work",
            "Better",
            "Good progress",
            "Very good",
            "Almost there",
        ],
    )

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_reflections=5,
        quality_threshold=0.9,
        improvement_threshold=0.04,  # Lower threshold so improvements don't stop early
    )

    result = await agent.process(Message(role="user", content="Test"))

    assert result.metadata["reflection_iterations"] == 5
    assert result.metadata["stop_reason"] == "max_reflections"


@pytest.mark.asyncio
async def test_reflection_perfect_score():
    """Test stopping at perfect score."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.8, 1.0])  # Perfect score on iteration 2

    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=10)

    result = await agent.process(Message(role="user", content="Test"))

    assert result.metadata["reflection_iterations"] == 2
    assert result.metadata["final_quality_score"] == 1.0
    assert result.metadata["stop_reason"] == "perfect_score"


@pytest.mark.asyncio
async def test_reflection_history():
    """Test reflection history structure."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.6, 0.8, 0.95])

    agent = ReflectionAgent(
        generator=generator,
        critic=critic,
        max_reflections=3,
        verbose=True,  # Enable history
    )

    result = await agent.process(Message(role="user", content="Test"))

    assert "reflection_history" in result.metadata
    history = result.metadata["reflection_history"]

    assert len(history) == 3
    for i, step in enumerate(history):
        assert "iteration" in step
        assert step["iteration"] == i + 1
        assert "output" in step
        assert "critique" in step
        assert "quality_score" in step
        assert "improvement" in step
        assert "timestamp" in step


@pytest.mark.asyncio
async def test_reflection_metadata_structure():
    """Test all metadata fields are present."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.7, 0.9])

    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=3)

    result = await agent.process(Message(role="user", content="Test"))

    # Check required metadata
    assert "reflection_iterations" in result.metadata
    assert "final_quality_score" in result.metadata
    assert "stop_reason" in result.metadata
    assert "initial_quality_score" in result.metadata
    assert "total_improvement" in result.metadata

    # Validate types
    assert isinstance(result.metadata["reflection_iterations"], int)
    assert isinstance(result.metadata["final_quality_score"], float)
    assert isinstance(result.metadata["stop_reason"], str)


@pytest.mark.asyncio
async def test_reflection_improvement_calculation():
    """Test improvement is calculated correctly."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.5, 0.7, 0.9])

    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=3)

    result = await agent.process(Message(role="user", content="Test"))

    assert result.metadata["initial_quality_score"] == 0.5
    assert result.metadata["final_quality_score"] >= 0.9
    assert result.metadata["total_improvement"] >= 0.4  # 0.9 - 0.5


@pytest.mark.asyncio
async def test_reflection_critique_parsing_structured():
    """Test structured critique parsing (JSON format)."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()
    critic.format = "structured"

    agent = ReflectionAgent(
        generator=generator, critic=critic, critique_format=CritiqueFormat.STRUCTURED
    )

    result = await agent.process(Message(role="user", content="Test"))

    # Should successfully parse JSON critiques
    assert result.metadata["reflection_iterations"] > 0
    assert "final_quality_score" in result.metadata


@pytest.mark.asyncio
async def test_reflection_critique_parsing_free_form():
    """Test free-form critique parsing."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()
    critic.format = "free_form"

    agent = ReflectionAgent(
        generator=generator, critic=critic, critique_format=CritiqueFormat.FREE_FORM
    )

    result = await agent.process(Message(role="user", content="Test"))

    # Should successfully parse free-form critiques
    assert result.metadata["reflection_iterations"] > 0
    assert "final_quality_score" in result.metadata


@pytest.mark.asyncio
async def test_reflection_get_history():
    """Test get_history() method."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.6, 0.8, 0.95])

    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=3)

    await agent.process(Message(role="user", content="Test"))

    history = agent.get_history()

    assert len(history) == 3
    assert all(isinstance(step, ReflectionStep) for step in history)


@pytest.mark.asyncio
async def test_reflection_clear_history():
    """Test clear_history() method."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=3)

    await agent.process(Message(role="user", content="Test"))
    assert len(agent.get_history()) > 0

    agent.clear_history()
    assert len(agent.get_history()) == 0


@pytest.mark.asyncio
async def test_reflection_name_property():
    """Test agent name property."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    agent = ReflectionAgent(generator=generator, critic=critic)

    assert agent.name == "ReflectionAgent"


@pytest.mark.asyncio
async def test_reflection_capabilities():
    """Test agent capabilities include both generator and critic."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    agent = ReflectionAgent(generator=generator, critic=critic)

    capabilities = agent.capabilities

    assert "generation" in capabilities
    assert "critique" in capabilities
    assert "reflection" in capabilities
    assert "self-critique" in capabilities


def test_reflection_validation_max_reflections():
    """Test validation of max_reflections parameter."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    with pytest.raises(ValueError, match="max_reflections must be at least 1"):
        ReflectionAgent(generator=generator, critic=critic, max_reflections=0)


def test_reflection_validation_quality_threshold():
    """Test validation of quality_threshold parameter."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    with pytest.raises(ValueError, match=r"quality_threshold must be between 0.0 and 1.0"):
        ReflectionAgent(generator=generator, critic=critic, quality_threshold=1.5)

    with pytest.raises(ValueError, match=r"quality_threshold must be between 0.0 and 1.0"):
        ReflectionAgent(generator=generator, critic=critic, quality_threshold=-0.1)


def test_reflection_validation_improvement_threshold():
    """Test validation of improvement_threshold parameter."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent()

    with pytest.raises(ValueError, match=r"improvement_threshold must be between 0.0 and 1.0"):
        ReflectionAgent(generator=generator, critic=critic, improvement_threshold=1.5)


@pytest.mark.asyncio
async def test_reflection_json_with_code_block():
    """Test parsing JSON wrapped in markdown code blocks."""

    class CodeBlockCritic:
        name = "CodeBlockCritic"
        capabilities = []

        async def process(self, message: Message) -> Message:
            # Return JSON in markdown code block (common LLM output)
            content = """```json
{
  "score": 0.85,
  "feedback": "Good output, minor improvements needed"
}
```"""
            return Message(role="assistant", content=content)

    generator = MockGeneratorAgent(outputs=["Output 1", "Output 2"])
    critic = CodeBlockCritic()

    agent = ReflectionAgent(
        generator=generator, critic=critic, max_reflections=2, quality_threshold=0.8
    )

    result = await agent.process(Message(role="user", content="Test"))

    # Should successfully parse JSON from code block
    assert result.metadata["final_quality_score"] >= 0.8


@pytest.mark.asyncio
async def test_reflection_step_to_dict():
    """Test ReflectionStep.to_dict() method."""
    from datetime import datetime, timezone

    step = ReflectionStep(
        iteration=1,
        output="Test output",
        critique="Test critique",
        quality_score=0.75,
        improvement=0.15,
        timestamp=datetime.now(timezone.utc),
    )

    step_dict = step.to_dict()

    assert step_dict["iteration"] == 1
    assert step_dict["output"] == "Test output"
    assert step_dict["critique"] == "Test critique"
    assert step_dict["quality_score"] == 0.75
    assert step_dict["improvement"] == 0.15
    assert "timestamp" in step_dict


@pytest.mark.asyncio
async def test_reflection_verbose_mode():
    """Test verbose mode includes full history."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.6, 0.8])

    # Verbose mode
    agent_verbose = ReflectionAgent(generator=generator, critic=critic, verbose=True)

    result_verbose = await agent_verbose.process(Message(role="user", content="Test"))

    assert "reflection_history" in result_verbose.metadata

    # Non-verbose mode
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.6, 0.8])
    agent_quiet = ReflectionAgent(generator=generator, critic=critic, verbose=False)

    result_quiet = await agent_quiet.process(Message(role="user", content="Test"))

    assert "reflection_history" not in result_quiet.metadata


@pytest.mark.asyncio
async def test_reflection_stop_reason_enum():
    """Test StopReason enum values."""
    assert StopReason.QUALITY_THRESHOLD_MET.value == "quality_threshold_met"
    assert StopReason.MINIMAL_IMPROVEMENT.value == "minimal_improvement"
    assert StopReason.MAX_REFLECTIONS.value == "max_reflections"
    assert StopReason.PERFECT_SCORE.value == "perfect_score"


@pytest.mark.asyncio
async def test_reflection_first_iteration_quality():
    """Test that first iteration records initial quality correctly."""
    generator = MockGeneratorAgent()
    critic = MockCriticAgent(scores=[0.45, 0.95])  # Start low, then high

    agent = ReflectionAgent(generator=generator, critic=critic, max_reflections=5)

    result = await agent.process(Message(role="user", content="Test"))

    assert result.metadata["initial_quality_score"] == 0.45
    assert result.metadata["final_quality_score"] >= 0.9
    # Improvement should be ~0.5
    assert result.metadata["total_improvement"] >= 0.4
