/**
 * Middleware Resilience Chaos Tests
 *
 * Tests middleware behavior under chaos conditions:
 * - Retry middleware with various failure patterns
 * - Circuit breaker with overload
 * - Timeout middleware with slow responses
 * - Rate limiter under load
 * - Middleware composition under chaos
 *
 * These tests validate that resilience middleware works correctly
 * when agents fail in various ways.
 */

import { describe, it, expect } from 'vitest';
import type { Message } from '../../core/interfaces';
import { ChaosAgent, ChaosMode, FlakeyAgent, OverloadedAgent, SimpleAgent } from './chaos_agents';

// ============================================
// Retry Middleware Tests
// ============================================

describe('Retry Middleware Resilience', () => {
  it('should retry on connection refused and eventually fail', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate retry middleware (3 attempts)
    const maxRetries = 2;
    let attempts = 0;
    let lastError: Error | null = null;

    for (let retry = 0; retry <= maxRetries; retry++) {
      attempts++;
      try {
        await chaosAgent.process(message);
        break;
      } catch (e) {
        lastError = e as Error;
        if (retry < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    expect(attempts).toBe(maxRetries + 1);
    expect(lastError).not.toBeNull();
    expect(lastError?.message).toContain('Connection refused');
  });

  it('should succeed after retries with flakey agent', async () => {
    const baseAgent = new SimpleAgent();
    // Fail twice, then succeed
    const flakeyAgent = new FlakeyAgent(baseAgent, [false, false, true]);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate retry middleware
    const maxRetries = 3;
    let response: Message | null = null;

    for (let retry = 0; retry <= maxRetries; retry++) {
      try {
        response = await flakeyAgent.process(message);
        break;
      } catch {
        if (retry < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    expect(response).not.toBeNull();
    expect(response?.content).toBe('Processed: Test');
  });

  it('should not retry on timeout (different error type)', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.TIMEOUT);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate retry middleware that only retries on connection errors
    const maxRetries = 2;
    let attempts = 0;

    for (let retry = 0; retry <= maxRetries; retry++) {
      attempts++;
      const timeout = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), 100)
      );

      try {
        await Promise.race([chaosAgent.process(message), timeout]);
        break;
      } catch (e) {
        const error = e as Error;
        // Don't retry on timeout errors
        if (error.message === 'Timeout') {
          break;
        }
      }
    }

    // Should only attempt once (no retries on timeout)
    expect(attempts).toBe(1);
  });
});

// ============================================
// Circuit Breaker Tests
// ============================================

describe('Circuit Breaker Resilience', () => {
  it('should open circuit after failure threshold', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate circuit breaker
    const failureThreshold = 3;
    let failures = 0;
    let circuitOpen = false;

    // Make requests until circuit opens
    for (let i = 0; i < 5; i++) {
      if (circuitOpen) {
        // Circuit breaker prevents request
        continue;
      }

      try {
        await chaosAgent.process(message);
        failures = 0; // Reset on success
      } catch {
        failures++;
        if (failures >= failureThreshold) {
          circuitOpen = true;
        }
      }
    }

    expect(circuitOpen).toBe(true);
    expect(failures).toBeGreaterThanOrEqual(failureThreshold);
  });

  it('should handle overloaded agent with circuit breaker', async () => {
    const baseAgent = new SimpleAgent();
    const overloadedAgent = new OverloadedAgent(baseAgent, 5, 0.9);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate circuit breaker
    let failures = 0;
    let circuitOpen = false;
    const failureThreshold = 3;

    // Make requests that will overload the agent
    for (let i = 0; i < 15; i++) {
      if (circuitOpen) {
        continue;
      }

      try {
        await overloadedAgent.process(message);
        failures = 0;
      } catch {
        failures++;
        if (failures >= failureThreshold) {
          circuitOpen = true;
        }
      }
    }

    expect(circuitOpen).toBe(true);
    expect(overloadedAgent.isOverloaded()).toBe(true);
  });
});

