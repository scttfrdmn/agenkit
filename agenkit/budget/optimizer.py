"""
Model optimizer for cost-quality tradeoff.

Intelligently routes requests to models based on complexity and cost,
optimizing for the best cost-quality balance.
"""

import logging
from typing import Callable, Optional, Awaitable
from abc import ABC, abstractmethod

from ..interfaces import Message

logger = logging.getLogger(__name__)


class ComplexityDetector(ABC):
    """Abstract interface for complexity detection."""

    @abstractmethod
    async def detect(self, messages: list[Message]) -> str:
        """
        Detect query complexity.

        Args:
            messages: Conversation messages

        Returns:
            Complexity level: "simple", "medium", or "complex"
        """
        pass


class HeuristicComplexityDetector(ComplexityDetector):
    """
    Default complexity detection using heuristics.

    Factors:
    - Query length (longer = more complex)
    - Keywords (reasoning, analysis, comparison = complex)
    - History length (more context = more complex)
    """

    COMPLEX_KEYWORDS = [
        "analyze", "compare", "reasoning", "explain why",
        "step by step", "think through", "evaluate",
        "pros and cons", "trade-offs", "implications",
        "in detail", "comprehensive", "thorough"
    ]

    def __init__(
        self,
        long_query_threshold: int = 500,
        long_history_threshold: int = 10
    ):
        """
        Initialize heuristic detector.

        Args:
            long_query_threshold: Character count threshold for long queries
            long_history_threshold: Message count threshold for long history
        """
        self.long_query_threshold = long_query_threshold
        self.long_history_threshold = long_history_threshold

    async def detect(self, messages: list[Message]) -> str:
        """Detect complexity using heuristics."""
        if not messages:
            return "simple"

        latest = messages[-1].content if messages else ""

        # Check for complex keywords
        latest_lower = latest.lower()
        has_complex_keywords = any(
            kw in latest_lower for kw in self.COMPLEX_KEYWORDS
        )

        # Check query length
        is_long_query = len(latest) > self.long_query_threshold

        # Check history length
        is_long_history = len(messages) > self.long_history_threshold

        # Determine complexity
        if is_long_query or has_complex_keywords:
            return "complex"
        elif is_long_history:
            return "medium"
        else:
            return "simple"


class LLMBasedComplexityDetector(ComplexityDetector):
    """
    LLM-based complexity detection.

    Uses a cheap LLM to analyze query complexity before routing.
    More accurate but adds latency and cost.
    """

    def __init__(self, llm_client):
        """
        Initialize LLM-based detector.

        Args:
            llm_client: LLM client with async complete() method
        """
        self.llm = llm_client

    async def detect(self, messages: list[Message]) -> str:
        """Detect complexity using LLM."""
        if not messages:
            return "simple"

        latest = messages[-1].content

        prompt = f"""Analyze the following query and classify its complexity:

Query: "{latest}"

Classify as:
- "simple": Basic questions, greetings, short requests
- "medium": Standard questions requiring some thought
- "complex": Deep analysis, reasoning, multi-step problems

Respond with only one word: simple, medium, or complex."""

        response = await self.llm.complete([Message(role="user", content=prompt)])
        complexity = response.content.strip().lower()

        if complexity not in ("simple", "medium", "complex"):
            logger.warning(f"Invalid complexity from LLM: {complexity}, defaulting to medium")
            return "medium"

        return complexity


