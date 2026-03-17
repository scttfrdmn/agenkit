# agenkit-java

Java implementation of [agenkit](https://github.com/agenkit/agenkit) — a minimal, composable toolkit for building AI agents.

## Requirements

- Java 17+ (compatible with Java 21 LTS)
- Maven 3.8+

## Quick Start

```bash
cd agenkit-java
mvn test        # run all 200+ tests
mvn package     # build the jar
```

## Installation

```xml
<dependency>
  <groupId>io.agenkit</groupId>
  <artifactId>agenkit</artifactId>
  <version>0.72.0</version>
</dependency>
```

## Usage

```java
import io.agenkit.adapters.OpenAiAdapter;
import io.agenkit.core.Message;
import io.agenkit.patterns.ConversationalAgent;

var llm = new OpenAiAdapter(System.getenv("OPENAI_API_KEY"), "gpt-4o-mini");
var agent = new ConversationalAgent("assistant", llm);

Message response = agent.process(Message.of("user", "Hello!")).get();
System.out.println(response.contentString());
```

## Features

### 18 Agent Patterns

| Pattern | Description |
|---------|-------------|
| `ConversationalAgent` | Maintains conversation history |
| `ReActAgent` | Reasoning + tool use (ReAct framework) |
| `PlanningAgent` | Creates and executes multi-step plans |
| `ReflectionAgent` | Self-critique and iterative refinement |
| `RouterAgent` | Classifies and routes to sub-agents |
| `SupervisorAgent` | Hierarchical task decomposition |
| `CollaborativeAgent` | Peer consensus via synthesis |
| `HumanInLoopAgent` | Human approval gates |
| `FallbackAgent` | Sequential fallback chain |
| `AutonomousAgent` | Goal-driven autonomous loops |
| `OrchestrationAgent` | Sequential / parallel / router orchestration |
| `MultiAgentOrchestrator` | Multi-agent coordination |
| `ReasoningWithToolsAgent` | Chain-of-thought with tools |
| `MemoryAugmentedAgent` | Pluggable memory integration |
| `TaskAgent` | One-shot lifecycle management |
| `SequentialAgent` | Pipeline composition |
| `ParallelAgent` | Fan-out composition |
| `ConditionalAgent` | Predicate-based routing |

### 8 Middleware (Decorator Pattern)

```java
Agent agent = AgentBuilder.wrap(new MyAgent())
    .withRetry(3)
    .withTimeout(Duration.ofSeconds(30))
    .withCircuitBreaker()
    .withCaching()
    .withRateLimit(100)
    .withMetrics()
    .build();
```

### Memory Systems

- `EphemeralMemory` — in-memory, session-scoped
- `MemoryHierarchy` — 3-tier (working / episodic / semantic)
- `VectorMemory` — keyword-similarity retrieval

### LLM Adapters

- `OpenAiAdapter` — OpenAI Chat Completions API
- `AnthropicAdapter` — Anthropic Messages API
- `MockAdapter` — Testing and development

## Examples

```bash
# Basic conversational agent
cd examples/basic && mvn exec:java

# ReAct agent with tools
cd examples/react-agent && mvn exec:java

# Middleware composition
cd examples/middleware && mvn exec:java

# Streaming
cd examples/streaming && mvn exec:java
```

## Architecture

```
io.agenkit
├── core/          # Agent, StreamingAgent, Tool, Message, ToolResult, IntrospectionResult
├── patterns/      # 15 agent patterns
├── composition/   # SequentialAgent, ParallelAgent, ConditionalAgent
├── middleware/    # 8 middleware + AgentBuilder
├── memory/        # Memory interface + 3 implementations
├── adapters/      # LlmClient + OpenAI/Anthropic/Mock adapters
├── safety/        # InputValidator, OutputValidator, PermissionChecker, AuditLogger
├── observability/ # TracingAgent, MetricsCollector
├── budget/        # ModelPricing, CostTracker, BudgetLimiter
├── evaluation/    # Metric, Evaluator, Benchmark
└── checkpointing/ # CheckpointManager, DurableAgent
```
