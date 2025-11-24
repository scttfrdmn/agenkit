"""
Extended thinking and reasoning budget allocation.

Provides dynamic allocation of thinking budgets for models that support
extended reasoning modes (e.g., o3, Claude 4 extended thinking).
"""

import logging
from dataclasses import dataclass
from enum import Enum

from ..interfaces import Message

logger = logging.getLogger(__name__)


class ThinkingMode(Enum):
    """Thinking mode for model inference."""

    INSTANT = "instant"
    EXTENDED = "extended"


@dataclass
class ThinkingBudget:
    """
    Thinking budget allocation.

    Attributes:
        mode: Instant or extended thinking
        max_thinking_tokens: Maximum tokens to spend on reasoning
        estimated_cost: Estimated cost for this thinking budget
        reasoning_time_multiplier: Expected time multiplier (extended = ~2-5x slower)
    """

    mode: ThinkingMode
    max_thinking_tokens: int
    estimated_cost: float
    reasoning_time_multiplier: float


class ThinkingBudgetAllocator:
    """
    Dynamically allocate thinking budgets based on complexity and constraints.

    Features:
    - Instant vs extended thinking mode selection
    - Thinking token budget allocation
    - Cost-aware thinking budget optimization
    - Complexity-based reasoning allocation

    Strategy:
    - Simple queries → Instant (0 thinking tokens)
    - Medium queries → Light extended (2-5k thinking tokens)
    - Complex queries → Full extended (10-20k thinking tokens)

    Example:
        >>> allocator = ThinkingBudgetAllocator(
        ...     instant_thinking_tokens=0,
        ...     light_thinking_tokens=3000,
        ...     full_thinking_tokens=15000
        ... )
        >>> budget = await allocator.allocate(
        ...     messages=messages,
        ...     complexity="complex",
        ...     budget_remaining=5.0
        ... )
        >>> print(f"{budget.mode.value}: {budget.max_thinking_tokens} tokens")
        extended: 15000 tokens
    """

    def __init__(
        self,
        instant_thinking_tokens: int = 0,
        light_thinking_tokens: int = 3000,
        full_thinking_tokens: int = 15000,
        thinking_cost_multiplier: float = 1.0,
        min_budget_for_extended: float = 0.10,
    ):
        """
        Initialize thinking budget allocator.

        Args:
            instant_thinking_tokens: Tokens for instant mode (usually 0)
            light_thinking_tokens: Tokens for light extended thinking
            full_thinking_tokens: Tokens for full extended thinking
            thinking_cost_multiplier: Cost multiplier for thinking tokens vs output
                (some models charge differently for thinking)
            min_budget_for_extended: Minimum budget remaining to allow extended thinking
        """
        self.instant_thinking_tokens = instant_thinking_tokens
        self.light_thinking_tokens = light_thinking_tokens
        self.full_thinking_tokens = full_thinking_tokens
        self.thinking_cost_multiplier = thinking_cost_multiplier
        self.min_budget_for_extended = min_budget_for_extended

    async def allocate(
        self,
        messages: list[Message],
        complexity: str,
        budget_remaining: float | None = None,
        model: str | None = None,
    ) -> ThinkingBudget:
        """
        Allocate thinking budget based on complexity and constraints.

        Args:
            messages: Conversation messages (for context)
            complexity: Query complexity ("simple", "medium", "complex")
            budget_remaining: Remaining budget in dollars (None = unlimited)
            model: Model identifier (for model-specific pricing)

        Returns:
            ThinkingBudget with mode and token allocation

        Example:
            >>> budget = await allocator.allocate(
            ...     messages=[Message(role="user", content="Solve this complex problem...")],
            ...     complexity="complex",
            ...     budget_remaining=2.0
            ... )
            >>> print(budget.mode.value)
            extended
        """
        # Check if budget allows extended thinking
        if budget_remaining is not None and budget_remaining < self.min_budget_for_extended:
            logger.info(
                f"Insufficient budget for extended thinking "
                f"(${budget_remaining:.2f} < ${self.min_budget_for_extended:.2f}), using instant mode"
            )
            return self._instant_budget(model)

        # Allocate based on complexity
        if complexity == "simple":
            return self._instant_budget(model)
        elif complexity == "medium":
            return self._light_extended_budget(model)
        else:  # complex
            return self._full_extended_budget(model)

    def _instant_budget(self, model: str | None = None) -> ThinkingBudget:
        """Create instant thinking budget."""
        return ThinkingBudget(
            mode=ThinkingMode.INSTANT,
            max_thinking_tokens=self.instant_thinking_tokens,
            estimated_cost=0.0,
            reasoning_time_multiplier=1.0,
        )

    def _light_extended_budget(self, model: str | None = None) -> ThinkingBudget:
        """Create light extended thinking budget."""
        # Estimate cost for thinking tokens
        estimated_cost = self._estimate_thinking_cost(self.light_thinking_tokens, model)

        return ThinkingBudget(
            mode=ThinkingMode.EXTENDED,
            max_thinking_tokens=self.light_thinking_tokens,
            estimated_cost=estimated_cost,
            reasoning_time_multiplier=2.0,  # ~2x slower
        )

    def _full_extended_budget(self, model: str | None = None) -> ThinkingBudget:
        """Create full extended thinking budget."""
        # Estimate cost for thinking tokens
        estimated_cost = self._estimate_thinking_cost(self.full_thinking_tokens, model)

        return ThinkingBudget(
            mode=ThinkingMode.EXTENDED,
            max_thinking_tokens=self.full_thinking_tokens,
            estimated_cost=estimated_cost,
            reasoning_time_multiplier=4.0,  # ~4x slower
        )

    def _estimate_thinking_cost(self, thinking_tokens: int, model: str | None = None) -> float:
        """
        Estimate cost for thinking tokens.

        Args:
            thinking_tokens: Number of thinking tokens
            model: Model identifier

        Returns:
            Estimated cost in dollars
        """
        from .models import ModelPricing

        pricing = ModelPricing()

        # For models without specific thinking token pricing,
        # use output token pricing with multiplier
        if model:
            base_cost = pricing.calculate(model, thinking_tokens, "output")
        else:
            # Use default pricing
            base_cost = pricing.calculate("default", thinking_tokens, "output")

        return base_cost * self.thinking_cost_multiplier

    async def should_use_extended_thinking(
        self, messages: list[Message], complexity: str, budget_remaining: float | None = None
    ) -> bool:
        """
        Determine if extended thinking should be used.

        Args:
            messages: Conversation messages
            complexity: Query complexity
            budget_remaining: Remaining budget

        Returns:
            True if extended thinking should be used

        Example:
            >>> should_extend = await allocator.should_use_extended_thinking(
            ...     messages=messages,
            ...     complexity="complex",
            ...     budget_remaining=5.0
            ... )
            >>> print(should_extend)
            True
        """
        budget = await self.allocate(messages, complexity, budget_remaining)
        return budget.mode == ThinkingMode.EXTENDED


