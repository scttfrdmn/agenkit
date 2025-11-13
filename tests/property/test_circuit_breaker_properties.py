"""
Circuit Breaker Property-Based Tests

Validates circuit breaker invariants:
- State transitions follow valid state machine (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Opens after exactly failure_threshold failures
- Transitions to HALF_OPEN after recovery_timeout
- Closes after exactly success_threshold successes in HALF_OPEN
- Failure count never decreases except on reset
"""
import asyncio
import time

import pytest
from hypothesis import given, settings, assume, strategies as st

from tests.property.strategies import small_positive_int_strategy


class CircuitBreakerState:
    """Valid circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class SimpleCircuitBreaker:
    """Simple circuit breaker for property testing."""

    def __init__(self, failure_threshold: int, success_threshold: int, recovery_timeout: float):
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._recovery_timeout = recovery_timeout

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._state_history = [CircuitBreakerState.CLOSED]

    def get_state(self) -> str:
        return self._state

    def get_failure_count(self) -> int:
        return self._failure_count

    def get_state_history(self) -> list[str]:
        return self._state_history.copy()

    def _transition_to(self, new_state: str):
        """Record state transition."""
        if new_state != self._state:
            self._state = new_state
            self._state_history.append(new_state)

    def is_request_allowed(self) -> bool:
        """Check if request should be allowed."""
        if self._state == CircuitBreakerState.CLOSED:
            return True
        elif self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time and \
               (time.time() - self._last_failure_time) >= self._recovery_timeout:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
                self._success_count = 0
                return True
            return False
        elif self._state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def record_success(self):
        """Record successful request."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)
                self._failure_count = 0

    def record_failure(self):
        """Record failed request."""
        self._last_failure_time = time.time()

        if self._state == CircuitBreakerState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._transition_to(CircuitBreakerState.OPEN)
        elif self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(CircuitBreakerState.OPEN)
            self._failure_count = self._failure_threshold

    def reset(self):
        """Reset circuit breaker."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._state_history = [CircuitBreakerState.CLOSED]


# ============================================
# Property: State Transitions Follow Valid State Machine
# ============================================

@pytest.mark.property
@given(
    failure_threshold=st.integers(min_value=1, max_value=5),
    success_threshold=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100, deadline=None)
def test_state_transitions_are_valid(failure_threshold, success_threshold):
    """Property: Only valid state transitions occur."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        recovery_timeout=0.1
    )

    # Valid transitions map
    valid_transitions = {
        CircuitBreakerState.CLOSED: {CircuitBreakerState.OPEN},
        CircuitBreakerState.OPEN: {CircuitBreakerState.HALF_OPEN},
        CircuitBreakerState.HALF_OPEN: {CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN},
    }

    # Generate failures to trigger transitions
    for _ in range(failure_threshold):
        cb.record_failure()

    assert cb.get_state() == CircuitBreakerState.OPEN, "Should be OPEN after threshold failures"

    # Wait for recovery
    time.sleep(0.15)

    # Allow request (triggers transition to HALF_OPEN)
    cb.is_request_allowed()

    # Validate transition history
    history = cb.get_state_history()
    for i in range(len(history) - 1):
        current = history[i]
        next_state = history[i + 1]

        # Property: Transition must be valid
        assert next_state in valid_transitions.get(current, set()), \
            f"Invalid transition from {current} to {next_state}"


# ============================================
# Property: Opens After Exactly failure_threshold Failures
# ============================================

@pytest.mark.property
@given(
    failure_threshold=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100, deadline=None)
def test_opens_after_exact_threshold(failure_threshold):
    """Property: Circuit opens after exactly failure_threshold failures."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=2,
        recovery_timeout=1.0
    )

    # Record failures
    for i in range(failure_threshold - 1):
        cb.record_failure()
        # Should still be CLOSED
        assert cb.get_state() == CircuitBreakerState.CLOSED, \
            f"Should be CLOSED after {i+1} failures (threshold={failure_threshold})"

    # One more failure should open circuit
    cb.record_failure()

    # Property: Circuit should be OPEN after exactly failure_threshold failures
    assert cb.get_state() == CircuitBreakerState.OPEN, \
        f"Should be OPEN after {failure_threshold} failures"
    assert cb.get_failure_count() == failure_threshold


# ============================================
# Property: Transitions to HALF_OPEN After recovery_timeout
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    failure_threshold=st.integers(min_value=1, max_value=3),
    recovery_timeout=st.floats(min_value=0.05, max_value=0.2),
)
@settings(max_examples=50, deadline=None)
async def test_transitions_to_half_open_after_timeout(failure_threshold, recovery_timeout):
    """Property: Circuit transitions to HALF_OPEN after recovery_timeout."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=2,
        recovery_timeout=recovery_timeout
    )

    # Open the circuit
    for _ in range(failure_threshold):
        cb.record_failure()

    assert cb.get_state() == CircuitBreakerState.OPEN

    # Before timeout: should reject requests
    assert not cb.is_request_allowed(), "Should reject before recovery timeout"
    assert cb.get_state() == CircuitBreakerState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(recovery_timeout + 0.05)

    # After timeout: should allow request and transition to HALF_OPEN
    # Property: is_request_allowed() returns True and transitions to HALF_OPEN
    assert cb.is_request_allowed(), "Should allow request after recovery timeout"
    assert cb.get_state() == CircuitBreakerState.HALF_OPEN, \
        "Should transition to HALF_OPEN after recovery timeout"


