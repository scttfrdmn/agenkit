"""
Automated Optimization Framework

This module provides intelligent optimization of agent configurations, prompts,
and hyperparameters using Bayesian optimization, genetic algorithms, and other
search strategies.

Classes:
    Optimizer: Base class for optimization algorithms
    OptimizationResult: Results from optimization run
    SearchSpace: Definition of parameter search space
    RandomSearchOptimizer: Baseline random search
    BayesianOptimizer: Bayesian optimization with Gaussian Process

Example:
    >>> from agenkit.evaluation import BayesianOptimizer
    >>>
    >>> # Define search space
    >>> search_space = {
    ...     "temperature": (0.0, 1.0),
    ...     "top_p": (0.0, 1.0),
    ... }
    >>>
    >>> # Create optimizer
    >>> optimizer = BayesianOptimizer(
    ...     agent_factory=lambda config: MyAgent(**config),
    ...     search_space=search_space,
    ...     objective="accuracy"
    ... )
    >>>
    >>> # Run optimization
    >>> result = await optimizer.optimize(test_cases, n_iterations=50)
    >>> print(f"Best config: {result.best_config}")
    >>> print(f"Best score: {result.best_score:.3f}")
"""

import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SearchSpace:
    """
    Definition of parameter search space for optimization.

    Supports continuous, discrete, integer, and categorical parameters
    with optional conditional dependencies.

    Example:
        >>> space = SearchSpace()
        >>> space.add_continuous("temperature", 0.0, 1.0)
        >>> space.add_discrete("max_tokens", [128, 256, 512])
        >>> space.add_categorical("model", ["gpt-4", "claude-3"])
    """

    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_continuous(self, name: str, low: float, high: float) -> None:
        """Add continuous parameter with range [low, high]."""
        self.parameters[name] = {"type": "continuous", "low": low, "high": high}

    def add_discrete(self, name: str, values: list[int | float]) -> None:
        """Add discrete parameter with specific values."""
        self.parameters[name] = {"type": "discrete", "values": values}

    def add_integer(self, name: str, low: int, high: int) -> None:
        """Add integer parameter with range [low, high]."""
        self.parameters[name] = {"type": "integer", "low": low, "high": high}

    def add_categorical(self, name: str, values: list[str]) -> None:
        """Add categorical parameter with specific values."""
        self.parameters[name] = {"type": "categorical", "values": values}

    def sample(self) -> dict[str, Any]:
        """Sample random configuration from search space."""
        config = {}
        for name, spec in self.parameters.items():
            if spec["type"] == "continuous":
                config[name] = random.uniform(spec["low"], spec["high"])
            elif spec["type"] == "discrete":
                config[name] = random.choice(spec["values"])
            elif spec["type"] == "integer":
                config[name] = random.randint(spec["low"], spec["high"])
            elif spec["type"] == "categorical":
                config[name] = random.choice(spec["values"])
        return config

    def validate(self, config: dict[str, Any]) -> bool:
        """Validate that configuration is within search space."""
        for name, value in config.items():
            if name not in self.parameters:
                return False

            spec = self.parameters[name]
            if spec["type"] == "continuous":
                if not (spec["low"] <= value <= spec["high"]):
                    return False
            elif spec["type"] == "discrete":
                if value not in spec["values"]:
                    return False
            elif spec["type"] == "integer":
                if not isinstance(value, int) or not (spec["low"] <= value <= spec["high"]):
                    return False
            elif spec["type"] == "categorical":
                if value not in spec["values"]:
                    return False

        return True


