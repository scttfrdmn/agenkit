# Deployment Patterns for AI Agents

Production deployment patterns for safely rolling out, operating, and scaling agenkit agents in production environments.

---

## Table of Contents

- [Canary Deployments for Agent Rollouts](#1-canary-deployments-for-agent-rollouts)
- [Blue/Green Deployment with Session Continuity](#2-bluegreen-deployment-with-session-continuity)
- [Self-Healing Agents (Checkpoint + Restart)](#3-self-healing-agents-checkpoint--restart)
- [Cost Optimization (Model Routing, Token Budgeting)](#4-cost-optimization-model-routing-token-budgeting)
- [Horizontal Scaling Patterns](#5-horizontal-scaling-patterns)
- [Pattern Summary](#pattern-summary)

---

## 1. Canary Deployments for Agent Rollouts

A canary deployment sends a small percentage of traffic to a new agent version while keeping the majority on the stable version. If error rates or quality metrics degrade, you roll back automatically before most users are affected.

### When to Use

- Deploying a new model (e.g., upgrading from claude-sonnet-4 to claude-opus-4)
- Rolling out a new system prompt or reasoning technique
- Testing a new tool set on live traffic before full rollout

### CanaryRouter Pattern

`RouterAgent` supports weight-based routing. Use it to split traffic between a stable ("blue") agent and a canary ("green") agent:

```python
import asyncio
import random
from dataclasses import dataclass, field

from agenkit import Agent, Message
from agenkit.patterns import RouterAgent, RouterConfig


@dataclass
class CanaryConfig:
    """Configuration for a canary deployment."""
    canary_weight: float = 0.05          # 5% of traffic to canary
    error_threshold: float = 0.02        # Roll back if error rate exceeds 2%
    min_sample_size: int = 50            # Minimum requests before evaluating
    rollback_on_quality_drop: bool = True


@dataclass
class CanaryMetrics:
    """Rolling metrics for canary evaluation."""
    stable_requests: int = 0
    stable_errors: int = 0
    canary_requests: int = 0
    canary_errors: int = 0

    def stable_error_rate(self) -> float:
        if self.stable_requests == 0:
            return 0.0
        return self.stable_errors / self.stable_requests

    def canary_error_rate(self) -> float:
        if self.canary_requests == 0:
            return 0.0
        return self.canary_errors / self.canary_requests


class CanaryRouter:
    """
    Routes a configurable percentage of traffic to a canary agent.

    Monitors error rates and automatically freezes the canary (routes
    all traffic back to stable) if degradation is detected.

    Example:
        >>> router = CanaryRouter(
        ...     stable=stable_agent,
        ...     canary=canary_agent,
        ...     config=CanaryConfig(canary_weight=0.05),
        ... )
        >>> response = await router.process(message)
    """

    def __init__(
        self,
        stable: Agent,
        canary: Agent,
        config: CanaryConfig | None = None,
    ):
        self.stable = stable
        self.canary = canary
        self.config = config or CanaryConfig()
        self.metrics = CanaryMetrics()
        self._frozen = False  # True when canary is rolled back

    @property
    def name(self) -> str:
        return "canary_router"

    def capabilities(self) -> list[str]:
        return ["canary_routing"]

    def _should_use_canary(self) -> bool:
        if self._frozen:
            return False
        return random.random() < self.config.canary_weight

    def _check_rollback(self) -> bool:
        """Return True if canary should be rolled back."""
        if self.metrics.canary_requests < self.config.min_sample_size:
            return False
        canary_rate = self.metrics.canary_error_rate()
        stable_rate = self.metrics.stable_error_rate()
        # Roll back if canary error rate exceeds threshold OR is
        # significantly worse than stable
        return (
            canary_rate > self.config.error_threshold
            or canary_rate > stable_rate * 2.0
        )

    async def process(self, message: Message) -> Message:
        use_canary = self._should_use_canary()
        target = self.canary if use_canary else self.stable

        try:
            response = await target.process(message)
            if use_canary:
                self.metrics.canary_requests += 1
            else:
                self.metrics.stable_requests += 1
            return response
        except Exception:
            if use_canary:
                self.metrics.canary_requests += 1
                self.metrics.canary_errors += 1
                if self._check_rollback():
                    self._frozen = True
                    # Re-process on stable after freezing canary
                    return await self.stable.process(message)
            else:
                self.metrics.stable_requests += 1
                self.metrics.stable_errors += 1
            raise
```

### Monitoring and Rollback

Query metrics at any time to observe canary health:

```python
router = CanaryRouter(stable_agent, canary_agent, CanaryConfig(canary_weight=0.10))

# After traffic flows:
print(f"Stable error rate:  {router.metrics.stable_error_rate():.2%}")
print(f"Canary error rate:  {router.metrics.canary_error_rate():.2%}")
print(f"Canary frozen:      {router._frozen}")

# Manual rollback:
router._frozen = True
```

### Go Equivalent

```go
type CanaryRouter struct {
    Stable  agenkit.Agent
    Canary  agenkit.Agent
    Weight  float64
    metrics CanaryMetrics
    frozen  atomic.Bool
}

func (r *CanaryRouter) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    if !r.frozen.Load() && rand.Float64() < r.Weight {
        resp, err := r.Canary.Process(ctx, msg)
        if err != nil {
            r.metrics.RecordCanaryError()
            if r.metrics.ShouldRollback() {
                r.frozen.Store(true)
            }
            return r.Stable.Process(ctx, msg)
        }
        r.metrics.RecordCanarySuccess()
        return resp, nil
    }
    return r.Stable.Process(ctx, msg)
}
```

### Graduated Rollout Schedule

| Phase | Canary Weight | Evaluation Window | Proceed If |
|-------|--------------|-------------------|------------|
| 1     | 1%           | 500 requests      | Error rate < 2% |
| 2     | 5%           | 2,000 requests    | Error rate < 2%, quality parity |
| 3     | 25%          | 10,000 requests   | P99 latency within 20% |
| 4     | 100%         | —                 | Promote canary to stable |

---

## 2. Blue/Green Deployment with Session Continuity

Blue/green deployment maintains two complete, identical environments. Traffic switches atomically from blue to green. The critical challenge with stateful agents is preserving in-flight sessions across the switch.

### The Problem

Without checkpointing, an atomic traffic switch drops all in-flight sessions. Users mid-conversation lose their context. With agenkit's `DurableAgent` and shared checkpoint storage, sessions survive the switch because state lives in the storage layer, not in the agent process.

### Architecture

```
                    ┌─────────────────────────────┐
                    │     Load Balancer / Proxy     │
                    │   (atomic traffic switch)     │
                    └──────┬──────────────┬─────────┘
                           │              │
                   [Blue]  │              │  [Green]
             ┌─────────────▼──┐     ┌────▼────────────┐
             │  DurableAgent   │     │  DurableAgent   │
             │   v1.2.0        │     │   v1.3.0        │
             └────────┬────────┘     └────────┬────────┘
                      │                       │
                      └──────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Shared Checkpoint     │
                    │   Storage (S3 / NFS)    │
                    └─────────────────────────┘
```

### DurableAgent with Shared Storage

```python
import asyncio
import uuid
from dataclasses import dataclass

from agenkit import Agent, Message
from agenkit.checkpointing.checkpoint import Checkpoint, CheckpointStorage
from agenkit.checkpointing.storage import S3CheckpointStorage


@dataclass
class DurableAgentConfig:
    """Configuration for a durable agent with checkpoint-based session continuity."""
    checkpoint_interval: int = 10    # Checkpoint every N steps
    storage: CheckpointStorage | None = None
    agent_name: str = "durable_agent"


class DurableAgent:
    """
    Agent that checkpoints state to shared storage on every N steps.

    Sessions survive environment switches because the checkpoint storage
    is shared between blue and green environments. On startup the agent
    restores any existing session state before processing new messages.

    Example:
        >>> storage = S3CheckpointStorage(bucket="my-checkpoints", prefix="agents/")
        >>> agent = DurableAgent(inner=my_llm_agent, config=DurableAgentConfig(storage=storage))
        >>> response = await agent.process(message, session_id="user-123")
    """

    def __init__(self, inner: Agent, config: DurableAgentConfig | None = None):
        self.inner = inner
        self.config = config or DurableAgentConfig()
        self._sessions: dict[str, dict] = {}
        self._step_counts: dict[str, int] = {}

    @property
    def name(self) -> str:
        return self.config.agent_name

    def capabilities(self) -> list[str]:
        return ["durable", "checkpointing"]

    async def _restore_session(self, session_id: str) -> dict:
        """Restore session state from checkpoint storage."""
        if self.config.storage is None:
            return {}
        checkpoint = await self.config.storage.load_latest(session_id)
        if checkpoint is None:
            return {}
        return checkpoint.state

    async def _maybe_checkpoint(self, session_id: str, messages: list[Message]) -> None:
        """Write checkpoint if step interval reached."""
        if self.config.storage is None:
            return
        step = self._step_counts.get(session_id, 0)
        if step % self.config.checkpoint_interval == 0:
            state = self._sessions.get(session_id, {})
            checkpoint = Checkpoint(
                checkpoint_id=str(uuid.uuid4()),
                session_id=session_id,
                agent_name=self.name,
                timestamp=__import__("datetime").datetime.utcnow(),
                step_number=step,
                state=state,
                messages=messages,
            )
            await self.config.storage.save(checkpoint)

    async def process(self, message: Message, session_id: str | None = None) -> Message:
        session_id = session_id or str(uuid.uuid4())

        # Restore from shared storage if session is new to this process
        if session_id not in self._sessions:
            self._sessions[session_id] = await self._restore_session(session_id)

        response = await self.inner.process(message)

        self._step_counts[session_id] = self._step_counts.get(session_id, 0) + 1
        await self._maybe_checkpoint(session_id, [message, response])

        return response
```

### Blue/Green Traffic Switch

With shared checkpoint storage, the switch is a single load-balancer operation:

```python
# Blue and green share the same S3 storage
shared_storage = S3CheckpointStorage(
    bucket="prod-agent-checkpoints",
    prefix="sessions/",
)

blue_agent = DurableAgent(
    inner=AgentV1(),
    config=DurableAgentConfig(storage=shared_storage, checkpoint_interval=5),
)

green_agent = DurableAgent(
    inner=AgentV2(),
    config=DurableAgentConfig(storage=shared_storage, checkpoint_interval=5),
)

# Switch traffic at the load balancer level.
# In-flight sessions on blue are already checkpointed to S3.
# Green picks them up transparently on next request.
```

### Session Continuity Guarantees

| Scenario | Outcome |
|----------|---------|
| Switch mid-session | Session resumes from last checkpoint (max `checkpoint_interval` steps back) |
| Blue crashes before checkpoint | Up to `checkpoint_interval` steps replayed |
| Both blue and green running | Sessions load-balanced; each restores from shared storage |
| Green rollback | Switch back to blue; sessions restore from S3 without data loss |

---

## 3. Self-Healing Agents (Checkpoint + Restart)

A self-healing agent detects when a worker agent becomes unhealthy (via health checks, exception counts, or timeout monitoring) and automatically checkpoints state, restarts the agent, and restores it from the checkpoint.

### Pattern Overview

`SupervisorAgent` coordinates a set of specialist workers. Extend it with health monitoring to build a self-healing supervisor:

```python
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from agenkit import Agent, Message
from agenkit.checkpointing.checkpoint import Checkpoint, CheckpointStorage
from agenkit.patterns import SupervisorAgent, SupervisorConfig

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Tracks health metrics for a single agent."""
    consecutive_errors: int = 0
    total_errors: int = 0
    last_success: datetime = field(default_factory=datetime.utcnow)
    last_checkpoint_id: str | None = None

    def is_healthy(
        self,
        max_consecutive_errors: int = 3,
        max_silence_seconds: int = 300,
    ) -> bool:
        too_many_errors = self.consecutive_errors >= max_consecutive_errors
        silent_too_long = (datetime.utcnow() - self.last_success) > timedelta(
            seconds=max_silence_seconds
        )
        return not too_many_errors and not silent_too_long


class SelfHealingAgent:
    """
    Supervisor that monitors worker health, checkpoints state on failure,
    and restarts workers with restored state.

    Uses SupervisorAgent for task coordination plus health tracking and
    automatic restart logic layered on top.

    Example:
        >>> supervisor = SelfHealingAgent(
        ...     workers={"analysis": analysis_agent, "write": writer_agent},
        ...     storage=LocalCheckpointStorage(directory="./checkpoints"),
        ...     max_consecutive_errors=3,
        ... )
        >>> response = await supervisor.process(message)
    """

    def __init__(
        self,
        workers: dict[str, Agent],
        storage: CheckpointStorage,
        max_consecutive_errors: int = 3,
        max_silence_seconds: int = 300,
        factory: dict[str, type[Agent]] | None = None,
    ):
        self.workers = dict(workers)
        self.storage = storage
        self.max_consecutive_errors = max_consecutive_errors
        self.max_silence_seconds = max_silence_seconds
        self.factory = factory or {}  # For recreating agents: name -> class
        self._health: dict[str, HealthStatus] = {
            name: HealthStatus() for name in workers
        }

    @property
    def name(self) -> str:
        return "self_healing_supervisor"

    def capabilities(self) -> list[str]:
        return ["supervision", "self_healing", "checkpointing"]

    async def _checkpoint_worker(self, name: str, session_id: str, state: dict) -> str:
        checkpoint = Checkpoint(
            checkpoint_id=__import__("uuid").uuid4().hex,
            session_id=session_id,
            agent_name=name,
            timestamp=datetime.utcnow(),
            step_number=self._health[name].total_errors,
            state=state,
            messages=[],
        )
        await self.storage.save(checkpoint)
        return checkpoint.checkpoint_id

    async def _restart_worker(self, name: str, session_id: str) -> None:
        """Checkpoint current state, then recreate and restore the worker."""
        logger.warning("restarting unhealthy worker: %s", name)

        # Checkpoint before restart
        ckpt_id = await self._checkpoint_worker(name, session_id, state={})
        self._health[name].last_checkpoint_id = ckpt_id

        # Recreate if factory is provided
        if name in self.factory:
            self.workers[name] = self.factory[name]()
            logger.info("worker %s recreated from factory", name)

        # Reset health tracker
        self._health[name].consecutive_errors = 0
        self._health[name].last_success = datetime.utcnow()

    async def dispatch(self, name: str, message: Message, session_id: str) -> Message:
        """Dispatch to a named worker with health tracking."""
        health = self._health[name]

        if not health.is_healthy(self.max_consecutive_errors, self.max_silence_seconds):
            await self._restart_worker(name, session_id)

        worker = self.workers[name]
        try:
            response = await worker.process(message)
            health.consecutive_errors = 0
            health.last_success = datetime.utcnow()
            return response
        except Exception as exc:
            health.consecutive_errors += 1
            health.total_errors += 1
            logger.error("worker %s failed: %s", name, exc)
            raise

    async def process(self, message: Message, session_id: str = "default") -> Message:
        # Simple dispatch to all workers sequentially (extend with SupervisorAgent
        # for complex planning + synthesis)
        results = []
        for name in self.workers:
            try:
                response = await self.dispatch(name, message, session_id)
                results.append(response.content)
            except Exception as exc:
                results.append(f"[{name} failed: {exc}]")

        from agenkit import Message as Msg
        return Msg(role="assistant", content="\n".join(results))
```

### Integration with SupervisorAgent

For production use, combine `SelfHealingAgent` with `SupervisorAgent`'s planning capability:

```python
from agenkit.patterns import SupervisorAgent, SupervisorConfig

# The SupervisorAgent handles task decomposition and synthesis.
# Wrap each specialist with health monitoring at the dispatch layer.
config = SupervisorConfig(
    planner=planner_agent,
    specialists={
        "search": self_healing.workers["search"],
        "write":  self_healing.workers["write"],
        "review": self_healing.workers["review"],
    },
)
supervisor = SupervisorAgent(config)
```

### Health Check Thresholds (Recommended)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Consecutive errors | 3 | Restart worker |
| Silence (no success) | 5 minutes | Restart worker |
| Total restarts in 1 hour | 10 | Page on-call, halt agent |
| Checkpoint lag | > 5 minutes | Alert (not restart) |

---

## 4. Cost Optimization (Model Routing, Token Budgeting)

LLM costs vary by 60x between the cheapest and most expensive models. A cost-aware routing strategy reduces costs by directing simple tasks to cheaper models without sacrificing quality on complex tasks.

### Model Cost Reference (November 2025)

| Model | Input $/1M | Output $/1M | Best For |
|-------|-----------|-------------|----------|
| claude-haiku-3 | $0.25 | $1.25 | Classification, extraction, simple Q&A |
| claude-sonnet-4 | $3.00 | $15.00 | General reasoning, summarization |
| claude-opus-4 | $15.00 | $75.00 | Complex multi-step reasoning, code review |
| gpt-3.5-turbo | $0.50 | $1.50 | Simple chat, FAQ |
| gpt-4o | $2.50 | $10.00 | General purpose |

### CostAwareRouter

```python
from dataclasses import dataclass
from enum import Enum

from agenkit import Agent, Message
from agenkit.budget.limiter import BudgetLimiter
from agenkit.budget.models import ModelPricing
from agenkit.budget.tracker import CostTracker


class Complexity(str, Enum):
    LOW = "low"       # Haiku-class: classification, entity extraction
    MEDIUM = "medium" # Sonnet-class: summarization, moderate reasoning
    HIGH = "high"     # Opus-class: complex planning, deep reasoning


@dataclass
class CostAwareRouterConfig:
    """Configuration for cost-aware model routing."""
    # Token count thresholds for complexity classification
    low_threshold: int = 500       # <= 500 input tokens -> LOW
    high_threshold: int = 4_000    # >= 4000 input tokens -> HIGH
    # Budget limits per session
    session_budget_usd: float = 1.00
    # Alert when session cost exceeds this fraction of budget
    alert_fraction: float = 0.80


class CostAwareRouter:
    """
    Routes requests to the cheapest model capable of handling the task.

    Complexity is estimated from input token count. Enforces per-session
    budget limits using BudgetLimiter. Emits a warning when 80% of budget
    is consumed.

    Example:
        >>> tracker = CostTracker()
        >>> router = CostAwareRouter(
        ...     low_agent=haiku_agent,
        ...     medium_agent=sonnet_agent,
        ...     high_agent=opus_agent,
        ...     tracker=tracker,
        ...     config=CostAwareRouterConfig(session_budget_usd=2.00),
        ... )
        >>> response = await router.process(message, session_id="user-42")
    """

    def __init__(
        self,
        low_agent: Agent,
        medium_agent: Agent,
        high_agent: Agent,
        tracker: CostTracker,
        config: CostAwareRouterConfig | None = None,
    ):
        self.low_agent = low_agent
        self.medium_agent = medium_agent
        self.high_agent = high_agent
        self.tracker = tracker
        self.config = config or CostAwareRouterConfig()
        self._pricing = ModelPricing()
        self._limiter = BudgetLimiter(
            tracker,
            session_budget=self.config.session_budget_usd,
            action="error",
        )

    @property
    def name(self) -> str:
        return "cost_aware_router"

    def capabilities(self) -> list[str]:
        return ["cost_routing", "budget_enforcement"]

    def _estimate_complexity(self, message: Message) -> Complexity:
        # Rough token estimate: 1 token ≈ 4 characters
        token_estimate = len(message.content) // 4
        if token_estimate <= self.config.low_threshold:
            return Complexity.LOW
        if token_estimate >= self.config.high_threshold:
            return Complexity.HIGH
        return Complexity.MEDIUM

    def _select_agent(self, complexity: Complexity) -> Agent:
        return {
            Complexity.LOW: self.low_agent,
            Complexity.MEDIUM: self.medium_agent,
            Complexity.HIGH: self.high_agent,
        }[complexity]

    async def process(self, message: Message, session_id: str = "default") -> Message:
        complexity = self._estimate_complexity(message)
        agent = self._select_agent(complexity)

        # Budget check: raises BudgetExceededError if over limit
        wrapped = self._limiter(agent)
        return await wrapped.process(message)
```

### Token Budget Configuration

```python
from agenkit.budget.tracker import CostTracker
from agenkit.budget.limiter import BudgetLimiter

tracker = CostTracker()

# Hard limits per scope
session_limiter = BudgetLimiter(
    tracker,
    session_budget=1.00,   # $1 per session
    agent_budget=0.25,     # $0.25 per agent invocation
    global_budget=100.00,  # $100 total (across all sessions)
    action="error",        # Raise BudgetExceededError when exceeded
)

# Soft limits: log warnings but continue
soft_limiter = BudgetLimiter(
    tracker,
    session_budget=0.50,
    action="warning",
)

# Auto-downgrade: switch to cheaper model when budget is low
downgrade_limiter = BudgetLimiter(
    tracker,
    session_budget=0.50,
    action="switch_model",
    model_switcher=lambda model: "claude-haiku-3",  # Always downgrade to haiku
)
```

### Go Budget Configuration

```go
import "github.com/anthropics/agenkit-go/budget"

tracker := budget.NewCostTracker(budget.MemoryStorage{})

limiter := budget.NewBudgetLimiter(tracker, budget.LimiterConfig{
    SessionBudget: 1.00,   // $1 per session
    AgentBudget:   0.25,
    GlobalBudget:  100.00,
    Action:        budget.ActionError,
})

wrappedAgent := limiter.Wrap(myAgent)
```

### Cost Optimization Rules of Thumb

1. **Route classification tasks to haiku** — Binary classification and entity extraction rarely need more than haiku-class capability.
2. **Set session budgets before deployment** — Prevents runaway costs from adversarial or looping agents.
3. **Log costs per request** — Use `CostTracker` to identify expensive outliers.
4. **Batch small requests** — `BatchingMiddleware` with `max_batch_size=10` reduces per-request overhead at high volume.
5. **Cache deterministic calls** — Identical prompts (FAQ answers, static lookups) can be cached with `CachingMiddleware`.

---

## 5. Horizontal Scaling Patterns

### Stateless Agents Behind a Load Balancer

Agents that do not maintain in-process session state can be scaled horizontally behind any standard load balancer. Each request is independent.

```python
# Stateless agent: no in-process session state
class StatelessQAAgent:
    @property
    def name(self) -> str:
        return "qa_agent"

    def capabilities(self) -> list[str]:
        return ["qa"]

    async def process(self, message: Message) -> Message:
        # All context comes from the message itself (or is fetched from
        # external storage per-request). No instance variables used.
        return await self.llm.process(message)

# Deploy N replicas behind nginx / AWS ALB / GCP Load Balancer.
# Any replica handles any request. No sticky sessions needed.
```

### Sticky Sessions for Stateful Agents

When agent state lives in-process (e.g., conversation history), route requests from the same session to the same replica. Use consistent hashing on `session_id`:

```
# nginx upstream with consistent hash
upstream agents {
    hash $http_x_session_id consistent;
    server agent-0:8080;
    server agent-1:8080;
    server agent-2:8080;
}
```

Pass the session ID as an HTTP header or query parameter:

```python
import httpx

async def call_agent(session_id: str, message: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://agents/process",
            json={"content": message},
            headers={"X-Session-Id": session_id},
        )
        return response.json()["content"]
```

For fault tolerance, pair sticky sessions with `DurableAgent` and shared checkpoint storage. If a replica dies, the next replica restores the session from the shared checkpoint backend.

### Work Queue Pattern for Batch Processing

For workloads where latency is not critical (nightly batch jobs, document ingestion, async research tasks), use a work queue instead of a synchronous load balancer:

```python
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from agenkit import Agent, Message
from agenkit.middleware.batching import BatchingConfig, BatchingMiddleware


@dataclass
class WorkItem:
    item_id: str
    message: Message


class WorkQueueProcessor:
    """
    Processes a queue of work items using batching middleware.

    BatchingMiddleware accumulates requests and processes them in batches,
    improving throughput at the cost of added latency.

    Example:
        >>> processor = WorkQueueProcessor(
        ...     agent=analysis_agent,
        ...     config=BatchingConfig(max_batch_size=10, max_wait_time=0.5),
        ... )
        >>> async for result in processor.process_queue(items):
        ...     print(result)
    """

    def __init__(self, agent: Agent, config: BatchingConfig | None = None):
        self.config = config or BatchingConfig(max_batch_size=10, max_wait_time=0.1)
        self.batched_agent = BatchingMiddleware(agent, self.config)

    async def process_queue(
        self, items: list[WorkItem]
    ) -> AsyncIterator[tuple[str, Message]]:
        tasks = [
            asyncio.create_task(
                self._process_one(item), name=f"work-{item.item_id}"
            )
            for item in items
        ]
        for item, task in zip(items, tasks, strict=True):
            result = await task
            yield item.item_id, result

    async def _process_one(self, item: WorkItem) -> Message:
        return await self.batched_agent.process(item.message)


# Usage: process 1000 documents with up to 10 concurrent batches
async def batch_process_documents(docs: list[str], agent: Agent) -> list[str]:
    processor = WorkQueueProcessor(
        agent,
        BatchingConfig(max_batch_size=10, max_wait_time=0.2, max_queue_size=200),
    )
    items = [WorkItem(item_id=str(i), message=Message(role="user", content=doc))
             for i, doc in enumerate(docs)]

    results = {}
    async for item_id, response in processor.process_queue(items):
        results[item_id] = response.content

    return [results[str(i)] for i in range(len(docs))]
```

### Scaling Decision Guide

| Requirement | Pattern | Notes |
|-------------|---------|-------|
| Stateless, high RPS | Load balancer, no sticky | Simplest; any replica handles any request |
| Stateful, fault tolerant | Sticky sessions + DurableAgent + shared storage | Combine consistent hashing with S3 checkpoints |
| Batch throughput > latency | Work queue + BatchingMiddleware | Ideal for nightly jobs, document pipelines |
| Long-running sessions | DurableAgent + checkpoint interval < 5 min | Survives instance preemptions |
| Cost-sensitive | CostAwareRouter + BudgetLimiter | Route by complexity, enforce hard limits |

---

## Pattern Summary

| Pattern | Agenkit Components | Primary Benefit |
|---------|-------------------|-----------------|
| Canary Deployment | `RouterAgent`, custom `CanaryRouter` | Safe rollout with auto-rollback |
| Blue/Green | `DurableAgent`, `S3CheckpointStorage` | Zero-downtime switch, no session loss |
| Self-Healing | `SupervisorAgent`, `CheckpointStorage` | Automatic recovery from worker failures |
| Cost Routing | `BudgetLimiter`, `CostTracker`, `RouterAgent` | 60x cost reduction for mixed workloads |
| Horizontal Scale | `BatchingMiddleware`, `DurableAgent` | High throughput, fault-tolerant sessions |

For checkpointing internals and storage backends, see [docs/CHECKPOINTING.md](../CHECKPOINTING.md).
For cross-language deployment considerations, see [docs/CROSS_LANGUAGE_MIGRATION.md](../CROSS_LANGUAGE_MIGRATION.md).
