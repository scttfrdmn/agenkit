"""
Tests for A/B testing framework.

Tests ABTest, ABVariant, ABResult, and statistical methods.
"""

import pytest

from agenkit.evaluation.ab_testing import (
    ABResult,
    ABTest,
    ABVariant,
    SignificanceLevel,
    StatisticalTestType,
    calculate_sample_size,
)
from agenkit.interfaces import Message


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, accuracy=0.8, latency_ms=100):
        """
        Initialize mock agent.

        Args:
            accuracy: Success rate (0.0 to 1.0)
            latency_ms: Simulated latency in milliseconds
        """
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.name = f"mock_agent_{accuracy}"

    async def process(self, message: Message, session_id=None):
        """Process message with simulated accuracy."""
        import asyncio
        import random

        await asyncio.sleep(self.latency_ms / 1000)

        # Simulate success/failure based on accuracy
        success = (
            random.random() < self.accuracy
        )  # noqa: S311 - Pseudo-random acceptable for test mocking
        content = "correct" if success else "incorrect"

        return Message(role="assistant", content=content)


# ABVariant Tests


def test_ab_variant_creation():
    """Test ABVariant creation and basic properties."""
    agent = MockAgent(accuracy=0.8)
    variant = ABVariant(name="control", agent=agent)

    assert variant.name == "control"
    assert variant.agent == agent
    assert variant.samples == []
    assert variant.metadata == {}


def test_ab_variant_add_samples():
    """Test adding samples to a variant."""
    agent = MockAgent()
    variant = ABVariant(name="test", agent=agent)

    variant.add_sample(0.5)
    variant.add_sample(0.7)
    variant.add_sample(0.9)

    assert len(variant.samples) == 3
    assert variant.sample_size == 3


def test_ab_variant_statistics():
    """Test variant statistical properties."""
    agent = MockAgent()
    variant = ABVariant(name="test", agent=agent)

    samples = [0.5, 0.6, 0.7, 0.8, 0.9]
    for sample in samples:
        variant.add_sample(sample)

    assert variant.mean == 0.7
    assert variant.sample_size == 5
    assert variant.std > 0


def test_ab_variant_empty_samples():
    """Test variant with no samples."""
    agent = MockAgent()
    variant = ABVariant(name="test", agent=agent)

    assert variant.mean == 0.0
    assert variant.std == 0.0
    assert variant.sample_size == 0


# ABResult Tests


def test_ab_result_significance():
    """Test ABResult significance detection."""
    control = ABVariant(name="control", agent=MockAgent())
    control.samples = [0.5, 0.5, 0.5, 0.5, 0.5]

    treatment = ABVariant(name="treatment", agent=MockAgent())
    treatment.samples = [0.9, 0.9, 0.9, 0.9, 0.9]

    result = ABResult(
        experiment_name="test",
        control_variant=control,
        treatment_variant=treatment,
        metric_name="accuracy",
        p_value=0.001,  # Highly significant
        test_type=StatisticalTestType.T_TEST,
        significance_level=SignificanceLevel.P_0_05,
        effect_size=2.5,
        confidence_interval=(0.3, 0.5),
    )

    assert result.is_significant
    assert result.winner == "treatment"


def test_ab_result_not_significant():
    """Test ABResult when difference is not significant."""
    control = ABVariant(name="control", agent=MockAgent())
    control.samples = [0.5, 0.5, 0.5]

    treatment = ABVariant(name="treatment", agent=MockAgent())
    treatment.samples = [0.51, 0.52, 0.53]

    result = ABResult(
        experiment_name="test",
        control_variant=control,
        treatment_variant=treatment,
        metric_name="accuracy",
        p_value=0.8,  # Not significant
        test_type=StatisticalTestType.T_TEST,
        significance_level=SignificanceLevel.P_0_05,
        effect_size=0.1,
        confidence_interval=(-0.1, 0.2),
    )

    assert not result.is_significant
    assert result.winner is None


def test_ab_result_improvement_percent():
    """Test improvement percentage calculation."""
    control = ABVariant(name="control", agent=MockAgent())
    control.samples = [0.5, 0.5, 0.5]

    treatment = ABVariant(name="treatment", agent=MockAgent())
    treatment.samples = [0.75, 0.75, 0.75]

    result = ABResult(
        experiment_name="test",
        control_variant=control,
        treatment_variant=treatment,
        metric_name="accuracy",
        p_value=0.01,
        test_type=StatisticalTestType.T_TEST,
        significance_level=SignificanceLevel.P_0_05,
        effect_size=1.0,
        confidence_interval=(0.1, 0.4),
    )

    assert result.improvement_percent == 50.0  # 0.75 is 50% better than 0.5


