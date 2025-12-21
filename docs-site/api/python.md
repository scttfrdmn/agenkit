# Python API Reference

Complete API documentation for Agenkit Python implementation.

## Core Interfaces

The foundation of Agenkit - minimal, perfect primitives for agent communication.

### Agent

::: agenkit.interfaces.Agent
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      show_signature_annotations: true

### Message

::: agenkit.interfaces.Message
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Tool

::: agenkit.interfaces.Tool
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### ToolResult

::: agenkit.interfaces.ToolResult
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### IntrospectionResult

::: agenkit.interfaces.IntrospectionResult
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Composition Patterns

Basic composition primitives for connecting agents.

### SequentialAgent

::: agenkit.composition.SequentialAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### ParallelAgent

::: agenkit.composition.ParallelAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### ConditionalAgent

::: agenkit.composition.ConditionalAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### FallbackAgent

::: agenkit.composition.FallbackAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Agent Patterns

Advanced agent patterns for specialized behaviors.

### Conversational

::: agenkit.patterns.ConversationalAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### ReAct

::: agenkit.patterns.ReActAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Reflection

::: agenkit.patterns.ReflectionAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Orchestration

::: agenkit.patterns.OrchestrationAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Agents-as-Tools

::: agenkit.patterns.AgentsAsToolsAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Planning

::: agenkit.patterns.PlanningAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Autonomous

::: agenkit.patterns.AutonomousAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Multiagent

::: agenkit.patterns.MultiagentAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Router

::: agenkit.patterns.RouterAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Task

::: agenkit.patterns.Task
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Memory Hierarchy

::: agenkit.patterns.MemoryHierarchyAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Reasoning with Tools

::: agenkit.patterns.ReasoningWithToolsAgent
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Reasoning Techniques

Advanced reasoning patterns for complex problem-solving.

### Chain-of-Thought

::: agenkit.techniques.reasoning.ChainOfThought
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Tree-of-Thought

::: agenkit.techniques.reasoning.TreeOfThought
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Graph-of-Thought

::: agenkit.techniques.reasoning.GraphOfThought
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Self-Consistency

::: agenkit.techniques.reasoning.SelfConsistency
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Reasoning Tree

::: agenkit.techniques.reasoning.ReasoningTree
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Middleware

Production-grade middleware for resilience and observability.

### Retry

::: agenkit.middleware.RetryMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Circuit Breaker

::: agenkit.middleware.CircuitBreakerMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Timeout

::: agenkit.middleware.TimeoutMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Rate Limiter

::: agenkit.middleware.RateLimiterMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Caching

::: agenkit.middleware.CachingMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Batching

::: agenkit.middleware.BatchingMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Metrics

::: agenkit.middleware.MetricsMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## LLM Adapters

Adapters for connecting to various LLM providers.

### Anthropic

::: agenkit.adapters.AnthropicAdapter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### OpenAI

::: agenkit.adapters.OpenAIAdapter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Bedrock

::: agenkit.adapters.BedrockAdapter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Gemini

::: agenkit.adapters.GeminiAdapter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Base Adapter

::: agenkit.adapters.llm.LLMAdapter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Memory

Memory management for stateful agents.

### Memory Hierarchy

::: agenkit.memory.MemoryHierarchy
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Working Memory

::: agenkit.memory.WorkingMemory
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Episodic Memory

::: agenkit.memory.EpisodicMemory
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Semantic Memory

::: agenkit.memory.SemanticMemory
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Memory Strategies

::: agenkit.memory.strategies
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## Observability

Tracing and metrics for production monitoring.

### Tracing

::: agenkit.observability.TracingMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Metrics

::: agenkit.observability.MetricsCollector
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Logging

::: agenkit.observability.setup_logging
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Evaluation

Testing and optimization tools for agent development.

### Recorder

::: agenkit.evaluation.Recorder
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Benchmark Runner

::: agenkit.evaluation.BenchmarkRunner
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Metrics

::: agenkit.evaluation.Metrics
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Bayesian Optimizer

::: agenkit.evaluation.BayesianOptimizer
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Prompt Optimizer

::: agenkit.evaluation.PromptOptimizer
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Tools

Built-in tools and utilities for agents.

### Base Tool

::: agenkit.tools.BaseTool
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Tool Registry

::: agenkit.tools.ToolRegistry
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Routing

Intelligent routing for multi-agent systems.

### Router

::: agenkit.routing.Router
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Routing Strategies

::: agenkit.routing.RoutingStrategy
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Safety

Safety guardrails and content filtering.

### Content Filter

::: agenkit.safety.ContentFilter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Safety Middleware

::: agenkit.safety.SafetyMiddleware
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Budget

Token and cost management for LLM calls.

### Budget Limiter

::: agenkit.budget.BudgetLimiter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Token Counter

::: agenkit.budget.TokenCounter
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Checkpointing

State persistence for long-running agents.

### Checkpoint Manager

::: agenkit.checkpointing.CheckpointManager
    options:
      show_root_heading: true
      show_source: true
      members_order: source

---

## Protocols

Integration protocols for agent communication.

### MCP (Model Context Protocol)

::: agenkit.techniques.protocols.mcp
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### A2A (Agent-to-Agent)

::: agenkit.techniques.protocols.a2a
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## Utilities

Helper functions and utilities.

### Introspection Helpers

```python
from agenkit import default_introspection_result

# Get default introspection for an agent
result = default_introspection_result(agent)
```

---

## Type Hints

Agenkit is fully typed. Import types from `agenkit.interfaces`:

```python
from agenkit.interfaces import (
    Agent,
    Message,
    Tool,
    ToolResult,
    IntrospectionResult
)
```

---

## Version Information

```python
import agenkit

print(agenkit.__version__)  # Current version
```

---

## See Also

- **[Core Concepts](../core-concepts/index.md)**: Understand Agenkit architecture
- **[Patterns](guides/agent-patterns.md)**: Learn about agent patterns
- **[Examples](../examples/index.md)**: See complete examples
- **[Go API Reference](go.md)**: Go implementation API docs
- **[Migration Guides](../../docs/migrations/)**: Migrate from other frameworks
