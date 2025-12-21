/**
 * Introspection capability for examining agent internal state.
 *
 * This module provides introspection support - the ability for agents to examine
 * their own internal state, memory, and capabilities. This is distinct from the
 * Reflection pattern, which is about analyzing past performance.
 *
 * Key distinctions:
 * - Introspection (this module): "What do I know?" - State examination
 * - Reflection (pattern): "How did I do?" - Performance analysis
 *
 * References:
 * - Issue #301: Add Introspection Capability to Agent Interface
 * - ArXiv: Introspection of Thought Helps AI Agents (https://arxiv.org/abs/2507.08664)
 * - Biswas & Talukdar: Building Agentic AI Systems
 */

/**
 * Result of agent introspection - a snapshot of internal state.
 *
 * This provides a structured view into an agent's current state, including
 * its capabilities, memory contents, and any agent-specific internal state.
 *
 * Design decisions:
 * - timestamp: ISO 8601 string for when this snapshot was taken
 * - agentName: Which agent was introspected
 * - capabilities: What the agent can do
 * - memoryState: Contents of agent's memory (undefined if no memory)
 * - internalState: Agent-specific state information
 * - metadata: Extension point for additional information
 *
 * Usage:
 *   const result = agent.introspect();
 *   console.log(`Agent: ${result.agentName}`);
 *   console.log(`Capabilities: ${result.capabilities}`);
 *   if (result.memoryState) {
 *     console.log(`Memory entries: ${Object.keys(result.memoryState).length}`);
 *   }
 *
 * Introspection is useful for:
 * - Debugging: Examine agent state during development
 * - Monitoring: Track agent state in production
 * - Coordination: Agents can inspect each other's capabilities
 * - Testing: Verify agent state in tests
 * - Explainability: Understand what an agent "knows"
 */
export interface IntrospectionResult {
  /** ISO 8601 timestamp when introspection was performed */
  timestamp: string;

  /** Name of the agent that was introspected */
  agentName: string;

  /** List of capability strings this agent supports */
  capabilities: string[];

  /** Agent's memory contents (undefined if no memory) */
  memoryState?: Record<string, unknown>;

  /** Agent-specific internal state */
  internalState: Record<string, unknown>;

  /** Additional introspection metadata */
  metadata: Record<string, unknown>;
}

/**
 * Create a default introspection result for an agent.
 *
 * This is a helper function that creates an introspection result with default
 * values for agents that don't have custom memory or internal state.
 *
 * @param agent The agent to introspect
 * @returns IntrospectionResult with basic information
 *
 * Usage:
 *   class MyAgent implements Agent {
 *     name = 'my-agent';
 *     capabilities = ['test'];
 *
 *     async process(message: Message): Promise<Message> { ... }
 *
 *     introspect(): IntrospectionResult {
 *       return createDefaultIntrospectionResult(this);
 *     }
 *   }
 */
export function createDefaultIntrospectionResult(agent: {
  name: string;
  capabilities?: string[];
}): IntrospectionResult {
  return {
    timestamp: new Date().toISOString(),
    agentName: agent.name,
    capabilities: agent.capabilities || [],
    memoryState: undefined,
    internalState: {},
    metadata: {},
  };
}

/**
 * Validate an introspection result.
 *
 * @param result IntrospectionResult to validate
 * @throws Error if result is invalid
 */
export function validateIntrospectionResult(
  result: IntrospectionResult,
): void {
  if (!result.agentName || typeof result.agentName !== 'string') {
    throw new Error('agentName must be a non-empty string');
  }

  if (!Array.isArray(result.capabilities)) {
    throw new Error('capabilities must be an array');
  }

  if (
    typeof result.internalState !== 'object' ||
    result.internalState === null
  ) {
    throw new Error('internalState must be an object');
  }

  if (
    result.memoryState !== undefined &&
    (typeof result.memoryState !== 'object' || result.memoryState === null)
  ) {
    throw new Error('memoryState must be an object or undefined');
  }
}
