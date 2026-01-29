/**
 * Parallel agent composition pattern.
 *
 * Executes multiple agents concurrently and combines their results.
 */

import type { Agent, Message } from '../core/interfaces.js';
import { createMessage } from '../core/interfaces.js';

/**
 * Result from a single agent execution.
 */
export interface AgentResult {
  agentName: string;
  message: Message | null;
  error: Error | null;
}

/**
 * Agent that executes multiple agents concurrently and combines their results.
 *
 * All agents receive the same input message and execute in parallel.
 * Results are combined into a single output message.
 *
 * @example
 * ```typescript
 * const parallel = new ParallelAgent('ensemble', [
 *   expertAgent1,
 *   expertAgent2,
 *   expertAgent3
 * ]);
 *
 * const result = await parallel.process(message);
 * ```
 */
export class ParallelAgent implements Agent {
  readonly name: string;
  private agents: Agent[];

  /**
   * Create a new parallel agent.
   *
   * @param name - Name of this parallel agent
   * @param agents - List of agents to execute in parallel
   * @throws Error if agents list is empty
   */
  constructor(name: string, agents: Agent[]) {
    if (agents.length === 0) {
      throw new Error('Parallel agent requires at least one agent');
    }

    this.name = name;
    this.agents = agents;
  }

  /**
   * Get combined capabilities of all agents.
   */
  get capabilities(): string[] {
    const capsSet = new Set<string>();

    for (const agent of this.agents) {
      if (agent.capabilities) {
        for (const cap of agent.capabilities) {
          capsSet.add(cap);
        }
      }
    }

    const caps = Array.from(capsSet);
    caps.push('parallel');
    return caps;
  }

  /**
   * Execute all agents in parallel and combine their results.
   *
   * @param message - Input message
   * @returns Combined message with results from all agents
   * @throws Error if any agent fails
   */
  async process(message: Message): Promise<Message> {
    // Create tasks for all agents
    const tasks = this.agents.map((agent) =>
      this.executeAgent(agent, message),
    );

    // Wait for all agents to complete
    const results = await Promise.all(tasks);

    // Check for errors
    const errors: string[] = [];
    for (const result of results) {
      if (result.error) {
        errors.push(`${result.agentName}: ${result.error.message}`);
      }
    }

    if (errors.length > 0) {
      throw new Error(`Parallel execution had errors: ${errors.join('; ')}`);
    }

    // Combine all responses
    return this.combineResponses(results);
  }

  /**
   * Execute a single agent and return the result.
   */
  private async executeAgent(
    agent: Agent,
    message: Message,
  ): Promise<AgentResult> {
    try {
      const result = await agent.process(message);
      return {
        agentName: agent.name,
        message: result,
        error: null,
      };
    } catch (error) {
      return {
        agentName: agent.name,
        message: null,
        error: error instanceof Error ? error : new Error(String(error)),
      };
    }
  }

  /**
   * Combine multiple agent responses into a single message.
   */
  private combineResponses(results: AgentResult[]): Message {
    const contentParts: string[] = [];
    const combinedMetadata: Record<string, unknown> = {};

    for (const result of results) {
      if (result.message) {
        contentParts.push(
          `[${result.agentName}]: ${result.message.content}`,
        );

        // Merge metadata with agent name prefix
        if (result.message.metadata) {
          for (const [key, value] of Object.entries(result.message.metadata)) {
            const prefixedKey = `${result.agentName}.${key}`;
            combinedMetadata[prefixedKey] = value;
          }
        }
      }
    }

    return createMessage('agent', contentParts.join('\n'), combinedMetadata);
  }

  /**
   * Get the list of agents that run in parallel.
   */
  getAgents(): Agent[] {
    return this.agents;
  }
}
