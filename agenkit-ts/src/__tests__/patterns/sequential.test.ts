/**
 * Comprehensive tests for Sequential pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Basic pipeline execution
 * - Pipeline transformation
 * - Metadata preservation
 * - Error handling
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import { SequentialAgent } from '../../patterns/sequential';
import { createMessage } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  createAppendAgent,
  createMetadataAgent,
  CallCountingAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

describe('SequentialAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid agents list', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const sequential = new SequentialAgent([agent1, agent2]);

      expect(sequential).toBeDefined();
      expect(sequential.name).toBe('SequentialAgent');
    });

    it('should throw error with empty agents list', () => {
      expect(() => new SequentialAgent([])).toThrow('at least one agent is required');
    });

    it('should throw error with null agents', () => {
      expect(() => new SequentialAgent(null as any)).toThrow('at least one agent is required');
    });

    it('should throw error with undefined agents', () => {
      expect(() => new SequentialAgent(undefined as any)).toThrow(
        'at least one agent is required',
      );
    });

    it('should work with single agent', () => {
      const agent = createMockAgent('solo', 'result');
      const sequential = new SequentialAgent([agent]);

      expect(sequential).toBeDefined();
      expect(sequential.capabilities).toContain('sequential');
    });
  });

  describe('Capabilities', () => {
    it('should include sequential and pipeline capabilities', () => {
      const agent = createMockAgent('agent', 'result');
      const sequential = new SequentialAgent([agent]);

      const caps = sequential.capabilities;
      expect(caps).toContain('sequential');
      expect(caps).toContain('pipeline');
    });

    it('should combine capabilities from all agents', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const sequential = new SequentialAgent([agent1, agent2]);
      const caps = sequential.capabilities;

      expect(caps).toContain('mock');
      expect(caps).toContain('sequential');
      expect(caps).toContain('pipeline');
    });

    it('should deduplicate capabilities', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const sequential = new SequentialAgent([agent1, agent2]);
      const caps = sequential.capabilities;

      const mockCount = caps.filter((c) => c === 'mock').length;
      expect(mockCount).toBe(1);
    });
  });

  describe('Basic Processing', () => {
    it('should process message through single agent', async () => {
      const agent = createMockAgent('agent', 'processed');
      const sequential = new SequentialAgent([agent]);

      const input = createMessage('user', 'test input');
      const result = await sequential.process(input);

      validateMessage(result);
      expect(result.content).toBe('processed');
    });

    it('should process message through multiple agents', async () => {
      const agent1 = createMockAgent('agent1', 'step1');
      const agent2 = createMockAgent('agent2', 'step2');
      const agent3 = createMockAgent('agent3', 'final');

      const sequential = new SequentialAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test input');
      const result = await sequential.process(input);

      expect(result.content).toBe('final');
    });

    it('should throw error with null message', async () => {
      const agent = createMockAgent('agent', 'result');
      const sequential = new SequentialAgent([agent]);

      await expect(sequential.process(null as any)).rejects.toThrow('message cannot be nil');
    });

    it('should throw error with undefined message', async () => {
      const agent = createMockAgent('agent', 'result');
      const sequential = new SequentialAgent([agent]);

      await expect(sequential.process(undefined as any)).rejects.toThrow('message cannot be nil');
    });
  });

  describe('Pipeline Transformation', () => {
    it('should pass each agents output to next agent', async () => {
      const agent1 = createAppendAgent('agent1', ' -> stage1');
      const agent2 = createAppendAgent('agent2', ' -> stage2');
      const agent3 = createAppendAgent('agent3', ' -> stage3');

      const sequential = new SequentialAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'input');
      const result = await sequential.process(input);

      expect(result.content).toBe('input -> stage1 -> stage2 -> stage3');
    });

    it('should transform data progressively through stages', async () => {
      const upperCase = createMockAgent('upper', '');
      upperCase.process = async (msg) =>
        createMessage('assistant', String(msg.content).toUpperCase());

      const addPrefix = createMockAgent('prefix', '');
      addPrefix.process = async (msg) => createMessage('assistant', `RESULT: ${msg.content}`);

      const sequential = new SequentialAgent([upperCase, addPrefix]);

      const input = createMessage('user', 'hello world');
      const result = await sequential.process(input);

      expect(result.content).toBe('RESULT: HELLO WORLD');
    });

    it('should handle empty content', async () => {
      const agent1 = createAppendAgent('agent1', '-suffix');
      const sequential = new SequentialAgent([agent1]);

      const input = createMessage('user', '');
      const result = await sequential.process(input);

      expect(result.content).toBe('-suffix');
    });

    it('should handle object content transformation', async () => {
      const agent1 = createMockAgent('agent1', '');
      agent1.process = async (msg) => {
        const data = msg.content as any;
        return createMessage('assistant', { ...data, processed: true });
      };

      const agent2 = createMockAgent('agent2', '');
      agent2.process = async (msg) => {
        const data = msg.content as any;
        return createMessage('assistant', { ...data, validated: true });
      };

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', { value: 42 });
      const result = await sequential.process(input);

      expect(result.content).toEqual({
        value: 42,
        processed: true,
        validated: true,
      });
    });
  });

  describe('Metadata Preservation', () => {
    it('should add pipeline metadata to result', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await sequential.process(input);

      expect(hasMetadata(result, 'pipeline_stages')).toBe(true);
      expect(hasMetadata(result, 'pipeline_length')).toBe(true);
      expect(getMetadata(result, 'pipeline_length')).toBe(2);
    });

    it('should record stage information', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');
      const agent3 = createMockAgent('agent3', 'result3');

      const sequential = new SequentialAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      const result = await sequential.process(input);

      const stages = getMetadata(result, 'pipeline_stages') as any[];
      expect(stages).toHaveLength(3);
      expect(stages[0].agent).toBe('agent1');
      expect(stages[0].stage).toBe(0);
      expect(stages[1].agent).toBe('agent2');
      expect(stages[1].stage).toBe(1);
      expect(stages[2].agent).toBe('agent3');
      expect(stages[2].stage).toBe(2);
    });

    it('should preserve agent metadata in stages', async () => {
      const agent1 = createMetadataAgent('agent1', 'result1', { stage1_key: 'value1' });
      const agent2 = createMetadataAgent('agent2', 'result2', { stage2_key: 'value2' });

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await sequential.process(input);

      const stages = getMetadata(result, 'pipeline_stages') as any[];
      expect(stages[0].metadata?.stage1_key).toBe('value1');
      expect(stages[1].metadata?.stage2_key).toBe('value2');
    });

    it('should handle agents without metadata', async () => {
      const agent = createMockAgent('agent', 'result');
      const sequential = new SequentialAgent([agent]);

      const input = createMessage('user', 'test');
      const result = await sequential.process(input);

      expect(hasMetadata(result, 'pipeline_stages')).toBe(true);
      const stages = getMetadata(result, 'pipeline_stages') as any[];
      expect(stages).toHaveLength(1);
    });
  });

  describe('Error Handling', () => {
    it('should stop pipeline on first error', async () => {
      const agent1 = createMockAgent('agent1', 'step1');
      const agent2 = createErrorAgent('agent2', 'agent2 failed');
      const agent3 = createMockAgent('agent3', 'step3');

      const sequential = new SequentialAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      await expect(sequential.process(input)).rejects.toThrow('agent 1 (agent2) failed');
    });

    it('should include agent name in error', async () => {
      const agent = createErrorAgent('failing-agent', 'custom error message');
      const sequential = new SequentialAgent([agent]);

      const input = createMessage('user', 'test');
      await expect(sequential.process(input)).rejects.toThrow('agent 0 (failing-agent) failed');
    });

    it('should include original error message', async () => {
      const agent = createErrorAgent('agent', 'original error');
      const sequential = new SequentialAgent([agent]);

      const input = createMessage('user', 'test');
      await expect(sequential.process(input)).rejects.toThrow('original error');
    });

    it('should handle error in first agent', async () => {
      const agent1 = createErrorAgent('agent1', 'first agent error');
      const agent2 = createMockAgent('agent2', 'result2');

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      await expect(sequential.process(input)).rejects.toThrow('agent 0 (agent1) failed');
    });

    it('should handle error in last agent', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createErrorAgent('agent2', 'last agent error');

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      await expect(sequential.process(input)).rejects.toThrow('agent 1 (agent2) failed');
    });

    it('should handle error in middle agent', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createErrorAgent('agent2', 'middle agent error');
      const agent3 = createMockAgent('agent3', 'result3');

      const sequential = new SequentialAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      await expect(sequential.process(input)).rejects.toThrow('agent 1 (agent2) failed');
    });
  });

  describe('Edge Cases', () => {
    it('should handle very long pipelines', async () => {
      const agents = Array.from({ length: 10 }, (_, i) =>
        createAppendAgent(`agent${i}`, `-${i}`),
      );

      const sequential = new SequentialAgent(agents);

      const input = createMessage('user', 'start');
      const result = await sequential.process(input);

      expect(String(result.content)).toContain('start-0-1-2-3-4-5-6-7-8-9');
      expect(getMetadata(result, 'pipeline_length')).toBe(10);
    });

    it('should handle agents with different response types', async () => {
      const agent1 = createMockAgent('agent1', '');
      agent1.process = async () => createMessage('assistant', { data: 'object' });

      const agent2 = createMockAgent('agent2', '');
      agent2.process = async () => createMessage('assistant', 'string result');

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await sequential.process(input);

      expect(result.content).toBe('string result');
    });

    it('should maintain message role through pipeline', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const sequential = new SequentialAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await sequential.process(input);

      expect(result.role).toBe('assistant');
    });

    it('should handle rapid successive calls', async () => {
      const counter = new CallCountingAgent('counter', 'counted');
      const sequential = new SequentialAgent([counter]);

      const input = createMessage('user', 'test');

      await Promise.all([
        sequential.process(input),
        sequential.process(input),
        sequential.process(input),
      ]);

      expect(counter.callCount).toBe(3);
    });
  });
});
