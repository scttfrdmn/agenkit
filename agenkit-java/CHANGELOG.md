# Changelog

## [0.72.0] - 2026-03-17

### Added
- Initial Java implementation of agenkit
- **Core**: `Message`, `Agent`, `StreamingAgent`, `Tool`, `ToolResult`, `IntrospectionResult`
- **15 Patterns**: ConversationalAgent, ReActAgent, PlanningAgent, ReflectionAgent, RouterAgent,
  SupervisorAgent, CollaborativeAgent, HumanInLoopAgent, FallbackAgent, AutonomousAgent,
  OrchestrationAgent, MultiAgentOrchestrator, ReasoningWithToolsAgent, MemoryAugmentedAgent, TaskAgent
- **3 Composition**: SequentialAgent, ParallelAgent, ConditionalAgent
- **8 Middleware**: Retry, Timeout, CircuitBreaker, Caching, RateLimiter, PerUserRateLimiter,
  Metrics, Batching — plus fluent `AgentBuilder`
- **Memory**: EphemeralMemory, MemoryHierarchy (3-tier), VectorMemory
- **Adapters**: `LlmClient`, OpenAiAdapter, AnthropicAdapter, MockAdapter
- **Safety**: InputValidator, OutputValidator, PermissionChecker, AnomalyDetector, AuditLogger
- **Observability**: TracingAgent, MetricsCollector
- **Budget**: ModelPricing, CostTracker, BudgetLimiter
- **Evaluation**: Metric, Evaluator, Benchmark
- **Checkpointing**: CheckpointManager, DurableAgent
- **4 Examples**: basic, react-agent, middleware, streaming
- Maven artifact: `io.agenkit:agenkit:0.72.0`
- Target: Java 17 LTS (compatible with Java 21 LTS)
