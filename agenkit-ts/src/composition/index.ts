/**
 * Agent composition patterns.
 *
 * Simple, lightweight building blocks for composing agents:
 * - Sequential: Execute agents in order (pipeline)
 * - Parallel: Execute agents concurrently (ensemble)
 * - Conditional: Route to different agents based on conditions
 * - Fallback: Try agents in order until one succeeds (fault tolerance)
 *
 * These are minimal composition primitives. For richer agent patterns
 * with advanced features, see the `patterns/` module.
 */

export { SequentialAgent } from './sequential.js';
export { ParallelAgent, type AgentResult } from './parallel.js';
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
} from './conditional.js';
export { FallbackAgent } from './fallback.js';
