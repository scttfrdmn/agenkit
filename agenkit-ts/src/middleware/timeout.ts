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
 * Timeout metrics.
 */
export interface TimeoutMetrics {
  /** Total number of requests */
  totalRequests: number;

  /** Number of successful requests (completed within timeout) */
  successfulRequests: number;

  /** Number of requests that timed out */
  timedOutRequests: number;

  /** Number of requests that failed for other reasons */
  failedRequests: number;

  /** Minimum request duration in milliseconds */
  minDuration: number | null;

  /** Maximum request duration in milliseconds */
  maxDuration: number | null;

  /** Average request duration in milliseconds */
  avgDuration: number;

  /** Total duration of all requests */
  totalDuration: number;
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
  private _metrics: TimeoutMetrics;

  constructor(agent: Agent, config: TimeoutConfig) {
    super(agent);
    this.timeout = config.timeout;
    this._metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      timedOutRequests: 0,
      failedRequests: 0,
      minDuration: null,
      maxDuration: null,
      avgDuration: 0,
      totalDuration: 0,
    };
  }

  /**
   * Get current metrics.
   */
  get metrics(): TimeoutMetrics {
    return { ...this._metrics };
  }

  private updateDurationStats(duration: number): void {
    this._metrics.totalDuration += duration;

    if (this._metrics.minDuration === null || duration < this._metrics.minDuration) {
      this._metrics.minDuration = duration;
    }

    if (this._metrics.maxDuration === null || duration > this._metrics.maxDuration) {
      this._metrics.maxDuration = duration;
    }

    this._metrics.avgDuration = this._metrics.totalDuration / this._metrics.totalRequests;
  }

  async process(message: Message): Promise<Message> {
    this._metrics.totalRequests++;
    const startTime = Date.now();

    try {
      const result = await Promise.race([
        this.agent.process(message),
        new Promise<Message>((_, reject) =>
          setTimeout(() => reject(new TimeoutError(this.timeout)), this.timeout),
        ),
      ]);

      const duration = Date.now() - startTime;
      this._metrics.successfulRequests++;
      this.updateDurationStats(duration);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;

      if (error instanceof TimeoutError) {
        this._metrics.timedOutRequests++;
      } else {
        this._metrics.failedRequests++;
      }

      this.updateDurationStats(duration);
      throw error;
    }
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
