# Budget Tracking

Comprehensive token and cost tracking for LLM-powered agents with provider-specific pricing, limits, and optimization strategies.

## Overview

The Budget package provides fine-grained control over token usage and costs, essential for production deployments where controlling LLM expenses is critical. Track usage across multiple models, enforce limits, and optimize spending.

**Key Statistics:**
- **Python**: 1,520 lines
- **Go**: 1,728 lines (114% parity)
- **Providers**: OpenAI, Anthropic, Google, custom
- **Precision**: Per-token cost tracking

## Features

✅ **Multi-Provider Support** - OpenAI, Anthropic Claude, Google Gemini, custom providers
✅ **Token Counting** - Accurate token estimation per model
✅ **Cost Tracking** - Real-time cost calculation with provider-specific pricing
✅ **Budget Limits** - Enforce token and cost limits with alerts
✅ **Optimization** - Identify cost-saving opportunities
✅ **Cross-language** - Full Python/Go parity
✅ **Production Ready** - Thread-safe, tested at scale

## Installation

Budget tracking is included in the core Agenkit package:

```bash
# Python
pip install agenkit

# Go
go get github.com/agenkit/agenkit-go/budget
```

## Quick Start

### Python

```python
from agenkit.budget import BudgetTracker

# Create budget tracker
tracker = BudgetTracker(
    max_tokens=100000,      # 100K token limit
    max_cost=10.0,          # $10 cost limit
    model="claude-sonnet-4"
)

# Track token usage
tracker.add_tokens(
    prompt_tokens=500,
    completion_tokens=1000
)

# Check status
print(f"Tokens used: {tracker.tokens_used}/{tracker.max_tokens}")
print(f"Cost: ${tracker.cost:.2f}/${tracker.max_cost:.2f}")
print(f"Remaining: {tracker.budget_remaining_percent():.1f}%")

# Check if budget exceeded
if tracker.is_budget_exceeded():
    print("WARNING: Budget limit exceeded!")
```

**Output:**
```
Tokens used: 1500/100000
Cost: $0.03/$10.00
Remaining: 99.7%
```

### Go

```go
package main

import (
    "fmt"
    "github.com/agenkit/agenkit-go/budget"
)

func main() {
    // Create budget tracker
    tracker := budget.NewBudgetTracker(
        100000,  // max tokens
        10.0,    // max cost
        "claude-sonnet-4",
    )

    // Track usage
    tracker.AddTokens(500, 1000)

    // Check status
    fmt.Printf("Tokens: %d/%d\n", tracker.TokensUsed(), tracker.MaxTokens())
    fmt.Printf("Cost: $%.2f/$%.2f\n", tracker.Cost(), tracker.MaxCost())
    fmt.Printf("Remaining: %.1f%%\n", tracker.BudgetRemainingPercent())

    // Check if exceeded
    if tracker.IsBudgetExceeded() {
        fmt.Println("WARNING: Budget limit exceeded!")
    }
}
```

## Supported Providers

### OpenAI Models

```python
from agenkit.budget import BudgetTracker

# GPT-4 Turbo
tracker_gpt4 = BudgetTracker(
    max_tokens=50000,
    max_cost=5.0,
    model="gpt-4-turbo"
)

# GPT-3.5 Turbo (more cost-effective)
tracker_gpt35 = BudgetTracker(
    max_tokens=100000,
    max_cost=5.0,
    model="gpt-3.5-turbo"
)
```

**Pricing** (as of 2024):
- GPT-4 Turbo: $0.01/1K prompt, $0.03/1K completion
- GPT-3.5 Turbo: $0.0005/1K prompt, $0.0015/1K completion

### Anthropic Claude Models

```python
# Claude Sonnet 4
tracker_sonnet = BudgetTracker(
    max_tokens=100000,
    max_cost=10.0,
    model="claude-sonnet-4"
)

# Claude Haiku (fastest, cheapest)
tracker_haiku = BudgetTracker(
    max_tokens=200000,
    max_cost=5.0,
    model="claude-haiku-3.5"
)

# Claude Opus (most capable)
tracker_opus = BudgetTracker(
    max_tokens=50000,
    max_cost=10.0,
    model="claude-opus-4"
)
```

**Pricing**:
- Claude Sonnet 4: $0.003/1K prompt, $0.015/1K completion
- Claude Haiku 3.5: $0.00025/1K prompt, $0.00125/1K completion
- Claude Opus 4: $0.015/1K prompt, $0.075/1K completion

### Google Gemini Models

```python
# Gemini Pro
tracker_gemini = BudgetTracker(
    max_tokens=100000,
    max_cost=8.0,
    model="gemini-pro"
)
```

### Custom Provider

