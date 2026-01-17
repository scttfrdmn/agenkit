/**
 * Tests for circuit breaker middleware.
 *
 * Tests CircuitBreakerMiddleware for preventing cascading failures.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import {
  CircuitBreakerMiddleware,
  CircuitBreakerError,
  RequestTimeoutError,
  CircuitState,
} from '../../middleware/circuit-breaker';

// Unreliable agent that follows a failure pattern
class UnreliableAgent implements Agent {
  name = 'unreliable-agent';
  capabilities = [];
  private callIndex = 0;

  constructor(
    private failurePattern: boolean[], // true = fail, false = succeed
    private delay: number = 0,
  ) {}

  async process(message: Message): Promise<Message> {
    if (this.delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.delay));
    }

    const shouldFail = this.failurePattern[this.callIndex % this.failurePattern.length];
    this.callIndex++;

    if (shouldFail) {
      throw new Error('Service unavailable');
    }

    return createMessage('assistant', 'success');
  }

  reset(): void {
    this.callIndex = 0;
  }
}

// ============================================
// Basic Circuit Breaker Tests
// ============================================

describe('CircuitBreakerMiddleware: Basic Functionality', () => {
  it('should start in CLOSED state and allow requests', async () => {
    const agent = new UnreliableAgent([false, false, false]); // All succeed
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 3,
      timeout: 100,
    });

    expect(cb.getState()).toBe(CircuitState.CLOSED);

    const input = createMessage('user', 'test');
    const result = await cb.process(input);

    expect(result.content).toBe('success');
    expect(cb.getState()).toBe(CircuitState.CLOSED);
    expect(cb.metrics.successfulRequests).toBe(1);
  });

  it('should open circuit after failure threshold', async () => {
    const agent = new UnreliableAgent([true, true, true, true, true]); // All fail
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 3,
      timeout: 1000,
    });

    const input = createMessage('user', 'test');

    // Fail 3 times to hit threshold
    for (let i = 0; i < 3; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);
    expect(cb.getFailureCount()).toBe(3);
    expect(cb.metrics.failedRequests).toBe(3);
  });

  it('should reject requests when circuit is OPEN', async () => {
    const agent = new UnreliableAgent([true, true, true, true]); // All fail
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      timeout: 1000,
    });

    const input = createMessage('user', 'test');

    // Fail twice to open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);

    // Next request should be rejected immediately
    await expect(cb.process(input)).rejects.toThrow(CircuitBreakerError);
    await expect(cb.process(input)).rejects.toThrow(/Circuit breaker OPEN/);
    expect(cb.metrics.rejectedRequests).toBe(2);
  });
});

// ============================================
// State Transition Tests
// ============================================

describe('CircuitBreakerMiddleware: State Transitions', () => {
  it('should transition to HALF_OPEN after timeout', async () => {
    const agent = new UnreliableAgent([true, true, false]); // Fail twice, then succeed
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      timeout: 100, // Short timeout for testing
    });

    const input = createMessage('user', 'test');

    // Fail twice to open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);

    // Wait for timeout
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Next request should transition to HALF_OPEN
    const result = await cb.process(input);

    expect(result.content).toBe('success');
    expect(cb.getState()).toBe(CircuitState.HALF_OPEN);
  });

  it('should close circuit after success threshold in HALF_OPEN', async () => {
    const agent = new UnreliableAgent([true, true, false, false, false]); // Fail 2x, succeed 3x
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      successThreshold: 2,
      timeout: 100,
    });

    const input = createMessage('user', 'test');

    // Open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);

    // Wait for timeout
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Succeed twice to close circuit
    await cb.process(input);
    expect(cb.getState()).toBe(CircuitState.HALF_OPEN);

    await cb.process(input);
    expect(cb.getState()).toBe(CircuitState.CLOSED);
    expect(cb.metrics.stateChanges['HALF_OPEN->CLOSED']).toBe(1);
  });

  it('should reopen circuit on failure in HALF_OPEN', async () => {
    const agent = new UnreliableAgent([true, true, false, true]); // Fail, fail, succeed, fail
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      timeout: 100,
    });

    const input = createMessage('user', 'test');

    // Open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);

    // Wait for timeout
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Succeed once (transition to HALF_OPEN)
    await cb.process(input);
    expect(cb.getState()).toBe(CircuitState.HALF_OPEN);

    // Fail again (should reopen)
    try {
      await cb.process(input);
    } catch {
      // Expected
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);
    expect(cb.metrics.stateChanges['HALF_OPEN->OPEN']).toBe(1);
  });
});

// ============================================
// Request Timeout Tests
// ============================================

describe('CircuitBreakerMiddleware: Request Timeout', () => {
  it('should timeout slow requests when configured', async () => {
    const agent = new UnreliableAgent([false], 500); // Slow but successful
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      requestTimeout: 100,
    });

    const input = createMessage('user', 'test');

    await expect(cb.process(input)).rejects.toThrow(RequestTimeoutError);
    expect(cb.metrics.failedRequests).toBe(1);
  });

  it('should count timeouts as failures', async () => {
    const agent = new UnreliableAgent([false, false], 500); // All slow
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      requestTimeout: 100,
    });

    const input = createMessage('user', 'test');

    // Timeout twice to open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected timeout
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);
    expect(cb.getFailureCount()).toBe(2);
  });
});

// ============================================
// Metrics Tests
// ============================================

describe('CircuitBreakerMiddleware: Metrics', () => {
  it('should track state transitions', async () => {
    const agent = new UnreliableAgent([true, true, false, false]);
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
      successThreshold: 2,
      timeout: 100,
    });

    const input = createMessage('user', 'test');

    // Open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 150));

    // Close circuit
    await cb.process(input);
    await cb.process(input);

    const metrics = cb.metrics;

    expect(metrics.stateChanges['CLOSED->OPEN']).toBe(1);
    expect(metrics.stateChanges['OPEN->HALF_OPEN']).toBe(1);
    expect(metrics.stateChanges['HALF_OPEN->CLOSED']).toBe(1);
    expect(metrics.currentState).toBe(CircuitState.CLOSED);
    expect(metrics.lastStateChange).toBeGreaterThan(0);
  });

  it('should track request counts correctly', async () => {
    const agent = new UnreliableAgent([false, true, false]);
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 5,
    });

    const input = createMessage('user', 'test');

    await cb.process(input); // Success
    try {
      await cb.process(input); // Failure
    } catch {
      // Expected
    }
    await cb.process(input); // Success

    const metrics = cb.metrics;

    expect(metrics.totalRequests).toBe(3);
    expect(metrics.successfulRequests).toBe(2);
    expect(metrics.failedRequests).toBe(1);
  });

  it('should return metrics copy to prevent mutation', () => {
    const agent = new UnreliableAgent([false]);
    const cb = new CircuitBreakerMiddleware(agent);

    const metrics1 = cb.metrics;
    const metrics2 = cb.metrics;

    expect(metrics1).toEqual(metrics2);
    expect(metrics1).not.toBe(metrics2); // Different objects
    expect(metrics1.stateChanges).not.toBe(metrics2.stateChanges); // Deep copy
  });
});

// ============================================
// Manual Reset Tests
// ============================================

describe('CircuitBreakerMiddleware: Manual Reset', () => {
  it('should reset circuit to CLOSED state', async () => {
    const agent = new UnreliableAgent([true, true, true]);
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 2,
    });

    const input = createMessage('user', 'test');

    // Open circuit
    for (let i = 0; i < 2; i++) {
      try {
        await cb.process(input);
      } catch {
        // Expected
      }
    }

    expect(cb.getState()).toBe(CircuitState.OPEN);

    // Manual reset
    cb.reset();

    expect(cb.getState()).toBe(CircuitState.CLOSED);
    expect(cb.getFailureCount()).toBe(0);
    expect(cb.getSuccessCount()).toBe(0);
  });
});

// ============================================
// Agent Interface Tests
// ============================================

describe('CircuitBreakerMiddleware: Agent Interface', () => {
  it('should preserve agent name and capabilities', () => {
    const agent = new UnreliableAgent([false]);
    agent.name = 'custom-agent';
    agent.capabilities = ['chat', 'tools'];

    const cb = new CircuitBreakerMiddleware(agent);

    expect(cb.name).toBe('custom-agent');
    expect(cb.capabilities).toEqual(['chat', 'tools']);
  });
});

// ============================================
// Configuration Tests
// ============================================

describe('CircuitBreakerMiddleware: Configuration', () => {
  it('should use default configuration values', () => {
    const agent = new UnreliableAgent([false]);
    const cb = new CircuitBreakerMiddleware(agent);

    expect(cb).toBeDefined();
    expect(cb.getState()).toBe(CircuitState.CLOSED);
  });

  it('should accept custom configuration', () => {
    const agent = new UnreliableAgent([false]);
    const cb = new CircuitBreakerMiddleware(agent, {
      failureThreshold: 10,
      successThreshold: 5,
      timeout: 30000,
      requestTimeout: 5000,
      name: 'my-circuit-breaker',
    });

    expect(cb).toBeDefined();
  });
});
