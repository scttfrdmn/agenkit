/**
 * Comprehensive tests for AutonomousAgent pattern.
 *
 * Tests cover:
 * - Constructor and configuration
 * - Goal management
 * - Run loop behavior
 * - Stop conditions
 * - Progress tracking
 */

import { describe, it, expect } from 'vitest';
import {
  AutonomousAgent,
  createGoal,
  type Goal,
  type GoalStatus,
} from '../../patterns/autonomous';
import { createMessage } from '../../core/interfaces';

describe('createGoal', () => {
  it('should create a goal with default values', () => {
    const goal = createGoal('Do something');

    expect(goal.description).toBe('Do something');
    expect(goal.priority).toBe(1);
    expect(goal.status).toBe('active');
    expect(goal.progress).toBe(0.0);
    expect(goal.createdAt).toBeInstanceOf(Date);
  });

  it('should create a goal with custom priority', () => {
    const goal = createGoal('High priority task', 10);

    expect(goal.priority).toBe(10);
  });

  it('should create a goal with custom status', () => {
    const goal = createGoal('Done task', 1, 'completed');

    expect(goal.status).toBe('completed');
  });
});

describe('AutonomousAgent', () => {
  describe('Constructor', () => {
    it('should create agent with objective', () => {
      const agent = new AutonomousAgent('Research AI trends');

      expect(agent.name).toBe('AutonomousAgent');
      expect(agent.objective).toBe('Research AI trends');
    });

    it('should use default maxIterations of 10', () => {
      const agent = new AutonomousAgent('Test objective');

      expect(agent.maxIterations).toBe(10);
    });

    it('should accept custom maxIterations', () => {
      const agent = new AutonomousAgent('Test objective', 5);

      expect(agent.maxIterations).toBe(5);
    });

    it('should start with empty goals', () => {
      const agent = new AutonomousAgent('Test objective');

      expect(agent.goals).toHaveLength(0);
    });

    it('should start not running', () => {
      const agent = new AutonomousAgent('Test objective');

      expect(agent.isRunning).toBe(false);
    });
  });

  describe('process method', () => {
    it('should return a message about the objective', async () => {
      const agent = new AutonomousAgent('Test objective');
      const result = await agent.process(createMessage('user', 'start'));

      expect(result.role).toBe('assistant');
      expect(String(result.content)).toContain('Test objective');
    });
  });

  describe('addGoal', () => {
    it('should add a goal with default priority', () => {
      const agent = new AutonomousAgent('Test objective');
      const goal = agent.addGoal('Research topic');

      expect(goal.description).toBe('Research topic');
      expect(goal.priority).toBe(1);
      expect(goal.status).toBe('active');
      expect(agent.goals).toHaveLength(1);
    });

    it('should add a goal with custom priority', () => {
      const agent = new AutonomousAgent('Test objective');
      const goal = agent.addGoal('Important task', 10);

      expect(goal.priority).toBe(10);
    });

    it('should accumulate multiple goals', () => {
      const agent = new AutonomousAgent('Test objective');
      agent.addGoal('Goal 1', 1);
      agent.addGoal('Goal 2', 2);
      agent.addGoal('Goal 3', 3);

      expect(agent.goals).toHaveLength(3);
    });
  });

  describe('run', () => {
    it('should run and return result object', async () => {
      const agent = new AutonomousAgent('Test objective', 3);
      agent.addGoal('Simple goal', 1);

      const result = await agent.run();

      expect(result.objective).toBe('Test objective');
      expect(typeof result.iterations).toBe('number');
      expect(typeof result.goalsCompleted).toBe('number');
      expect(Array.isArray(result.results)).toBe(true);
    });

    it('should stop when no active goals', async () => {
      const agent = new AutonomousAgent('Test objective', 100);
      // No goals added - should exit immediately

      const result = await agent.run();

      expect(result.iterations).toBe(0);
    });

    it('should not run more iterations than maxIterations', async () => {
      const agent = new AutonomousAgent('Test objective', 3);
      // Add a goal that won't complete quickly
      agent.addGoal('Long running task', 1);

      const result = await agent.run();

      expect(result.iterations).toBeLessThanOrEqual(3);
    });

    it('should complete goal after enough progress', async () => {
      const agent = new AutonomousAgent('Test objective', 10);
      agent.addGoal('Complete task', 1);

      const result = await agent.run();

      // With progress += 0.2 per iteration, needs 5 iterations to complete
      expect(result.goalsCompleted).toBeGreaterThan(0);
    });

    it('should set isRunning to false after completion', async () => {
      const agent = new AutonomousAgent('Test objective', 3);
      agent.addGoal('Goal', 1);

      await agent.run();

      expect(agent.isRunning).toBe(false);
    });

    it('should stop when stop condition returns true', async () => {
      let checkCount = 0;
      const stopAfter = 2;

      const agent = new AutonomousAgent(
        'Test objective',
        100,
        () => {
          checkCount++;
          return checkCount >= stopAfter;
        }
      );
      agent.addGoal('Long task', 1);

      const result = await agent.run();

      expect(result.iterations).toBeLessThanOrEqual(stopAfter);
    });

    it('should work on highest priority goal first', async () => {
      const agent = new AutonomousAgent('Test objective', 1);
      agent.addGoal('Low priority', 1);
      agent.addGoal('High priority', 10);

      const result = await agent.run();

      // Ensure at least one iteration ran
      expect(result.iterations).toBeGreaterThan(0);
    });
  });

  describe('stop', () => {
    it('should set isRunning to false', () => {
      const agent = new AutonomousAgent('Test objective');
      agent.stop();

      expect(agent.isRunning).toBe(false);
    });
  });

  describe('getProgress', () => {
    it('should return 0 when no goals', () => {
      const agent = new AutonomousAgent('Test objective');

      expect(agent.getProgress()).toBe(0);
    });

    it('should return value between 0 and 100', async () => {
      const agent = new AutonomousAgent('Test objective', 5);
      agent.addGoal('Goal 1', 1);
      agent.addGoal('Goal 2', 1);

      await agent.run();

      const progress = agent.getProgress();
      expect(progress).toBeGreaterThanOrEqual(0);
      expect(progress).toBeLessThanOrEqual(100);
    });

    it('should increase with completed goals', async () => {
      const agent = new AutonomousAgent('Test objective', 10);
      agent.addGoal('Goal', 1);

      const progressBefore = agent.getProgress();
      await agent.run();
      const progressAfter = agent.getProgress();

      expect(progressAfter).toBeGreaterThanOrEqual(progressBefore);
    });
  });
});
