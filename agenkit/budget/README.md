# Cost Tracking & Budget Management

> **Status**: Production Ready
> **Python**: ✅ | **Go**: 🚧 Planned Q1 2026

## Overview

The Agenkit Budget System provides comprehensive cost tracking and budget management for LLM-powered autonomous agents. Essential for preventing runaway costs in long-running agents (30+ hour operations).

## Quick Start

```python
from agenkit.budget import CostTracker, BudgetLimiter

# Track costs
tracker = CostTracker()
await tracker.record_cost(
    "session-123",
    "assistant",
    "claude-sonnet-4",
    input_tokens=1000,
    output_tokens=500
)

# Enforce budget
limiter = BudgetLimiter(tracker, session_budget=10.00)
wrapped_agent = limiter(agent)
```

## Components

### 1. ModelPricing
Pricing data for major LLM providers (November 2025 rates):
- **OpenAI**: GPT-4o, o3, o3-mini
- **Anthropic**: Claude Opus 4, Sonnet 4/4.5, Haiku 3
- **Google**: Gemini 2.0, Pro

### 2. CostTracker
Track costs per session, agent, and globally:
- Per-session cost tracking
- Per-agent cost tracking
- Cost breakdown by model
- Time-series cost data
- Multiple storage backends (InMemory, Redis, Postgres)

### 3. BudgetLimiter (Middleware)
Enforce cost budgets:
- Session budgets
- Agent budgets
- Global budgets
- Actions: error, warning, switch_model

### 4. ModelOptimizer
Intelligent model routing based on complexity:
- Simple queries → Cheap model (Haiku)
- Medium queries → Mid-tier (Sonnet 4)
- Complex queries → Expensive (Opus 4, o3)
- Heuristic or LLM-based complexity detection

## Real-World Scenario

**30-hour autonomous agent without budget control:**
```
Processes: 1000 requests
Tokens: 10M input + 5M output
Model: Claude Opus 4
Cost: $150 (input) + $375 (output) = $525 💸
```

**With budget management:**
```python
tracker = CostTracker()
limiter = BudgetLimiter(tracker, session_budget=100.00, action="error")
optimizer = ModelOptimizer(cheap, medium, expensive)  # Route intelligently

# Cost: ~$50 (10x savings) ✅
```

## Examples

See `examples/budget/cost_tracking_demo.py` for:
1. Basic cost tracking
2. Budget enforcement
3. Cost analysis and reporting
4. Model cost comparison
5. 30-hour scenario simulation

## API Reference

### CostTracker

```python
tracker = CostTracker(storage=InMemoryStorage())

# Record cost
await tracker.record_cost(
    session_id="session-123",
    agent_name="assistant",
    model="claude-sonnet-4",
    input_tokens=1000,
    output_tokens=500,
    metadata={"request_id": "req-456"}
)

# Query costs
session_cost = await tracker.get_session_cost("session-123")
agent_cost = await tracker.get_agent_cost("assistant")
breakdown = await tracker.get_breakdown(session_id="session-123")
top_sessions = await tracker.get_top_sessions(limit=10)
```

### BudgetLimiter

```python
limiter = BudgetLimiter(
    tracker=tracker,
    session_budget=10.00,   # $10 per session
    agent_budget=50.00,     # $50 per agent
    global_budget=100.00,   # $100 total
    action="error"          # or "warning"
)

wrapped_agent = limiter(agent)
```

### ModelOptimizer

```python
optimizer = ModelOptimizer(
    cheap_model="claude-haiku-3",
    medium_model="claude-sonnet-4",
    expensive_model="claude-opus-4",
    llm_clients={
        "claude-haiku-3": haiku_client,
        "claude-sonnet-4": sonnet_client,
        "claude-opus-4": opus_client
    },
    complexity_detector=HeuristicComplexityDetector()
)

response = await optimizer.complete(messages)
print(response.metadata["selected_model"])  # Auto-selected based on complexity
```

## Testing

```bash
# Run tests (30 tests)
uv run pytest tests/budget/ -v

# Run example
python examples/budget/cost_tracking_demo.py
```

## Model Pricing (November 2025)

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| GPT-4o | $2.50 | $10.00 |
| o3 | $5.00 | $15.00 |
| o3-mini | $1.00 | $3.00 |
| Claude Opus 4 | $15.00 | $75.00 |
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Claude Haiku 3 | $0.25 | $1.25 |
| Gemini 2.0 Flash | $0.00 | $0.00 (free tier) |

## Best Practices

1. **Always track costs** in production deployments
2. **Set session budgets** for user-facing agents ($1-$10)
3. **Set global budgets** for autonomous systems ($50-$100/day)
4. **Use ModelOptimizer** for cost savings (2-10x cheaper)
5. **Monitor top sessions** to identify expensive usage patterns
6. **Alert on budget warnings** before limits reached

## Related

- [Memory Systems](../memory/) - Context management for long-running agents
- [Agent Safety Framework](../safety/) - Security for autonomous agents
- [Long-Running Agents](#) - Checkpointing and state management

## Contributing

Found pricing outdated? Submit a PR with updated rates!

```python
ModelPricing.PRICING["new-model"] = {
    "input": 1.50,
    "output": 5.00
}
```
