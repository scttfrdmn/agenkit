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

import { describe, it, expect, vi } from 'vitest';
import type { Message } from '../../core/interfaces';
import { ChaosAgent, ChaosMode, SimpleAgent } from './chaos_agents';
import { atLeastMs } from '../support/timing';

// ============================================
// Basic Slow Response Tests
// ============================================

describe('Slow Responses', () => {
  it('should complete slow response within timeout', async () => {
    const baseAgent = new SimpleAgent();
    // Delay magnitude reduced 100ms -> 30ms: the test asserts the response
    // arrives no sooner than the injected delay (real wall-clock latency is
    // respected), which holds at any positive magnitude.
    const slowAgent = new ChaosAgent(baseAgent, 0, 30, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    const start = Date.now();
    const response = await slowAgent.process(message);
    const elapsed = Date.now() - start;

    expect(response.content).toBe('Processed: Test');
    expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(30));
  });

  it('should timeout on excessively slow response', async () => {
    const baseAgent = new SimpleAgent();
    const slowAgent = new ChaosAgent(baseAgent, 0, 500, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Pure behavior assertion (timeout fires before the slow agent resolves),
    // so fake timers make this instant without changing what is asserted.
    vi.useFakeTimers();
    try {
      // Simulate timeout middleware (200ms timeout)
      const timeout = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), 200)
      );

      const assertion = expect(
        Promise.race([slowAgent.process(message), timeout])
      ).rejects.toThrow('Request timeout');
      await vi.advanceTimersByTimeAsync(200);
      await assertion;
    } finally {
      vi.useRealTimers();
    }
  });

  it('should measure response time accurately', async () => {
    // Magnitudes scaled down 5x ([50,100,200] -> [10,20,40]); the test still
    // proves measured latency tracks the injected delay within tolerance.
    const delays = [10, 20, 40];

    for (const delay of delays) {
      const baseAgent = new SimpleAgent();
      const slowAgent = new ChaosAgent(baseAgent, 0, delay, ChaosMode.SLOW_RESPONSE);

      const message: Message = { role: 'user', content: 'Test' };

      const start = Date.now();
      await slowAgent.process(message);
      const elapsed = Date.now() - start;

      // Allow generous upper variance (scheduling jitter is a larger fraction
      // of these smaller delays).
      expect(elapsed).toBeGreaterThanOrEqual(delay - 5);
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

    // Simulate gradual degradation. Magnitudes scaled down (10/50/150 ->
    // 10/30/60); the assertion is purely that each stage is slower than the
    // last, which the ordering preserves while spacing stays > jitter.
    const degradationStages = [10, 30, 60];

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

    // Collect 100 samples with varying delays. Tiers scaled down from
    // 10/50/200 to 1/20/60 to cut ~3s of real sleeps; the percentile logic
    // under test is unchanged. Tier gaps are kept wide (1 vs 20 vs 60ms) so
    // that scheduling jitter (a few ms) cannot blur one tier into the next.
    //
    // The fast tier holds 60 of the 100 samples, not 50. With an even 50 the
    // median landed on the *last* fast sample, so a single fast request that
    // jittered above 20ms displaced it and p50 became a mid-tier 20 — `expected
    // 20 to be less than 15`, seen once in 40 full-suite runs (#658). At 60 the
    // median has ten samples of slack.
    for (let i = 0; i < 100; i++) {
      // Simulate realistic latency distribution: mostly fast, some slow
      const delay = i < 60 ? 1 : i < 95 ? 20 : 60;
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

    expect(p50).toBeLessThan(15); // Median in fast tier (~1ms + jitter margin)
    expect(p95).toBeGreaterThanOrEqual(atLeastMs(20)); // p95 includes the mid tier (20ms)
    expect(p99).toBeGreaterThanOrEqual(atLeastMs(60)); // p99 includes the slowest tier
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

    // Normal latency (5ms). Spike reduced 500 -> 200; the assertion is only
    // that the spike is >10x the normal latency. The spike is kept at 200ms so
    // that even if the ~5ms normal request jitters up to ~15ms, 10x (~150ms)
    // still sits below the spike.
    const normalAgent = new ChaosAgent(baseAgent, 0, 5, ChaosMode.SLOW_RESPONSE);
    const start1 = Date.now();
    await normalAgent.process(message);
    const normal = Date.now() - start1;

    // Latency spike (200ms)
    const spikeAgent = new ChaosAgent(baseAgent, 0, 200, ChaosMode.SLOW_RESPONSE);
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

    // Pure behavior assertion (timeout fires before the spike resolves) ->
    // fake timers, no real wait, same assertion.
    vi.useFakeTimers();
    try {
      // Timeout before spike completes
      const timeout = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Spike timeout')), 100)
      );

      const assertion = expect(
        Promise.race([spikeAgent.process(message), timeout])
      ).rejects.toThrow('Spike timeout');
      await vi.advanceTimersByTimeAsync(100);
      await assertion;
    } finally {
      vi.useRealTimers();
    }
  });

  it('should recover after latency spike', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Spike reduced 300 -> 100, recovery delay 10 -> 5. Thresholds adjusted to
    // match while still proving the spike is far slower than the recovered
    // request (spike > 50ms, recovered < 30ms).
    const spikeAgent = new ChaosAgent(baseAgent, 0, 100, ChaosMode.SLOW_RESPONSE);
    const start1 = Date.now();
    await spikeAgent.process(message);
    const spike = Date.now() - start1;

    // Recovery
    const normalAgent = new ChaosAgent(baseAgent, 0, 5, ChaosMode.SLOW_RESPONSE);
    const start2 = Date.now();
    await normalAgent.process(message);
    const recovered = Date.now() - start2;

    expect(spike).toBeGreaterThan(50);
    expect(recovered).toBeLessThan(30);
  });
});

