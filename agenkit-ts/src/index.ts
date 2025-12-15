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

// Middleware
export { Middleware, applyMiddleware, BaseMiddleware } from './middleware/base';
export { RetryMiddleware, RetryConfig, retry } from './middleware/retry';
export { TimeoutMiddleware, TimeoutConfig, TimeoutError, timeout } from './middleware/timeout';
export {
  CircuitBreakerMiddleware,
  CircuitBreakerConfig,
  CircuitBreakerError,
  CircuitState,
  circuitBreaker,
} from './middleware/circuit-breaker';

// LLM Adapters
export { OpenAIAgent, OpenAIConfig } from './llm/openai';
export { AnthropicAgent, AnthropicConfig } from './llm/anthropic';

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
