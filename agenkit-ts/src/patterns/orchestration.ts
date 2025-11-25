/**
 * Core orchestration patterns for agenkit.
 *
 * Patterns are reusable ways to compose agents:
 * - Sequential: Execute agents one after another (pipeline)
 * - Parallel: Execute agents concurrently (fan-out)
 *
 * Design principles:
 * - Simple, obvious implementations
 * - No magic, no surprises
 * - Composable (patterns can contain patterns)
 * - Observable (hooks for monitoring)
 *
 * Example:
 * ```typescript
 * // Sequential pipeline
 * const pipeline = new SequentialPattern([preprocessor, analyzer, formatter]);
 * const result = await pipeline.process(message);
 *
 * // Parallel execution
 * const parallel = new ParallelPattern([agent1, agent2, agent3]);
 * const result = await parallel.process(message);
 * ```
 */

import { Agent, Message } from '../core/interfaces';

/** Hook function called before/after agent execution */
export type AgentHook = (agent: Agent, message: Message) => void;

/** Aggregator function to combine parallel results */
export type Aggregator = (messages: Message[]) => Message;

/**
 * Execute agents sequentially - output of one becomes input of next.
 *
 * This is the simplest and most common pattern: agent1 → agent2 → agent3
 *
 * Performance characteristics:
 * - No overhead vs calling agents directly
 * - Agents execute in order (no parallelism)
 * - Short-circuits on error (stops at first failure)
 *
 * Example:
 * ```typescript
 * const pipeline = new SequentialPattern([agent1, agent2, agent3]);
 * const result = await pipeline.process(message);
 * ```
 */
export class SequentialPattern implements Agent {
  readonly name: string;
  private agents: Agent[];
  private beforeAgent?: AgentHook;
  private afterAgent?: AgentHook;

  constructor(
    agents: Agent[],
    options?: {
      name?: string;
      beforeAgent?: AgentHook;
      afterAgent?: AgentHook;
    }
  ) {
    if (!agents || agents.length === 0) {
      throw new Error('Sequential pattern requires at least one agent');
    }

    this.agents = agents;
    this.name = options?.name || 'sequential';
    this.beforeAgent = options?.beforeAgent;
    this.afterAgent = options?.afterAgent;
  }

  get capabilities(): string[] {
    const caps = new Set<string>();
    for (const agent of this.agents) {
      if (agent.capabilities) {
        agent.capabilities.forEach(c => caps.add(c));
      }
    }
    return Array.from(caps);
  }

  /**
   * Execute agents sequentially.
   *
   * @param message Initial input message
   * @returns Final message after all agents have processed
   */
  async process(message: Message): Promise<Message> {
    let current = message;

    for (const agent of this.agents) {
      // Hook: before agent
      if (this.beforeAgent) {
        this.beforeAgent(agent, current);
      }

      // Process
      current = await agent.process(current);

      // Hook: after agent
      if (this.afterAgent) {
        this.afterAgent(agent, current);
      }
    }

    return current;
  }

  /**
   * Get underlying agents list.
   *
   * @returns Copy of agents array in execution order
   */
  unwrap(): Agent[] {
    return [...this.agents];
  }
}

/**
 * Execute agents in parallel and aggregate results.
 *
 * All agents receive the same input, execute concurrently, results are combined.
 *
 * Performance characteristics:
 * - True parallelism (uses Promise.all)
 * - Bounded by slowest agent
 * - Memory: O(n) where n = number of agents
 *
 * Example:
 * ```typescript
 * const parallel = new ParallelPattern(
 *   [agent1, agent2, agent3],
 *   { aggregator: (results) => combineResults(results) }
 * );
 * const result = await parallel.process(message);
 * ```
 */
export class ParallelPattern implements Agent {
  readonly name: string;
  private agents: Agent[];
  private aggregator: Aggregator;

  constructor(
    agents: Agent[],
    options?: {
      name?: string;
      aggregator?: Aggregator;
    }
  ) {
    if (!agents || agents.length === 0) {
      throw new Error('Parallel pattern requires at least one agent');
    }

    this.agents = agents;
    this.name = options?.name || 'parallel';
    this.aggregator = options?.aggregator || ParallelPattern.defaultAggregator;
  }

  /**
   * Default aggregation: combine all content into metadata, return first.
   *
   * @param messages Results from all agents
   * @returns First message with all results in metadata
   */
  static defaultAggregator(messages: Message[]): Message {
    if (!messages || messages.length === 0) {
      throw new Error('No messages to aggregate');
    }

    const first = messages[0];
    // Put all results in metadata for inspection
    const allResults = messages.map(msg => ({
      role: msg.role,
      content: msg.content,
      metadata: msg.metadata,
    }));

    return {
      ...first,
      metadata: {
        ...first.metadata,
        parallelResults: allResults,
      },
    };
  }

  get capabilities(): string[] {
    const caps = new Set<string>();
    for (const agent of this.agents) {
      if (agent.capabilities) {
        agent.capabilities.forEach(c => caps.add(c));
      }
    }
    return Array.from(caps);
  }

  /**
   * Execute agents in parallel and aggregate results.
   *
   * @param message Input message (sent to all agents)
   * @returns Aggregated message from all agents
   */
  async process(message: Message): Promise<Message> {
    // Execute all agents concurrently
    const tasks = this.agents.map(agent => agent.process(message));
    const results = await Promise.all(tasks);

    // Aggregate results
    return this.aggregator(results);
  }

  /**
   * Get underlying agents list.
   *
   * @returns Copy of agents array (no particular order)
   */
  unwrap(): Agent[] {
    return [...this.agents];
  }
}
