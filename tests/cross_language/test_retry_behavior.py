"""
Cross-language retry behavior tests for Python.

Tests that Agenkit's Python retry middleware behaves consistently with
the cross-language retry behavior specification.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.middleware.retry import RetryDecorator, RetryConfig


# Load retry behavior fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

with open(FIXTURES_DIR / "retry_behavior.json") as f:
    RETRY_FIXTURES = json.load(f)


class MockAgent(Agent):
    """Mock agent that simulates responses from fixture scenarios."""

    def __init__(self, responses: list[dict[str, Any]]):
        """Initialize with list of responses to return."""
        self.responses = responses
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        """Return next response or raise error."""
        if self.call_count >= len(self.responses):
            raise RuntimeError("No more responses available")

        response = self.responses[self.call_count]
        self.call_count += 1

        if response.get("success"):
            return Message(role="agent", content=response["content"])
        else:
            raise Exception(response["error"])


class TestRetryBehavior:
    """Test retry middleware behavior matches cross-language specification."""

    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        """Verify successful first attempt requires no retries."""
        test_case = next(
            tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_success_first_attempt"
        )

        # Create agent with responses from scenario
        agent = MockAgent(test_case["scenario"]["agent_responses"])

        # Create retry decorator with config from fixture
        config_data = test_case["config"]
        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
        )
        retry = RetryDecorator(agent, config)

        # Execute
        msg = Message(role="user", content="test")
        response = await retry.process(msg)

        # Verify expected behavior
        expected = test_case["expected_behavior"]
        assert agent.call_count == expected["total_attempts"]
        assert response.content == expected["final_response"]

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Verify success after one failed attempt."""
        test_case = next(
            tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_success_second_attempt"
        )

        agent = MockAgent(test_case["scenario"]["agent_responses"])
        config_data = test_case["config"]
        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
        )
        retry = RetryDecorator(agent, config)

        # Measure time to verify delay
        start = asyncio.get_event_loop().time()
        msg = Message(role="user", content="test")
        response = await retry.process(msg)
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        # Verify expected behavior
        expected = test_case["expected_behavior"]
        assert agent.call_count == expected["total_attempts"]
        assert response.content == expected["final_response"]

        # Verify delay is within expected range
        min_delay = expected.get("min_total_delay_ms", 0)
        max_delay = expected.get("max_total_delay_ms", float("inf"))
        assert (
            min_delay <= elapsed_ms <= max_delay * 1.5
        ), f"Delay {elapsed_ms}ms not in range [{min_delay}, {max_delay}]"

    @pytest.mark.asyncio
    async def test_retries_exhausted(self):
        """Verify failure when all retries exhausted."""
        test_case = next(tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_exhausted")

        agent = MockAgent(test_case["scenario"]["agent_responses"])
        config_data = test_case["config"]
        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
        )
        retry = RetryDecorator(agent, config)

        # Should raise exception after exhausting retries
        msg = Message(role="user", content="test")
        with pytest.raises(Exception) as exc_info:
            await retry.process(msg)

        # Verify expected behavior
        expected = test_case["expected_behavior"]
        assert agent.call_count == expected["total_attempts"]
        assert not expected["successful"]

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Verify exponential backoff timing."""
        test_case = next(
            tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_exponential_backoff"
        )

        agent = MockAgent(test_case["scenario"]["agent_responses"])
        config_data = test_case["config"]
        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
        )
        retry = RetryDecorator(agent, config)

        # Measure time
        start = asyncio.get_event_loop().time()
        msg = Message(role="user", content="test")
        response = await retry.process(msg)
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        # Verify expected behavior
        expected = test_case["expected_behavior"]
        assert agent.call_count == expected["total_attempts"]
        assert expected["successful"]

        # Verify delay matches exponential backoff
        # Expected: 100ms + 200ms + 400ms = 700ms
        min_delay = expected.get("min_total_delay_ms", 0)
        max_delay = expected.get("max_total_delay_ms", float("inf"))
        assert (
            min_delay <= elapsed_ms <= max_delay * 1.5
        ), f"Delay {elapsed_ms}ms not in range [{min_delay}, {max_delay}]"

    @pytest.mark.asyncio
    async def test_max_backoff_cap(self):
        """Verify backoff is capped at max_backoff."""
        test_case = next(
            tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_max_backoff_capped"
        )

        agent = MockAgent(test_case["scenario"]["agent_responses"])
        config_data = test_case["config"]
        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
        )
        retry = RetryDecorator(agent, config)

        # Measure time
        start = asyncio.get_event_loop().time()
        msg = Message(role="user", content="test")
        response = await retry.process(msg)
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        # Verify expected behavior
        expected = test_case["expected_behavior"]
        assert agent.call_count == expected["total_attempts"]
        assert expected["successful"]
        assert expected.get("delays_capped", False)

        # Verify capped backoff: 100ms + 200ms (capped) + 200ms (capped) + 200ms (capped) = 700ms
        min_delay = expected.get("min_total_delay_ms", 0)
        max_delay = expected.get("max_total_delay_ms", float("inf"))
        assert (
            min_delay <= elapsed_ms <= max_delay * 1.5
        ), f"Delay {elapsed_ms}ms not in range [{min_delay}, {max_delay}]"

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Verify non-retryable errors fail immediately."""
        test_case = next(
            tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_non_retryable_error"
        )

        agent = MockAgent(test_case["scenario"]["agent_responses"])
        config_data = test_case["config"]

        # Define should_retry predicate
        def should_retry(error: Exception) -> bool:
            return "NonRetryable" not in str(error)

        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
            should_retry=should_retry,
        )
        retry = RetryDecorator(agent, config)

        # Should fail immediately without retrying
        msg = Message(role="user", content="test")
        with pytest.raises(Exception) as exc_info:
            await retry.process(msg)

        # Verify expected behavior
        expected = test_case["expected_behavior"]
        assert agent.call_count == expected["total_attempts"]
        assert not expected["successful"]

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Verify retry metrics are tracked correctly."""
        test_case = next(
            tc for tc in RETRY_FIXTURES["test_cases"] if tc["id"] == "retry_metrics_tracking"
        )

        agent = MockAgent(test_case["scenario"]["agent_responses"])
        config_data = test_case["config"]
        config = RetryConfig(
            max_retries=config_data["max_retries"],
            initial_delay=config_data["initial_backoff_ms"] / 1000.0,
            max_delay=config_data["max_backoff_ms"] / 1000.0,
            multiplier=config_data["backoff_multiplier"],
        )
        retry = RetryDecorator(agent, config)

        # Execute request (fails once, then succeeds)
        msg = Message(role="user", content="test")
        response = await retry.process(msg)

        # Verify metrics
        expected = test_case["expected_metrics"]
        metrics = retry.metrics

        # Verify basic metrics
        assert metrics.total_attempts == expected["total_attempts"]
        assert metrics.successful_first_attempt == expected["successful_first_attempt"]
        assert metrics.successful_on_retry == expected["successful_on_retry"]
        assert response.content == "Success"
