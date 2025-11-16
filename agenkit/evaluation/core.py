"""
Core evaluation framework classes.

Provides base interfaces and orchestration for agent evaluation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone

from ..interfaces import Agent, Message


class Metric(ABC):
    """
    Base class for evaluation metrics.

    Metrics measure specific aspects of agent performance:
    - Accuracy
    - Latency
    - Context usage
    - Quality scores
    - etc.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Metric name."""
        pass

    @abstractmethod
    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Measure metric for a single agent interaction.

        Args:
            agent: The agent being evaluated
            input_message: Input to the agent
            output_message: Agent's response
            context: Additional context (session history, etc.)

        Returns:
            Metric value (typically 0.0 to 1.0)
        """
        pass

    @abstractmethod
    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate multiple measurements.

        Args:
            measurements: List of individual measurements

        Returns:
            Aggregated statistics (mean, std, min, max, etc.)
        """
        pass


@dataclass
class EvaluationResult:
    """
    Results from an evaluation run.

    Contains metrics, metadata, and analysis.
    """

    # Identification
    evaluation_id: str
    agent_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Metrics
    metrics: Dict[str, float] = field(default_factory=dict)
    aggregated_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Context information
    context_length: Optional[int] = None
    compressed_length: Optional[int] = None
    compression_ratio: Optional[float] = None

    # Quality scores
    accuracy: Optional[float] = None
    quality_score: Optional[float] = None

    # Performance
    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None

    # Test details
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "aggregated_metrics": self.aggregated_metrics,
            "context_length": self.context_length,
            "compressed_length": self.compressed_length,
            "compression_ratio": self.compression_ratio,
            "accuracy": self.accuracy,
            "quality_score": self.quality_score,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": self.success_rate,
            "metadata": self.metadata
        }


class Evaluator:
    """
    Core evaluation orchestrator.

    Runs benchmarks, collects metrics, and aggregates results.

    Example:
        >>> evaluator = Evaluator(agent)
        >>> suite = BenchmarkSuite.standard()
        >>> results = await evaluator.evaluate(suite)
        >>> print(f"Accuracy: {results.accuracy:.2f}")
    """

    def __init__(
        self,
        agent: Agent,
        metrics: Optional[List[Metric]] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize evaluator.

        Args:
            agent: Agent to evaluate
            metrics: List of metrics to collect (defaults to standard set)
            session_id: Optional session ID for context tracking
        """
        self.agent = agent
        self.metrics = metrics or []
        self.session_id = session_id or f"eval-{datetime.now(timezone.utc).timestamp()}"

    async def evaluate(
        self,
        test_cases: List[Dict[str, Any]],
        evaluation_id: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluate agent on test cases.

        Args:
            test_cases: List of test cases, each with 'input' and 'expected' keys
            evaluation_id: Optional evaluation ID

        Returns:
            EvaluationResult with metrics and analysis
        """
        import uuid

        eval_id = evaluation_id or str(uuid.uuid4())
        result = EvaluationResult(
            evaluation_id=eval_id,
            agent_name=getattr(self.agent, "name", "unknown"),
            total_tests=len(test_cases)
        )

        # Run tests and collect metrics
        for test_case in test_cases:
            # Handle both dict and TestCase objects
            if hasattr(test_case, 'input'):
                # TestCase object
                input_content = test_case.input
                expected = test_case.expected if hasattr(test_case, 'expected') else None
            else:
                # Dictionary
                input_content = test_case["input"]
                expected = test_case.get("expected")

            input_msg = Message(
                role="user",
                content=input_content,
                metadata={"session_id": self.session_id}
            )

            try:
                # Run agent
                import time
                start = time.perf_counter()
                output_msg = await self.agent.process(input_msg)
                latency = (time.perf_counter() - start) * 1000  # ms

                # Collect metrics
                context = {
                    "expected": expected,
                    "test_case": test_case,
                    "latency_ms": latency
                }

                test_passed = await self._check_test(output_msg, test_case)
                if test_passed:
                    result.passed_tests += 1
                else:
                    result.failed_tests += 1

                # Store latency
                if "latencies" not in result.metadata:
                    result.metadata["latencies"] = []
                result.metadata["latencies"].append(latency)

                # Run metrics
                for metric in self.metrics:
                    metric_value = await metric.measure(
                        self.agent,
                        input_msg,
                        output_msg,
                        context
                    )
                    if metric.name not in result.metrics:
                        result.metrics[metric.name] = []
                    result.metrics[metric.name].append(metric_value)

            except Exception as e:
                result.failed_tests += 1
                result.metadata.setdefault("errors", []).append(str(e))

        # Aggregate metrics
        for metric in self.metrics:
            if metric.name in result.metrics:
                result.aggregated_metrics[metric.name] = metric.aggregate(
                    result.metrics[metric.name]
                )

        # Calculate aggregate statistics
        result.accuracy = result.success_rate

        if "latencies" in result.metadata:
            latencies = result.metadata["latencies"]
            result.avg_latency_ms = sum(latencies) / len(latencies)
            result.p95_latency_ms = sorted(latencies)[int(len(latencies) * 0.95)]

        return result

    async def _check_test(
        self,
        output: Message,
        test_case: Any
    ) -> bool:
        """
        Check if output passes test case.

        Args:
            output: Agent output
            test_case: Test case (dict or TestCase object) with expected output

        Returns:
            True if test passed
        """
        # Handle both dict and TestCase objects
        if hasattr(test_case, 'expected'):
            expected = test_case.expected
        elif isinstance(test_case, dict) and "expected" in test_case:
            expected = test_case["expected"]
        else:
            return True

        # Simple string matching
        if isinstance(expected, str):
            return expected.lower() in str(output.content).lower()

        # Custom validator function
        if callable(expected):
            return expected(output)

        return True

    async def evaluate_single(
        self,
        input_message: Message,
        expected_output: Optional[Any] = None
    ) -> Dict[str, float]:
        """
        Evaluate single interaction.

        Args:
            input_message: Input to agent
            expected_output: Expected output (optional)

        Returns:
            Dictionary of metric values
        """
        output_message = await self.agent.process(input_message)

        metrics_results = {}
        context = {"expected": expected_output}

        for metric in self.metrics:
            value = await metric.measure(
                self.agent,
                input_message,
                output_message,
                context
            )
            metrics_results[metric.name] = value

        return metrics_results
