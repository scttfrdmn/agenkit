/**
 * Partial Failures Chaos Tests
 *
 * Tests system behavior when parts of the system fail:
 * - Partial agent failures (some succeed, some fail)
 * - Multi-agent scenarios with mixed success
 * - Cascading failures
 * - Graceful degradation with fallbacks
 *
 * These tests validate that the system can continue operating
 * when some components fail.
 */

import { describe, it, expect } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { ChaosAgent, ChaosMode, FlakeyAgent, SimpleAgent } from './chaos_agents';

// ============================================
// Partial Agent Failure Tests
// ============================================

describe('Partial Agent Failures', () => {
  it('should handle some agents failing while others succeed', async () => {
    const baseAgent = new SimpleAgent();
    const healthyAgent = new SimpleAgent('healthy-agent');
    const failingAgent = new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED);

    const message: Message = { role: 'user', content: 'Test' };

    const results = await Promise.allSettled([
      healthyAgent.process(message),
      failingAgent.process(message),
      healthyAgent.process(message),
    ]);

    const successes = results.filter((r) => r.status === 'fulfilled');
    const failures = results.filter((r) => r.status === 'rejected');

    expect(successes).toHaveLength(2);
    expect(failures).toHaveLength(1);
  });

  it('should aggregate results from partially failing agents', async () => {
    const agent1 = new SimpleAgent('agent-1');
    const agent2 = new ChaosAgent(new SimpleAgent('agent-2'), 0, 0, ChaosMode.CONNECTION_DROP);
    const agent3 = new SimpleAgent('agent-3');

    const message: Message = { role: 'user', content: 'Test' };

    const results = await Promise.allSettled([
      agent1.process(message),
      agent2.process(message),
      agent3.process(message),
    ]);

    // Collect successful results
    const successfulResults = results
      .filter((r): r is PromiseFulfilledResult<Message> => r.status === 'fulfilled')
      .map((r) => r.value);

    expect(successfulResults).toHaveLength(2);
    expect(successfulResults[0].metadata?.agent).toBe('agent-1');
    expect(successfulResults[1].metadata?.agent).toBe('agent-3');
  });
});

// ============================================
// Multi-Agent Scenarios
// ============================================

describe('Multi-Agent Scenarios with Mixed Success', () => {
  it('should continue processing with majority of agents healthy', async () => {
    const message: Message = { role: 'user', content: 'Test' };

    // Create pool of agents (4 healthy, 1 failing)
    const agents: Agent[] = [
      new SimpleAgent('agent-1'),
      new SimpleAgent('agent-2'),
      new ChaosAgent(new SimpleAgent('agent-3'), 0, 0, ChaosMode.CONNECTION_REFUSED),
      new SimpleAgent('agent-4'),
      new SimpleAgent('agent-5'),
    ];

    const results = await Promise.allSettled(agents.map((agent) => agent.process(message)));

    const successes = results.filter((r) => r.status === 'fulfilled');
    const failures = results.filter((r) => r.status === 'rejected');

    expect(successes).toHaveLength(4); // 80% success rate
    expect(failures).toHaveLength(1);
  });

  it('should fail when majority of agents are unhealthy', async () => {
    const message: Message = { role: 'user', content: 'Test' };

    // Create pool of agents (2 healthy, 3 failing)
    const baseAgent = new SimpleAgent();
    const agents: Agent[] = [
      new SimpleAgent('agent-1'),
      new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_REFUSED),
      new ChaosAgent(baseAgent, 0, 0, ChaosMode.CONNECTION_DROP),
      new SimpleAgent('agent-2'),
      new ChaosAgent(baseAgent, 0, 0, ChaosMode.CRASH),
    ];

    const results = await Promise.allSettled(agents.map((agent) => agent.process(message)));

    const successes = results.filter((r) => r.status === 'fulfilled');
    const failures = results.filter((r) => r.status === 'rejected');

    expect(successes).toHaveLength(2); // Only 40% success
    expect(failures).toHaveLength(3);

    // Would trigger majority failure alert
    const successRate = successes.length / agents.length;
    expect(successRate).toBeLessThan(0.5);
  });
});

// ============================================
// Cascading Failure Tests
// ============================================

describe('Cascading Failures', () => {
  it('should prevent cascading failures with circuit breaker', async () => {
    const baseAgent = new SimpleAgent();
    const flakeyAgent = new FlakeyAgent(baseAgent, [false, false, false, true]);

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate circuit breaker
    let circuitOpen = false;
    let consecutiveFailures = 0;
    const failureThreshold = 2;
    let blockedRequests = 0;

    // Send requests
    for (let i = 0; i < 6; i++) {
      if (circuitOpen) {
        blockedRequests++;
        continue;
      }

      try {
        await flakeyAgent.process(message);
        consecutiveFailures = 0;
      } catch {
        consecutiveFailures++;
        if (consecutiveFailures >= failureThreshold) {
          circuitOpen = true;
        }
      }
    }

    // Circuit should open and block remaining requests
    expect(circuitOpen).toBe(true);
    expect(blockedRequests).toBeGreaterThan(0);
  });

  it('should isolate failures to prevent cascade', async () => {
    const message: Message = { role: 'user', content: 'Test' };

    // Simulate service mesh with isolated agents
    const services = {
      frontend: new SimpleAgent('frontend'),
      backend: new ChaosAgent(new SimpleAgent('backend'), 0, 0, ChaosMode.CONNECTION_REFUSED),
      database: new SimpleAgent('database'),
      cache: new SimpleAgent('cache'),
    };

    // Backend fails, but other services continue
    const results = await Promise.allSettled([
      services.frontend.process(message),
      services.backend.process(message),
      services.database.process(message),
      services.cache.process(message),
    ]);

    const successfulServices = results.filter((r) => r.status === 'fulfilled');

    // 3/4 services still working despite backend failure
    expect(successfulServices).toHaveLength(3);
  });
});