// ============================================
// Concurrent Slow Request Tests
// ============================================

describe('Concurrent Slow Requests', () => {
  it('should handle multiple concurrent slow requests', async () => {
    const baseAgent = new SimpleAgent();
    // Delay reduced 100 -> 50; the test proves the 10 requests run
    // concurrently (total ~one delay, not ten), which holds at any magnitude.
    const slowAgent = new ChaosAgent(baseAgent, 0, 50, ChaosMode.SLOW_RESPONSE);

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

    // Should complete in ~50ms (concurrent), not ~500ms (sequential)
    expect(elapsed).toBeLessThan(150);
  });

  it('should timeout some concurrent requests based on timeout policy', async () => {
    const baseAgent = new SimpleAgent();
    // Magnitudes scaled down ~2.5x (agent 150 -> 60, timeouts 100/200 ->
    // 40/80). The ordering — and thus which races resolve vs reject — is
    // preserved: the 80ms timeout beats the 60ms agent, the 40ms ones don't.
    const slowAgent = new ChaosAgent(baseAgent, 0, 60, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send concurrent requests with varying timeouts
    const requests = [
      Promise.race([
        slowAgent.process(message),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 40)),
      ]),
      Promise.race([
        slowAgent.process(message),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 80)),
      ]),
      Promise.race([
        slowAgent.process(message),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Timeout')), 40)),
      ]),
    ];

    const results = await Promise.allSettled(requests);

    const successes = results.filter((r) => r.status === 'fulfilled');
    const timeouts = results.filter((r) => r.status === 'rejected');

    // Requests with 80ms timeout should succeed, 40ms should timeout
    expect(successes).toHaveLength(1);
    expect(timeouts).toHaveLength(2);
  });

  it('should not exhaust resources with many slow concurrent requests', async () => {
    const baseAgent = new SimpleAgent();
    // Delay reduced 50 -> 25; still proves 100 requests run concurrently.
    const slowAgent = new ChaosAgent(baseAgent, 0, 25, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send 100 concurrent slow requests
    const start = Date.now();
    const results = await Promise.all(
      Array.from({ length: 100 }, () => slowAgent.process(message))
    );
    const elapsed = Date.now() - start;

    expect(results).toHaveLength(100);
    // Should complete reasonably fast (concurrent execution)
    expect(elapsed).toBeLessThan(150);
  });
});

