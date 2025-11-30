/**
 * Parallel Pattern
 *
 * Enables concurrent execution of multiple agents with result aggregation.
 * This is ideal for ensemble methods, multi-perspective analysis, or
 * parallelizing independent tasks.
 *
 * Key concepts:
 * - Concurrent agent execution using Promise.all()
 * - Custom aggregation function for combining results
 * - All agents receive the same input message
 * - Results collected and aggregated after all complete
 *
 * Performance characteristics:
 * - Time: O(max agent time) - parallel execution
 * - Memory: O(n * message size) for concurrent processing
 * - Thread-safe with proper async handling
 *
 * Example use cases:
 * - Multi-model ensemble for improved accuracy
 * - Parallel document analysis (sentiment, entities, topics)
 * - A/B testing different agent implementations
 * - Redundant processing for reliability
 *
 * Example:
 * ```typescript
 * const parallel = new ParallelAgent(
 *   [sentimentAgent, entityAgent, topicAgent],
 *   DefaultAggregators.concatenate
 * );
 *
 * const result = await parallel.process(
 *   createMessage('user', 'Analyze this text')
 * );
 * // All agents process in parallel, results are combined
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Function that combines multiple agent responses into one.
 *
 * Common aggregation strategies include:
 * - Voting: Select most common response
 * - Averaging: Combine numeric results
 * - Concatenation: Merge all responses
 * - First-success: Return first successful result
 * - Consensus: Require agreement threshold
 */
export type AggregatorFunc = (messages: Message[]) => Message;

/**
 * Result from an individual agent execution.
 */
interface AgentResult {
  /** Agent name */
  agentName: string;
  /** Response message (if successful) */
  message?: Message;
  /** Error (if failed) */
  error?: string;
}

/**
 * Parallel agent that executes multiple agents concurrently and aggregates results.
 *
 * All agents receive the same input message and execute concurrently using
 * Promise.all(). Results are collected and passed to the aggregator function
 * which produces the final output.
 *
 * If any agent fails, the error is collected but other agents continue.
 * The aggregator receives all successful results.
 *
 * @example
 * ```typescript
 * const ensemble = new ParallelAgent(
 *   [model1, model2, model3],
 *   DefaultAggregators.majorityVote
 * );
 *
 * const result = await ensemble.process(
 *   createMessage('user', 'What is 2+2?')
 * );
 * ```
 */
export class ParallelAgent implements Agent {
  readonly name = 'ParallelAgent';
  private agents: Agent[];
  private aggregator: AggregatorFunc;

  /**
   * Creates a new parallel execution agent.
   *
   * @param agents - List of agents to execute concurrently (must have at least one)
   * @param aggregator - Function to combine agent results into final output
   * @throws Error if no agents provided or aggregator is missing
   *
   * @example
   * ```typescript
   * const parallel = new ParallelAgent(
   *   [agentA, agentB, agentC],
   *   (messages) => messages[0] // Use first result
   * );
   * ```
   */
  constructor(agents: Agent[], aggregator: AggregatorFunc) {
    if (!agents || agents.length === 0) {
      throw new Error('at least one agent is required');
    }
    if (!aggregator) {
      throw new Error('aggregator function is required');
    }
    this.agents = agents;
    this.aggregator = aggregator;
  }

  /**
   * Returns the combined capabilities of all agents.
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

    capSet.add('parallel');
    capSet.add('ensemble');

    return Array.from(capSet);
  }

  /**
   * Executes all agents concurrently and aggregates results.
   *
   * All agents receive the same input message and execute in parallel using
   * Promise.all(). Results are collected as they complete. Once all agents
   * finish (or fail), successful results are passed to the aggregator function.
   *
   * If all agents fail, an error is thrown. If some agents succeed, their
   * results are aggregated and any errors are recorded in metadata.
   *
   * The final message includes metadata about:
   * - Total agents executed
   * - Successful agent results
   * - Any errors that occurred
   *
   * @param message - Input message to process
   * @returns Aggregated message from successful agents
   * @throws Error if message is invalid or all agents fail
   *
   * @example
   * ```typescript
   * const result = await parallel.process(
   *   createMessage('user', 'Analyze this')
   * );
   *
   * // Access parallel execution metadata
   * console.log(result.metadata?.parallel_agents);
   * console.log(result.metadata?.successful_agents);
   * console.log(result.metadata?.errors);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    // Execute all agents concurrently
    const results = await Promise.allSettled(
      this.agents.map(async (agent) => {
        const result = await agent.process(message);
        return { agentName: agent.name, message: result };
      }),
    );

    // Collect successes and failures
    const successes: Message[] = [];
    const errors: Array<{ agent: string; error: string }> = [];

    for (const result of results) {
      if (result.status === 'fulfilled') {
        successes.push(result.value.message);
      } else {
        const agentIndex = results.indexOf(result);
        const agentName = this.agents[agentIndex]?.name || `Agent ${agentIndex}`;
        errors.push({
          agent: agentName,
          error: result.reason instanceof Error ? result.reason.message : String(result.reason),
        });
      }
    }

    // Check if all agents failed
    if (successes.length === 0) {
      throw new Error(`all agents failed: ${JSON.stringify(errors)}`);
    }

    // Aggregate successful results
    const aggregated = this.aggregator(successes);

    // Add parallel execution metadata
    if (!aggregated.metadata) {
      aggregated.metadata = {};
    }
    aggregated.metadata.parallel_agents = this.agents.length;
    aggregated.metadata.successful_agents = successes.length;
    if (errors.length > 0) {
      aggregated.metadata.errors = errors;
    }

    return aggregated;
  }
}

/**
 * Common aggregation strategies for parallel agent execution.
 *
 * These functions can be used with ParallelAgent to combine results
 * in different ways depending on your use case.
 */
export const DefaultAggregators = {
  /**
   * Returns the first successful result.
   *
   * Useful when you just want any successful response and don't care
   * about combining multiple perspectives.
   */
  first: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No results to aggregate');
    }
    return messages[0];
  },

  /**
   * Combines all results with separator.
   *
   * Useful when you want to see all perspectives or results side by side.
   */
  concatenate: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No results to aggregate');
    }

    const combined = messages
      .map((msg) => String(msg.content))
      .join('\n\n---\n\n');

    return createMessage('assistant', combined);
  },

  /**
   * Returns the most common response.
   *
   * Useful for ensemble methods where you want the majority opinion.
   * If there's a tie, returns the first message with the highest count.
   */
  majorityVote: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No results to aggregate');
    }

    // Count occurrences of each response
    const votes = new Map<string, number>();
    const msgByContent = new Map<string, Message>();

    for (const msg of messages) {
      const content = String(msg.content);
      votes.set(content, (votes.get(content) || 0) + 1);
      msgByContent.set(content, msg);
    }

    // Find most common response
    let maxVotes = 0;
    let winner = '';
    for (const [content, count] of Array.from(votes.entries())) {
      if (count > maxVotes) {
        maxVotes = count;
        winner = content;
      }
    }

    const result = msgByContent.get(winner)!;
    if (!result.metadata) {
      result.metadata = {};
    }
    result.metadata.votes = maxVotes;
    result.metadata.total_agents = messages.length;

    return result;
  },
};
