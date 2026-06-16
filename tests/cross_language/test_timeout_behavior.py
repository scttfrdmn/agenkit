"""
Cross-language timeout behavior tests for Python

Validates that Agenkit's Python timeout middleware behaves consistently
with the cross-language timeout behavior specification.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import pytest

from agenkit import Agent, Message
from agenkit.middleware import TimeoutConfig, TimeoutDecorator


class MockTimeoutAgent(Agent):
    """Mock agent that simulates delays for timeout testing"""

    def __init__(self, delay_ms: int, response: dict[str, Any]):
        self.delay_ms = delay_ms
        self.response = response
        self.call_count = 0

    def name(self) -> str:
        """Return agent name"""
        return "mock-timeout-agent"

    async def process(self, message: Message) -> Message:
        """Process with configurable delay"""
        self.call_count += 1

        # Simulate delay
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)

        # Return response or raise error
        if self.response.get("success"):
            return Message(role="agent", content=self.response["content"])
        else:
            raise Exception(self.response["error"])


def load_fixtures():
    """Load timeout behavior fixtures"""
    fixtures_path = Path(__file__).parent / "fixtures" / "timeout_behavior.json"
    with open(fixtures_path) as f:
        return json.load(f)


def find_test_case(fixtures: dict, test_id: str) -> dict:
    """Find a specific test case by ID"""
    for test_case in fixtures["test_cases"]:
        if test_case["id"] == test_id:
            return test_case
    raise ValueError(f"Test case not found: {test_id}")


@pytest.mark.asyncio
async def test_success_within_limit():
    """Test request completes within timeout"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_success_within_limit")

    # Create mock agent
    scenario = test_case["scenario"]
    mock_agent = MockTimeoutAgent(
        delay_ms=scenario["agent_delay_ms"],
        response=scenario["agent_response"],
    )

    # Wrap with timeout
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])
    timeout_agent = TimeoutDecorator(mock_agent, config)

    # Execute
    start = time.time()
    result = await timeout_agent.process(Message(role="user", content="test"))
    elapsed_ms = (time.time() - start) * 1000

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["successful"]
    assert not expected["timed_out"]
    assert result.content == expected["final_response"]
    assert expected["min_elapsed_ms"] <= elapsed_ms <= expected["max_elapsed_ms"]


@pytest.mark.asyncio
async def test_timeout_exceeded():
    """Test request exceeds timeout limit"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_exceeded")

    # Create mock agent
    scenario = test_case["scenario"]
    mock_agent = MockTimeoutAgent(
        delay_ms=scenario["agent_delay_ms"],
        response=scenario["agent_response"],
    )

    # Wrap with timeout
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])
    timeout_agent = TimeoutDecorator(mock_agent, config)

    # Execute and expect timeout
    start = time.time()
    expected = test_case["expected_behavior"]

    with pytest.raises(Exception) as exc_info:
        await timeout_agent.process(Message(role="user", content="test"))

    elapsed_ms = (time.time() - start) * 1000

    # Verify timeout error
    assert not expected["successful"]
    assert expected["timed_out"]
    assert expected["error_message_contains"] in str(exc_info.value)
    assert expected["min_elapsed_ms"] <= elapsed_ms <= expected["max_elapsed_ms"]


@pytest.mark.asyncio
async def test_timeout_exactly_at_limit():
    """Test request completes exactly at timeout boundary"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_exactly_at_limit")

    # Create mock agent
    scenario = test_case["scenario"]
    mock_agent = MockTimeoutAgent(
        delay_ms=scenario["agent_delay_ms"],
        response=scenario["agent_response"],
    )

    # Wrap with timeout
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])
    timeout_agent = TimeoutDecorator(mock_agent, config)

    # Execute
    start = time.time()
    result = await timeout_agent.process(Message(role="user", content="test"))
    elapsed_ms = (time.time() - start) * 1000

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["successful"]
    assert not expected["timed_out"]
    assert result.content == expected["final_response"]
    assert expected["min_elapsed_ms"] <= elapsed_ms <= expected["max_elapsed_ms"]


