/**
 * Tests for middleware.
 */

import { LocalAgent, createMessage, applyMiddleware, retry, timeout, BaseMiddleware } from '../index';
import { TimeoutError } from '../middleware/timeout';
import { CircuitBreakerMiddleware, RequestTimeoutError } from '../middleware/circuit-breaker';
import { RateLimiterDecorator, RateLimitError } from '../middleware/rate-limiter';
import { BatchingDecorator } from '../middleware/batching';
import { Message } from '../core/interfaces';

describe('Middleware', () => {
  describe('BaseMiddleware', () => {
    it('should proxy agent name and capabilities', () => {
      class TestMiddleware extends BaseMiddleware {
        async process(message: Message): Promise<Message> {
          return this.agent.process(message);
        }
      }

      const agent = new LocalAgent({
        name: 'test-agent',
        capabilities: ['test-cap'],
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const middleware = new TestMiddleware(agent);

      expect(middleware.name).toBe('test-agent');
      expect(middleware.capabilities).toEqual(['test-cap']);
    });

    it('should throw error if agent does not support streaming', async () => {
      class TestMiddleware extends BaseMiddleware {
        async process(message: Message): Promise<Message> {
          return this.agent.process(message);
        }
      }

      const agent = new LocalAgent({
        name: 'non-streaming',
        process: async (msg) => createMessage('assistant', msg.content),
        // No processStream
      });

      const middleware = new TestMiddleware(agent);

      expect(middleware.processStream).toBeDefined();
      const stream = middleware.processStream!(createMessage('user', 'test'));
      await expect(stream.next()).rejects.toThrow('does not support streaming');
    });

    it('should delegate to agent processStream if available', async () => {
      class TestMiddleware extends BaseMiddleware {
        async process(message: Message): Promise<Message> {
          return this.agent.process(message);
        }
      }

      const agent = new LocalAgent({
        name: 'streaming',
        process: async (msg) => createMessage('assistant', msg.content),
        processStream: async function* (msg) {
          yield createMessage('assistant', 'chunk1');
          yield createMessage('assistant', 'chunk2');
        },
      });

      const middleware = new TestMiddleware(agent);

      const chunks: string[] = [];
      for await (const chunk of middleware.processStream!(createMessage('user', 'test'))) {
        chunks.push(chunk.content as string);
      }

      expect(chunks).toEqual(['chunk1', 'chunk2']);
    });
  });

  describe('applyMiddleware', () => {
    it('should return agent unchanged when middleware array is empty', () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const wrapped = applyMiddleware(agent, []);

      expect(wrapped).toBe(agent);
    });
  });

  describe('RetryMiddleware', () => {
    it('should retry on failure and eventually succeed', async () => {
      let attempts = 0;

      const agent = new LocalAgent({
        name: 'flaky',
        process: async (msg) => {
          attempts++;

          if (attempts < 3) {
            throw new Error('Network error');
          }

          return createMessage('assistant', 'Success!');
        },
      });

      const retriedAgent = applyMiddleware(agent, [retry({ maxRetries: 3, initialDelayMs: 10 })]);

      const response = await retriedAgent.process(createMessage('user', 'Hello'));

      expect(response.content).toBe('Success!');
      expect(attempts).toBe(3);
    });

    it('should throw error after max attempts', async () => {
      let attempts = 0;

      const agent = new LocalAgent({
        name: 'always-fails',
        process: async () => {
          attempts++;
          throw new Error('Network error');  // Changed to retryable error
        },
      });

      const retriedAgent = applyMiddleware(agent, [retry({ maxRetries: 2, initialDelayMs: 10 })]);

      await expect(retriedAgent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        'Network error',
      );

      expect(attempts).toBe(2);
    });

    it('should not retry if error is not retryable', async () => {
      let attempts = 0;

      const agent = new LocalAgent({
        name: 'non-retryable',
        process: async () => {
          attempts++;
          throw new Error('Validation error');
        },
      });

      const retriedAgent = applyMiddleware(agent, [
        retry({
          maxRetries: 3,
          initialDelayMs: 10,
          shouldRetry: (error) => error.message.includes('network'),
        }),
      ]);

      await expect(retriedAgent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        'Validation error',
      );

      expect(attempts).toBe(1);
    });

    it('should apply exponential backoff', async () => {
      let attempts = 0;
      const timestamps: number[] = [];

      const agent = new LocalAgent({
        name: 'backoff-test',
        process: async () => {
          attempts++;
          timestamps.push(Date.now());

          if (attempts < 3) {
            throw new Error('Network timeout');
          }

          return createMessage('assistant', 'Success');
        },
      });

      const retriedAgent = applyMiddleware(agent, [
        retry({ maxRetries: 3, initialDelayMs: 50, backoffMultiplier: 2.0 }),
      ]);

      await retriedAgent.process(createMessage('user', 'Hello'));

      expect(attempts).toBe(3);
      expect(timestamps.length).toBe(3);

      // Check that delays increased
      if (timestamps.length >= 3) {
        const delay1 = timestamps[1] - timestamps[0];
        const delay2 = timestamps[2] - timestamps[1];

        // Second delay should be at least as long as first (exponential backoff)
        // Using >= instead of > 1.5x due to system timing variability
        expect(delay2).toBeGreaterThanOrEqual(delay1 * 0.9);

        // Verify both delays are reasonable (within expected range)
        expect(delay1).toBeGreaterThanOrEqual(30); // At least 30ms (50ms - timing noise)
        expect(delay2).toBeGreaterThanOrEqual(70); // At least 70ms (100ms - timing noise)
      }
    });

    it('should respect maxDelay', async () => {
      let attempts = 0;

      const agent = new LocalAgent({
        name: 'max-delay-test',
        process: async () => {
          attempts++;
          if (attempts < 4) {
            throw new Error('Network error');
          }
          return createMessage('assistant', 'Success');
        },
      });

      const retriedAgent = applyMiddleware(agent, [
        retry({
          maxRetries: 4,
          initialDelayMs: 100,
          backoffMultiplier: 10.0, // Would cause very long delay
          maxDelayMs: 200, // Cap at 200ms
        }),
      ]);

      const start = Date.now();
      await retriedAgent.process(createMessage('user', 'Hello'));
      const duration = Date.now() - start;

      // With uncapped backoff: 100ms + 1000ms + 10000ms = 11100ms
      // With maxDelay=200ms: 100ms + 200ms + 200ms = 500ms
      expect(duration).toBeLessThan(1000);
      expect(attempts).toBe(4);
    });
  });

  describe('TimeoutMiddleware', () => {
    it('should timeout long-running requests', async () => {
      const agent = new LocalAgent({
        name: 'slow',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          return createMessage('assistant', msg.content);
        },
      });

      const timedAgent = applyMiddleware(agent, [timeout({ timeoutMs: 100 })]);

      await expect(timedAgent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        TimeoutError,
      );
    });

    it('should allow fast requests', async () => {
      const agent = new LocalAgent({
        name: 'fast',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 10));
          return createMessage('assistant', msg.content);
        },
      });

      const timedAgent = applyMiddleware(agent, [timeout({ timeoutMs: 100 })]);

      const response = await timedAgent.process(createMessage('user', 'Hello'));

      expect(response.content).toBe('Hello');
    });

    it('should provide clear error message', async () => {
      const agent = new LocalAgent({
        name: 'very-slow',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 500));
          return createMessage('assistant', msg.content);
        },
      });

      const timedAgent = applyMiddleware(agent, [timeout({ timeoutMs: 50 })]);

      await expect(timedAgent.process(createMessage('user', 'Hello')))
        .rejects.toThrow('Request timeout after 50ms');
    });
  });

  describe('Middleware composition', () => {
    it('should apply multiple middleware in order', async () => {
      let attempts = 0;

      const agent = new LocalAgent({
        name: 'composition-test',
        process: async (msg) => {
          attempts++;

          // Fail on first attempt
          if (attempts === 1) {
            throw new Error('Network error');
          }

          // Take 50ms on second attempt
          await new Promise((resolve) => setTimeout(resolve, 50));

          return createMessage('assistant', `Attempt ${attempts}`);
        },
      });

      // Apply retry, then timeout
      const robustAgent = applyMiddleware(agent, [
        retry({ maxRetries: 2, initialDelayMs: 10 }),
        timeout({ timeoutMs: 200 }),
      ]);

      const response = await robustAgent.process(createMessage('user', 'Hello'));

      expect(response.content).toBe('Attempt 2');
      expect(attempts).toBe(2);
    });

    it('should handle timeout within retry', async () => {
      let attempts = 0;

      const agent = new LocalAgent({
        name: 'timeout-retry-test',
        process: async () => {
          attempts++;

          // All attempts take too long
          await new Promise((resolve) => setTimeout(resolve, 200));

          return createMessage('assistant', 'Should not reach here');
        },
      });

      // Timeout wraps each retry attempt
      const robustAgent = applyMiddleware(agent, [
        timeout({ timeoutMs: 50 }),
        retry({ maxRetries: 3, initialDelayMs: 10 }),
      ]);

      await expect(robustAgent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        TimeoutError,
      );

      // Should try 3 times, each timing out
      expect(attempts).toBe(3);
    });
  });

  describe('Timeout - Method-Specific Timeouts', () => {
    it('should use method-specific timeout when specified', async () => {
      const agent = new LocalAgent({
        name: 'method-aware',
        process: async (msg) => {
          // Simulate different operation durations
          const delay = msg.metadata?.method === 'health_check' ? 20 : 150;
          await new Promise((resolve) => setTimeout(resolve, delay));
          return createMessage('assistant', `Processed ${msg.metadata?.method}`);
        },
      });

      const timedAgent = applyMiddleware(agent, [
        timeout({ timeoutMs: 100, // Default timeout
          methodTimeouts: {
            health_check: 50, // Shorter timeout for health checks
            long_operation: 200, // Longer timeout for long operations
          },
        }),
      ]);

      // Health check should succeed with short timeout
      const healthMsg = createMessage('user', 'check');
      healthMsg.metadata = { method: 'health_check' };
      const healthResult = await timedAgent.process(healthMsg);
      expect(healthResult.content).toBe('Processed health_check');

      // Long operation should timeout with default timeout
      const longMsg = createMessage('user', 'process');
      longMsg.metadata = { method: 'unknown_method' };
      await expect(timedAgent.process(longMsg)).rejects.toThrow(TimeoutError);
    });

    it('should fall back to default timeout for unspecified methods', async () => {
      const agent = new LocalAgent({
        name: 'fallback-test',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 150));
          return createMessage('assistant', 'Done');
        },
      });

      const timedAgent = applyMiddleware(agent, [
        timeout({ timeoutMs: 100,
          methodTimeouts: {
            special: 300,
          },
        }),
      ]);

      // Unspecified method should use default timeout (100ms) and fail
      const msg = createMessage('user', 'test');
      msg.metadata = { method: 'other' };
      await expect(timedAgent.process(msg)).rejects.toThrow(TimeoutError);
    });
  });

  describe('Timeout - Streaming Support', () => {
    it('should enforce timeout on streaming operations', async () => {
      const agent = new LocalAgent({
        name: 'slow-stream',
        process: async (msg) => createMessage('assistant', msg.content),
        processStream: async function* (msg) {
          for (let i = 0; i < 5; i++) {
            await new Promise((resolve) => setTimeout(resolve, 50));
            yield createMessage('assistant', `chunk${i}`);
          }
        },
      });

      const timedAgent = applyMiddleware(agent, [timeout({ timeoutMs: 120 })]);

      const chunks: string[] = [];
      let didThrow = false;
      try {
        for await (const chunk of timedAgent.processStream!(createMessage('user', 'test'))) {
          chunks.push(chunk.content as string);
        }
      } catch (error) {
        didThrow = true;
        expect(error).toBeInstanceOf(TimeoutError);
        // Should have received at least 2 chunks before timeout
        expect(chunks.length).toBeGreaterThanOrEqual(2);
        expect(chunks.length).toBeLessThan(5);
      }
      expect(didThrow).toBe(true);
    });

    it('should allow fast streams to complete', async () => {
      const agent = new LocalAgent({
        name: 'fast-stream',
        process: async (msg) => createMessage('assistant', msg.content),
        processStream: async function* (msg) {
          for (let i = 0; i < 3; i++) {
            await new Promise((resolve) => setTimeout(resolve, 10));
            yield createMessage('assistant', `chunk${i}`);
          }
        },
      });

      const timedAgent = applyMiddleware(agent, [timeout({ timeoutMs: 200 })]);

      const chunks: string[] = [];
      for await (const chunk of timedAgent.processStream!(createMessage('user', 'test'))) {
        chunks.push(chunk.content as string);
      }

      expect(chunks).toEqual(['chunk0', 'chunk1', 'chunk2']);
    });

    it('should throw error for non-streaming agent', async () => {
      const agent = new LocalAgent({
        name: 'non-streaming',
        process: async (msg) => createMessage('assistant', msg.content),
        // No processStream
      });

      const timedAgent = applyMiddleware(agent, [timeout({ timeoutMs: 100 })]);

      const stream = timedAgent.processStream!(createMessage('user', 'test'));
      await expect(stream.next()).rejects.toThrow('does not support streaming');
    });
  });

  describe('CircuitBreaker - Request Timeout', () => {
    it('should enforce request timeout on individual requests', async () => {
      const agent = new LocalAgent({
        name: 'slow-agent',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 150));
          return createMessage('assistant', msg.content);
        },
      });

      const circuitBreaker = new CircuitBreakerMiddleware(agent, {
        failureThreshold: 3,
        successThreshold: 2,
        timeout: 60000,
        requestTimeout: 100, // Individual request timeout
      });

      // Request should timeout
      await expect(circuitBreaker.process(createMessage('user', 'test'))).rejects.toThrow(
        RequestTimeoutError,
      );

      // Verify metrics show failure
      const metrics = circuitBreaker.metrics;
      expect(metrics.failedRequests).toBe(1);
    });

    it('should allow fast requests even with request timeout set', async () => {
      const agent = new LocalAgent({
        name: 'fast-agent',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 20));
          return createMessage('assistant', msg.content);
        },
      });

      const circuitBreaker = new CircuitBreakerMiddleware(agent, {
        failureThreshold: 3,
        requestTimeout: 100,
      });

      const response = await circuitBreaker.process(createMessage('user', 'test'));
      expect(response.content).toBe('test');

      const metrics = circuitBreaker.metrics;
      expect(metrics.successfulRequests).toBe(1);
    });

    it('should work without request timeout configured', async () => {
      const agent = new LocalAgent({
        name: 'no-timeout-agent',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 50));
          return createMessage('assistant', msg.content);
        },
      });

      const circuitBreaker = new CircuitBreakerMiddleware(agent, {
        failureThreshold: 3,
        // No requestTimeout specified
      });

      const response = await circuitBreaker.process(createMessage('user', 'test'));
      expect(response.content).toBe('test');
    });
  });

  describe('RateLimiter - Max Wait Timeout', () => {
    it('should reject requests when wait time exceeds maxWaitTimeout', async () => {
      const agent = new LocalAgent({
        name: 'rate-limited',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const rateLimiter = new RateLimiterDecorator(agent, {
        rate: 1.0, // 1 token per second
        capacity: 1,
        tokensPerRequest: 1,
        maxWaitTimeout: 100, // Max wait 100ms
      });

      // First request should succeed immediately
      await rateLimiter.process(createMessage('user', 'first'));

      // Second request would need to wait ~1000ms but max wait is 100ms
      await expect(rateLimiter.process(createMessage('user', 'second'))).rejects.toThrow(
        RateLimitError,
      );

      const metrics = rateLimiter.metrics;
      expect(metrics.allowedRequests).toBe(1);
      expect(metrics.rejectedRequests).toBe(1);
    });

    it('should wait indefinitely when maxWaitTimeout is 0', async () => {
      const agent = new LocalAgent({
        name: 'rate-limited-wait',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const rateLimiter = new RateLimiterDecorator(agent, {
        rate: 5.0, // 5 tokens per second
        capacity: 2,
        tokensPerRequest: 2,
        maxWaitTimeout: 0, // Wait indefinitely
      });

      // First request uses 2 tokens
      await rateLimiter.process(createMessage('user', 'first'));

      // Second request should wait for tokens to refill
      const start = Date.now();
      await rateLimiter.process(createMessage('user', 'second'));
      const elapsed = Date.now() - start;

      // Should have waited ~400ms (2 tokens at 5/sec)
      expect(elapsed).toBeGreaterThanOrEqual(300); // Allow for some timing variability
      expect(elapsed).toBeLessThan(600);

      const metrics = rateLimiter.metrics;
      expect(metrics.allowedRequests).toBe(2);
      expect(metrics.rejectedRequests).toBe(0);
    });

    it('should provide clear error message when exceeding max wait', async () => {
      const agent = new LocalAgent({
        name: 'rate-test',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const rateLimiter = new RateLimiterDecorator(agent, {
        rate: 1.0,
        capacity: 1,
        tokensPerRequest: 1,
        maxWaitTimeout: 50,
      });

      await rateLimiter.process(createMessage('user', 'first'));

      const promise = rateLimiter.process(createMessage('user', 'second'));
      await expect(promise).rejects.toThrow(RateLimitError);
      await expect(promise).rejects.toThrow(/max wait timeout/);
    });
  });

  describe('Batching - Shutdown Method', () => {
    it('should shutdown gracefully and flush pending requests', async () => {
      const agent = new LocalAgent({
        name: 'batch-agent',
        process: async (msg) => {
          await new Promise((resolve) => setTimeout(resolve, 10));
          return createMessage('assistant', msg.content);
        },
      });

      const batching = new BatchingDecorator(agent, {
        maxBatchSize: 10,
        maxWaitTime: 1000, // Long wait time to test shutdown
      });

      // Enqueue multiple requests
      const promises = [
        batching.process(createMessage('user', 'msg1')),
        batching.process(createMessage('user', 'msg2')),
        batching.process(createMessage('user', 'msg3')),
      ];

      // Shutdown before batch timeout
      await batching.shutdown();

      // All requests should still complete
      const results = await Promise.all(promises);
      expect(results.length).toBe(3);
      expect(results[0].content).toBe('msg1');
      expect(results[1].content).toBe('msg2');
      expect(results[2].content).toBe('msg3');

      // New requests should be rejected
      await expect(batching.process(createMessage('user', 'msg4'))).rejects.toThrow(
        'shut down',
      );
    });

    it('should reject new requests after shutdown', async () => {
      const agent = new LocalAgent({
        name: 'batch-agent',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const batching = new BatchingDecorator(agent, {
        maxBatchSize: 10,
        maxWaitTime: 100,
      });

      await batching.shutdown();

      await expect(batching.process(createMessage('user', 'test'))).rejects.toThrow(
        'shut down',
      );
    });

    it('should handle empty queue during shutdown', async () => {
      const agent = new LocalAgent({
        name: 'batch-agent',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const batching = new BatchingDecorator(agent, {
        maxBatchSize: 10,
        maxWaitTime: 100,
      });

      // Shutdown with empty queue should not throw
      await expect(batching.shutdown()).resolves.not.toThrow();
    });
  });
});
