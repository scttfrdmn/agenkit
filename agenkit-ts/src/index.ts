/**
 * Agenkit TypeScript - Minimal, composable interfaces for AI agents.
 *
 * @packageDocumentation
 */

// Core interfaces
export {
  Agent,
  Message,
  Tool,
  ToolResult,
  createMessage,
  validateMessage,
} from './core/interfaces';

// Introspection
export {
  IntrospectionResult,
  createDefaultIntrospectionResult,
  validateIntrospectionResult,
} from './core/introspection';

// Adapters
export {
  LocalAgent,
  ProcessFunction,
  ProcessStreamFunction,
  LocalAgentConfig,
  createEchoAgent,
  createCounterAgent,
} from './adapters/local';

// Transports
export { HTTPAgent, HttpTransportConfig, HttpTransportError } from './transports/http';
export {
  WebSocketAgent,
  WebSocketTransportConfig,
  WebSocketTransportError,
} from './transports/websocket';
export {
  GrpcAgent,
  GrpcServer,
  GrpcTransportConfig,
  GrpcServerConfig,
  GrpcTransportError,
} from './transports/grpc';
export { TCPTransport } from './transports/tcp';
export { RemoteAgent, RemoteAgentConfig } from './transports/remote';
export {
  Transport,
  parseEndpoint,
  MAX_MESSAGE_SIZE,
  ProtocolError,
  ProtocolErrorCode,
  ConnectionError,
  ConnectionTimeoutError,
  ConnectionClosedError,
  InvalidMessageError,
  UnsupportedVersionError,
  MalformedPayloadError,
  AgentNotFoundError,
  AgentUnavailableError,
  AgentTimeoutError,
  ToolNotFoundError,
  ToolExecutionFailedError,
  RegistrationFailedError,
  DuplicateAgentError,
  RemoteExecutionError,
  PROTOCOL_VERSION,
  ProtocolEnvelope,
  encodeMessage,
  decodeMessage,
  encodeToolResult,
  decodeToolResult,
  createRequestEnvelope,
  createResponseEnvelope,
  createErrorEnvelope,
  createStreamChunkEnvelope,
  createStreamEndEnvelope,
  validateEnvelope,
  encodeBytes,
  decodeBytes,
} from './transports';

// Middleware
export { Middleware, applyMiddleware, BaseMiddleware } from './middleware/base';
export { RetryMiddleware, RetryConfig, RetryMetrics, retry } from './middleware/retry';
export { TimeoutMiddleware, TimeoutConfig, TimeoutError, TimeoutMetrics, timeout } from './middleware/timeout';
export {
  CircuitBreakerMiddleware,
  CircuitBreakerConfig,
  CircuitState,
  CircuitBreakerError,
  CircuitBreakerMetrics,
  circuitBreaker,
} from './middleware/circuit-breaker';
export { BatchingDecorator, BatchingConfig, BatchingMetrics } from './middleware/batching';
export { CachingDecorator, CachingConfig, CachingMetrics } from './middleware/caching';
export { MetricsDecorator, Metrics } from './middleware/metrics';
export {
  RateLimiterDecorator,
  RateLimiterConfig,
  RateLimiterMetrics,
  RateLimitError,
} from './middleware/rate-limiter';
export {
  PerUserRateLimiterDecorator,
  PerUserRateLimiterConfig,
  PerUserRateLimiterMetrics,
  PerUserRateLimitError,
  GlobalRateLimitError,
} from './middleware/per-user-rate-limiter';

// LLM Adapters
export { OpenAIAgent, OpenAIConfig } from './llm/openai';
export { AnthropicAgent, AnthropicConfig } from './llm/anthropic';
export { OpenAICompatibleAgent, OpenAICompatibleConfig } from './llm/openai-compatible';
export { usageFromMessage } from './llm/usage';
export type { Usage, UsageReporter } from './llm/usage';

// Composition Patterns
export { SequentialAgent } from './composition/sequential';
export { ParallelAgent, type AgentResult } from './composition/parallel';
export {
  ConditionalAgent,
  type Condition,
  type ConditionalRoute,
  contentContains,
  roleEquals,
  metadataHasKey,
  metadataEquals,
  andConditions,
  orConditions,
  notCondition,
} from './composition/conditional';
export { FallbackAgent } from './composition/fallback';

