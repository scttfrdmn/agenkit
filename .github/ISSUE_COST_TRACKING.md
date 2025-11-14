# Cost Tracking & Budget Management for Autonomous Agents

## Problem Statement

**November 2025 Reality:** Autonomous agents can now run for 30+ hours (Claude Sonnet 4.5), and reasoning models are expensive:

- **OpenAI o3:** ~$5/1M input tokens, ~$15/1M output tokens
- **Claude Opus 4:** ~$15/1M input tokens, ~$75/1M output tokens
- **Claude Sonnet 4.5:** ~$3/1M input tokens, ~$15/1M output tokens

**Problem:** A 30-hour autonomous agent could easily rack up hundreds of dollars in costs without monitoring.

**Real Scenario:**
```
Agent runs for 30 hours
Processes 1000 requests
Average 10K tokens input + 5K output per request
Total: 10M input + 5M output tokens
Cost: (10M * $15 + 5M * $75) / 1M = $150 + $375 = $525
```

**Current State:** No built-in cost tracking. Users must manually calculate, no way to set budgets or stop runaway costs.

## Proposed Solution

Implement comprehensive cost tracking and budget management middleware.

### Architecture

```python
agenkit/
  budget/              # NEW PACKAGE
    tracker.py         # CostTracker - track spend per session/agent
    limiter.py         # BudgetLimiter - stop at threshold
    optimizer.py       # ModelOptimizer - route based on complexity/cost
    models.py          # Model pricing data
```

### 1. Cost Tracker

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Cost:
    """Single cost record."""
    session_id: str
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: datetime
    metadata: dict

