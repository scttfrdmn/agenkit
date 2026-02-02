/**
 * Retry middleware - automatic retries with exponential backoff.
 *
 * Handles transient failures by retrying requests with configurable
 * backoff strategy.
 */

import { Agent, Message } from '../core/interfaces';
import { BaseMiddleware } from './base';

/**
 * Retry configuration.
 */
export interface RetryConfig {
  /** Maximum number of retry attempts (default: 3) */
  maxAttempts?: number;

  /** Initial delay in milliseconds (default: 1000) */
  initialDelay?: number;

  /** Backoff multiplier (default: 2.0) */
  backoffMultiplier?: number;

  /** Maximum delay in milliseconds (default: 30000) */
  maxDelay?: number;

  /** Predicate to determine if error should trigger retry */
  shouldRetry?: (error: Error) => boolean;
}

/**
 * Retry metrics.
 */
export interface RetryMetrics {
  /** Total number of requests (including retries) */
  totalAttempts: number;

  /** Number of requests that succeeded on first try */
  successfulFirstAttempt: number;

  /** Number of requests that succeeded after retry */
  successfulOnRetry: number;

  /** Number of requests that failed after all retries */
  failedAfterRetries: number;

  /** Total number of retry attempts across all requests */
  totalRetries: number;
}

/**
 * Default retry predicate - retries on network errors.
 */
function defaultShouldRetry(error: Error): boolean {
  // Retry on network errors, timeouts, 5xx errors
  const message = error.message.toLowerCase();
  return (
    message.includes('network') ||
    message.includes('timeout') ||
    message.includes('econnrefused') ||
    message.includes('enotfound') ||
    message.includes('http 5')
  );
}

/**
 * RetryMiddleware implements automatic retry with exponential backoff.
 *
 * Features:
 * - Configurable retry attempts
 * - Exponential backoff
 * - Customizable retry predicate
 * - Preserves error stack traces
 *
 * Usage:
 *   const agent = new RetryMiddleware(baseAgent, {
 *     maxAttempts: 3,
 *     initialDelay: 1000,
 *     backoffMultiplier: 2.0,
 *   });
 */
export class RetryMiddleware extends BaseMiddleware {
  private maxAttempts: number;
  private initialDelay: number;
  private backoffMultiplier: number;
  private maxDelay: number;
  private shouldRetry: (error: Error) => boolean;
  private _metrics: RetryMetrics;

  constructor(agent: Agent, config: RetryConfig = {}) {
    super(agent);
    this.maxAttempts = config.maxAttempts || 3;
    this.initialDelay = config.initialDelay || 1000;
    this.backoffMultiplier = config.backoffMultiplier || 2.0;
    this.maxDelay = config.maxDelay || 30000;
    this.shouldRetry = config.shouldRetry || defaultShouldRetry;
    this._metrics = {
      totalAttempts: 0,
      successfulFirstAttempt: 0,
      successfulOnRetry: 0,
      failedAfterRetries: 0,
      totalRetries: 0,
    };
  }

  /**
   * Get current metrics.
   */
  get metrics(): RetryMetrics {
    return { ...this._metrics };
  }

  async process(message: Message): Promise<Message> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.maxAttempts; attempt++) {
      this._metrics.totalAttempts++; // Track each attempt (initial + retries)

      try {
        const result = await this.agent.process(message);

        // Record success
        if (attempt === 0) {
          this._metrics.successfulFirstAttempt++;
        } else {
          this._metrics.successfulOnRetry++;
        }

        return result;
      } catch (error) {
        lastError = error as Error;

        // Track retry attempts (not counting the initial attempt)
        if (attempt > 0) {
          this._metrics.totalRetries++;
        }

        // Don't retry if predicate says no or if we're on last attempt
        if (!this.shouldRetry(lastError) || attempt === this.maxAttempts - 1) {
          this._metrics.failedAfterRetries++;
          throw lastError;
        }

        // Calculate delay with exponential backoff
        const delay = Math.min(
          this.initialDelay * Math.pow(this.backoffMultiplier, attempt),
          this.maxDelay,
        );

        // Wait before retrying
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    // Should never reach here, but TypeScript needs it
    this._metrics.failedAfterRetries++;
    throw lastError || new Error('Retry failed');
  }
}

/**
 * Create retry middleware function.
 *
 * @param config Retry configuration
 * @returns Middleware function
 */
export function retry(config: RetryConfig = {}) {
  return (agent: Agent): Agent => new RetryMiddleware(agent, config);
}
