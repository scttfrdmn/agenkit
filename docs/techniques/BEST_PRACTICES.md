# Best Practices and Decision Guides

Actionable guidance for choosing the right agenkit abstraction, optimizing performance, hardening security, and preparing agents for production.

---

## Table of Contents

- [When to Use Patterns vs Compositions vs Techniques](#1-when-to-use-patterns-vs-compositions-vs-techniques)
- [Performance Optimization Checklist](#2-performance-optimization-checklist)
- [Security Hardening Checklist](#3-security-hardening-checklist)
- [Deployment Readiness Checklist](#4-deployment-readiness-checklist)
- [Cross-Language Migration Guide](#5-cross-language-migration-guide)

---

## 1. When to Use Patterns vs Compositions vs Techniques

Agenkit has three distinct abstraction layers. Choosing the wrong one leads to over-engineered code (using a full pattern when a technique suffices) or under-powered code (using a raw LLM call when a pattern is warranted).

### Definitions

**Patterns** are reusable architectural templates that solve recurring agent *coordination* problems. They define clear roles, interactions, and lifecycle. Agenkit provides 18 named patterns.

- Examples: `RouterAgent`, `SupervisorAgent`, `ReflectionAgent`, `PlanningAgent`, `AutonomousAgent`
- Use when: multiple agents interact, execution has multiple phases, coordination logic is non-trivial

**Compositions** are lightweight combinations of patterns for a specific workflow. They are not new patterns — they are *recipes* that wire existing patterns together.

- Examples: `SequentialAgent([validation, router, writer])`, `FallbackAgent([primary, backup])`, `ParallelAgent([search, compute])`
- Use when: you need to connect two or more patterns in a straightforward pipeline

**Techniques** are prompt engineering approaches that shape LLM *reasoning* within a single call. They do not introduce new agents or coordination — they change how one LLM thinks.

- Examples: `ChainOfThought`, `TreeOfThought`, `SelfConsistency`, `LeastToMost`, `PlanAndSolve`
- Use when: improving the quality of a single LLM's output, not coordinating between agents

### Decision Flowchart

```
Start: I need to build an agent behavior
            │
            ▼
   Does it require multiple                  NO
   agents coordinating? ──────────────────────────►  Does the LLM need
            │                                        structured reasoning?
           YES                                            │
            │                                           YES│        NO
            ▼                                            ▼          ▼
   Is there a named pattern            Apply a         Just use
   that fits? (see table below)      Technique        a plain LLM
            │
     YES ◄──┼──► NO
     │               │
     ▼               ▼
Use the          Compose existing
Pattern          patterns (Sequential,
                 Parallel, Fallback)
```

### Use-Case to Abstraction Mapping

| Use Case | Best Abstraction | Example |
|----------|-----------------|---------|
| Route by intent to specialist agent | Pattern: `RouterAgent` | Customer support triage |
| Iterative critique and rewrite | Pattern: `ReflectionAgent` | Code review, essay editing |
| Decompose task and delegate | Pattern: `SupervisorAgent` | Research + write + publish |
| Break down a problem step by step | Technique: `ChainOfThought` | Math, logical deduction |
| Validate multiple reasoning paths | Technique: `SelfConsistency` | High-stakes decisions |
| Run agents A then B in order | Composition: `SequentialAgent` | Validate input, then process |
| Try primary, fall back to backup | Composition: `FallbackAgent` | Primary model + backup model |
| Run agents concurrently | Composition: `ParallelAgent` | Parallel search + compute |
| Long-running autonomous task | Pattern: `AutonomousAgent` | Autonomous research loop |
| Human approval required | Pattern: `HumanInLoopAgent` | Approval before executing |
| Shared memory across agents | Pattern: `MemoryHierarchyAgent` | Multi-session context |

### When NOT to Use a Pattern

- **Simple single-turn Q&A**: A raw LLM call with a good prompt is sufficient.
- **Static text transformation**: If the output is deterministic given the input, consider a non-LLM approach.
- **One-off scripts**: Patterns add structure that pays off over the lifetime of a system, not in a throwaway script.

---

## 2. Performance Optimization Checklist

Performance in agenkit systems is dominated by LLM call latency and cost. Network, CPU, and memory overhead from the toolkit itself is negligible (<1% of total request time in benchmarks).

### Checklist

1. **Use `ParallelAgent` for independent subtasks.**
   When subtasks do not depend on each other's output, run them concurrently. For N independent agents each taking T seconds, sequential execution takes N×T; parallel takes T + coordination overhead (~5ms).

   ```python
   from agenkit.patterns import ParallelAgent, ParallelConfig

   # Independent: search, compute, classify can all run at once
   parallel = ParallelAgent(ParallelConfig(
       agents=[search_agent, compute_agent, classify_agent]
   ))
   ```

2. **Cache deterministic LLM calls with `CachingMiddleware`.**
   FAQ responses, static document summaries, and classification labels for common inputs are deterministic. Cache them. A cache hit avoids both latency (typically 500ms–2s per call) and cost.

   ```python
   from agenkit.middleware.caching import CachingMiddleware, CachingConfig

   cached_agent = CachingMiddleware(
       agent=classifier_agent,
       config=CachingConfig(max_size=1000, ttl_seconds=3600),
   )
   ```

   Target cache hit rate: >30% for FAQ/classification workloads.

3. **Batch small requests with `BatchingMiddleware`.**
   At >100 RPS, individual LLM calls have significant per-request overhead. Batching 10 requests together reduces API round-trips by 10x.

   ```python
   from agenkit.middleware.batching import BatchingMiddleware, BatchingConfig

   batched_agent = BatchingMiddleware(
       agent=my_agent,
       config=BatchingConfig(
           max_batch_size=10,
           max_wait_time=0.1,   # 100ms max latency added
           max_queue_size=500,
       ),
   )
   ```

   Use batching when: throughput > 50 RPS and added latency < 500ms is acceptable.

4. **Right-size models by task complexity.**
   Route by complexity, not by convenience. A haiku-class model ($0.25/1M input) is 60x cheaper than opus-class ($15/1M input) and sufficient for classification, extraction, and simple Q&A.

   | Task Type | Recommended Model | Rationale |
   |-----------|------------------|-----------|
   | Binary classification | claude-haiku-3 | High accuracy, lowest cost |
   | Entity extraction | claude-haiku-3 | Structured output, no reasoning needed |
   | Summarization (short) | claude-haiku-3 | Sufficient for <2K token inputs |
   | General reasoning | claude-sonnet-4 | Good balance of quality and cost |
   | Complex multi-step | claude-opus-4 | Reserve for tasks that genuinely need it |

5. **Set explicit token budgets on every agent.**
   Unbounded agents can consume 10x their expected cost due to loops, verbose outputs, or adversarial inputs. Always configure `BudgetLimiter`.

   ```python
   from agenkit.budget.limiter import BudgetLimiter
   from agenkit.budget.tracker import CostTracker

   tracker = CostTracker()
   limiter = BudgetLimiter(tracker, session_budget=1.00, action="error")
   safe_agent = limiter(my_agent)
   ```

   Recommended limits: $0.10–$1.00 per session for interactive agents; $1.00–$10.00 for autonomous research agents.

6. **Profile before optimizing.**
   Use `CostTracker.get_session_costs(session_id)` to identify which agents are the cost and latency bottlenecks before applying caching, batching, or model downgrades.

---

## 3. Security Hardening Checklist

1. **Validate all user inputs before passing to the LLM.**
   Use `InputValidationAgent` to check for prompt injection patterns, maximum length, and disallowed content before the LLM sees the input.

   ```python
   from agenkit.safety.input_validation import InputValidator, ValidationConfig

   validator = InputValidator(ValidationConfig(
       max_length=4096,
       block_patterns=[r"ignore previous instructions", r"system prompt"],
       strip_html=True,
   ))
   pipeline = SequentialAgent([validator, my_agent])
   ```

2. **Redact PII from logs and LLM responses.**
   Names, emails, phone numbers, and credit card numbers must not appear in logs or be returned to unpermissioned callers. Apply output validation.

   ```python
   from agenkit.safety.output_validation import OutputValidator, OutputValidationConfig

   redacted_agent = OutputValidator(
       agent=my_agent,
       config=OutputValidationConfig(redact_pii=True),
   )
   ```

3. **Apply least-privilege permissions with `PermissionsConfig`.**
   Agents should only have the permissions they need. An agent that only reads files should not have `WRITE_FILES` or `EXECUTE_COMMANDS`.

   ```python
   from agenkit.safety.permissions import Permission, PermissionsConfig, PermissionGuard

   read_only_config = PermissionsConfig(
       allowed=[Permission.READ_FILES, Permission.QUERY_DATABASE],
   )
   guarded_agent = PermissionGuard(agent=my_agent, config=read_only_config)
   ```

4. **Rotate API keys on a schedule and never hard-code them.**
   Store API keys in environment variables or a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager). Set a rotation schedule of 90 days or less.

   ```python
   import os
   # CORRECT: read from environment
   api_key = os.environ["ANTHROPIC_API_KEY"]

   # WRONG: hard-coded
   # api_key = "sk-ant-..."
   ```

5. **Monitor for prompt injection patterns.**
   Log and alert on inputs that contain injection indicators: "ignore previous", "new instructions", "system:", "you are now", role-switching commands. Use `InputValidator` block patterns and route flagged inputs to a human review queue.

6. **Never expose internal agent topology to users.**
   Error messages, stack traces, and agent names reveal system structure. Catch all exceptions at the API boundary and return a generic error message. Log the detail internally.

   ```python
   async def api_handler(request):
       try:
           return await agent.process(message)
       except Exception:
           logger.exception("agent error for request %s", request.id)
           # Return generic message; do not include exc or agent name
           return {"error": "request could not be processed"}
   ```

7. **Audit all tool invocations.**
   Use `agenkit.safety.audit` or `agenkit.observability.audit` to log every tool call with timestamp, agent identity, parameters (with PII redacted), and result. Retain audit logs for 90+ days for compliance.

---

## 4. Deployment Readiness Checklist

Use this checklist before switching any production traffic to a new agent or agent version.

1. **Retry and circuit breaker configured on all LLM calls.**
   LLM APIs have transient errors (rate limits, 529s, timeouts). All agents must use `RetryMiddleware` and `CircuitBreakerMiddleware`.

   ```python
   from agenkit.middleware.retry import RetryMiddleware, RetryConfig
   from agenkit.middleware.circuit_breaker import CircuitBreakerMiddleware, CircuitBreakerConfig

   resilient_agent = CircuitBreakerMiddleware(
       RetryMiddleware(
           my_agent,
           RetryConfig(max_attempts=3, base_delay=1.0, exponential_base=2.0),
       ),
       CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30.0),
   )
   ```

2. **Health checks implemented and registered.**
   Expose a `/health` endpoint that verifies the agent can be instantiated and that required dependencies (LLM API, storage) are reachable. Use a timeout of 5 seconds.

3. **Graceful shutdown handles in-flight requests.**
   On SIGTERM, stop accepting new requests, allow in-flight requests to complete (30-second drain window), checkpoint any open sessions, then exit.

4. **Checkpoint interval under 5 minutes for long-running sessions.**
   For sessions expected to last more than 5 minutes, set `checkpoint_interval` such that checkpoints are written at least every 5 minutes. This limits replay cost after a restart.

   ```python
   # At ~10s per step, interval=30 checkpoints every ~5 minutes
   DurableAgentConfig(checkpoint_interval=30, storage=shared_storage)
   ```

5. **Token budget alerts configured.**
   Set `action="warning"` at 80% of budget and `action="error"` at 100%. Alert on-call when a session exceeds 80% budget more than 10 times in an hour.

6. **Shadow mode validation complete before traffic switch.**
   Run the new agent version in shadow mode (receives all traffic but responses are discarded) for a minimum of 1,000 requests or 24 hours. Compare outputs against the stable version before promoting.

7. **Rollback plan documented and tested.**
   Know exactly how to roll back: which load-balancer flag to flip, how long rollback takes, and whether in-flight sessions are preserved. Practice the rollback in staging before the production rollout.

8. **Observability pipeline active.**
   Distributed traces, cost metrics, error rates, and latency histograms must be flowing to your observability backend before traffic is switched. Do not deploy blind.

---

## 5. Cross-Language Migration Guide

Agenkit provides 100% feature parity across Python, Go, TypeScript, Rust, C++, and Zig. Migrating is a structural translation, not a feature backport.

### When to Migrate from Python to Go

Migrate to Go when:

- **Throughput > 1,000 RPS** — Go's goroutine model handles concurrent connections with lower memory overhead than Python's asyncio. Python async is efficient but the GIL (even in 3.13 free-threaded mode) creates contention at high concurrency.
- **P99 latency target < 100ms** — Go's runtime avoids Python's interpreter overhead. Benchmarks show Go agenkit is 3–10x faster for CPU-bound middleware (caching, routing, serialization).
- **Low-memory containerized deployment** — Go agents use ~10–30MB RSS vs. ~50–150MB for a Python agent with dependencies.
- **Team is already operating Go services** — Operational uniformity reduces cognitive overhead.

Stay in Python when:

- **Prototyping or research** — Python's iteration speed and REPL workflow dominate.
- **ML integrations** — PyTorch, TensorFlow, Hugging Face, LangChain integrations are Python-first. Wrapping them for Go adds friction.
- **Team is Python-primary** — A correct Python service beats an incorrect Go service. Language skill trumps benchmarks.
- **Evaluation-heavy workflows** — `agenkit.evaluation` (Bayesian optimizer, A/B testing, regression benchmarks) is Python-only as of v0.49.0.

### Migration Checklist: Python to Go

1. **Inventory all patterns used.** List every `agenkit.*` import in the Python codebase. Confirm each has a Go equivalent in `agenkit-go/`.
2. **Confirm middleware parity.** Check that every middleware (retry, circuit breaker, caching, batching, rate limiting, budget) used in Python is available in `agenkit-go/middleware/`.
3. **Translate configuration structs.** Python uses dataclasses (`RouterConfig`, `SupervisorConfig`); Go uses structs with the same field names (snake_case → camelCase).
4. **Update error handling.** Python raises exceptions; Go returns `(result, error)`. Every `await agent.process(msg)` becomes `resp, err := agent.Process(ctx, msg)` with explicit error handling.
5. **Replace async/await with goroutines.** Python `asyncio.gather` → Go `errgroup.Group` or `sync.WaitGroup`.
6. **Run test parity suite.** Use `./scripts/test-parity.sh` to verify identical behavior between Python and Go implementations.
7. **Shadow-mode validate.** Run the Go service in shadow mode alongside Python for 24 hours, comparing outputs before switching traffic.

### Migration Checklist: Python to TypeScript

1. Replace Python `async def` with TypeScript `async` functions.
2. Convert `@dataclass` configurations to TypeScript interfaces.
3. Replace `agenkit.patterns.*` imports with `@anthropic/agenkit/patterns`.
4. Python `Optional[X]` → TypeScript `X | undefined`.
5. Verify `agenkit-ts` middleware covers all Python middleware used.

### Detailed Migration Guides

For step-by-step translation of specific patterns, configurations, and idioms, see:

- [docs/CROSS_LANGUAGE_MIGRATION.md](../CROSS_LANGUAGE_MIGRATION.md) — Overview and all migration paths
- [docs/MIGRATE_PYTHON_TO_GO.md](../MIGRATE_PYTHON_TO_GO.md) — Python → Go with code examples
- [docs/MIGRATE_PYTHON_TO_TYPESCRIPT.md](../MIGRATE_PYTHON_TO_TYPESCRIPT.md) — Python → TypeScript
- [docs/MIGRATE_PYTHON_TO_RUST.md](../MIGRATE_PYTHON_TO_RUST.md) — Python → Rust (ownership model)
- [docs/LANGUAGE_PROFILE_GO.md](../LANGUAGE_PROFILE_GO.md) — Go-specific idioms and patterns

---

## Quick Reference: Abstraction Selection

```
Is this about how one LLM reasons?
  → Use a Technique (CoT, ToT, SelfConsistency)

Is this about connecting two or more agents in a pipeline?
  → Use a Composition (Sequential, Parallel, Fallback)

Is this a recurring coordination problem with roles and lifecycle?
  → Use a named Pattern (Router, Supervisor, Reflection, ...)

Is this about runtime behavior (cost, resilience, observability)?
  → Use Middleware (BudgetLimiter, RetryMiddleware, CachingMiddleware, ...)
```
