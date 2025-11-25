/**
 * Tests for Autonomous Agent pattern.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  AutonomousAgent,
  Goal,
  GoalStatus,
  createGoal,
  AutonomousResult,
} from '../patterns/autonomous';
import { createMessage } from '../core/interfaces';

// ============================================================================
// Mock Implementations
// ============================================================================

class MockAutonomousAgent extends AutonomousAgent {
  public workLog: string[] = [];

  protected async workOnGoal(goal: Goal): Promise<string> {
    this.workLog.push(goal.description);
    await new Promise(resolve => setTimeout(resolve, 10)); // Simulate work
    return `Completed: ${goal.description}`;
  }
}

class CountingAgent extends AutonomousAgent {
  public count: number = 0;

  protected async workOnGoal(goal: Goal): Promise<string> {
    this.count++;
    await new Promise(resolve => setTimeout(resolve, 10));
    return `Iteration ${this.count}`;
  }
}

// ============================================================================
// Goal Tests
// ============================================================================

describe('Goal', () => {
  it('should create a goal with defaults', () => {
    const goal = createGoal('Test goal');

    expect(goal.description).toBe('Test goal');
    expect(goal.priority).toBe(1);
    expect(goal.status).toBe('active');
    expect(goal.progress).toBe(0.0);
    expect(goal.createdAt).toBeInstanceOf(Date);
  });

  it('should create goal with custom priority', () => {
    const goal = createGoal('High priority', 10);

    expect(goal.priority).toBe(10);
  });

  it('should create goal with custom status', () => {
    const goal = createGoal('Test', 1, 'completed');

    expect(goal.status).toBe('completed');
  });

  it('should create goal with custom progress', () => {
    const goal = createGoal('Test', 1, 'active', 0.5);

    expect(goal.progress).toBe(0.5);
  });

  it('should set createdAt automatically', () => {
    const before = new Date();
    const goal = createGoal('Test');
    const after = new Date();

    expect(goal.createdAt.getTime()).toBeGreaterThanOrEqual(before.getTime());
    expect(goal.createdAt.getTime()).toBeLessThanOrEqual(after.getTime());
  });

  it('should allow explicit createdAt', () => {
    const timestamp = new Date('2024-01-01T12:00:00Z');
    const goal = createGoal('Test', 1, 'active', 0.0, timestamp);

    expect(goal.createdAt).toBe(timestamp);
  });
});

// ============================================================================
// AutonomousAgent Tests
// ============================================================================

describe('AutonomousAgent', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const agent = new MockAutonomousAgent('Test objective');

      expect(agent.name).toBe('AutonomousAgent');
      expect(agent.objective).toBe('Test objective');
      expect(agent.maxIterations).toBe(10);
      expect(agent.stopCondition).toBeUndefined();
      expect(agent.goals).toEqual([]);
      expect(agent.iterationCount).toBe(0);
      expect(agent.isRunning).toBe(false);
    });

    it('should create with custom max iterations', () => {
      const agent = new MockAutonomousAgent('Test', 5);

      expect(agent.maxIterations).toBe(5);
    });

    it('should create with stop condition', () => {
      const stopFunc = () => true;
      const agent = new MockAutonomousAgent('Test', 10, stopFunc);

      expect(agent.stopCondition).toBe(stopFunc);
    });
  });

  describe('Process', () => {
    it('should return objective in process response', async () => {
      const agent = new MockAutonomousAgent('Test objective');

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Test objective');
    });
  });

  describe('Goal Management', () => {
    let agent: MockAutonomousAgent;

    beforeEach(() => {
      agent = new MockAutonomousAgent('Test');
    });

    it('should add goal with default priority', () => {
      const goal = agent.addGoal('First goal');

      expect(agent.goals).toHaveLength(1);
      expect(goal.description).toBe('First goal');
      expect(goal.priority).toBe(1);
    });

    it('should add goal with custom priority', () => {
      const goal = agent.addGoal('High priority goal', 10);

      expect(goal.priority).toBe(10);
    });

    it('should add multiple goals', () => {
      agent.addGoal('Goal 1', 1);
      agent.addGoal('Goal 2', 5);
      agent.addGoal('Goal 3', 10);

      expect(agent.goals).toHaveLength(3);
    });

    it('should track all added goals', () => {
      const goal1 = agent.addGoal('First', 1);
      const goal2 = agent.addGoal('Second', 2);

      expect(agent.goals).toContain(goal1);
      expect(agent.goals).toContain(goal2);
    });
  });

  describe('Execution', () => {
    it('should run with no goals', async () => {
      const agent = new MockAutonomousAgent('Test', 10);

      const result = await agent.run();

      expect(result.objective).toBe('Test');
      expect(result.iterations).toBe(0);
      expect(result.goalsCompleted).toBe(0);
      expect(result.results).toEqual([]);
    });

    it('should work on single goal', async () => {
      const agent = new MockAutonomousAgent('Test', 10);
      agent.addGoal('Task 1');

      const result = await agent.run();

      expect(agent.workLog).toContain('Task 1');
      expect(result.iterations).toBeGreaterThan(0);
    });

    it('should work on highest priority goal', async () => {
      const agent = new MockAutonomousAgent('Test', 10);
      agent.addGoal('Low priority', 1);
      agent.addGoal('High priority', 10);
      agent.addGoal('Medium priority', 5);

      await agent.run();

      // First work should be on highest priority
      expect(agent.workLog[0]).toBe('High priority');
    });

    it('should respect max iterations', async () => {
      const agent = new MockAutonomousAgent('Test', 3);
      agent.addGoal('Task 1');

      const result = await agent.run();

      expect(result.iterations).toBe(3);
    });

    it('should stop when all goals completed', async () => {
      const agent = new MockAutonomousAgent('Test', 100);
      agent.addGoal('Task 1');

      const result = await agent.run();

      // Should complete goal in 5 iterations (0.2 progress each)
      expect(result.iterations).toBe(5);
      expect(result.goalsCompleted).toBe(1);
    });

    it('should update goal progress', async () => {
      const agent = new MockAutonomousAgent('Test', 2);
      agent.addGoal('Task 1');

      await agent.run();

      expect(agent.goals[0].progress).toBe(0.4); // 2 iterations * 0.2
    });

    it('should mark goal as completed', async () => {
      const agent = new MockAutonomousAgent('Test', 10);
      agent.addGoal('Task 1');

      await agent.run();

      expect(agent.goals[0].status).toBe('completed');
    });

    it('should return results from each iteration', async () => {
      const agent = new MockAutonomousAgent('Test', 3);
      agent.addGoal('Task 1');

      const result = await agent.run();

      expect(result.results).toHaveLength(3);
      expect(result.results[0]).toContain('Completed: Task 1');
    });

    it('should track iteration count', async () => {
      const agent = new CountingAgent('Test', 5);
      agent.addGoal('Count');

      await agent.run();

      expect(agent.count).toBe(5);
      expect(agent.iterationCount).toBe(5);
    });

    it('should set isRunning during execution', async () => {
      const agent = new MockAutonomousAgent('Test', 10);
      agent.addGoal('Task 1');

      const runPromise = agent.run();
      expect(agent.isRunning).toBe(true);

      await runPromise;
      expect(agent.isRunning).toBe(false);
    });
  });

  describe('Stop Condition', () => {
    it('should stop when stop condition returns true', async () => {
      let callCount = 0;
      const stopFunc = () => {
        callCount++;
        return callCount >= 3;
      };

      const agent = new MockAutonomousAgent('Test', 100, stopFunc);
      agent.addGoal('Task 1');

      const result = await agent.run();

      expect(result.iterations).toBe(3);
    });

    it('should not call stop condition if not provided', async () => {
      const agent = new MockAutonomousAgent('Test', 5);
      agent.addGoal('Task 1');

      const result = await agent.run();

      expect(result.iterations).toBeGreaterThan(0);
    });
  });

  describe('Manual Stop', () => {
    it('should stop when stop() is called', async () => {
      const agent = new MockAutonomousAgent('Test', 100);
      agent.addGoal('Task 1');

      setTimeout(() => agent.stop(), 50);

      const result = await agent.run();

      expect(result.iterations).toBeLessThan(100);
      expect(agent.isRunning).toBe(false);
    });

    it('should set isRunning to false', () => {
      const agent = new MockAutonomousAgent('Test', 10);
      agent.isRunning = true;

      agent.stop();

      expect(agent.isRunning).toBe(false);
    });
  });

  describe('Progress Tracking', () => {
    let agent: MockAutonomousAgent;

    beforeEach(() => {
      agent = new MockAutonomousAgent('Test', 10);
    });

    it('should return 0% with no goals', () => {
      expect(agent.getProgress()).toBe(0);
    });

    it('should calculate progress with single goal', async () => {
      agent.addGoal('Task 1');
      await agent.run();

      expect(agent.getProgress()).toBe(100);
    });

    it('should calculate progress with multiple goals', () => {
      agent.addGoal('Task 1');
      agent.addGoal('Task 2');

      agent.goals[0].progress = 1.0;
      agent.goals[1].progress = 0.5;

      expect(agent.getProgress()).toBe(75); // (1.0 + 0.5) / 2 * 100
    });

    it('should calculate partial progress', () => {
      agent.addGoal('Task 1');
      agent.addGoal('Task 2');
      agent.addGoal('Task 3');

      agent.goals[0].progress = 1.0;
      agent.goals[1].progress = 0.5;
      agent.goals[2].progress = 0.0;

      expect(agent.getProgress()).toBe(50); // (1.0 + 0.5 + 0.0) / 3 * 100
    });
  });

  describe('Multiple Goals', () => {
    it('should complete multiple goals', async () => {
      const agent = new MockAutonomousAgent('Test', 100);
      agent.addGoal('Task 1', 10);
      agent.addGoal('Task 2', 5);

      const result = await agent.run();

      expect(result.goalsCompleted).toBe(2);
      expect(agent.goals[0].status).toBe('completed');
      expect(agent.goals[1].status).toBe('completed');
    });

    it('should work on goals in priority order', async () => {
      const agent = new MockAutonomousAgent('Test', 100);
      agent.addGoal('Low', 1);
      agent.addGoal('High', 10);
      agent.addGoal('Medium', 5);

      await agent.run();

      // Check that high priority was worked on first
      const highPriorityIndex = agent.workLog.findIndex(w => w === 'High');
      const lowPriorityIndex = agent.workLog.findIndex(w => w === 'Low');

      expect(highPriorityIndex).toBeLessThan(lowPriorityIndex);
    });

    it('should switch to next active goal when one completes', async () => {
      const agent = new MockAutonomousAgent('Test', 100);
      agent.addGoal('First', 10);
      agent.addGoal('Second', 5);

      await agent.run();

      // Both goals should have been worked on
      expect(agent.workLog).toContain('First');
      expect(agent.workLog).toContain('Second');
    });
  });
});
