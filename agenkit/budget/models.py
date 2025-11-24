"""
Model pricing data for LLM cost tracking.

Pricing data as of November 2025. Rates are per 1 million tokens.
"""

import logging

logger = logging.getLogger(__name__)


class ModelPricing:
    """
    Pricing data for LLM models (as of November 2025).

    All prices are per 1 million tokens (input and output separately).

    Example:
        >>> pricing = ModelPricing()
        >>> cost = pricing.calculate("claude-sonnet-4", 10000, "input")
        >>> print(f"Cost: ${cost:.4f}")
        Cost: $0.0300
    """

    # Pricing data (per 1M tokens)
    PRICING = {
        # OpenAI
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "o3": {"input": 5.00, "output": 15.00},
        "o3-mini": {"input": 1.00, "output": 3.00},
        # Anthropic
        "claude-opus-4": {"input": 15.00, "output": 75.00},
        "claude-sonnet-4": {"input": 3.00, "output": 15.00},
        "claude-sonnet-4.5": {"input": 3.00, "output": 15.00},
        "claude-haiku-3": {"input": 0.25, "output": 1.25},
        # Google
        "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # Free tier
        "gemini-pro": {"input": 0.50, "output": 1.50},
        # Generic fallback
        "default": {"input": 0.01, "output": 0.01},
    }

    def calculate(
        self,
        model: str,
        tokens: int,
        direction: str,  # "input" or "output"
    ) -> float:
        """
        Calculate cost for tokens.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4")
            tokens: Number of tokens
            direction: "input" or "output"

        Returns:
            Cost in dollars

        Example:
            >>> pricing = ModelPricing()
            >>> cost = pricing.calculate("claude-opus-4", 100000, "input")
            >>> print(f"${cost:.2f}")
            $1.50
        """
        if direction not in ("input", "output"):
            raise ValueError(f"direction must be 'input' or 'output', got: {direction}")

        if model not in self.PRICING:
            logger.warning(
                f"Unknown model '{model}', using default pricing. "
                f"Known models: {list(self.PRICING.keys())}"
            )
            model = "default"

        price_per_million = self.PRICING[model][direction]
        return (tokens / 1_000_000) * price_per_million

    def get_model_pricing(self, model: str) -> dict | None:
        """
        Get pricing for specific model.

        Args:
            model: Model identifier

        Returns:
            Dict with "input" and "output" prices per 1M tokens,
            or None if model not found

        Example:
            >>> pricing = ModelPricing()
            >>> rates = pricing.get_model_pricing("claude-sonnet-4")
            >>> print(rates)
            {"input": 3.00, "output": 15.00}
        """
        return self.PRICING.get(model)

    def list_models(self) -> list[str]:
        """
        List all supported models.

        Returns:
            List of model identifiers

        Example:
            >>> pricing = ModelPricing()
            >>> models = pricing.list_models()
            >>> print(len(models))
            12
        """
        return [model for model in self.PRICING if model != "default"]

    @classmethod
    def update_pricing(cls, model: str, input_price: float, output_price: float) -> None:
        """
        Update pricing for model (for testing or custom deployments).

        Args:
            model: Model identifier
            input_price: Price per 1M input tokens
            output_price: Price per 1M output tokens

        Example:
            >>> ModelPricing.update_pricing("custom-model", 1.0, 5.0)
            >>> pricing = ModelPricing()
            >>> cost = pricing.calculate("custom-model", 1000000, "output")
            >>> print(f"${cost:.2f}")
            $5.00
        """
        cls.PRICING[model] = {"input": input_price, "output": output_price}
        logger.info(
            f"Updated pricing for {model}: ${input_price}/M input, ${output_price}/M output"
        )

    def estimate_conversation_cost(
        self, model: str, num_turns: int, avg_input_tokens: int, avg_output_tokens: int
    ) -> float:
        """
        Estimate cost for a conversation.

        Args:
            model: Model identifier
            num_turns: Number of conversation turns
            avg_input_tokens: Average input tokens per turn
            avg_output_tokens: Average output tokens per turn

        Returns:
            Estimated total cost in dollars

        Example:
            >>> pricing = ModelPricing()
            >>> cost = pricing.estimate_conversation_cost(
            ...     "claude-sonnet-4",
            ...     num_turns=100,
            ...     avg_input_tokens=1000,
            ...     avg_output_tokens=500
            ... )
            >>> print(f"Estimated: ${cost:.2f}")
            Estimated: $1.05
        """
        total_input = num_turns * avg_input_tokens
        total_output = num_turns * avg_output_tokens

        input_cost = self.calculate(model, total_input, "input")
        output_cost = self.calculate(model, total_output, "output")

        return input_cost + output_cost

    def compare_models(
        self, models: list[str], input_tokens: int, output_tokens: int
    ) -> dict[str, float]:
        """
        Compare costs across different models.

        Args:
            models: List of model identifiers
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Dict mapping model to total cost

        Example:
            >>> pricing = ModelPricing()
            >>> comparison = pricing.compare_models(
            ...     ["claude-haiku-3", "claude-sonnet-4", "claude-opus-4"],
            ...     input_tokens=100000,
            ...     output_tokens=50000
            ... )
            >>> for model, cost in sorted(comparison.items(), key=lambda x: x[1]):
            ...     print(f"{model}: ${cost:.2f}")
            claude-haiku-3: $0.09
            claude-sonnet-4: $1.05
            claude-opus-4: $5.25
        """
        costs = {}
        for model in models:
            input_cost = self.calculate(model, input_tokens, "input")
            output_cost = self.calculate(model, output_tokens, "output")
            costs[model] = input_cost + output_cost

        return costs
