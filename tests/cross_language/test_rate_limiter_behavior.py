"""Cross-language rate limiter behavior tests for Python.

Validates that Agenkit's Python rate limiter middleware behaves consistently
with the cross-language rate limiter behavior specification.
"""

import asyncio
import json
import time
from pathlib import Path

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.middleware.rate_limiter import (
    RateLimiterConfig,
    RateLimiterDecorator,
    RateLimitError,
)


class MockRateLimiterAgent(Agent):
    """Mock agent for rate limiter testing."""

    def __init__(self):
        """Initialize with call tracking."""
        self.call_count = 0

    @property
    def name(self) -> str:
        """Return agent name."""
        return "mock-rate-limiter-agent"

    async def process(self, message: Message) -> Message:
        """Process message immediately."""
        self.call_count += 1
        return Message(role="agent", content=f"Response {self.call_count}")


def load_fixtures():
    """Load rate limiter behavior fixtures."""
    fixtures_path = Path(__file__).parent / "fixtures" / "rate_limiter_behavior.json"
    with open(fixtures_path) as f:
        return json.load(f)


def find_test_case(fixtures: dict, test_id: str) -> dict:
    """Find a specific test case by ID."""
    for test_case in fixtures["test_cases"]:
        if test_case["id"] == test_id:
            return test_case
    raise ValueError(f"Test case not found: {test_id}")


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_capacity():
    """Test that requests succeed within burst capacity."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_allows_within_capacity")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute requests
    start_time = time.time()
    successful = 0
    for _ in range(len(test_case["scenario"]["requests"])):
        msg = Message(role="user", content="test")
        try:
            await rate_limiter.process(msg)
            successful += 1
        except RateLimitError:
            pass
    elapsed_ms = (time.time() - start_time) * 1000

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["all_successful"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]
    assert successful == expected["total_requests"]
    assert expected["min_total_time_ms"] <= elapsed_ms <= expected["max_total_time_ms"]


@pytest.mark.asyncio
async def test_rate_limiter_waits_for_tokens():
    """Test that requests wait when capacity is exceeded."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_waits_for_tokens")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute requests and track timing
    wait_times = []
    for _i in range(len(test_case["scenario"]["requests"])):
        msg = Message(role="user", content="test")
        start = time.time()
        await rate_limiter.process(msg)
        elapsed = (time.time() - start) * 1000
        wait_times.append(elapsed)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["all_successful"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]
    assert expected["sixth_request_waited"]

    # Sixth request (index 5) should have waited
    sixth_wait = wait_times[5]
    assert expected["min_wait_time_ms"] <= sixth_wait <= expected["max_wait_time_ms"]


@pytest.mark.asyncio
async def test_rate_limiter_rejects_on_timeout():
    """Test that requests are rejected when max_wait is exceeded."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_rejects_on_timeout")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute requests
    rejected = 0
    for _ in range(len(test_case["scenario"]["requests"])):
        msg = Message(role="user", content="test")
        try:
            await rate_limiter.process(msg)
        except RateLimitError:
            rejected += 1

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert not expected["all_successful"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]
    assert rejected == expected["rejected_requests"]
    assert expected["third_request_rejected"]


@pytest.mark.asyncio
async def test_rate_limiter_token_refill():
    """Test that tokens refill at configured rate."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_token_refill")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute steps
    request_count = 0
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            msg = Message(role="user", content="test")
            await rate_limiter.process(msg)
            request_count += 1
        elif step["action"] == "wait":
            await asyncio.sleep(step["duration_ms"] / 1000.0)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["all_successful"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]
    assert expected["tokens_refilled"]


@pytest.mark.asyncio
async def test_rate_limiter_burst_capacity():
    """Test that burst capacity allows temporary spikes."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_burst_capacity")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute burst of requests
    start_time = time.time()
    for _ in range(len(test_case["scenario"]["requests"])):
        msg = Message(role="user", content="test")
        await rate_limiter.process(msg)
    elapsed_ms = (time.time() - start_time) * 1000

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["all_successful"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]
    assert expected["burst_handled"]
    assert elapsed_ms <= expected["max_total_time_ms"]


@pytest.mark.asyncio
async def test_rate_limiter_multiple_tokens_per_request():
    """Test that multiple tokens can be consumed per request."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_multiple_tokens_per_request")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute requests
    for _ in range(len(test_case["scenario"]["requests"])):
        msg = Message(role="user", content="test")
        await rate_limiter.process(msg)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["all_successful"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]


@pytest.mark.asyncio
async def test_rate_limiter_metrics_tracking():
    """Test that rate limiter tracks metrics accurately."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "rate_limiter_metrics_tracking")

    # Create mock agent
    mock_agent = MockRateLimiterAgent()

    # Create rate limiter
    config = RateLimiterConfig(
        rate=test_case["config"]["rate"],
        capacity=test_case["config"]["capacity"],
        tokens_per_request=test_case["config"]["tokens_per_request"],
        max_wait_ms=test_case["config"]["max_wait_ms"],
    )
    rate_limiter = RateLimiterDecorator(mock_agent, config)

    # Execute requests
    for _ in range(len(test_case["scenario"]["requests"])):
        msg = Message(role="user", content="test")
        try:
            await rate_limiter.process(msg)
        except RateLimitError:
            pass

    # Verify expected metrics
    expected = test_case["expected_metrics"]
    assert rate_limiter.metrics.total_requests == expected["total_requests"]
    assert rate_limiter.metrics.allowed_requests == expected["allowed_requests"]
    assert rate_limiter.metrics.rejected_requests == expected["rejected_requests"]
    assert rate_limiter.metrics.total_wait_time * 1000 >= expected["total_wait_time_greater_than"]
