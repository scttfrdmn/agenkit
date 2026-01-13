/**
 * Circuit breaker middleware - prevents cascading failures.
 *
 * Implements the circuit breaker pattern to protect services from
 * repeated failures by temporarily stopping requests.
 */

import { Agent, Message } from '../core/interfaces';
import { BaseMiddleware } from './base';

/**
 * Circuit breaker states.
 */
export enum CircuitState {
  CLOSED = 'CLOSED', // Normal operation
  OPEN = 'OPEN', // Failing, reject requests immediately
  HALF_OPEN = 'HALF_OPEN', // Testing if service recovered
}

/**
 * Circuit breaker configuration.
 */
export interface CircuitBreakerConfig {
  /** Failure threshold to open circuit (default: 5) */
  failureThreshold?: number;

  /** Success threshold to close circuit from half-open (default: 2) */
  successThreshold?: number;

  /** Timeout in ms before attempting recovery (default: 60000) */
  timeout?: number;

  /** Optional per-request timeout in ms (default: none) */
  requestTimeout?: number;

  /** Optional name for logging */
  name?: string;
}

/**
 * Circuit breaker error.
 */
export class CircuitBreakerError extends Error {
  constructor(agentName: string) {
    super(`Circuit breaker OPEN for agent: ${agentName}`);
    this.name = 'CircuitBreakerError';
  }
}

/**
 * Request timeout error.
 */
export class RequestTimeoutError extends Error {
  constructor(timeout: number) {
    super(`Request timeout after ${timeout}ms`);
    this.name = 'RequestTimeoutError';
  }
}

/**
 * Circuit breaker metrics.
 */
export interface CircuitBreakerMetrics {
  /** Total number of requests attempted */
  totalRequests: number;

  /** Number of successful requests */
  successfulRequests: number;

  /** Number of failed requests */
  failedRequests: number;

  /** Number of requests rejected due to open circuit */
  rejectedRequests: number;

  /** State transition counts (e.g., "CLOSED->OPEN": 3) */
  stateChanges: Record<string, number>;

  /** Timestamp of last state change */
  lastStateChange: number | null;

  /** Current circuit state */
  currentState: CircuitState;
}

/**
 * CircuitBreakerMiddleware implements the circuit breaker pattern.
 *
 * Features:
 * - Three states: CLOSED, OPEN, HALF_OPEN
 * - Automatic recovery attempts
 * - Configurable thresholds
 * - Metrics tracking
 *
 * Usage:
 *   const agent = new CircuitBreakerMiddleware(baseAgent, {
 *     failureThreshold: 5,
 *     successThreshold: 2,
 *     timeout: 60000,
 *   });
 */
export class CircuitBreakerMiddleware extends BaseMiddleware {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private nextAttempt = 0;

  private failureThreshold: number;
  private successThreshold: number;
  private timeout: number;
  private requestTimeout?: number;
  private cbName: string;
  private _metrics: CircuitBreakerMetrics;

  constructor(agent: Agent, config: CircuitBreakerConfig = {}) {
    super(agent);
    this.failureThreshold = config.failureThreshold || 5;
    this.successThreshold = config.successThreshold || 2;
    this.timeout = config.timeout || 60000;
    this.requestTimeout = config.requestTimeout;
    this.cbName = config.name || `circuit-breaker-${agent.name}`;
    this._metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      rejectedRequests: 0,
      stateChanges: {},
      lastStateChange: null,
      currentState: CircuitState.CLOSED,
    };
  }

  /**
   * Get current metrics.
   */
  get metrics(): CircuitBreakerMetrics {
    return {
      ...this._metrics,
      stateChanges: { ...this._metrics.stateChanges },
    };
  }

  private recordStateChange(from: CircuitState, to: CircuitState): void {
    const key = `${from}->${to}`;
    this._metrics.stateChanges[key] = (this._metrics.stateChanges[key] || 0) + 1;
    this._metrics.lastStateChange = Date.now();
    this._metrics.currentState = to;
  }

  /**
   * Wrap a promise with a timeout.
   * Returns the promise as-is if no requestTimeout is configured.
   */
  private async withTimeout<T>(promise: Promise<T>): Promise<T> {
    if (!this.requestTimeout) {
      return promise;
    }

    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new RequestTimeoutError(this.requestTimeout!)), this.requestTimeout)
      ),
    ]);
  }

  async process(message: Message): Promise<Message> {
    this._metrics.totalRequests++;

    // Check circuit state
    if (this.state === CircuitState.OPEN) {
      // Check if timeout expired
      if (Date.now() >= this.nextAttempt) {
        const oldState = this.state;
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
        this.recordStateChange(oldState, CircuitState.HALF_OPEN);
      } else {
        this._metrics.rejectedRequests++;
        throw new CircuitBreakerError(this.agent.name);
      }
    }

    try {
      const response = await this.withTimeout(this.agent.process(message));

      // Record success
      this._metrics.successfulRequests++;
      this.onSuccess();

      return response;
    } catch (error) {
      // Record failure
      this._metrics.failedRequests++;
      this.onFailure();

      throw error;
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;

    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;

      if (this.successCount >= this.successThreshold) {
        const oldState = this.state;
        this.state = CircuitState.CLOSED;
        this.successCount = 0;
        this.recordStateChange(oldState, CircuitState.CLOSED);
      }
    }
  }

  private onFailure(): void {
    this.failureCount++;

    if (this.state === CircuitState.HALF_OPEN) {
      // Failed in half-open, immediately open circuit
      const oldState = this.state;
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.timeout;
      this.successCount = 0;
      this.recordStateChange(oldState, CircuitState.OPEN);
    } else if (this.failureCount >= this.failureThreshold) {
      // Exceeded threshold, open circuit
      const oldState = this.state;
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.timeout;
      this.recordStateChange(oldState, CircuitState.OPEN);
    }
  }

  /**
   * Get current circuit state.
   */
  getState(): CircuitState {
    return this.state;
  }

  /**
   * Get failure count.
   */
  getFailureCount(): number {
    return this.failureCount;
  }

  /**
   * Get success count (in half-open state).
   */
  getSuccessCount(): number {
    return this.successCount;
  }

  /**
   * Manually reset circuit breaker.
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.nextAttempt = 0;
  }
}

/**
 * Create circuit breaker middleware function.
 *
 * @param config Circuit breaker configuration
 * @returns Middleware function
 */
export function circuitBreaker(config: CircuitBreakerConfig = {}) {
  return (agent: Agent): Agent => new CircuitBreakerMiddleware(agent, config);
}
