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
  EvaluationResult,
  evaluateAgent,
} from './evaluation/quality-metrics';
export {
  MemoryEntry,
  MemoryStore,
  WorkingMemory,
  ShortTermMemory,
  LongTermMemory,
  MemoryHierarchy,
  createMemoryEntry,
} from './patterns/memory';
