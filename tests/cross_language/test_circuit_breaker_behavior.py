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

    # Execute requests, recording each outcome so per-request claims can be checked
    outcomes = []
    failed = 0
    rejected = 0
    for _ in range(len(test_case["scenario"]["agent_responses"])):
        msg = Message(role="user", content="test")
        try:
            await circuit_breaker.process(msg)
            outcomes.append("ok")
        except CircuitBreakerError:
            rejected += 1
            outcomes.append("rejected")
        except Exception:
            failed += 1
            outcomes.append("failed")

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.metrics.total_requests == expected["total_requests"]
    assert circuit_breaker.metrics.failed_requests == expected["failed_requests"]
    assert circuit_breaker.metrics.rejected_requests == expected["rejected_requests"]

    # `assert expected["fourth_request_rejected"]` was a tautology: it asserted a `true`
    # literal read out of the fixture, so it passed with the middleware deleted (#791).
    # Check the actual claim — the fourth request was rejected by the open circuit, not
    # merely failed by the inner agent (whose fourth scripted response is a success).
    if expected.get("fourth_request_rejected"):
        assert outcomes[3] == "rejected", f"expected 4th request rejected, got {outcomes}"


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

    # Execute steps, recording the state seen before each request so the transition
    # path — not just the final state — can be checked
    observed_states = []
    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            observed_states.append(circuit_breaker.state)
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

    # `assert expected["recovery_successful"]` was a tautology (#791). The real claim is
    # that the circuit opened, then recovered *through* half-open — a breaker that never
    # opened would also end CLOSED and pass the final-state check alone.
    if expected.get("recovery_successful"):
        assert CircuitState.OPEN in observed_states, (
            f"circuit never opened; states seen: {observed_states}"
        )
        assert circuit_breaker.metrics.state_changes.get("open->half_open", 0) >= 1, (
            f"circuit never probed half-open: {circuit_breaker.metrics.state_changes}"
        )
        assert circuit_breaker.metrics.state_changes.get("half_open->closed", 0) >= 1, (
            f"circuit never closed from half-open: {circuit_breaker.metrics.state_changes}"
        )


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

    # Execute steps.
    #
    # Counting half-open successes needs the state *around* each call, not just before
    # it. The OPEN -> HALF_OPEN transition happens inside `process`, so the first
    # half-open probe still reads OPEN beforehand: sampling only the prior state misses
    # it and undercounts by one. (The previous `was_half_open` flag was also sticky —
    # once set it never cleared, so it would have counted later CLOSED-state successes
    # as half-open ones too.) A request ran as a half-open probe if it started half-open,
    # or if it started open and left the circuit no longer open.
    successful_in_half_open = 0
    was_half_open = False

    for step in test_case["scenario"]["steps"]:
        if step["action"] == "request":
            msg = Message(role="user", content="test")
            state_before = circuit_breaker.state
            succeeded = False
            try:
                await circuit_breaker.process(msg)
                succeeded = True
            except Exception:
                pass
            state_after = circuit_breaker.state

            ran_in_half_open = state_before == CircuitState.HALF_OPEN or (
                state_before == CircuitState.OPEN and state_after != CircuitState.OPEN
            )
            if ran_in_half_open:
                was_half_open = True
                if succeeded:
                    successful_in_half_open += 1
        elif step["action"] == "wait":
            await asyncio.sleep(step["duration_ms"] / 1000.0)

    # Verify expected behavior
    expected = test_case["expected_behavior"]
    assert circuit_breaker.state == CircuitState.CLOSED

    # `assert expected["circuit_fully_recovered"]` was a tautology (#791). Check the two
    # real claims: the circuit did close from half-open, and it took the configured
    # number of half-open successes to do it.
    if expected.get("circuit_fully_recovered"):
        assert was_half_open, "circuit never entered half-open"
        assert circuit_breaker.metrics.state_changes.get("half_open->closed", 0) >= 1, (
            f"circuit never closed from half-open: {circuit_breaker.metrics.state_changes}"
        )
    if "total_successful_in_half_open" in expected:
        assert successful_in_half_open == expected["total_successful_in_half_open"]


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

    # `assert expected["reopened_after_partial_recovery"]` was a tautology (#791). The
    # real claim is the full path closed -> open -> half_open -> open: a breaker that
    # opened once and never probed would also end OPEN and pass the final-state check.
    if expected.get("reopened_after_partial_recovery"):
        changes = circuit_breaker.metrics.state_changes
        assert changes.get("closed->open", 0) >= 1, f"never opened: {changes}"
        assert changes.get("open->half_open", 0) >= 1, f"never probed half-open: {changes}"
        assert changes.get("half_open->open", 0) >= 1, f"never reopened from half-open: {changes}"


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

    # Assert the state_changes map itself, not just the scalar counters. This field is
    # the cross-language transition-key contract; it went unasserted in all five
    # harnesses long enough for four different key formats to appear (#791).
    assert circuit_breaker.metrics.state_changes == expected["state_changes"]
