"""Test LLM parameter validation across all adapters."""

import pytest

from agenkit.adapters.llm.base import LLM
from agenkit.adapters.llm.openai import OpenAILLM
from agenkit.interfaces import Message


# Test the base LLM validation method directly
class TestBaseLLMValidation:
    """Test the base LLM class validation method."""

    @pytest.fixture
    def llm(self):
        """Create an OpenAI LLM instance for testing validation."""
        return OpenAILLM(model="gpt-4o", api_key="dummy-key-for-testing")

    def test_temperature_validation_too_low(self, llm):
        """Test that temperature below 0 raises ValueError."""
        with pytest.raises(ValueError, match=r"temperature must be between 0 and 2, got -0\.5"):
            llm._validate_llm_params(temperature=-0.5, max_tokens=None)

    def test_temperature_validation_too_high(self, llm):
        """Test that temperature above 2 raises ValueError."""
        with pytest.raises(ValueError, match=r"temperature must be between 0 and 2, got 3\.0"):
            llm._validate_llm_params(temperature=3.0, max_tokens=None)

    def test_temperature_validation_valid_range(self, llm):
        """Test that valid temperatures don't raise errors."""
        llm._validate_llm_params(temperature=0.0, max_tokens=None)
        llm._validate_llm_params(temperature=1.0, max_tokens=None)
        llm._validate_llm_params(temperature=2.0, max_tokens=None)

    def test_temperature_validation_none(self, llm):
        """Test that temperature=None is valid."""
        llm._validate_llm_params(temperature=None, max_tokens=None)

    def test_temperature_validation_invalid_type(self, llm):
        """Test that non-numeric temperature raises ValueError."""
        with pytest.raises(ValueError, match=r"temperature must be a number, got str"):
            llm._validate_llm_params(temperature="hot", max_tokens=None)  # type: ignore

    def test_max_tokens_validation_zero(self, llm):
        """Test that max_tokens=0 raises ValueError."""
        with pytest.raises(ValueError, match=r"max_tokens must be positive, got 0"):
            llm._validate_llm_params(temperature=1.0, max_tokens=0)

    def test_max_tokens_validation_negative(self, llm):
        """Test that negative max_tokens raises ValueError."""
        with pytest.raises(ValueError, match=r"max_tokens must be positive, got -10"):
            llm._validate_llm_params(temperature=1.0, max_tokens=-10)

    def test_max_tokens_validation_none(self, llm):
        """Test that max_tokens=None is valid (uses model default)."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None)

    def test_max_tokens_validation_positive(self, llm):
        """Test that positive max_tokens are valid."""
        llm._validate_llm_params(temperature=1.0, max_tokens=1)
        llm._validate_llm_params(temperature=1.0, max_tokens=100)
        llm._validate_llm_params(temperature=1.0, max_tokens=4096)

    def test_max_tokens_validation_invalid_type(self, llm):
        """Test that non-integer max_tokens raises ValueError."""
        with pytest.raises(ValueError, match=r"max_tokens must be an integer, got str"):
            llm._validate_llm_params(temperature=1.0, max_tokens="many")  # type: ignore

    def test_top_p_validation_too_low(self, llm):
        """Test that top_p below 0 raises ValueError."""
        with pytest.raises(ValueError, match=r"top_p must be between 0 and 1, got -0\.1"):
            llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=-0.1)

    def test_top_p_validation_too_high(self, llm):
        """Test that top_p above 1 raises ValueError."""
        with pytest.raises(ValueError, match=r"top_p must be between 0 and 1, got 1\.5"):
            llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=1.5)

    def test_top_p_validation_valid_range(self, llm):
        """Test that valid top_p values don't raise errors."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=0.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=0.5)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=1.0)

    def test_frequency_penalty_validation_too_low(self, llm):
        """Test that frequency_penalty below -2 raises ValueError."""
        with pytest.raises(ValueError, match=r"frequency_penalty must be between -2 and 2, got -3"):
            llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=-3)

    def test_frequency_penalty_validation_too_high(self, llm):
        """Test that frequency_penalty above 2 raises ValueError."""
        with pytest.raises(ValueError, match=r"frequency_penalty must be between -2 and 2, got 3"):
            llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=3)

    def test_frequency_penalty_validation_valid_range(self, llm):
        """Test that valid frequency_penalty values don't raise errors."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=-2.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=0.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=2.0)

    def test_presence_penalty_validation_too_low(self, llm):
        """Test that presence_penalty below -2 raises ValueError."""
        with pytest.raises(ValueError, match=r"presence_penalty must be between -2 and 2, got -2\.5"):
            llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=-2.5)

    def test_presence_penalty_validation_too_high(self, llm):
        """Test that presence_penalty above 2 raises ValueError."""
        with pytest.raises(ValueError, match=r"presence_penalty must be between -2 and 2, got 2\.5"):
            llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=2.5)

    def test_presence_penalty_validation_valid_range(self, llm):
        """Test that valid presence_penalty values don't raise errors."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=-2.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=0.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=2.0)

    def test_multiple_valid_params(self, llm):
        """Test that all valid parameters together don't raise errors."""
        llm._validate_llm_params(
            temperature=1.0,
            max_tokens=100,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=-0.5,
        )

    def test_multiple_invalid_params(self, llm):
        """Test that first invalid parameter is caught."""
        # temperature is checked first
        with pytest.raises(ValueError, match=r"temperature"):
            llm._validate_llm_params(
                temperature=5.0,  # Invalid
                max_tokens=-10,  # Also invalid, but temperature checked first
            )


