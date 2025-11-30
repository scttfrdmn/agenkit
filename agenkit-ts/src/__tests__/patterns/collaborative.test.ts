/**
 * Comprehensive tests for Collaborative pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Multi-round collaboration
 * - Consensus detection
 * - Merge strategies
 * - Error handling
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  CollaborativeAgent,
  DefaultConsensusFunc,
  DefaultMergeFunc,
  ConsensusFunc,
  MergeFunc,
} from '../../patterns/collaborative';
import { Message, createMessage } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  CallCountingAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

describe('CollaborativeAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        mergeFunc: DefaultMergeFunc.first,
      });

      expect(collaborative).toBeDefined();
      expect(collaborative.name).toBe('CollaborativeAgent');
    });

    it('should throw error with null config', () => {
      expect(() => new CollaborativeAgent(null as any)).toThrow('config is required');
    });

    it('should throw error with undefined config', () => {
      expect(() => new CollaborativeAgent(undefined as any)).toThrow('config is required');
    });

    it('should throw error with less than 2 agents', () => {
      const agent = createMockAgent('agent', 'result');

      expect(
        () =>
          new CollaborativeAgent({
            agents: [agent],
            mergeFunc: DefaultMergeFunc.first,
          }),
      ).toThrow('at least two agents are required');
    });

    it('should throw error with empty agents', () => {
      expect(
        () =>
          new CollaborativeAgent({
            agents: [],
            mergeFunc: DefaultMergeFunc.first,
          }),
      ).toThrow('at least two agents are required');
    });

    it('should throw error with missing merge function', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      expect(
        () =>
          new CollaborativeAgent({
            agents: [agent1, agent2],
            mergeFunc: null as any,
          }),
      ).toThrow('merge function is required');
    });

    it('should use default max rounds if not provided', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        mergeFunc: DefaultMergeFunc.first,
      });

      expect(collaborative).toBeDefined();
    });

    it('should accept custom max rounds', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 5,
        mergeFunc: DefaultMergeFunc.first,
      });

      expect(collaborative).toBeDefined();
    });
  });

  describe('Capabilities', () => {
    it('should include collaborative capabilities', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        mergeFunc: DefaultMergeFunc.first,
      });

      const caps = collaborative.capabilities;
      expect(caps).toContain('collaborative');
      expect(caps).toContain('iterative');
      expect(caps).toContain('consensus');
    });

    it('should combine capabilities from all agents', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        mergeFunc: DefaultMergeFunc.first,
      });

      const caps = collaborative.capabilities;
      expect(caps).toContain('mock');
      expect(caps).toContain('collaborative');
    });
  });

  describe('Multi-Round Collaboration', () => {
    it('should execute single round when max rounds is 1', async () => {
      const counter1 = new CallCountingAgent('counter1', 'A');
      const counter2 = new CallCountingAgent('counter2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [counter1, counter2],
        maxRounds: 1,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      await collaborative.process(input);

      expect(counter1.callCount).toBe(1);
      expect(counter2.callCount).toBe(1);
    });

    it('should execute multiple rounds', async () => {
      const counter1 = new CallCountingAgent('counter1', 'A');
      const counter2 = new CallCountingAgent('counter2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [counter1, counter2],
        maxRounds: 3,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      await collaborative.process(input);

      expect(counter1.callCount).toBe(3);
      expect(counter2.callCount).toBe(3);
    });

    it('should stop when consensus reached', async () => {
      const agent1 = createMockAgent('agent1', 'agreed');
      const agent2 = createMockAgent('agent2', 'agreed');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 5,
        consensusFunc: DefaultConsensusFunc.exactMatch,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      expect(getMetadata(result, 'collaboration_rounds')).toBe(1);
      expect(getMetadata(result, 'stop_reason')).toBe('consensus');
    });

    it('should continue until max rounds without consensus', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createMockAgent('agent2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 3,
        consensusFunc: DefaultConsensusFunc.exactMatch,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      expect(getMetadata(result, 'collaboration_rounds')).toBe(3);
      expect(getMetadata(result, 'stop_reason')).toBe('max_rounds');
    });

    it('should provide context to agents in later rounds', async () => {
      const counter = new CallCountingAgent('counter', 'response');

      const collaborative = new CollaborativeAgent({
        agents: [counter, counter],
        maxRounds: 2,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'original');
      await collaborative.process(input);

      // In round 0, should see original
      // In round 1, should see original + previous responses
      expect(counter.lastMessage?.content).toBeDefined();
      expect(String(counter.lastMessage?.content)).toContain('Collaboration Round');
    });

    it('should throw error with null message', async () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        mergeFunc: DefaultMergeFunc.first,
      });

      await expect(collaborative.process(null as any)).rejects.toThrow('message cannot be nil');
    });
  });

  describe('Consensus Detection', () => {
    describe('Exact Match', () => {
      it('should detect exact match consensus', async () => {
        const messages = [
          createMessage('assistant', 'same'),
          createMessage('assistant', 'same'),
          createMessage('assistant', 'same'),
        ];

        expect(DefaultConsensusFunc.exactMatch(messages)).toBe(true);
      });

      it('should not detect consensus with different responses', async () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
          createMessage('assistant', 'C'),
        ];

        expect(DefaultConsensusFunc.exactMatch(messages)).toBe(false);
      });

      it('should handle single message as consensus', async () => {
        const messages = [createMessage('assistant', 'solo')];
        expect(DefaultConsensusFunc.exactMatch(messages)).toBe(true);
      });

      it('should handle empty messages', async () => {
        expect(DefaultConsensusFunc.exactMatch([])).toBe(true);
      });
    });

    describe('Majority Agreement', () => {
      it('should detect majority consensus', async () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
        ];

        expect(DefaultConsensusFunc.majorityAgreement(messages)).toBe(true);
      });

      it('should not detect consensus without majority', async () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
          createMessage('assistant', 'C'),
        ];

        expect(DefaultConsensusFunc.majorityAgreement(messages)).toBe(false);
      });

      it('should require true majority not just plurality', async () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
          createMessage('assistant', 'B'),
        ];

        expect(DefaultConsensusFunc.majorityAgreement(messages)).toBe(false);
      });

      it('should handle single message', async () => {
        const messages = [createMessage('assistant', 'solo')];
        expect(DefaultConsensusFunc.majorityAgreement(messages)).toBe(true);
      });
    });

    describe('Similarity Threshold', () => {
      it('should create threshold function', () => {
        const func = DefaultConsensusFunc.similarityThreshold(0.8);
        expect(func).toBeDefined();
      });

      it('should detect similar responses', async () => {
        const func = DefaultConsensusFunc.similarityThreshold(0.5);
        const messages = [
          createMessage('assistant', 'The answer is definitely 42'),
          createMessage('assistant', 'The answer is definite'),
        ];

        // The simple similarity check looks for substring matches in first 20 chars
        // Both messages contain "The answer is definite" prefix
        expect(func(messages)).toBe(true);
      });
    });

    describe('Custom Consensus', () => {
      it('should use custom consensus function', async () => {
        const customConsensus: ConsensusFunc = (messages) => {
          return messages.length >= 2;
        };

        const agent1 = createMockAgent('agent1', 'A');
        const agent2 = createMockAgent('agent2', 'B');

        const collaborative = new CollaborativeAgent({
          agents: [agent1, agent2],
          maxRounds: 5,
          consensusFunc: customConsensus,
          mergeFunc: DefaultMergeFunc.first,
        });

        const input = createMessage('user', 'test');
        const result = await collaborative.process(input);

        expect(getMetadata(result, 'collaboration_rounds')).toBe(1);
        expect(getMetadata(result, 'stop_reason')).toBe('consensus');
      });
    });
  });

  describe('Merge Strategies', () => {
    describe('First Merge', () => {
      it('should return first response', () => {
        const messages = [
          createMessage('assistant', 'first'),
          createMessage('assistant', 'second'),
        ];

        const result = DefaultMergeFunc.first(messages);
        expect(result.content).toBe('first');
      });

      it('should handle empty messages', () => {
        const result = DefaultMergeFunc.first([]);
        expect(result.content).toBe('No responses to merge');
      });
    });

    describe('Last Merge', () => {
      it('should return last response', () => {
        const messages = [
          createMessage('assistant', 'first'),
          createMessage('assistant', 'last'),
        ];

        const result = DefaultMergeFunc.last(messages);
        expect(result.content).toBe('last');
      });

      it('should handle empty messages', () => {
        const result = DefaultMergeFunc.last([]);
        expect(result.content).toBe('No responses to merge');
      });
    });

    describe('Concatenate Merge', () => {
      it('should combine all responses', () => {
        const messages = [
          createMessage('assistant', 'first'),
          createMessage('assistant', 'second'),
          createMessage('assistant', 'third'),
        ];

        const result = DefaultMergeFunc.concatenate(messages);
        expect(String(result.content)).toContain('first');
        expect(String(result.content)).toContain('second');
        expect(String(result.content)).toContain('third');
      });

      it('should include separator', () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
        ];

        const result = DefaultMergeFunc.concatenate(messages);
        expect(String(result.content)).toContain('---');
      });
    });

    describe('Vote Merge', () => {
      it('should return most common response', () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
        ];

        const result = DefaultMergeFunc.vote(messages);
        expect(result.content).toBe('A');
        expect(getMetadata(result, 'votes')).toBe(2);
        expect(getMetadata(result, 'total')).toBe(3);
      });

      it('should handle tie by returning first winner', () => {
        const messages = [
          createMessage('assistant', 'A'),
          createMessage('assistant', 'B'),
        ];

        const result = DefaultMergeFunc.vote(messages);
        expect(['A', 'B']).toContain(result.content);
      });
    });

    describe('Custom Merge', () => {
      it('should use custom merge function', async () => {
        const customMerge: MergeFunc = (messages) => {
          const count = messages.length;
          return createMessage('assistant', `Merged ${count} responses`);
        };

        const agent1 = createMockAgent('agent1', 'A');
        const agent2 = createMockAgent('agent2', 'B');

        const collaborative = new CollaborativeAgent({
          agents: [agent1, agent2],
          maxRounds: 1,
          mergeFunc: customMerge,
        });

        const input = createMessage('user', 'test');
        const result = await collaborative.process(input);

        expect(result.content).toBe('Merged 2 responses');
      });
    });
  });

  describe('Metadata', () => {
    it('should add collaboration metadata', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createMockAgent('agent2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 2,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      expect(hasMetadata(result, 'collaboration_rounds')).toBe(true);
      expect(hasMetadata(result, 'collaboration_agents')).toBe(true);
      expect(hasMetadata(result, 'stop_reason')).toBe(true);
      expect(hasMetadata(result, 'rounds')).toBe(true);
    });

    it('should record round details', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createMockAgent('agent2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 2,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      const rounds = getMetadata(result, 'rounds') as any[];
      expect(rounds).toHaveLength(2);
      expect(rounds[0].round).toBe(0);
      expect(rounds[0].responses).toBe(2);
      expect(rounds[1].round).toBe(1);
      expect(rounds[1].responses).toBe(2);
    });

    it('should record consensus status per round', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createMockAgent('agent2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 2,
        consensusFunc: DefaultConsensusFunc.exactMatch,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      const rounds = getMetadata(result, 'rounds') as any[];
      expect(rounds[0].consensus).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('should handle agent failure in first round', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createErrorAgent('agent2', 'agent2 failed');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 1,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      await expect(collaborative.process(input)).rejects.toThrow('agent2 failed');
    });

    it('should include round number in error', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createErrorAgent('agent2', 'error');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 3,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');

      try {
        await collaborative.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('round 0');
      }
    });

    it('should handle error in later round', async () => {
      let callCount = 0;
      const flakyAgent = createMockAgent('flaky', '');
      flakyAgent.process = async () => {
        callCount++;
        if (callCount > 2) {
          throw new Error('failed in round 1');
        }
        return createMessage('assistant', 'ok');
      };

      const agent2 = createMockAgent('agent2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [flakyAgent, agent2],
        maxRounds: 3,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      await expect(collaborative.process(input)).rejects.toThrow('failed in round 1');
    });
  });

  describe('Edge Cases', () => {
    it('should handle many agents', async () => {
      const agents = Array.from({ length: 5 }, (_, i) => createMockAgent(`agent${i}`, `${i}`));

      const collaborative = new CollaborativeAgent({
        agents,
        maxRounds: 1,
        mergeFunc: DefaultMergeFunc.concatenate,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      expect(getMetadata(result, 'collaboration_agents')).toBe(5);
    });

    it('should handle many rounds', async () => {
      const agent1 = createMockAgent('agent1', 'A');
      const agent2 = createMockAgent('agent2', 'B');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2],
        maxRounds: 10,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      expect(getMetadata(result, 'collaboration_rounds')).toBe(10);
    });

    it('should handle consensus on first round', async () => {
      const agent1 = createMockAgent('agent1', 'agreed');
      const agent2 = createMockAgent('agent2', 'agreed');
      const agent3 = createMockAgent('agent3', 'agreed');

      const collaborative = new CollaborativeAgent({
        agents: [agent1, agent2, agent3],
        maxRounds: 5,
        consensusFunc: DefaultConsensusFunc.exactMatch,
        mergeFunc: DefaultMergeFunc.first,
      });

      const input = createMessage('user', 'test');
      const result = await collaborative.process(input);

      expect(getMetadata(result, 'collaboration_rounds')).toBe(1);
      expect(getMetadata(result, 'stop_reason')).toBe('consensus');
    });
  });
});
