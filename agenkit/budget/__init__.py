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
"""

from .models import ModelPricing
from .tracker import Cost, CostTracker, Storage, InMemoryStorage
from .limiter import BudgetLimiter, BudgetWarning, BudgetExceededError
from .optimizer import (
    ModelOptimizer,
    ComplexityDetector,
    HeuristicComplexityDetector,
    LLMBasedComplexityDetector
)

__all__ = [
    # Pricing
    "ModelPricing",

    # Tracking
    "Cost",
    "CostTracker",
    "Storage",
    "InMemoryStorage",

    # Limiting
    "BudgetLimiter",
    "BudgetWarning",
    "BudgetExceededError",

    # Optimization
    "ModelOptimizer",
    "ComplexityDetector",
    "HeuristicComplexityDetector",
    "LLMBasedComplexityDetector",
]