# Test that validation is actually called in adapters
class TestAdapterValidationIntegration:
    """Test that validation is integrated into adapter methods."""

    @pytest.fixture
    def openai_llm(self):
        """Create OpenAI LLM instance."""
        return OpenAILLM(model="gpt-4o", api_key="dummy-key")

    @pytest.mark.asyncio
    async def test_openai_complete_validates_temperature(self, openai_llm, monkeypatch):
        """Test that complete() validates temperature before calling API."""
        # Mock the API call to fail if it's reached
        def mock_create(*args, **kwargs):
            pytest.fail("API should not be called when validation fails")

        monkeypatch.setattr(openai_llm._client.chat.completions, "create", mock_create)

        messages = [Message(role="user", content="test")]

        # Should fail validation before reaching API
        with pytest.raises(ValueError, match=r"temperature"):
            await openai_llm.complete(messages, temperature=5.0)

    @pytest.mark.asyncio
    async def test_openai_complete_validates_max_tokens(self, openai_llm, monkeypatch):
        """Test that complete() validates max_tokens before calling API."""
        def mock_create(*args, **kwargs):
            pytest.fail("API should not be called when validation fails")

        monkeypatch.setattr(openai_llm._client.chat.completions, "create", mock_create)

        messages = [Message(role="user", content="test")]

        # Should fail validation before reaching API
        with pytest.raises(ValueError, match=r"max_tokens"):
            await openai_llm.complete(messages, temperature=1.0, max_tokens=-1)

    @pytest.mark.asyncio
    async def test_openai_stream_validates_temperature(self, openai_llm, monkeypatch):
        """Test that stream() validates temperature before calling API."""
        def mock_create(*args, **kwargs):
            pytest.fail("API should not be called when validation fails")

        monkeypatch.setattr(openai_llm._client.chat.completions, "create", mock_create)

        messages = [Message(role="user", content="test")]

        # Should fail validation before reaching API
        with pytest.raises(ValueError, match=r"temperature"):
            # Just trying to create the async generator should trigger validation
            async for _ in openai_llm.stream(messages, temperature=-1.0):
                pass


# Edge case tests
class TestValidationEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def llm(self):
        """Create an LLM instance for testing."""
        return OpenAILLM(model="gpt-4o", api_key="dummy-key")

    def test_temperature_exactly_zero(self, llm):
        """Test that temperature=0.0 (deterministic) is valid."""
        llm._validate_llm_params(temperature=0.0, max_tokens=None)

    def test_temperature_exactly_two(self, llm):
        """Test that temperature=2.0 (maximum) is valid."""
        llm._validate_llm_params(temperature=2.0, max_tokens=None)

    def test_max_tokens_exactly_one(self, llm):
        """Test that max_tokens=1 (minimum valid) is allowed."""
        llm._validate_llm_params(temperature=1.0, max_tokens=1)

    def test_top_p_exactly_zero(self, llm):
        """Test that top_p=0.0 is valid."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=0.0)

    def test_top_p_exactly_one(self, llm):
        """Test that top_p=1.0 is valid."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, top_p=1.0)

    def test_penalty_exactly_negative_two(self, llm):
        """Test that penalties=-2.0 (minimum) are valid."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=-2.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=-2.0)

    def test_penalty_exactly_positive_two(self, llm):
        """Test that penalties=2.0 (maximum) are valid."""
        llm._validate_llm_params(temperature=1.0, max_tokens=None, frequency_penalty=2.0)
        llm._validate_llm_params(temperature=1.0, max_tokens=None, presence_penalty=2.0)

    def test_validation_with_no_kwargs(self, llm):
        """Test validation when no optional parameters provided."""
        llm._validate_llm_params(temperature=1.0, max_tokens=100)

    def test_validation_with_unrecognized_kwargs(self, llm):
        """Test that unrecognized kwargs don't cause errors."""
        # Should not raise - adapter will pass these through to provider
        llm._validate_llm_params(
            temperature=1.0,
            max_tokens=100,
            custom_param="value",  # Not validated
            another_param=42,  # Not validated
        )
