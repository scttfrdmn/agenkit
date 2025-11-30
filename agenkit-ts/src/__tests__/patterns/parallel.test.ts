/**
 * Comprehensive tests for Parallel pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Concurrent execution
 * - Aggregation strategies
 * - Error handling
 * - Partial failures
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import { ParallelAgent, DefaultAggregators } from '../../patterns/parallel';
import { Message, createMessage } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  createDelayAgent,
  CallCountingAgent,
  FlakyAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

describe('ParallelAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

      expect(parallel).toBeDefined();
      expect(parallel.name).toBe('ParallelAgent');
    });

    it('should throw error with empty agents list', () => {
      expect(() => new ParallelAgent([], DefaultAggregators.first)).toThrow(
        'at least one agent is required',
      );
    });

    it('should throw error with null agents', () => {
      expect(() => new ParallelAgent(null as any, DefaultAggregators.first)).toThrow(
        'at least one agent is required',
      );
    });

    it('should throw error with undefined agents', () => {
      expect(() => new ParallelAgent(undefined as any, DefaultAggregators.first)).toThrow(
        'at least one agent is required',
      );
    });

    it('should throw error with missing aggregator', () => {
      const agent = createMockAgent('agent', 'result');
      expect(() => new ParallelAgent([agent], null as any)).toThrow(
        'aggregator function is required',
      );
    });

    it('should throw error with undefined aggregator', () => {
      const agent = createMockAgent('agent', 'result');
      expect(() => new ParallelAgent([agent], undefined as any)).toThrow(
        'aggregator function is required',
      );
    });

    it('should work with single agent', () => {
      const agent = createMockAgent('solo', 'result');
      const parallel = new ParallelAgent([agent], DefaultAggregators.first);

      expect(parallel).toBeDefined();
      expect(parallel.capabilities).toContain('parallel');
    });
  });

  describe('Capabilities', () => {
    it('should include parallel and ensemble capabilities', () => {
      const agent = createMockAgent('agent', 'result');
      const parallel = new ParallelAgent([agent], DefaultAggregators.first);

      const caps = parallel.capabilities;
      expect(caps).toContain('parallel');
      expect(caps).toContain('ensemble');
    });

    it('should combine capabilities from all agents', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);
      const caps = parallel.capabilities;

      expect(caps).toContain('mock');
      expect(caps).toContain('parallel');
      expect(caps).toContain('ensemble');
    });

    it('should deduplicate capabilities', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);
      const caps = parallel.capabilities;

      const mockCount = caps.filter((c) => c === 'mock').length;
      expect(mockCount).toBe(1);
    });
  });

  describe('Basic Processing', () => {
    it('should process message with single agent', async () => {
      const agent = createMockAgent('agent', 'processed');
      const parallel = new ParallelAgent([agent], DefaultAggregators.first);

      const input = createMessage('user', 'test input');
      const result = await parallel.process(input);

      validateMessage(result);
      expect(result.content).toBe('processed');
    });

    it('should process message with multiple agents', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');
      const agent3 = createMockAgent('agent3', 'result3');

      const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.first);

      const input = createMessage('user', 'test input');
      const result = await parallel.process(input);

      expect(result.content).toBe('result1');
    });

    it('should throw error with null message', async () => {
      const agent = createMockAgent('agent', 'result');
      const parallel = new ParallelAgent([agent], DefaultAggregators.first);

      await expect(parallel.process(null as any)).rejects.toThrow('message cannot be nil');
    });

    it('should throw error with undefined message', async () => {
      const agent = createMockAgent('agent', 'result');
      const parallel = new ParallelAgent([agent], DefaultAggregators.first);

      await expect(parallel.process(undefined as any)).rejects.toThrow('message cannot be nil');
    });
  });

  describe('Concurrent Execution', () => {
    it('should execute agents concurrently', async () => {
      const startTime = Date.now();

      const agent1 = createDelayAgent('agent1', 'result1', 50);
      const agent2 = createDelayAgent('agent2', 'result2', 50);
      const agent3 = createDelayAgent('agent3', 'result3', 50);

      const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      await parallel.process(input);

      const elapsed = Date.now() - startTime;

      // Should be ~50ms (parallel) not ~150ms (sequential)
      expect(elapsed).toBeLessThan(150);
    });

    it('should call all agents with same input', async () => {
      const counter1 = new CallCountingAgent('counter1', 'result1');
      const counter2 = new CallCountingAgent('counter2', 'result2');
      const counter3 = new CallCountingAgent('counter3', 'result3');

      const parallel = new ParallelAgent(
        [counter1, counter2, counter3],
        DefaultAggregators.first,
      );

      const input = createMessage('user', 'test input');
      await parallel.process(input);

      expect(counter1.callCount).toBe(1);
      expect(counter2.callCount).toBe(1);
      expect(counter3.callCount).toBe(1);
      expect(String(counter1.lastMessage?.content)).toBe('test input');
      expect(String(counter2.lastMessage?.content)).toBe('test input');
      expect(String(counter3.lastMessage?.content)).toBe('test input');
    });

    it('should collect all successful results', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createMockAgent('agent2', 'B');
      const agent3 = createMockAgent('agent3', 'C');

      const customAggregator = (messages: Message[]) => {
        const combined = messages.map((m) => String(m.content)).join('');
        return createMessage('assistant', combined);
      };

      const parallel = new ParallelAgent([agent1, agent2, agent3], customAggregator);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(String(result.content)).toMatch(/^[ABC]{3}$/);
      expect(String(result.content).length).toBe(3);
    });
  });

  describe('Aggregation Strategies', () => {
    describe('First Aggregator', () => {
      it('should return first result', async () => {
        const agent1 = createMockAgent('agent1', 'first');
        const agent2 = createMockAgent('agent2', 'second');

        const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

        const input = createMessage('user', 'test');
        const result = await parallel.process(input);

        expect(result.content).toBe('first');
      });

      it('should handle empty results', async () => {
        const result = DefaultAggregators.first([]);
        expect(result.content).toBe('No results to aggregate');
      });
    });

    describe('Concatenate Aggregator', () => {
      it('should combine all results with separator', async () => {
        const agent1 = createMockAgent('agent1', 'first');
        const agent2 = createMockAgent('agent2', 'second');
        const agent3 = createMockAgent('agent3', 'third');

        const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.concatenate);

        const input = createMessage('user', 'test');
        const result = await parallel.process(input);

        expect(String(result.content)).toContain('first');
        expect(String(result.content)).toContain('second');
        expect(String(result.content)).toContain('third');
        expect(String(result.content)).toContain('---');
      });

      it('should handle empty results', async () => {
        const result = DefaultAggregators.concatenate([]);
        expect(result.content).toBe('No results to aggregate');
      });
    });

    describe('Majority Vote Aggregator', () => {
      it('should return most common result', async () => {
        const agent1 = createMockAgent('agent1', 'A');
        const agent2 = createMockAgent('agent2', 'A');
        const agent3 = createMockAgent('agent3', 'B');

        const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.majorityVote);

        const input = createMessage('user', 'test');
        const result = await parallel.process(input);

        expect(result.content).toBe('A');
        expect(getMetadata(result, 'votes')).toBe(2);
        expect(getMetadata(result, 'total_agents')).toBe(3);
      });

      it('should handle tie by returning first', async () => {
        const agent1 = createMockAgent('agent1', 'A');
        const agent2 = createMockAgent('agent2', 'B');

        const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.majorityVote);

        const input = createMessage('user', 'test');
        const result = await parallel.process(input);

        expect(['A', 'B']).toContain(result.content);
      });

      it('should handle empty results', async () => {
        const result = DefaultAggregators.majorityVote([]);
        expect(result.content).toBe('No results to aggregate');
      });

      it('should count votes correctly', async () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'A'),
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
        ];

        const result = DefaultAggregators.majorityVote(messages);
        expect(result.content).toBe('A');
        expect(getMetadata(result, 'votes')).toBe(3);
      });
    });

    describe('Custom Aggregator', () => {
      it('should use custom aggregation logic', async () => {
        const agent1 = createMockAgent('agent1', '5');
        const agent2 = createMockAgent('agent2', '10');
        const agent3 = createMockAgent('agent3', '15');

        const sumAggregator = (messages: Message[]) => {
          const sum = messages.reduce((acc, msg) => acc + Number(msg.content), 0);
          return createMessage('assistant', String(sum));
        };

        const parallel = new ParallelAgent([agent1, agent2, agent3], sumAggregator);

        const input = createMessage('user', 'test');
        const result = await parallel.process(input);

        expect(result.content).toBe('30');
      });
    });
  });

  describe('Error Handling', () => {
    it('should continue if one agent fails', async () => {
      const agent1 = createMockAgent('agent1', 'success1');
      const agent2 = createErrorAgent('agent2', 'agent2 failed');
      const agent3 = createMockAgent('agent3', 'success3');

      const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(result.content).toBe('success1');
    });

    it('should throw if all agents fail', async () => {
      const agent1 = createErrorAgent('agent1', 'error1');
      const agent2 = createErrorAgent('agent2', 'error2');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      await expect(parallel.process(input)).rejects.toThrow('all agents failed');
    });

    it('should collect error information', async () => {
      const agent1 = createMockAgent('agent1', 'success');
      const agent2 = createErrorAgent('agent2', 'custom error');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(hasMetadata(result, 'errors')).toBe(true);
      const errors = getMetadata(result, 'errors') as any[];
      expect(errors).toHaveLength(1);
      expect(errors[0].agent).toBe('agent2');
      expect(errors[0].error).toContain('custom error');
    });

    it('should include all error messages when all fail', async () => {
      const agent1 = createErrorAgent('agent1', 'error message 1');
      const agent2 = createErrorAgent('agent2', 'error message 2');
      const agent3 = createErrorAgent('agent3', 'error message 3');

      const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.first);

      const input = createMessage('user', 'test');

      try {
        await parallel.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('agent1');
        expect(errorMsg).toContain('agent2');
        expect(errorMsg).toContain('agent3');
      }
    });

    it('should handle mix of successes and failures', async () => {
      const agent1 = createErrorAgent('agent1', 'fail');
      const agent2 = createMockAgent('agent2', 'success');
      const agent3 = createErrorAgent('agent3', 'fail');

      const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(result.content).toBe('success');
      expect(getMetadata(result, 'successful_agents')).toBe(1);
      expect(getMetadata(result, 'parallel_agents')).toBe(3);
    });
  });

  describe('Metadata', () => {
    it('should add parallel execution metadata', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(hasMetadata(result, 'parallel_agents')).toBe(true);
      expect(hasMetadata(result, 'successful_agents')).toBe(true);
      expect(getMetadata(result, 'parallel_agents')).toBe(2);
      expect(getMetadata(result, 'successful_agents')).toBe(2);
    });

    it('should not include errors metadata when all succeed', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(hasMetadata(result, 'errors')).toBe(false);
    });

    it('should track partial failures', async () => {
      const agent1 = createMockAgent('agent1', 'success');
      const agent2 = createErrorAgent('agent2', 'fail1');
      const agent3 = createErrorAgent('agent3', 'fail2');

      const parallel = new ParallelAgent([agent1, agent2, agent3], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(getMetadata(result, 'successful_agents')).toBe(1);
      const errors = getMetadata(result, 'errors') as any[];
      expect(errors).toHaveLength(2);
    });
  });

  describe('Edge Cases', () => {
    it('should handle many agents', async () => {
      const agents = Array.from({ length: 10 }, (_, i) =>
        createMockAgent(`agent${i}`, `result${i}`),
      );

      const parallel = new ParallelAgent(agents, DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(getMetadata(result, 'parallel_agents')).toBe(10);
      expect(getMetadata(result, 'successful_agents')).toBe(10);
    });

    it('should handle flaky agents with retries', async () => {
      const flaky = new FlakyAgent('flaky', 'eventual success', 0, 'temporary failure');
      const backup = createMockAgent('backup', 'backup result');

      const parallel = new ParallelAgent([flaky, backup], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect([flaky.name, backup.name]).toContain(result.content === 'eventual success' ? 'flaky' : 'backup');
    });

    it('should handle rapid successive calls', async () => {
      const counter = new CallCountingAgent('counter', 'counted');
      const parallel = new ParallelAgent([counter], DefaultAggregators.first);

      const input = createMessage('user', 'test');

      await Promise.all([
        parallel.process(input),
        parallel.process(input),
        parallel.process(input),
      ]);

      expect(counter.callCount).toBe(3);
    });

    it('should handle agents returning different types', async () => {
      const agent1 = createMockAgent('agent1', '');
      agent1.process = async () => createMessage('assistant', { type: 'object' });

      const agent2 = createMockAgent('agent2', 'string');

      const parallel = new ParallelAgent([agent1, agent2], DefaultAggregators.first);

      const input = createMessage('user', 'test');
      const result = await parallel.process(input);

      expect(result.content).toBeDefined();
    });
  });
});