// Patterns
export {
  ReflectionAgent,
  ReflectionConfig,
  ReflectionStep,
  StopReason,
  CritiqueFormat,
} from './patterns/reflection';
export {
  AgentTool,
  AgentToolConfig,
  OutputFormat,
  createAgentTool,
  createAgentToolSimple,
} from './patterns/agents-as-tools';
export {
  SequentialPattern,
  ParallelPattern,
  RouterPattern,
  AgentHook,
  Aggregator,
  Router,
} from './patterns/orchestration';
export {
  ReActAgent,
  ReActConfig,
  ReActStep,
  ReActStopReason,
  createReActAgent,
} from './patterns/react';
export {
  ConversationalAgent,
  ConversationalAgentConfig,
  LLMClient,
  createConversationalAgent,
} from './patterns/conversational';
export { Task, TaskConfig, TimeoutError as TaskTimeoutError, executeTask } from './patterns/task';
export {
  MultiAgentOrchestrator,
  ConsensusAgent,
  AgentTask,
  TaskStatus,
  OrchestrationStrategy,
  VotingStrategy,
} from './patterns/multiagent';
export {
  PlanningAgent,
  Plan,
  PlanStep,
  StepStatus,
  LLMClient as PlanningLLMClient,
  StepExecutor,
  DefaultStepExecutor,
  PlanningAgentConfig,
  createPlan,
  createPlanStep,
  getNextSteps,
  isPlanComplete,
  hasPlanFailures,
  getPlanProgress,
  canExecuteStep,
} from './patterns/planning';

// Evaluation
export {
  ABTest,
  ABVariant,
  ABTestResult,
  TestCase as ABTestCase,
  ABTestConfig,
  RunOptions,
  SignificanceLevel,
} from './evaluation/ab-testing';
export {
  Benchmark,
  TestCase,
  SimpleQABenchmark,
  ReasoningBenchmark,
  NeedleInHaystackBenchmark,
  NeedleInHaystackConfig,
  CodeGenerationBenchmark,
  BenchmarkResult,
  TestCaseResult,
  getAllBenchmarks,
  getBenchmarkByName,
  runBenchmark,
} from './evaluation/benchmarks';
export {
  Metric,
  AccuracyMetric,
  AccuracyMetricConfig,
  QualityMetrics,
  QualityMetricsConfig,
  QualityWeights,
  LatencyMetric,
  Validator,
  EvaluationResult as QualityEvaluationResult,
  evaluateAgent as evaluateAgentQuality,
} from './evaluation/quality-metrics';
export {
  Evaluator,
  EvaluationResult,
  TestCase as CoreTestCase,
  getSuccessRate,
  resultToDict,
  evaluateAgent,
} from './evaluation/core';
export {
  ContextMetrics,
  CompressionMetrics,
  AgentWithContextStats,
  CompressionStats,
  createCompressionStats,
  compressionStatsToDict,
} from './evaluation/context-metrics';
export {
  ErrorTracker,
  StepResult,
  RecordStepOptions,
} from './evaluation/error-tracker';
export {
  SessionRecorder,
  SessionReplay,
  RecordingStorage,
  FileRecordingStorage,
  InMemoryRecordingStorage,
  SessionRecording,
  InteractionRecord,
  MessageDict,
  ReplayResults,
  ReplayInteraction,
  ReplayComparison,
  OutputDifference,
  getSessionDuration,
  getTotalLatency,
  sessionRecordingToDict,
  sessionRecordingFromDict,
  interactionRecordToDict,
  interactionRecordFromDict,
} from './evaluation/recorder';
export {
  RegressionDetector,
  RegressionDetectorConfig,
  Regression,
  Severity,
  MetricComparison,
  TrendStats,
  isRegression,
  regressionToDict,
} from './evaluation/regression';
export {
  SearchSpace,
  Optimizer,
  RandomSearchOptimizer,
  OptimizationResult,
  ParameterType,
  ParameterSpec,
  AgentFactory,
  ObjectiveFunction,
  getOptimizationDuration,
  getOptimizationImprovement,
  optimizationResultToDict,
} from './evaluation/optimizer';
export {
  BayesianOptimizer,
  BayesianOptimizerConfig,
  AcquisitionFunction,
} from './evaluation/bayesian-optimizer';
export {
  PromptOptimizer,
  PromptOptimizerConfig,
  PromptOptimizationResult,
  PromptEvaluation,
  PromptAgentFactory,
  OptimizationStrategy,
  GeneticConfig,
  getPromptOptimizationDuration,
  promptOptimizationResultToDict,
} from './evaluation/prompt-optimizer';
export {
  SessionResult,
  MetricsCollector,
  SessionStatus,
  MetricType,
  MetricMeasurement,
  ErrorRecord,
  AggregatedMetric,
  createMetricMeasurement,
  createErrorRecord,
} from './evaluation/metrics';
export {
  MemoryEntry,
  MemoryStore,
  WorkingMemory,
  ShortTermMemory,
  LongTermMemory,
  MemoryHierarchy,
  createMemoryEntry,
} from './patterns/memory';
export {
  AutonomousAgent,
  Goal,
  GoalStatus,
  AutonomousResult,
  StopCondition,
  createGoal,
} from './patterns/autonomous';
export {
  ReasoningWithToolsAgent,
  ReasoningStepType,
  ReasoningStep,
  ReasoningTrace,
  ReasoningWithToolsConfig,
  createReasoningStep,
  createReasoningTrace,
  addStepToTrace,
  finalizeTrace,
  getTraceDuration,
  traceToDict,
} from './patterns/reasoning-with-tools';

