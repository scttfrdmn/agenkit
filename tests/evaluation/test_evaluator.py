"""
Tests for core evaluation framework.

Tests Evaluator, Metric, EvaluationResult.
"""

import pytest

from agenkit.evaluation import AccuracyMetric, EvaluationResult, Evaluator
from agenkit.interfaces import Message


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, responses=None):
        self.responses = responses or ["Response"]
        self.call_count = 0
        self.name = "mock_agent"

    async def process(self, message: Message, session_id=None):
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return Message(role="assistant", content=response)


@pytest.mark.asyncio
async def test_evaluator_basic():
    """Test basic evaluator functionality."""
    agent = MockAgent(responses=["Paris", "4"])
    evaluator = Evaluator(agent)

    test_cases = [
        {"input": "What is the capital of France?", "expected": "Paris"},
        {"input": "What is 2+2?", "expected": "4"},
    ]

    result = await evaluator.evaluate(test_cases)

    assert result.total_tests == 2
    assert result.passed_tests == 2
    assert result.failed_tests == 0
    assert result.accuracy == 1.0


@pytest.mark.asyncio
async def test_evaluator_with_failures():
    """Test evaluator with failing test cases."""
    agent = MockAgent(responses=["London", "5"])  # Wrong answers
    evaluator = Evaluator(agent)

    test_cases = [
        {"input": "What is the capital of France?", "expected": "Paris"},
        {"input": "What is 2+2?", "expected": "4"},
    ]

    result = await evaluator.evaluate(test_cases)

    assert result.total_tests == 2
    assert result.passed_tests == 0
    assert result.failed_tests == 2
    assert result.accuracy == 0.0


@pytest.mark.asyncio
async def test_evaluator_with_metrics():
    """Test evaluator with custom metrics."""
    agent = MockAgent(responses=["Paris"])
    metric = AccuracyMetric()
    evaluator = Evaluator(agent, metrics=[metric])

    test_cases = [{"input": "What is the capital of France?", "expected": "Paris"}]

    result = await evaluator.evaluate(test_cases)

    assert "accuracy" in result.aggregated_metrics
    assert result.aggregated_metrics["accuracy"]["accuracy"] == 1.0


@pytest.mark.asyncio
async def test_evaluator_latency_tracking():
    """Test that evaluator tracks latency."""
    agent = MockAgent(responses=["Response"])
    evaluator = Evaluator(agent)

    test_cases = [{"input": "Test", "expected": "Response"}]

    result = await evaluator.evaluate(test_cases)

    assert result.avg_latency_ms is not None
    assert result.avg_latency_ms > 0
    assert result.p95_latency_ms is not None


@pytest.mark.asyncio
async def test_evaluator_single():
    """Test single interaction evaluation."""
    agent = MockAgent(responses=["Paris"])
    metric = AccuracyMetric()
    evaluator = Evaluator(agent, metrics=[metric])

    input_msg = Message(role="user", content="What is the capital of France?")

    metrics = await evaluator.evaluate_single(input_msg, expected_output="Paris")

    assert "accuracy" in metrics
    assert metrics["accuracy"] == 1.0


@pytest.mark.asyncio
async def test_evaluation_result_to_dict():
    """Test EvaluationResult serialization."""
    result = EvaluationResult(
        evaluation_id="test-123",
        agent_name="test_agent",
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
    )

    data = result.to_dict()

    assert data["evaluation_id"] == "test-123"
    assert data["agent_name"] == "test_agent"
    assert data["success_rate"] == 0.8
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_evaluator_error_handling():
    """Test evaluator handles agent errors gracefully."""

    class FailingAgent:
        async def process(self, message, session_id=None):
            raise ValueError("Agent error")

    agent = FailingAgent()
    evaluator = Evaluator(agent)

    test_cases = [{"input": "Test"}]

    result = await evaluator.evaluate(test_cases)

    assert result.total_tests == 1
    assert result.failed_tests == 1
    assert "errors" in result.metadata
    assert len(result.metadata["errors"]) == 1


@pytest.mark.asyncio
async def test_evaluator_callable_expected():
    """Test evaluator with callable expected value."""
    agent = MockAgent(responses=["Long response with content"])
    evaluator = Evaluator(agent)

    # Validator function
    def check_length(output):
        return len(str(output.content)) > 10

    test_cases = [{"input": "Test", "expected": check_length}]

    result = await evaluator.evaluate(test_cases)

    assert result.passed_tests == 1


@pytest.mark.asyncio
async def test_evaluator_no_expected():
    """Test evaluator with test cases that have no expected output."""
    agent = MockAgent(responses=["Response"])
    evaluator = Evaluator(agent)

    test_cases = [
        {"input": "Test"}  # No expected output
    ]

    result = await evaluator.evaluate(test_cases)

    # Should pass since no expected output to compare
    assert result.passed_tests == 1