@pytest.mark.asyncio
async def test_zero_delay():
    """Test request with zero delay completes immediately"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_zero_delay")

    # Create mock agent
    scenario = test_case["scenario"]
    mock_agent = MockTimeoutAgent(
        delay_ms=scenario["agent_delay_ms"],
        response=scenario["agent_response"],
    )

    # Wrap with timeout
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])
    timeout_agent = TimeoutDecorator(mock_agent, config)

    # Execute
    start = time.time()
    result = await timeout_agent.process(Message(role="user", content="test"))
    elapsed_ms = (time.time() - start) * 1000

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert expected["successful"]
    assert not expected["timed_out"]
    assert result.content == expected["final_response"]
    assert elapsed_ms <= expected["max_elapsed_ms"]


@pytest.mark.asyncio
async def test_agent_error():
    """Test agent error propagates before timeout"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_agent_error")

    # Create mock agent
    scenario = test_case["scenario"]
    mock_agent = MockTimeoutAgent(
        delay_ms=scenario["agent_delay_ms"],
        response=scenario["agent_response"],
    )

    # Wrap with timeout
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])
    timeout_agent = TimeoutDecorator(mock_agent, config)

    # Execute and expect agent error
    start = time.time()
    expected = test_case["expected_behavior"]

    with pytest.raises(Exception) as exc_info:
        await timeout_agent.process(Message(role="user", content="test"))

    elapsed_ms = (time.time() - start) * 1000

    # Verify agent error (not timeout)
    assert not expected["successful"]
    assert not expected["timed_out"]
    assert expected["error_message_contains"] in str(exc_info.value)
    assert expected["min_elapsed_ms"] <= elapsed_ms <= expected["max_elapsed_ms"]


@pytest.mark.asyncio
async def test_very_short_timeout():
    """Test very short timeout (10ms)"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_very_short")

    # Create mock agent
    scenario = test_case["scenario"]
    mock_agent = MockTimeoutAgent(
        delay_ms=scenario["agent_delay_ms"],
        response=scenario["agent_response"],
    )

    # Wrap with timeout
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])
    timeout_agent = TimeoutDecorator(mock_agent, config)

    # Execute and expect timeout
    start = time.time()
    expected = test_case["expected_behavior"]

    with pytest.raises(Exception):
        await timeout_agent.process(Message(role="user", content="test"))

    elapsed_ms = (time.time() - start) * 1000

    # Verify timeout
    assert not expected["successful"]
    assert expected["timed_out"]
    # Note: Very short timeouts might have wider tolerance
    assert expected["min_elapsed_ms"] <= elapsed_ms <= expected["max_elapsed_ms"] + 20


@pytest.mark.asyncio
async def test_metrics_tracking():
    """Test metrics track timeouts correctly"""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "timeout_metrics_tracking")

    # Create timeout decorator
    config = TimeoutConfig(timeout_ms=test_case["config"]["timeout_ms"])

    # Process multiple requests
    results = []
    for request in test_case["scenario"]["requests"]:
        mock_agent = MockTimeoutAgent(
            delay_ms=request["agent_delay_ms"],
            response=request["agent_response"],
        )
        timeout_agent = TimeoutDecorator(mock_agent, config)

        try:
            result = await timeout_agent.process(Message(role="user", content="test"))
            results.append({"success": True, "content": result.content})
        except Exception as e:
            results.append({"success": False, "error": str(e)})

    # Count outcomes
    successful = sum(1 for r in results if r["success"])
    timed_out = sum(1 for r in results if not r["success"])

    # Verify metrics
    expected_metrics = test_case["expected_metrics"]
    assert len(results) == expected_metrics["total_requests"]
    assert successful == expected_metrics["successful_requests"]
    assert timed_out == expected_metrics["timed_out_requests"]
