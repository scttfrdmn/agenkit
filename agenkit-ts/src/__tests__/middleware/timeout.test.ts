/**
 * Tests for timeout middleware.
 *
 * Tests TimeoutMiddleware for request timeout enforcement.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import { TimeoutMiddleware, TimeoutError } from '../../middleware/timeout';

// Fast agent (completes quickly)
class FastAgent implements Agent {
  name = 'fast-agent';
  capabilities = [];

  constructor(private delay: number = 10) {}

  async process(message: Message): Promise<Message> {
    await new Promise((resolve) => setTimeout(resolve, this.delay));
    return createMessage('assistant', 'fast response');
  }
}

// Slow agent (hangs for a long time)
class SlowAgent implements Agent {
  name = 'slow-agent';
  capabilities = [];

  constructor(private delay: number = 5000) {}

  async process(message: Message): Promise<Message> {
    await new Promise((resolve) => setTimeout(resolve, this.delay));
    return createMessage('assistant', 'slow response');
  }
}

// Failing agent (throws errors)
class FailingAgent implements Agent {
  name = 'failing-agent';
  capabilities = [];

  constructor(private errorMessage: string = 'test error') {}

  async process(_message: Message): Promise<Message> {
    throw new Error(this.errorMessage);
  }
}

// Streaming agent
class StreamingAgent implements Agent {
  name = 'streaming-agent';
  capabilities = ['streaming'];

  constructor(private chunkDelay: number = 10, private numChunks: number = 3) {}

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'non-streaming response');
  }

  async *processStream(_message: Message): AsyncGenerator<Message> {
    for (let i = 0; i < this.numChunks; i++) {
      await new Promise((resolve) => setTimeout(resolve, this.chunkDelay));
      yield createMessage('assistant', `chunk ${i + 1}`);
    }
  }
}

// ============================================
// Basic Timeout Tests
// ============================================

describe('TimeoutMiddleware: Basic Functionality', () => {
  it('should allow fast requests to complete', async () => {
    const agent = new FastAgent(10);
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    const input = createMessage('user', 'test');
    const result = await middleware.process(input);

    expect(result.content).toBe('fast response');
    expect(middleware.metrics.totalRequests).toBe(1);
    expect(middleware.metrics.successfulRequests).toBe(1);
    expect(middleware.metrics.timedOutRequests).toBe(0);
  });

  it('should timeout slow requests', async () => {
    const agent = new SlowAgent(500);
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 100 });

    const input = createMessage('user', 'test');

    await expect(middleware.process(input)).rejects.toThrow(TimeoutError);
    await expect(middleware.process(input)).rejects.toThrow(/Request timeout after 100ms/);

    expect(middleware.metrics.totalRequests).toBe(2);
    expect(middleware.metrics.successfulRequests).toBe(0);
    expect(middleware.metrics.timedOutRequests).toBe(2);
  });

  it('should handle multiple successful requests', async () => {
    const agent = new FastAgent(10);
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    const input = createMessage('user', 'test');

    await middleware.process(input);
    await middleware.process(input);
    await middleware.process(input);

    expect(middleware.metrics.totalRequests).toBe(3);
    expect(middleware.metrics.successfulRequests).toBe(3);
    expect(middleware.metrics.timedOutRequests).toBe(0);
  });

  it('should handle boundary case at timeout threshold', async () => {
    const agent = new FastAgent(95); // Just under 100ms
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 100 });

    const input = createMessage('user', 'test');
    const result = await middleware.process(input);

    expect(result.content).toBe('fast response');
    expect(middleware.metrics.successfulRequests).toBe(1);
  });
});

// ============================================
// Method-Specific Timeout Tests
// ============================================

describe('TimeoutMiddleware: Method-Specific Timeouts', () => {
  it('should use method-specific timeout from metadata', async () => {
    const middleware = new TimeoutMiddleware(new SlowAgent(150), {
      timeout: 100,
      methodTimeouts: {
        slow_operation: 200,
      },
    });

    const input = createMessage('user', 'test');
    input.metadata = { method: 'slow_operation' };

    const result = await middleware.process(input);

    expect(result.content).toBe('slow response');
    expect(middleware.metrics.successfulRequests).toBe(1);
  });

  it('should fall back to default timeout if method not configured', async () => {
    const middleware = new TimeoutMiddleware(new SlowAgent(150), {
      timeout: 100,
      methodTimeouts: {
        other_method: 200,
      },
    });

    const input = createMessage('user', 'test');
    input.metadata = { method: 'unknown_method' };

    await expect(middleware.process(input)).rejects.toThrow(TimeoutError);
  });

  it('should support operation field in metadata', async () => {
    const middleware = new TimeoutMiddleware(new SlowAgent(150), {
      timeout: 100,
      methodTimeouts: {
        long_task: 200,
      },
    });

    const input = createMessage('user', 'test');
    input.metadata = { operation: 'long_task' };

    const result = await middleware.process(input);

    expect(result.content).toBe('slow response');
  });
});

// ============================================
// Error Handling Tests
// ============================================

describe('TimeoutMiddleware: Error Handling', () => {
  it('should preserve non-timeout errors', async () => {
    const agent = new FailingAgent('custom error');
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    const input = createMessage('user', 'test');

    await expect(middleware.process(input)).rejects.toThrow('custom error');
    expect(middleware.metrics.timedOutRequests).toBe(0);
    expect(middleware.metrics.failedRequests).toBe(1);
  });

  it('should track errors separately from timeouts', async () => {
    const agent = new FailingAgent('test error');
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    const input = createMessage('user', 'test');

    try {
      await middleware.process(input);
    } catch {
      // Expected
    }

    expect(middleware.metrics.failedRequests).toBe(1);
    expect(middleware.metrics.timedOutRequests).toBe(0);
  });
});

// ============================================
// Streaming Tests
// ============================================

describe('TimeoutMiddleware: Streaming', () => {
  it('should handle streaming with chunks within timeout', async () => {
    const agent = new StreamingAgent(10, 3); // 3 chunks, 10ms each
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    const input = createMessage('user', 'test');
    const chunks: Message[] = [];

    for await (const chunk of middleware.processStream(input)) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(3);
    expect(chunks[0].content).toBe('chunk 1');
    expect(chunks[2].content).toBe('chunk 3');
    expect(middleware.metrics.successfulRequests).toBe(1);
  });

  it('should timeout streaming if deadline exceeded', async () => {
    const agent = new StreamingAgent(150, 4); // 4 chunks * 150ms = 600ms total
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 300 });

    const input = createMessage('user', 'test');

    await expect(async () => {
      for await (const _chunk of middleware.processStream(input)) {
        // Processing chunks
      }
    }).rejects.toThrow(TimeoutError);

    expect(middleware.metrics.timedOutRequests).toBeGreaterThanOrEqual(1);
  });

  it('should throw error if agent does not support streaming', async () => {
    const agent = new FastAgent(10); // No processStream method
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    const input = createMessage('user', 'test');

    await expect(async () => {
      for await (const _chunk of middleware.processStream(input)) {
        // Should not reach here
      }
    }).rejects.toThrow('Underlying agent does not support streaming');
  });
});

// ============================================
// Metrics Tests
// ============================================

describe('TimeoutMiddleware: Metrics', () => {
  it('should track request duration statistics', async () => {
    const middleware = new TimeoutMiddleware(new FastAgent(50), { timeoutMs: 1000 });

    const input = createMessage('user', 'test');
    await middleware.process(input);

    const metrics = middleware.metrics;

    expect(metrics.minDuration).toBeGreaterThan(0);
    expect(metrics.maxDuration).toBeGreaterThan(0);
    expect(metrics.avgDuration).toBeGreaterThan(0);
    expect(metrics.totalDuration).toBeGreaterThan(0);
  });

  it('should track min/max duration across multiple requests', async () => {
    const middleware = new TimeoutMiddleware(new FastAgent(10), { timeoutMs: 1000 });

    const input = createMessage('user', 'test');

    // Make several requests
    await middleware.process(input);
    await middleware.process(input);
    await middleware.process(input);

    const metrics = middleware.metrics;

    expect(metrics.totalRequests).toBe(3);
    expect(metrics.minDuration).toBeLessThanOrEqual(metrics.maxDuration!);
    expect(metrics.avgDuration).toBeGreaterThan(0);
  });

  it('should include timeout duration in metrics', async () => {
    const agent = new SlowAgent(500);
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 100 });

    const input = createMessage('user', 'test');

    try {
      await middleware.process(input);
    } catch {
      // Expected timeout
    }

    const metrics = middleware.metrics;

    expect(metrics.timedOutRequests).toBe(1);
    expect(metrics.totalDuration).toBeGreaterThanOrEqual(100);
    expect(metrics.maxDuration).toBeGreaterThanOrEqual(100);
  });

  it('should calculate average duration correctly', async () => {
    const middleware = new TimeoutMiddleware(new FastAgent(50), { timeoutMs: 1000 });

    const input = createMessage('user', 'test');

    await middleware.process(input);
    await middleware.process(input);

    const metrics = middleware.metrics;

    expect(metrics.avgDuration).toBeCloseTo(metrics.totalDuration / 2, 0);
  });

  it('should return metrics copy to prevent mutation', () => {
    const middleware = new TimeoutMiddleware(new FastAgent(10), { timeoutMs: 1000 });

    const metrics1 = middleware.metrics;
    const metrics2 = middleware.metrics;

    expect(metrics1).toEqual(metrics2);
    expect(metrics1).not.toBe(metrics2); // Different objects
  });
});

// ============================================
// Agent Interface Tests
// ============================================

describe('TimeoutMiddleware: Agent Interface', () => {
  it('should preserve agent name and capabilities', () => {
    const agent = new FastAgent(10);
    agent.name = 'custom-agent';
    agent.capabilities = ['chat', 'tools'];

    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    expect(middleware.name).toBe('custom-agent');
    expect(middleware.capabilities).toEqual(['chat', 'tools']);
  });

  it('should preserve streaming capability', () => {
    const agent = new StreamingAgent(10, 3);

    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 1000 });

    expect(middleware.capabilities).toContain('streaming');
  });
});

// ============================================
// Configuration Tests
// ============================================

describe('TimeoutMiddleware: Configuration', () => {
  it('should accept timeout configuration', () => {
    const agent = new FastAgent(10);
    const middleware = new TimeoutMiddleware(agent, { timeoutMs: 5000 });

    expect(middleware).toBeDefined();
  });

  it('should accept method-specific timeouts', () => {
    const agent = new FastAgent(10);
    const middleware = new TimeoutMiddleware(agent, {
      timeout: 1000,
      methodTimeouts: {
        fast: 500,
        slow: 5000,
      },
    });

    expect(middleware).toBeDefined();
  });
});