class ThinkingModeDetector:
    """
    Detect if a query would benefit from extended thinking.

    More sophisticated than basic complexity detection - specifically
    identifies reasoning, multi-step, and analytical queries.
    """

    REASONING_KEYWORDS = [
        # Multi-step reasoning
        "step by step",
        "think through",
        "work through",
        "let's think",
        "reason about",
        "analyze",
        "break down",
        # Comparison and evaluation
        "compare",
        "contrast",
        "evaluate",
        "pros and cons",
        "trade-offs",
        "advantages",
        "disadvantages",
        # Deep analysis
        "explain why",
        "in detail",
        "comprehensive",
        "thorough",
        "deep dive",
        "implications",
        "consequences",
        # Problem solving
        "solve",
        "figure out",
        "calculate",
        "compute",
        "optimize",
        "find the best",
        "determine",
        # Logical reasoning
        "if-then",
        "therefore",
        "because",
        "given that",
        "assuming",
        "hypothesis",
        "prove",
        "demonstrate",
    ]

    def __init__(
        self, reasoning_keyword_threshold: int = 2, min_query_length_for_extended: int = 100
    ):
        """
        Initialize thinking mode detector.

        Args:
            reasoning_keyword_threshold: Number of keywords to trigger extended thinking
            min_query_length_for_extended: Minimum query length for extended thinking
        """
        self.reasoning_keyword_threshold = reasoning_keyword_threshold
        self.min_query_length_for_extended = min_query_length_for_extended

    async def needs_extended_thinking(self, messages: list[Message]) -> bool:
        """
        Detect if query needs extended thinking.

        Args:
            messages: Conversation messages

        Returns:
            True if extended thinking is beneficial

        Example:
            >>> detector = ThinkingModeDetector()
            >>> needs_extended = await detector.needs_extended_thinking(messages)
            >>> print(needs_extended)
            True
        """
        if not messages:
            return False

        latest = messages[-1].content.lower()

        # Count reasoning keywords
        keyword_count = sum(1 for keyword in self.REASONING_KEYWORDS if keyword in latest)

        # Check if query suggests reasoning need
        has_reasoning_keywords = keyword_count >= self.reasoning_keyword_threshold

        # Check query length (longer = more complex)
        is_substantial = len(latest) >= self.min_query_length_for_extended

        # Check for mathematical or coding problems (often benefit from extended thinking)
        has_math_or_code = any(
            indicator in latest for indicator in ["```", "math", "equation", "formula", "algorithm"]
        )

        # Extended thinking beneficial if any condition met
        return has_reasoning_keywords or (is_substantial and has_math_or_code)