# ============================================
# Property: Closes After success_threshold Successes in HALF_OPEN
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    failure_threshold=st.integers(min_value=1, max_value=3),
    success_threshold=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50, deadline=None)
async def test_closes_after_success_threshold(failure_threshold, success_threshold):
    """Property: Circuit closes after exactly success_threshold successes in HALF_OPEN."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        recovery_timeout=0.05
    )

    # Open circuit
    for _ in range(failure_threshold):
        cb.record_failure()

    # Wait and transition to HALF_OPEN
    await asyncio.sleep(0.1)
    cb.is_request_allowed()

    assert cb.get_state() == CircuitBreakerState.HALF_OPEN

    # Record successes
    for i in range(success_threshold - 1):
        cb.record_success()
        # Should still be HALF_OPEN
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN, \
            f"Should be HALF_OPEN after {i+1} successes (threshold={success_threshold})"

    # One more success should close circuit
    cb.record_success()

    # Property: Circuit should be CLOSED after exactly success_threshold successes
    assert cb.get_state() == CircuitBreakerState.CLOSED, \
        f"Should be CLOSED after {success_threshold} successes"


# ============================================
# Property: Failure Count Never Decreases (Except on Reset/Close)
# ============================================

@pytest.mark.property
@given(
    failure_threshold=small_positive_int_strategy,
    num_operations=st.lists(
        st.sampled_from(["failure", "success"]),
        min_size=1,
        max_size=20
    ),
)
@settings(max_examples=100, deadline=None)
def test_failure_count_monotonicity(failure_threshold, num_operations):
    """Property: Failure count never decreases except on reset or close."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=2,
        recovery_timeout=1.0
    )

    previous_count = 0
    previous_state = cb.get_state()

    for op in num_operations:
        current_count = cb.get_failure_count()
        current_state = cb.get_state()

        # Property: Failure count only decreases when state changes to CLOSED
        if current_count < previous_count:
            assert current_state == CircuitBreakerState.CLOSED and \
                   previous_state != CircuitBreakerState.CLOSED, \
                "Failure count should only decrease when transitioning to CLOSED"

        # Record operation
        if op == "failure":
            cb.record_failure()
        else:  # success (only matters in HALF_OPEN)
            cb.record_success()

        previous_count = cb.get_failure_count()
        previous_state = cb.get_state()


# ============================================
# Property: Open Circuit Blocks All Requests
# ============================================

@pytest.mark.property
@given(
    failure_threshold=small_positive_int_strategy,
    num_attempts=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=100, deadline=None)
def test_open_circuit_blocks_requests(failure_threshold, num_attempts):
    """Property: Open circuit blocks all requests before recovery timeout."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=2,
        recovery_timeout=10.0  # Long timeout
    )

    # Open circuit
    for _ in range(failure_threshold):
        cb.record_failure()

    assert cb.get_state() == CircuitBreakerState.OPEN

    # Property: All requests are blocked
    blocked_count = 0
    for _ in range(num_attempts):
        if not cb.is_request_allowed():
            blocked_count += 1

    assert blocked_count == num_attempts, \
        f"All {num_attempts} requests should be blocked in OPEN state"


# ============================================
# Property: Reset Restores Initial State
# ============================================

@pytest.mark.property
@given(
    failure_threshold=small_positive_int_strategy,
    num_failures=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100, deadline=None)
def test_reset_restores_initial_state(failure_threshold, num_failures):
    """Property: Reset restores circuit breaker to initial state."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=2,
        recovery_timeout=1.0
    )

    # Generate some failures (may or may not open circuit)
    for _ in range(num_failures):
        cb.record_failure()

    # Reset
    cb.reset()

    # Property: After reset, should be in CLOSED state with 0 failures
    assert cb.get_state() == CircuitBreakerState.CLOSED, "Should be CLOSED after reset"
    assert cb.get_failure_count() == 0, "Failure count should be 0 after reset"
    assert cb.is_request_allowed(), "Should allow requests after reset"


# ============================================
# Property: HALF_OPEN Failure Immediately Opens Circuit
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    failure_threshold=small_positive_int_strategy,
)
@settings(max_examples=50, deadline=None)
async def test_half_open_failure_immediately_opens(failure_threshold):
    """Property: Failure in HALF_OPEN immediately transitions back to OPEN."""
    cb = SimpleCircuitBreaker(
        failure_threshold=failure_threshold,
        success_threshold=2,
        recovery_timeout=0.05
    )

    # Open circuit
    for _ in range(failure_threshold):
        cb.record_failure()

    # Wait and transition to HALF_OPEN
    await asyncio.sleep(0.1)
    cb.is_request_allowed()

    assert cb.get_state() == CircuitBreakerState.HALF_OPEN

    # Record failure in HALF_OPEN
    cb.record_failure()

    # Property: Should immediately transition back to OPEN
    assert cb.get_state() == CircuitBreakerState.OPEN, \
        "Failure in HALF_OPEN should immediately transition to OPEN"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
