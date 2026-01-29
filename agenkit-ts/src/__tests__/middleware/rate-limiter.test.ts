/**
 * Tests for rate limiter middleware.
 *
 * Tests RateLimiterDecorator for token bucket rate limiting.
 */

import { describe, it, expect } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import { RateLimiterDecorator, RateLimitError } from '../../middleware/rate-limiter';

// Simple test agent
class TestAgent implements Agent {
  name = 'test-agent';
  capabilities = [];
  private callCount = 0;

  async process(message: Message): Promise<Message> {
    this.callCount++;
    return createMessage('assistant', `response ${this.callCount}`);
  }

  getCallCount(): number {
    return this.callCount;
  }
}

// ============================================
// Basic Rate Limiting Tests
// ============================================

describe('RateLimiterDecorator: Basic Functionality', () => {
  it('should allow requests up to capacity', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 10,
      capacity: 10,
    });

    const input = createMessage('user', 'test');

    // Should allow 10 requests immediately (burst capacity)
    for (let i = 0; i < 10; i++) {
      const result = await limiter.process(input);
      expect(result.content).toContain('response');
    }

    expect(agent.getCallCount()).toBe(10);
    expect(limiter.metrics.allowedRequests).toBe(10);
    expect(limiter.metrics.rejectedRequests).toBe(0);
  });

  it('should refill tokens over time', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 2, // 2 tokens per second
      capacity: 5,
    });

    const input = createMessage('user', 'test');

    // Use up all tokens
    for (let i = 0; i < 5; i++) {
      await limiter.process(input);
    }

    expect(limiter.metrics.currentTokens).toBeLessThan(1);

    // Wait 0.5 seconds -> should get ~1 new token
    await new Promise((resolve) => setTimeout(resolve, 500));

    const result = await limiter.process(input);
    expect(result.content).toContain('response');
    expect(agent.getCallCount()).toBe(6);
  });

  it('should wait for tokens when needed', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 5, // 5 tokens per second
      capacity: 5,
    });

    const input = createMessage('user', 'test');

    // Use all tokens
    for (let i = 0; i < 5; i++) {
      await limiter.process(input);
    }

    // Next request should wait ~200ms for 1 token at 5 tokens/sec
    const start = Date.now();
    await limiter.process(input);
    const elapsed = Date.now() - start;

    expect(elapsed).toBeGreaterThanOrEqual(100); // Allow some variance
    expect(limiter.metrics.totalWaitTime).toBeGreaterThan(0);
  });
});

// ============================================
// Burst Capacity Tests
// ============================================

describe('RateLimiterDecorator: Burst Capacity', () => {
  it('should allow burst with high capacity', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 2, // Slow rate
      capacity: 10, // But high burst capacity
    });

    const input = createMessage('user', 'test');

    // Should allow 10 immediate requests due to burst capacity
    for (let i = 0; i < 10; i++) {
      await limiter.process(input);
    }

    expect(agent.getCallCount()).toBe(10);
  });
});

// ============================================
// Multi-Token Requests Tests
// ============================================

describe('RateLimiterDecorator: Multi-Token Requests', () => {
  it('should consume multiple tokens per request', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 10,
      capacity: 10,
      tokensPerRequest: 5,
    });

    const input = createMessage('user', 'test');

    // Should allow only 2 requests (5 tokens each)
    await limiter.process(input);
    await limiter.process(input);

    expect(limiter.metrics.allowedRequests).toBe(2);
    expect(limiter.metrics.currentTokens).toBeLessThan(1);
  });
});

// ============================================
// Max Wait Timeout Tests
// ============================================

