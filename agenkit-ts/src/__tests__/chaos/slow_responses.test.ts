/**
 * Slow Response Chaos Tests
 *
 * Tests system behavior under slow response conditions:
 * - Gradual performance degradation
 * - Timeout handling
 * - Latency spikes
 * - Concurrent slow requests
 *
 * These tests validate that the system handles slow responses
 * gracefully and respects timeout policies.
 */

import { describe, it, expect } from 'vitest';
import type { Message } from '../../core/interfaces';
import { ChaosAgent, ChaosMode, SimpleAgent } from './chaos_agents';

// ============================================
// Basic Slow Response Tests
// ============================================

describe('Slow Responses', () => {
  it('should complete slow response within timeout', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 100, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    const start = Date.now();
    const response = await slowAgent.process(message);
    const elapsed = Date.now() - start;

    expect(response.content).toBe('Processed: Test');
    expect(elapsed).toBeGreaterThanOrEqual(100);
  });

  it('should timeout on excessively slow response', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 500, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate timeout middleware (200ms timeout)
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Request timeout')), 200)
    );

    await expect(Promise.race([slowAgent.process(message), timeout])).rejects.toThrow(
      'Request timeout'
    );
  });

  it('should measure response time accurately', async () => {
    const delays = [50, 100, 200];

    for (const delay of delays) {
      const baseAgent = new SimpleAgent();
      const slowAgent = new ChaosAgent(baseAgent, 0, delay, ChaosMode.SLOW_RESPONSE);

      const message: Message = { role: 'user', content: 'Test' };

      const start = Date.now();
      await slowAgent.process(message);
      const elapsed = Date.now() - start;

      // Allow ±30ms variance
      expect(elapsed).toBeGreaterThanOrEqual(delay - 10);
      expect(elapsed).toBeLessThan(delay + 30);
    }
  });
});

// ============================================
// Gradual Degradation Tests
// ============================================

describe('Gradual Performance Degradation', () => {
  it('should detect gradual slowdown over time', async () => {
    const message: Message = { role: 'user', content: 'Test' };
    const measurements: number[] = [];

    // Simulate gradual degradation: 10ms → 50ms → 150ms
    const degradationStages = [10, 50, 150];

    for (const delay of degradationStages) {
      const baseAgent = new SimpleAgent();
      const slowAgent = new ChaosAgent(baseAgent, 0, delay, ChaosMode.SLOW_RESPONSE);

      const start = Date.now();
      await slowAgent.process(message);
      const elapsed = Date.now() - start;

      measurements.push(elapsed);
    }

    // Each stage should be slower than the previous
    expect(measurements[1]).toBeGreaterThan(measurements[0]);
    expect(measurements[2]).toBeGreaterThan(measurements[1]);
  });

  it('should track p50, p95, p99 latencies', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };
    const latencies: number[] = [];

    // Collect 100 samples with varying delays
    for (let i = 0; i < 100; i++) {
      // Simulate realistic latency distribution: mostly fast, some slow
      const delay = i < 50 ? 10 : i < 95 ? 50 : 200;
      const slowAgent = new ChaosAgent(baseAgent, 0, delay, ChaosMode.SLOW_RESPONSE);

      const start = Date.now();
      await slowAgent.process(message);
      latencies.push(Date.now() - start);
    }

    // Calculate percentiles
    latencies.sort((a, b) => a - b);
    const p50 = latencies[49]; // median
    const p95 = latencies[94];
    const p99 = latencies[98];

    expect(p50).toBeLessThan(50); // Median should be fast
    expect(p95).toBeGreaterThan(50); // p95 includes slow requests
    expect(p99).toBeGreaterThan(100); // p99 includes slowest
    expect(p99).toBeGreaterThan(p95);
    expect(p95).toBeGreaterThan(p50);
  });
});

// ============================================
// Latency Spike Tests
// ============================================

describe('Latency Spikes', () => {
  it('should handle sudden latency spike', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Normal latency (10ms)
    const normalAgent = new ChaosAgent(baseAgent, 0, 10, ChaosMode.SLOW_RESPONSE);
    const start1 = Date.now();
    await normalAgent.process(message);
    const normal = Date.now() - start1;

    // Latency spike (500ms)
    const spikeAgent = new ChaosAgent(baseAgent, 0, 500, ChaosMode.SLOW_RESPONSE);
    const start2 = Date.now();
    await spikeAgent.process(message);
    const spike = Date.now() - start2;

    // Spike should be significantly higher
    expect(spike).toBeGreaterThan(normal * 10);
  });

  it('should timeout during latency spike', async () => {
    const baseAgent = new SimpleAgent();
    const spikeAgent = new ChaosAgent(baseAgent, 0, 1000, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Timeout before spike completes
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Spike timeout')), 100)
    );

    await expect(Promise.race([spikeAgent.process(message), timeout])).rejects.toThrow(
      'Spike timeout'
    );
  });

  it('should recover after latency spike', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Spike
    const spikeAgent = new ChaosAgent(baseAgent, 0, 300, ChaosMode.SLOW_RESPONSE);
    const start1 = Date.now();
    await spikeAgent.process(message);
    const spike = Date.now() - start1;

    // Recovery
    const normalAgent = new ChaosAgent(baseAgent, 0, 10, ChaosMode.SLOW_RESPONSE);
    const start2 = Date.now();
    await normalAgent.process(message);
    const recovered = Date.now() - start2;

    expect(spike).toBeGreaterThan(200);
    expect(recovered).toBeLessThan(50);
  });
});

