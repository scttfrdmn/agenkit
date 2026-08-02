/**
 * Network Failure Chaos Tests
 *
 * Tests system resilience under various network failure conditions:
 * - Connection timeouts
 * - Connection refused
 * - Connection drops
 * - Intermittent connectivity
 *
 * These tests validate that the system handles network failures gracefully
 * and that resilience middleware (retry, circuit breaker, timeout) works correctly.
 */

import { describe, it, expect } from 'vitest';
import type { Message } from '../../core/interfaces';
import { ChaosAgent, ChaosMode, SimpleAgent } from './chaos_agents';
import { atLeastMs } from '../support/timing';

// ============================================
// Connection Timeout Tests
// ============================================

describe('Connection Timeout', () => {
  it('should timeout when connection hangs', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.TIMEOUT);

    const message: Message = { role: 'user', content: 'Test timeout' };

    // Should timeout after configured duration
    await expect(
      Promise.race([
        chaosAgent.process(message),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 100)),
      ])
    ).rejects.toThrow('Timeout');
  });

  it('should timeout on each retry attempt', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.TIMEOUT);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate retry logic
    const maxRetries = 3;
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      await expect(
        Promise.race([
          chaosAgent.process(message),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 100)),
        ])
      ).rejects.toThrow('Timeout');
    }

    // All retries should have been attempted
    expect(chaosAgent.getStats().requestCount).toBe(maxRetries);
  });

  it('should succeed for slow responses within timeout', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 50, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Should succeed with 200ms timeout
    const start = Date.now();
    const response = await Promise.race([
      chaosAgent.process(message),
      new Promise<Message>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 200)),
    ]);
    const elapsed = Date.now() - start;

    expect(response.content).toBe('Processed: Test');
    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(50));
    expect(elapsed).toBeLessThan(200);
  });
});

// ============================================
// Connection Refused Tests
// ============================================

describe('Connection Refused', () => {
  it('should throw connection refused error', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    await expect(chaosAgent.process(message)).rejects.toThrow(/ECONNREFUSED.*Connection refused/);
    expect(chaosAgent.getStats().failureCount).toBe(1);
  });

  it('should fail all retry attempts with connection refused', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate retry logic
    const maxRetries = 3;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        await chaosAgent.process(message);
        break;
      } catch (e) {
        lastError = e as Error;
        if (attempt < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    // All attempts should fail
    expect(lastError).not.toBeNull();
    expect(chaosAgent.getStats().requestCount).toBe(maxRetries + 1);
    expect(chaosAgent.getStats().failureCount).toBe(maxRetries + 1);
  });
});

// ============================================
// Connection Drop Tests
// ============================================

describe('Connection Drop', () => {
  it('should throw connection dropped error', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_DROP);

    const message: Message = { role: 'user', content: 'Test' };

    await expect(chaosAgent.process(message)).rejects.toThrow(/ECONNRESET.*Connection dropped/);
  });

  it('should recover after connection drop', async () => {
    const baseAgent = new SimpleAgent();

    // First request: connection drops
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_DROP);
    const message: Message = { role: 'user', content: 'Test' };

    await expect(chaosAgent.process(message)).rejects.toThrow(/Connection dropped/);

    // Second request: connection works (use normal agent)
    const response = await baseAgent.process(message);
    expect(response.content).toBe('Processed: Test');
  });
});

// ============================================
// Intermittent Connectivity Tests
// ============================================

describe('Intermittent Connectivity', () => {
  it('should fail approximately 50% of requests with 0.5 failure rate', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0.5, 0, ChaosMode.INTERMITTENT);

    const message: Message = { role: 'user', content: 'Test' };

    // Run 100 requests
    let successes = 0;
    let failures = 0;

    for (let i = 0; i < 100; i++) {
      try {
        await chaosAgent.process(message);
        successes++;
      } catch {
        failures++;
      }
    }

    // Should be roughly 50/50 split (allow ±20% variance)
    expect(successes).toBeGreaterThanOrEqual(30);
    expect(successes).toBeLessThanOrEqual(70);
    expect(failures).toBeGreaterThanOrEqual(30);
    expect(failures).toBeLessThanOrEqual(70);

    // Verify stats
    const stats = chaosAgent.getStats();
    expect(stats.requestCount).toBe(100);
    expect(stats.failureCount).toBeGreaterThanOrEqual(30);
    expect(stats.failureCount).toBeLessThanOrEqual(70);
  });

  it('should eventually succeed with retries despite high failure rate', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0.7, 0, ChaosMode.INTERMITTENT);

    // Fail a fixed 8 of the 11 attempts below rather than each with probability
    // 0.7. The assertion is that the retry loop eventually succeeds, which under
    // random failures is only probabilistic — see the corrected arithmetic
    // below (#658).
    chaosAgent.setFailFirstN(8);

    const message: Message = { role: 'user', content: 'Test' };

    // Retry up to 10 times - should eventually succeed
    const maxRetries = 10;
    let response: Message | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        response = await chaosAgent.process(message);
        break;
      } catch {
        if (attempt < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    // Now guaranteed. This previously relied on chance and justified it as
    // "probability of all failing: 0.7^11 ≈ 0.2%" — the arithmetic was off by a
    // factor of ten: 0.7^11 is 1.98%, i.e. roughly 1 run in 50, not 1 in 500.
    expect(response).not.toBeNull();
    expect(response?.content).toBe('Processed: Test');
  });
});

// ============================================
// Random Error Tests
// ============================================

describe('Random Errors', () => {
  it('should fail approximately 30% of requests with 0.3 failure rate', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0.3, 0, ChaosMode.RANDOM_ERROR);

    const message: Message = { role: 'user', content: 'Test' };

    // Run 100 requests
    let successes = 0;
    let errors = 0;

    for (let i = 0; i < 100; i++) {
      try {
        const response = await chaosAgent.process(message);
        expect(response.content).toBe('Processed: Test');
        successes++;
      } catch (e) {
        expect((e as Error).message).toContain('Random failure');
        errors++;
      }
    }

    // Should be roughly 70/30 split (allow ±15% variance)
    expect(successes).toBeGreaterThanOrEqual(55);
    expect(successes).toBeLessThanOrEqual(85);
    expect(errors).toBeGreaterThanOrEqual(15);
    expect(errors).toBeLessThanOrEqual(45);
  });
});

// ============================================
// Concurrent Requests
// ============================================

describe('Concurrent Requests with Network Chaos', () => {
  it('should handle concurrent requests with intermittent failures', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0.5, 0, ChaosMode.INTERMITTENT);

    const message: Message = { role: 'user', content: 'Test' };

    // 20 concurrent requests
    const results = await Promise.allSettled(
      Array.from({ length: 20 }, () => chaosAgent.process(message))
    );

    // Count successes and failures
    const successes = results.filter((r) => r.status === 'fulfilled').length;
    const failures = results.filter((r) => r.status === 'rejected').length;

    expect(successes + failures).toBe(20);
    // With 50% failure rate, expect ~10 successes (allow ±7 variance)
    expect(successes).toBeGreaterThanOrEqual(3);
    expect(successes).toBeLessThanOrEqual(17);
  });
});