describe('RateLimiterDecorator: Max Wait Timeout', () => {
  it('should reject if wait time exceeds maxWaitTimeoutMs', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 2, // 2 tokens per second
      capacity: 5,
      maxWaitTimeoutMs: 100, // Only wait 100ms max
    });

    const input = createMessage('user', 'test');

    // Use all tokens
    for (let i = 0; i < 5; i++) {
      await limiter.process(input);
    }

    // Next request would need to wait 500ms (for 1 token at 2 tokens/sec)
    // But maxWaitTimeoutMs is 100ms, so should reject
    await expect(limiter.process(input)).rejects.toThrow(RateLimitError);
    await expect(limiter.process(input)).rejects.toThrow(/max wait timeout/);
    expect(limiter.metrics.rejectedRequests).toBeGreaterThanOrEqual(1);
  });
});

// ============================================
// Concurrent Requests Tests
// ============================================

describe('RateLimiterDecorator: Concurrent Requests', () => {
  it('should handle concurrent requests correctly', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 100, // High rate for testing
      capacity: 100,
    });

    const input = createMessage('user', 'test');

    // Make 50 concurrent requests
    const promises = Array.from({ length: 50 }, () => limiter.process(input));
    const results = await Promise.all(promises);

    expect(results).toHaveLength(50);
    expect(agent.getCallCount()).toBe(50);
    expect(limiter.metrics.allowedRequests).toBe(50);
  });
});

// ============================================
// Metrics Tests
// ============================================

describe('RateLimiterDecorator: Metrics', () => {
  it('should track token state', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 10,
      capacity: 10,
    });

    const initialTokens = limiter.metrics.currentTokens;
    expect(initialTokens).toBe(10); // Starts with full capacity

    await limiter.process(createMessage('user', 'test'));

    expect(limiter.metrics.currentTokens).toBeLessThan(initialTokens);
  });

  it('should track allowed and rejected requests', async () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent, {
      rate: 2,
      capacity: 2,
      maxWaitTimeoutMs: 10, // Very short timeout to trigger rejections
    });

    const input = createMessage('user', 'test');

    // Use all tokens
    await limiter.process(input);
    await limiter.process(input);

    // Next requests should be rejected
    try {
      await limiter.process(input);
    } catch {
      // Expected
    }

    try {
      await limiter.process(input);
    } catch {
      // Expected
    }

    expect(limiter.metrics.allowedRequests).toBe(2);
    expect(limiter.metrics.rejectedRequests).toBe(2);
    expect(limiter.metrics.totalRequests).toBe(4);
  });

  it('should return metrics copy to prevent mutation', () => {
    const agent = new TestAgent();
    const limiter = new RateLimiterDecorator(agent);

    const metrics1 = limiter.metrics;
    const metrics2 = limiter.metrics;

    expect(metrics1).toEqual(metrics2);
    expect(metrics1).not.toBe(metrics2); // Different objects
  });
});

// ============================================
// Configuration Validation Tests
// ============================================

describe('RateLimiterDecorator: Configuration Validation', () => {
  it('should reject negative or zero rate', () => {
    const agent = new TestAgent();

    expect(() => {
      new RateLimiterDecorator(agent, { rate: 0 });
    }).toThrow('rate must be positive');

    expect(() => {
      new RateLimiterDecorator(agent, { rate: -1 });
    }).toThrow('rate must be positive');
  });

  it('should reject capacity less than 1', () => {
    const agent = new TestAgent();

    expect(() => {
      new RateLimiterDecorator(agent, { capacity: 0 });
    }).toThrow('capacity must be at least 1');
  });

  it('should reject tokensPerRequest exceeding capacity', () => {
    const agent = new TestAgent();

    expect(() => {
      new RateLimiterDecorator(agent, {
        capacity: 5,
        tokensPerRequest: 10,
      });
    }).toThrow('tokensPerRequest cannot exceed capacity');
  });
});

// ============================================
// Agent Interface Tests
// ============================================

describe('RateLimiterDecorator: Agent Interface', () => {
  it('should preserve agent name and capabilities', () => {
    const agent = new TestAgent();
    agent.name = 'custom-agent';
    agent.capabilities = ['chat', 'tools'];

    const limiter = new RateLimiterDecorator(agent);

    expect(limiter.name).toBe('custom-agent');
    expect(limiter.capabilities).toEqual(['chat', 'tools']);
  });
});
