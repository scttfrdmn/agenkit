"""
Quality metrics for agent evaluation.

Measures task success, accuracy, and response quality.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from .core import Metric
from ..interfaces import Agent, Message


class AccuracyMetric(Metric):
    """
    Measure task accuracy.

    Compares agent output to expected output to determine
    correctness. Supports multiple validation methods:
    - Exact string matching
    - Substring matching (case-insensitive)
    - Custom validator functions
    - LLM-as-judge validation

    Example:
        >>> metric = AccuracyMetric()
        >>> score = await metric.measure(
        ...     agent,
        ...     input_msg,
        ...     output_msg,
        ...     context={"expected": "Paris"}
        ... )
        >>> print(f"Accuracy: {score}")  # 0.0 or 1.0
    """

    def __init__(
        self,
        validator: Optional[Callable[[str, str], bool]] = None,
        case_sensitive: bool = False
    ):
        """
        Initialize accuracy metric.

        Args:
            validator: Custom validation function(expected, actual) -> bool
            case_sensitive: Whether string matching is case-sensitive
        """
        self.validator = validator
        self.case_sensitive = case_sensitive

    @property
    def name(self) -> str:
        return "accuracy"

    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Measure accuracy for single interaction.

        Args:
            agent: Agent being evaluated
            input_message: Input to agent
            output_message: Agent's response
            context: Must contain "expected" key with expected output

        Returns:
            1.0 if correct, 0.0 if incorrect
        """
        context = context or {}

        if "expected" not in context:
            return 1.0  # No expected output = always correct

        expected = context["expected"]
        actual = str(output_message.content)

        # Custom validator
        if self.validator:
            return 1.0 if self.validator(expected, actual) else 0.0

        # Callable validator (e.g., lambda)
        if callable(expected):
            return 1.0 if expected(output_message) else 0.0

        # String matching
        expected_str = str(expected)
        if not self.case_sensitive:
            expected_str = expected_str.lower()
            actual = actual.lower()

        return 1.0 if expected_str in actual else 0.0

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate accuracy measurements.

        Args:
            measurements: List of 0.0/1.0 values

        Returns:
            Accuracy statistics: accuracy, total, correct, incorrect
        """
        if not measurements:
            return {
                "accuracy": 0.0,
                "total": 0,
                "correct": 0,
                "incorrect": 0
            }

        total = len(measurements)
        correct = sum(measurements)

        return {
            "accuracy": correct / total,
            "total": float(total),
            "correct": correct,
            "incorrect": float(total - correct)
        }


class QualityMetrics(Metric):
    """
    Comprehensive quality scoring.

    Evaluates multiple quality dimensions:
    - Relevance: How relevant is response to query?
    - Completeness: Does response answer all parts?
    - Coherence: Is response logically structured?
    - Accuracy: Is information factually correct?

    Can use rule-based scoring or LLM-as-judge.

    Example:
        >>> metric = QualityMetrics(use_llm_judge=True)
        >>> score = await metric.measure(agent, input_msg, output_msg)
        >>> print(f"Quality: {score:.2f}")  # 0.0 to 1.0
    """

    def __init__(
        self,
        use_llm_judge: bool = False,
        judge_model: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize quality metrics.

        Args:
            use_llm_judge: Use LLM to judge quality (requires judge model)
            judge_model: Model to use for judging (e.g., "claude-sonnet-4")
            weights: Weights for each dimension (relevance, completeness, etc.)
        """
        self.use_llm_judge = use_llm_judge
        self.judge_model = judge_model
        self.weights = weights or {
            "relevance": 0.3,
            "completeness": 0.3,
            "coherence": 0.2,
            "accuracy": 0.2
        }

    @property
    def name(self) -> str:
        return "quality"

    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Measure response quality.

        Args:
            agent: Agent being evaluated
            input_message: Input query
            output_message: Agent response
            context: Optional context

        Returns:
            Quality score (0.0 to 1.0)
        """
        if self.use_llm_judge and self.judge_model:
            return await self._llm_judge(input_message, output_message, context)
        else:
            return await self._rule_based_quality(input_message, output_message, context)

    async def _llm_judge(
        self,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """
        Use LLM to judge quality.

        Prompts judge model to evaluate response on multiple dimensions.

        Returns:
            Quality score (0.0 to 1.0)
        """
        # TODO: Implement LLM-as-judge
        # For now, return rule-based score
        return await self._rule_based_quality(input_message, output_message, context)

    async def _rule_based_quality(
        self,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """
        Rule-based quality scoring.

        Uses heuristics to evaluate quality:
        - Relevance: Response mentions query terms
        - Completeness: Response length vs query complexity
        - Coherence: Proper structure, no repetition
        - Accuracy: Matches expected output if provided

        Returns:
            Quality score (0.0 to 1.0)
        """
        context = context or {}
        input_text = str(input_message.content).lower()
        output_text = str(output_message.content).lower()

        scores = {}

        # Relevance: Does response mention query terms?
        query_terms = set(input_text.split())
        output_terms = set(output_text.split())
        relevance = len(query_terms & output_terms) / max(len(query_terms), 1)
        scores["relevance"] = min(relevance, 1.0)

        # Completeness: Is response substantial?
        expected_length = max(len(input_text) * 2, 100)  # At least 2x input
        completeness = min(len(output_text) / expected_length, 1.0)
        scores["completeness"] = completeness

        # Coherence: Basic checks
        has_structure = len(output_text) > 20  # Non-trivial response
        no_repetition = not self._has_repetition(output_text)
        coherence = (int(has_structure) + int(no_repetition)) / 2.0
        scores["coherence"] = coherence

        # Accuracy: Compare to expected if available
        if "expected" in context:
            expected = str(context["expected"]).lower()
            accuracy = 1.0 if expected in output_text else 0.0
        else:
            accuracy = 0.5  # Neutral if no expected output
        scores["accuracy"] = accuracy

        # Weighted average
        total_score = sum(
            scores[dim] * self.weights[dim]
            for dim in scores
        )

        return total_score

    def _has_repetition(self, text: str) -> bool:
        """Check for excessive repetition in text."""
        words = text.split()
        if len(words) < 10:
            return False

        # Check for repeated phrases (3+ word sequences)
        seen_phrases = set()
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            if phrase in seen_phrases:
                return True
            seen_phrases.add(phrase)

        return False

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate quality measurements.

        Args:
            measurements: List of quality scores

        Returns:
            Statistics: mean, min, max, std
        """
        if not measurements:
            return {
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std": 0.0
            }

        mean = sum(measurements) / len(measurements)
        variance = sum((x - mean) ** 2 for x in measurements) / len(measurements)
        std = variance ** 0.5

        return {
            "mean": mean,
            "min": min(measurements),
            "max": max(measurements),
            "std": std
        }


