/**
 * Pattern Library for Agent Composition
 *
 * This module exports all agent composition patterns available in agenkit.
 * Patterns provide reusable approaches for combining agents to solve complex tasks.
 *
 * Pattern Categories:
 *
 * **Basic Composition:**
 * - Sequential: Pipeline-style processing (A -> B -> C)
 * - Parallel: Concurrent execution with aggregation
 * - Fallback: Sequential retry with automatic failover
 *
 * **Hierarchical Coordination:**
 * - Supervisor: Central planner delegates to specialists
 * - Router: Conditional routing based on classification
 *
 * **Collaborative:**
 * - Collaborative: Peer-to-peer iterative refinement
 *
 * **Human Oversight:**
 * - HumanInLoop: Confidence-based approval gates
 *
 * **Multi-Agent:**
 * - MultiAgentOrchestrator: Coordinate multiple agents
 * - ConsensusAgent: Reach consensus among agents
 *
 * **Reasoning & Planning:**
 * - ReActAgent: Reasoning and acting with tools
 * - ReflectionAgent: Self-reflection and improvement
 * - PlanningAgent: Hierarchical task planning
 * - ReasoningWithToolsAgent: Extended reasoning with tools
 * - OrchestrationAgent: Complex workflow orchestration
 *
 * **Specialized:**
 * - AgentsAsToolsAgent: Use agents as callable tools
 * - MemoryAgent: Conversation history management
 * - ConversationalAgent: Natural dialogue flow
 * - TaskAgent: Structured task execution
 * - AutonomousAgent: Self-directed goal pursuit
 *
 * @example
 * ```typescript
 * import { SequentialAgent, ParallelAgent } from './patterns';
 *
 * // Pipeline pattern
 * const pipeline = new SequentialAgent([agent1, agent2, agent3]);
 *
 * // Ensemble pattern
 * const ensemble = new ParallelAgent(
 *   [model1, model2, model3],
 *   DefaultAggregators.majorityVote
 * );
 * ```
 */

// Sequential pattern
export {
  SequentialAgent,
} from './sequential';

// Parallel pattern
export {
  ParallelAgent,
  DefaultAggregators,
  type AggregatorFunc,
} from './parallel';

// Supervisor pattern
export {
  SupervisorAgent,
  SimplePlanner,
  type PlannerAgent,
  type Subtask,
} from './supervisor';

// Router pattern
export {
  RouterAgent,
  SimpleClassifier,
  LLMClassifier,
  type ClassifierAgent,
  type RouterConfig,
} from './router';

// Collaborative pattern
export {
  CollaborativeAgent,
  DefaultConsensusFunc,
  DefaultMergeFunc,
  type ConsensusFunc,
  type MergeFunc,
  type CollaborativeConfig,
} from './collaborative';

// Human-in-loop pattern
export {
  HumanInLoopAgent,
  simpleApprovalFunc,
  confidenceBasedApprovalFunc,
  type ApprovalFunc,
  type ApprovalRequest,
  type ApprovalResponse,
  type HumanInLoopConfig,
} from './human-in-loop';

// Fallback pattern
export {
  FallbackAgent,
  RecoveryAgent,
  withRecovery,
  DefaultRecovery,
  type RecoveryFunc,
} from './fallback';

// Multi-agent patterns
export {
  MultiAgentOrchestrator,
  ConsensusAgent,
  type AgentTask,
  type TaskStatus,
  type OrchestrationStrategy,
  type VotingStrategy,
} from './multiagent';

// Reasoning patterns
export {
  ReActAgent,
  type ReActConfig,
} from './react';

export {
  ReflectionAgent,
  type ReflectionConfig,
} from './reflection';

export {
  PlanningAgent,
  DefaultStepExecutor,
  type PlanningAgentConfig,
  type Plan,
  type PlanStep,
  type LLMClient as PlanningLLMClient,
  type StepExecutor,
} from './planning';

export {
  ReasoningWithToolsAgent,
  type ReasoningWithToolsConfig,
  type ReasoningStep,
  type ReasoningTrace,
} from './reasoning-with-tools';

export {
  SequentialPattern,
  ParallelPattern,
  RouterPattern,
  type AgentHook,
  type Aggregator,
  type Router,
} from './orchestration';

// Specialized patterns
export {
  AgentTool,
  type AgentToolConfig,
} from './agents-as-tools';

export {
  WorkingMemory,
  ShortTermMemory,
  LongTermMemory,
  MemoryHierarchy,
  type MemoryEntry,
  type MemoryStore,
} from './memory';

export {
  ConversationalAgent,
  type ConversationalAgentConfig,
  type LLMClient as ConversationalLLMClient,
} from './conversational';

export {
  Task,
  type TaskConfig,
} from './task';

export {
  AutonomousAgent,
} from './autonomous';
