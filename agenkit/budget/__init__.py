"""
Budget management for cost tracking and control.

This package provides tools for tracking LLM costs and enforcing budgets,
essential for managing expenses in long-running autonomous agents.

Classes:
    ModelPricing: Pricing data for LLM models (November 2025 rates)
    Cost: Single cost record dataclass
    CostTracker: Track costs per session, agent, and globally
    BudgetLimiter: Middleware for enforcing cost budgets
    BudgetWarning: Middleware for budget warnings
    ModelOptimizer: Route queries to models based on complexity/cost
    ThinkingBudgetAllocator: Dynamic thinking budget allocation
    ThinkingMode: Enum for instant vs extended thinking
    ThinkingBudget: Thinking budget allocation dataclass
    ThinkingModeDetector: Detect if queries need extended thinking

Example:
    >>> from agenkit.budget import CostTracker, BudgetLimiter
    >>>
    >>> # Track costs
    >>> tracker = CostTracker()
    >>> await tracker.record_cost(
    ...     "session-123",
    ...     "assistant",
    ...     "claude-sonnet-4",
    ...     input_tokens=1000,
    ...     output_tokens=500
    ... )
    >>>
    >>> # Enforce budget
    >>> limiter = BudgetLimiter(tracker, session_budget=10.00)
    >>> wrapped_agent = limiter(agent)
    >>>
    >>> # Extended thinking
    >>> from agenkit.budget import ThinkingBudgetAllocator
    >>> allocator = ThinkingBudgetAllocator()
    >>> budget = await allocator.allocate(messages, complexity="complex")
"""

from .limiter import BudgetExceededError, BudgetLimiter, BudgetWarning
from .models import ModelPricing
from .optimizer import (ComplexityDetector, HeuristicComplexityDetector,
                        LLMBasedComplexityDetector, ModelOptimizer)
from .reasoning import (ThinkingBudget, ThinkingBudgetAllocator, ThinkingMode,
                        ThinkingModeDetector)
from .tracker import Cost, CostTracker, InMemoryStorage, Storage

__all__ = [
    "BudgetExceededError",
    # Limiting
    "BudgetLimiter",
    "BudgetWarning",
    "ComplexityDetector",
    # Tracking
    "Cost",
    "CostTracker",
    "HeuristicComplexityDetector",
    "InMemoryStorage",
    "LLMBasedComplexityDetector",
    # Optimization
    "ModelOptimizer",
    # Pricing
    "ModelPricing",
    "Storage",
    "ThinkingBudget",
    # Extended Thinking
    "ThinkingBudgetAllocator",
    "ThinkingMode",
    "ThinkingModeDetector",
]
