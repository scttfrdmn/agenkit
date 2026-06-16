"""
A/B Testing Framework for Agent Evaluation

This module provides statistical A/B testing capabilities for comparing agent
performance with proper significance testing and confidence intervals.

Classes:
    ABTest: Orchestrates A/B experiments
    ABVariant: Represents a test variant (control/treatment)
    ABResult: Experiment results with statistical analysis
    SignificanceTest: Statistical test implementations

Example:
    >>> from agenkit.evaluation import ABTest, SessionRecorder
    >>>
    >>> # Create A/B test
    >>> ab_test = ABTest(
    ...     name="agent_comparison",
    ...     control_agent=agent_v1,
    ...     treatment_agent=agent_v2,
    ...     metrics=["accuracy", "latency"]
    ... )
    >>>
    >>> # Run experiment
    >>> result = await ab_test.run(test_cases, sample_size=100)
    >>>
    >>> # Check significance
    >>> if result.is_significant("accuracy"):
    ...     print(f"Winner: {result.winner}")
    ...     print(f"Improvement: {result.improvement_percent:.1f}%")
"""

import asyncio
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from scipy import stats


class SignificanceLevel(Enum):
    """Statistical significance levels."""

    P_0_001 = 0.001  # 99.9% confidence
    P_0_01 = 0.01  # 99% confidence
    P_0_05 = 0.05  # 95% confidence (default)
    P_0_10 = 0.10  # 90% confidence


class StatisticalTestType(Enum):
    """Statistical test types."""

    T_TEST = "t_test"  # Parametric (assumes normal distribution)
    MANN_WHITNEY = "mann_whitney"  # Non-parametric
    CHI_SQUARE = "chi_square"  # Categorical data
    BOOTSTRAP = "bootstrap"  # Distribution-free


@dataclass
class ABVariant:
    """Represents a variant in an A/B test."""

    name: str
    agent: Any  # Agent instance
    samples: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_sample(self, value: float):
        """Add a measurement sample."""
        self.samples.append(value)

    @property
    def mean(self) -> float:
        """Mean of samples."""
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def std(self) -> float:
        """Standard deviation of samples."""
        return statistics.stdev(self.samples) if len(self.samples) > 1 else 0.0

    @property
    def sample_size(self) -> int:
        """Number of samples."""
        return len(self.samples)


@dataclass
class ABResult:
    """Results of an A/B test with statistical analysis."""

    experiment_name: str
    control_variant: ABVariant
    treatment_variant: ABVariant
    metric_name: str
    p_value: float
    test_type: StatisticalTestType
    significance_level: SignificanceLevel
    effect_size: float
    confidence_interval: tuple[float, float]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_significant(self) -> bool:
        """Check if result is statistically significant."""
        return self.p_value < self.significance_level.value

    @property
    def winner(self) -> str | None:
        """Return winner variant name if significant."""
        if not self.is_significant:
            return None

        if self.treatment_variant.mean > self.control_variant.mean:
            return self.treatment_variant.name
        return self.control_variant.name

    @property
    def improvement_percent(self) -> float:
        """Percent improvement of treatment over control."""
        if self.control_variant.mean == 0:
            return 0.0
        return (
            (self.treatment_variant.mean - self.control_variant.mean)
            / abs(self.control_variant.mean)
        ) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_name": self.experiment_name,
            "metric": self.metric_name,
            "control": {
                "name": self.control_variant.name,
                "mean": self.control_variant.mean,
                "std": self.control_variant.std,
                "sample_size": self.control_variant.sample_size,
            },
            "treatment": {
                "name": self.treatment_variant.name,
                "mean": self.treatment_variant.mean,
                "std": self.treatment_variant.std,
                "sample_size": self.treatment_variant.sample_size,
            },
            "statistics": {
                "p_value": self.p_value,
                "test_type": self.test_type.value,
                "significance_level": self.significance_level.value,
                "is_significant": self.is_significant,
                "effect_size": self.effect_size,
                "confidence_interval": self.confidence_interval,
            },
            "outcome": {
                "winner": self.winner,
                "improvement_percent": self.improvement_percent,
            },
            "timestamp": self.timestamp,
        }