// ============================================
// Adaptive Timeout Tests
// ============================================

describe('Adaptive Timeout Behavior', () => {
  it('should increase timeout for consistently slow responses', async () => {
    const baseAgent = new SimpleAgent();
    // Magnitudes scaled down ~2.5x (agent 150 -> 60, timeout window
    // 100/50/300 -> 40/20/120). The adaptive loop still must raise the timeout
    // at least once before the 60ms agent fits, preserving the assertion.
    const slowAgent = new ChaosAgent(baseAgent, 0, 60, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Start with aggressive timeout
    let timeout = 40;
    const timeoutIncrement = 20;
    const maxTimeout = 120;

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
    expect(timeout).toBeGreaterThan(40); // Timeout was increased
    expect(timeout).toBeLessThanOrEqual(maxTimeout);
  });

  it('should reduce timeout for fast responses', async () => {
    const baseAgent = new SimpleAgent();
    const fastAgent = new ChaosAgent(baseAgent, 0, 10, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Start with conservative timeout
    const timeout = 500;
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
    // Delay reduced 100 -> 50; still proves concurrent (~one delay) execution.
    const slowAgent = new ChaosAgent(baseAgent, 0, 50, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Send requests sequentially (simulating queue)
    const queue: Promise<Message>[] = [];

    for (let i = 0; i < 5; i++) {
      queue.push(slowAgent.process(message));
    }

    const start = Date.now();
    await Promise.all(queue);
    const elapsed = Date.now() - start;

    // Should process concurrently (~50ms), not sequentially (~250ms)
    expect(elapsed).toBeLessThan(150);
  });

  it('should detect queue buildup from slow responses', async () => {
    const baseAgent = new SimpleAgent();
    const agentDelayMs = 20;
    const enqueueGapMs = 5;
    const requestCount = 8;
    const slowAgent = new ChaosAgent(baseAgent, 0, agentDelayMs, ChaosMode.SLOW_RESPONSE);

    const message: Message = { role: 'user', content: 'Test' };

    // Requests are drained by a single serialized worker. This matters: the
    // previous version fired all ten concurrently, so there was no queue and no
    // buildup to detect — every request waited one agent delay and nothing else.
    // Worse, the bias ran against the assertion, because the early entries were
    // enqueued while the loop was still running and so measured *longer* than
    // the late ones. It compensated with a 1ms fudge and still failed ~1 run in
    // 4 (#658). Serializing the drain is what makes wait time actually grow:
    // request i waits agentDelay*(i+1) to be served but was enqueued at
    // gap*i, so its wait grows by (agentDelay - gap) per position.
    const queue: Array<{ enqueued: number; completed: number }> = [];
    let worker: Promise<void> = Promise.resolve();

    for (let i = 0; i < requestCount; i++) {
      const enqueued = Date.now();
      worker = worker.then(async () => {
        await slowAgent.process(message);
        queue.push({ enqueued, completed: Date.now() });
      });

      await new Promise((resolve) => setTimeout(resolve, enqueueGapMs));
    }

    // Await the drain rather than sleeping a fixed interval. The old fixed wait
    // could expire before the queue emptied, and the entries that had not
    // completed were silently filtered out of the measurement.
    await worker;
    expect(queue).toHaveLength(requestCount);

    const waitTimes = queue.map((e) => e.completed - e.enqueued);

    // Later requests should have longer wait times (queue buildup).
    const earlyWait = waitTimes.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
    const lateWait = waitTimes.slice(-3).reduce((a, b) => a + b, 0) / 3;

    // Expected separation is (agentDelay - enqueueGap) * 5 = 75ms, so this is a
    // wide margin rather than a fudge factor.
    expect(lateWait).toBeGreaterThan(earlyWait);
  });
});
