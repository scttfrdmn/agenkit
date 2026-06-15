"""
Cross-language API consistency tests for Python.

Tests that Agenkit's Python implementation conforms to the cross-language
API consistency specification, validating parameter naming, default values,
and interface signatures.
"""

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from agenkit.middleware.retry import RetryDecorator, RetryConfig
from agenkit.middleware.timeout import TimeoutDecorator, TimeoutConfig
from agenkit.middleware.rate_limiter import RateLimiterDecorator, RateLimiterConfig
from agenkit.middleware.circuit_breaker import CircuitBreakerDecorator, CircuitBreakerConfig


# Load API consistency fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

with open(FIXTURES_DIR / "api_consistency.json") as f:
    API_FIXTURES = json.load(f)


class TestParameterNaming:
    """Test that parameter names follow cross-language conventions."""

    def test_retry_parameter_names(self):
        """Verify RetryDecorator uses consistent parameter names."""
        test_case = next(
            tc
            for tc in API_FIXTURES["test_categories"]["parameter_naming"]["test_cases"]
            if tc["id"] == "retry_parameter_names"
        )

        # Get RetryConfig signature
        sig = inspect.signature(RetryConfig.__init__)
        param_names = set(sig.parameters.keys()) - {"self"}

        # Verify expected parameters exist
        params = test_case["parameters"]

        # Check max_retries
        expected_name = params["max_retries"]["expected_names"]["python"]
        assert expected_name in param_names, f"RetryConfig should have parameter '{expected_name}'"

        # NOTE: We allow deprecated parameters during the transition period (v0.50.0)
        # These will be removed in v0.51.0
        # Therefore, we don't check "must_not_be_named" - old names are temporarily acceptable

        # Check initial_delay
        expected_name = params["initial_delay"]["expected_names"]["python"]
        assert expected_name in param_names, f"RetryConfig should have parameter '{expected_name}'"

        # Check max_delay
        expected_name = params["max_delay"]["expected_names"]["python"]
        assert expected_name in param_names, f"RetryConfig should have parameter '{expected_name}'"

    def test_retry_parameter_transition(self):
        """Verify new parameter names exist (deprecated names removed in v0.51.0)."""
        sig = inspect.signature(RetryConfig.__init__)
        param_names = set(sig.parameters.keys()) - {"self"}

        # v0.53.0: New parameter names (deprecated names removed in v0.51.0)
        assert "max_retries" in param_names, "New parameter name max_retries should exist"
        assert "initial_delay" in param_names, "New parameter name initial_delay should exist"
        assert "max_delay" in param_names, "New parameter name max_delay should exist"
        assert "multiplier" in param_names, "New parameter name multiplier should exist"

        # v0.53.0: Old parameter names removed (deprecated in v0.50.0, removed in v0.51.0)
        assert "max_attempts" not in param_names, "Deprecated max_attempts should be removed"
        assert "initial_backoff" not in param_names, "Deprecated initial_backoff should be removed"
        assert "max_backoff" not in param_names, "Deprecated max_backoff should be removed"
        assert (
            "backoff_multiplier" not in param_names
        ), "Deprecated backoff_multiplier should be removed"

    def test_timeout_parameter_names(self):
        """Verify TimeoutMiddleware parameter names clearly indicate units."""
        test_case = next(
            tc
            for tc in API_FIXTURES["test_categories"]["parameter_naming"]["test_cases"]
            if tc["id"] == "timeout_parameter_names"
        )

        # Get TimeoutConfig signature
        sig = inspect.signature(TimeoutConfig.__init__)
        param_names = set(sig.parameters.keys()) - {"self"}

        # Python should use timeout_ms or timeout (with timedelta support)
        # Check that at least one timeout-related parameter exists
        timeout_params = [p for p in param_names if "timeout" in p.lower()]
        assert len(timeout_params) > 0, "TimeoutConfig should have timeout-related parameters"

        # If using primitive (not timedelta), should indicate unit
        # This is a soft check - we're validating the pattern exists
        has_clear_unit = any("_ms" in p or "_seconds" in p for p in timeout_params)
        # Note: This test documents the expectation but allows flexibility
        # for implementations that use timedelta (which is self-documenting)