@dataclass
class OptimizationResult:
    """
    Results from optimization run.

    Attributes:
        best_config: Best configuration found
        best_score: Best objective score achieved
        history: List of (config, score) tuples from all evaluations
        n_iterations: Number of iterations performed
        start_time: Optimization start timestamp
        end_time: Optimization end timestamp
        metadata: Additional metadata
    """

    best_config: dict[str, Any]
    best_score: float
    history: list[tuple[dict[str, Any], float]]
    n_iterations: int
    start_time: str
    end_time: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Duration of optimization in seconds."""
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return (end - start).total_seconds()

    def get_improvement(self) -> float:
        """Improvement from initial to best score."""
        if not self.history:
            return 0.0
        initial_score = self.history[0][1]
        if initial_score == 0:
            return 0.0
        return ((self.best_score - initial_score) / abs(initial_score)) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "best_config": self.best_config,
            "best_score": self.best_score,
            "n_iterations": self.n_iterations,
            "improvement_percent": self.get_improvement(),
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata,
        }


class Optimizer(ABC):
    """
    Base class for optimization algorithms.

    Subclasses should implement the optimize() method to perform
    intelligent search over the configuration space.
    """

    def __init__(
        self,
        agent_factory: Callable[[dict[str, Any]], Any],
        search_space: SearchSpace | dict[str, Any],
        objective: str | Callable,
        maximize: bool = True,
    ):
        """
        Initialize optimizer.

        Args:
            agent_factory: Function that creates agent from config
            search_space: SearchSpace or dict defining parameter space
            objective: Metric name or custom objective function
            maximize: Whether to maximize (True) or minimize (False) objective
        """
        self.agent_factory = agent_factory

        # Convert dict to SearchSpace if needed
        if isinstance(search_space, dict):
            space = SearchSpace()
            for name, spec in search_space.items():
                if isinstance(spec, tuple) and len(spec) == 2:
                    # Continuous range
                    space.add_continuous(name, spec[0], spec[1])
                elif isinstance(spec, list):
                    # Discrete/categorical values
                    if all(isinstance(v, (int, float)) for v in spec):
                        space.add_discrete(name, spec)
                    else:
                        space.add_categorical(name, spec)
            self.search_space = space
        else:
            self.search_space = search_space

        self.objective = objective
        self.maximize = maximize
        self.history: list[tuple[dict[str, Any], float]] = []

    @abstractmethod
    async def optimize(
        self, test_cases: list[dict[str, Any]], n_iterations: int, **kwargs: Any
    ) -> OptimizationResult:
        """
        Run optimization.

        Args:
            test_cases: Test cases for evaluation
            n_iterations: Number of iterations to run
            **kwargs: Additional algorithm-specific parameters

        Returns:
            OptimizationResult with best configuration and history
        """
        pass

    async def evaluate_config(
        self, config: dict[str, Any], test_cases: list[dict[str, Any]]
    ) -> float:
        """
        Evaluate a configuration on test cases.

        Args:
            config: Configuration to evaluate
            test_cases: Test cases for evaluation

        Returns:
            Objective score (higher is better if maximize=True)
        """
        # Create agent with config
        agent = self.agent_factory(config)

        # Evaluate on test cases
        from agenkit.evaluation.core import Evaluator

        # Use objective as metric
        if isinstance(self.objective, str):
            # Create appropriate metrics
            from agenkit.evaluation.quality_metrics import AccuracyMetric, QualityMetrics

            metrics = []
            if self.objective == "accuracy":
                metrics.append(AccuracyMetric(None, False))
            elif self.objective == "quality_score":
                metrics.append(QualityMetrics(False, "", None))

            # Use named metric
            evaluator = Evaluator(agent, metrics, "opt-session")
            result = await evaluator.evaluate(test_cases, "")

            # Get metric value
            if self.objective == "accuracy" and result.accuracy is not None:
                score = result.accuracy
            elif self.objective == "quality_score" and result.quality_score is not None:
                score = result.quality_score
            elif self.objective == "latency_ms" and result.avg_latency_ms is not None:
                score = result.avg_latency_ms
                # Invert for latency (lower is better)
                if self.maximize:
                    score = -score
            else:
                # Default to accuracy
                score = result.accuracy if result.accuracy is not None else 0.0
        else:
            # Use custom objective function
            score = await self.objective(agent, test_cases)

        return score if self.maximize else -score


class RandomSearchOptimizer(Optimizer):
    """
    Baseline random search optimizer.

    Randomly samples configurations from the search space and
    evaluates them. Useful as a baseline for comparison.

    Example:
        >>> optimizer = RandomSearchOptimizer(
        ...     agent_factory=lambda c: MyAgent(**c),
        ...     search_space={"temperature": (0.0, 1.0)},
        ...     objective="accuracy"
        ... )
        >>> result = await optimizer.optimize(test_cases, n_iterations=20)
    """

    async def optimize(
        self, test_cases: list[dict[str, Any]], n_iterations: int, **kwargs: Any
    ) -> OptimizationResult:
        """Run random search optimization."""
        start_time = datetime.now(timezone.utc).isoformat()
        self.history = []

        best_config: dict[str, Any] | None = None
        best_score = float("-inf")

        for _ in range(n_iterations):
            # Sample random configuration
            config = self.search_space.sample()

            # Evaluate
            score = await self.evaluate_config(config, test_cases)
            self.history.append((config.copy(), score))

            # Update best
            if score > best_score:
                best_score = score
                best_config = config.copy()

        end_time = datetime.now(timezone.utc).isoformat()

        if best_config is None:
            best_config = self.search_space.sample()

        return OptimizationResult(
            best_config=best_config,
            best_score=best_score,
            history=self.history,
            n_iterations=n_iterations,
            start_time=start_time,
            end_time=end_time,
            metadata={"algorithm": "random_search"},
        )
