/**
 * Fallback Pattern
 *
 * Implements sequential retry across multiple agents. If one agent fails,
 * the next agent is tried until one succeeds or all agents are exhausted.
 *
 * Key concepts:
 * - Sequential attempt order
 * - Automatic failover on errors
 * - First successful result wins
 * - Error collection for debugging
 *
 * Performance characteristics:
 * - Best case: O(first agent) - immediate success
 * - Worst case: O(sum of all agents) - all fail
 * - Early termination on first success
 *
 * Example use cases:
 * - High availability: fallback from primary to backup systems
 * - Multi-provider: try different LLM providers until one succeeds
 * - Graceful degradation: try advanced model, fallback to simple model
 * - Retry with alternatives: different strategies for same task
 * - Error recovery: fallback to cached/default responses
 *
 * Example:
 * ```typescript
 * const fallback = new FallbackAgent([
 *   primaryAgent,
 *   backupAgent,
 *   cachedAgent
 * ]);
 *
 * const result = await fallback.process(
 *   createMessage('user', 'Process this')
 * );
 * // Tries primaryAgent first, falls back if it fails
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Result of a single agent attempt.
 */
interface AttemptResult {
  /** Agent index in fallback list */
  agentIndex: number;
  /** Agent name */
  agentName: string;
  /** Whether attempt succeeded */
  success: boolean;
  /** Response message (if successful) */
  message?: Message;
  /** Error (if failed) */
  error?: string;
}

/**
 * Fallback agent that tries agents in sequence until one succeeds.
 *
 * Each agent is attempted in order. The first agent to return a successful
 * response wins, and that response is returned immediately. If an agent
 * fails, the next agent is tried. If all agents fail, an error is thrown
 * combining all failure reasons.
 *
 * The fallback pattern is ideal when you need resilience and have
 * multiple ways to accomplish the same task.
 *
 * @example
 * ```typescript
 * const fallback = new FallbackAgent([
 *   advancedModel,
 *   standardModel,
 *   simpleModel
 * ]);
 *
 * const result = await fallback.process(
 *   createMessage('user', 'Answer this')
 * );
 * // Tries agents in order until one succeeds
 * ```
 */
export class FallbackAgent implements Agent {
  readonly name = 'FallbackAgent';
  private agents: Agent[];

  /**
   * Creates a new fallback agent.
   *
   * @param agents - List of agents to try in order (must have at least one)
   * @throws Error if no agents provided
   *
   * @example
   * ```typescript
   * const fallback = new FallbackAgent([
   *   primaryAgent,
   *   secondaryAgent
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

    capSet.add('fallback');
    capSet.add('retry');
    capSet.add('high-availability');

    return Array.from(capSet);
  }

  /**
   * Tries agents sequentially until one succeeds.
   *
   * Each agent is attempted in order. If an agent succeeds, its response
   * is returned immediately with metadata about the attempt. If an agent
   * fails, the next agent is tried.
   *
   * If all agents fail, an error is thrown that includes information
   * about all failed attempts.
   *
   * The successful message includes metadata about:
   * - Which agent succeeded
   * - How many attempts were made
   * - Which agents were tried
   *
   * @param message - Input message to process
   * @returns Response from first successful agent
   * @throws Error if message invalid or all agents fail
   *
   * @example
   * ```typescript
   * const result = await fallback.process(
   *   createMessage('user', 'Process this')
   * );
   *
   * // Access fallback metadata
   * console.log(result.metadata?.fallback_attempts);
   * console.log(result.metadata?.fallback_success_agent);
   * console.log(result.metadata?.fallback_failed_attempts);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    const attempts: AttemptResult[] = [];

    for (let i = 0; i < this.agents.length; i++) {
      const agent = this.agents[i];

      try {
        // Try agent
        const result = await agent.process(message);

        // Record successful attempt
        const attempt: AttemptResult = {
          agentIndex: i,
          agentName: agent.name,
          success: true,
          message: result,
        };
        attempts.push(attempt);

        // Success! Return with metadata
        return this.buildSuccessResult(result, attempts);
      } catch (error) {
        // Record failed attempt
        const errorMsg = error instanceof Error ? error.message : String(error);
        const attempt: AttemptResult = {
          agentIndex: i,
          agentName: agent.name,
          success: false,
          error: errorMsg,
        };
        attempts.push(attempt);

        // Agent failed, try next (if available)
        // Error will be included in final error if all fail
      }
    }

    // All agents failed
    throw this.buildFailureError(attempts);
  }

  /**
   * Adds fallback metadata to successful response.
   */
  private buildSuccessResult(message: Message, attempts: AttemptResult[]): Message {
    if (!message.metadata) {
      message.metadata = {};
    }

    const successfulAttempt = attempts[attempts.length - 1];

    message.metadata.fallback_attempts = attempts.length;
    message.metadata.fallback_success_index = successfulAttempt.agentIndex;
    message.metadata.fallback_success_agent = successfulAttempt.agentName;
    message.metadata.fallback_total_agents = this.agents.length;

    // Include failed attempts for observability
    if (attempts.length > 1) {
      const failedAttempts = attempts.slice(0, -1).map((attempt) => ({
        index: attempt.agentIndex,
        agent: attempt.agentName,
        error: attempt.error,
      }));
      message.metadata.fallback_failed_attempts = failedAttempts;
    }

    return message;
  }

