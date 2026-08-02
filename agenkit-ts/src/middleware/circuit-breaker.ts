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
 * Cross-language wire names for circuit states.
 *
 * This is the *protocol* spelling, deliberately separate from the enum values above,
 * which are the local/human-facing ones. Keying `stateChanges` off the enum value is
 * what let TypeScript drift to `CLOSED->OPEN` while Python and Go produced
 * `closed->open` (#791): a display choice silently became protocol. Anything crossing a
 * language boundary uses this map; anything local can use the enum value.
 *
 * Canonical form is lowercase, matching Python (`CircuitState.CLOSED = "closed"`) and
 * Go (`CircuitState.String()`), the shared fixtures, and every cross-language harness —
 * all of which already downcase before comparing.
 */
const CIRCUIT_STATE_WIRE_NAMES: Record<CircuitState, string> = {
  [CircuitState.CLOSED]: 'closed',
  [CircuitState.OPEN]: 'open',
  [CircuitState.HALF_OPEN]: 'half_open',
};

/**
 * Returns the cross-language wire name for a circuit state.
 */
export function circuitStateWireName(state: CircuitState): string {
  return CIRCUIT_STATE_WIRE_NAMES[state];
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

  /** Per-request timeout in ms (default: 30000) */
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

  /**
   * State transition counts, keyed `"{from}->{to}"` using
   * {@link circuitStateWireName} (e.g., `"closed->open": 3`).
   *
   * The key format is a cross-language contract shared with the other cores and the
   * `circuit_breaker_behavior.json` fixture — see #791. Do not derive it from the
   * `CircuitState` enum values, which are uppercase.
   */
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
 *     timeout: 60000,        // Recovery timeout
 *     requestTimeout: 30000, // Request timeout (optional, defaults to 30000)
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
  private requestTimeout: number;
  private cbName: string;
  private _metrics: CircuitBreakerMetrics;

  constructor(agent: Agent, config: CircuitBreakerConfig = {}) {
    super(agent);
    this.failureThreshold = config.failureThreshold || 5;
    this.successThreshold = config.successThreshold || 2;
    this.timeout = config.timeout || 60000;
    this.requestTimeout = config.requestTimeout ?? 30000;
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
    const key = `${circuitStateWireName(from)}->${circuitStateWireName(to)}`;
    this._metrics.stateChanges[key] = (this._metrics.stateChanges[key] || 0) + 1;
    this._metrics.lastStateChange = Date.now();
    this._metrics.currentState = to;
  }

  /**
   * Wrap a promise with a timeout.
   * Applies the configured requestTimeout (default 30000ms).
   */
  private async withTimeout<T>(promise: Promise<T>): Promise<T> {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new RequestTimeoutError(this.requestTimeout)), this.requestTimeout)
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