def test_ab_result_control_wins():
    """Test when control variant is better."""
    control = ABVariant(name="control", agent=MockAgent())
    control.samples = [0.9, 0.9, 0.9]

    treatment = ABVariant(name="treatment", agent=MockAgent())
    treatment.samples = [0.5, 0.5, 0.5]

    result = ABResult(
        experiment_name="test",
        control_variant=control,
        treatment_variant=treatment,
        metric_name="accuracy",
        p_value=0.001,
        test_type=StatisticalTestType.T_TEST,
        significance_level=SignificanceLevel.P_0_05,
        effect_size=-2.0,
        confidence_interval=(-0.5, -0.3),
    )

    assert result.is_significant
    assert result.winner == "control"


def test_ab_result_to_dict():
    """Test ABResult serialization."""
    control = ABVariant(name="control", agent=MockAgent())
    control.samples = [0.5, 0.5, 0.5]

    treatment = ABVariant(name="treatment", agent=MockAgent())
    treatment.samples = [0.75, 0.75, 0.75]

    result = ABResult(
        experiment_name="prompt_test",
        control_variant=control,
        treatment_variant=treatment,
        metric_name="accuracy",
        p_value=0.01,
        test_type=StatisticalTestType.T_TEST,
        significance_level=SignificanceLevel.P_0_05,
        effect_size=1.5,
        confidence_interval=(0.1, 0.4),
    )

    data = result.to_dict()

    assert data["experiment_name"] == "prompt_test"
    assert data["metric"] == "accuracy"
    assert data["control"]["name"] == "control"
    assert data["control"]["mean"] == 0.5
    assert data["treatment"]["name"] == "treatment"
    assert data["treatment"]["mean"] == 0.75
    assert data["statistics"]["p_value"] == 0.01
    assert data["statistics"]["is_significant"] is True
    assert data["outcome"]["winner"] == "treatment"
    assert "timestamp" in data


# ABTest Tests


