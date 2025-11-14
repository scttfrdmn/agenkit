# Implement Agent Patterns from Guide

## Problem Statement

The Agent Patterns Guide (docs-site/guides/agent-patterns.md) documents 7 core agent patterns, but we don't have reference implementations. Users need working code to see how these patterns are built with Agenkit's minimal interface.

## Proposed Solution

Implement the 7 patterns documented in Chapters 5-11 of the guide:

### Pattern Implementations

**1. Sequential Pattern** (Chapter 6)
```python
class SequentialAgent:
    """Pipeline of agents executing in order."""

    def __init__(self, agents: list[Agent]):
        self.agents = agents

    async def call(self, messages: list[Message], **kwargs) -> Message:
        result = messages
        for agent in self.agents:
            result = await agent.call(result, **kwargs)
        return result
```

**2. Parallel Pattern** (Chapter 7)
```python
class ParallelAgent:
    """Concurrent agent execution with aggregation."""

    def __init__(self, agents: list[Agent], aggregator: Callable):
        self.agents = agents
        self.aggregator = aggregator

    async def call(self, messages: list[Message], **kwargs) -> Message:
        results = await asyncio.gather(*[
            agent.call(messages, **kwargs) for agent in self.agents
        ])
        return self.aggregator(results)
```

**3. Supervisor Pattern** (Chapter 8)
```python
class SupervisorAgent:
    """Hierarchical coordination with central supervisor."""

    def __init__(self, planner: LLM, specialists: dict[str, Agent]):
        self.planner = planner
        self.specialists = specialists

    async def call(self, messages: list[Message], **kwargs) -> Message:
        # Plan decomposition
        plan = await self.planner.create_plan(messages)

        # Delegate to specialists
        results = []
        for subtask in plan:
            specialist = self.specialists[subtask.type]
            result = await specialist.call(subtask.messages)
            results.append(result)

        # Synthesize
        return await self.planner.synthesize(results)
```

**4. Router Pattern** (Chapter 9)
```python
class RouterAgent:
    """Conditional agent selection based on routing logic."""

    def __init__(self, classifier: LLM, agents: dict[str, Agent]):
        self.classifier = classifier
        self.agents = agents

    async def call(self, messages: list[Message], **kwargs) -> Message:
        # Classify intent
        category = await self.classifier.classify(messages)

        # Route to appropriate agent
        agent = self.agents[category]
        return await agent.call(messages, **kwargs)
```

**5. Collaborative Pattern** (Chapter 10)
```python
class CollaborativeAgent:
    """Peer collaboration with iterative refinement."""

    def __init__(self, agents: list[Agent], max_rounds: int = 3):
        self.agents = agents
        self.max_rounds = max_rounds

    async def call(self, messages: list[Message], **kwargs) -> Message:
        current = messages
        for round in range(self.max_rounds):
            results = []
            for agent in self.agents:
                result = await agent.call(current, **kwargs)
                results.append(result)

            if self.has_consensus(results):
                return self.merge(results)

            current = self.prepare_next_round(results)

        return self.merge(results)
```

**6. Human-in-Loop Pattern** (Chapter 11)
```python
class HumanInLoopAgent:
    """Agent with human approval for high-stakes decisions."""

    def __init__(self, agent: Agent, approval_threshold: float = 0.8):
        self.agent = agent
        self.threshold = approval_threshold

    async def call(self, messages: list[Message], **kwargs) -> Message:
        # Get proposal
        proposal = await self.agent.call(messages, **kwargs)

        # Check if approval needed
        if proposal.confidence < self.threshold:
            approved = await self.request_approval(proposal)
            if not approved:
                return Message(
                    role="agent",
                    content="Action rejected by human reviewer"
                )

        return proposal
```

**7. Fallback Pattern** (bonus - from guide examples)
```python
class FallbackAgent:
    """Try agents in sequence until one succeeds."""

    def __init__(self, agents: list[Agent]):
        self.agents = agents

    async def call(self, messages: list[Message], **kwargs) -> Message:
        for agent in self.agents:
            try:
                return await agent.call(messages, **kwargs)
            except Exception as e:
                logger.warning(f"Agent {agent} failed: {e}, trying next")
                continue
        raise Exception("All agents failed")
```

### Go Implementations

Implement equivalent patterns in Go:
- `agenkit-go/patterns/sequential.go`
- `agenkit-go/patterns/parallel.go`
- `agenkit-go/patterns/supervisor.go`
- `agenkit-go/patterns/router.go`
- `agenkit-go/patterns/collaborative.go`
- `agenkit-go/patterns/human_in_loop.go`
- `agenkit-go/patterns/fallback.go`

## Use Cases

These patterns enable:
1. **Document processing pipelines** (Sequential)
2. **Multi-model ensembles** (Parallel)
3. **Software development agents** (Supervisor)
4. **Customer service routing** (Router)
5. **Code review systems** (Collaborative)
6. **Financial trading** (Human-in-Loop)
7. **High availability systems** (Fallback)

## Implementation Considerations

**Scope:**
- [x] Python implementation
- [ ] Go implementation
- [ ] Cross-language compatibility tested
- [ ] Backward compatible

**Affected Components:**
- [x] Core patterns module
- [ ] Documentation (guide already exists)
- [ ] Examples

**Complexity Estimate:**
- [ ] Small (< 1 day)
- [ ] Medium (1-3 days)
- [x] Large (> 3 days) - 7 patterns × 2 languages + tests + examples

## Acceptance Criteria

- [ ] All 7 patterns implemented in Python (`agenkit/patterns/`)
- [ ] All 7 patterns implemented in Go (`agenkit-go/patterns/`)
- [ ] Unit tests for each pattern (both languages)
- [ ] Integration tests for cross-language usage
- [ ] Examples for each pattern (`examples/patterns/`)
- [ ] Documentation in guide references implementations
- [ ] API documentation added (`docs-site/api/patterns.md`)
- [ ] Code coverage > 90%

## Related

- Complements Agent Patterns Guide (#61)
- Uses Task pattern (#60)
- Can integrate with LLM adapters (#58, #59, #62, #63)

## Priority

**High** - These are the core abstractions users need to build complex agent systems

## Labels

`enhancement`, `patterns`, `python`, `go`, `good-first-issue` (individual patterns), `help-wanted`