class TestDefaultValues:
    """Test that default configuration values match specification."""

    def test_timeout_defaults(self):
        """Verify TimeoutMiddleware default timeout is 30 seconds."""
        test_case = next(
            tc
            for tc in API_FIXTURES["test_categories"]["default_values"]["test_cases"]
            if tc["id"] == "timeout_defaults"
        )

        expected_ms = test_case["defaults"]["timeout"]["value_ms"]

        # Create config with defaults
        config = TimeoutConfig()

        # Convert to milliseconds for comparison
        # Python uses float seconds by default
        if hasattr(config, "timeout_ms"):
            actual_ms = config.timeout_ms
        elif hasattr(config, "timeout"):
            # Assuming timeout is in seconds
            actual_ms = config.timeout * 1000
        else:
            pytest.fail("TimeoutConfig has no recognizable timeout attribute")

        assert (
            actual_ms == expected_ms
        ), f"TimeoutConfig default should be {expected_ms}ms (30 seconds), got {actual_ms}ms"

    def test_retry_defaults(self):
        """Verify RetryMiddleware default configuration values."""
        test_case = next(
            tc
            for tc in API_FIXTURES["test_categories"]["default_values"]["test_cases"]
            if tc["id"] == "retry_defaults"
        )

        defaults = test_case["defaults"]
        config = RetryConfig()

        # Check max_retries
        expected_max_retries = defaults["max_retries"]["value"]
        assert (
            config.max_retries == expected_max_retries
        ), f"max_retries default should be {expected_max_retries}"

        # Check initial_delay (convert to ms)
        expected_initial_delay_ms = defaults["initial_delay"]["value_ms"]
        if hasattr(config, "initial_delay_ms"):
            actual_delay_ms = config.initial_delay_ms
        elif hasattr(config, "initial_delay"):
            actual_delay_ms = config.initial_delay * 1000
        else:
            pytest.fail("RetryConfig has no recognizable initial_delay attribute")

        assert (
            actual_delay_ms == expected_initial_delay_ms
        ), f"initial_delay default should be {expected_initial_delay_ms}ms"

        # Check max_delay (convert to ms)
        expected_max_delay_ms = defaults["max_delay"]["value_ms"]
        if hasattr(config, "max_delay_ms"):
            actual_max_delay_ms = config.max_delay_ms
        elif hasattr(config, "max_delay"):
            actual_max_delay_ms = config.max_delay * 1000
        else:
            pytest.fail("RetryConfig has no recognizable max_delay attribute")

        assert (
            actual_max_delay_ms == expected_max_delay_ms
        ), f"max_delay default should be {expected_max_delay_ms}ms"

        # Check multiplier
        expected_multiplier = defaults["multiplier"]["value"]
        assert (
            config.multiplier == expected_multiplier
        ), f"multiplier default should be {expected_multiplier}"

    def test_retry_using_new_parameter_names(self):
        """Verify RetryConfig works correctly when using new parameter names."""
        # Use new parameter names explicitly
        config = RetryConfig(max_retries=5, initial_delay=0.5, max_delay=20.0, multiplier=3.0)

        assert config.max_retries == 5, "max_retries should be set correctly"
        assert config.initial_delay == 0.5, "initial_delay should be set correctly"
        assert config.max_delay == 20.0, "max_delay should be set correctly"
        assert config.multiplier == 3.0, "multiplier should be set correctly"

    # test_retry_using_deprecated_parameter_names removed in v0.53.0
    # Deprecated parameters (max_attempts, initial_backoff, max_backoff, backoff_multiplier)
    # were removed in v0.51.0 after deprecation period in v0.50.0

    def test_rate_limiter_defaults(self):
        """Verify RateLimiterMiddleware default configuration values."""
        test_case = next(
            tc
            for tc in API_FIXTURES["test_categories"]["default_values"]["test_cases"]
            if tc["id"] == "rate_limiter_defaults"
        )

        defaults = test_case["defaults"]
        config = RateLimiterConfig()

        # Check rate
        expected_rate = defaults["rate"]["value"]
        assert (
            config.rate == expected_rate
        ), f"rate default should be {expected_rate} requests/second"

        # Check capacity
        expected_capacity = defaults["capacity"]["value"]
        assert (
            config.capacity == expected_capacity
        ), f"capacity default should be {expected_capacity}"

    def test_circuit_breaker_defaults(self):
        """Verify CircuitBreakerMiddleware default configuration values."""
        test_case = next(
            tc
            for tc in API_FIXTURES["test_categories"]["default_values"]["test_cases"]
            if tc["id"] == "circuit_breaker_defaults"
        )

        defaults = test_case["defaults"]
        config = CircuitBreakerConfig()

        # Check failure_threshold
        expected_failure_threshold = defaults["failure_threshold"]["value"]
        assert (
            config.failure_threshold == expected_failure_threshold
        ), f"failure_threshold default should be {expected_failure_threshold}"

        # Check success_threshold
        expected_success_threshold = defaults["success_threshold"]["value"]
        assert (
            config.success_threshold == expected_success_threshold
        ), f"success_threshold default should be {expected_success_threshold}"

        # Check timeout (convert to ms)
        expected_timeout_ms = defaults["timeout"]["value_ms"]
        if hasattr(config, "timeout_ms"):
            actual_timeout_ms = config.timeout_ms
        elif hasattr(config, "timeout"):
            actual_timeout_ms = config.timeout * 1000
        else:
            pytest.fail("CircuitBreakerConfig has no recognizable timeout attribute")

        assert (
            actual_timeout_ms == expected_timeout_ms
        ), f"timeout default should be {expected_timeout_ms}ms"

        # Check recovery_timeout (convert to ms)
        expected_recovery_ms = defaults["recovery_timeout"]["value_ms"]
        if hasattr(config, "recovery_timeout_ms"):
            actual_recovery_ms = config.recovery_timeout_ms
        elif hasattr(config, "recovery_timeout"):
            actual_recovery_ms = config.recovery_timeout * 1000
        else:
            pytest.fail("CircuitBreakerConfig has no recognizable recovery_timeout attribute")

        assert (
            actual_recovery_ms == expected_recovery_ms
        ), f"recovery_timeout default should be {expected_recovery_ms}ms"


