/**
 * Tests for Plan-and-Solve reasoning technique
 */

import { describe, it, expect } from 'vitest';
import { PlanAndSolve, type PlanStep, type Plan } from './plan-and-solve';
import type { Agent, Message } from '../../core/interfaces';

/**
 * Mock agent for testing
 */
class MockAgent implements Agent {
  readonly name = 'mock_agent';
  readonly capabilities = ['mock', 'testing'];
  private responses: string[];
  private index = 0;

  constructor(responses: string | string[]) {
    this.responses = Array.isArray(responses) ? responses : [responses];
  }

  async process(message: Message): Promise<Message> {
    const response = this.responses[this.index % this.responses.length];
    this.index++;

    return {
      role: 'assistant',
      content: response,
      timestamp: new Date().toISOString(),
    };
  }

  resetIndex(): void {
    this.index = 0;
  }
}

describe('PlanAndSolve', () => {
  describe('basic functionality', () => {
    it('should process message with plan-and-solve', async () => {
      const mockAgent = new MockAgent([
        // Planning response
        '1. Gather ingredients\n2. Preheat oven\n3. Mix ingredients\n4. Bake',
        // Validation response
        'VALID: Plan is complete',
        // Execution responses
        'Gathered: flour, sugar, eggs',
        'Preheated oven to 350°F',
        'Mixed all ingredients thoroughly',
        'Baked for 30 minutes',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: true });

      const message = {
        role: 'user' as const,
        content: 'How do I bake a cake?',
      };

      const response = await agent.process(message);

      expect(response.content).toBeTruthy();
      expect(response.metadata?.technique).toBe('plan_and_solve');
      expect(response.metadata?.num_steps).toBe(4);
    });

    it('should have correct name and capabilities', () => {
      const mockAgent = new MockAgent('response');
      const agent = new PlanAndSolve(mockAgent);

      expect(agent.name).toBe('plan_and_solve');
      expect(agent.capabilities).toContain('reasoning');
      expect(agent.capabilities).toContain('planning');
      expect(agent.capabilities).toContain('plan_and_solve');
      expect(agent.capabilities).toContain('strategic_thinking');
      expect(agent.capabilities).toContain('step_by_step_execution');
    });
  });

  describe('planning phase', () => {
    it('should create a plan from problem', async () => {
      const mockAgent = new MockAgent([
        '1. Step one\n2. Step two\n3. Step three',
        'Step result 1',
        'Step result 2',
        'Step result 3',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Test problem' };
      const response = await agent.process(message);

      expect(response.metadata?.num_steps).toBe(3);
      expect(response.metadata?.plan_steps).toHaveLength(3);
      expect(response.metadata?.plan_steps[0]).toBe('Step one');
    });

    it('should parse steps correctly', async () => {
      const mockAgent = new MockAgent([
        '1. First step\n2. Second step',
        'Result 1',
        'Result 2',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Problem' };
      const response = await agent.process(message);

      const planSteps = response.metadata?.plan_steps as string[];
      expect(planSteps).toEqual(['First step', 'Second step']);
    });
  });

  describe('validation', () => {
    it('should validate plan when enabled', async () => {
      const mockAgent = new MockAgent([
        '1. Step 1\n2. Step 2',
        'VALID: The plan is complete and feasible',
        'Result 1',
        'Result 2',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: true });

      const message = { role: 'user' as const, content: 'Problem' };
      const response = await agent.process(message);

      expect(response.metadata?.validated).toBe(true);
      expect(response.metadata?.validation_notes).toContain('VALID');
    });

    it('should skip validation when disabled', async () => {
      const mockAgent = new MockAgent([
        '1. Step',
        'Result',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Simple problem' };
      await agent.process(message);

      // With validation disabled, should only call LLM twice (plan + execute)
      // not three times (plan + validate + execute)
      expect(mockAgent['index']).toBe(2);
    });

    it('should handle invalid plan validation', async () => {
      const mockAgent = new MockAgent([
        '1. Step 1',
        'INVALID: Missing important step',
        'Result 1',
      ]);

      const agent = new PlanAndSolve(mockAgent, {
        validatePlan: true,
        allowReplanning: false,
      });

      const message = { role: 'user' as const, content: 'Problem' };
      const response = await agent.process(message);

      expect(response.metadata?.validated).toBe(false);
      expect(response.metadata?.validation_notes).toContain('INVALID');
    });
  });

  describe('execution phase', () => {
    it('should execute plan steps sequentially', async () => {
      const mockAgent = new MockAgent([
        '1. Step A\n2. Step B',
        'Answer A',
        'Answer B',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Problem' };
      const response = await agent.process(message);

      expect(response.metadata?.execution_steps).toEqual(['Answer A', 'Answer B']);
    });

    it('should return final solution as response content', async () => {
      const mockAgent = new MockAgent([
        '1. Subproblem 1\n2. Subproblem 2',
        'Intermediate',
        'Final answer',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Problem' };
      const response = await agent.process(message);

      expect(response.content).toBe('Final answer');
      expect(response.role).toBe('assistant');
    });

    it('should track execution state', async () => {
      const step: PlanStep = {
        description: 'Test step',
        order: 0,
        dependencies: [],
        estimatedComplexity: 1,
        executed: false,
      };

      expect(step.executed).toBe(false);

      step.executed = true;
      step.result = 'Test result';

      expect(step.executed).toBe(true);
      expect(step.result).toBe('Test result');
    });
  });

  describe('custom functions', () => {
    it('should use custom planner when provided', async () => {
      const customPlanner = async (problem: string): Promise<Plan> => {
        return {
          problem,
          steps: [
            { description: 'Custom step 1', order: 0, dependencies: [], estimatedComplexity: 1, executed: false },
            { description: 'Custom step 2', order: 1, dependencies: [], estimatedComplexity: 1, executed: false },
          ],
          validated: false,
          strategy: 'Custom strategy',
        };
      };

      const mockAgent = new MockAgent(['Step 1 result', 'Step 2 result']);

      const agent = new PlanAndSolve(mockAgent, {
        planner: customPlanner,
        validatePlan: false,
      });

      const message = { role: 'user' as const, content: 'Test problem' };
      const response = await agent.process(message);

      const planSteps = response.metadata?.plan_steps as string[];
      expect(planSteps).toHaveLength(2);
      expect(planSteps[0]).toBe('Custom step 1');
      expect(response.metadata?.strategy).toBe('Custom strategy');
    });

    it('should use custom solver when provided', async () => {
      const customSolver = async (step: PlanStep, previousResults: string[]): Promise<string> => {
        return `Custom solution for: ${step.description}`;
      };

      const mockAgent = new MockAgent('1. Test step');

      const agent = new PlanAndSolve(mockAgent, {
        solver: customSolver,
        validatePlan: false,
      });

      const message = { role: 'user' as const, content: 'Test problem' };
      const response = await agent.process(message);

      expect(response.content).toContain('Custom solution');
    });
  });

  describe('replanning', () => {
    it('should replan when validation fails and replanning enabled', async () => {
      const mockAgent = new MockAgent([
        '1. Initial step',
        'INVALID: Missing steps',
        // Replanning prompt (consumed but not used for test)
        '',
        // New plan after replanning
        '1. Better step 1\n2. Better step 2',
        'VALID',
        'Result 1',
        'Result 2',
      ]);

      const agent = new PlanAndSolve(mockAgent, {
        validatePlan: true,
        allowReplanning: true,
      });

      const message = { role: 'user' as const, content: 'Complex problem' };
      const response = await agent.process(message);

      // Should have replanned and gotten a valid plan
      expect(response.metadata?.num_steps).toBe(2);
    });
  });

  describe('edge cases', () => {
    it('should handle empty plan', async () => {
      const mockAgent = new MockAgent(''); // Empty response

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Problem' };
      const response = await agent.process(message);

      expect(response.metadata?.num_steps).toBe(0);
      expect(response.content).toBe('');
    });

    it('should handle single step plan', async () => {
      const mockAgent = new MockAgent([
        '1. Only step',
        'Step result',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const message = { role: 'user' as const, content: 'Simple task' };
      const response = await agent.process(message);

      expect(response.metadata?.num_steps).toBe(1);
      expect(response.content).toBe('Step result');
    });
  });

  describe('numbering formats', () => {
    it('should parse period numbering', async () => {
      const mockAgent = new MockAgent([
        '1. Step one\n2. Step two\n3. Step three',
        'R1', 'R2', 'R3',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const response = await agent.process({ role: 'user' as const, content: 'Problem' });

      expect(response.metadata?.num_steps).toBe(3);
      expect(response.metadata?.plan_steps).toEqual(['Step one', 'Step two', 'Step three']);
    });

    it('should parse parenthesis numbering', async () => {
      const mockAgent = new MockAgent([
        '1) Step one\n2) Step two',
        'R1', 'R2',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const response = await agent.process({ role: 'user' as const, content: 'Problem' });

      expect(response.metadata?.num_steps).toBe(2);
      expect(response.metadata?.plan_steps).toEqual(['Step one', 'Step two']);
    });

    it('should skip empty lines', async () => {
      const mockAgent = new MockAgent([
        '1. Step one\n\n2. Step two\n\n',
        'R1', 'R2',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: false });

      const response = await agent.process({ role: 'user' as const, content: 'Problem' });

      expect(response.metadata?.num_steps).toBe(2);
    });
  });

  describe('metadata tracking', () => {
    it('should include all required metadata fields', async () => {
      const mockAgent = new MockAgent([
        '1. Step 1\n2. Step 2',
        'VALID',
        'Result 1',
        'Result 2',
      ]);

      const agent = new PlanAndSolve(mockAgent, { validatePlan: true });

      const message = { role: 'user' as const, content: 'Test' };
      const response = await agent.process(message);

      expect(response.metadata).toBeDefined();
      expect(response.metadata?.technique).toBe('plan_and_solve');
      expect(response.metadata?.num_steps).toBe(2);
      expect(response.metadata?.plan_steps).toHaveLength(2);
      expect(response.metadata?.execution_steps).toHaveLength(2);
      expect(response.metadata?.validated).toBe(true);
      expect(response.metadata?.validation_notes).toBeDefined();
      expect(response.metadata?.allow_replanning).toBeDefined();
    });

    it('should track strategy when provided', async () => {
      const customPlanner = async (problem: string): Promise<Plan> => {
        return {
          problem,
          steps: [{ description: 'Step', order: 0, dependencies: [], estimatedComplexity: 1, executed: false }],
          validated: false,
          strategy: 'Divide and conquer',
        };
      };

      const mockAgent = new MockAgent('Result');

      const agent = new PlanAndSolve(mockAgent, {
        planner: customPlanner,
        validatePlan: false,
      });

      const response = await agent.process({ role: 'user' as const, content: 'Problem' });

      expect(response.metadata?.strategy).toBe('Divide and conquer');
    });
  });

  describe('step dependencies', () => {
    it('should track step dependencies', () => {
      const plan: Plan = {
        problem: 'Test',
        steps: [
          { description: 'Step 1', order: 0, dependencies: [], estimatedComplexity: 1, executed: false },
          { description: 'Step 2', order: 1, dependencies: [0], estimatedComplexity: 1, executed: false },
          { description: 'Step 3', order: 2, dependencies: [0, 1], estimatedComplexity: 2, executed: false },
        ],
        validated: false,
      };

      // Verify step 2 depends on step 1
      expect(plan.steps[1].dependencies).toEqual([0]);

      // Verify step 3 depends on steps 1 and 2
      expect(plan.steps[2].dependencies).toEqual([0, 1]);

      // Verify complexity tracking
      expect(plan.steps[2].estimatedComplexity).toBe(2);
    });
  });

  describe('plan dataclass', () => {
    it('should create valid plan structure', () => {
      const plan: Plan = {
        problem: 'Test problem',
        steps: [],
        validated: false,
      };

      expect(plan.problem).toBe('Test problem');
      expect(plan.steps).toEqual([]);
      expect(plan.validated).toBe(false);
    });

    it('should support optional fields', () => {
      const plan: Plan = {
        problem: 'Test',
        steps: [],
        validated: true,
        strategy: 'Test strategy',
        validationNotes: 'All good',
      };

      expect(plan.strategy).toBe('Test strategy');
      expect(plan.validationNotes).toBe('All good');
    });
  });

  describe('planstep dataclass', () => {
    it('should create valid plan step structure', () => {
      const step: PlanStep = {
        description: 'Test step',
        order: 0,
        dependencies: [],
        estimatedComplexity: 1,
        executed: false,
      };

      expect(step.description).toBe('Test step');
      expect(step.order).toBe(0);
      expect(step.dependencies).toEqual([]);
      expect(step.estimatedComplexity).toBe(1);
      expect(step.executed).toBe(false);
    });

    it('should support optional result field', () => {
      const step: PlanStep = {
        description: 'Test step',
        order: 0,
        dependencies: [],
        estimatedComplexity: 1,
        executed: true,
        result: 'Test result',
      };

      expect(step.result).toBe('Test result');
    });
  });
});
