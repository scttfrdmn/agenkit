/**
 * Service Unavailability Chaos Tests
 *
 * Tests system behavior when services are unavailable:
 * - Agent crashes
 * - Service restarts
 * - Gradual degradation
 * - Complete service failure
 *
 * These tests validate graceful degradation and recovery patterns.
 */

import { describe, it, expect } from 'vitest';
import type { Message } from '../../core/interfaces';
import { ChaosAgent, ChaosMode, SimpleAgent } from './chaos_agents';

// ============================================
// Agent Crash Tests
// ============================================

describe('Agent Crashes', () => {
  it('should throw error when agent crashes', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CRASH);

    const message: Message = { role: 'user', content: 'Test' };

    await expect(chaosAgent.process(message)).rejects.toThrow('Agent crashed (simulated)');
    expect(chaosAgent.getStats().failureCount).toBe(1);
  });

  it('should crash after N successful requests', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.NONE);
    chaosAgent.setCrashAfter(3);

    const message: Message = { role: 'user', content: 'Test' };

    // First 3 requests should succeed
    for (let i = 0; i < 3; i++) {
      const response = await chaosAgent.process(message);
      expect(response.content).toBe('Processed: Test');
    }

    // 4th request should crash
    await expect(chaosAgent.process(message)).rejects.toThrow('Agent crashed (simulated)');
    expect(chaosAgent.getStats().requestCount).toBe(4);
  });

  it('should handle crash with fallback agent', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CRASH);
    const fallbackAgent = new SimpleAgent('fallback-agent');

    const message: Message = { role: 'user', content: 'Test' };

    // Primary agent crashes
    let response: Message | null = null;
    try {
      response = await chaosAgent.process(message);
    } catch {
      // Fallback to backup agent
      response = await fallbackAgent.process(message);
    }

    expect(response).not.toBeNull();
    expect(response?.content).toBe('Processed: Test');
    expect(response?.metadata?.agent).toBe('fallback-agent');
  });
});

// ============================================
// Service Restart Tests
// ============================================

describe('Service Restarts', () => {
  it('should handle agent restart pattern', async () => {
    const baseAgent = new SimpleAgent();
    const chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.NONE);

    const message: Message = { role: 'user', content: 'Test' };

    // Process requests normally
    await chaosAgent.process(message);
    await chaosAgent.process(message);
    expect(chaosAgent.getStats().requestCount).toBe(2);

    // Simulate restart by creating new instance
    const restartedAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.NONE);

    // Should start fresh
    const response = await restartedAgent.process(message);
    expect(response.content).toBe('Processed: Test');
    expect(restartedAgent.getStats().requestCount).toBe(1);
  });

  it('should recover after crash and restart', async () => {
    const baseAgent = new SimpleAgent();
    let chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.NONE);
    chaosAgent.setCrashAfter(2);

    const message: Message = { role: 'user', content: 'Test' };

    // Process 2 requests
    await chaosAgent.process(message);
    await chaosAgent.process(message);

    // 3rd request crashes
    await expect(chaosAgent.process(message)).rejects.toThrow('Agent crashed');

    // Simulate restart
    chaosAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.NONE);

    // Should work after restart
    const response = await chaosAgent.process(message);
    expect(response.content).toBe('Processed: Test');
  });
});

// ============================================
// Gradual Degradation Tests
// ============================================

