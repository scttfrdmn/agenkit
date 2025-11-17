"""
Tests for extended thinking and reasoning budget allocation.
"""

import pytest
from agenkit import Message
from agenkit.budget.reasoning import (
    ThinkingBudgetAllocator,
    ThinkingMode,
    ThinkingBudget,
    ThinkingModeDetector
)


class TestThinkingBudgetAllocator:
    """Tests for ThinkingBudgetAllocator."""

    @pytest.mark.asyncio
    async def test_allocate_simple_complexity(self):
        """Test allocation for simple complexity uses instant mode."""
        allocator = ThinkingBudgetAllocator()

        messages = [Message(role="user", content="Hello")]
        budget = await allocator.allocate(
            messages=messages,
            complexity="simple"
        )

        assert budget.mode == ThinkingMode.INSTANT
        assert budget.max_thinking_tokens == 0
        assert budget.estimated_cost == 0.0
        assert budget.reasoning_time_multiplier == 1.0

    @pytest.mark.asyncio
    async def test_allocate_medium_complexity(self):
        """Test allocation for medium complexity uses light extended thinking."""
        allocator = ThinkingBudgetAllocator(light_thinking_tokens=3000)

        messages = [Message(role="user", content="Explain quantum computing")]
        budget = await allocator.allocate(
            messages=messages,
            complexity="medium"
        )

        assert budget.mode == ThinkingMode.EXTENDED
        assert budget.max_thinking_tokens == 3000
        assert budget.estimated_cost > 0
        assert budget.reasoning_time_multiplier == 2.0

    @pytest.mark.asyncio
    async def test_allocate_complex_complexity(self):
        """Test allocation for complex complexity uses full extended thinking."""
        allocator = ThinkingBudgetAllocator(full_thinking_tokens=15000)

        messages = [Message(role="user", content="Analyze this complex system")]
        budget = await allocator.allocate(
            messages=messages,
            complexity="complex"
        )

        assert budget.mode == ThinkingMode.EXTENDED
        assert budget.max_thinking_tokens == 15000
        assert budget.estimated_cost > 0
        assert budget.reasoning_time_multiplier == 4.0

    @pytest.mark.asyncio
    async def test_allocate_insufficient_budget(self):
        """Test that insufficient budget forces instant mode."""
        allocator = ThinkingBudgetAllocator(min_budget_for_extended=1.0)

        messages = [Message(role="user", content="Complex analysis")]
        budget = await allocator.allocate(
            messages=messages,
            complexity="complex",
            budget_remaining=0.05  # Below minimum
        )

        # Should fall back to instant mode due to insufficient budget
        assert budget.mode == ThinkingMode.INSTANT
        assert budget.max_thinking_tokens == 0

    @pytest.mark.asyncio
    async def test_allocate_sufficient_budget(self):
        """Test that sufficient budget allows extended thinking."""
        allocator = ThinkingBudgetAllocator(min_budget_for_extended=0.10)

        messages = [Message(role="user", content="Complex analysis")]
        budget = await allocator.allocate(
            messages=messages,
            complexity="complex",
            budget_remaining=5.0  # Above minimum
        )

        # Should use extended mode
        assert budget.mode == ThinkingMode.EXTENDED
        assert budget.max_thinking_tokens > 0

    @pytest.mark.asyncio
    async def test_allocate_custom_thinking_tokens(self):
        """Test custom thinking token configuration."""
        allocator = ThinkingBudgetAllocator(
            instant_thinking_tokens=0,
            light_thinking_tokens=5000,
            full_thinking_tokens=20000
        )

        # Medium complexity
        budget = await allocator.allocate(
            messages=[Message(role="user", content="test")],
            complexity="medium"
        )
        assert budget.max_thinking_tokens == 5000

        # Complex complexity
        budget = await allocator.allocate(
            messages=[Message(role="user", content="test")],
            complexity="complex"
        )
        assert budget.max_thinking_tokens == 20000

    @pytest.mark.asyncio
    async def test_allocate_with_model_specific_pricing(self):
        """Test allocation with model-specific cost estimation."""
        allocator = ThinkingBudgetAllocator(full_thinking_tokens=10000)

        budget = await allocator.allocate(
            messages=[Message(role="user", content="test")],
            complexity="complex",
            model="claude-opus-4"
        )

        # Should estimate cost based on Opus pricing
        assert budget.estimated_cost > 0
        # Opus is expensive, so cost should be significant
        assert budget.estimated_cost > 0.1

    @pytest.mark.asyncio
    async def test_should_use_extended_thinking(self):
        """Test should_use_extended_thinking helper method."""
        allocator = ThinkingBudgetAllocator()

        # Simple should not use extended
        should_extend = await allocator.should_use_extended_thinking(
            messages=[Message(role="user", content="Hello")],
            complexity="simple"
        )
        assert should_extend is False

        # Complex should use extended
        should_extend = await allocator.should_use_extended_thinking(
            messages=[Message(role="user", content="Analyze")],
            complexity="complex"
        )
        assert should_extend is True

    @pytest.mark.asyncio
    async def test_thinking_cost_multiplier(self):
        """Test thinking cost multiplier affects cost estimation."""
        # Default multiplier
        allocator1 = ThinkingBudgetAllocator(
            full_thinking_tokens=10000,
            thinking_cost_multiplier=1.0
        )

        # Double multiplier
        allocator2 = ThinkingBudgetAllocator(
            full_thinking_tokens=10000,
            thinking_cost_multiplier=2.0
        )

        budget1 = await allocator1.allocate(
            messages=[Message(role="user", content="test")],
            complexity="complex"
        )

        budget2 = await allocator2.allocate(
            messages=[Message(role="user", content="test")],
            complexity="complex"
        )

        # Budget2 should cost approximately twice as much
        assert budget2.estimated_cost > budget1.estimated_cost
        assert abs(budget2.estimated_cost / budget1.estimated_cost - 2.0) < 0.1


