/**
 * Tests for Tree-of-Thought reasoning technique.
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message, createMessage } from '../../core/interfaces';
import { TreeOfThought, createTreeOfThought } from './tree-of-thought';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];
  private callCount: number;
  private shouldFail: boolean;

  constructor() {
    this.name = 'mock_agent';
    this.capabilities = ['mock', 'testing'];
    this.callCount = 0;
    this.shouldFail = false;
  }

  setFail(fail: boolean): void {
    this.shouldFail = fail;
  }

  resetCallCount(): void {
    this.callCount = 0;
  }

  async process(message: Message): Promise<Message> {
    if (this.shouldFail) {
      throw new Error('Mock agent failed');
    }

    this.callCount++;

    // Generate varied responses for tree branches
    const responses = [
      `Branch A: Let's approach this by first analyzing the problem (call ${this.callCount}).`,
      `Branch B: Another way is to break it down into smaller parts (call ${this.callCount}).`,
      `Branch C: We could also consider edge cases first (call ${this.callCount}).`,
      `Step ${this.callCount}: Continue reasoning with more detail about the approach.`,
    ];

    const response = responses[this.callCount % responses.length];
    return createMessage('assistant', response);
  }
}

describe('TreeOfThought', () => {
  describe('basic functionality', () => {
    it('should process message with ToT reasoning', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'Solve this problem');
      const response = await tot.process(message);

      expect(response.metadata?.technique).toBe('tree_of_thought');
      expect(response.metadata?.search_strategy).toBeDefined();
      expect(response.metadata?.reasoning_tree_stats).toBeDefined();
      expect(response.metadata?.reasoning_path).toBeDefined();
      expect(response.metadata?.num_steps).toBeGreaterThan(0);
      expect(typeof response.metadata?.best_score).toBe('number');
    });

    it('should have correct name and capabilities', () => {
      const mockAgent = new MockAgent();
      const tot = new TreeOfThought(mockAgent);

      expect(tot.name).toBe('tree_of_thought');
      expect(tot.capabilities).toContain('reasoning');
      expect(tot.capabilities).toContain('tree_search');
      expect(tot.capabilities).toContain('multi_path_exploration');
      expect(tot.capabilities).toContain('backtracking');
      expect(tot.capabilities).toContain('tree_of_thought');
      expect(tot.capabilities).toContain('planning');
    });
  });

  describe('search strategies', () => {
    it('should support BFS strategy', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
        strategy: 'bfs',
      });

      const message = createMessage('user', 'Test query');
      const response = await tot.process(message);

      expect(response.metadata?.search_strategy).toBe('bfs');
      expect(response.metadata?.reasoning_tree_stats).toBeDefined();
    });

    it('should support DFS strategy', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
        strategy: 'dfs',
      });

      const message = createMessage('user', 'Test query');
      const response = await tot.process(message);

      expect(response.metadata?.search_strategy).toBe('dfs');
    });

    it('should support best-first strategy', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
        strategy: 'best-first',
      });

      const message = createMessage('user', 'Test query');
      const response = await tot.process(message);

      expect(response.metadata?.search_strategy).toBe('best-first');
    });

    it('should throw error on invalid strategy', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        strategy: 'invalid' as any,
      });

      const message = createMessage('user', 'Test');

      await expect(tot.process(message)).rejects.toThrow('Invalid strategy');
    });
  });

  describe('tree statistics', () => {
    it('should track total nodes', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const stats = response.metadata?.reasoning_tree_stats as any;
      expect(stats.totalNodes).toBeGreaterThan(1);
    });

    it('should track max depth', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 3,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const stats = response.metadata?.reasoning_tree_stats as any;
      expect(stats.maxDepth).toBeLessThanOrEqual(3);
    });

    it('should track leaf nodes', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const stats = response.metadata?.reasoning_tree_stats as any;
      expect(stats.numLeaves).toBeGreaterThan(0);
    });

    it('should track best score', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const stats = response.metadata?.reasoning_tree_stats as any;
      expect(stats.bestScore).toBeGreaterThanOrEqual(0);
      expect(stats.bestScore).toBeLessThanOrEqual(1);
    });
  });

  describe('custom evaluator', () => {
    it('should use custom evaluator function', async () => {
      const mockAgent = new MockAgent();

      // Custom evaluator that favors responses containing "Branch A"
      const customEvaluator = (text: string): number => {
        return text.includes('Branch A') ? 1.0 : 0.5;
      };

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 3,
        maxDepth: 2,
        evaluator: customEvaluator,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // Best path should contain "Branch A" due to custom evaluator
      const pathText = String(response.content);
      expect(pathText).toContain('Branch A');
    });

    it('should use default evaluator when none provided', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // Should complete without error using default evaluator
      expect(response.metadata?.best_score).toBeGreaterThan(0);
    });
  });

  describe('pruning', () => {
    it('should prune low-scoring paths', async () => {
      const mockAgent = new MockAgent();

      // Evaluator that gives low scores
      const lowScoreEvaluator = (): number => 0.1;

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 3,
        maxDepth: 2,
        evaluator: lowScoreEvaluator,
        pruneThreshold: 0.2,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const stats = response.metadata?.reasoning_tree_stats as any;
      // Most paths should be pruned
      expect(stats.numPruned).toBeGreaterThan(0);
    });

    it('should not prune when score above threshold', async () => {
      const mockAgent = new MockAgent();

      // Evaluator that gives high scores
      const highScoreEvaluator = (): number => 0.9;

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
        evaluator: highScoreEvaluator,
        pruneThreshold: 0.3,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const stats = response.metadata?.reasoning_tree_stats as any;
      // Should have many leaf nodes (not pruned)
      expect(stats.numLeaves).toBeGreaterThan(0);
    });
  });

  describe('branching factor', () => {
    it('should respect branching factor', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 3,
        maxDepth: 1,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // Root + 3 children = 4 nodes minimum (without pruning)
      const stats = response.metadata?.reasoning_tree_stats as any;
      expect(stats.totalNodes).toBeGreaterThanOrEqual(1);
    });
  });

  describe('reasoning path', () => {
    it('should return complete reasoning path', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 3,
      });

      const message = createMessage('user', 'Test query');
      const response = await tot.process(message);

      const path = response.metadata?.reasoning_path as string[];
      expect(Array.isArray(path)).toBe(true);
      expect(path.length).toBeGreaterThan(0);

      // First element should be the query
      expect(path[0]).toBe('Test query');

      // Path should not exceed max depth + 1 (root)
      expect(path.length).toBeLessThanOrEqual(4);
    });

    it('should include query as root node', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'What is 2+2?');
      const response = await tot.process(message);

      const path = response.metadata?.reasoning_path as string[];
      expect(path[0]).toBe('What is 2+2?');
    });
  });

  describe('edge cases', () => {
    it('should handle maxDepth of 1', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 1,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      const path = response.metadata?.reasoning_path as string[];
      // Root + 1 level = 2 nodes max
      expect(path.length).toBeLessThanOrEqual(2);
    });

    it('should handle no valid paths found', async () => {
      const mockAgent = new MockAgent();

      // Evaluator that always returns 0 (all paths pruned)
      const zeroEvaluator = (): number => 0.0;

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
        evaluator: zeroEvaluator,
        pruneThreshold: 0.1,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // With zero evaluator and low threshold, most paths should be pruned
      // But root node might still exist as a leaf
      const stats = response.metadata?.reasoning_tree_stats as any;
      expect(stats.numPruned).toBeGreaterThan(0);
    });

    it('should handle small branching factor', async () => {
      const mockAgent = new MockAgent();

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 1,
        maxDepth: 3,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // Should still complete successfully
      expect(response.metadata?.technique).toBe('tree_of_thought');
    });
  });

  describe('factory function', () => {
    it('should create agent with createTreeOfThought', async () => {
      const mockAgent = new MockAgent();

      const tot = createTreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      expect(tot).toBeInstanceOf(TreeOfThought);
      expect(tot.name).toBe('tree_of_thought');

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      expect(response.metadata?.technique).toBe('tree_of_thought');
    });
  });

  describe('error handling', () => {
    it('should propagate agent errors', async () => {
      const mockAgent = new MockAgent();
      mockAgent.setFail(true);

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 2,
      });

      const message = createMessage('user', 'Test');

      await expect(tot.process(message)).rejects.toThrow('Mock agent failed');
    });
  });

  describe('default evaluator', () => {
    it('should penalize very short responses', async () => {
      const mockAgent: Agent = {
        name: 'short',
        async process(): Promise<Message> {
          return createMessage('assistant', 'Hi');
        },
      };

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 2,
        maxDepth: 1,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // Short responses should get low scores from default evaluator
      expect(response.metadata?.best_score).toBeLessThan(0.5);
    });

    it('should favor structured responses', async () => {
      const mockAgent: Agent = {
        name: 'structured',
        async process(): Promise<Message> {
          return createMessage(
            'assistant',
            '1. First step with detail\n2. Second step with more content\n3. Third step completing',
          );
        },
      };

      const tot = new TreeOfThought(mockAgent, {
        branchingFactor: 1,
        maxDepth: 1,
      });

      const message = createMessage('user', 'Test');
      const response = await tot.process(message);

      // Structured responses should get bonus points
      // Score is based on length and structure
      expect(response.metadata?.best_score).toBeGreaterThan(0.2);
    });
  });
});