```python
from agenkit.budget import CustomModelPricing

# Define custom pricing
custom_pricing = CustomModelPricing(
    prompt_price_per_1k=0.002,
    completion_price_per_1k=0.010,
    model_name="my-custom-model"
)

tracker = BudgetTracker(
    max_tokens=100000,
    max_cost=10.0,
    pricing=custom_pricing
)
```

## Advanced Usage

### Multi-Model Tracking

Track usage across multiple models:

**Python:**
```python
from agenkit.budget import MultiModelBudgetTracker

# Track multiple models with shared budget
tracker = MultiModelBudgetTracker(
    models=["gpt-4-turbo", "gpt-3.5-turbo", "claude-sonnet-4"],
    max_cost=50.0  # Shared $50 budget
)

# Track usage per model
tracker.add_tokens("gpt-4-turbo", prompt=100, completion=500)
tracker.add_tokens("gpt-3.5-turbo", prompt=200, completion=800)
tracker.add_tokens("claude-sonnet-4", prompt=150, completion=600)

# Get breakdown
breakdown = tracker.get_breakdown()
for model, stats in breakdown.items():
    print(f"{model}:")
    print(f"  Tokens: {stats['tokens']:,}")
    print(f"  Cost: ${stats['cost']:.2f}")
```

**Go:**
```go
tracker := budget.NewMultiModelBudgetTracker(
    []string{"gpt-4-turbo", "gpt-3.5-turbo", "claude-sonnet-4"},
    50.0,
)

tracker.AddTokens("gpt-4-turbo", 100, 500)
tracker.AddTokens("gpt-3.5-turbo", 200, 800)
tracker.AddTokens("claude-sonnet-4", 150, 600)

breakdown := tracker.GetBreakdown()
for model, stats := range breakdown {
    fmt.Printf("%s: %d tokens, $%.2f\n",
        model, stats.Tokens, stats.Cost)
}
```

### Budget Alerts

Set up alerts for budget thresholds:

**Python:**
```python
from agenkit.budget import BudgetTracker, BudgetAlert

tracker = BudgetTracker(
    max_tokens=100000,
    max_cost=10.0,
    model="claude-sonnet-4"
)

# Add alert callbacks
def alert_50_percent():
    print("WARNING: 50% of budget used!")

def alert_75_percent():
    print("CRITICAL: 75% of budget used!")
    # Send notification, email, etc.

def alert_90_percent():
    print("URGENT: 90% of budget used!")
    # Consider switching to cheaper model

tracker.add_alert(BudgetAlert(threshold=0.5, callback=alert_50_percent))
tracker.add_alert(BudgetAlert(threshold=0.75, callback=alert_75_percent))
tracker.add_alert(BudgetAlert(threshold=0.9, callback=alert_90_percent))

# Alerts fire automatically when thresholds crossed
tracker.add_tokens(prompt=10000, completion=20000)
```

**Go:**
```go
tracker := budget.NewBudgetTracker(100000, 10.0, "claude-sonnet-4")

// Add alert callbacks
tracker.AddAlert(0.5, func() {
    fmt.Println("WARNING: 50% of budget used!")
})

tracker.AddAlert(0.75, func() {
    fmt.Println("CRITICAL: 75% of budget used!")
})

tracker.AddAlert(0.9, func() {
    fmt.Println("URGENT: 90% of budget used!")
})

// Alerts fire automatically
tracker.AddTokens(10000, 20000)
```

### Cost Optimization

Automatically switch models to reduce costs:

**Python:**
```python
from agenkit.budget import CostOptimizer

optimizer = CostOptimizer(
    primary_model="claude-sonnet-4",
    fallback_model="claude-haiku-3.5",  # Cheaper alternative
    cost_threshold=5.0  # Switch after $5 spent
)

# Process message with cost optimization
response = optimizer.process_with_budget(
    agent=agent,
    message=message,
    tracker=tracker
)

# Optimizer automatically switches to cheaper model if needed
print(f"Used model: {optimizer.current_model}")
print(f"Total cost: ${optimizer.total_cost:.2f}")
```

**Go:**
```go
optimizer := budget.NewCostOptimizer(
    "claude-sonnet-4",
    "claude-haiku-3.5",
    5.0,
)

response, err := optimizer.ProcessWithBudget(agent, message, tracker)
fmt.Printf("Used model: %s\n", optimizer.CurrentModel())
fmt.Printf("Total cost: $%.2f\n", optimizer.TotalCost())
```

### Token Estimation

Estimate tokens before sending:

**Python:**
```python
from agenkit.budget import TokenEstimator

estimator = TokenEstimator(model="claude-sonnet-4")

# Estimate tokens for message
prompt = "What is the capital of France?"
estimated = estimator.estimate(prompt)
print(f"Estimated tokens: {estimated}")

# Estimate cost
cost = estimator.estimate_cost(prompt)
print(f"Estimated cost: ${cost:.4f}")

# Check if within budget before sending
if tracker.would_exceed_budget(estimated):
    print("ERROR: Would exceed budget!")
else:
    # Safe to proceed
    response = agent.process(message)
```