class ABTest:
    """
    A/B testing framework for comparing agent variants.

    Provides statistical significance testing, effect size calculation,
    and automated experiment orchestration.

    Example:
        >>> ab_test = ABTest(
        ...     name="prompt_comparison",
        ...     control_agent=baseline_agent,
        ...     treatment_agent=optimized_agent,
        ...     metrics=["accuracy", "latency_ms"]
        ... )
        >>>
        >>> result = await ab_test.run(test_cases, sample_size=50)
        >>> print(f"Significant: {result.is_significant}")
        >>> print(f"Winner: {result.winner}")
    """

    def __init__(
        self,
        name: str,
        control_agent: Any,
        treatment_agent: Any,
        metrics: list[str] | None = None,
        significance_level: SignificanceLevel = SignificanceLevel.P_0_05,
        test_type: StatisticalTestType = StatisticalTestType.T_TEST,
    ):
        """
        Initialize A/B test.

        Args:
            name: Experiment name
            control_agent: Control/baseline agent
            treatment_agent: Treatment/variant agent
            metrics: List of metrics to compare (default: ["accuracy"])
            significance_level: Statistical significance threshold
            test_type: Type of statistical test to use
        """
        self.name = name
        self.control = ABVariant(name="control", agent=control_agent)
        self.treatment = ABVariant(name="treatment", agent=treatment_agent)
        self.metrics = metrics or ["accuracy"]
        self.significance_level = significance_level
        self.test_type = test_type
        self.results: dict[str, ABResult] = {}

    async def run(
        self,
        test_cases: list[dict[str, Any]],
        sample_size: int | None = None,
        shuffle: bool = True,
    ) -> dict[str, ABResult]:
        """
        Run A/B test experiment.

        Args:
            test_cases: Test cases to evaluate
            sample_size: Number of samples per variant (None = all)
            shuffle: Shuffle test cases before splitting

        Returns:
            Dictionary of results per metric
        """
        # Prepare test cases
        if shuffle:
            import random

            test_cases = test_cases.copy()
            random.shuffle(test_cases)

        if sample_size:
            test_cases = test_cases[:sample_size]

        # Run both variants
        control_results = await self._evaluate_variant(self.control, test_cases)
        treatment_results = await self._evaluate_variant(self.treatment, test_cases)

        # Store samples for each metric
        for metric in self.metrics:
            self.control.samples = [r.get(metric, 0) for r in control_results]
            self.treatment.samples = [r.get(metric, 0) for r in treatment_results]

            # Run statistical test
            result = self._run_statistical_test(metric)
            self.results[metric] = result

        return self.results

    async def _evaluate_variant(
        self, variant: ABVariant, test_cases: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Evaluate a variant on test cases."""
        results = []

        for test_case in test_cases:
            try:
                # Run agent
                from agenkit.interfaces import Message

                message = Message(role="user", content=test_case.get("input", ""))
                start_time = asyncio.get_event_loop().time()

                response = await variant.agent.process(message)

                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                # Calculate accuracy (simple string matching for demo)
                expected = test_case.get("expected", "")
                actual = str(response.content)
                accuracy = 1.0 if expected.lower() in actual.lower() else 0.0

                results.append(
                    {
                        "accuracy": accuracy,
                        "latency_ms": latency_ms,
                        "input": test_case.get("input"),
                        "expected": expected,
                        "actual": actual,
                    }
                )

            except Exception as e:
                results.append({"accuracy": 0.0, "latency_ms": 0.0, "error": str(e)})

        return results

    def _run_statistical_test(self, metric_name: str) -> ABResult:
        """Run statistical significance test."""
        control_samples = self.control.samples
        treatment_samples = self.treatment.samples

        if self.test_type == StatisticalTestType.T_TEST:
            # Independent samples t-test
            statistic, p_value = stats.ttest_ind(control_samples, treatment_samples)

            # Cohen's d effect size
            pooled_std = ((self.control.std**2 + self.treatment.std**2) / 2) ** 0.5
            effect_size = (
                (self.treatment.mean - self.control.mean) / pooled_std if pooled_std > 0 else 0.0
            )

            # Confidence interval for difference in means
            ci = stats.t.interval(
                1 - self.significance_level.value,
                len(control_samples) + len(treatment_samples) - 2,
                loc=self.treatment.mean - self.control.mean,
                scale=pooled_std,
            )

        elif self.test_type == StatisticalTestType.MANN_WHITNEY:
            # Non-parametric test
            statistic, p_value = stats.mannwhitneyu(
                control_samples, treatment_samples, alternative="two-sided"
            )

            # Effect size (rank-biserial correlation)
            n1, n2 = len(control_samples), len(treatment_samples)
            effect_size = 1 - (2 * statistic) / (n1 * n2)

            # Bootstrap confidence interval
            ci = self._bootstrap_ci(control_samples, treatment_samples)

        else:
            # Default to t-test
            statistic, p_value = stats.ttest_ind(control_samples, treatment_samples)
            effect_size = 0.0
            ci = (0.0, 0.0)

        return ABResult(
            experiment_name=self.name,
            control_variant=self.control,
            treatment_variant=self.treatment,
            metric_name=metric_name,
            p_value=p_value,
            test_type=self.test_type,
            significance_level=self.significance_level,
            effect_size=effect_size,
            confidence_interval=ci,
        )

    def _bootstrap_ci(
        self, control_samples: list[float], treatment_samples: list[float], n_iterations: int = 1000
    ) -> tuple[float, float]:
        """Bootstrap confidence interval for non-parametric tests."""
        import random

        differences = []

        for _ in range(n_iterations):
            control_resample = [
                random.choice(control_samples)
                for _ in range(len(control_samples))  # noqa: S311
            ]
            treatment_resample = [
                random.choice(treatment_samples)  # noqa: S311
                for _ in range(len(treatment_samples))
            ]

            diff = statistics.mean(treatment_resample) - statistics.mean(control_resample)
            differences.append(diff)

        differences.sort()
        lower_idx = int(n_iterations * (self.significance_level.value / 2))
        upper_idx = int(n_iterations * (1 - self.significance_level.value / 2))

        return (differences[lower_idx], differences[upper_idx])

    def get_summary(self) -> dict[str, Any]:
        """Get experiment summary."""
        return {
            "experiment_name": self.name,
            "variants": {
                "control": self.control.name,
                "treatment": self.treatment.name,
            },
            "metrics": self.metrics,
            "results": {metric: result.to_dict() for metric, result in self.results.items()},
        }


def calculate_sample_size(
    baseline_mean: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
    std_dev: float | None = None,
) -> int:
    """
    Calculate required sample size for A/B test.

    Args:
        baseline_mean: Expected mean of control group
        minimum_detectable_effect: Minimum effect size to detect (absolute)
        alpha: Significance level (default 0.05 for 95% confidence)
        power: Statistical power (default 0.80 for 80% power)
        std_dev: Standard deviation (estimated from baseline if not provided)

    Returns:
        Required sample size per variant

    Example:
        >>> # Need to detect 5% improvement in accuracy (0.80 -> 0.84)
        >>> n = calculate_sample_size(
        ...     baseline_mean=0.80,
        ...     minimum_detectable_effect=0.04,
        ...     std_dev=0.1
        ... )
        >>> print(f"Need {n} samples per variant")
    """
    if std_dev is None:
        # Estimate std dev as 25% of baseline mean if not provided
        std_dev = baseline_mean * 0.25

    # Effect size (standardized difference)
    _effect_size = minimum_detectable_effect / std_dev

    # Z-scores for alpha and beta
    z_alpha = stats.norm.ppf(1 - alpha / 2)  # Two-tailed
    z_beta = stats.norm.ppf(power)

    # Sample size calculation
    n = ((z_alpha + z_beta) ** 2 * 2 * std_dev**2) / (minimum_detectable_effect**2)

    return int(n) + 1
