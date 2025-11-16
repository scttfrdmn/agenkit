"""
Context-aware metrics for extreme-scale evaluation.

Designed for systems like endless that operate at 1M-25M+ token contexts.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from .core import Metric
from ..interfaces import Agent, Message


class ContextMetrics(Metric):
    """
    Track context length and growth over agent lifecycle.

    Essential for extreme-scale systems (endless) that operate at
    1M-25M+ token contexts. Measures:
    - Raw context token count
    - Compressed context token count (if compression used)
    - Compression ratio
    - Context growth rate

    Example:
        >>> metrics = ContextMetrics()
        >>> result = await metrics.measure(agent, input_msg, output_msg, context)
        >>> print(f"Compression: {result}x")
    """

    @property
    def name(self) -> str:
        return "context_length"

    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Measure context length metrics.

        Args:
            agent: Agent being evaluated
            input_message: Input message
            output_message: Agent response
            context: Additional context with session history

        Returns:
            Current context length in tokens (or compressed tokens if available)
        """
        context = context or {}

        # Get context length from agent metadata if available
        if hasattr(agent, "get_context_stats"):
            stats = await agent.get_context_stats(
                context.get("session_id", "default")
            )
            return float(stats.get("context_length", 0))

        # Fallback: estimate from message metadata
        if "context_length" in input_message.metadata:
            return float(input_message.metadata["context_length"])

        # Fallback: count from conversation history
        if "conversation_history" in context:
            history = context["conversation_history"]
            total_tokens = sum(
                self._estimate_tokens(msg.content)
                for msg in history
            )
            return float(total_tokens)

        return 0.0

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate context length measurements.

        Args:
            measurements: List of context lengths over time

        Returns:
            Statistics: mean, min, max, final, growth_rate
        """
        if not measurements:
            return {
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "final": 0.0,
                "growth_rate": 0.0
            }

        return {
            "mean": sum(measurements) / len(measurements),
            "min": min(measurements),
            "max": max(measurements),
            "final": measurements[-1],
            "growth_rate": (measurements[-1] - measurements[0]) / len(measurements)
                          if len(measurements) > 1 else 0.0
        }

    def _estimate_tokens(self, content: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(str(content)) // 4


@dataclass
class CompressionStats:
    """Statistics from compression evaluation."""

    raw_tokens: int
    compressed_tokens: int
    compression_ratio: float
    retrieval_accuracy: float
    context_length_tested: int
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "raw_tokens": self.raw_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": self.compression_ratio,
            "retrieval_accuracy": self.retrieval_accuracy,
            "context_length_tested": self.context_length_tested,
            "timestamp": self.timestamp.isoformat()
        }


class CompressionMetrics(Metric):
    """
    Measure compression quality at extreme scale.

    Critical for endless and similar systems that use 100x-1000x
    compression at 25M+ tokens. Measures:
    - Compression ratio achieved
    - Information retention after compression
    - Retrieval accuracy from compressed context
    - Quality degradation as context grows

    Example:
        >>> metrics = CompressionMetrics(
        ...     test_lengths=[1_000_000, 10_000_000, 25_000_000]
        ... )
        >>> stats = await metrics.evaluate_at_lengths(agent, session_id)
        >>> for length, stat in stats.items():
        ...     print(f"{length/1e6}M tokens: {stat.compression_ratio}x compression")
    """

    def __init__(
        self,
        test_lengths: Optional[List[int]] = None,
        needle_count: int = 10
    ):
        """
        Initialize compression metrics.

        Args:
            test_lengths: Context lengths to test (defaults to 1M, 10M, 25M)
            needle_count: Number of "needle" facts to test retrieval
        """
        self.test_lengths = test_lengths or [
            1_000_000,    # 1M tokens
            10_000_000,   # 10M tokens
            25_000_000    # 25M tokens (endless scale)
        ]
        self.needle_count = needle_count

    @property
    def name(self) -> str:
        return "compression_quality"

    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Measure compression quality for single interaction.

        Returns:
            Compression ratio (raw_tokens / compressed_tokens)
        """
        context = context or {}

        # Get compression stats from agent if available
        if hasattr(agent, "get_compression_stats"):
            stats = await agent.get_compression_stats(
                context.get("session_id", "default")
            )
            raw = stats.get("raw_tokens", 0)
            compressed = stats.get("compressed_tokens", 0)
            if compressed > 0:
                return float(raw) / float(compressed)

        # Check metadata
        if "compression_ratio" in output_message.metadata:
            return float(output_message.metadata["compression_ratio"])

        return 1.0  # No compression

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate compression ratios.

        Args:
            measurements: List of compression ratios

        Returns:
            Statistics: mean, min, max, std
        """
        if not measurements:
            return {
                "mean": 1.0,
                "min": 1.0,
                "max": 1.0,
                "std": 0.0
            }

        mean_ratio = sum(measurements) / len(measurements)
        variance = sum((x - mean_ratio) ** 2 for x in measurements) / len(measurements)
        std = variance ** 0.5

        return {
            "mean": mean_ratio,
            "min": min(measurements),
            "max": max(measurements),
            "std": std
        }

    async def evaluate_at_lengths(
        self,
        agent: Agent,
        session_id: str,
        needle_content: Optional[List[str]] = None
    ) -> Dict[int, CompressionStats]:
        """
        Evaluate compression quality at multiple context lengths.

        Tests compression and retrieval at 1M, 10M, 25M tokens to
        detect quality degradation as context grows.

        Args:
            agent: Agent with compression capability
            session_id: Session to evaluate
            needle_content: Specific facts to test retrieval (optional)

        Returns:
            Dictionary mapping context_length -> CompressionStats
        """
        results = {}

        for length in self.test_lengths:
            # Create test messages to reach target length
            test_messages = await self._generate_test_context(
                length,
                needle_content or self._default_needles()
            )

            # Process messages through agent
            for msg in test_messages:
                await agent.process(
                    Message(role="user", content=msg),
                    session_id=session_id
                )

            # Get compression stats
            if hasattr(agent, "get_compression_stats"):
                stats = await agent.get_compression_stats(session_id)

                # Test retrieval accuracy
                accuracy = await self._test_retrieval(
                    agent,
                    session_id,
                    needle_content or self._default_needles()
                )

                results[length] = CompressionStats(
                    raw_tokens=stats.get("raw_tokens", 0),
                    compressed_tokens=stats.get("compressed_tokens", 0),
                    compression_ratio=stats.get("raw_tokens", 0) / max(stats.get("compressed_tokens", 1), 1),
                    retrieval_accuracy=accuracy,
                    context_length_tested=length
                )

        return results

    async def _generate_test_context(
        self,
        target_tokens: int,
        needles: List[str]
    ) -> List[str]:
        """
        Generate test context with embedded needles.

        Args:
            target_tokens: Target context length
            needles: Facts to embed for retrieval testing

        Returns:
            List of messages totaling ~target_tokens
        """
        messages = []
        current_tokens = 0

        # Insert needles at regular intervals
        needle_interval = target_tokens // (len(needles) + 1)
        next_needle_at = needle_interval
        needle_idx = 0

        # Generate filler content
        filler = "This is filler content for context expansion. " * 20
        filler_tokens = len(filler) // 4

        while current_tokens < target_tokens:
            # Insert needle if at interval
            if current_tokens >= next_needle_at and needle_idx < len(needles):
                messages.append(needles[needle_idx])
                current_tokens += len(needles[needle_idx]) // 4
                needle_idx += 1
                next_needle_at += needle_interval
            else:
                # Add filler
                messages.append(filler)
                current_tokens += filler_tokens

        return messages

    async def _test_retrieval(
        self,
        agent: Agent,
        session_id: str,
        needles: List[str]
    ) -> float:
        """
        Test retrieval accuracy of needles from context.

        Args:
            agent: Agent to test
            session_id: Session with context
            needles: Facts that should be retrievable

        Returns:
            Accuracy (0.0 to 1.0)
        """
        correct = 0

        for needle in needles:
            # Ask agent to retrieve the fact
            query = Message(
                role="user",
                content=f"Recall: What was mentioned about {needle[:50]}?"
            )

            response = await agent.process(query, session_id=session_id)

            # Check if response contains needle content
            if needle.lower() in str(response.content).lower():
                correct += 1

        return correct / len(needles) if needles else 0.0

    def _default_needles(self) -> List[str]:
        """Generate default needle facts for testing."""
        return [
            f"NEEDLE FACT {i}: The secret code is ALPHA-{i:04d}-OMEGA."
            for i in range(self.needle_count)
        ]


class LatencyMetric(Metric):
    """
    Measure agent response latency.

    Tracks processing time per interaction. Critical for production
    systems where response time matters.
    """

    @property
    def name(self) -> str:
        return "latency"

    async def measure(
        self,
        agent: Agent,
        input_message: Message,
        output_message: Message,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Get latency for this interaction.

        Returns:
            Latency in milliseconds
        """
        context = context or {}
        return float(context.get("latency_ms", 0.0))

    def aggregate(self, measurements: List[float]) -> Dict[str, float]:
        """
        Aggregate latency measurements.

        Returns:
            mean, p50, p95, p99, min, max
        """
        if not measurements:
            return {
                "mean": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "min": 0.0,
                "max": 0.0
            }

        sorted_measurements = sorted(measurements)
        n = len(sorted_measurements)

        return {
            "mean": sum(measurements) / n,
            "p50": sorted_measurements[int(n * 0.50)],
            "p95": sorted_measurements[int(n * 0.95)],
            "p99": sorted_measurements[int(n * 0.99)],
            "min": sorted_measurements[0],
            "max": sorted_measurements[-1]
        }
