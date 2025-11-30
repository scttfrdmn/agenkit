/**
 * Sequential Pattern
 *
 * Enables pipeline-style agent composition where each agent processes the output
 * of the previous agent. This is ideal for multi-stage processing workflows.
 *
 * Key concepts:
 * - Linear processing pipeline
 * - Output of agent N becomes input of agent N+1
 * - Early termination on errors
 * - Preserves metadata across pipeline stages
 *
 * Performance characteristics:
 * - Time: O(sum of agent times) - sequential execution
 * - Memory: O(1) for message passing (no accumulation)
 * - Each agent sees only previous agent's output
 *
 * Example use cases:
 * - Document processing: extract -> translate -> summarize
 * - Data pipeline: validate -> transform -> enrich
 * - Content generation: draft -> review -> format
 *
 * Example:
 * ```typescript
 * const pipeline = new SequentialAgent([
 *   extractorAgent,
 *   translatorAgent,
 *   summarizerAgent
 * ]);
 *
 * const result = await pipeline.process(
 *   createMessage('user', 'Process this document')
 * );
 * // Each agent processes the output of the previous agent
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Stage information for observability.
 */
interface PipelineStage {
  /** Agent name */
  agent: string;
  /** Stage index in pipeline */
  stage: number;
  /** Stage metadata (if any) */
  metadata?: Record<string, unknown>;
}

/**
 * Sequential pipeline agent that executes agents in order.
 *
 * Each agent receives the output of the previous agent as input.
 * The final agent's output is returned as the result.
 *
 * The pipeline stops immediately if any agent returns an error.
 *
 * @example
 * ```typescript
 * const sequential = new SequentialAgent([
 *   validatorAgent,
 *   transformerAgent,
 *   enricherAgent
 * ]);
 *
 * const result = await sequential.process(
 *   createMessage('user', 'Input data')
 * );
 * ```
 */
export class SequentialAgent implements Agent {
  readonly name = 'SequentialAgent';
  private agents: Agent[];

  /**
   * Creates a new sequential pipeline agent.
   *
   * @param agents - List of agents to execute in order (must have at least one)
   * @throws Error if no agents are provided
   *
   * @example
   * ```typescript
   * const pipeline = new SequentialAgent([
   *   agentA,
   *   agentB,
   *   agentC
   * ]);
   * ```
   */
  constructor(agents: Agent[]) {
    if (!agents || agents.length === 0) {
      throw new Error('at least one agent is required');
    }
    this.agents = agents;
  }

  /**
   * Returns the combined capabilities of all agents in the pipeline.
   */
  get capabilities(): string[] {
    const capSet = new Set<string>();

    for (const agent of this.agents) {
      if (agent.capabilities) {
        for (const cap of agent.capabilities) {
          capSet.add(cap);
        }
      }
    }

    capSet.add('sequential');
    capSet.add('pipeline');

    return Array.from(capSet);
  }

  /**
   * Executes the agent pipeline sequentially.
   *
   * The message is passed through each agent in order. Each agent's output
   * becomes the input for the next agent. If any agent throws an error,
   * the pipeline stops and the error is propagated immediately.
   *
   * Metadata from each agent is preserved in the final message under the
   * "pipeline_stages" key, allowing inspection of intermediate results.
   *
   * @param message - Input message to process
   * @returns Final message from last agent in pipeline
   * @throws Error if message is invalid or any agent fails
   *
   * @example
   * ```typescript
   * const result = await pipeline.process(
   *   createMessage('user', 'Process this')
   * );
   *
   * // Access pipeline metadata
   * console.log(result.metadata?.pipeline_stages);
   * console.log(result.metadata?.pipeline_length);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    // Track pipeline stages for observability
    const stages: PipelineStage[] = [];

    // Pass message through each agent
    let current = message;
    for (let i = 0; i < this.agents.length; i++) {
      const agent = this.agents[i];

      try {
        // Process with current agent
        const result = await agent.process(current);

        // Record stage metadata
        const stageInfo: PipelineStage = {
          agent: agent.name,
          stage: i,
        };
        if (result.metadata) {
          stageInfo.metadata = result.metadata;
        }
        stages.push(stageInfo);

        // Use result as input for next agent
        current = result;
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        throw new Error(`agent ${i} (${agent.name}) failed: ${errorMsg}`);
      }
    }

    // Add pipeline metadata to final result
    if (!current.metadata) {
      current.metadata = {};
    }
    current.metadata.pipeline_stages = stages;
    current.metadata.pipeline_length = this.agents.length;

    return current;
  }
}