class ModelOptimizer:
    """
    Intelligently route requests to models based on complexity and cost.

    Strategy:
    - Simple queries → Cheap model (Haiku, GPT-3.5)
    - Medium queries → Mid-tier (Sonnet 4, GPT-4)
    - Complex queries → Expensive (Opus 4, o3)

    Example:
        >>> optimizer = ModelOptimizer(
        ...     cheap_model="claude-haiku-3",
        ...     medium_model="claude-sonnet-4",
        ...     expensive_model="claude-opus-4",
        ...     llm_clients={
        ...         "claude-haiku-3": haiku_client,
        ...         "claude-sonnet-4": sonnet_client,
        ...         "claude-opus-4": opus_client
        ...     }
        ... )
        >>> response = await optimizer.complete(messages)
        >>> print(response.metadata["selected_model"])
        claude-sonnet-4
    """

    def __init__(
        self,
        cheap_model: str,
        medium_model: str,
        expensive_model: str,
        llm_clients: dict,  # model_name -> LLM client
        complexity_detector: Optional[ComplexityDetector] = None
    ):
        """
        Initialize model optimizer.

        Args:
            cheap_model: Model for simple queries (e.g., "claude-haiku-3")
            medium_model: Model for medium queries (e.g., "claude-sonnet-4")
            expensive_model: Model for complex queries (e.g., "claude-opus-4")
            llm_clients: Dict mapping model names to LLM clients
            complexity_detector: Complexity detector (defaults to heuristic)
        """
        self.cheap_model = cheap_model
        self.medium_model = medium_model
        self.expensive_model = expensive_model
        self.llm_clients = llm_clients
        self.detector = complexity_detector or HeuristicComplexityDetector()

        # Validate clients
        for model in [cheap_model, medium_model, expensive_model]:
            if model not in llm_clients:
                raise ValueError(f"LLM client for {model} not provided")

    async def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> Message:
        """
        Route to appropriate model based on complexity.

        Args:
            messages: Conversation messages
            **kwargs: Additional arguments for LLM

        Returns:
            Response message with metadata including:
            - selected_model: Model that was used
            - complexity: Detected complexity level
            - routing_reason: Why this model was selected

        Example:
            >>> response = await optimizer.complete(messages)
            >>> print(f"Used {response.metadata['selected_model']} for {response.metadata['complexity']} query")
            Used claude-sonnet-4 for medium query
        """
        # Detect complexity
        complexity = await self.detector.detect(messages)

        # Select model
        if complexity == "simple":
            model_name = self.cheap_model
            reason = "Simple query, using cheap model"
        elif complexity == "medium":
            model_name = self.medium_model
            reason = "Medium complexity, using mid-tier model"
        else:  # complex
            model_name = self.expensive_model
            reason = "Complex query, using expensive model"

        logger.info(f"Routing to {model_name}: {reason}")

        # Get LLM client
        llm = self.llm_clients[model_name]

        # Complete
        response = await llm.complete(messages, **kwargs)

        # Add routing metadata
        response.metadata["selected_model"] = model_name
        response.metadata["complexity"] = complexity
        response.metadata["routing_reason"] = reason

        return response

    async def complete_with_fallback(
        self,
        messages: list[Message],
        max_attempts: int = 3,
        **kwargs
    ) -> Message:
        """
        Complete with automatic fallback to cheaper models on budget constraints.

        Tries expensive → medium → cheap until successful.

        Args:
            messages: Conversation messages
            max_attempts: Maximum fallback attempts
            **kwargs: Additional arguments

        Returns:
            Response message
        """
        # Detect complexity
        complexity = await self.detector.detect(messages)

        # Determine fallback order based on complexity
        if complexity == "complex":
            models = [self.expensive_model, self.medium_model, self.cheap_model]
        elif complexity == "medium":
            models = [self.medium_model, self.cheap_model]
        else:
            models = [self.cheap_model]

        last_error = None

        for i, model_name in enumerate(models[:max_attempts]):
            try:
                llm = self.llm_clients[model_name]
                response = await llm.complete(messages, **kwargs)

                # Add metadata
                response.metadata["selected_model"] = model_name
                response.metadata["complexity"] = complexity
                response.metadata["fallback_attempt"] = i + 1
                if i > 0:
                    response.metadata["fallback_reason"] = "Budget constraint or error"

                return response

            except Exception as e:
                logger.warning(f"Failed with {model_name}: {e}")
                last_error = e
                continue

        # All models failed
        raise last_error or Exception("All model attempts failed")

    def get_model_for_complexity(self, complexity: str) -> str:
        """
        Get model name for given complexity.

        Args:
            complexity: "simple", "medium", or "complex"

        Returns:
            Model name
        """
        if complexity == "simple":
            return self.cheap_model
        elif complexity == "medium":
            return self.medium_model
        elif complexity == "complex":
            return self.expensive_model
        else:
            raise ValueError(f"Unknown complexity: {complexity}")

    async def estimate_cost(
        self,
        messages: list[Message],
        input_tokens: int,
        output_tokens: int
    ) -> dict[str, float]:
        """
        Estimate cost for different models.

        Args:
            messages: Conversation messages (for complexity detection)
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens

        Returns:
            Dict mapping model to estimated cost
        """
        from .models import ModelPricing

        pricing = ModelPricing()

        estimates = {}
        for model_name in [self.cheap_model, self.medium_model, self.expensive_model]:
            input_cost = pricing.calculate(model_name, input_tokens, "input")
            output_cost = pricing.calculate(model_name, output_tokens, "output")
            estimates[model_name] = input_cost + output_cost

        return estimates
