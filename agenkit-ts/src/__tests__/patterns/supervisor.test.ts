/**
 * Comprehensive tests for Supervisor pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Task planning and delegation
 * - Specialist coordination
 * - Result synthesis
 * - Error handling
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  SupervisorAgent,
  SimplePlanner,
  PlannerAgent,
  Subtask,
} from '../../patterns/supervisor';
import { Message, createMessage, Agent } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

/** Mock planner for testing */
class MockPlanner implements PlannerAgent {
  readonly name = 'MockPlanner';
  private subtasks: Subtask[];
  private synthesisResponse: string;

  constructor(subtasks: Subtask[], synthesisResponse: string = 'synthesized') {
    this.subtasks = subtasks;
    this.synthesisResponse = synthesisResponse;
  }

  get capabilities(): string[] {
    return ['mock', 'planning'];
  }

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'planner direct response');
  }

  async plan(message: Message): Promise<Subtask[]> {
    return this.subtasks;
  }

  async synthesize(original: Message, results: Record<string, Message>): Promise<Message> {
    return createMessage('assistant', this.synthesisResponse);
  }
}

/** Error-throwing planner */
class ErrorPlanner implements PlannerAgent {
  readonly name = 'ErrorPlanner';
  private planError?: Error;
  private synthesisError?: Error;

  constructor(planError?: Error, synthesisError?: Error) {
    this.planError = planError;
    this.synthesisError = synthesisError;
  }

  get capabilities(): string[] {
    return ['mock', 'planning'];
  }

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', 'error planner response');
  }

  async plan(message: Message): Promise<Subtask[]> {
    if (this.planError) {
      throw this.planError;
    }
    // Return a dummy subtask to trigger synthesis path
    return [{ type: 'dummy', message: createMessage('user', 'dummy') }];
  }

  async synthesize(original: Message, results: Record<string, Message>): Promise<Message> {
    if (this.synthesisError) {
      throw this.synthesisError;
    }
    return createMessage('assistant', 'synthesized');
  }
}

