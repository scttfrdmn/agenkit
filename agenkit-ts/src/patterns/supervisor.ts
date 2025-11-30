/**
 * Supervisor Pattern
 *
 * Implements hierarchical coordination where a central supervisor agent plans
 * task decomposition, delegates to specialist agents, and synthesizes their
 * results into a final response.
 *
 * Key concepts:
 * - Central planner/supervisor for coordination
 * - Specialist agents for domain-specific tasks
 * - Task decomposition and delegation
 * - Result synthesis from specialist outputs
 *
 * Performance characteristics:
 * - Time: O(planning + max(specialist) + synthesis)
 * - Memory: O(n specialists * message size)
 * - Hierarchical execution model
 *
 * Example use cases:
 * - Software development: planner coordinates coder, tester, reviewer
 * - Research: planner coordinates searcher, analyzer, writer
 * - Data processing: planner coordinates extractor, transformer, validator
 * - Customer service: planner coordinates billing, technical, account specialists
 *
 * Example:
 * ```typescript
 * const planner = new SimplePlanner(llmAgent);
 * const supervisor = new SupervisorAgent(planner, {
 *   coder: coderAgent,
 *   tester: testerAgent,
 *   reviewer: reviewerAgent
 * });
 *
 * const result = await supervisor.process(
 *   createMessage('user', 'Implement a feature')
 * );
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Represents a decomposed task for a specialist agent.
 */
export interface Subtask {
  /** Type identifies which specialist should handle this subtask */
  type: string;
  /** Message is the input for the specialist */
  message: Message;
  /** Metadata contains additional task information */
  metadata?: Record<string, unknown>;
}

/**
 * Agent responsible for task decomposition and result synthesis.
 *
 * The planner receives the initial message and breaks it down into subtasks
 * for specialist agents. After specialists complete their work, the planner
 * synthesizes their results into a final response.
 */
export interface PlannerAgent extends Agent {
  /**
   * Decomposes a message into subtasks for specialists.
   *
   * @param message - Input message to decompose
   * @returns Array of subtasks to be executed
   */
  plan(message: Message): Promise<Subtask[]>;

  /**
   * Combines specialist results into final response.
   *
   * @param original - Original input message
   * @param results - Map of specialist results keyed by type_index
   * @returns Synthesized final response
   */
  synthesize(original: Message, results: Record<string, Message>): Promise<Message>;
}

/**
 * Execution order information for observability.
 */
interface ExecutionInfo {
  /** Subtask index */
  index: number;
  /** Specialist type */
  type: string;
  /** Specialist agent name */
  specialist: string;
}

/**
 * Supervisor agent that coordinates specialist agents through hierarchical planning.
 *
 * The supervisor uses a planner agent to decompose complex tasks into subtasks,
 * delegates each subtask to an appropriate specialist, and synthesizes the
 * specialist results into a coherent final response.
 *
 * The supervisor pattern is ideal when tasks have clear domain boundaries
 * and benefit from specialized expertise.
 *
 * @example
 * ```typescript
 * const supervisor = new SupervisorAgent(
 *   plannerAgent,
 *   {
 *     research: researchAgent,
 *     analysis: analysisAgent,
 *     writing: writingAgent
 *   }
 * );
 *
 * const result = await supervisor.process(
 *   createMessage('user', 'Create a research report')
 * );
 * ```
 */
export class SupervisorAgent implements Agent {
  readonly name = 'SupervisorAgent';
  private planner: PlannerAgent;
  private specialists: Record<string, Agent>;

  /**
   * Creates a new supervisor agent.
   *
   * @param planner - Agent responsible for planning and synthesis
   * @param specialists - Map of specialist agents keyed by their domain/type
   * @throws Error if planner is missing or no specialists provided
   *
   * @example
   * ```typescript
   * const supervisor = new SupervisorAgent(
   *   myPlanner,
   *   {
   *     specialist1: agent1,
   *     specialist2: agent2
   *   }
   * );
   * ```
   */
  constructor(planner: PlannerAgent, specialists: Record<string, Agent>) {
    if (!planner) {
      throw new Error('planner is required');
    }
    if (!specialists || Object.keys(specialists).length === 0) {
      throw new Error('at least one specialist is required');
    }
    this.planner = planner;
    this.specialists = specialists;
  }

  /**
   * Returns the combined capabilities of planner and specialists.
   */
  get capabilities(): string[] {
    const capSet = new Set<string>();

    // Add planner capabilities
    if (this.planner.capabilities) {
      for (const cap of this.planner.capabilities) {
        capSet.add(cap);
      }
    }

    // Add specialist capabilities
    for (const specialist of Object.values(this.specialists)) {
      if (specialist.capabilities) {
        for (const cap of specialist.capabilities) {
          capSet.add(cap);
        }
      }
    }

    capSet.add('supervisor');
    capSet.add('hierarchical');
    capSet.add('coordination');

    return Array.from(capSet);
  }