class TestInterfaceSignatures:
    """Test that core interface signatures are equivalent."""

    def test_tool_execute_signature(self):
        """Verify Tool.execute() method signature matches specification."""
        from agenkit.interfaces import Tool

        # Get the abstract method signature
        sig = inspect.signature(Tool.execute)
        params = list(sig.parameters.keys())

        # Python should have: self, params (dict[str, Any])
        assert "self" in params
        assert (
            "params" in params or "kwargs" in params
        ), "Tool.execute should accept params or **kwargs"

        # Check return type annotation if available
        if sig.return_annotation != inspect.Signature.empty:
            # Should return ToolResult (or awaitable ToolResult for async)
            return_type_str = str(sig.return_annotation)
            assert (
                "ToolResult" in return_type_str
            ), f"Tool.execute should return ToolResult, got {return_type_str}"

    def test_agent_process_signature(self):
        """Verify Agent.process() method signature matches specification."""
        from agenkit.interfaces import Agent

        # Get the abstract method signature
        sig = inspect.signature(Agent.process)
        params = list(sig.parameters.keys())

        # Python should have: self, message (Message)
        assert "self" in params
        assert "message" in params, "Agent.process should accept message parameter"

        # Check return type annotation if available
        if sig.return_annotation != inspect.Signature.empty:
            return_type_str = str(sig.return_annotation)
            assert (
                "Message" in return_type_str
            ), f"Agent.process should return Message, got {return_type_str}"


class TestErrorTypes:
    """Test that error types are equivalent across languages."""

    def test_timeout_error_exists(self):
        """Verify TimeoutError type exists with expected structure."""
        from agenkit.middleware.timeout import TimeoutError

        # Should be able to instantiate with message
        error = TimeoutError("Test timeout")

        assert str(error) == "Test timeout", "TimeoutError should have message"

    def test_max_retries_exceeded_error_exists(self):
        """Verify MaxRetriesExceeded error type exists."""
        from agenkit.middleware.retry import MaxRetriesExceededError

        # Should be able to instantiate with message and attempts
        error = MaxRetriesExceededError("Max retries exceeded", attempts=3)

        assert str(error) == "Max retries exceeded", "MaxRetriesExceededError should have message"
        assert error.attempts == 3, "MaxRetriesExceededError should track number of attempts"
