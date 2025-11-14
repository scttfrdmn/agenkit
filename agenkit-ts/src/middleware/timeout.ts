/**
 * Timeout middleware - prevents long-running requests.
 *
 * Automatically cancels requests that exceed a time limit.
 */

import { Agent, Message } from '../core/interfaces';
import { BaseMiddleware } from './base';

/**
 * Timeout configuration.
 */
export interface TimeoutConfig {
  /** Timeout in milliseconds */
  timeout: number;
}

/**
 * Timeout error.
 */
export class TimeoutError extends Error {
  constructor(timeout: number) {
    super(`Request timeout after ${timeout}ms`);
    this.name = 'TimeoutError';
  }
}

/**
 * TimeoutMiddleware implements request timeout.
 *
 * Features:
 * - Configurable timeout
 * - Automatic cancellation
 * - Clear error messages
 *
 * Usage:
 *   const agent = new TimeoutMiddleware(baseAgent, {
 *     timeout: 30000, // 30 seconds
 *   });
 */
export class TimeoutMiddleware extends BaseMiddleware {
  private timeout: number;

  constructor(agent: Agent, config: TimeoutConfig) {
    super(agent);
    this.timeout = config.timeout;
  }

  async process(message: Message): Promise<Message> {
    return Promise.race([
      this.agent.process(message),
      new Promise<Message>((_, reject) =>
        setTimeout(() => reject(new TimeoutError(this.timeout)), this.timeout),
      ),
    ]);
  }
}

/**
 * Create timeout middleware function.
 *
 * @param config Timeout configuration
 * @returns Middleware function
 */
export function timeout(config: TimeoutConfig) {
  return (agent: Agent): Agent => new TimeoutMiddleware(agent, config);
}