  /**
   * Executes the supervisor pattern: plan, delegate, synthesize.
   *
   * The process follows these steps:
   * 1. Planning: Planner decomposes the task into subtasks
   * 2. Delegation: Each subtask is routed to appropriate specialist
   * 3. Execution: Specialists process their assigned subtasks
   * 4. Synthesis: Planner combines specialist results into final response
   *
   * If any subtask references an unknown specialist type, an error is thrown.
   * If any specialist fails, the error is propagated immediately.
   *
   * The final message includes metadata about the planning and delegation process.
   *
   * @param message - Input message to process
   * @returns Synthesized final response
   * @throws Error if message is invalid, planning fails, specialist unavailable, or execution fails
   *
   * @example
   * ```typescript
   * const result = await supervisor.process(
   *   createMessage('user', 'Complex task')
   * );
   *
   * // Access supervisor metadata
   * console.log(result.metadata?.supervisor_subtasks);
   * console.log(result.metadata?.execution_order);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    // Step 1: Plan - decompose task into subtasks
    let subtasks: Subtask[];
    try {
      subtasks = await this.planner.plan(message);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`planning failed: ${errorMsg}`);
    }

    if (subtasks.length === 0) {
      // No subtasks - let planner handle directly
      return this.planner.process(message);
    }

    // Step 2: Validate specialist availability
    for (let i = 0; i < subtasks.length; i++) {
      const subtask = subtasks[i];
      if (!(subtask.type in this.specialists)) {
        const availableTypes = Object.keys(this.specialists);
        throw new Error(
          `subtask ${i} references unknown specialist type '${subtask.type}' (available: ${availableTypes.join(', ')})`,
        );
      }
    }

    // Step 3: Execute subtasks with specialists
    const results: Record<string, Message> = {};
    const executionOrder: ExecutionInfo[] = [];

    for (let i = 0; i < subtasks.length; i++) {
      const subtask = subtasks[i];
      const specialist = this.specialists[subtask.type];

      try {
        // Execute subtask
        const result = await specialist.process(subtask.message);

        // Store result keyed by specialist type and index for synthesis
        const resultKey = `${subtask.type}_${i}`;
        results[resultKey] = result;

        // Track execution order
        executionOrder.push({
          index: i,
          type: subtask.type,
          specialist: specialist.name,
        });
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        throw new Error(`specialist '${subtask.type}' failed on subtask ${i}: ${errorMsg}`);
      }
    }

    // Step 4: Synthesize - combine specialist results
    let final: Message;
    try {
      final = await this.planner.synthesize(message, results);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`synthesis failed: ${errorMsg}`);
    }

    // Add supervisor metadata
    if (!final.metadata) {
      final.metadata = {};
    }
    final.metadata.supervisor_subtasks = subtasks.length;
    final.metadata.supervisor_specialists = Object.keys(this.specialists).length;
    final.metadata.execution_order = executionOrder;

    return final;
  }
}

/**
 * Simple planner implementation for basic use cases.
 *
 * This planner uses an LLM agent to handle both planning and synthesis.
 * For planning, it prompts the LLM to decompose the task. For synthesis,
 * it prompts the LLM to combine results.
 *
 * For production use, consider implementing a custom PlannerAgent with
 * domain-specific planning and synthesis logic.
 *
 * @example
 * ```typescript
 * const planner = new SimplePlanner(llmAgent);
 * const supervisor = new SupervisorAgent(planner, specialists);
 * ```
 */
export class SimplePlanner implements PlannerAgent {
  readonly name = 'SimplePlanner';
  private agent: Agent;

  /**
   * Creates a basic planner using an LLM agent.
   *
   * @param agent - LLM agent for planning and synthesis
   */
  constructor(agent: Agent) {
    this.agent = agent;
  }

  /**
   * Returns the planner's capabilities.
   */
  get capabilities(): string[] {
    const caps = this.agent.capabilities ? [...this.agent.capabilities] : [];
    caps.push('planning', 'synthesis');
    return caps;
  }

  /**
   * Handles direct message processing (delegates to underlying agent).
   *
   * @param message - Input message
   * @returns Agent response
   */
  async process(message: Message): Promise<Message> {
    return this.agent.process(message);
  }

  /**
   * Uses the LLM to decompose tasks (simplified implementation).
   *
   * Note: This is a basic implementation. Production code should parse
   * the LLM response and create proper Subtask structures.
   *
   * @param message - Input message to decompose
   * @returns Array of subtasks (empty for this simple implementation)
   */
  async plan(message: Message): Promise<Subtask[]> {
    // In a real implementation, this would prompt the LLM to create a plan
    // and parse the response into Subtask structures.
    // For now, return empty to trigger direct processing.
    return [];
  }

  /**
   * Combines specialist results (simplified implementation).
   *
   * @param original - Original input message
   * @param results - Map of specialist results
   * @returns Combined synthesis message
   */
  async synthesize(original: Message, results: Record<string, Message>): Promise<Message> {
    // Combine all results
    const parts: string[] = ['Synthesis of specialist results:\n'];

    for (const [key, result] of Object.entries(results)) {
      parts.push(`\nResult from ${key}:\n${String(result.content)}\n`);
    }

    return createMessage('assistant', parts.join(''));
  }
}