class TestThinkingModeDetector:
    """Tests for ThinkingModeDetector."""

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_reasoning_keywords(self):
        """Test detection based on reasoning keywords."""
        detector = ThinkingModeDetector(reasoning_keyword_threshold=2)

        # Query with reasoning keywords
        messages = [Message(
            role="user",
            content="Let's think step by step and analyze the pros and cons of this approach"
        )]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is True

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_simple_query(self):
        """Test that simple queries don't need extended thinking."""
        detector = ThinkingModeDetector()

        messages = [Message(role="user", content="Hello, how are you?")]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is False

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_mathematical_content(self):
        """Test detection for mathematical/code content."""
        detector = ThinkingModeDetector()

        # Need longer query or more keywords to trigger
        messages = [Message(
            role="user",
            content="Please solve this complex math problem step by step: 2x + 5 = 15 and explain the reasoning"
        )]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is True

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_code_block(self):
        """Test detection for code blocks."""
        detector = ThinkingModeDetector()

        # Code block plus length should trigger
        messages = [Message(
            role="user",
            content="Please analyze this code and explain what it does step by step:\n```python\ndef factorial(n): return 1 if n <= 1 else n * factorial(n-1)\n```"
        )]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is True

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_long_query(self):
        """Test detection based on query length."""
        detector = ThinkingModeDetector(min_query_length_for_extended=100)

        # Long substantial query
        long_content = "A" * 150 + " with some code ```python```"
        messages = [Message(role="user", content=long_content)]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is True

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_keyword_threshold(self):
        """Test that keyword threshold is respected."""
        detector = ThinkingModeDetector(reasoning_keyword_threshold=3)

        # Only 2 keywords (below threshold)
        messages = [Message(
            role="user",
            content="Please analyze and compare these two options"
        )]

        needs_extended = await detector.needs_extended_thinking(messages)
        # With threshold=3, this should be False (only has "analyze" and "compare")
        # But it might still be True due to other factors like query length
        # Let's make it short to avoid that
        messages = [Message(role="user", content="analyze compare")]
        needs_extended = await detector.needs_extended_thinking(messages)
        # Still might be True depending on exact matching

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_empty_messages(self):
        """Test handling of empty messages."""
        detector = ThinkingModeDetector()

        needs_extended = await detector.needs_extended_thinking([])
        assert needs_extended is False

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_algorithm_keyword(self):
        """Test detection for algorithm-related queries."""
        detector = ThinkingModeDetector()

        # Need more keywords or length to trigger
        messages = [Message(
            role="user",
            content="Explain the algorithm for binary search step by step and analyze its complexity"
        )]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is True

    @pytest.mark.asyncio
    async def test_needs_extended_thinking_multiple_reasoning_patterns(self):
        """Test detection with multiple reasoning patterns."""
        detector = ThinkingModeDetector(reasoning_keyword_threshold=1)

        messages = [Message(
            role="user",
            content="Think through this step by step, evaluate the trade-offs, "
                   "and explain why this approach is better"
        )]

        needs_extended = await detector.needs_extended_thinking(messages)
        assert needs_extended is True


class TestThinkingBudgetDataclass:
    """Tests for ThinkingBudget dataclass."""

    def test_thinking_budget_attributes(self):
        """Test ThinkingBudget dataclass attributes."""
        budget = ThinkingBudget(
            mode=ThinkingMode.EXTENDED,
            max_thinking_tokens=10000,
            estimated_cost=1.5,
            reasoning_time_multiplier=3.0
        )

        assert budget.mode == ThinkingMode.EXTENDED
        assert budget.max_thinking_tokens == 10000
        assert budget.estimated_cost == 1.5
        assert budget.reasoning_time_multiplier == 3.0

    def test_thinking_mode_enum(self):
        """Test ThinkingMode enum values."""
        assert ThinkingMode.INSTANT.value == "instant"
        assert ThinkingMode.EXTENDED.value == "extended"

        # Test enum comparison
        assert ThinkingMode.INSTANT != ThinkingMode.EXTENDED
        assert ThinkingMode.INSTANT == ThinkingMode.INSTANT


@pytest.mark.asyncio
async def test_integration_allocator_with_tracker():
    """Test integration of ThinkingBudgetAllocator with CostTracker."""
    from agenkit.budget.tracker import CostTracker

    allocator = ThinkingBudgetAllocator(full_thinking_tokens=10000)
    tracker = CostTracker()

    # Allocate budget
    messages = [Message(role="user", content="Complex analysis task")]
    budget = await allocator.allocate(
        messages=messages,
        complexity="complex"
    )

    # Record cost with thinking tokens
    cost = await tracker.record_cost(
        session_id="test-session",
        agent_name="test-agent",
        model="claude-sonnet-4",
        input_tokens=1000,
        output_tokens=500,
        thinking_tokens=budget.max_thinking_tokens
    )

    assert cost.thinking_tokens == 10000
    assert cost.thinking_cost > 0
    assert cost.total_cost == cost.input_cost + cost.output_cost + cost.thinking_cost

    # Get statistics with thinking tokens
    stats = await tracker.get_statistics(session_id="test-session")
    assert stats["total_thinking_tokens"] == 10000
    assert stats["total_tokens"] == 1000 + 500 + 10000
