/**
 * Tests for Self-Consistency reasoning technique.
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message, createMessage } from '../../core/interfaces';
import { SelfConsistencyAgent, createSelfConsistencyAgent } from './self-consistency';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];
  private readonly responses: string[];
  private callCount: number;
  private shouldFail: boolean;

  constructor(responses: string[]) {
    this.name = 'mock_agent';
    this.capabilities = ['mock', 'testing'];
    this.responses = responses;
    this.callCount = 0;
    this.shouldFail = false;
  }

  setFail(fail: boolean): void {
    this.shouldFail = fail;
  }

  async process(message: Message): Promise<Message> {
    if (this.shouldFail) {
      throw new Error('Mock agent failed');
    }

    // Return responses in round-robin fashion
    const response = this.responses[this.callCount % this.responses.length];
    this.callCount++;

    return createMessage('assistant', response);
  }
}

describe('SelfConsistencyAgent', () => {
  describe('basic functionality', () => {
    it('should process message with majority voting', async () => {
      const mockAgent = new MockAgent([
        'The answer is 42.',
        'I think it\'s 42.',
        'The answer is 41.',
        '42 is the answer.',
        'The answer is 42.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 5,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'What is the answer?');
      const response = await sc.process(message);

      expect(String(response.content)).toContain('42');
      expect(response.metadata?.technique).toBe('self_consistency');
      expect(response.metadata?.num_samples).toBe(5);
      expect(response.metadata?.voting_strategy).toBe('majority');
      expect(typeof response.metadata?.consistency_score).toBe('number');
      expect(response.metadata?.samples).toHaveLength(5);
      expect(response.metadata?.extracted_answers).toHaveLength(5);
    });

    it('should have correct name and capabilities', () => {
      const mockAgent = new MockAgent(['response']);
      const sc = new SelfConsistencyAgent(mockAgent);

      expect(sc.name).toBe('self_consistency');
      expect(sc.capabilities).toContain('reasoning');
      expect(sc.capabilities).toContain('self_consistency');
      expect(sc.capabilities).toContain('majority_voting');
      expect(sc.capabilities).toContain('reliability');
      expect(sc.capabilities).toContain('consensus');
    });
  });

  describe('majority voting', () => {
    it('should select most common answer', async () => {
      const mockAgent = new MockAgent([
        'The answer is Paris.',
        'The answer is London.',
        'The answer is Paris.',
        'The answer is Paris.',
        'The answer is London.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 5,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'What is the capital of France?');
      const response = await sc.process(message);

      expect(String(response.content).toLowerCase()).toContain('paris');
      expect(response.metadata?.consistency_score).toBe(0.6); // 3/5
    });

    it('should be case-insensitive', async () => {
      const mockAgent = new MockAgent([
        'The answer is PARIS.',
        'The answer is Paris.',
        'The answer is paris.',
        'The answer is PaRiS.',
        'The answer is London.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 5,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'What is the capital?');
      const response = await sc.process(message);

      expect(String(response.content).toLowerCase()).toContain('paris');
      expect(response.metadata?.consistency_score).toBe(0.8); // 4/5
    });
  });

  describe('weighted voting', () => {
    it('should favor longer responses', async () => {
      const mockAgent = new MockAgent([
        'The answer is Paris.',
        'The answer is Paris.',
        'The answer is Paris.',
        'After careful consideration and analysis of the question, I believe London is correct.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 4,
        votingStrategy: 'weighted',
      });

      const message = createMessage('user', 'What is the capital?');
      const response = await sc.process(message);

      expect(String(response.content).toLowerCase()).toContain('london');
    });
  });

  describe('first strategy', () => {
    it('should return first answer', async () => {
      const mockAgent = new MockAgent([
        'The answer is A.',
        'The answer is A.',
        'The answer is A.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 3,
        votingStrategy: 'first',
      });

      const message = createMessage('user', 'Test question');
      const response = await sc.process(message);

      expect(String(response.content)).toContain('A');
      expect(response.metadata?.consistency_score).toBe(1.0);
    });
  });

  describe('custom answer extractor', () => {
    it('should use custom extractor', async () => {
      const mockAgent = new MockAgent([
        '[ANSWER: 42]',
        '[ANSWER: 42]',
        '[ANSWER: 43]',
      ]);

      const customExtractor = (text: string): string => {
        const match = text.match(/\[ANSWER: ([^\]]+)\]/);
        return match ? match[1] : text;
      };

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 3,
        votingStrategy: 'majority',
        answerExtractor: customExtractor,
      });

      const message = createMessage('user', 'Test question');
      const response = await sc.process(message);

      expect(response.content).toBe('42');
    });
  });

  describe('answer extraction patterns', () => {
    const testPatterns = [
      {
        name: 'therefore pattern',
        input: 'Let me think. Step 1... Step 2... Therefore, the answer is 42.',
        expected: '42',
      },
      {
        name: 'thus pattern',
        input: 'After analysis, thus, 42 is correct.',
        expected: '42',
      },
      {
        name: 'so pattern',
        input: 'Calculating... so, the result is 100.',
        expected: '100',
      },
      {
        name: 'the answer is pattern',
        input: 'Based on the data, the answer is Paris.',
        expected: 'paris',
      },
      {
        name: 'math equation pattern',
        input: 'Let x = 5, then 2x = 10. x = 5',
        expected: '5',
      },
      {
        name: 'conclusion pattern',
        input: 'After review, conclusion: the hypothesis is true.',
        expected: 'hypothesis',
      },
      {
        name: 'result pattern',
        input: 'Computation complete. Result: 42',
        expected: '42',
      },
      {
        name: 'last line fallback',
        input: 'Step 1: do this\nStep 2: do that\nFinal answer is here',
        expected: 'final answer is here',
      },
    ];

    testPatterns.forEach(({ name, input, expected }) => {
      it(`should extract answer from ${name}`, async () => {
        const mockAgent = new MockAgent([input]);

        const sc = new SelfConsistencyAgent(mockAgent, {
          numSamples: 1,
          votingStrategy: 'first',
        });

        const message = createMessage('user', 'Test');
        const response = await sc.process(message);

        expect(String(response.content).toLowerCase()).toContain(expected.toLowerCase());
      });
    });
  });

  describe('edge cases', () => {
    it('should handle single sample', async () => {
      const mockAgent = new MockAgent(['The answer is 42.']);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 1,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'Test question');
      const response = await sc.process(message);

      expect(String(response.content)).toContain('42');
      expect(response.metadata?.consistency_score).toBe(1.0);
    });

    it('should handle perfect consistency', async () => {
      const mockAgent = new MockAgent([
        'The answer is 42.',
        'The answer is 42.',
        'The answer is 42.',
        'The answer is 42.',
        'The answer is 42.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 5,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'Test question');
      const response = await sc.process(message);

      expect(response.metadata?.consistency_score).toBe(1.0);
    });

    it('should handle no consistency', async () => {
      const mockAgent = new MockAgent([
        'The answer is 1.',
        'The answer is 2.',
        'The answer is 3.',
        'The answer is 4.',
        'The answer is 5.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 5,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'Test question');
      const response = await sc.process(message);

      expect(response.metadata?.consistency_score).toBe(0.2); // 1/5
    });
  });

  describe('error handling', () => {
    it('should propagate agent errors', async () => {
      const mockAgent = new MockAgent(['response']);
      mockAgent.setFail(true);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 3,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'Test question');

      await expect(sc.process(message)).rejects.toThrow('Sampling failed');
    });

    it('should throw on invalid voting strategy', async () => {
      const mockAgent = new MockAgent(['response']);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 3,
        votingStrategy: 'majority',
      });

      // Manually set invalid strategy (not possible via public API)
      (sc as any).votingStrategy = 'invalid';

      const message = createMessage('user', 'Test question');

      await expect(sc.process(message)).rejects.toThrow('Invalid voting strategy');
    });
  });

  describe('metadata', () => {
    it('should include answer counts', async () => {
      const mockAgent = new MockAgent([
        'The answer is A.',
        'The answer is B.',
        'The answer is A.',
        'The answer is C.',
        'The answer is A.',
      ]);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 5,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'Test question');
      const response = await sc.process(message);

      const answerCounts = response.metadata?.answer_counts as Record<string, number>;
      expect(answerCounts['a']).toBe(3);
      expect(answerCounts['b']).toBe(1);
      expect(answerCounts['c']).toBe(1);
    });

    it('should include base agent name', async () => {
      const mockAgent = new MockAgent(['response']);

      const sc = new SelfConsistencyAgent(mockAgent, {
        numSamples: 1,
        votingStrategy: 'majority',
      });

      const message = createMessage('user', 'Test');
      const response = await sc.process(message);

      expect(response.metadata?.base_agent).toBe('mock_agent');
    });
  });

  describe('factory function', () => {
    it('should create agent with createSelfConsistencyAgent', async () => {
      const mockAgent = new MockAgent(['The answer is 42.']);

      const sc = createSelfConsistencyAgent(mockAgent, {
        numSamples: 3,
        votingStrategy: 'majority',
      });

      expect(sc).toBeInstanceOf(SelfConsistencyAgent);
      expect(sc.name).toBe('self_consistency');

      const message = createMessage('user', 'Test');
      const response = await sc.process(message);

      expect(String(response.content)).toContain('42');
    });
  });
});