class CostTracker:
    """
    Track LLM costs per session, agent, and globally.

    Features:
    - Per-session cost tracking
    - Per-agent cost tracking
    - Global cost tracking
    - Cost breakdown by model
    - Time-series cost data
    """

    def __init__(self, storage: Optional[Storage] = None):
        """
        Args:
            storage: Optional persistent storage (Redis, Postgres, etc.)
                     If None, uses in-memory storage
        """
        self.storage = storage or InMemoryStorage()
        self.model_pricing = ModelPricing()  # Pricing data

    async def record_cost(
        self,
        session_id: str,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[dict] = None
    ) -> Cost:
        """Record a cost event."""
        # Calculate cost
        input_cost = self.model_pricing.calculate(
            model, input_tokens, "input"
        )
        output_cost = self.model_pricing.calculate(
            model, output_tokens, "output"
        )
        total_cost = input_cost + output_cost

        # Create record
        cost = Cost(
            session_id=session_id,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            timestamp=datetime.now(UTC),
            metadata=metadata or {}
        )

        # Store
        await self.storage.store(cost)

        return cost

    async def get_session_cost(
        self,
        session_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """Get total cost for session (optionally in time range)."""
        costs = await self.storage.query(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time
        )
        return sum(c.total_cost for c in costs)

    async def get_agent_cost(
        self,
        agent_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """Get total cost for agent."""
        costs = await self.storage.query(
            agent_name=agent_name,
            start_time=start_time,
            end_time=end_time
        )
        return sum(c.total_cost for c in costs)

    async def get_breakdown(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> dict[str, float]:
        """Get cost breakdown by model."""
        costs = await self.storage.query(
            session_id=session_id,
            agent_name=agent_name
        )

        breakdown = {}
        for cost in costs:
            breakdown[cost.model] = breakdown.get(cost.model, 0) + cost.total_cost

        return breakdown

    async def get_top_sessions(self, limit: int = 10) -> list[tuple[str, float]]:
        """Get top N sessions by cost."""
        costs = await self.storage.query()
        session_totals = {}

        for cost in costs:
            session_totals[cost.session_id] = (
                session_totals.get(cost.session_id, 0) + cost.total_cost
            )

        sorted_sessions = sorted(
            session_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_sessions[:limit]
```

### 2. Budget Limiter (Middleware)

```python
class BudgetLimiter:
    """
    Middleware that enforces cost budgets.

    Stops agent execution when budget exceeded.
    """

    def __init__(
        self,
        tracker: CostTracker,
        session_budget: Optional[float] = None,  # $ per session
        agent_budget: Optional[float] = None,    # $ per agent
        global_budget: Optional[float] = None,   # $ global
        action: str = "error"  # "error", "warning", "switch_model"
    ):
        self.tracker = tracker
        self.session_budget = session_budget
        self.agent_budget = agent_budget
        self.global_budget = global_budget
        self.action = action

    def __call__(self, agent: Agent) -> Agent:
        """Wrap agent with budget enforcement."""

        @functools.wraps(agent.process)
        async def wrapped_process(message: Message) -> Message:
            session_id = message.metadata.get("session_id")
            agent_name = agent.name

            # Check budgets before processing
            if self.session_budget:
                current_cost = await self.tracker.get_session_cost(session_id)
                if current_cost >= self.session_budget:
                    if self.action == "error":
                        raise BudgetExceededError(
                            f"Session budget ${self.session_budget} exceeded "
                            f"(current: ${current_cost:.2f})"
                        )
                    elif self.action == "warning":
                        logger.warning(f"Session budget exceeded: ${current_cost:.2f}")

            if self.agent_budget:
                current_cost = await self.tracker.get_agent_cost(agent_name)
                if current_cost >= self.agent_budget:
                    raise BudgetExceededError(
                        f"Agent budget ${self.agent_budget} exceeded"
                    )

            # Process
            response = await agent.process(message)

            # Record cost (extract from response metadata)
            if "usage" in response.metadata:
                usage = response.metadata["usage"]
                await self.tracker.record_cost(
                    session_id=session_id,
                    agent_name=agent_name,
                    model=response.metadata.get("model", "unknown"),
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    metadata={"message_id": message.metadata.get("message_id")}
                )

            return response

        agent.process = wrapped_process
        return agent
```

### 3. Model Optimizer (Cost-Quality Tradeoff)

```python
class ModelOptimizer:
    """
    Intelligently route requests to models based on complexity and cost.

    Strategy:
    - Simple queries → Cheap model (Haiku, GPT-3.5)
    - Medium queries → Mid-tier (Sonnet 4, GPT-4)
    - Complex queries → Expensive (Opus 4, o3)
    """

    def __init__(
        self,
        cheap_llm: LLM,      # e.g., Claude Haiku
        medium_llm: LLM,     # e.g., Claude Sonnet 4
        expensive_llm: LLM,  # e.g., Claude Opus 4 or o3
        complexity_detector: Callable = None
    ):
        self.cheap = cheap_llm
        self.medium = medium_llm
        self.expensive = expensive_llm
        self.detector = complexity_detector or self._default_complexity_detector

    async def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> Message:
        """Route to appropriate model based on complexity."""
        complexity = await self.detector(messages)

        if complexity == "simple":
            model = self.cheap
        elif complexity == "medium":
            model = self.medium
        else:  # complex
            model = self.expensive

        response = await model.complete(messages, **kwargs)
        response.metadata["selected_model"] = model.model
        response.metadata["complexity"] = complexity

        return response

    async def _default_complexity_detector(
        self,
        messages: list[Message]
    ) -> str:
        """
        Default complexity detection heuristic.

        Factors:
        - Query length (longer = more complex)
        - Keywords (reasoning, analysis, comparison = complex)
        - History length (more context = more complex)
        """
        latest = messages[-1].content if messages else ""

        # Simple heuristics (can be replaced with LLM-based detection)
        complex_keywords = [
            "analyze", "compare", "reasoning", "explain why",
            "step by step", "think through", "evaluate"
        ]

        if len(latest) > 500:
            return "complex"
        elif any(kw in latest.lower() for kw in complex_keywords):
            return "medium"
        elif len(messages) > 10:
            return "medium"
        else:
            return "simple"
```

### Model Pricing Data

```python
class ModelPricing:
    """Pricing data for LLM models (as of November 2025)."""

    PRICING = {
        # OpenAI
        "gpt-4o": {"input": 2.50, "output": 10.00},  # per 1M tokens
        "gpt-4-turbo": {"input": 10.00, "output": 30.00"},
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
    }

    def calculate(
        self,
        model: str,
        tokens: int,
        direction: str  # "input" or "output"
    ) -> float:
        """Calculate cost for tokens."""
        if model not in self.PRICING:
            logger.warning(f"Unknown model {model}, using default pricing")
            return tokens * 0.01 / 1000  # Fallback estimate

        price_per_million = self.PRICING[model][direction]
        return (tokens / 1_000_000) * price_per_million

    @classmethod
    def update_pricing(cls, model: str, input_price: float, output_price: float):
        """Update pricing for model (for testing or custom deployments)."""
        cls.PRICING[model] = {"input": input_price, "output": output_price}
```

## Usage Examples

### Example 1: Basic Cost Tracking

```python
from agenkit.budget import CostTracker, BudgetLimiter

# Create tracker
tracker = CostTracker()

# Wrap agent with budget enforcer
agent = BudgetLimiter(
    tracker,
    session_budget=10.00,  # Max $10 per session
    action="error"
)(my_agent)

# Use agent
response = await agent.call(messages, session_id="user-123")

# Check costs
session_cost = await tracker.get_session_cost("user-123")
print(f"Session cost: ${session_cost:.2f}")

# Get breakdown
breakdown = await tracker.get_breakdown(session_id="user-123")
# {"claude-sonnet-4": 2.50, "claude-opus-4": 5.75}
```

### Example 2: Cost Optimization

```python
from agenkit.budget import ModelOptimizer
from agenkit.adapters.llm import AnthropicLLM

# Create models
cheap = AnthropicLLM(api_key, "claude-haiku-3")
medium = AnthropicLLM(api_key, "claude-sonnet-4")
expensive = AnthropicLLM(api_key, "claude-opus-4")

# Create optimizer
optimizer = ModelOptimizer(cheap, medium, expensive)

# Use optimizer (automatically routes based on complexity)
response = await optimizer.complete(messages)

# Check which model was used
print(f"Selected: {response.metadata['selected_model']}")
print(f"Complexity: {response.metadata['complexity']}")
```

### Example 3: Dashboard/Reporting

```python
# Get top 10 costliest sessions
top_sessions = await tracker.get_top_sessions(limit=10)
for session_id, cost in top_sessions:
    print(f"{session_id}: ${cost:.2f}")

# Get agent performance
agent_cost = await tracker.get_agent_cost("research-assistant")
print(f"Research assistant total cost: ${agent_cost:.2f}")

# Time-based analysis
today = datetime.now(UTC).replace(hour=0, minute=0, second=0)
today_cost = await tracker.get_session_cost(
    "user-123",
    start_time=today
)
print(f"Today's cost: ${today_cost:.2f}")
```

## Go Implementation

```go
package budget

type Cost struct {
    SessionID    string
    AgentName    string
    Model        string
    InputTokens  int
    OutputTokens int
    InputCost    float64
    OutputCost   float64
    TotalCost    float64
    Timestamp    time.Time
    Metadata     map[string]interface{}
}

type CostTracker interface {
    RecordCost(ctx context.Context, cost *Cost) error
    GetSessionCost(ctx context.Context, sessionID string, opts ...Option) (float64, error)
    GetAgentCost(ctx context.Context, agentName string, opts ...Option) (float64, error)
    GetBreakdown(ctx context.Context, opts ...Option) (map[string]float64, error)
}

type BudgetLimiter struct {
    tracker       CostTracker
    sessionBudget *float64
    agentBudget   *float64
    action        string
}

func (b *BudgetLimiter) Wrap(agent Agent) Agent {
    // Middleware implementation
}
```

## Acceptance Criteria

### Cost Tracker
- [ ] CostTracker class (Python + Go)
- [ ] Multiple storage backends (InMemory, Redis, Postgres)
- [ ] Per-session, per-agent, global tracking
- [ ] Cost breakdown by model
- [ ] Time-series queries
- [ ] Tests (20+ tests)

### Budget Limiter
- [ ] BudgetLimiter middleware (Python + Go)
- [ ] Session budget enforcement
- [ ] Agent budget enforcement
- [ ] Global budget enforcement
- [ ] Multiple actions (error, warning, switch_model)
- [ ] Tests (15+ tests)

### Model Optimizer
- [ ] ModelOptimizer class (Python + Go)
- [ ] Complexity detection (default + custom)
- [ ] Automatic model routing
- [ ] Cost-quality tradeoffs
- [ ] Tests (10+ tests)

### Model Pricing
- [ ] ModelPricing class with current rates
- [ ] Support for major providers (OpenAI, Anthropic, Google)
- [ ] Update mechanism for pricing changes
- [ ] Tests (5+ tests)

### Documentation
- [ ] Cost tracking guide
- [ ] Budget management best practices
- [ ] Model optimization strategies
- [ ] Dashboard/reporting examples
- [ ] Production deployment guide

### Examples
- [ ] Basic cost tracking example
- [ ] Budget enforcement example
- [ ] Model optimization example
- [ ] Dashboard/reporting example
- [ ] Multi-agent cost tracking

## Related

- Complements LLM adapters (#58)
- Required for long-running agents (#69)
- Enables production deployments
- Foundation for evaluation (#73)

## Priority

**Critical** - Q4 2025 (Nov-Dec)

Prevents runaway costs in 30-hour autonomous agents.

## Labels

`enhancement`, `budget`, `cost-tracking`, `python`, `go`, `q4-2025`, `critical`