// ============================================
// Graceful Degradation Tests
// ============================================

describe('Graceful Degradation with Fallbacks', () => {
  it('should fallback to cache when primary agent fails', async () => {
    const primaryAgent = new ChaosAgent(
      new SimpleAgent('primary'),
      0,
      0,
      ChaosMode.CONNECTION_REFUSED
    );
    const cacheAgent = new SimpleAgent('cache');

    const message: Message = { role: 'user', content: 'Test' };

    // Try primary, fallback to cache
    let response: Message | null = null;
    let usedCache = false;

    try {
      response = await primaryAgent.process(message);
    } catch {
      response = await cacheAgent.process(message);
      usedCache = true;
    }

    expect(response).not.toBeNull();
    expect(usedCache).toBe(true);
    expect(response?.metadata?.agent).toBe('cache');
  });

  it('should degrade to read-only mode when writes fail', async () => {
    const writeAgent = new ChaosAgent(
      new SimpleAgent('write-agent'),
      0,
      0,
      ChaosMode.CONNECTION_REFUSED
    );
    const readAgent = new SimpleAgent('read-agent');

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate degraded mode
    let canWrite = true;

    try {
      await writeAgent.process(message);
    } catch {
      canWrite = false;
    }

    // Fall back to read-only
    let response: Message | null = null;
    if (!canWrite) {
      response = await readAgent.process(message);
    }

    expect(canWrite).toBe(false);
    expect(response).not.toBeNull();
    expect(response?.metadata?.agent).toBe('read-agent');
  });

  it('should use stale data when fresh data is unavailable', async () => {
    const freshAgent = new ChaosAgent(
      new SimpleAgent('fresh-data'),
      0,
      0,
      ChaosMode.CONNECTION_DROP
    );
    const staleAgent = new SimpleAgent('stale-data');

    const message: Message = { role: 'user', content: 'Test' };

    let response: Message | null = null;
    let usedStaleData = false;

    try {
      response = await freshAgent.process(message);
    } catch {
      response = await staleAgent.process(message);
      usedStaleData = true;
    }

    expect(response).not.toBeNull();
    expect(usedStaleData).toBe(true);
  });
});

// ============================================
// Partial Response Tests
// ============================================

describe('Partial Responses', () => {
  it('should handle intermittent failures in multi-step process', async () => {
    const step1 = new SimpleAgent('step-1');
    const step2 = new ChaosAgent(new SimpleAgent('step-2'), 0.5, 0, ChaosMode.INTERMITTENT);
    const step3 = new SimpleAgent('step-3');

    const message: Message = { role: 'user', content: 'Test' };

    // Try multi-step process with retries on step 2
    const result1 = await step1.process(message);
    expect(result1.content).toBe('Processed: Test');

    let result2: Message | null = null;
    const maxRetries = 5;

    for (let retry = 0; retry <= maxRetries; retry++) {
      try {
        result2 = await step2.process(result1);
        break;
      } catch {
        if (retry < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }
    }

    expect(result2).not.toBeNull();

    const result3 = await step3.process(result2!);
    // Each step adds "Processed: " prefix, so after 3 steps we have 3 prefixes
    expect(result3.content).toContain('Processed:');
  });
});

// ============================================
// Load Balancing with Failures
// ============================================

describe('Load Balancing with Partial Failures', () => {
  it('should route around failing agents in load balancer', async () => {
    const agents: Agent[] = [
      new SimpleAgent('agent-1'),
      new ChaosAgent(new SimpleAgent('agent-2'), 0, 0, ChaosMode.CONNECTION_REFUSED),
      new SimpleAgent('agent-3'),
    ];

    const message: Message = { role: 'user', content: 'Test' };

    // Simulate load balancer trying agents until success
    let response: Message | null = null;

    for (const agent of agents) {
      try {
        response = await agent.process(message);
        break;
      } catch {
        continue;
      }
    }

    expect(response).not.toBeNull();
    expect(['agent-1', 'agent-3']).toContain(response?.metadata?.agent);
  });

  it('should track agent health and route to healthy agents', async () => {
    const agents = [
      { agent: new SimpleAgent('agent-1'), healthy: true },
      {
        agent: new ChaosAgent(new SimpleAgent('agent-2'), 0, 0, ChaosMode.CONNECTION_REFUSED),
        healthy: true,
      },
      { agent: new SimpleAgent('agent-3'), healthy: true },
    ];

    const message: Message = { role: 'user', content: 'Test' };

    // Test health and mark unhealthy agents
    for (const entry of agents) {
      try {
        await entry.agent.process(message);
      } catch {
        entry.healthy = false;
      }
    }

    // Route only to healthy agents
    const healthyAgents = agents.filter((e) => e.healthy);

    expect(healthyAgents).toHaveLength(2);
    expect(healthyAgents.map((e) => e.agent.name)).toEqual(
      expect.arrayContaining(['agent-1', 'agent-3'])
    );
  });
});
