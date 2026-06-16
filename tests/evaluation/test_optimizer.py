"""
Tests for optimization framework base classes.
"""

from datetime import UTC

import pytest

from agenkit.evaluation import OptimizationResult, RandomSearchOptimizer, SearchSpace
from agenkit.interfaces import Message


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, temperature: float = 0.7, top_p: float = 0.9):
        self.temperature = temperature
        self.top_p = top_p
        self.call_count = 0

    async def process(self, message: Message, session_id: str = "") -> Message:
        """Process message (mock implementation)."""
        self.call_count += 1
        # Simulate performance based on config
        # Better configs (lower temp, higher top_p) perform better
        score = (1 - self.temperature) * self.top_p
        is_correct = score > 0.5
        content = "correct answer" if is_correct else "incorrect"
        return Message(role="assistant", content=content)


# Test SearchSpace


def test_search_space_continuous():
    """Test continuous parameter definition."""
    space = SearchSpace()
    space.add_continuous("temperature", 0.0, 1.0)

    assert "temperature" in space.parameters
    assert space.parameters["temperature"]["type"] == "continuous"
    assert space.parameters["temperature"]["low"] == 0.0
    assert space.parameters["temperature"]["high"] == 1.0


def test_search_space_discrete():
    """Test discrete parameter definition."""
    space = SearchSpace()
    space.add_discrete("max_tokens", [128, 256, 512])

    assert "max_tokens" in space.parameters
    assert space.parameters["max_tokens"]["type"] == "discrete"
    assert space.parameters["max_tokens"]["values"] == [128, 256, 512]


def test_search_space_integer():
    """Test integer parameter definition."""
    space = SearchSpace()
    space.add_integer("n_examples", 1, 10)

    assert "n_examples" in space.parameters
    assert space.parameters["n_examples"]["type"] == "integer"
    assert space.parameters["n_examples"]["low"] == 1
    assert space.parameters["n_examples"]["high"] == 10


def test_search_space_categorical():
    """Test categorical parameter definition."""
    space = SearchSpace()
    space.add_categorical("model", ["gpt-4", "claude-3"])

    assert "model" in space.parameters
    assert space.parameters["model"]["type"] == "categorical"
    assert space.parameters["model"]["values"] == ["gpt-4", "claude-3"]


def test_search_space_sample():
    """Test sampling from search space."""
    space = SearchSpace()
    space.add_continuous("temperature", 0.0, 1.0)
    space.add_discrete("max_tokens", [128, 256, 512])
    space.add_categorical("model", ["gpt-4", "claude-3"])

    config = space.sample()

    assert "temperature" in config
    assert 0.0 <= config["temperature"] <= 1.0
    assert "max_tokens" in config
    assert config["max_tokens"] in [128, 256, 512]
    assert "model" in config
    assert config["model"] in ["gpt-4", "claude-3"]


def test_search_space_validate():
    """Test configuration validation."""
    space = SearchSpace()
    space.add_continuous("temperature", 0.0, 1.0)
    space.add_discrete("max_tokens", [128, 256, 512])

    # Valid config
    assert space.validate({"temperature": 0.5, "max_tokens": 256})

    # Invalid - out of range
    assert not space.validate({"temperature": 1.5, "max_tokens": 256})

    # Invalid - wrong discrete value
    assert not space.validate({"temperature": 0.5, "max_tokens": 1024})

    # Invalid - unknown parameter
    assert not space.validate({"temperature": 0.5, "unknown": 42})


# Test OptimizationResult


def test_optimization_result_creation():
    """Test optimization result creation."""
    from datetime import datetime

    start = datetime.now(UTC).isoformat()
    end = datetime.now(UTC).isoformat()

    result = OptimizationResult(
        best_config={"temperature": 0.5},
        best_score=0.95,
        history=[({"temperature": 0.3}, 0.85), ({"temperature": 0.5}, 0.95)],
        n_iterations=2,
        start_time=start,
        end_time=end,
    )

    assert result.best_config == {"temperature": 0.5}
    assert result.best_score == 0.95
    assert len(result.history) == 2
    assert result.n_iterations == 2


