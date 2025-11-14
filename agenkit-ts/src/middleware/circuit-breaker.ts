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
  private cbName: string;

  constructor(agent: Agent, config: CircuitBreakerConfig = {}) {
    super(agent);
    this.failureThreshold = config.failureThreshold || 5;
    this.successThreshold = config.successThreshold || 2;
    this.timeout = config.timeout || 60000;
    this.cbName = config.name || `circuit-breaker-${agent.name}`;
  }

  async process(message: Message): Promise<Message> {
    // Check circuit state
    if (this.state === CircuitState.OPEN) {
      // Check if timeout expired
      if (Date.now() >= this.nextAttempt) {
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
      } else {
        throw new CircuitBreakerError(this.agent.name);
      }
    }

    try {
      const response = await this.agent.process(message);

      // Record success
      this.onSuccess();

      return response;
    } catch (error) {
      // Record failure
      this.onFailure();

      throw error;
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;

    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;

      if (this.successCount >= this.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.successCount = 0;
      }
    }
  }

  private onFailure(): void {
    this.failureCount++;

    if (this.state === CircuitState.HALF_OPEN) {
      // Failed in half-open, immediately open circuit
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.timeout;
      this.successCount = 0;
    } else if (this.failureCount >= this.failureThreshold) {
      // Exceeded threshold, open circuit
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.timeout;
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
