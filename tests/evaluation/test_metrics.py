"""
Tests for evaluation metrics.

Tests AccuracyMetric, QualityMetrics, ContextMetrics, etc.
"""

import pytest

from agenkit.evaluation import (AccuracyMetric, PrecisionRecallMetric,
                                QualityMetrics)
from agenkit.evaluation.context_metrics import (CompressionMetrics,
                                                ContextMetrics, LatencyMetric)
from agenkit.interfaces import Message


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, context_stats=None, compression_stats=None):
        self.context_stats = context_stats or {}
        self.compression_stats = compression_stats or {}
        self.name = "mock_agent"

    async def get_context_stats(self, session_id):
        return self.context_stats

    async def get_compression_stats(self, session_id):
        return self.compression_stats

    async def process(self, message: Message, session_id=None):
        return Message(role="assistant", content="Response")


@pytest.mark.asyncio
async def test_accuracy_metric_correct():
    """Test accuracy metric with correct answer."""
    agent = MockAgent()
    metric = AccuracyMetric()

    input_msg = Message(role="user", content="What is 2+2?")
    output_msg = Message(role="assistant", content="The answer is 4")

    score = await metric.measure(agent, input_msg, output_msg, context={"expected": "4"})

    assert score == 1.0


@pytest.mark.asyncio
async def test_accuracy_metric_incorrect():
    """Test accuracy metric with incorrect answer."""
    agent = MockAgent()
    metric = AccuracyMetric()

    input_msg = Message(role="user", content="What is 2+2?")
    output_msg = Message(role="assistant", content="The answer is 5")

    score = await metric.measure(agent, input_msg, output_msg, context={"expected": "4"})

    assert score == 0.0


@pytest.mark.asyncio
async def test_accuracy_metric_case_insensitive():
    """Test accuracy metric is case-insensitive by default."""
    agent = MockAgent()
    metric = AccuracyMetric(case_sensitive=False)

    input_msg = Message(role="user", content="Capital of France?")
    output_msg = Message(role="assistant", content="PARIS")

    score = await metric.measure(agent, input_msg, output_msg, context={"expected": "paris"})

    assert score == 1.0


@pytest.mark.asyncio
async def test_accuracy_metric_custom_validator():
    """Test accuracy metric with custom validator."""

    def custom_validator(expected, actual):
        return len(actual) > 10

    agent = MockAgent()
    metric = AccuracyMetric(validator=custom_validator)

    input_msg = Message(role="user", content="Test")
    output_msg = Message(role="assistant", content="This is a long response")

    score = await metric.measure(agent, input_msg, output_msg, context={"expected": "ignored"})

    assert score == 1.0


@pytest.mark.asyncio
async def test_accuracy_metric_aggregate():
    """Test accuracy metric aggregation."""
    metric = AccuracyMetric()

    measurements = [1.0, 1.0, 0.0, 1.0, 0.0]
    stats = metric.aggregate(measurements)

    assert stats["accuracy"] == 0.6
    assert stats["total"] == 5.0
    assert stats["correct"] == 3.0
    assert stats["incorrect"] == 2.0


@pytest.mark.asyncio
async def test_quality_metrics_rule_based():
    """Test rule-based quality scoring."""
    agent = MockAgent()
    metric = QualityMetrics(use_llm_judge=False)

    input_msg = Message(role="user", content="What is the capital of France?")
    output_msg = Message(
        role="assistant", content="The capital of France is Paris, which is a beautiful city."
    )

    score = await metric.measure(agent, input_msg, output_msg)

    assert 0.0 <= score <= 1.0
    assert score > 0.5  # Should score reasonably well


@pytest.mark.asyncio
async def test_quality_metrics_aggregate():
    """Test quality metrics aggregation."""
    metric = QualityMetrics()

    measurements = [0.8, 0.9, 0.7, 0.85]
    stats = metric.aggregate(measurements)

    assert "mean" in stats
    assert "std" in stats
    assert 0.7 <= stats["mean"] <= 0.9


@pytest.mark.asyncio
async def test_context_metrics():
    """Test context length tracking."""
    agent = MockAgent(context_stats={"context_length": 1000})
    metric = ContextMetrics()

    input_msg = Message(role="user", content="Test")
    output_msg = Message(role="assistant", content="Response")

    length = await metric.measure(agent, input_msg, output_msg, context={"session_id": "test"})

    assert length == 1000.0


