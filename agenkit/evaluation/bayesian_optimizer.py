"""
Bayesian Optimization for Hyperparameter Tuning

Uses Gaussian Process regression to build a surrogate model of the
objective function and selects next configurations using acquisition
functions (Expected Improvement, Upper Confidence Bound).

Example:
    >>> from agenkit.evaluation import BayesianOptimizer
    >>>
    >>> optimizer = BayesianOptimizer(
    ...     agent_factory=lambda config: MyAgent(**config),
    ...     search_space={"temperature": (0.0, 1.0), "top_p": (0.0, 1.0)},
    ...     objective="accuracy",
    ...     acquisition="ei"
    ... )
    >>>
    >>> result = await optimizer.optimize(test_cases, n_iterations=50)
"""

from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

from .optimizer import OptimizationResult, Optimizer, SearchSpace


class AcquisitionFunction(Enum):
    """Acquisition function types for Bayesian optimization."""

    EI = "ei"  # Expected Improvement
    UCB = "ucb"  # Upper Confidence Bound
    PI = "pi"  # Probability of Improvement


class BayesianOptimizer(Optimizer):
    """
    Bayesian optimization using Gaussian Process.

    Uses a probabilistic surrogate model to intelligently select
    configurations to evaluate, balancing exploration and exploitation.

    Algorithm:
        1. Sample n_initial random configurations
        2. Evaluate and fit Gaussian Process
        3. Use acquisition function to select next config
        4. Evaluate new config
        5. Update GP and repeat

    Example:
        >>> optimizer = BayesianOptimizer(
        ...     agent_factory=lambda c: MyAgent(**c),
        ...     search_space={"temperature": (0.0, 1.0)},
        ...     objective="accuracy",
        ...     acquisition="ei",
        ...     n_initial=10
        ... )
        >>> result = await optimizer.optimize(test_cases, n_iterations=50)
    """

    def __init__(
        self,
        agent_factory: Callable[[dict[str, Any]], Any],
        search_space: SearchSpace | dict[str, Any],
        objective: str | Callable,
        maximize: bool = True,
        acquisition: str = "ei",
        n_initial: int = 5,
        xi: float = 0.01,
        kappa: float = 2.576,
        kernel: Any | None = None,
    ):
        """
        Initialize Bayesian optimizer.

        Args:
            agent_factory: Function that creates agent from config
            search_space: SearchSpace or dict defining parameter space
            objective: Metric name or custom objective function
            maximize: Whether to maximize (True) or minimize (False)
            acquisition: Acquisition function ("ei", "ucb", "pi")
            n_initial: Number of random initial samples
            xi: Exploration parameter for EI and PI (default: 0.01)
            kappa: Exploration parameter for UCB (default: 2.576 for 99% confidence)
            kernel: Gaussian Process kernel (default: Matern)
        """
        super().__init__(agent_factory, search_space, objective, maximize)

        self.acquisition_func = AcquisitionFunction(acquisition)
        self.n_initial = n_initial
        self.xi = xi
        self.kappa = kappa

        # Initialize Gaussian Process
        if kernel is None:
            kernel = Matern(nu=2.5)
        self.gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, random_state=42)

        # Track parameter names and bounds for continuous parameters
        self.param_names: list[str] = []
        self.param_bounds: list[tuple] = []
        self._setup_continuous_space()

    def _setup_continuous_space(self) -> None:
        """Setup continuous parameter space for GP optimization."""
        for name, spec in self.search_space.parameters.items():
            if spec["type"] in ("continuous", "integer"):
                self.param_names.append(name)
                self.param_bounds.append((spec["low"], spec["high"]))

    def _config_to_vector(self, config: dict[str, Any]) -> np.ndarray:
        """Convert configuration dict to vector for GP."""
        return np.array([config[name] for name in self.param_names])

    def _vector_to_config(self, vector: np.ndarray) -> dict[str, Any]:
        """Convert vector to configuration dict."""
        config = {}
        for i, name in enumerate(self.param_names):
            spec = self.search_space.parameters[name]
            if spec["type"] == "integer":
                config[name] = round(vector[i])
            else:
                config[name] = float(vector[i])

        # Add categorical/discrete parameters (sample randomly for now)
        for name, spec in self.search_space.parameters.items():
            if name not in config and (spec["type"] == "discrete" or spec["type"] == "categorical"):
                config[name] = np.random.choice(spec["values"])

        return config

    def _expected_improvement(
        self,
        X: np.ndarray,  # noqa: N803
        X_sample: np.ndarray,  # noqa: N803
        Y_sample: np.ndarray,  # noqa: N803
    ) -> np.ndarray:
        """
        Expected Improvement acquisition function.

        Args:
            X: Points to evaluate
            X_sample: Observed points
            Y_sample: Observed values

        Returns:
            Expected improvement at each point in X
        """
        mu, sigma = self.gp.predict(X, return_std=True)
        mu_sample_opt = np.max(Y_sample)

        with np.errstate(divide="warn"):
            imp = mu - mu_sample_opt - self.xi
            Z = imp / sigma  # noqa: N806
            ei = imp * self._norm_cdf(Z) + sigma * self._norm_pdf(Z)
            ei[sigma == 0.0] = 0.0

        return ei

    def _upper_confidence_bound(self, X: np.ndarray) -> np.ndarray:  # noqa: N803
        """
        Upper Confidence Bound acquisition function.

        Args:
            X: Points to evaluate

        Returns:
            UCB values at each point in X
        """
        mu, sigma = self.gp.predict(X, return_std=True)
        return mu + self.kappa * sigma

    def _probability_of_improvement(
        self,
        X: np.ndarray,  # noqa: N803
        X_sample: np.ndarray,  # noqa: N803
        Y_sample: np.ndarray,  # noqa: N803
    ) -> np.ndarray:
        """
        Probability of Improvement acquisition function.

        Args:
            X: Points to evaluate
            X_sample: Observed points
            Y_sample: Observed values

        Returns:
            Probability of improvement at each point in X
        """
        mu, sigma = self.gp.predict(X, return_std=True)
        mu_sample_opt = np.max(Y_sample)

        with np.errstate(divide="warn"):
            Z = (mu - mu_sample_opt - self.xi) / sigma  # noqa: N806
            pi = self._norm_cdf(Z)
            pi[sigma == 0.0] = 0.0

        return pi

    @staticmethod
    def _norm_cdf(x: np.ndarray) -> np.ndarray:
        """Standard normal cumulative distribution function."""
        import math

        return 0.5 * (1.0 + np.vectorize(lambda z: math.erf(z / math.sqrt(2.0)))(x))

    @staticmethod
    def _norm_pdf(x: np.ndarray) -> np.ndarray:
        """Standard normal probability density function."""
        return np.exp(-0.5 * x**2) / np.sqrt(2.0 * np.pi)

    def _propose_location(
        self,
        X_sample: np.ndarray,  # noqa: N803
        Y_sample: np.ndarray,  # noqa: N803
        n_candidates: int = 1000,
    ) -> np.ndarray:
        """
        Propose next location to sample using acquisition function.

        Args:
            X_sample: Observed points
            Y_sample: Observed values
            n_candidates: Number of random candidates to evaluate

        Returns:
            Next point to sample
        """
        # Generate random candidates
        candidates = np.random.uniform(
            low=[b[0] for b in self.param_bounds],
            high=[b[1] for b in self.param_bounds],
            size=(n_candidates, len(self.param_bounds)),
        )

        # Evaluate acquisition function
        if self.acquisition_func == AcquisitionFunction.EI:
            acq_values = self._expected_improvement(candidates, X_sample, Y_sample)
        elif self.acquisition_func == AcquisitionFunction.UCB:
            acq_values = self._upper_confidence_bound(candidates)
        elif self.acquisition_func == AcquisitionFunction.PI:
            acq_values = self._probability_of_improvement(candidates, X_sample, Y_sample)
        else:
            msg = f"Unknown acquisition function: {self.acquisition_func}"
            raise ValueError(msg)

        # Return candidate with highest acquisition value
        best_idx = np.argmax(acq_values)
        return candidates[best_idx]

    async def optimize(
        self, test_cases: list[dict[str, Any]], n_iterations: int, **kwargs: Any
    ) -> OptimizationResult:
        """
        Run Bayesian optimization.

        Args:
            test_cases: Test cases for evaluation
            n_iterations: Total number of iterations (including initial samples)
            **kwargs: Additional parameters

        Returns:
            OptimizationResult with best configuration
        """
        start_time = datetime.now(timezone.utc).isoformat()
        self.history = []

        # Phase 1: Random initialization
        X_sample: list[np.ndarray] = []  # noqa: N806
        Y_sample: list[float] = []  # noqa: N806

        for _ in range(min(self.n_initial, n_iterations)):
            config = self.search_space.sample()
            score = await self.evaluate_config(config, test_cases)

            self.history.append((config.copy(), score))
            X_sample.append(self._config_to_vector(config))
            Y_sample.append(score)

        # Phase 2: Bayesian optimization
        for _ in range(self.n_initial, n_iterations):
            # Fit GP on observed data
            X_array = np.array(X_sample)  # noqa: N806
            Y_array = np.array(Y_sample)  # noqa: N806
            self.gp.fit(X_array, Y_array)

            # Propose next location
            next_x = self._propose_location(X_array, Y_array)
            next_config = self._vector_to_config(next_x)

            # Evaluate
            score = await self.evaluate_config(next_config, test_cases)

            # Update history
            self.history.append((next_config.copy(), score))
            X_sample.append(next_x)
            Y_sample.append(score)

        # Find best configuration
        best_idx = int(np.argmax(Y_sample))
        best_config = self.history[best_idx][0]
        best_score = Y_sample[best_idx]

        end_time = datetime.now(timezone.utc).isoformat()

        return OptimizationResult(
            best_config=best_config,
            best_score=best_score,
            history=self.history,
            n_iterations=n_iterations,
            start_time=start_time,
            end_time=end_time,
            metadata={
                "algorithm": "bayesian_optimization",
                "acquisition": self.acquisition_func.value,
                "n_initial": self.n_initial,
                "kernel": str(self.gp.kernel_),
            },
        )
