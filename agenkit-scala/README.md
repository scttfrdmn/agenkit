# agenkit-scala

Scala 3 implementation of [agenkit](https://github.com/scttfrdmn/agenkit) — a minimal,
composable toolkit for building AI agents.

## Requirements

- Scala 3.4.2
- sbt 1.9.8+
- JDK 17+

## Installation

Add to `build.sbt`:

```scala
libraryDependencies += "io.agenkit" %% "agenkit-scala" % "0.89.0"
```

The artifact coordinates are `io.agenkit:agenkit-scala_3` (organization `io.agenkit`,
artifact name `agenkit-scala`, Scala 3 binary suffix `_3`).

## Building From Source

```bash
cd agenkit-scala
sbt test        # run the test suite (363+ tests: ScalaTest + ScalaCheck property tests)
sbt package     # build the jar
```

## Quick Start

```scala
import io.agenkit.adapters.MockAdapter
import io.agenkit.core.Message
import io.agenkit.patterns.ConversationalAgent
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

val llm   = MockAdapter("I'm a helpful assistant!")
val agent = ConversationalAgent("assistant", llm, systemPrompt = Some("You are a helpful assistant."))

val response = Await.result(agent.process(Message.user("Hello!")), 10.seconds)
println(response.contentString)
```

Swap `MockAdapter` for `OpenAiAdapter(apiKey)` or `AnthropicAdapter(apiKey)` to talk to a
real model.

## Core Concepts

Every agent implements the `Agent` trait:

```scala
trait Agent:
  def name: String
  def capabilities: List[String]
  def process(message: Message)(using ExecutionContext): Future[Message]
  def introspect(): IntrospectionResult
```

`Message` is an immutable case class (`role`, `content: Option[String]`, `metadata`,
`timestamp`), and `process` is asynchronous — it returns a `Future[Message]` and needs an
`ExecutionContext` in scope (`scala.concurrent.ExecutionContext.Implicits.global` works
for examples and tests).

## Features

### Agent Patterns (`io.agenkit.patterns`)

`ConversationalAgent`, `ReActAgent`, `PlanningAgent`, `ReflectionAgent`, `RouterAgent`,
`SupervisorAgent`, `CollaborativeAgent`, `HumanInLoopAgent`, `FallbackAgent`,
`AutonomousAgent`, `OrchestrationAgent`, `MultiAgentOrchestrator`,
`ReasoningWithToolsAgent`, `MemoryAugmentedAgent`, `TaskAgent`.

### Composition (`io.agenkit.composition`)

`SequentialAgent`, `ParallelAgent`, `ConditionalAgent`.

### Middleware (`io.agenkit.middleware`)

Applied via fluent extension methods on any `Agent`:

```scala
import io.agenkit.middleware.*

val resilient = myAgent
  .withRetry(maxAttempts = 3)
  .withTimeout(30.seconds)
  .withCircuitBreaker(threshold = 5)
  .withMetrics("demo")
```

`RetryMiddleware`, `TimeoutMiddleware`, `CircuitBreakerMiddleware`, `CachingMiddleware`,
`RateLimiterMiddleware`, `PerUserRateLimiterMiddleware`, `BatchingMiddleware`,
`MetricsMiddleware`.

### Memory (`io.agenkit.memory`)

`EphemeralMemory`, `MemoryHierarchy` (composes multiple `Memory` layers), `VectorMemory`,
plus retention strategies (`SlidingWindowStrategy`, `ImportanceWeightingStrategy`,
`SummarizationStrategy`).

### LLM Adapters (`io.agenkit.adapters`)

`OpenAiAdapter` (OpenAI Chat Completions API, also works against
OpenAI-compatible endpoints via `baseUrl`), `AnthropicAdapter` (Anthropic Messages API),
`MockAdapter` (deterministic responses for tests and examples).

### Safety (`io.agenkit.safety`)

`InputValidator`, `OutputValidator`, `PermissionChecker`, `AnomalyDetector`,
`AuditLogger`.

### Observability (`io.agenkit.observability`)

`TracingAgent`, `MetricsCollector`.

### Budget (`io.agenkit.budget`)

`ModelPricing`, `CostTracker`, `BudgetLimiter`.

### Evaluation (`io.agenkit.evaluation`)

`Metric`, `Evaluator`, `Benchmark`.

### Checkpointing (`io.agenkit.checkpointing`)

`CheckpointManager` (thread-safe in-memory checkpoint store keyed by checkpoint id) and
`DurableAgent` (wraps an agent, snapshotting message history to the manager every
`checkpointInterval` messages — default `10`).

### MCP (`io.agenkit.protocols.mcp`)

`McpClient` trait with `HttpClient` and `StdioClient` implementations, plus
`McpServer` and `McpToolAdapter`.

### Agent Skills (`io.agenkit.skills`)

`AgentSkill`, `SkillRegistry`, `SkillEnabledAgent`.

## Examples

[`examples/`](examples/) contains four reference programs — read them for usage
patterns, mirroring the snippets above:

- [`examples/basic`](examples/basic/src/main/scala/io/agenkit/examples/BasicExample.scala) — `ConversationalAgent` with a mock LLM
- [`examples/react-agent`](examples/react-agent/src/main/scala/io/agenkit/examples/ReactAgentExample.scala) — `ReActAgent` using a mock tool
- [`examples/middleware`](examples/middleware/src/main/scala/io/agenkit/examples/MiddlewareExample.scala) — middleware composition via extension methods
- [`examples/streaming`](examples/streaming/src/main/scala/io/agenkit/examples/StreamingExample.scala) — `StreamingAgent`

> **Note:** unlike `agenkit-java`'s `examples/*` (each with its own `pom.xml`), these
> directories are not currently wired into `build.sbt` as runnable subprojects, so
> `sbt run` cannot execute them yet. Treat them as reference source, not `sbt run`
> targets, until that's fixed.

## Architecture

```
io.agenkit
├── core/          # Agent, Message, StreamingAgent, Tool, ToolResult, IntrospectionResult
├── patterns/      # 15 agent patterns
├── composition/   # SequentialAgent, ParallelAgent, ConditionalAgent
├── middleware/    # 8 middleware, applied via extension methods (AgentOps)
├── memory/        # Memory trait + 3 implementations + retention strategies
├── adapters/      # LlmClient + OpenAI/Anthropic/Mock adapters
├── safety/        # InputValidator, OutputValidator, PermissionChecker, AuditLogger, AnomalyDetector
├── observability/ # TracingAgent, MetricsCollector
├── budget/        # ModelPricing, CostTracker, BudgetLimiter
├── evaluation/    # Metric, Evaluator, Benchmark
├── checkpointing/ # CheckpointManager, DurableAgent
├── protocols/mcp/ # McpClient (HTTP + stdio), McpServer, McpToolAdapter
└── skills/        # AgentSkill, SkillRegistry, SkillEnabledAgent
```

## Testing

```bash
sbt test
```

Uses ScalaTest with `scalacheck-1-17` for property-based tests.

## Cross-Language Parity

agenkit-scala maintains behavioral parity with the other eight agenkit implementations
(Python, Go, TypeScript, Rust, C++, Zig, C#, Java). See the root
[docs/DEFAULTS.md](../docs/DEFAULTS.md) and [docs/CHECKPOINTING.md](../docs/CHECKPOINTING.md)
for cross-language default-value and checkpointing comparisons.

## License

MIT License — see the repository [LICENSE](../LICENSE) file.
