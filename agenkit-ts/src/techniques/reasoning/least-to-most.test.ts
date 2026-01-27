/**
 * Tests for Least-to-Most reasoning technique.
 */

import { describe, it, expect, vi } from 'vitest';
import { Agent, Message, createMessage } from '../../core/interfaces';
import { LeastToMost, createLeastToMost, Subproblem } from './least-to-most';

/**
 * Mock agent for testing.
 * Can simulate different responses for decomposition and solving.
 */
class MockAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];
  private responses: string[];
  private responseIndex: number;
  private shouldFail: boolean;

  constructor(responses: string | string[]) {
    this.name = 'mock_agent';
    this.capabilities = ['mock', 'testing'];
    this.responses = Array.isArray(responses) ? responses : [responses];
    this.responseIndex = 0;
    this.shouldFail = false;
  }

  setFail(fail: boolean): void {
    this.shouldFail = fail;
  }

  async process(message: Message): Promise<Message> {
    if (this.shouldFail) {
      throw new Error('Mock agent failed');
    }

    const response = this.responses[this.responseIndex % this.responses.length];
    this.responseIndex++;

    return createMessage('assistant', response);
  }

  resetIndex(): void {
    this.responseIndex = 0;
  }
}

describe('LeastToMost', () => {
  describe('basic functionality', () => {
    it('should process message with least-to-most prompting', async () => {
      const mockAgent = new MockAgent([
        // Decomposition response
        '1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results',
        // Solutions
        '12',
        '10',
        '22',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const message = createMessage('user', 'Calculate 3*4 + 2*5');
      const response = await ltm.process(message);

      expect(response.content).toBe('22');
      expect(response.metadata?.technique).toBe('least_to_most');
      expect(response.metadata?.num_subproblems).toBe(3);
      expect(response.metadata?.subproblems).toHaveLength(3);
      expect(response.metadata?.subproblem_solutions).toHaveLength(3);
    });

    it('should have correct name and capabilities', () => {
      const mockAgent = new MockAgent('response');
      const ltm = new LeastToMost(mockAgent);

      expect(ltm.name).toBe('least_to_most');
      expect(ltm.capabilities).toContain('reasoning');
      expect(ltm.capabilities).toContain('decomposition');
      expect(ltm.capabilities).toContain('compositional_reasoning');
      expect(ltm.capabilities).toContain('least_to_most');
      expect(ltm.capabilities).toContain('sequential_solving');
    });

    it('should decompose problem into subproblems', async () => {
      const mockAgent = new MockAgent([
        '1. First subproblem\n2. Second subproblem\n3. Third subproblem',
        'Solution 1',
        'Solution 2',
        'Solution 3',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const message = createMessage('user', 'Complex problem');
      const response = await ltm.process(message);

      expect(response.metadata?.subproblems).toEqual([
        'First subproblem',
        'Second subproblem',
        'Third subproblem',
      ]);
    });

    it('should solve subproblems sequentially', async () => {
      const mockAgent = new MockAgent([
        '1. Step A\n2. Step B',
        'Answer A',
        'Answer B',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const message = createMessage('user', 'Problem');
      const response = await ltm.process(message);

      expect(response.metadata?.subproblem_solutions).toEqual(['Answer A', 'Answer B']);
    });

    it('should return final solution as response content', async () => {
      const mockAgent = new MockAgent([
        '1. Subproblem 1\n2. Subproblem 2',
        'Intermediate',
        'Final answer',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const message = createMessage('user', 'Problem');
      const response = await ltm.process(message);

      expect(response.content).toBe('Final answer');
      expect(response.role).toBe('assistant');
    });
  });

  describe('configuration options', () => {
    it('should respect maxSubproblems limit', async () => {
      const mockAgent = new MockAgent([
        '1. Sub 1\n2. Sub 2\n3. Sub 3\n4. Sub 4\n5. Sub 5\n6. Sub 6',
        'S1',
        'S2',
        'S3',
      ]);

      const ltm = new LeastToMost(mockAgent, { maxSubproblems: 3 });

      const message = createMessage('user', 'Problem');
      const response = await ltm.process(message);

      expect(response.metadata?.num_subproblems).toBe(3);
      expect(response.metadata?.subproblems).toHaveLength(3);
    });

    it('should use custom decomposer when provided', async () => {
      const customDecomposer = (problem: string) => [
        'Custom step 1',
        'Custom step 2',
        'Custom step 3',
      ];

      const mockAgent = new MockAgent(['Sol 1', 'Sol 2', 'Sol 3']);

      const ltm = new LeastToMost(mockAgent, {
        decomposer: customDecomposer,
      });

      const message = createMessage('user', 'Any problem');
      const response = await ltm.process(message);

      expect(response.metadata?.subproblems).toEqual([
        'Custom step 1',
        'Custom step 2',
        'Custom step 3',
      ]);
    });

    it('should support async custom decomposer', async () => {
      const asyncDecomposer = async (problem: string) => {
        await new Promise((resolve) => setTimeout(resolve, 10));
        return ['Async step 1', 'Async step 2'];
      };

      const mockAgent = new MockAgent(['Sol 1', 'Sol 2']);

      const ltm = new LeastToMost(mockAgent, {
        decomposer: asyncDecomposer,
      });

      const message = createMessage('user', 'Problem');
      const response = await ltm.process(message);

      expect(response.metadata?.subproblems).toEqual(['Async step 1', 'Async step 2']);
    });

    it('should compose solutions when enabled (default)', async () => {
      let capturedPrompts: string[] = [];
      const capturingAgent: Agent = {
        name: 'capturing',
        capabilities: [],
        async process(message: Message): Promise<Message> {
          capturedPrompts.push(String(message.content));

          // Decomposition response
          if (capturedPrompts.length === 1) {
            return createMessage('assistant', '1. Sub 1\n2. Sub 2');
          }

          return createMessage('assistant', `Solution ${capturedPrompts.length - 1}`);
        },
      };

      const ltm = new LeastToMost(capturingAgent, {
        composeSolutions: true,
      });

      await ltm.process(createMessage('user', 'Problem'));

      // Second solution should include first solution as context
      expect(capturedPrompts[2]).toContain('Previous solution 1');
      expect(capturedPrompts[2]).toContain('Solution 1');
    });

    it('should not compose solutions when disabled', async () => {
      let capturedPrompts: string[] = [];
      const capturingAgent: Agent = {
        name: 'capturing',
        capabilities: [],
        async process(message: Message): Promise<Message> {
          capturedPrompts.push(String(message.content));

          if (capturedPrompts.length === 1) {
            return createMessage('assistant', '1. Sub 1\n2. Sub 2');
          }

          return createMessage('assistant', 'Solution');
        },
      };

      const ltm = new LeastToMost(capturingAgent, {
        composeSolutions: false,
      });

      await ltm.process(createMessage('user', 'Problem'));

      // Second solution should NOT include first solution
      expect(capturedPrompts[2]).not.toContain('Previous solution');
    });
  });

  describe('decomposition parsing', () => {
    it('should parse numbered steps with periods', async () => {
      const mockAgent = new MockAgent([
        '1. First\n2. Second\n3. Third',
        'S1',
        'S2',
        'S3',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.subproblems).toEqual(['First', 'Second', 'Third']);
    });

    it('should parse numbered steps with parentheses', async () => {
      const mockAgent = new MockAgent(['1) First\n2) Second\n3) Third', 'S1', 'S2', 'S3']);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.subproblems).toEqual(['First', 'Second', 'Third']);
    });

    it('should skip empty lines during parsing', async () => {
      const mockAgent = new MockAgent([
        '1. First\n\n2. Second\n\n\n3. Third',
        'S1',
        'S2',
        'S3',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.num_subproblems).toBe(3);
    });

    it('should handle single atomic problem when decomposition fails', async () => {
      const mockAgent = new MockAgent(['No valid decomposition', 'Single solution']);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Simple problem'));

      expect(response.metadata?.num_subproblems).toBe(1);
      expect(response.metadata?.subproblems).toEqual(['Simple problem']);
      expect(response.content).toBe('Single solution');
    });

    it('should handle whitespace in decomposition', async () => {
      const mockAgent = new MockAgent([
        '  1.   Trimmed   \n  2.   Also trimmed   ',
        'S1',
        'S2',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.subproblems).toEqual(['Trimmed', 'Also trimmed']);
    });
  });

  describe('metadata tracking', () => {
    it('should track compose_solutions setting in metadata', async () => {
      const mockAgent = new MockAgent(['1. Sub', 'Sol']);

      const ltm1 = new LeastToMost(mockAgent, { composeSolutions: true });
      const response1 = await ltm1.process(createMessage('user', 'Problem'));
      expect(response1.metadata?.compose_solutions).toBe(true);

      mockAgent.resetIndex();

      const ltm2 = new LeastToMost(mockAgent, { composeSolutions: false });
      const response2 = await ltm2.process(createMessage('user', 'Problem'));
      expect(response2.metadata?.compose_solutions).toBe(false);
    });

    it('should include all subproblem texts', async () => {
      const mockAgent = new MockAgent([
        '1. Calculate x\n2. Calculate y\n3. Combine results',
        'X',
        'Y',
        'XY',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.subproblems).toEqual([
        'Calculate x',
        'Calculate y',
        'Combine results',
      ]);
    });

    it('should include all subproblem solutions', async () => {
      const mockAgent = new MockAgent([
        '1. Sub 1\n2. Sub 2',
        'First answer',
        'Second answer',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.subproblem_solutions).toEqual([
        'First answer',
        'Second answer',
      ]);
    });

    it('should include timestamp in response', async () => {
      const mockAgent = new MockAgent(['1. Sub', 'Sol']);

      const ltm = new LeastToMost(mockAgent);

      const before = new Date().toISOString();
      const response = await ltm.process(createMessage('user', 'Problem'));
      const after = new Date().toISOString();

      expect(response.timestamp).toBeDefined();
      expect(response.timestamp! >= before).toBe(true);
      expect(response.timestamp! <= after).toBe(true);
    });
  });

  describe('factory function', () => {
    it('should create instance with factory', () => {
      const mockAgent = new MockAgent('response');

      const ltm = createLeastToMost(mockAgent);

      expect(ltm).toBeInstanceOf(LeastToMost);
      expect(ltm.name).toBe('least_to_most');
    });

    it('should accept config via factory', async () => {
      const mockAgent = new MockAgent(['1. A\n2. B\n3. C\n4. D', 'S1', 'S2', 'S3']);

      const ltm = createLeastToMost(mockAgent, { maxSubproblems: 3 });

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.num_subproblems).toBe(3);
    });
  });

  describe('edge cases', () => {
    it('should handle empty problem string', async () => {
      const mockAgent = new MockAgent(['1. Sub', 'Sol']);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', ''));

      expect(response).toBeDefined();
      expect(response.metadata?.technique).toBe('least_to_most');
    });

    it('should handle maxSubproblems of 1', async () => {
      const mockAgent = new MockAgent(['1. A\n2. B\n3. C', 'Only one']);

      const ltm = new LeastToMost(mockAgent, { maxSubproblems: 1 });

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.metadata?.num_subproblems).toBe(1);
      expect(response.metadata?.subproblems).toHaveLength(1);
    });

    it('should trim whitespace from solutions', async () => {
      const mockAgent = new MockAgent([
        '1. Sub',
        '   Solution with whitespace   ',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      expect(response.content).toBe('Solution with whitespace');
      expect(response.metadata?.subproblem_solutions[0]).toBe('Solution with whitespace');
    });

    it('should handle custom decomposer returning empty array', async () => {
      const emptyDecomposer = () => [];

      const mockAgent = new MockAgent(['Should not be called']);

      const ltm = new LeastToMost(mockAgent, {
        decomposer: emptyDecomposer,
      });

      const response = await ltm.process(createMessage('user', 'Problem'));

      // Should have 0 subproblems and empty final solution
      expect(response.metadata?.num_subproblems).toBe(0);
      expect(response.content).toBe('');
    });

    it('should handle multiline subproblem content', async () => {
      const mockAgent = new MockAgent([
        '1. First part\n   continued\n2. Second',
        'S1',
        'S2',
      ]);

      const ltm = new LeastToMost(mockAgent);

      const response = await ltm.process(createMessage('user', 'Problem'));

      // Should only parse lines starting with numbers
      expect(response.metadata?.num_subproblems).toBe(2);
    });
  });

  describe('error handling', () => {
    it('should propagate errors from agent', async () => {
      const mockAgent = new MockAgent('response');
      mockAgent.setFail(true);

      const ltm = new LeastToMost(mockAgent);

      await expect(ltm.process(createMessage('user', 'Problem'))).rejects.toThrow(
        'Mock agent failed',
      );
    });
  });
});