**Go:**
```go
estimator := budget.NewTokenEstimator("claude-sonnet-4")

prompt := "What is the capital of France?"
estimated := estimator.Estimate(prompt)
fmt.Printf("Estimated tokens: %d\n", estimated)

cost := estimator.EstimateCost(prompt)
fmt.Printf("Estimated cost: $%.4f\n", cost)

if tracker.WouldExceedBudget(estimated) {
    fmt.Println("ERROR: Would exceed budget!")
} else {
    response, _ := agent.Process(ctx, message)
}
```

### Session-Based Tracking

Track budgets per session/user:

**Python:**
```python
from agenkit.budget import SessionBudgetManager

# Manage budgets for multiple sessions
manager = SessionBudgetManager(
    default_max_tokens=10000,
    default_max_cost=1.0,  # $1 per session
    model="claude-sonnet-4"
)

# Create session tracker
session_id = "user-123"
tracker = manager.get_or_create_session(session_id)

# Track usage for this session
tracker.add_tokens(prompt=50, completion=100)

# Get all session statistics
all_sessions = manager.get_all_sessions()
for session_id, stats in all_sessions.items():
    print(f"Session {session_id}:")
    print(f"  Tokens: {stats['tokens']}")
    print(f"  Cost: ${stats['cost']:.2f}")

# Reset session when done
manager.reset_session(session_id)
```

**Go:**
```go
manager := budget.NewSessionBudgetManager(10000, 1.0, "claude-sonnet-4")

// Get tracker for session
sessionID := "user-123"
tracker := manager.GetOrCreateSession(sessionID)

// Track usage
tracker.AddTokens(50, 100)

// Get all sessions
allSessions := manager.GetAllSessions()
for id, stats := range allSessions {
    fmt.Printf("Session %s: %d tokens, $%.2f\n",
        id, stats.Tokens, stats.Cost)
}

// Reset
manager.ResetSession(sessionID)
```

## Performance Monitoring

### Real-Time Dashboard

Track budget usage in real-time:

**Python:**
```python
from agenkit.budget import BudgetDashboard
from agenkit.observability import init_metrics

# Initialize Prometheus metrics
init_metrics("budget-service", port=8001)

# Create dashboard
dashboard = BudgetDashboard(tracker)

# Metrics are automatically exported:
# - budget_tokens_used
# - budget_tokens_remaining
# - budget_cost_usd
# - budget_remaining_percent

# View at http://localhost:8001/metrics
```

### Cost Analysis

Analyze spending patterns:

**Python:**
```python
from agenkit.budget import CostAnalyzer

analyzer = CostAnalyzer(tracker)

# Get daily breakdown
daily_costs = analyzer.get_daily_costs(days=7)
for date, cost in daily_costs.items():
    print(f"{date}: ${cost:.2f}")

# Get hourly pattern
hourly = analyzer.get_hourly_pattern()
peak_hour = max(hourly, key=hourly.get)
print(f"Peak usage hour: {peak_hour}:00 (${hourly[peak_hour]:.2f})")

# Get model comparison
comparison = analyzer.compare_models()
cheapest = min(comparison, key=lambda x: x['cost_per_1k'])
print(f"Most cost-effective: {cheapest['model']}")
```

## Integration with Middleware

### Rate Limiter + Budget

Combine rate limiting with budget tracking:

**Python:**
```python
from agenkit.middleware import RateLimiterMiddleware
from agenkit.budget import BudgetMiddleware

# Create agent with both protections
protected_agent = RateLimiterMiddleware(
    BudgetMiddleware(
        agent,
        tracker=tracker
    ),
    rate=10.0  # 10 requests/second
)

# Automatically enforces both limits
response = await protected_agent.process(message)
```

### Caching for Cost Savings

Cache responses to reduce LLM calls:

**Python:**
```python
from agenkit.middleware import CachingMiddleware
from agenkit.budget import BudgetTracker

# Track cache savings
tracker = BudgetTracker(max_tokens=100000, max_cost=10.0, model="claude-sonnet-4")

cached_agent = CachingMiddleware(
    agent,
    max_size=1000,
    ttl=3600
)

# First call: uses tokens
response1 = await cached_agent.process(message)
tracker.add_tokens(prompt=50, completion=100)

# Second call: cached (no tokens!)
response2 = await cached_agent.process(message)
# tracker.add_tokens not called

print(f"Cache savings: ${tracker.get_cache_savings():.2f}")
```

## Best Practices

### 1. Set Realistic Limits

