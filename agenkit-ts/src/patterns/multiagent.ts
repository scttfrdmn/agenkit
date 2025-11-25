/**
 * Multi-Agent Collaboration Pattern
 *
 * Enables multiple agents to work together on complex tasks through:
 * - Coordination: Agents working on different parts simultaneously
 * - Delegation: Agents delegating subtasks to specialists
 * - Consensus: Agents reaching agreement through discussion
 *
 * This pattern is useful for:
 * - Complex tasks requiring diverse expertise
 * - Parallelizable workflows
 * - Problems benefiting from multiple perspectives
 *
 * Example:
 * ```typescript
 * const orchestrator = new MultiAgentOrchestrator();
 * orchestrator.registerAgent('researcher', researchAgent);
 * orchestrator.registerAgent('writer', writingAgent);
 *
 * const result = await orchestrator.process(
 *   createMessage('user', 'Write a research report')
 * );
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Task execution status.
 */
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/**
 * A task assigned to an agent.
 */
export interface AgentTask {
  /** Name of the agent assigned to this task */
  agentName: string;
  /** Task description */
  description: string;
  /** Task result (if completed) */
  result?: any;
  /** Current task status */
  status: TaskStatus;
  /** Error message (if failed) */
  error?: string;
}

/**
 * Orchestration strategy for coordinating multiple agents.
 */
export type OrchestrationStrategy = 'sequential' | 'parallel' | 'delegate';

/**
 * Voting strategy for consensus building.
 */
export type VotingStrategy = 'majority' | 'unanimous' | 'weighted';

/**
 * Orchestrates multiple agents working together.
 *
 * The MultiAgentOrchestrator coordinates multiple agents to work on tasks,
 * supporting different orchestration strategies:
 *
 * - **sequential**: Agents execute one after another
 * - **parallel**: Agents execute simultaneously
 * - **delegate**: Main agent delegates to specialists
 *
 * Use this when:
 * - Tasks require diverse expertise
 * - Work can be parallelized
 * - You need to compose multiple agents
 *
 * Example:
 * ```typescript
 * const orchestrator = new MultiAgentOrchestrator('sequential');
 * orchestrator.registerAgent('researcher', researchAgent);
 * orchestrator.registerAgent('writer', writingAgent);
 * orchestrator.registerAgent('editor', editorAgent);
 *
 * const result = await orchestrator.process(
 *   createMessage('user', 'Create a comprehensive report on AI')
 * );
 * // Each agent processes the message in sequence
 * ```
 */
export class MultiAgentOrchestrator implements Agent {
  readonly name = 'MultiAgentOrchestrator';
  private agents: Map<string, Agent>;
  private _strategy: OrchestrationStrategy;
  private _tasks: AgentTask[];

  constructor(strategy: OrchestrationStrategy = 'sequential') {
    this.agents = new Map();
    this._strategy = strategy;
    this._tasks = [];
  }

  /**
   * Get the orchestration strategy.
   */
  get strategy(): OrchestrationStrategy {
    return this._strategy;
  }

  /**
   * Register an agent that can be used.
   *
   * @param name Unique name for the agent
   * @param agent Agent instance
   */
  registerAgent(name: string, agent: Agent): void {
    this.agents.set(name, agent);
  }

  /**
   * Remove a registered agent.
   *
   * @param name Name of the agent to remove
   */
  unregisterAgent(name: string): void {
    this.agents.delete(name);
  }

  /**
   * Get list of registered agent names.
   *
   * @returns Array of agent names
   */
  listAgents(): string[] {
    return Array.from(this.agents.keys());
  }

  /**
   * Process message by coordinating multiple agents.
   *
   * Currently implements sequential strategy where all agents process
   * the message one after another. Results are combined into a single
   * response.
   *
   * @param message Input message
   * @returns Combined response from all agents
   */
  async process(message: Message): Promise<Message> {
    const results: string[] = [];

    for (const [agentName, agent] of this.agents) {
      const task: AgentTask = {
        agentName,
        description: String(message.content),
        status: 'in_progress',
      };
      this._tasks.push(task);

      try {
        const response = await agent.process(message);
        task.result = response.content;
        task.status = 'completed';
        results.push(`${agentName}: ${response.content}`);
      } catch (error) {
        task.error = error instanceof Error ? error.message : String(error);
        task.status = 'failed';
        results.push(`${agentName}: Failed - ${task.error}`);
      }
    }

    const combinedResult = results.join('\n\n');
    return createMessage('assistant', combinedResult);
  }

  /**
   * Get all tasks that have been executed.
   *
   * @returns Copy of the task list
   */
  getTasks(): AgentTask[] {
    return [...this._tasks];
  }
}

/**
 * Reaches consensus among multiple agents.
 *
 * The ConsensusAgent collects responses from multiple agents and combines
 * them into a single consensus response. This is useful for:
 *
 * - Getting multiple perspectives on a problem
 * - Validating decisions across multiple models
 * - Ensemble approaches to improve reliability
 *
 * Example:
 * ```typescript
 * const consensus = new ConsensusAgent('majority');
 * consensus.addAgent(conservativeAgent);
 * consensus.addAgent(creativeAgent);
 * consensus.addAgent(analyticalAgent);
 *
 * const result = await consensus.process(
 *   createMessage('user', "What's the best approach?")
 * );
 * // Result combines perspectives from all three agents
 * ```
 */
export class ConsensusAgent implements Agent {
  readonly name = 'ConsensusAgent';
  private _agents: Agent[];
  private _votingStrategy: VotingStrategy;

  constructor(votingStrategy: VotingStrategy = 'majority') {
    this._agents = [];
    this._votingStrategy = votingStrategy;
  }

  /**
   * Get the voting strategy.
   */
  get votingStrategy(): VotingStrategy {
    return this._votingStrategy;
  }

  /**
   * Get the list of agents.
   */
  get agents(): Agent[] {
    return this._agents;
  }

  /**
   * Add an agent to the consensus group.
   *
   * @param agent Agent to add
   */
  addAgent(agent: Agent): void {
    this._agents.push(agent);
  }

  /**
   * Get responses from all agents and form consensus.
   *
   * Currently implements a simple consensus approach where all responses
   * are combined into a formatted summary showing each agent's perspective.
   *
   * @param message Input message
   * @returns Consensus response combining all agent perspectives
   */
  async process(message: Message): Promise<Message> {
    const responses: string[] = [];

    for (const agent of this._agents) {
      const response = await agent.process(message);
      responses.push(String(response.content));
    }

    // Simple consensus: combine all responses
    let consensus = `Consensus from ${responses.length} agents:\n\n`;
    consensus += responses.map((r, i) => `Agent ${i + 1}: ${r}`).join('\n\n');

    return createMessage('assistant', consensus);
  }
}