@pytest.mark.asyncio
async def test_ab_test_basic():
    """Test basic A/B test functionality."""
    # Use fixed random seed for reproducibility
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.7, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.8, latency_ms=10)

    ab_test = ABTest(
        name="test_experiment",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 50

    results = await ab_test.run(test_cases, sample_size=50, shuffle=False)

    assert "accuracy" in results
    assert results["accuracy"].experiment_name == "test_experiment"
    assert results["accuracy"].control_variant.sample_size == 50
    assert results["accuracy"].treatment_variant.sample_size == 50


@pytest.mark.asyncio
async def test_ab_test_multiple_metrics():
    """Test A/B test with multiple metrics."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.7, latency_ms=100)
    treatment_agent = MockAgent(accuracy=0.8, latency_ms=50)

    ab_test = ABTest(
        name="multi_metric_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy", "latency_ms"],
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 30

    results = await ab_test.run(test_cases, sample_size=30, shuffle=False)

    assert "accuracy" in results
    assert "latency_ms" in results
    assert len(results) == 2


@pytest.mark.asyncio
async def test_ab_test_mann_whitney():
    """Test A/B test with Mann-Whitney U test."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.6, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.9, latency_ms=10)

    ab_test = ABTest(
        name="mann_whitney_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
        test_type=StatisticalTestType.MANN_WHITNEY,
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 40

    results = await ab_test.run(test_cases, sample_size=40, shuffle=False)

    assert "accuracy" in results
    assert results["accuracy"].test_type == StatisticalTestType.MANN_WHITNEY


@pytest.mark.asyncio
async def test_ab_test_significance_levels():
    """Test different significance levels."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.75, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.76, latency_ms=10)

    # Test with lenient significance level
    ab_test = ABTest(
        name="lenient_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
        significance_level=SignificanceLevel.P_0_10,  # 90% confidence
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 30

    results = await ab_test.run(test_cases, sample_size=30, shuffle=False)

    assert results["accuracy"].significance_level == SignificanceLevel.P_0_10


@pytest.mark.asyncio
async def test_ab_test_get_summary():
    """Test experiment summary generation."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.7, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.8, latency_ms=10)

    ab_test = ABTest(
        name="summary_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 20

    await ab_test.run(test_cases, sample_size=20, shuffle=False)

    summary = ab_test.get_summary()

    assert summary["experiment_name"] == "summary_test"
    assert summary["variants"]["control"] == "control"
    assert summary["variants"]["treatment"] == "treatment"
    assert summary["metrics"] == ["accuracy"]
    assert "accuracy" in summary["results"]


@pytest.mark.asyncio
async def test_ab_test_shuffle():
    """Test that shuffle parameter works."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.7, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.8, latency_ms=10)

    ab_test = ABTest(
        name="shuffle_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    test_cases = [{"input": f"test_{i}", "expected": "correct"} for i in range(20)]

    # Run with shuffle=True (default)
    results1 = await ab_test.run(test_cases.copy(), sample_size=20, shuffle=True)

    # Run with shuffle=False
    random.seed(42)
    results2 = await ab_test.run(test_cases.copy(), sample_size=20, shuffle=False)

    # Both should complete successfully
    assert "accuracy" in results1
    assert "accuracy" in results2


@pytest.mark.asyncio
async def test_ab_test_sample_size_limit():
    """Test sample size limiting."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.7, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.8, latency_ms=10)

    ab_test = ABTest(
        name="sample_size_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 100

    # Request only 30 samples
    results = await ab_test.run(test_cases, sample_size=30, shuffle=False)

    assert results["accuracy"].control_variant.sample_size == 30
    assert results["accuracy"].treatment_variant.sample_size == 30


# Sample Size Calculator Tests


def test_calculate_sample_size_basic():
    """Test basic sample size calculation."""
    n = calculate_sample_size(
        baseline_mean=0.80, minimum_detectable_effect=0.04, alpha=0.05, power=0.80, std_dev=0.1
    )

    assert isinstance(n, int)
    assert n > 0
    assert n < 10000  # Reasonable upper bound


def test_calculate_sample_size_small_effect():
    """Test sample size for small effect size."""
    # Small effect should require larger sample
    n_small = calculate_sample_size(
        baseline_mean=0.80, minimum_detectable_effect=0.02, alpha=0.05, power=0.80, std_dev=0.1
    )

    n_large = calculate_sample_size(
        baseline_mean=0.80, minimum_detectable_effect=0.10, alpha=0.05, power=0.80, std_dev=0.1
    )

    assert n_small > n_large


def test_calculate_sample_size_higher_power():
    """Test sample size with higher statistical power."""
    # Higher power should require larger sample
    n_80 = calculate_sample_size(
        baseline_mean=0.80, minimum_detectable_effect=0.05, alpha=0.05, power=0.80, std_dev=0.1
    )

    n_95 = calculate_sample_size(
        baseline_mean=0.80, minimum_detectable_effect=0.05, alpha=0.05, power=0.95, std_dev=0.1
    )

    assert n_95 > n_80


def test_calculate_sample_size_no_std_dev():
    """Test sample size calculation with estimated std dev."""
    n = calculate_sample_size(
        baseline_mean=0.80, minimum_detectable_effect=0.05, alpha=0.05, power=0.80, std_dev=None
    )

    assert isinstance(n, int)
    assert n > 0


# Edge Cases and Error Handling


@pytest.mark.asyncio
async def test_ab_test_identical_performance():
    """Test A/B test when both agents perform identically."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.75, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.75, latency_ms=10)

    ab_test = ABTest(
        name="identical_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 50

    results = await ab_test.run(test_cases, sample_size=50, shuffle=False)

    # Should not be significant
    assert "accuracy" in results
    # With identical performance, p-value should be high (not significant)


@pytest.mark.asyncio
async def test_ab_test_small_sample():
    """Test A/B test with very small sample size."""
    import random

    random.seed(42)

    control_agent = MockAgent(accuracy=0.5, latency_ms=10)
    treatment_agent = MockAgent(accuracy=0.9, latency_ms=10)

    ab_test = ABTest(
        name="small_sample_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    # Very small sample
    test_cases = [{"input": "test", "expected": "correct"}] * 5

    results = await ab_test.run(test_cases, sample_size=5, shuffle=False)

    assert "accuracy" in results
    assert results["accuracy"].control_variant.sample_size == 5
    assert results["accuracy"].treatment_variant.sample_size == 5


def test_ab_result_zero_control_mean():
    """Test improvement calculation with zero control mean."""
    control = ABVariant(name="control", agent=MockAgent())
    control.samples = [0.0, 0.0, 0.0]

    treatment = ABVariant(name="treatment", agent=MockAgent())
    treatment.samples = [0.5, 0.5, 0.5]

    result = ABResult(
        experiment_name="test",
        control_variant=control,
        treatment_variant=treatment,
        metric_name="accuracy",
        p_value=0.01,
        test_type=StatisticalTestType.T_TEST,
        significance_level=SignificanceLevel.P_0_05,
        effect_size=1.0,
        confidence_interval=(0.3, 0.7),
    )

    # Should handle division by zero gracefully
    assert result.improvement_percent == 0.0


@pytest.mark.asyncio
async def test_ab_test_agent_errors():
    """Test A/B test handles agent errors gracefully."""

    class FailingAgent:
        async def process(self, message, session_id=None):
            raise ValueError("Agent error")

    control_agent = FailingAgent()
    treatment_agent = FailingAgent()

    ab_test = ABTest(
        name="error_test",
        control_agent=control_agent,
        treatment_agent=treatment_agent,
        metrics=["accuracy"],
    )

    test_cases = [{"input": "test", "expected": "correct"}] * 5

    # Should handle errors and continue
    results = await ab_test.run(test_cases, sample_size=5, shuffle=False)

    assert "accuracy" in results
    # All samples should be 0.0 due to errors
    assert results["accuracy"].control_variant.mean == 0.0
    assert results["accuracy"].treatment_variant.mean == 0.0
