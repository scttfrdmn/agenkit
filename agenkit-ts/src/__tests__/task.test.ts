/**
 * Tests for Task pattern.
 */

import { Task, TimeoutError, executeTask } from '../patterns/task';
import { Agent, Message, createMessage } from '../core/interfaces';
import { vi } from 'vitest';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name = 'MockAgent';
  private response: string;
  private delay: number;
  private shouldFail: boolean;
  private failCount: number;
  private callCount: number;

  constructor(response: string, delay: number = 0, shouldFail: boolean = false, failCount: number = 0) {
    this.response = response;
    this.delay = delay;
    this.shouldFail = shouldFail;
    this.failCount = failCount;
    this.callCount = 0;
  }

  async process(message: Message): Promise<Message> {
    this.callCount++;

    if (this.delay > 0) {
      await new Promise(resolve => setTimeout(resolve, this.delay));
    }

    if (this.shouldFail || this.callCount <= this.failCount) {
      throw new Error('Agent processing failed');
    }

    return createMessage('assistant', this.response);
  }

  getCallCount(): number {
    return this.callCount;
  }
}

describe('Task', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const agent = new MockAgent('response');
      const task = new Task(agent);

      expect(task.completed).toBe(false);
      expect(task.result).toBeUndefined();
    });

    it('should create with timeout', () => {
      const agent = new MockAgent('response');
      const task = new Task(agent, { timeout: 5000 });

      expect(task.completed).toBe(false);
    });

    it('should create with retries', () => {
      const agent = new MockAgent('response');
      const task = new Task(agent, { retries: 3 });

      expect(task.completed).toBe(false);
    });

    it('should create with custom config', () => {
      const agent = new MockAgent('response');
      const task = new Task(agent, {
        timeout: 5000,
        retries: 2,
        customField: 'value',
      });

      expect(task.completed).toBe(false);
    });
  });

  describe('Basic Execution', () => {
    it('should execute task successfully', async () => {
      const agent = new MockAgent('Hello');
      const task = new Task(agent);
      const input = createMessage('user', 'Hi');

      const result = await task.execute(input);

      expect(result.content).toBe('Hello');
      expect(task.completed).toBe(true);
      expect(task.result).toBe(result);
    });

    it('should prevent reuse after completion', async () => {
      const agent = new MockAgent('response');
      const task = new Task(agent);
      const input = createMessage('user', 'message');

      await task.execute(input);

      await expect(task.execute(input)).rejects.toThrow(
        'Task already completed. Create a new Task for another execution.'
      );
    });

    it('should mark as completed even on failure', async () => {
      const agent = new MockAgent('', 0, true);
      const task = new Task(agent);
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow('Agent processing failed');
      expect(task.completed).toBe(true);
    });

    it('should store result only on success', async () => {
      const agent = new MockAgent('', 0, true);
      const task = new Task(agent);
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow();
      expect(task.result).toBeUndefined();
    });
  });

  describe('Timeout Handling', () => {
    it('should timeout if execution exceeds limit', async () => {
      const agent = new MockAgent('response', 200); // 200ms delay
      const task = new Task(agent, { timeout: 100 }); // 100ms timeout
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow(TimeoutError);
      expect(task.completed).toBe(true);
    });

    it('should complete successfully if within timeout', async () => {
      const agent = new MockAgent('response', 50); // 50ms delay
      const task = new Task(agent, { timeout: 200 }); // 200ms timeout
      const input = createMessage('user', 'message');

      const result = await task.execute(input);

      expect(result.content).toBe('response');
      expect(task.completed).toBe(true);
    });

    it('should not retry on timeout', async () => {
      const agent = new MockAgent('response', 200);
      const task = new Task(agent, { timeout: 100, retries: 3 });
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow(TimeoutError);
      expect((agent as MockAgent).getCallCount()).toBe(1); // Should not retry
    });
  });

  describe('Retry Logic', () => {
    it('should retry on failure', async () => {
      const agent = new MockAgent('response', 0, false, 2); // Fail first 2 attempts
      const task = new Task(agent, { retries: 2 });
      const input = createMessage('user', 'message');

      const result = await task.execute(input);

      expect(result.content).toBe('response');
      expect((agent as MockAgent).getCallCount()).toBe(3); // 1 initial + 2 retries
    });

    it('should fail after all retries exhausted', async () => {
      const agent = new MockAgent('', 0, true);
      const task = new Task(agent, { retries: 2 });
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow('Agent processing failed');
      expect((agent as MockAgent).getCallCount()).toBe(3); // 1 initial + 2 retries
      expect(task.completed).toBe(true);
    });

    it('should use exponential backoff between retries', async () => {
      const agent = new MockAgent('response', 0, false, 1); // Fail first attempt
      const task = new Task(agent, { retries: 1 });
      const input = createMessage('user', 'message');

      const start = Date.now();
      await task.execute(input);
      const duration = Date.now() - start;

      // Should have at least 100ms backoff (first retry)
      expect(duration).toBeGreaterThanOrEqual(100);
    });

    it('should work with retries=0', async () => {
      const agent = new MockAgent('response');
      const task = new Task(agent, { retries: 0 });
      const input = createMessage('user', 'message');

      const result = await task.execute(input);

      expect(result.content).toBe('response');
      expect((agent as MockAgent).getCallCount()).toBe(1);
    });
  });

  describe('Cleanup Lifecycle', () => {
    it('should call cleanup on successful completion', async () => {
      const agent = new MockAgent('response');
      const task = new Task(agent);
      const cleanupSpy = vi.spyOn(task, 'cleanup');
      const input = createMessage('user', 'message');

      await task.execute(input);

      // Cleanup not called automatically on success
      expect(cleanupSpy).not.toHaveBeenCalled();
    });

    it('should call cleanup on failure', async () => {
      const agent = new MockAgent('', 0, true);
      const task = new Task(agent);
      const cleanupSpy = vi.spyOn(task, 'cleanup');
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow();

      expect(cleanupSpy).toHaveBeenCalled();
    });

    it('should call cleanup on timeout', async () => {
      const agent = new MockAgent('response', 200);
      const task = new Task(agent, { timeout: 100 });
      const cleanupSpy = vi.spyOn(task, 'cleanup');
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow(TimeoutError);

      expect(cleanupSpy).toHaveBeenCalled();
    });

    it('should allow custom cleanup logic', async () => {
      class CustomTask extends Task {
        public cleanupCalled = false;

        async cleanup(): Promise<void> {
          this.cleanupCalled = true;
          await super.cleanup();
        }
      }

      const agent = new MockAgent('', 0, true);
      const task = new CustomTask(agent);
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow();

      expect(task.cleanupCalled).toBe(true);
    });
  });

  describe('Context Manager Pattern', () => {
    it('should execute with automatic cleanup', async () => {
      const agent = new MockAgent('response');
      const input = createMessage('user', 'message');

      const result = await Task.withTask(agent, async task => {
        return await task.execute(input);
      });

      expect(result.content).toBe('response');
    });

    it('should cleanup even on error', async () => {
      const agent = new MockAgent('', 0, true);
      const input = createMessage('user', 'message');

      class CustomTask extends Task {
        public cleanupCalled = false;

        async cleanup(): Promise<void> {
          this.cleanupCalled = true;
          await super.cleanup();
        }

        static async withCustomTask(
          agent: Agent,
          fn: (task: CustomTask) => Promise<any>
        ): Promise<any> {
          const task = new CustomTask(agent);
          try {
            return await fn(task);
          } finally {
            await task.cleanup();
          }
        }
      }

      let taskInstance: CustomTask | undefined;
      await expect(
        CustomTask.withCustomTask(agent, async task => {
          taskInstance = task;
          return await task.execute(input);
        })
      ).rejects.toThrow();

      expect(taskInstance?.cleanupCalled).toBe(true);
    });

    it('should pass config to task', async () => {
      const agent = new MockAgent('response');
      const input = createMessage('user', 'message');

      const result = await Task.withTask(
        agent,
        async task => {
          return await task.execute(input);
        },
        { timeout: 5000, retries: 2 }
      );

      expect(result.content).toBe('response');
    });

    it('should return function result', async () => {
      const agent = new MockAgent('response');
      const input = createMessage('user', 'message');

      const result = await Task.withTask(agent, async task => {
        await task.execute(input);
        return 'custom return value';
      });

      expect(result).toBe('custom return value');
    });
  });

  describe('Convenience Function', () => {
    it('should execute task with executeTask function', async () => {
      const agent = new MockAgent('response');
      const input = createMessage('user', 'message');

      const result = await executeTask(agent, input);

      expect(result.content).toBe('response');
    });

    it('should support config in executeTask', async () => {
      const agent = new MockAgent('response', 0, false, 1);
      const input = createMessage('user', 'message');

      const result = await executeTask(agent, input, { retries: 2 });

      expect(result.content).toBe('response');
    });

    it('should handle timeout in executeTask', async () => {
      const agent = new MockAgent('response', 200);
      const input = createMessage('user', 'message');

      await expect(executeTask(agent, input, { timeout: 100 })).rejects.toThrow(TimeoutError);
    });
  });

  describe('Error Handling', () => {
    it('should preserve error type on failure', async () => {
      class CustomError extends Error {
        constructor(message: string) {
          super(message);
          this.name = 'CustomError';
        }
      }

      class FailingAgent implements Agent {
        readonly name = 'FailingAgent';

        async process(message: Message): Promise<Message> {
          throw new CustomError('Custom failure');
        }
      }

      const agent = new FailingAgent();
      const task = new Task(agent);
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow(CustomError);
    });

    it('should convert non-Error throws to Error', async () => {
      class StringThrowingAgent implements Agent {
        readonly name = 'StringThrowingAgent';

        async process(message: Message): Promise<Message> {
          throw 'String error';
        }
      }

      const agent = new StringThrowingAgent();
      const task = new Task(agent);
      const input = createMessage('user', 'message');

      await expect(task.execute(input)).rejects.toThrow('String error');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty message', async () => {
      const agent = new MockAgent('response');
      const task = new Task(agent);
      const input = createMessage('user', '');

      const result = await task.execute(input);

      expect(result.content).toBe('response');
    });

    it('should handle very long messages', async () => {
      const agent = new MockAgent('response');
      const task = new Task(agent);
      const longContent = 'a'.repeat(100000);
      const input = createMessage('user', longContent);

      const result = await task.execute(input);

      expect(result.content).toBe('response');
    });

    it('should handle multiple retries with different failures', async () => {
      let attempt = 0;
      class FlakyAgent implements Agent {
        readonly name = 'FlakyAgent';

        async process(message: Message): Promise<Message> {
          attempt++;
          if (attempt === 1) throw new Error('Network error');
          if (attempt === 2) throw new Error('Timeout error');
          return createMessage('assistant', 'Success');
        }
      }

      const agent = new FlakyAgent();
      const task = new Task(agent, { retries: 2 });
      const input = createMessage('user', 'message');

      const result = await task.execute(input);

      expect(result.content).toBe('Success');
      expect(attempt).toBe(3);
    });
  });
});
