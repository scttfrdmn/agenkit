# Agenkit — C#/.NET

Minimal, composable interfaces for AI agents — C#/.NET 10 LTS.

## Quick Start

```csharp
using Agenkit.Adapters;
using Agenkit.Core;
using Agenkit.Patterns;

var llm = new AnthropicAdapter(Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY")!);
var agent = new ConversationalAgent(new ConversationalAgentConfig(llm, MaxHistory: 10));

var response = await agent.ProcessAsync(Message.NewMessage("user", "Hello!"));
Console.WriteLine(response.ContentString());
```

## Patterns

| Pattern | Description |
|---------|-------------|
| `ConversationalAgent` | Multi-turn chat with history window |
| `ReActAgent` | Reasoning + Acting with tool use |
| `PlanningAgent` | Plan/execute for complex tasks |
| `ReflectionAgent` | Self-critique + iterative refinement |
| `RouterAgent` | Classify + route to sub-agents |
| `SupervisorAgent` | Hierarchical task decomposition |
| `CollaborativeAgent` | Multi-peer consensus |
| `HumanInLoopAgent` | Human approval gates |
| `FallbackAgent` | Sequential retry with fallback chain |
| `AutonomousAgent` | Goal-driven iteration loops |
| `OrchestrationAgent` | Sequential / parallel / router modes |
| `MultiAgentOrchestrator` | Named-agent coordination |
| `ReasoningWithToolsAgent` | Interleaved reasoning + tool calls |
| `MemoryAugmentedAgent` | Persistent memory integration |
| `TaskAgent` | One-shot lifecycle with state tracking |

## Middleware (fluent)

```csharp
var agent = new MyAgent()
    .WithRetry(new RetryConfig(MaxAttempts: 3))
    .WithTimeout(TimeSpan.FromSeconds(30))
    .WithCircuitBreaker()
    .WithCaching()
    .WithMetrics();
```

## Memory

```csharp
var memory = new MemoryHierarchy(workingCapacity: 5, shortTermCapacity: 20);
// or
var memory = new VectorMemory(maxMessages: 500);
```

## Adapters

```csharp
var openai    = new OpenAiAdapter(apiKey, model: "gpt-4o");
var anthropic = new AnthropicAdapter(apiKey, model: "claude-3-5-sonnet-20241022");
var mock      = new MockAdapter("deterministic response"); // for tests
```

## Testing

```bash
dotnet test
```

## Version

See [`src/Agenkit/Agenkit.csproj`](src/Agenkit/Agenkit.csproj) for the current version
(previously hardcoded here as v0.71.0, which drifted 18 releases stale — see #874).
Full parity with Python, Go, TypeScript, Rust, C++, and Zig implementations.