def test_optimization_result_improvement():
    """Test improvement calculation."""
    from datetime import datetime

    start = datetime.now(UTC).isoformat()
    end = datetime.now(UTC).isoformat()

    result = OptimizationResult(
        best_config={"temperature": 0.5},
        best_score=0.95,
        history=[({"temperature": 0.3}, 0.80), ({"temperature": 0.5}, 0.95)],
        n_iterations=2,
        start_time=start,
        end_time=end,
    )

    improvement = result.get_improvement()
    assert improvement > 0  # Positive improvement
    assert abs(improvement - 18.75) < 0.1  # (0.95 - 0.80) / 0.80 * 100 = 18.75%


def test_optimization_result_to_dict():
    """Test converting result to dictionary."""
    from datetime import datetime

    start = datetime.now(UTC).isoformat()
    end = datetime.now(UTC).isoformat()

    result = OptimizationResult(
        best_config={"temperature": 0.5},
        best_score=0.95,
        history=[({"temperature": 0.5}, 0.95)],
        n_iterations=1,
        start_time=start,
        end_time=end,
        metadata={"algorithm": "test"},
    )

    result_dict = result.to_dict()

    assert result_dict["best_config"] == {"temperature": 0.5}
    assert result_dict["best_score"] == 0.95
    assert result_dict["n_iterations"] == 1
    assert "duration_seconds" in result_dict
    assert result_dict["metadata"] == {"algorithm": "test"}


# Test RandomSearchOptimizer


@pytest.mark.asyncio
async def test_random_search_optimizer_basic():
    """Test basic random search optimization."""

    def agent_factory(config):
        return MockAgent(**config)

    search_space = {"temperature": (0.0, 1.0), "top_p": (0.0, 1.0)}

    optimizer = RandomSearchOptimizer(
        agent_factory=agent_factory, search_space=search_space, objective="accuracy", maximize=True
    )

    # Use expected values that match what MockAgent returns
    test_cases = [
        {"input": "What is 2+2?", "expected": "correct answer"},
        {"input": "What is the capital of France?", "expected": "correct answer"},
    ]

    result = await optimizer.optimize(test_cases, n_iterations=5)

    assert result.best_config is not None
    assert "temperature" in result.best_config
    assert "top_p" in result.best_config
    # With random search, at least one config should score > 0
    assert result.best_score >= 0
    assert len(result.history) == 5
    assert result.n_iterations == 5
    assert result.metadata["algorithm"] == "random_search"


@pytest.mark.asyncio
async def test_random_search_improvement():
    """Test that random search finds improvements."""

    def agent_factory(config):
        return MockAgent(**config)

    search_space = {"temperature": (0.0, 1.0), "top_p": (0.5, 1.0)}

    optimizer = RandomSearchOptimizer(
        agent_factory=agent_factory, search_space=search_space, objective="accuracy"
    )

    test_cases = [{"input": "Test", "expected": "correct answer"}] * 3

    result = await optimizer.optimize(test_cases, n_iterations=10)

    # With more iterations, should find reasonable config
    assert result.best_score > 0.3
    assert len(result.history) == 10


@pytest.mark.asyncio
async def test_random_search_discrete_space():
    """Test random search with discrete parameters."""

    def agent_factory(config):
        # Simulate that max_tokens=512 is best
        return MockAgent(temperature=config.get("temperature", 0.5))

    search_space = SearchSpace()
    search_space.add_continuous("temperature", 0.0, 1.0)
    search_space.add_discrete("max_tokens", [128, 256, 512])

    optimizer = RandomSearchOptimizer(
        agent_factory=agent_factory, search_space=search_space, objective="accuracy"
    )

    test_cases = [{"input": "Test", "expected": "correct answer"}] * 2

    result = await optimizer.optimize(test_cases, n_iterations=5)

    assert "max_tokens" in result.best_config
    assert result.best_config["max_tokens"] in [128, 256, 512]
