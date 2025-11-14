/**
 * Tests for middleware.
 */

import { LocalAgent, createMessage, applyMiddleware, retry, timeout } from '../index';
import { TimeoutError } from '../middleware/timeout';

describe('Middleware', () => {
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

      const retriedAgent = applyMiddleware(agent, [retry({ maxAttempts: 3, initialDelay: 10 })]);

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

      const retriedAgent = applyMiddleware(agent, [retry({ maxAttempts: 2, initialDelay: 10 })]);

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
          maxAttempts: 3,
          initialDelay: 10,
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
        retry({ maxAttempts: 3, initialDelay: 50, backoffMultiplier: 2.0 }),
      ]);

      await retriedAgent.process(createMessage('user', 'Hello'));

      expect(attempts).toBe(3);
      expect(timestamps.length).toBe(3);

      // Check that delays increased
      if (timestamps.length >= 3) {
        const delay1 = timestamps[1] - timestamps[0];
        const delay2 = timestamps[2] - timestamps[1];

        // Second delay should be roughly 2x first delay (with some tolerance)
        expect(delay2).toBeGreaterThan(delay1 * 1.5);
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
          maxAttempts: 4,
          initialDelay: 100,
          backoffMultiplier: 10.0, // Would cause very long delay
          maxDelay: 200, // Cap at 200ms
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

      const timedAgent = applyMiddleware(agent, [timeout({ timeout: 100 })]);

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

      const timedAgent = applyMiddleware(agent, [timeout({ timeout: 100 })]);

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

      const timedAgent = applyMiddleware(agent, [timeout({ timeout: 50 })]);

      try {
        await timedAgent.process(createMessage('user', 'Hello'));
        fail('Should have thrown TimeoutError');
      } catch (error) {
        expect(error).toBeInstanceOf(TimeoutError);
        expect((error as TimeoutError).message).toBe('Request timeout after 50ms');
      }
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
        retry({ maxAttempts: 2, initialDelay: 10 }),
        timeout({ timeout: 200 }),
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
        timeout({ timeout: 50 }),
        retry({ maxAttempts: 3, initialDelay: 10 }),
      ]);

      await expect(robustAgent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        TimeoutError,
      );

      // Should try 3 times, each timing out
      expect(attempts).toBe(3);
    });
  });
});