```python
# Development
dev_tracker = BudgetTracker(
    max_tokens=10000,
    max_cost=1.0,
    model="claude-haiku-3.5"  # Cheapest for testing
)

# Production - per user/session
prod_tracker = BudgetTracker(
    max_tokens=100000,
    max_cost=10.0,
    model="claude-sonnet-4"
)

# Production - total service
service_tracker = BudgetTracker(
    max_tokens=10_000_000,
    max_cost=1000.0,
    model="claude-sonnet-4"
)
```

### 2. Monitor Continuously

```python
import asyncio

async def budget_monitor():
    while True:
        await asyncio.sleep(60)  # Check every minute

        if tracker.budget_remaining_percent() < 20:
            # Alert team
            send_alert("Budget critically low!")

        if tracker.is_budget_exceeded():
            # Take action
            switch_to_cheaper_model()

asyncio.create_task(budget_monitor())
```

### 3. Estimate Before Processing

```python
# Always estimate first
estimator = TokenEstimator(model="claude-sonnet-4")
estimated = estimator.estimate(prompt)

if tracker.would_exceed_budget(estimated):
    # Use cheaper model or reject
    return "Budget limit reached. Please try again later."

# Safe to proceed
response = await agent.process(message)
tracker.add_tokens(prompt=estimated, completion=len(response))
```

### 4. Use Model Tiers

```python
# Implement tiered model selection
def select_model(complexity: str, budget_remaining: float) -> str:
    if complexity == "simple" or budget_remaining < 0.20:
        return "claude-haiku-3.5"  # Cheap
    elif complexity == "medium" or budget_remaining < 0.50:
        return "claude-sonnet-4"   # Balanced
    else:
        return "claude-opus-4"     # Best quality
```

### 5. Track Per-Feature Costs

```python
# Separate budgets per feature
feature_trackers = {
    "chat": BudgetTracker(max_cost=50.0, model="claude-sonnet-4"),
    "summary": BudgetTracker(max_cost=20.0, model="claude-haiku-3.5"),
    "analysis": BudgetTracker(max_cost=100.0, model="claude-opus-4"),
}

# Track and optimize per feature
def process_feature(feature: str, message):
    tracker = feature_trackers[feature]
    if tracker.is_budget_exceeded():
        return f"{feature} budget exceeded"

    response = agent.process(message)
    tracker.add_tokens(...)
    return response
```

## Examples

See the `examples/budget/` directory:

- `basic_tracking.py` - Simple token and cost tracking
- `multi_model.py` - Track multiple models
- `optimization.py` - Automatic cost optimization
- `alerts.py` - Budget alert system
- `session_tracking.py` - Per-user budget management

## API Reference

### Python API

**BudgetTracker**
- `__init__(max_tokens: int, max_cost: float, model: str)`
- `add_tokens(prompt_tokens: int, completion_tokens: int)`
- `tokens_used() -> int`
- `cost() -> float`
- `budget_remaining_percent() -> float`
- `is_budget_exceeded() -> bool`
- `would_exceed_budget(tokens: int) -> bool`
- `reset()`

**MultiModelBudgetTracker**
- `__init__(models: list[str], max_cost: float)`
- `add_tokens(model: str, prompt: int, completion: int)`
- `get_breakdown() -> dict`

**TokenEstimator**
- `__init__(model: str)`
- `estimate(text: str) -> int`
- `estimate_cost(text: str) -> float`

### Go API

**BudgetTracker**
- `NewBudgetTracker(maxTokens int, maxCost float64, model string) *BudgetTracker`
- `AddTokens(promptTokens, completionTokens int)`
- `TokensUsed() int`
- `Cost() float64`
- `BudgetRemainingPercent() float64`
- `IsBudgetExceeded() bool`
- `Reset()`

**MultiModelBudgetTracker**
- `NewMultiModelBudgetTracker(models []string, maxCost float64) *MultiModelBudgetTracker`
- `AddTokens(model string, prompt, completion int)`
- `GetBreakdown() map[string]BudgetStats`

## Troubleshooting

**Issue**: Costs higher than expected
**Solution**: Check model pricing, verify token counts, review caching effectiveness

**Issue**: Budget exceeded too quickly
**Solution**: Increase limits, switch to cheaper model, implement caching, reduce context size

**Issue**: Inaccurate token estimates
**Solution**: Update token counter, calibrate estimator, use actual counts from API

**Issue**: Can't track multi-model usage
**Solution**: Use MultiModelBudgetTracker or separate trackers per model

## Related Packages

- **[Memory Management](MEMORY.md)** - Optimize context size to reduce tokens
- **[Evaluation](EVALUATION.md)** - Measure cost-effectiveness
- **[Checkpointing](CHECKPOINTING.md)** - Persist budget state

---

**Control your LLM costs!** Start tracking budgets today! 💰
