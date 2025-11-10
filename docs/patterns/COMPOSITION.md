# Composition Patterns

## Table of Contents
- [Philosophy](#philosophy)
- [Pattern Selection Guide](#pattern-selection-guide)
- [Core Patterns](#core-patterns)
- [Combining Patterns](#combining-patterns)
- [Error Handling Strategies](#error-handling-strategies)
- [Performance Implications](#performance-implications)
- [Best Practices](#best-practices)

## Philosophy

Agent composition is about **combining simple agents to create complex behaviors**. The philosophy:

1. **Composition over Inheritance**: Build systems by combining agents, not subclassing
2. **Single Responsibility**: Each agent does one thing well
3. **Emergent Behavior**: Complex capabilities emerge from simple compositions
4. **Explicit Flow**: Data flow should be obvious from structure

### Why Composition?

```python
# ❌ Bad: Monolithic agent (inheritance)
class SuperAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Validate
        if not self._validate(message):
            return error_response

        # Translate if needed
        if self._detect_language(message) != "en":
            message = await self._translate(message)

        # Process based on type
        if "code" in message.content:
            return await self._handle_code(message)
        elif "data" in message.content:
            return await self._handle_data(message)
        else:
            return await self._handle_general(message)

# ✅ Good: Composed agents
pipeline = SequentialAgent(
    name="processing-pipeline",
    agents=[
        ValidationAgent(),
        TranslationAgent(),
        ConditionalAgent(
            name="router",
            default_agent=GeneralAgent()
        ).add_routes([
            (content_contains("code"), CodeAgent()),
            (content_contains("data"), DataAgent())
        ])
    ]
)
```

**Benefits:**
- Each agent is testable in isolation
- Easy to add/remove/reorder stages
- Clear data flow
- Reusable components

## Pattern Selection Guide

### Decision Tree

```
What's your goal?
│
├─ Process in sequence (stage 1 → stage 2 → stage 3)
│  └─ Use: SequentialAgent ✅
│
├─ Execute concurrently (fan-out, then aggregate)
│  └─ Use: ParallelAgent ✅
│
├─ Try agents until one succeeds (fallback chain)
│  └─ Use: FallbackAgent ✅
│
├─ Route to one agent based on condition
│  └─ Use: ConditionalAgent ✅
│
└─ Something else?
   └─ Combine patterns (see "Combining Patterns" below)
```

### Pattern Characteristics Matrix

| Pattern | Latency | Throughput | Use Case | Error Handling |
|---------|---------|------------|----------|----------------|
| **Sequential** | Sum of all | 1/sum | Pipelines, transformations | Stop on first error |
| **Parallel** | Max of all | N/max | Ensemble, search, A/B test | All-or-nothing |
| **Fallback** | First success | Variable | HA, cost optimization | Try next on error |
| **Conditional** | One agent | 1/one | Routing, specialization | From selected agent |

### Quick Reference

```python
# Sequential: A → B → C
sequential = SequentialAgent(
    name="pipeline",
    agents=[agent_a, agent_b, agent_c]
)

# Parallel: [A, B, C] → aggregate
parallel = ParallelAgent(
    name="ensemble",
    agents=[agent_a, agent_b, agent_c],
    aggregator=voting_function
)

# Fallback: Try A, else B, else C
fallback = FallbackAgent(
    name="ha-service",
    agents=[agent_a, agent_b, agent_c]
)

# Conditional: Route to A or B or C
conditional = ConditionalAgent(
    name="router",
    default_agent=agent_c
)
conditional.add_route(condition_a, agent_a)
conditional.add_route(condition_b, agent_b)
```

## Core Patterns

### 1. Sequential Pattern

**Intent:** Execute agents in order, passing output from one to input of next.

**When to use:**
- Data transformation pipelines (ETL)
- Multi-stage processing
- Validation → processing → formatting
- Order matters

**When NOT to use:**
- Operations are independent (use Parallel)
- Conditional logic needed (use Conditional)
- Need fallback (use Fallback)

**Performance:**
- Latency = sum of all agents
- No parallelism
- Memory: O(1) (one message at a time)

**Example:**
```python
# Content pipeline: Translate → Summarize → Analyze
pipeline = SequentialAgent(
    name="content-pipeline",
    agents=[
        TranslationAgent(),
        SummarizationAgent(),
        SentimentAgent()
    ]
)

# Input: Foreign language text
# Stage 1: Translate to English
# Stage 2: Summarize key points
# Stage 3: Analyze sentiment
result = await pipeline.process(message)
```

**Trade-offs:**
- ✅ Simple, clear, testable
- ✅ Easy to debug (linear flow)
- ❌ Sequential latency
- ❌ One failure stops pipeline

### 2. Parallel Pattern

**Intent:** Execute agents concurrently and aggregate results.

**When to use:**
- Independent operations
- Ensemble methods (voting, consensus)
- Multi-source search
- A/B testing
- Latency reduction

**When NOT to use:**
- Operations have dependencies (use Sequential)
- Order matters
- Resource constraints
- Need first result only

**Performance:**
- Latency = max of all agents
- Throughput = N× calls
- Memory: O(N) results
- CPU: N concurrent tasks

**Example:**
```python
# Ensemble: Get predictions from 3 models
ensemble = ParallelAgent(
    name="model-ensemble",
    agents=[
        ModelA(),
        ModelB(),
        ModelC()
    ],
    aggregator=lambda results: majority_vote(results)
)

# All three models run concurrently
# Aggregator combines results (e.g., voting)
result = await ensemble.process(message)
```

**Trade-offs:**
- ✅ Reduced latency (max vs sum)
- ✅ Redundancy, consensus
- ❌ N× resource cost
- ❌ Complexity (aggregation logic)

### 3. Fallback Pattern

**Intent:** Try agents in order until one succeeds.

**When to use:**
- High availability requirements
- Cost optimization (cheap → expensive)
- Quality tiers (premium → basic)
- Multi-region failover
- Rate limit handling

**When NOT to use:**
- All must succeed (use Sequential)
- Need all results (use Parallel)
- Fallback masks issues

**Performance:**
- Latency = first successful agent
- Best case: First agent
- Worst case: Sum of all failures + last success
- Memory: O(1)

**Example:**
```python
# HA service: Primary → Secondary → Tertiary
ha_service = FallbackAgent(
    name="ha-service",
    agents=[
        PrimaryService(),    # Try first (fast, premium)
        SecondaryService(),  # Fallback (medium)
        TertiaryService()    # Last resort (slow, free)
    ]
)

# Tries each until one succeeds
# Metadata shows which tier was used
result = await ha_service.process(message)
tier = result.metadata["fallback_agent_used"]
```

**Trade-offs:**
- ✅ High availability
- ✅ Cost optimization
- ✅ Graceful degradation
- ❌ Latency from retries
- ❌ May mask root causes

### 4. Conditional Pattern

**Intent:** Route message to one agent based on condition.

**When to use:**
- Intent-based routing
- Specialized agents
- Load balancing
- User-specific routing
- A/B testing

**When NOT to use:**
- All agents should run (use Parallel)
- Sequential processing (use Sequential)
- Simple if/else suffices

**Performance:**
- Latency = routing + one agent
- Routing should be O(1) or O(log N)
- Memory: O(1)

**Example:**
```python
# Intent router: Code vs Docs vs General
router = ConditionalAgent(
    name="intent-router",
    default_agent=GeneralAgent()
)

router.add_route(
    condition=lambda msg: "code" in msg.content.lower(),
    agent=CodeAgent()
)

router.add_route(
    condition=lambda msg: "explain" in msg.content.lower(),
    agent=DocsAgent()
)

# Routes to one specialized agent
result = await router.process(message)
```

**Trade-offs:**
- ✅ Specialization
- ✅ Resource optimization
- ✅ Personalization
- ❌ Routing complexity
- ❌ Misrouting impacts UX

## Combining Patterns

The real power comes from **composing patterns together**.

### Pattern 1: Sequential of Parallels

**Use case:** Multi-stage processing where each stage fans out.

```python
# Stage 1: Parallel validation (multiple validators)
stage1 = ParallelAgent(
    name="validators",
    agents=[SyntaxValidator(), SemanticValidator(), SecurityValidator()],
    aggregator=lambda results: all_passed(results)
)

# Stage 2: Process
stage2 = ProcessingAgent()

# Stage 3: Parallel formatting (multiple formats)
stage3 = ParallelAgent(
    name="formatters",
    agents=[JSONFormatter(), XMLFormatter(), MarkdownFormatter()],
    aggregator=lambda results: combine_formats(results)
)

# Combine: (Parallel) → (Single) → (Parallel)
pipeline = SequentialAgent(
    name="validation-processing-formatting",
    agents=[stage1, stage2, stage3]
)
```

**Benefits:**
- Parallel validation (fast)
- Single processing (correctness)
- Parallel formatting (efficiency)

### Pattern 2: Conditional with Fallback

**Use case:** Route to specialized agent with fallback.

```python
# Specialized agents with fallbacks
premium_with_fallback = FallbackAgent(
    name="premium-tier",
    agents=[PremiumAPI(), StandardAPI()]
)

free_with_fallback = FallbackAgent(
    name="free-tier",
    agents=[FreeAPI(), LocalModel()]
)

# Route by user tier
router = ConditionalAgent(
    name="tier-router",
    default_agent=free_with_fallback
)

router.add_route(
    condition=lambda msg: msg.metadata.get("tier") == "premium",
    agent=premium_with_fallback
)
```

**Benefits:**
- Tier-based routing
- HA within each tier
- Cost optimization

### Pattern 3: Parallel with Different Strategies

**Use case:** Ensemble with diverse approaches.

```python
# Different agent types in parallel
ensemble = ParallelAgent(
    name="diverse-ensemble",
    agents=[
        # Fast heuristic
        HeuristicAgent(),

        # ML model
        MLAgent(),

        # LLM
        LLMAgent(),

        # Rule-based
        RuleAgent()
    ],
    aggregator=weighted_vote  # Weight by confidence
)
```

**Benefits:**
- Diverse perspectives
- Redundancy
- Ensemble benefits

### Pattern 4: Sequential with Conditional Stages

**Use case:** Dynamic pipeline based on data.

```python
# Stage 1: Classify
classifier = ClassificationAgent()

# Stage 2: Route to specialist
router = ConditionalAgent(
    name="specialist-router",
    default_agent=GeneralAgent()
)
router.add_route(
    condition=lambda msg: msg.metadata.get("type") == "code",
    agent=CodeSpecialist()
)
router.add_route(
    condition=lambda msg: msg.metadata.get("type") == "data",
    agent=DataSpecialist()
)

# Stage 3: Format
formatter = FormatterAgent()

# Combine: Classify → Route → Format
pipeline = SequentialAgent(
    name="adaptive-pipeline",
    agents=[classifier, router, formatter]
)
```

**Benefits:**
- Classification informs routing
- Specialized processing
- Consistent formatting

### Pattern 5: Nested Conditionals

**Use case:** Hierarchical routing (coarse → fine-grained).

```python
# Coarse routing by domain
domain_router = ConditionalAgent(
    name="domain-router",
    default_agent=general_agent
)

# Fine-grained routing within code domain
code_router = ConditionalAgent(
    name="code-router",
    default_agent=general_code_agent
)
code_router.add_route(is_python, python_agent)
code_router.add_route(is_javascript, js_agent)
code_router.add_route(is_rust, rust_agent)

# Fine-grained routing within data domain
data_router = ConditionalAgent(
    name="data-router",
    default_agent=general_data_agent
)
data_router.add_route(is_sql, sql_agent)
data_router.add_route(is_csv, csv_agent)

# Add to domain router
domain_router.add_route(is_code_domain, code_router)
domain_router.add_route(is_data_domain, data_router)
```

**Benefits:**
- Hierarchical specialization
- Scalable routing
- Maintainable structure

## Error Handling Strategies

### Strategy 1: Fail Fast (Sequential Default)

```python
# Sequential stops on first error
pipeline = SequentialAgent(
    name="fail-fast",
    agents=[
        ValidationAgent(),  # If fails, stop here
        ProcessAgent(),
        FormatAgent()
    ]
)

try:
    result = await pipeline.process(message)
except ValidationError:
    # Handle early failure
    pass
```

**When to use:** Invalid data shouldn't be processed

### Strategy 2: Best Effort (Parallel with Partial Results)

```python
def partial_aggregator(results: list[Message]) -> Message:
    """Aggregate even with some failures."""
    successful = [r for r in results if not is_error(r)]
    if not successful:
        raise Exception("All agents failed")
    return combine(successful)

ensemble = ParallelAgent(
    name="best-effort",
    agents=[agent1, agent2, agent3],
    aggregator=partial_aggregator
)
```

**When to use:** Some results better than none

### Strategy 3: Graceful Degradation (Fallback)

```python
fallback = FallbackAgent(
    name="graceful",
    agents=[
        HighQualityAgent(),    # Try first
        MediumQualityAgent(),  # If fails, try this
        BasicAgent()           # Always succeeds
    ]
)

# Always returns *something*
result = await fallback.process(message)
quality = result.metadata.get("quality_tier")
```

**When to use:** Must return result, quality can vary

### Strategy 4: Retry with Transform

```python
class RetryWithTransformAgent(Agent):
    """Retry with modified input on failure."""

    async def process(self, message: Message) -> Message:
        try:
            return await self._agent.process(message)
        except ValidationError as e:
            # Transform input and retry
            fixed = self._fix_validation_error(message, e)
            return await self._agent.process(fixed)
```

**When to use:** Can fix input programmatically

### Strategy 5: Circuit Breaker

```python
class CircuitBreakerAgent(Agent):
    """Stop trying agent if failure rate too high."""

    def __init__(self, agent: Agent, threshold: float = 0.5):
        self._agent = agent
        self._threshold = threshold
        self._failures = 0
        self._requests = 0
        self._open = False

    async def process(self, message: Message) -> Message:
        if self._open:
            raise Exception("Circuit breaker open")

        self._requests += 1

        try:
            result = await self._agent.process(message)
            return result
        except Exception:
            self._failures += 1

            # Open circuit if failure rate exceeds threshold
            if self._failures / self._requests > self._threshold:
                self._open = True

            raise
```

**When to use:** Protect system from failing dependencies

## Performance Implications

### Latency Analysis

```python
# Sequential: Latency = sum
# [100ms] → [200ms] → [150ms] = 450ms total
sequential = SequentialAgent(agents=[a, b, c])

# Parallel: Latency = max
# [100ms]
# [200ms]  } = 200ms total (max)
# [150ms]
parallel = ParallelAgent(agents=[a, b, c])

# Fallback: Variable (best to worst)
# Best case: 100ms (first succeeds)
# Worst case: 100ms + 200ms + 150ms = 450ms (all fail but last)
fallback = FallbackAgent(agents=[a, b, c])

# Conditional: One agent + routing
# Routing: 5ms
# Agent: 100ms
# Total: 105ms
conditional = ConditionalAgent(...)
```

### Throughput Analysis

```python
# Sequential: 1 / sum(latencies)
# 1 / 450ms = 2.2 requests/sec

# Parallel: N / max(latency)
# 3 / 200ms = 15 requests/sec (3× agents, but constrained by slowest)

# Optimal parallel: All same latency
# 3 / 100ms = 30 requests/sec
```

### Resource Usage

```python
# Memory
sequential: O(1)  # One message at a time
parallel: O(N)    # N messages concurrently
fallback: O(1)    # One at a time
conditional: O(1) # One agent

# Connections (to external services)
sequential: 1     # Sequential connections
parallel: N       # N concurrent connections
fallback: 1       # One at a time
conditional: 1    # One agent

# CPU
sequential: 1 core effectively used
parallel: N cores can be used
fallback: 1 core
conditional: 1 core + routing overhead
```

### Optimization Strategies

#### 1. Profile Before Optimizing

```python
import time

async def profile_composition():
    start = time.perf_counter()

    # Profile each stage
    stage_times = []
    for agent in pipeline.unwrap():
        stage_start = time.perf_counter()
        await agent.process(message)
        stage_times.append(time.perf_counter() - stage_start)

    total = time.perf_counter() - start

    # Find bottleneck
    slowest_idx = stage_times.index(max(stage_times))
    print(f"Bottleneck: Stage {slowest_idx} ({stage_times[slowest_idx]:.2f}s)")
```

#### 2. Parallelize Independent Operations

```python
# ❌ Slow: Sequential independent operations
sequential = SequentialAgent([
    FetchUserData(),
    FetchProductData(),
    FetchOrderData()
])
# Total: 100ms + 150ms + 120ms = 370ms

# ✅ Fast: Parallel independent operations
parallel = ParallelAgent([
    FetchUserData(),
    FetchProductData(),
    FetchOrderData()
])
# Total: max(100ms, 150ms, 120ms) = 150ms
```

#### 3. Cache Expensive Operations

```python
# Add caching to expensive agent
cached_agent = CacheMiddleware(
    ExpensiveAgent(),
    ttl=300  # 5 minutes
)

pipeline = SequentialAgent([
    cheap_agent,
    cached_agent,  # Cached
    another_cheap_agent
])
```

#### 4. Short-Circuit When Possible

```python
class EarlyExitSequential(Agent):
    """Sequential that can exit early."""

    async def process(self, message: Message) -> Message:
        for agent in self._agents:
            message = await agent.process(message)

            # Exit early if done
            if message.metadata.get("complete"):
                return message

        return message
```

#### 5. Load Balance Conditional Routes

```python
def load_balanced_routing(message: Message) -> bool:
    """Route to least-loaded agent."""
    # Track load per agent
    loads = {agent.name: agent.current_load() for agent in agents}

    # Route to least loaded
    min_load_agent = min(loads.items(), key=lambda x: x[1])
    return min_load_agent[0]
```

## Best Practices

### 1. Design for Composition

```python
# ✅ Good: Single responsibility, composable
class ValidationAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Just validate
        errors = self._validate(message)
        message.metadata["valid"] = len(errors) == 0
        message.metadata["errors"] = errors
        return message

class ProcessingAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Check validation result
        if not message.metadata.get("valid"):
            return message  # Pass through

        # Process
        return self._process(message)

# Compose them
pipeline = SequentialAgent([
    ValidationAgent(),
    ProcessingAgent()
])
```

### 2. Use Metadata for Context

```python
# Pass context through metadata
message.metadata["user_id"] = user_id
message.metadata["request_id"] = request_id
message.metadata["timestamp"] = time.time()

# Agents can use this context
class ContextAwareAgent(Agent):
    async def process(self, message: Message) -> Message:
        user_id = message.metadata.get("user_id")
        # Use context...
        return result
```

### 3. Make Composition Observable

```python
# Add hooks for observability
pipeline = SequentialAgent(
    agents=[agent1, agent2, agent3],
    before_agent=lambda agent, msg: logger.info(f"Starting {agent.name}"),
    after_agent=lambda agent, msg: logger.info(f"Finished {agent.name}")
)
```

### 4. Test Compositions

```python
# Test the composition
async def test_pipeline():
    # Create pipeline
    pipeline = SequentialAgent([
        ValidationAgent(),
        ProcessAgent(),
        FormatAgent()
    ])

    # Test happy path
    result = await pipeline.process(valid_message)
    assert result.metadata.get("formatted")

    # Test error path
    with pytest.raises(ValidationError):
        await pipeline.process(invalid_message)
```

### 5. Document Data Flow

```python
class ContentPipeline(SequentialAgent):
    """
    Content processing pipeline.

    Data flow:
    1. TranslationAgent: Foreign language → English
    2. SummarizationAgent: Full text → Summary
    3. SentimentAgent: Summary → Sentiment + score

    Metadata flow:
    - translated: bool (added by TranslationAgent)
    - summary_length: int (added by SummarizationAgent)
    - sentiment: str (added by SentimentAgent)
    - sentiment_score: float (added by SentimentAgent)
    """

    def __init__(self):
        super().__init__(
            name="content-pipeline",
            agents=[
                TranslationAgent(),
                SummarizationAgent(),
                SentimentAgent()
            ]
        )
```

---

## Summary

**Choose your pattern:**
- **Sequential**: A → B → C (pipelines)
- **Parallel**: [A, B, C] → aggregate (ensemble)
- **Fallback**: Try A, else B, else C (HA)
- **Conditional**: Route to A or B or C (routing)

**Combine patterns:**
- Sequential of Parallels
- Conditional with Fallback
- Nested Conditionals
- And more...

**Performance:**
- Sequential: Latency = sum
- Parallel: Latency = max
- Fallback: Variable
- Conditional: One + routing

**Best practices:**
- Single responsibility
- Use metadata for context
- Make observable
- Test compositions
- Document data flow

**Next:** See the `/examples/composition/` directory for complete examples of each pattern.