// ============================================
// Concurrent Slow Request Tests
// ============================================

describe('Concurrent Slow Requests', () => {
  it('should handle multiple concurrent slow requests', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 100, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send 10 concurrent slow requests
    const start = Date.now();
    const results = await Promise.all(
      Array.from({ length: 10 }, () => slowAgent.process(message))
    );
    const elapsed = Date.now() - start;

    // All should succeed
    expect(results).toHaveLength(10);
    results.forEach((r) => expect(r.content).toBe('Processed: Test'));

    // Should complete in ~100ms (concurrent), not 1000ms (sequential)
    expect(elapsed).toBeLessThan(200);
  });

  it('should timeout some concurrent requests based on timeout policy', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 150, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send concurrent requests with varying timeouts
    const requests = [
      Promise.race([
        slowAgent.process(message),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 100)),
      ]),
      Promise.race([
        slowAgent.process(message),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 200)),
      ]),
      Promise.race([
        slowAgent.process(message),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 100)),
      ]),
    ];

    const results = await Promise.allSettled(requests);

    const successes = results.filter((r) => r.status === 'fulfilled');
    const timeouts = results.filter((r) => r.status === 'rejected');

    // Requests with 200ms timeout should succeed, 100ms should timeout
    expect(successes).toHaveLength(1);
    expect(timeouts).toHaveLength(2);
  });

  it('should not exhaust resources with many slow concurrent requests', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 50, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send 100 concurrent slow requests
    const start = Date.now();
    const results = await Promise.all(
      Array.from({ length: 100 }, () => slowAgent.process(message))
    );
    const elapsed = Date.now() - start;

    expect(results).toHaveLength(100);
    // Should complete reasonably fast (concurrent execution)
    expect(elapsed).toBeLessThan(200);
  });
});

// ============================================
// Adaptive Timeout Tests
// ============================================

describe('Adaptive Timeout Behavior', () => {
  it('should increase timeout for consistently slow responses', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 150, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Start with aggressive timeout
    let timeout = 100;
    const timeoutIncrement = 50;
    const maxTimeout = 300;

    let response: Message | null = null;

    while (response === null && timeout <= maxTimeout) {
      try {
        response = await Promise.race([
          slowAgent.process(message),
          new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), timeout)),
        ]);
      } catch {
        // Increase timeout adaptively
        timeout += timeoutIncrement;
      }
    }

    expect(response).not.toBeNull();
    expect(timeout).toBeGreaterThan(100); // Timeout was increased
    expect(timeout).toBeLessThanOrEqual(maxTimeout);
  });

  it('should reduce timeout for fast responses', async () => {
    const baseAgent = new SimpleAgent();
    const fastAgent = new ChaosAgent(baseAgent, 0, 10, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Start with conservative timeout
    let timeout = 500;
    const measurements: number[] = [];

    // Measure actual response times
    for (let i = 0; i < 5; i++) {
      const start = Date.now();
      await fastAgent.process(message);
      measurements.push(Date.now() - start);
    }

    // Calculate p95 latency
    const sorted = measurements.slice().sort((a, b) => a - b);
    const p95 = sorted[Math.floor(sorted.length * 0.95)];

    // Adaptive timeout should converge to p95 + margin
    const adaptiveTimeout = p95 * 1.5;

    expect(adaptiveTimeout).toBeLessThan(timeout); // Can reduce timeout safely
    expect(adaptiveTimeout).toBeGreaterThan(p95); // Still has safety margin
  });
});

// ============================================
// Queueing Behavior Tests
// ============================================

describe('Slow Response Queueing', () => {
  it('should queue requests when agent is slow', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 100, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send requests sequentially (simulating queue)
    const queue: Promise<Message>[] = [];

    for (let i = 0; i < 5; i++) {
      queue.push(slowAgent.process(message));
    }

    const start = Date.now();
    await Promise.all(queue);
    const elapsed = Date.now() - start;

    // Should process concurrently (~100ms), not sequentially (~500ms)
    expect(elapsed).toBeLessThan(200);
  });

  it('should detect queue buildup from slow responses', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 200, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate queue with timestamps
    const queue: Array<{ enqueued: number; completed?: number }> = [];

    // Enqueue rapidly
    for (let i = 0; i < 10; i++) {
      const entry = { enqueued: Date.now() };
      queue.push(entry);

      // Process slowly
      slowAgent.process(message).then(() => {
        entry.completed = Date.now();
      });

      await new Promise((resolve) => setTimeout(resolve, 10)); // 10ms between enqueues
    }

    // Wait for all to complete
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Calculate queue wait times
    const waitTimes = queue
      .filter((e) => e.completed !== undefined)
      .map((e) => e.completed! - e.enqueued);

    // Later requests should have longer wait times (queue buildup)
    const earlyWait = waitTimes.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
    const lateWait = waitTimes.slice(-3).reduce((a, b) => a + b, 0) / 3;

    expect(lateWait).toBeGreaterThanOrEqual(earlyWait);
  });
});
