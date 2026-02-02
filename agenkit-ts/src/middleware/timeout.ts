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
  /** Default timeout in milliseconds */
  timeoutMs: number;

  /**
   * Method-specific timeouts in milliseconds (optional).
   *
   * Allows configuring different timeouts for different operations.
   * The method is determined from message metadata "method" or "operation" field.
   * If not specified for a method, defaults to the main timeoutMs value.
   *
   * Example:
   *   methodTimeouts: {
   *     "health_check": 5000,     // 5 seconds for health checks
   *     "long_operation": 120000  // 2 minutes for long operations
   *   }
   */
  methodTimeouts?: Record<string, number>;
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
  private config: TimeoutConfig;
  private _metrics: TimeoutMetrics;

  constructor(agent: Agent, config: TimeoutConfig) {
    super(agent);

    this.config = config;

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

  /**
   * Get timeout for a specific message.
   *
   * Checks message metadata for "method" or "operation" field to determine
   * the operation type, then returns the method-specific timeout if configured,
   * otherwise returns the default timeout.
   */
  private getTimeoutForMessage(message: Message): number {
    if (!this.config.methodTimeouts) {
      return this.config.timeoutMs;
    }

    // Try to determine method from message metadata
    const method = message.metadata?.method || message.metadata?.operation;

    if (method && typeof method === 'string' && this.config.methodTimeouts[method]) {
      return this.config.methodTimeouts[method];
    }

    return this.config.timeoutMs;
  }

  async process(message: Message): Promise<Message> {
    this._metrics.totalRequests++;
    const startTime = Date.now();
    const timeout = this.getTimeoutForMessage(message);

    try {
      const result = await Promise.race([
        this.agent.process(message),
        new Promise<Message>((_, reject) =>
          setTimeout(() => reject(new TimeoutError(timeout)), timeout),
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

  /**
   * Stream messages with timeout enforcement.
   *
   * The timeout applies to the entire streaming operation - if no message is received
   * within the timeout period from the start of the stream, the operation times out.
   * This prevents hung streams from consuming resources indefinitely.
   *
   * @param message Input message
   * @returns Async generator yielding messages
   * @throws TimeoutError if stream times out
   */
  async *processStream(message: Message): AsyncGenerator<Message> {
    this._metrics.totalRequests++;
    const startTime = Date.now();
    const timeout = this.getTimeoutForMessage(message);
    const deadline = startTime + timeout;

    try {
      // Check if agent supports streaming
      if (typeof (this.agent as any).processStream !== 'function') {
        throw new Error('Underlying agent does not support streaming');
      }

      const streamGenerator = (this.agent as any).processStream(message);

      for await (const chunk of streamGenerator) {
        // Check if we've exceeded the deadline
        if (Date.now() > deadline) {
          const duration = Date.now() - startTime;
          this._metrics.timedOutRequests++;
          this.updateDurationStats(duration);
          throw new TimeoutError(timeout);
        }

        yield chunk;
      }

      // Success - stream completed within timeout
      const duration = Date.now() - startTime;
      this._metrics.successfulRequests++;
      this.updateDurationStats(duration);
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