describe('Gradual Degradation', () => {
  it('should degrade gradually with increasing failure rate', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Simulate gradual degradation by increasing failure rate
    const degradationStages = [
      { rate: 0.1, label: 'healthy' },
      { rate: 0.3, label: 'degraded' },
      { rate: 0.7, label: 'critical' },
    ];

    for (const stage of degradationStages) {
      const chaosAgent = new ChaosAgent(baseAgent, stage.rate, 0, ChaosMode.RANDOM_ERROR);

      let successes = 0;
      const attempts = 50;

      for (let i = 0; i < attempts; i++) {
        try {
          await chaosAgent.process(message);
          successes++;
        } catch {
          // Expected failures
        }
      }

      const successRate = successes / attempts;
      const expectedSuccess = 1 - stage.rate;

      // Allow ±20% variance
      expect(successRate).toBeGreaterThan(expectedSuccess - 0.2);
      expect(successRate).toBeLessThan(expectedSuccess + 0.2);
    }
  });

  it('should handle slow degradation over time', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Simulate increasing delays
    const delays = [10, 30, 100];

    for (const delay of delays) {
      const slowAgent = new ChaosAgent(baseAgent, 0, delay, ChaosMode.SLOW_RESPONSE);

      const start = Date.now();
      await slowAgent.process(message);
      const elapsed = Date.now() - start;

      expect(elapsed).toBeGreaterThanOrEqual(delay - 5);
      expect(elapsed).toBeLessThan(delay + 50);
    }
  });
});

// ============================================
// Complete Service Failure Tests
// ============================================

describe('Complete Service Failure', () => {
  it('should fail all requests when service is completely down', async () => {
    const baseAgent = new SimpleAgent();
    const downAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    // All requests should fail
    for (let i = 0; i < 5; i++) {
      await expect(downAgent.process(message)).rejects.toThrow(/Connection refused/);
    }

    expect(downAgent.getStats().failureCount).toBe(5);
    expect(downAgent.getStats().failureRate).toBe(1.0);
  });

  it('should handle service recovery after complete failure', async () => {
    const baseAgent = new SimpleAgent();
    const message: Message = { role: 'user', content: 'Test' };

    // Service is down
    const downAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);
    await expect(downAgent.process(message)).rejects.toThrow(/Connection refused/);

    // Service recovers
    const recoveredAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.NONE);
    const response = await recoveredAgent.process(message);

    expect(response.content).toBe('Processed: Test');
  });

  it('should exhaust retry budget on complete failure', async () => {
    const baseAgent = new SimpleAgent();
    const downAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate retry with exponential backoff
    const maxRetries = 3;
    let attempts = 0;
    let lastError: Error | null = null;

    for (let retry = 0; retry <= maxRetries; retry++) {
      attempts++;
      try {
        await downAgent.process(message);
        break;
      } catch (e) {
        lastError = e as Error;
        if (retry < maxRetries) {
          // Exponential backoff: 10ms, 20ms, 40ms
          await new Promise((resolve) => setTimeout(resolve, 10 * Math.pow(2, retry)));
        }
      }
    }

    expect(attempts).toBe(maxRetries + 1);
    expect(lastError).not.toBeNull();
    expect(downAgent.getStats().requestCount).toBe(maxRetries + 1);
    expect(downAgent.getStats().failureRate).toBe(1.0);
  });
});

// ============================================
// Health Check Tests
// ============================================

describe('Health Checks', () => {
  it('should detect unhealthy agent via failure rate', async () => {
    const baseAgent = new SimpleAgent();
    const unhealthyAgent = new ChaosAgent(baseAgent, 0.8, 0, ChaosMode.RANDOM_ERROR);

    const message: Message = { role: 'user', content: 'Test' };

    // Process requests to collect stats
    for (let i = 0; i < 20; i++) {
      try {
        await unhealthyAgent.process(message);
      } catch {
        // Expected failures
      }
    }

    const stats = unhealthyAgent.getStats();
    expect(stats.failureRate).toBeGreaterThan(0.6); // Above unhealthy threshold
  });

  it('should mark agent as healthy when failure rate is low', async () => {
    const baseAgent = new SimpleAgent();
    const healthyAgent = new ChaosAgent(baseAgent, 0.05, 0, ChaosMode.RANDOM_ERROR);

    const message: Message = { role: 'user', content: 'Test' };

    // Process requests
    for (let i = 0; i < 20; i++) {
      try {
        await healthyAgent.process(message);
      } catch {
        // Expected occasional failures
      }
    }

    const stats = healthyAgent.getStats();
    expect(stats.failureRate).toBeLessThan(0.2); // Below healthy threshold
  });
});
