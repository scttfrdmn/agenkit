# Changelog — Agenkit C#/.NET

## [0.71.0] — 2026-03-16

### Added
- Initial C#/.NET 10 implementation with full parity to all other language implementations
- 15 agent patterns: ConversationalAgent, ReActAgent, PlanningAgent, ReflectionAgent, RouterAgent, SupervisorAgent, CollaborativeAgent, HumanInLoopAgent, FallbackAgent, AutonomousAgent, OrchestrationAgent, MultiAgentOrchestrator, ReasoningWithToolsAgent, MemoryAugmentedAgent, TaskAgent
- 9 middleware components: Retry, Timeout, CircuitBreaker, Caching, RateLimiter, PerUserRateLimiter, Metrics, Batching — plus fluent `AgentExtensions`
- 3 composition primitives: SequentialAgent, ParallelAgent, ConditionalAgent
- 3 memory backends: EphemeralMemory, MemoryHierarchy (3-tier), VectorMemory (cosine similarity)
- 3 memory strategies: SlidingWindow, ImportanceWeighting, Summarization
- 2 LLM adapters: OpenAiAdapter, AnthropicAdapter (HttpClient-only, no SDK dependency)
- Safety: InputValidator, OutputValidator, PermissionChecker, AnomalyDetector, AuditLogger
- Observability: TracingAgent (OpenTelemetry ActivitySource), MetricsCollector
- Budget: ModelPricing, CostTracker, BudgetLimiter
- Evaluation: Metric, Evaluator, Benchmark
- Checkpointing: CheckpointManager (JSON), DurableAgent
- 241 xUnit tests, 0 failures
- 4 example programs (basic, react-agent, middleware, streaming)
