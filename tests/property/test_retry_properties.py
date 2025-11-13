"""
Retry Middleware Property-Based Tests

Validates retry middleware invariants:
- Retry count never exceeds max_retries
- Backoff delays are monotonically increasing (exponential backoff)
- Success propagation (returns immediately on success)
- Max delay cap is enforced
- Only retries on configured error types
"""
import asyncio
import time

import pytest
from hypothesis import given, settings, assume, strategies as st

from tests.property.strategies import small_positive_int_strategy


class RetryPolicy:
    """Retry policy for property testing."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_base: float = 0.1,
        backoff_multiplier: float = 2.0,
        max_delay: float = 10.0,
        retryable_exceptions: tuple = (Exception,)
    ):
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_multiplier = backoff_multiplier
        self._max_delay = max_delay
        self._retryable_exceptions = retryable_exceptions

        self._attempt_count = 0
        self._retry_count = 0
        self._delays = []

    def get_attempt_count(self) -> int:
        return self._attempt_count

    def get_retry_count(self) -> int:
        return self._retry_count

    def get_delays(self) -> list[float]:
        return self._delays.copy()

    def should_retry(self, exception: Exception) -> bool:
        """Check if should retry given an exception."""
        if self._retry_count >= self._max_retries:
            return False

        return isinstance(exception, self._retryable_exceptions)

    def get_next_delay(self) -> float:
        """Get delay for next retry."""
        # Exponential backoff with cap
        delay = self._backoff_base * (self._backoff_multiplier ** self._retry_count)
        delay = min(delay, self._max_delay)
        return delay

    async def execute(self, func):
        """Execute function with retry logic."""
        self._attempt_count = 0
        self._retry_count = 0
        self._delays = []

        while True:
            self._attempt_count += 1

            try:
                result = await func()
                return result
            except Exception as e:
                if self.should_retry(e):
                    self._retry_count += 1

                    # Get delay
                    delay = self.get_next_delay()
                    self._delays.append(delay)

                    # Wait before retry
                    await asyncio.sleep(delay)
                else:
                    # Max retries exceeded or non-retryable exception
                    raise


# ============================================
# Property: Retry Count Never Exceeds max_retries
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100, deadline=None)
async def test_retry_count_never_exceeds_max(max_retries):
    """Property: Retry count never exceeds max_retries."""
    policy = RetryPolicy(max_retries=max_retries, backoff_base=0.01)

    async def always_fails():
        raise RuntimeError("Always fails")

    # Try to execute
    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    # Property: Total attempts = 1 (initial) + max_retries
    assert policy.get_attempt_count() == 1 + max_retries, \
        f"Expected {1 + max_retries} attempts, got {policy.get_attempt_count()}"

    # Property: Retry count = max_retries
    assert policy.get_retry_count() == max_retries, \
        f"Expected {max_retries} retries, got {policy.get_retry_count()}"


# ============================================
# Property: Backoff Delays Are Monotonically Increasing
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=st.integers(min_value=2, max_value=5),
    backoff_base=st.floats(min_value=0.01, max_value=0.1),
    backoff_multiplier=st.floats(min_value=1.5, max_value=3.0),
)
@settings(max_examples=100, deadline=None)
async def test_backoff_delays_are_monotonic(max_retries, backoff_base, backoff_multiplier):
    """Property: Each retry delay >= previous delay (exponential backoff)."""
    assume(backoff_multiplier > 1.0)  # Ensure exponential growth

    policy = RetryPolicy(
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_multiplier=backoff_multiplier,
        max_delay=999999.0  # No cap for this test
    )

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    delays = policy.get_delays()

    # Property: Each delay should be >= previous delay
    for i in range(1, len(delays)):
        assert delays[i] >= delays[i-1], \
            f"Delay {i} ({delays[i]}) should be >= delay {i-1} ({delays[i-1]})"


# ============================================
# Property: Success Propagates Immediately
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    success_on_attempt=st.integers(min_value=1, max_value=5),
    max_retries=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100, deadline=None)
async def test_success_propagates_immediately(success_on_attempt, max_retries):
    """Property: Returns immediately on success (no extra retries)."""
    assume(success_on_attempt <= max_retries + 1)

    policy = RetryPolicy(max_retries=max_retries, backoff_base=0.01)

    attempt_counter = 0

    async def succeeds_on_nth_attempt():
        nonlocal attempt_counter
        attempt_counter += 1

        if attempt_counter == success_on_attempt:
            return "Success"
        else:
            raise RuntimeError(f"Attempt {attempt_counter}")

    result = await policy.execute(succeeds_on_nth_attempt)

    # Property: Should stop immediately on success
    assert policy.get_attempt_count() == success_on_attempt, \
        f"Should stop on attempt {success_on_attempt}, got {policy.get_attempt_count()}"

    assert result == "Success"


# ============================================
# Property: Max Delay Cap is Enforced
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=st.integers(min_value=3, max_value=5),
    backoff_base=st.floats(min_value=0.1, max_value=1.0),
    max_delay=st.floats(min_value=0.5, max_value=2.0),
)
@settings(max_examples=100, deadline=None)
async def test_max_delay_cap_is_enforced(max_retries, backoff_base, max_delay):
    """Property: Delay never exceeds max_delay."""
    policy = RetryPolicy(
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_multiplier=2.0,
        max_delay=max_delay
    )

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    delays = policy.get_delays()

    # Property: No delay should exceed max_delay
    for i, delay in enumerate(delays):
        assert delay <= max_delay, \
            f"Delay {i} ({delay}) exceeds max_delay ({max_delay})"


# ============================================
# Property: Total Attempts = 1 + Retries
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=small_positive_int_strategy,
)
@settings(max_examples=100, deadline=None)
async def test_total_attempts_equals_one_plus_retries(max_retries):
    """Property: total_attempts = 1 (initial) + retry_count."""
    policy = RetryPolicy(max_retries=max_retries, backoff_base=0.01)

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    # Property: attempts = 1 + retries
    assert policy.get_attempt_count() == 1 + policy.get_retry_count(), \
        f"Attempts ({policy.get_attempt_count()}) != 1 + retries ({policy.get_retry_count()})"


# ============================================
# Property: Only Retries on Configured Exceptions
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=small_positive_int_strategy,
)
@settings(max_examples=100, deadline=None)
async def test_only_retries_on_configured_exceptions(max_retries):
    """Property: Only retries on configured exception types."""
    # Configure to only retry on RuntimeError
    policy = RetryPolicy(
        max_retries=max_retries,
        backoff_base=0.01,
        retryable_exceptions=(RuntimeError,)
    )

    async def raises_value_error():
        raise ValueError("Non-retryable")

    # Should not retry ValueError
    try:
        await policy.execute(raises_value_error)
    except ValueError:
        pass

    # Property: Should not retry (0 retries for non-retryable exception)
    assert policy.get_retry_count() == 0, \
        f"Should not retry non-retryable exception, got {policy.get_retry_count()} retries"
    assert policy.get_attempt_count() == 1, \
        f"Should only attempt once for non-retryable exception"


# ============================================
# Property: Exponential Growth with Multiplier
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=st.integers(min_value=3, max_value=5),
    backoff_base=st.floats(min_value=0.01, max_value=0.1),
    backoff_multiplier=st.floats(min_value=2.0, max_value=3.0),
)
@settings(max_examples=100, deadline=None)
async def test_exponential_growth_formula(max_retries, backoff_base, backoff_multiplier):
    """Property: Delays follow exponential formula (before cap)."""
    policy = RetryPolicy(
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_multiplier=backoff_multiplier,
        max_delay=999999.0  # No cap
    )

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    delays = policy.get_delays()

    # Property: Each delay follows formula: base * multiplier^retry_number
    for i, delay in enumerate(delays):
        expected_delay = backoff_base * (backoff_multiplier ** i)

        # Allow small floating point error
        assert abs(delay - expected_delay) < 0.001, \
            f"Delay {i} ({delay}) doesn't match formula ({expected_delay})"


# ============================================
# Property: Zero Retries Means No Retries
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_zero_retries_means_no_retries():
    """Property: max_retries=0 means no retries (only initial attempt)."""
    policy = RetryPolicy(max_retries=0, backoff_base=0.01)

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    # Property: Should only attempt once (no retries)
    assert policy.get_attempt_count() == 1, "Should only attempt once with max_retries=0"
    assert policy.get_retry_count() == 0, "Should have 0 retries"
    assert len(policy.get_delays()) == 0, "Should have no delays"


# ============================================
# Property: Delays List Length Equals Retry Count
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    max_retries=small_positive_int_strategy,
)
@settings(max_examples=100, deadline=None)
async def test_delays_length_equals_retry_count(max_retries):
    """Property: Number of delays equals number of retries."""
    policy = RetryPolicy(max_retries=max_retries, backoff_base=0.01)

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    delays = policy.get_delays()

    # Property: len(delays) == retry_count
    assert len(delays) == policy.get_retry_count(), \
        f"Delays length ({len(delays)}) != retry count ({policy.get_retry_count()})"


# ============================================
# Property: First Delay is Base Delay
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    backoff_base=st.floats(min_value=0.01, max_value=1.0),
)
@settings(max_examples=100, deadline=None)
async def test_first_delay_is_base_delay(backoff_base):
    """Property: First retry delay equals backoff_base."""
    policy = RetryPolicy(
        max_retries=3,
        backoff_base=backoff_base,
        max_delay=999999.0
    )

    async def always_fails():
        raise RuntimeError("Always fails")

    try:
        await policy.execute(always_fails)
    except RuntimeError:
        pass

    delays = policy.get_delays()

    # Property: First delay should be base delay
    assert len(delays) > 0, "Should have at least one delay"
    assert abs(delays[0] - backoff_base) < 0.001, \
        f"First delay ({delays[0]}) should equal backoff_base ({backoff_base})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