  /**
   * Creates a comprehensive error from all failed attempts.
   */
  private buildFailureError(attempts: AttemptResult[]): Error {
    const errorParts: string[] = [`all ${attempts.length} agents failed:`];

    for (const attempt of attempts) {
      errorParts.push(`  [${attempt.agentIndex}] ${attempt.agentName}: ${attempt.error}`);
    }

    return new Error(errorParts.join('\n'));
  }
}

/**
 * Function that generates fallback responses when primary agent fails.
 *
 * @param message - Original input message
 * @param originalError - Error from primary agent
 * @returns Fallback response message
 */
export type RecoveryFunc = (message: Message, originalError: Error) => Promise<Message>;

/**
 * Recovery agent that wraps an agent with a recovery function.
 *
 * When the primary agent fails, the recovery function is called to generate
 * a fallback response. This is useful for graceful degradation scenarios.
 *
 * @example
 * ```typescript
 * const recovery = withRecovery(
 *   primaryAgent,
 *   async (msg, err) => createMessage('assistant', 'Service temporarily unavailable')
 * );
 *
 * const result = await recovery.process(
 *   createMessage('user', 'Do something')
 * );
 * // Returns recovery message if primary fails
 * ```
 */
export class RecoveryAgent implements Agent {
  readonly name: string;
  private agent: Agent;
  private recoveryFunc: RecoveryFunc;

  /**
   * Creates a recovery agent.
   *
   * @param agent - Primary agent to wrap
   * @param recoveryFunc - Function to generate fallback responses
   */
  constructor(agent: Agent, recoveryFunc: RecoveryFunc) {
    this.name = `${agent.name}+Recovery`;
    this.agent = agent;
    this.recoveryFunc = recoveryFunc;
  }

  /**
   * Returns the agent's capabilities plus recovery.
   */
  get capabilities(): string[] {
    const caps = this.agent.capabilities ? [...this.agent.capabilities] : [];
    caps.push('recovery', 'error-handling');
    return caps;
  }

  /**
   * Executes the agent with recovery on failure.
   *
   * @param message - Input message
   * @returns Primary response or recovered response
   */
  async process(message: Message): Promise<Message> {
    try {
      const result = await this.agent.process(message);
      return result;
    } catch (error) {
      // Primary agent failed, try recovery
      const primaryError = error instanceof Error ? error : new Error(String(error));

      try {
        const recovered = await this.recoveryFunc(message, primaryError);

        // Add recovery metadata
        if (!recovered.metadata) {
          recovered.metadata = {};
        }
        recovered.metadata.recovery_used = true;
        recovered.metadata.original_error = primaryError.message;

        return recovered;
      } catch (recoveryError) {
        const recoveryMsg =
          recoveryError instanceof Error ? recoveryError.message : String(recoveryError);
        throw new Error(
          `primary agent failed: ${primaryError.message}; recovery failed: ${recoveryMsg}`,
        );
      }
    }
  }
}

/**
 * Creates a fallback agent with custom recovery logic.
 *
 * This is a convenience function for creating RecoveryAgent instances.
 *
 * @param agent - Primary agent
 * @param recovery - Recovery function
 * @returns RecoveryAgent instance
 *
 * @example
 * ```typescript
 * const agent = withRecovery(
 *   primaryAgent,
 *   async (msg, err) => {
 *     console.error('Primary failed:', err);
 *     return createMessage('assistant', 'Fallback response');
 *   }
 * );
 * ```
 */
export function withRecovery(agent: Agent, recovery: RecoveryFunc): RecoveryAgent {
  return new RecoveryAgent(agent, recovery);
}

/**
 * Common recovery strategies.
 */
export const DefaultRecovery = {
  /**
   * Returns a fixed fallback message.
   *
   * @param message - Static message to return on failure
   */
  staticMessage: (message: string): RecoveryFunc => {
    return async (): Promise<Message> => {
      return createMessage('assistant', message);
    };
  },

  /**
   * Returns an empty but valid response.
   */
  emptyResponse: async (): Promise<Message> => {
    return createMessage('assistant', '');
  },

  /**
   * Returns error information in the response.
   */
  errorResponse: async (message: Message, originalError: Error): Promise<Message> => {
    return createMessage(
      'assistant',
      `An error occurred: ${originalError.message}. Please try again.`,
    );
  },
};
