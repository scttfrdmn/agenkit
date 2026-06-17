/**
 * Tests for retry middleware.
 *
 * Tests RetryMiddleware for automatic retries with exponential backoff.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import { RetryMiddleware } from '../../middleware/retry';

// Mock agent that fails a specified number of times before succeeding
class FailingAgent implements Agent {
  name = 'failing-agent';
  capabilities = [];
  private attemptCount = 0;

  constructor(
    private failCount: number,
    private successMessage: string = 'success',
    private errorMessage: string = 'network error',
  ) {}

  async process(message: Message): Promise<Message> {
    this.attemptCount++;

    if (this.attemptCount <= this.failCount) {
      throw new Error(this.errorMessage);
    }

    return createMessage('assistant', this.successMessage);
  }

  getAttemptCount(): number {
    return this.attemptCount;
  }

  reset(): void {
    this.attemptCount = 0;
  }
}

// ============================================
// Basic Retry Tests
// ============================================

describe('RetryMiddleware: Basic Functionality', () => {
  it('should succeed on first try without retry', async () => {
    const agent = new FailingAgent(0, 'success');
    const retry = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 10 });

    const input = createMessage('user', 'test');
    const result = await retry.process(input);

    expect(result.content).toBe('success');
    expect(agent.getAttemptCount()).toBe(1);
    expect(retry.metrics.totalAttempts).toBe(1);
    expect(retry.metrics.successfulFirstAttempt).toBe(1);
    expect(retry.metrics.totalRetries).toBe(0);
  });

  it('should succeed on retry after failures', async () => {
    const agent = new FailingAgent(2, 'success', 'network error');
    const retry = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 10 });

    const input = createMessage('user', 'test');
    const result = await retry.process(input);

    expect(result.content).toBe('success');
    expect(agent.getAttemptCount()).toBe(3); // Failed twice, succeeded third time
    // totalAttempts counts every attempt incl. retries (per RetryMetrics docs):
    // two failures + one success = 3.
    expect(retry.metrics.totalAttempts).toBe(3);
    expect(retry.metrics.successfulFirstAttempt).toBe(0);
    expect(retry.metrics.successfulOnRetry).toBe(1);
    expect(retry.metrics.totalRetries).toBe(1); // 1 retry attempt (not counting first failure)
  });

  it('should fail after max attempts exceeded', async () => {
    const agent = new FailingAgent(5, 'success', 'network error');
    const retry = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 10 });

    const input = createMessage('user', 'test');

    await expect(retry.process(input)).rejects.toThrow('network error');
    expect(agent.getAttemptCount()).toBe(3); // All 3 attempts exhausted
    expect(retry.metrics.failedAfterRetries).toBe(1);
    expect(retry.metrics.totalRetries).toBe(2); // 2 retries (not counting first attempt)
  });
});

// ============================================
// Exponential Backoff Tests
// ============================================

describe('RetryMiddleware: Exponential Backoff', () => {
  // Fake timers make the backoff assertions deterministic: we measure the
  // exact simulated time the middleware schedules rather than wall-clock
  // elapsed (which was flaky on loaded CI and depended on a 250–400ms window).
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  /** Run process() to completion while advancing fake timers, returning the
   *  total simulated milliseconds spent in backoff sleeps. */
  async function runWithSimulatedTime(retry: RetryMiddleware, input: Message): Promise<number> {
    const start = Date.now();
    const done = retry.process(input);
    // Drain all pending timers (the backoff sleeps) until the promise settles.
    await vi.runAllTimersAsync();
    await done;
    return Date.now() - start;
  }

  it('should apply exponential backoff between retries', async () => {
    const agent = new FailingAgent(2, 'success', 'timeout');
    const retry = new RetryMiddleware(agent, {
      maxRetries: 3,
      initialDelayMs: 100,
      backoffMultiplier: 2.0,
    });

    const elapsed = await runWithSimulatedTime(retry, createMessage('user', 'test'));

    // First retry: 100ms, second retry: 200ms = exactly 300ms simulated.
    expect(elapsed).toBe(300);
    expect(agent.getAttemptCount()).toBe(3);
  });

  it('should cap delay at maxDelay', async () => {
    const agent = new FailingAgent(2, 'success', 'timeout');
    const retry = new RetryMiddleware(agent, {
      maxRetries: 3,
      initialDelayMs: 1000,
      backoffMultiplier: 10.0, // Would be 1000, then 10000 without the cap
      maxDelayMs: 150, // Cap each delay at 150ms
    });

    const elapsed = await runWithSimulatedTime(retry, createMessage('user', 'test'));

    // Both retries capped at 150ms = exactly 300ms simulated.
    expect(elapsed).toBe(300);
    expect(agent.getAttemptCount()).toBe(3);
  });
});