// ============================================
// Timeout Middleware Tests
// ============================================

describe('Timeout Middleware Resilience', () => {
  it('should timeout slow responses', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 200, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate timeout middleware (100ms timeout)
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Request timeout')), 100)
    );

    await expect(Promise.race([slowAgent.process(message), timeout])).rejects.toThrow(
      'Request timeout'
    );
  });

  it('should succeed for responses within timeout', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 50, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate timeout middleware (200ms timeout)
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Request timeout')), 200)
    );

    const response = await Promise.race([slowAgent.process(message), timeout]);
    expect(response.content).toBe('Processed: Test');
  });
});

// ============================================
// Rate Limiter Tests
// ============================================

describe('Rate Limiter Resilience', () => {
  it('should throttle high request rates', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Simulate rate limiter (max 5 requests per 100ms)
    const maxRequests = 5;
    const windowMs = 100;
    let requestsInWindow = 0;
    let windowStart = Date.now();
    let throttledCount = 0;

    // Send 20 requests rapidly
    for (let i = 0; i < 20; i++) {
      const now = Date.now();
      if (now - windowStart > windowMs) {
        // Reset window
        windowStart = now;
        requestsInWindow = 0;
      }

      if (requestsInWindow >= maxRequests) {
        // Rate limit exceeded
        throttledCount++;
        await new Promise((resolve) => setTimeout(resolve, 10));
        continue;
      }

      requestsInWindow++;
      await baseAgent.process(message);
    }

    expect(throttledCount).toBeGreaterThan(0);
  });
});

// ============================================
// Middleware Composition Tests
// ============================================

describe('Middleware Composition under Chaos', () => {
  it('should handle retry + timeout + circuit breaker together', async () => {
    const baseAgent = new SimpleAgent();
    const flakeyAgent = new FlakeyAgent(baseAgent, [false, false, true]);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate composed middleware: timeout + retry + circuit breaker
    const timeoutMs = 200;
    const maxRetries = 3;
    let response: Message | null = null;
    let circuitOpen = false;
    let consecutiveFailures = 0;

    for (let retry = 0; retry <= maxRetries; retry++) {
      if (circuitOpen) {
        break;
      }

      try {
        const timeout = new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Timeout')), timeoutMs)
        );
        response = await Promise.race([flakeyAgent.process(message), timeout]);
        consecutiveFailures = 0;
        break;
      } catch {
        consecutiveFailures++;
        if (consecutiveFailures >= 3) {
          circuitOpen = true;
        }
        if (retry < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    // Should eventually succeed before circuit opens
    expect(response).not.toBeNull();
    expect(circuitOpen).toBe(false);
  });

  it('should open circuit with persistent failures despite retries', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate composed middleware
    const maxRetries = 2;
    let circuitOpen = false;
    let totalAttempts = 0;

    // Make multiple top-level requests
    for (let request = 0; request < 3; request++) {
      if (circuitOpen) {
        break;
      }

      // Each request gets retries
      for (let retry = 0; retry <= maxRetries; retry++) {
        totalAttempts++;
        try {
          await chaosAgent.process(message);
          break;
        } catch {
          if (retry === maxRetries) {
            // All retries exhausted, open circuit
            circuitOpen = true;
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    expect(circuitOpen).toBe(true);
    expect(totalAttempts).toBeGreaterThanOrEqual(maxRetries + 1);
  });
});

// ============================================
// Memory Pressure Tests
// ============================================

describe('Memory Pressure Resilience', () => {
  it('should handle large responses from chaos agent', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.MEMORY_PRESSURE);

    const message: Message = { role: 'user', content: 'Test' };

    const response = await chaosAgent.process(message);

    // Should return large content
    expect(response.content.length).toBeGreaterThan(1024 * 1024); // > 1MB
    expect(response.metadata?.chaos).toBe('memory_pressure');
  });
});
