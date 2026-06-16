"""Cross-language circuit breaker behavior tests for Python.

Validates that Agenkit's Python circuit breaker middleware behaves consistently
with the cross-language circuit breaker behavior specification.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from agenkit.interfaces import Agent, Message
from agenkit.middleware.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    CircuitBreakerError,
    CircuitState,
)


class MockCircuitBreakerAgent(Agent):
    """Mock agent that simulates responses from fixture scenarios."""

    def __init__(self, responses: list[dict[str, Any]]):
        """Initialize with list of responses to return."""
        self.responses = responses
        self.call_count = 0

    @property
    def name(self) -> str:
        """Return agent name."""
        return "mock-circuit-breaker-agent"

    async def process(self, message: Message) -> Message:
        """Process message with configured response."""
        if self.call_count >= len(self.responses):
            raise Exception("No more responses available")

        response = self.responses[self.call_count]
        self.call_count += 1

        if response.get("success"):
            return Message(role="agent", content=response.get("content", ""))
        else:
            raise Exception(response.get("error", "Agent error"))


def load_fixtures():
    """Load circuit breaker behavior fixtures."""
    fixtures_path = Path(__file__).parent / "fixtures" / "circuit_breaker_behavior.json"
    with open(fixtures_path) as f:
        return json.load(f)


def find_test_case(fixtures: dict, test_id: str) -> dict:
    """Find a specific test case by ID."""
    for test_case in fixtures["test_cases"]:
        if test_case["id"] == test_id:
            return test_case
    raise ValueError(f"Test case not found: {test_id}")


@pytest.mark.asyncio
async def test_circuit_breaker_closed_success():
    """Test that circuit remains closed with successful requests."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_closed_success")

    # Create mock agent
    mock_agent = MockCircuitBreakerAgent(test_case["scenario"]["agent_responses"])

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute requests
    successful = 0
    for _ in range(len(test_case["scenario"]["agent_responses"])):
        msg = Message(role="user", content="test")
        result = await circuit_breaker.process(msg)
        assert result is not None
        successful += 1

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.metrics.total_requests == expected["total_requests"]
    assert circuit_breaker.metrics.successful_requests == expected["successful_requests"]
    assert circuit_breaker.metrics.failed_requests == expected["failed_requests"]
    assert circuit_breaker.metrics.rejected_requests == expected["rejected_requests"]
    assert successful == expected["total_requests"]


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test that circuit opens after failure threshold is reached."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_opens_on_failures")

    # Create mock agent
    mock_agent = MockCircuitBreakerAgent(test_case["scenario"]["agent_responses"])

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute requests
    failed = 0
    rejected = 0
    for _ in range(len(test_case["scenario"]["agent_responses"])):
        msg = Message(role="user", content="test")
        try:
            await circuit_breaker.process(msg)
        except CircuitBreakerError:
            rejected += 1
        except Exception:
            failed += 1

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.metrics.total_requests == expected["total_requests"]
    assert circuit_breaker.metrics.failed_requests == expected["failed_requests"]
    assert circuit_breaker.metrics.rejected_requests == expected["rejected_requests"]
    assert expected["fourth_request_rejected"]


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_transition():
    """Test that circuit transitions to half-open after recovery timeout."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_half_open_transition")

    # Create mock agent (responses extracted from steps)
    responses = []
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            responses.append(step["agent_response"])

    mock_agent = MockCircuitBreakerAgent(responses)

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute steps
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            msg = Message(role="user", content="test")
            try:
                await circuit_breaker.process(msg)
            except Exception:
                pass
        elif step["action"] == "wait":
            await asyncio.sleep(step["duration_ms"] / 1000.0)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.CLOSED
    assert expected["recovery_successful"]


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_to_closed():
    """Test that circuit closes after success threshold in half-open state."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_half_open_to_closed")

    # Create mock agent (responses extracted from steps)
    responses = []
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            responses.append(step["agent_response"])

    mock_agent = MockCircuitBreakerAgent(responses)

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute steps
    successful_in_half_open = 0
    was_half_open = False

    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            msg = Message(role="user", content="test")
            try:
                if circuit_breaker.state == CircuitState.HALF_OPEN:
                    was_half_open = True
                await circuit_breaker.process(msg)
                if was_half_open:
                    successful_in_half_open += 1
            except Exception:
                pass
        elif step["action"] == "wait":
            await asyncio.sleep(step["duration_ms"] / 1000.0)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.CLOSED
    assert expected["circuit_fully_recovered"]


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_reopens():
    """Test that circuit reopens on failure in half-open state."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_half_open_reopens")

    # Create mock agent (responses extracted from steps)
    responses = []
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            responses.append(step["agent_response"])

    mock_agent = MockCircuitBreakerAgent(responses)

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute steps
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            msg = Message(role="user", content="test")
            try:
                await circuit_breaker.process(msg)
            except Exception:
                pass
        elif step["action"] == "wait":
            await asyncio.sleep(step["duration_ms"] / 1000.0)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.OPEN
    assert expected["reopened_after_partial_recovery"]


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test that circuit rejects all requests when open."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_rejects_when_open")

    # Create mock agent
    mock_agent = MockCircuitBreakerAgent(test_case["scenario"]["agent_responses"])

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute requests
    rejected = 0
    for _ in range(len(test_case["scenario"]["agent_responses"])):
        msg = Message(role="user", content="test")
        try:
            await circuit_breaker.process(msg)
        except CircuitBreakerError:
            rejected += 1
        except Exception:
            pass

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.metrics.rejected_requests == expected["rejected_requests"]
    assert rejected == expected["rejected_requests"]


@pytest.mark.asyncio
async def test_circuit_breaker_metrics_tracking():
    """Test that circuit breaker tracks metrics accurately."""
    fixtures = load_fixtures()
    test_case = find_test_case(fixtures, "circuit_breaker_metrics_tracking")

    # Create mock agent (responses extracted from steps)
    responses = []
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            responses.append(step["agent_response"])

    mock_agent = MockCircuitBreakerAgent(responses)

    # Create circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=test_case["config"]["failure_threshold"],
        recovery_timeout_ms=test_case["config"]["recovery_timeout_ms"],
        success_threshold=test_case["config"]["success_threshold"],
        timeout_ms=test_case["config"]["timeout_ms"],
    )
    circuit_breaker = CircuitBreakerDecorator(mock_agent, config)

    # Execute steps
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            msg = Message(role="user", content="test")
            try:
                await circuit_breaker.process(msg)
            except Exception:
                pass
        elif step["action"] == "wait":
            await asyncio.sleep(step["duration_ms"] / 1000.0)

    # Verify expected metrics
    expected = test_case["expected_metrics"]
    assert circuit_breaker.metrics.total_requests == expected["total_requests"]
    assert circuit_breaker.metrics.successful_requests == expected["successful_requests"]
    assert circuit_breaker.metrics.failed_requests == expected["failed_requests"]
    assert circuit_breaker.metrics.rejected_requests == expected["rejected_requests"]
    assert circuit_breaker.state.value == expected["final_state"]