// Reasoning Techniques
export {
  SelfConsistencyAgent,
  SelfConsistencyConfig,
  VotingStrategy as SelfConsistencyVotingStrategy,
  AnswerExtractor,
  createSelfConsistencyAgent,
} from './techniques/reasoning/self-consistency';
export {
  ChainOfThought,
  ChainOfThoughtConfig,
  createChainOfThought,
} from './techniques/reasoning/chain-of-thought';
export {
  TreeOfThought,
  TreeOfThoughtConfig,
  SearchStrategy as TreeOfThoughtSearchStrategy,
  EvaluatorFunction,
  createTreeOfThought,
} from './techniques/reasoning/tree-of-thought';
export {
  ReasoningTree,
  ReasoningNode,
  NodeState,
  TreeStatistics,
} from './techniques/reasoning/reasoning-tree';
export {
  LeastToMost,
  LeastToMostConfig,
  Subproblem,
  DecomposerFunction,
} from './techniques/reasoning/least-to-most';
export {
  GraphOfThought,
  GraphOfThoughtConfig,
  AggregatorType,
} from './techniques/reasoning/graph-of-thought';
export {
  ReasoningGraph,
  ThoughtNode,
  LogicalEdge,
  NodeType,
  EdgeType,
  GraphStatistics,
} from './techniques/reasoning/reasoning-graph';
export {
  PlanAndSolve,
  PlanAndSolveConfig,
  Plan as PaSPlan,
  PlanStep as PaSPlanStep,
  PlannerFunc as PaSPlannerFunc,
  SolverFunc as PaSSolverFunc,
} from './techniques/reasoning/plan-and-solve';

// Observability
export {
  TracingConfig,
  TraceContext,
  initTracing,
  shutdownTracing,
  getTracer,
  injectTraceContext,
  extractTraceContext,
  TracingMiddleware,
  createTracedAgent,
  MetricsConfig,
  initMetrics,
  shutdownMetrics,
  getMetricsUrl,
  MetricsMiddleware,
  createMonitoredAgent,
  LogLevel,
  LoggingConfig,
  LogEntry,
  Logger,
  configureLogging,
  getLoggingConfig,
  getLoggerWithTrace,
} from './observability';

// Safety and Security
export {
  AuditEventType,
  AuditSeverity,
  AuditEvent,
  SecurityAuditLoggerConfig,
  SecurityAuditLogger,
  getAuditLogger,
  configureAuditLogger,
  SecurityEvent,
  AnomalyDetector,
  AnomalyDetectionMiddleware,
  anomalyDetection,
  ValidationError,
  PromptInjectionDetector,
  ContentFilter,
  InputValidationMiddleware,
  inputValidation,
  OutputValidationError,
  SchemaValidator,
  SensitiveDataRedactor,
  OutputValidationMiddleware,
  outputValidation,
  Permission,
  Role,
  ROLE_PERMISSIONS,
  PermissionDeniedError,
  Sandbox,
  PermissionMiddleware,
  permissions,
} from './safety';

// Memory Systems
export { Memory, InMemoryMemory } from './memory';

// Budget Management
export { ModelPricing, Cost, costToDict, Storage, InMemoryStorage, CostTracker } from './budget';

// Infrastructure
export {
  LoadBalancer,
  LoadBalancingStrategy,
  LoadBalancerConfig,
  LoadBalancerMetrics,
  AgentBackend,
  BackendStats,
  defaultLoadBalancerConfig,
  HealthChecker,
  HealthStatus,
  ProbeType,
  HealthCheckResult,
  HealthCheckConfig,
  HealthMetrics,
  defaultHealthCheckConfig,
  EnhancedRetryDecorator,
  JitterType,
  ErrorClass,
  ErrorStrategy,
  RetryBudget,
  EnhancedRetryConfig,
  EnhancedRetryMetrics,
  defaultEnhancedRetryConfig,
} from './infrastructure';

// MCP Protocol
export type { McpTool, McpContent, McpToolResult, McpServerInfo, McpClient } from './protocols/mcp/index.js';
export {
  textContent,
  StdioClient as McpStdioClient,
  HttpClient as McpHttpClient,
  McpServer,
  McpToolAdapter,
  toolsFromClient,
} from './protocols/mcp/index.js';

// Agent Skills
export { AgentSkill, SkillRegistry, SkillEnabledAgent } from './skills';
