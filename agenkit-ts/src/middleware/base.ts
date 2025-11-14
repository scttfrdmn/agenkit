/**
 * Base middleware definitions for agent wrapping.
 *
 * Middleware wraps agents to add cross-cutting concerns like:
 * - Retry logic
 * - Circuit breaking
 * - Timeouts
 * - Logging
 * - Metrics
 * - Caching
 */

import { Agent, Message } from '../core/interfaces';

/**
 * Middleware function type.
 *
 * Takes an agent and returns a wrapped agent with added functionality.
 */
export type Middleware = (agent: Agent) => Agent;

/**
 * Apply multiple middleware to an agent.
 *
 * Middleware is applied in order, so the first middleware in the array
 * is the outermost wrapper (executes first).
 *
 * @param agent Base agent
 * @param middleware Array of middleware to apply
 * @returns Wrapped agent
 *
 * Usage:
 *   const wrapped = applyMiddleware(
 *     agent,
 *     [retryMiddleware, timeoutMiddleware, loggingMiddleware]
 *   );
 */
export function applyMiddleware(agent: Agent, middleware: Middleware[]): Agent {
  return middleware.reduce((wrapped, mw) => mw(wrapped), agent);
}

/**
 * Base class for middleware implementations.
 *
 * Provides common functionality for wrapping agents.
 */
export abstract class BaseMiddleware implements Agent {
  protected agent: Agent;

  constructor(agent: Agent) {
    this.agent = agent;
  }

  get name(): string {
    return this.agent.name;
  }

  get capabilities(): string[] | undefined {
    return this.agent.capabilities;
  }

  abstract process(message: Message): Promise<Message>;

  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    if (!this.agent.processStream) {
      throw new Error(`Agent ${this.agent.name} does not support streaming`);
    }

    yield* this.agent.processStream(message);
  }
}