@dataclass
class PrecisionRecallStats:
    """Precision and recall statistics."""

    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    @property
    def precision(self) -> float:
        """Calculate precision."""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        """Calculate recall."""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1_score(self) -> float:
        """Calculate F1 score."""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score
        }


class PrecisionRecallMetric(Metric):
    """
    Measure precision and recall for classification tasks.

    Useful for agents that categorize, filter, or make binary decisions.

    Example:
        >>> metric = PrecisionRecallMetric()
        >>> # Agent classifies documents as relevant/not relevant
        >>> for doc in test_docs:
        ...     score = await metric.measure(agent, doc, output, context)
    """

    def __init__(self):
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.true_negatives = 0

    @property
    def name(self) -> str:
        return "precision_recall"

    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Measure precision/recall for single classification.

        Context must contain:
        - "true_label": Ground truth (True/False or 1/0)
        - "predicted_label": Agent's prediction (True/False or 1/0)

        Returns:
            1.0 if correct classification, 0.0 if incorrect
        """
        context = context or {}

        if "true_label" not in context or "predicted_label" not in context:
            return 1.0  # No labels = always correct

        true_label = bool(context["true_label"])
        predicted_label = bool(context["predicted_label"])

        # Update confusion matrix
        if true_label and predicted_label:
            self.true_positives += 1
            return 1.0
        elif not true_label and predicted_label:
            self.false_positives += 1
            return 0.0
        elif true_label and not predicted_label:
            self.false_negatives += 1
            return 0.0
        else:  # not true_label and not predicted_label
            self.true_negatives += 1
            return 1.0

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate precision/recall metrics.

        Returns:
            Precision, recall, F1 score, and confusion matrix counts
        """
        stats = PrecisionRecallStats(
            true_positives=self.true_positives,
            false_positives=self.false_positives,
            false_negatives=self.false_negatives,
            true_negatives=self.true_negatives
        )

        return stats.to_dict()

    def reset(self):
        """Reset confusion matrix counts."""
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.true_negatives = 0
