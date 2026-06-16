"""Test LLM parameter validation across all adapters."""

import pytest

from agenkit.adapters.llm.base import LLM


class MockLLM(LLM):
    """Mock LLM for testing validation."""

    async def complete(self, messages, **kwargs):
        """Mock complete method."""
        return None

    async def stream(self, messages, **kwargs):
        """Mock stream method."""
        yield None

    @property
    def model(self):
        """Mock model property."""
        return "mock-model"


class TestLLMValidation:
    """Test parameter validation for LLM adapters."""

    def test_temperature_validation(self):
        """Temperature must be between 0 and 2."""
        llm = MockLLM()

        # Valid temperatures
        llm._validate_llm_params(temperature=0.0)
        llm._validate_llm_params(temperature=1.0)
        llm._validate_llm_params(temperature=2.0)

        # Invalid: too low
        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            llm._validate_llm_params(temperature=-0.1)

        # Invalid: too high
        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            llm._validate_llm_params(temperature=2.1)

        # Invalid: wrong type
        with pytest.raises(ValueError, match="temperature must be a number"):
            llm._validate_llm_params(temperature="1.0")

    def test_max_tokens_validation(self):
        """Max tokens must be a positive integer."""
        llm = MockLLM()

        # Valid max_tokens
        llm._validate_llm_params(max_tokens=1)
        llm._validate_llm_params(max_tokens=100)
        llm._validate_llm_params(max_tokens=4096)

        # Invalid: zero
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            llm._validate_llm_params(max_tokens=0)

        # Invalid: negative
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            llm._validate_llm_params(max_tokens=-100)

        # Invalid: wrong type
        with pytest.raises(ValueError, match="max_tokens must be an integer"):
            llm._validate_llm_params(max_tokens=100.5)

    def test_top_p_validation(self):
        """Top_p must be between 0 and 1."""
        llm = MockLLM()

        # Valid top_p
        llm._validate_llm_params(top_p=0.0)
        llm._validate_llm_params(top_p=0.5)
        llm._validate_llm_params(top_p=1.0)

        # Invalid: too low
        with pytest.raises(ValueError, match="top_p must be between 0 and 1"):
            llm._validate_llm_params(top_p=-0.1)

        # Invalid: too high
        with pytest.raises(ValueError, match="top_p must be between 0 and 1"):
            llm._validate_llm_params(top_p=1.1)

    def test_frequency_penalty_validation(self):
        """Frequency penalty must be between -2 and 2."""
        llm = MockLLM()

        # Valid frequency_penalty
        llm._validate_llm_params(frequency_penalty=-2.0)
        llm._validate_llm_params(frequency_penalty=0.0)
        llm._validate_llm_params(frequency_penalty=2.0)

        # Invalid: too low
        with pytest.raises(ValueError, match="frequency_penalty must be between -2 and 2"):
            llm._validate_llm_params(frequency_penalty=-2.1)

        # Invalid: too high
        with pytest.raises(ValueError, match="frequency_penalty must be between -2 and 2"):
            llm._validate_llm_params(frequency_penalty=2.1)

    def test_presence_penalty_validation(self):
        """Presence penalty must be between -2 and 2."""
        llm = MockLLM()

        # Valid presence_penalty
        llm._validate_llm_params(presence_penalty=-2.0)
        llm._validate_llm_params(presence_penalty=0.0)
        llm._validate_llm_params(presence_penalty=2.0)

        # Invalid: too low
        with pytest.raises(ValueError, match="presence_penalty must be between -2 and 2"):
            llm._validate_llm_params(presence_penalty=-2.1)

        # Invalid: too high
        with pytest.raises(ValueError, match="presence_penalty must be between -2 and 2"):
            llm._validate_llm_params(presence_penalty=2.1)

    def test_multiple_parameters(self):
        """Validate multiple parameters at once."""
        llm = MockLLM()

        # All valid
        llm._validate_llm_params(
            temperature=0.7,
            max_tokens=100,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=-0.5,
        )

        # One invalid parameter should raise
        with pytest.raises(ValueError, match="temperature"):
            llm._validate_llm_params(
                temperature=3.0,  # Invalid
                max_tokens=100,
                top_p=0.9,
            )
