/**
 * Sequential agent composition pattern.
 *
 * Executes multiple agents in sequence where the output of one agent
 * becomes the input to the next agent.
 */

import type { Agent, Message } from '../core/interfaces.js';

/**
 * Agent that executes multiple agents in sequence.
 *
 * The output of one agent becomes the input to the next agent.
 * This is useful for building processing pipelines.
 *
 * @example
 * ```typescript
 * const sequential = new SequentialAgent('pipeline', [
 *   extractAgent,
 *   translateAgent,
 *   summarizeAgent
 * ]);
 *
 * const result = await sequential.process(message);
 * ```
 */
export class SequentialAgent implements Agent {
  readonly name: string;
  private agents: Agent[];

  /**
   * Create a new sequential agent.
   *
   * @param name - Name of this sequential agent
   * @param agents - List of agents to execute in sequence
   * @throws Error if agents list is empty
   */
  constructor(name: string, agents: Agent[]) {
    if (agents.length === 0) {
      throw new Error('Sequential agent requires at least one agent');
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
    caps.push('sequential');
    return caps;
  }

  /**
   * Execute all agents in sequence.
   *
   * @param message - Input message
   * @returns Output message from the last agent in the sequence
   * @throws Error if any agent in the sequence fails
   */
  async process(message: Message): Promise<Message> {
    let current = message;

    for (let i = 0; i < this.agents.length; i++) {
      const agent = this.agents[i];

      try {
        const result = await agent.process(current);
        current = result;
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        throw new Error(
          `Step ${i + 1} (${agent.name}) failed: ${errorMessage}`,
        );
      }
    }

    return current;
  }

  /**
   * Get the list of agents in the sequence.
   */
  getAgents(): Agent[] {
    return this.agents;
  }
}
