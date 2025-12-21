"""
Prompt Optimization Framework

Automatically improve prompts through systematic variation and testing
using grid search, random search, or genetic algorithms.

Example:
    >>> from agenkit.evaluation import PromptOptimizer
    >>>
    >>> template = '''
    ... You are a {role}.
    ... {instructions}
    ... '''
    >>>
    >>> variations = {
    ...     "role": ["helpful assistant", "expert advisor"],
    ...     "instructions": ["Be concise.", "Be detailed."]
    ... }
    >>>
    >>> optimizer = PromptOptimizer(
    ...     template=template,
    ...     variations=variations,
    ...     agent_factory=lambda prompt: MyAgent(system_prompt=prompt),
    ...     metrics=["accuracy"]
    ... )
    >>>
    >>> result = await optimizer.optimize(test_cases)
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .core import Evaluator


class OptimizationStrategy(Enum):
    """Prompt optimization strategies."""

    GRID = "grid"  # Exhaustive grid search
    RANDOM = "random"  # Random sampling
    GENETIC = "genetic"  # Genetic algorithm


@dataclass
class PromptOptimizationResult:
    """
    Results from prompt optimization.

    Attributes:
        best_prompt: Best prompt found
        best_config: Best variable configuration
        best_scores: Best metric scores
        history: List of (prompt, config, scores) tuples
        n_evaluated: Number of prompts evaluated
        strategy: Optimization strategy used
        start_time: Optimization start timestamp
        end_time: Optimization end timestamp
    """

    best_prompt: str
    best_config: dict[str, str]
    best_scores: dict[str, float]
    history: list[tuple[str, dict[str, str], dict[str, float]]]
    n_evaluated: int
    strategy: str
    start_time: str
    end_time: str

    @property
    def duration_seconds(self) -> float:
        """Duration of optimization in seconds."""
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return (end - start).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "best_prompt": self.best_prompt,
            "best_config": self.best_config,
            "best_scores": self.best_scores,
            "n_evaluated": self.n_evaluated,
            "strategy": self.strategy,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class PromptOptimizer:
    """
    Prompt optimization through systematic variation.

    Supports multiple optimization strategies:
    - Grid search: Exhaustive evaluation of all combinations
    - Random search: Random sampling of combinations
    - Genetic algorithm: Evolutionary optimization

    Example:
        >>> optimizer = PromptOptimizer(
        ...     template="You are a {role}. {instructions}",
        ...     variations={
        ...         "role": ["assistant", "advisor", "guide"],
        ...         "instructions": ["Be brief.", "Be detailed."]
        ...     },
        ...     agent_factory=lambda p: MyAgent(system_prompt=p),
        ...     metrics=["accuracy", "quality_score"]
        ... )
        >>> result = await optimizer.optimize(test_cases, strategy="grid")
    """

    def __init__(
        self,
        template: str,
        variations: dict[str, list[str]],
        agent_factory: Callable[[str], Any],
        metrics: list[str],
        objective_metric: str | None = None,
        maximize: bool = True,
    ):
        """
        Initialize prompt optimizer.

        Args:
            template: Prompt template with {variable} placeholders
            variations: Dict mapping variable names to possible values
            agent_factory: Function that creates agent from prompt string
            metrics: List of metrics to evaluate
            objective_metric: Primary metric for optimization (default: first metric)
            maximize: Whether to maximize (True) or minimize (False) objective
        """
        self.template = template
        self.variations = variations
        self.agent_factory = agent_factory
        self.metrics = metrics
        self.objective_metric = objective_metric or metrics[0]
        self.maximize = maximize
        self.history: list[tuple[str, dict[str, str], dict[str, float]]] = []

    def _fill_template(self, config: dict[str, str]) -> str:
        """Fill template with configuration values."""
        return self.template.format(**config)

    def _generate_all_configs(self) -> list[dict[str, str]]:
        """Generate all possible configurations (Cartesian product)."""
        import itertools

        keys = list(self.variations.keys())
        values = [self.variations[k] for k in keys]

        configs = []
        for combo in itertools.product(*values):
            config = dict(zip(keys, combo, strict=False))
            configs.append(config)

        return configs

    def _sample_config(self) -> dict[str, str]:
        """Sample random configuration."""
        return {key: random.choice(values) for key, values in self.variations.items()}

    async def _evaluate_prompt(self, prompt: str, test_cases: list[dict[str, Any]]) -> dict[str, float]:
        """
        Evaluate prompt on test cases.

        Args:
            prompt: Prompt to evaluate
            test_cases: Test cases for evaluation

        Returns:
            Dict of metric scores
        """
        # Create agent with prompt
        agent = self.agent_factory(prompt)

        # Evaluate
        from agenkit.evaluation.quality_metrics import AccuracyMetric, QualityMetrics

        # Create metrics
        metric_objs = []
        if "accuracy" in self.metrics:
            metric_objs.append(AccuracyMetric(None, False))
        if "quality_score" in self.metrics:
            metric_objs.append(QualityMetrics(False, "", None))

        evaluator = Evaluator(agent, metric_objs, "prompt-opt")
        result = await evaluator.evaluate(test_cases, "")

        # Extract scores
        scores = {}
        if "accuracy" in self.metrics and result.accuracy is not None:
            scores["accuracy"] = result.accuracy
        if "quality_score" in self.metrics and result.quality_score is not None:
            scores["quality_score"] = result.quality_score
        if "latency_ms" in self.metrics and result.avg_latency_ms is not None:
            scores["latency_ms"] = result.avg_latency_ms

        return scores

    def _get_objective_score(self, scores: dict[str, float]) -> float:
        """Get objective score from metric scores."""
        score = scores.get(self.objective_metric, 0.0)

        # Invert if minimizing (e.g., latency)
        if not self.maximize:
            score = -score

        return score

    async def optimize_grid(
        self, test_cases: list[dict[str, Any]]
    ) -> PromptOptimizationResult:
        """
        Grid search: Evaluate all possible combinations.

        Args:
            test_cases: Test cases for evaluation

        Returns:
            PromptOptimizationResult
        """
        start_time = datetime.now(timezone.utc).isoformat()
        self.history = []

        # Generate all configs
        configs = self._generate_all_configs()

        best_prompt = ""
        best_config: dict[str, str] = {}
        best_scores: dict[str, float] = {}
        best_objective = float("-inf")

        # Evaluate each configuration
        for config in configs:
            prompt = self._fill_template(config)
            scores = await self._evaluate_prompt(prompt, test_cases)
            objective_score = self._get_objective_score(scores)

            self.history.append((prompt, config.copy(), scores.copy()))

            if objective_score > best_objective:
                best_objective = objective_score
                best_prompt = prompt
                best_config = config.copy()
                best_scores = scores.copy()

        end_time = datetime.now(timezone.utc).isoformat()

        return PromptOptimizationResult(
            best_prompt=best_prompt,
            best_config=best_config,
            best_scores=best_scores,
            history=self.history,
            n_evaluated=len(configs),
            strategy="grid",
            start_time=start_time,
            end_time=end_time,
        )

    async def optimize_random(
        self, test_cases: list[dict[str, Any]], n_samples: int = 20
    ) -> PromptOptimizationResult:
        """
        Random search: Sample random combinations.

        Args:
            test_cases: Test cases for evaluation
            n_samples: Number of random samples to evaluate

        Returns:
            PromptOptimizationResult
        """
        start_time = datetime.now(timezone.utc).isoformat()
        self.history = []

        best_prompt = ""
        best_config: dict[str, str] = {}
        best_scores: dict[str, float] = {}
        best_objective = float("-inf")

        # Sample and evaluate random configurations
        for _ in range(n_samples):
            config = self._sample_config()
            prompt = self._fill_template(config)
            scores = await self._evaluate_prompt(prompt, test_cases)
            objective_score = self._get_objective_score(scores)

            self.history.append((prompt, config.copy(), scores.copy()))

            if objective_score > best_objective:
                best_objective = objective_score
                best_prompt = prompt
                best_config = config.copy()
                best_scores = scores.copy()

        end_time = datetime.now(timezone.utc).isoformat()

        return PromptOptimizationResult(
            best_prompt=best_prompt,
            best_config=best_config,
            best_scores=best_scores,
            history=self.history,
            n_evaluated=n_samples,
            strategy="random",
            start_time=start_time,
            end_time=end_time,
        )

    async def optimize_genetic(
        self,
        test_cases: list[dict[str, Any]],
        population_size: int = 10,
        n_generations: int = 5,
        mutation_rate: float = 0.2,
    ) -> PromptOptimizationResult:
        """
        Genetic algorithm: Evolve prompts through selection and mutation.

        Args:
            test_cases: Test cases for evaluation
            population_size: Size of population
            n_generations: Number of generations
            mutation_rate: Probability of mutation per gene

        Returns:
            PromptOptimizationResult
        """
        start_time = datetime.now(timezone.utc).isoformat()
        self.history = []

        # Initialize population with random configurations
        population = [self._sample_config() for _ in range(population_size)]
        fitness_scores: list[float] = []

        # Evaluate initial population
        for config in population:
            prompt = self._fill_template(config)
            scores = await self._evaluate_prompt(prompt, test_cases)
            objective_score = self._get_objective_score(scores)
            fitness_scores.append(objective_score)
            self.history.append((prompt, config.copy(), scores.copy()))

        # Evolution loop
        for _ in range(n_generations):
            # Selection: Tournament selection
            new_population = []
            for _ in range(population_size):
                # Select 2 random individuals
                idx1, idx2 = random.sample(range(population_size), 2)
                # Choose fitter one
                winner_idx = idx1 if fitness_scores[idx1] > fitness_scores[idx2] else idx2
                new_population.append(population[winner_idx].copy())

            # Mutation
            for config in new_population:
                for key in config:
                    if random.random() < mutation_rate:
                        config[key] = random.choice(self.variations[key])

            # Evaluate new population
            population = new_population
            fitness_scores = []

            for config in population:
                prompt = self._fill_template(config)
                scores = await self._evaluate_prompt(prompt, test_cases)
                objective_score = self._get_objective_score(scores)
                fitness_scores.append(objective_score)
                self.history.append((prompt, config.copy(), scores.copy()))

        # Find best from all history
        best_idx = max(range(len(self.history)), key=lambda i: self._get_objective_score(self.history[i][2]))
        best_prompt, best_config, best_scores = self.history[best_idx]

        end_time = datetime.now(timezone.utc).isoformat()

        return PromptOptimizationResult(
            best_prompt=best_prompt,
            best_config=best_config,
            best_scores=best_scores,
            history=self.history,
            n_evaluated=len(self.history),
            strategy="genetic",
            start_time=start_time,
            end_time=end_time,
        )

    async def optimize(
        self,
        test_cases: list[dict[str, Any]],
        strategy: str = "random",
        **kwargs: Any,
    ) -> PromptOptimizationResult:
        """
        Run prompt optimization.

        Args:
            test_cases: Test cases for evaluation
            strategy: Optimization strategy ("grid", "random", "genetic")
            **kwargs: Strategy-specific parameters

        Returns:
            PromptOptimizationResult
        """
        if strategy == "grid":
            return await self.optimize_grid(test_cases)
        if strategy == "random":
            n_samples = kwargs.get("n_samples", 20)
            return await self.optimize_random(test_cases, n_samples=n_samples)
        if strategy == "genetic":
            population_size = kwargs.get("population_size", 10)
            n_generations = kwargs.get("n_generations", 5)
            mutation_rate = kwargs.get("mutation_rate", 0.2)
            return await self.optimize_genetic(
                test_cases,
                population_size=population_size,
                n_generations=n_generations,
                mutation_rate=mutation_rate,
            )
        msg = f"Unknown strategy: {strategy}"
        raise ValueError(msg)
