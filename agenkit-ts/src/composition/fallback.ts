/**
 * Fallback agent composition pattern.
 *
 * Tries agents in order until one succeeds.
 * This implements the Fallback/Retry pattern for reliability.
 */

import type { Agent, Message } from '../core/interfaces.js';

/**
 * Agent that tries agents in order until one succeeds.
 *
 * This is useful for building fault-tolerant systems where you want
 * to try multiple agents as fallbacks.
 *
 * @example
 * ```typescript
 * const fallback = new FallbackAgent('reliable', [
 *   primaryAgent,
 *   secondaryAgent,
 *   lastResortAgent
 * ]);
 *
 * const result = await fallback.process(message);
 * ```
 */
export class FallbackAgent implements Agent {
  readonly name: string;
  private agents: Agent[];

  /**
   * Create a new fallback agent.
   *
   * @param name - Name of this fallback agent
   * @param agents - List of agents to try in order
   * @throws Error if agents list is empty
   */
  constructor(name: string, agents: Agent[]) {
    if (agents.length === 0) {
      throw new Error('Fallback agent requires at least one agent');
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
    caps.push('fallback');
    return caps;
  }

  /**
   * Try each agent in order until one succeeds.
   *
   * @param message - Input message
   * @returns Response from the first successful agent
   * @throws Error if all agents fail
   */
  async process(message: Message): Promise<Message> {
    const errors: string[] = [];

    for (let i = 0; i < this.agents.length; i++) {
      const agent = this.agents[i];

      try {
        const result = await agent.process(message);

        // Success! Add metadata about which agent was used
        result.metadata = result.metadata || {};
        result.metadata.fallback_agent_used = agent.name;
        result.metadata.fallback_attempt = i + 1;

        return result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        errors.push(`agent ${i + 1} (${agent.name}): ${errorMessage}`);
      }
    }

    // All agents failed
    throw new Error(
      `All ${this.agents.length} agents failed: ${errors.join('; ')}`,
    );
  }

  /**
   * Get the list of fallback agents.
   */
  getAgents(): Agent[] {
    return this.agents;
  }
}