@pytest.mark.asyncio
async def test_context_metrics_aggregate():
    """Test context metrics aggregation."""
    metric = ContextMetrics()

    measurements = [1000, 2000, 3000, 4000, 5000]
    stats = metric.aggregate(measurements)

    assert stats["mean"] == 3000.0
    assert stats["min"] == 1000.0
    assert stats["max"] == 5000.0
    assert stats["final"] == 5000.0
    assert stats["growth_rate"] > 0


@pytest.mark.asyncio
async def test_compression_metrics():
    """Test compression quality measurement."""
    agent = MockAgent(compression_stats={"raw_tokens": 10000, "compressed_tokens": 100})
    metric = CompressionMetrics()

    input_msg = Message(role="user", content="Test")
    output_msg = Message(role="assistant", content="Response")

    ratio = await metric.measure(agent, input_msg, output_msg, context={"session_id": "test"})

    assert ratio == 100.0  # 10000 / 100


@pytest.mark.asyncio
async def test_compression_metrics_aggregate():
    """Test compression metrics aggregation."""
    metric = CompressionMetrics()

    measurements = [100.0, 150.0, 120.0, 200.0]
    stats = metric.aggregate(measurements)

    assert "mean" in stats
    assert "std" in stats
    assert 100.0 <= stats["mean"] <= 200.0


@pytest.mark.asyncio
async def test_latency_metric():
    """Test latency measurement."""
    agent = MockAgent()
    metric = LatencyMetric()

    input_msg = Message(role="user", content="Test")
    output_msg = Message(role="assistant", content="Response")

    latency = await metric.measure(agent, input_msg, output_msg, context={"latency_ms": 123.45})

    assert latency == 123.45


@pytest.mark.asyncio
async def test_latency_metric_aggregate():
    """Test latency metric aggregation."""
    metric = LatencyMetric()

    measurements = [100, 200, 150, 300, 250]
    stats = metric.aggregate(measurements)

    assert "mean" in stats
    assert "p50" in stats
    assert "p95" in stats
    assert "p99" in stats
    assert stats["mean"] == 200.0
    # Sorted: [100, 150, 200, 250, 300], p50 at index 2 (50% of 5) = 200
    assert stats["p50"] == 200


@pytest.mark.asyncio
async def test_precision_recall_metric():
    """Test precision/recall for classification."""
    agent = MockAgent()
    metric = PrecisionRecallMetric()

    # True positive
    await metric.measure(
        agent,
        Message(role="user", content="Test"),
        Message(role="assistant", content="positive"),
        context={"true_label": True, "predicted_label": True},
    )

    # False positive
    await metric.measure(
        agent,
        Message(role="user", content="Test"),
        Message(role="assistant", content="positive"),
        context={"true_label": False, "predicted_label": True},
    )

    # False negative
    await metric.measure(
        agent,
        Message(role="user", content="Test"),
        Message(role="assistant", content="negative"),
        context={"true_label": True, "predicted_label": False},
    )

    # True negative
    await metric.measure(
        agent,
        Message(role="user", content="Test"),
        Message(role="assistant", content="negative"),
        context={"true_label": False, "predicted_label": False},
    )

    stats = metric.aggregate([])

    assert stats["true_positives"] == 1
    assert stats["false_positives"] == 1
    assert stats["false_negatives"] == 1
    assert stats["true_negatives"] == 1
    assert stats["precision"] == 0.5  # TP / (TP + FP)
    assert stats["recall"] == 0.5  # TP / (TP + FN)
    assert stats["f1_score"] == 0.5


@pytest.mark.asyncio
async def test_precision_recall_reset():
    """Test resetting precision/recall metric."""
    metric = PrecisionRecallMetric()

    # Add some data
    await metric.measure(
        MockAgent(),
        Message(role="user", content="Test"),
        Message(role="assistant", content="positive"),
        context={"true_label": True, "predicted_label": True},
    )

    assert metric.true_positives == 1

    # Reset
    metric.reset()

    assert metric.true_positives == 0
    assert metric.false_positives == 0