// ============================================
// Custom Retry Predicate Tests
// ============================================

describe('RetryMiddleware: Custom Predicates', () => {
  it('should use custom shouldRetry predicate', async () => {
    const agent = new FailingAgent(2, 'success', 'custom error');
    const retry = new RetryMiddleware(agent, {
      maxRetries: 3,
      initialDelayMs: 10,
      shouldRetry: (error: Error) => error.message.includes('custom'),
    });

    const input = createMessage('user', 'test');
    const result = await retry.process(input);

    expect(result.content).toBe('success');
    expect(agent.getAttemptCount()).toBe(3);
  });

  it('should not retry on non-retryable errors', async () => {
    const agent = new FailingAgent(3, 'success', 'validation error');
    const retry = new RetryMiddleware(agent, {
      maxRetries: 3,
      initialDelayMs: 10,
      shouldRetry: (error: Error) => error.message.includes('network'),
    });

    const input = createMessage('user', 'test');

    await expect(retry.process(input)).rejects.toThrow('validation error');
    expect(agent.getAttemptCount()).toBe(1); // Only one attempt, no retries
    expect(retry.metrics.failedAfterRetries).toBe(1);
    expect(retry.metrics.totalRetries).toBe(0);
  });

  it('should retry on default network errors', async () => {
    const networkErrors = ['network error', 'timeout', 'ECONNREFUSED', 'ENOTFOUND', 'HTTP 500'];

    for (const errorMsg of networkErrors) {
      const agent = new FailingAgent(1, 'success', errorMsg);
      const retry = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 10 });

      const input = createMessage('user', 'test');
      const result = await retry.process(input);

      expect(result.content).toBe('success');
      expect(agent.getAttemptCount()).toBe(2); // Failed once, succeeded on retry
      agent.reset();
    }
  });
});

// ============================================
// Metrics Tests
// ============================================

describe('RetryMiddleware: Metrics', () => {
  it('should track metrics correctly across multiple requests', async () => {
    // First request: succeeds immediately
    const retry = new RetryMiddleware(new FailingAgent(0, 'success'), {
      maxRetries: 3,
      initialDelayMs: 10,
    });
    await retry.process(createMessage('user', 'test1'));
    expect(retry.metrics.successfulFirstAttempt).toBe(1);

    // Second request: fails once, then succeeds
    const agent2 = new FailingAgent(1, 'success', 'network error');
    const retry2 = new RetryMiddleware(agent2, { maxRetries: 3, initialDelayMs: 10 });
    await retry2.process(createMessage('user', 'test2'));
    expect(retry2.metrics.successfulOnRetry).toBe(1);

    // Third request: fails completely
    const agent3 = new FailingAgent(5, 'success', 'network error');
    const retry3 = new RetryMiddleware(agent3, { maxRetries: 3, initialDelayMs: 10 });
    try {
      await retry3.process(createMessage('user', 'test3'));
    } catch {
      // Expected
    }
    expect(retry3.metrics.failedAfterRetries).toBe(1);
  });

  it('should return metrics copy to prevent mutation', () => {
    const retry = new RetryMiddleware(new FailingAgent(0, 'success'), {
      maxRetries: 3,
    });

    const metrics1 = retry.metrics;
    const metrics2 = retry.metrics;

    expect(metrics1).toEqual(metrics2);
    expect(metrics1).not.toBe(metrics2); // Different objects
  });
});

// ============================================
// Config Validation Tests
// ============================================

describe('RetryMiddleware: Configuration', () => {
  it('should use default config values', () => {
    const agent = new FailingAgent(0, 'success');
    const retry = new RetryMiddleware(agent);

    const input = createMessage('user', 'test');
    expect(retry.process(input)).resolves.toBeDefined();
  });

  it('should accept custom config values', () => {
    const agent = new FailingAgent(0, 'success');
    const retry = new RetryMiddleware(agent, {
      maxRetries: 5,
      initialDelayMs: 500,
      backoffMultiplier: 3.0,
      maxDelayMs: 10000,
    });

    expect(retry).toBeDefined();
  });
});

// ============================================
// Agent Interface Tests
// ============================================

describe('RetryMiddleware: Agent Interface', () => {
  it('should preserve agent name and capabilities', () => {
    const agent = new FailingAgent(0, 'success');
    agent.name = 'custom-agent';
    agent.capabilities = ['chat', 'tools'];

    const retry = new RetryMiddleware(agent);

    expect(retry.name).toBe('custom-agent');
    expect(retry.capabilities).toEqual(['chat', 'tools']);
  });
});
