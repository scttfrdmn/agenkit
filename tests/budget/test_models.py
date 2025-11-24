"""
Tests for ModelPricing.
"""

import pytest

from agenkit.budget.models import ModelPricing


def test_calculate_input_cost():
    """Test calculating input token cost."""
    pricing = ModelPricing()

    # Claude Sonnet 4: $3.00 per 1M input tokens
    cost = pricing.calculate("claude-sonnet-4", 100000, "input")
    assert abs(cost - 0.30) < 0.001  # $0.30 for 100K tokens


def test_calculate_output_cost():
    """Test calculating output token cost."""
    pricing = ModelPricing()

    # Claude Sonnet 4: $15.00 per 1M output tokens
    cost = pricing.calculate("claude-sonnet-4", 100000, "output")
    assert abs(cost - 1.50) < 0.001  # $1.50 for 100K tokens


def test_calculate_expensive_model():
    """Test calculating cost for expensive model (Opus 4)."""
    pricing = ModelPricing()

    # Claude Opus 4: $15/$75 per 1M tokens
    input_cost = pricing.calculate("claude-opus-4", 100000, "input")
    output_cost = pricing.calculate("claude-opus-4", 100000, "output")

    assert abs(input_cost - 1.50) < 0.001  # $1.50
    assert abs(output_cost - 7.50) < 0.001  # $7.50


def test_calculate_cheap_model():
    """Test calculating cost for cheap model (Haiku 3)."""
    pricing = ModelPricing()

    # Claude Haiku 3: $0.25/$1.25 per 1M tokens
    input_cost = pricing.calculate("claude-haiku-3", 100000, "input")
    output_cost = pricing.calculate("claude-haiku-3", 100000, "output")

    assert abs(input_cost - 0.025) < 0.001  # $0.025
    assert abs(output_cost - 0.125) < 0.001  # $0.125


def test_calculate_unknown_model():
    """Test calculating cost for unknown model (uses default)."""
    pricing = ModelPricing()

    cost = pricing.calculate("unknown-model", 100000, "input")
    # Should use default: $0.01 per 1M tokens
    assert abs(cost - 0.001) < 0.0001


def test_calculate_invalid_direction():
    """Test invalid direction raises ValueError."""
    pricing = ModelPricing()

    with pytest.raises(ValueError, match="direction must be"):
        pricing.calculate("claude-sonnet-4", 1000, "invalid")


def test_calculate_zero_tokens():
    """Test calculating cost for zero tokens."""
    pricing = ModelPricing()

    cost = pricing.calculate("claude-sonnet-4", 0, "input")
    assert cost == 0.0


def test_get_model_pricing():
    """Test getting pricing for specific model."""
    pricing = ModelPricing()

    rates = pricing.get_model_pricing("claude-sonnet-4")
    assert rates == {"input": 3.00, "output": 15.00}


def test_get_model_pricing_unknown():
    """Test getting pricing for unknown model."""
    pricing = ModelPricing()

    rates = pricing.get_model_pricing("unknown-model")
    assert rates is None


def test_list_models():
    """Test listing all supported models."""
    pricing = ModelPricing()

    models = pricing.list_models()

    # Should include major models
    assert "claude-sonnet-4" in models
    assert "claude-opus-4" in models
    assert "gpt-4o" in models
    assert "o3" in models

    # Should not include default
    assert "default" not in models


def test_update_pricing():
    """Test updating pricing for a model."""
    ModelPricing.update_pricing("test-model", 1.0, 5.0)

    pricing = ModelPricing()
    input_cost = pricing.calculate("test-model", 1000000, "input")
    output_cost = pricing.calculate("test-model", 1000000, "output")

    assert abs(input_cost - 1.0) < 0.001
    assert abs(output_cost - 5.0) < 0.001


def test_estimate_conversation_cost():
    """Test estimating cost for a conversation."""
    pricing = ModelPricing()

    cost = pricing.estimate_conversation_cost(
        "claude-sonnet-4", num_turns=100, avg_input_tokens=1000, avg_output_tokens=500
    )

    # 100 turns * 1000 input = 100K input tokens = $0.30
    # 100 turns * 500 output = 50K output tokens = $0.75
    # Total = $1.05
    assert abs(cost - 1.05) < 0.01


def test_compare_models():
    """Test comparing costs across models."""
    pricing = ModelPricing()

    comparison = pricing.compare_models(
        ["claude-haiku-3", "claude-sonnet-4", "claude-opus-4"],
        input_tokens=100000,
        output_tokens=50000,
    )

    # Verify all models included
    assert "claude-haiku-3" in comparison
    assert "claude-sonnet-4" in comparison
    assert "claude-opus-4" in comparison

    # Verify cost ordering (haiku cheapest, opus most expensive)
    assert comparison["claude-haiku-3"] < comparison["claude-sonnet-4"]
    assert comparison["claude-sonnet-4"] < comparison["claude-opus-4"]


def test_free_model():
    """Test calculating cost for free model."""
    pricing = ModelPricing()

    input_cost = pricing.calculate("gemini-2.0-flash-exp", 100000, "input")
    output_cost = pricing.calculate("gemini-2.0-flash-exp", 100000, "output")

    assert input_cost == 0.0
    assert output_cost == 0.0


def test_realistic_30_hour_scenario():
    """Test realistic cost estimate for 30-hour autonomous agent."""
    pricing = ModelPricing()

    # Scenario: 30-hour agent, 1000 requests
    # Average 10K input + 5K output per request
    total_input = 1000 * 10000  # 10M tokens
    total_output = 1000 * 5000  # 5M tokens

    # Claude Opus 4 (expensive)
    opus_cost = pricing.calculate("claude-opus-4", total_input, "input") + pricing.calculate(
        "claude-opus-4", total_output, "output"
    )

    # Should be $150 + $375 = $525
    assert abs(opus_cost - 525.0) < 1.0

    # Claude Sonnet 4 (medium)
    sonnet_cost = pricing.calculate("claude-sonnet-4", total_input, "input") + pricing.calculate(
        "claude-sonnet-4", total_input, "output"
    )

    # Should be much cheaper
    assert sonnet_cost < opus_cost