describe('SupervisorAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const planner = new MockPlanner([], 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      expect(supervisor).toBeDefined();
      expect(supervisor.name).toBe('SupervisorAgent');
    });

    it('should throw error with null planner', () => {
      const specialist = createMockAgent('specialist', 'done');

      expect(() => new SupervisorAgent(null as any, { specialist })).toThrow(
        'planner is required',
      );
    });

    it('should throw error with undefined planner', () => {
      const specialist = createMockAgent('specialist', 'done');

      expect(() => new SupervisorAgent(undefined as any, { specialist })).toThrow(
        'planner is required',
      );
    });

    it('should throw error with empty specialists', () => {
      const planner = new MockPlanner([], 'result');

      expect(() => new SupervisorAgent(planner, {})).toThrow(
        'at least one specialist is required',
      );
    });

    it('should throw error with null specialists', () => {
      const planner = new MockPlanner([], 'result');

      expect(() => new SupervisorAgent(planner, null as any)).toThrow(
        'at least one specialist is required',
      );
    });

    it('should work with single specialist', () => {
      const planner = new MockPlanner([], 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      expect(supervisor).toBeDefined();
    });
  });

  describe('Capabilities', () => {
    it('should include supervisor capabilities', () => {
      const planner = new MockPlanner([], 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const caps = supervisor.capabilities;
      expect(caps).toContain('supervisor');
      expect(caps).toContain('hierarchical');
      expect(caps).toContain('coordination');
    });

    it('should combine planner and specialist capabilities', () => {
      const planner = new MockPlanner([], 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });
      const caps = supervisor.capabilities;

      expect(caps).toContain('mock');
      expect(caps).toContain('planning');
      expect(caps).toContain('supervisor');
    });

    it('should include all specialist capabilities', () => {
      const planner = new MockPlanner([], 'result');
      const specialist1 = createMockAgent('specialist1', 'done1');
      const specialist2 = createMockAgent('specialist2', 'done2');

      const supervisor = new SupervisorAgent(planner, { specialist1, specialist2 });
      const caps = supervisor.capabilities;

      expect(caps).toContain('mock');
      expect(caps).toContain('supervisor');
    });
  });

  describe('Planning and Delegation', () => {
    it('should handle empty plan by using planner directly', async () => {
      const planner = new MockPlanner([], 'direct result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      // When no subtasks, planner.process() is called instead
      expect(result.content).toBe('planner direct response');
    });

    it('should delegate single subtask to specialist', async () => {
      const subtasks: Subtask[] = [
        {
          type: 'specialist',
          message: createMessage('user', 'do work'),
        },
      ];
      const planner = new MockPlanner(subtasks, 'synthesized result');
      const specialist = createMockAgent('specialist', 'work done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      expect(result.content).toBe('synthesized result');
    });

    it('should delegate multiple subtasks', async () => {
      const subtasks: Subtask[] = [
        { type: 'coder', message: createMessage('user', 'write code') },
        { type: 'tester', message: createMessage('user', 'test code') },
        { type: 'reviewer', message: createMessage('user', 'review code') },
      ];
      const planner = new MockPlanner(subtasks, 'final result');
      const coder = createMockAgent('coder', 'code written');
      const tester = createMockAgent('tester', 'tests passed');
      const reviewer = createMockAgent('reviewer', 'approved');

      const supervisor = new SupervisorAgent(planner, { coder, tester, reviewer });

      const input = createMessage('user', 'implement feature');
      const result = await supervisor.process(input);

      expect(result.content).toBe('final result');
    });

    it('should validate specialist availability', async () => {
      const subtasks: Subtask[] = [
        { type: 'unknown', message: createMessage('user', 'work') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      await expect(supervisor.process(input)).rejects.toThrow(
        "references unknown specialist type 'unknown'",
      );
    });

    it('should include available types in error message', async () => {
      const subtasks: Subtask[] = [
        { type: 'missing', message: createMessage('user', 'work') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const spec1 = createMockAgent('spec1', 'done');
      const spec2 = createMockAgent('spec2', 'done');

      const supervisor = new SupervisorAgent(planner, { spec1, spec2 });

      const input = createMessage('user', 'test');

      try {
        await supervisor.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('spec1');
        expect(errorMsg).toContain('spec2');
      }
    });
  });

  describe('Result Synthesis', () => {
    it('should pass specialist results to synthesize', async () => {
      let capturedResults: Record<string, Message> | undefined;

      class CapturePlanner extends MockPlanner {
        async synthesize(original: Message, results: Record<string, Message>): Promise<Message> {
          capturedResults = results;
          return createMessage('assistant', 'synthesized');
        }
      }

      const subtasks: Subtask[] = [
        { type: 'specialist', message: createMessage('user', 'work') },
      ];
      const planner = new CapturePlanner(subtasks, 'result');
      const specialist = createMockAgent('specialist', 'specialist output');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      await supervisor.process(input);

      expect(capturedResults).toBeDefined();
      expect(Object.keys(capturedResults!)).toHaveLength(1);
      expect(Object.values(capturedResults!)[0].content).toBe('specialist output');
    });

    it('should key results by type and index', async () => {
      let capturedResults: Record<string, Message> | undefined;

      class CapturePlanner extends MockPlanner {
        async synthesize(original: Message, results: Record<string, Message>): Promise<Message> {
          capturedResults = results;
          return createMessage('assistant', 'synthesized');
        }
      }

      const subtasks: Subtask[] = [
        { type: 'spec', message: createMessage('user', 'work1') },
        { type: 'spec', message: createMessage('user', 'work2') },
      ];
      const planner = new CapturePlanner(subtasks, 'result');
      const spec = createMockAgent('spec', 'done');

      const supervisor = new SupervisorAgent(planner, { spec });

      const input = createMessage('user', 'test');
      await supervisor.process(input);

      expect(Object.keys(capturedResults!)).toContain('spec_0');
      expect(Object.keys(capturedResults!)).toContain('spec_1');
    });

    it('should synthesize multiple specialist results', async () => {
      class CustomPlanner extends MockPlanner {
        async synthesize(original: Message, results: Record<string, Message>): Promise<Message> {
          const combined = Object.entries(results)
            .map(([key, msg]) => `${key}: ${msg.content}`)
            .join(', ');
          return createMessage('assistant', combined);
        }
      }

      const subtasks: Subtask[] = [
        { type: 'a', message: createMessage('user', 'work') },
        { type: 'b', message: createMessage('user', 'work') },
      ];
      const planner = new CustomPlanner(subtasks, 'unused');
      const specA = createMockAgent('specA', 'result A');
      const specB = createMockAgent('specB', 'result B');

      const supervisor = new SupervisorAgent(planner, { a: specA, b: specB });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      expect(String(result.content)).toContain('a_0: result A');
      expect(String(result.content)).toContain('b_1: result B');
    });
  });

  describe('Metadata', () => {
    it('should add supervisor metadata to result', async () => {
      const subtasks: Subtask[] = [
        { type: 'specialist', message: createMessage('user', 'work') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      expect(hasMetadata(result, 'supervisor_subtasks')).toBe(true);
      expect(hasMetadata(result, 'supervisor_specialists')).toBe(true);
      expect(hasMetadata(result, 'execution_order')).toBe(true);
    });

    it('should record correct subtask count', async () => {
      const subtasks: Subtask[] = [
        { type: 'a', message: createMessage('user', 'work1') },
        { type: 'b', message: createMessage('user', 'work2') },
        { type: 'c', message: createMessage('user', 'work3') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const specA = createMockAgent('specA', 'done');
      const specB = createMockAgent('specB', 'done');
      const specC = createMockAgent('specC', 'done');

      const supervisor = new SupervisorAgent(planner, { a: specA, b: specB, c: specC });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      expect(getMetadata(result, 'supervisor_subtasks')).toBe(3);
      expect(getMetadata(result, 'supervisor_specialists')).toBe(3);
    });

    it('should record execution order', async () => {
      const subtasks: Subtask[] = [
        { type: 'first', message: createMessage('user', 'work1') },
        { type: 'second', message: createMessage('user', 'work2') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const first = createMockAgent('firstAgent', 'done1');
      const second = createMockAgent('secondAgent', 'done2');

      const supervisor = new SupervisorAgent(planner, { first, second });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      const execOrder = getMetadata(result, 'execution_order') as any[];
      expect(execOrder).toHaveLength(2);
      expect(execOrder[0].index).toBe(0);
      expect(execOrder[0].type).toBe('first');
      expect(execOrder[0].specialist).toBe('firstAgent');
      expect(execOrder[1].index).toBe(1);
      expect(execOrder[1].type).toBe('second');
      expect(execOrder[1].specialist).toBe('secondAgent');
    });
  });

  describe('Error Handling', () => {
    it('should throw error with null message', async () => {
      const planner = new MockPlanner([], 'result');
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      await expect(supervisor.process(null as any)).rejects.toThrow('message cannot be nil');
    });

    it('should handle planning failure', async () => {
      const planner = new ErrorPlanner(new Error('planning failed'));
      const specialist = createMockAgent('specialist', 'done');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      await expect(supervisor.process(input)).rejects.toThrow('planning failed');
    });

    it('should handle specialist failure', async () => {
      const subtasks: Subtask[] = [
        { type: 'specialist', message: createMessage('user', 'work') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const specialist = createErrorAgent('specialist', 'specialist error');

      const supervisor = new SupervisorAgent(planner, { specialist });

      const input = createMessage('user', 'test');
      await expect(supervisor.process(input)).rejects.toThrow("specialist 'specialist' failed");
    });

    it('should include subtask index in error', async () => {
      const subtasks: Subtask[] = [
        { type: 'a', message: createMessage('user', 'work1') },
        { type: 'b', message: createMessage('user', 'work2') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const specA = createMockAgent('specA', 'done');
      const specB = createErrorAgent('specB', 'error in B');

      const supervisor = new SupervisorAgent(planner, { a: specA, b: specB });

      const input = createMessage('user', 'test');

      try {
        await supervisor.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('subtask 1');
        expect(errorMsg).toContain('error in B');
      }
    });

    it('should handle synthesis failure', async () => {
      const planner = new ErrorPlanner(undefined, new Error('synthesis failed'));
      const dummy = createMockAgent('dummy', 'done');

      const supervisor = new SupervisorAgent(planner, { dummy });

      const input = createMessage('user', 'test');
      await expect(supervisor.process(input)).rejects.toThrow('synthesis failed');
    });

    it('should stop on first specialist failure', async () => {
      const subtasks: Subtask[] = [
        { type: 'a', message: createMessage('user', 'work1') },
        { type: 'b', message: createMessage('user', 'work2') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const specA = createErrorAgent('specA', 'error in A');
      const specB = createMockAgent('specB', 'should not run');

      const supervisor = new SupervisorAgent(planner, { a: specA, b: specB });

      const input = createMessage('user', 'test');
      await expect(supervisor.process(input)).rejects.toThrow('error in A');
    });
  });

  describe('SimplePlanner', () => {
    it('should create planner with agent', () => {
      const agent = createMockAgent('agent', 'result');
      const planner = new SimplePlanner(agent);

      expect(planner).toBeDefined();
      expect(planner.name).toBe('SimplePlanner');
    });

    it('should include planning capabilities', () => {
      const agent = createMockAgent('agent', 'result');
      const planner = new SimplePlanner(agent);

      const caps = planner.capabilities;
      expect(caps).toContain('planning');
      expect(caps).toContain('synthesis');
    });

    it('should delegate process to underlying agent', async () => {
      const agent = createMockAgent('agent', 'direct response');
      const planner = new SimplePlanner(agent);

      const input = createMessage('user', 'test');
      const result = await planner.process(input);

      expect(result.content).toBe('direct response');
    });

    it('should return empty plan by default', async () => {
      const agent = createMockAgent('agent', 'result');
      const planner = new SimplePlanner(agent);

      const input = createMessage('user', 'test');
      const plan = await planner.plan(input);

      expect(plan).toEqual([]);
    });

    it('should synthesize results with summary', async () => {
      const agent = createMockAgent('agent', 'result');
      const planner = new SimplePlanner(agent);

      const original = createMessage('user', 'test');
      const results = {
        'spec_0': createMessage('assistant', 'result A'),
        'spec_1': createMessage('assistant', 'result B'),
      };

      const synthesized = await planner.synthesize(original, results);

      expect(String(synthesized.content)).toContain('Synthesis');
      expect(String(synthesized.content)).toContain('spec_0');
      expect(String(synthesized.content)).toContain('spec_1');
    });
  });

  describe('Edge Cases', () => {
    it('should handle many specialists', async () => {
      const subtasks: Subtask[] = Array.from({ length: 10 }, (_, i) => ({
        type: `spec${i}`,
        message: createMessage('user', `work${i}`),
      }));

      const planner = new MockPlanner(subtasks, 'result');
      const specialists: Record<string, Agent> = {};
      for (let i = 0; i < 10; i++) {
        specialists[`spec${i}`] = createMockAgent(`agent${i}`, `result${i}`);
      }

      const supervisor = new SupervisorAgent(planner, specialists);

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      expect(getMetadata(result, 'supervisor_subtasks')).toBe(10);
    });

    it('should handle same specialist type multiple times', async () => {
      const subtasks: Subtask[] = [
        { type: 'worker', message: createMessage('user', 'work1') },
        { type: 'worker', message: createMessage('user', 'work2') },
        { type: 'worker', message: createMessage('user', 'work3') },
      ];
      const planner = new MockPlanner(subtasks, 'result');
      const worker = createMockAgent('worker', 'done');

      const supervisor = new SupervisorAgent(planner, { worker });

      const input = createMessage('user', 'test');
      const result = await supervisor.process(input);

      expect(getMetadata(result, 'supervisor_subtasks')).toBe(3);
    });
  });
});
