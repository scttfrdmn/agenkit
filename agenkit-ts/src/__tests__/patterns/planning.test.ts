/**
 * Comprehensive tests for PlanningAgent pattern.
 *
 * Tests cover:
 * - Plan utility functions
 * - PlanStep creation and management
 * - PlanningAgent constructor and processing
 * - Step execution
 * - Error handling
 */

import { describe, it, expect } from 'vitest';
import {
  PlanningAgent,
  createPlan,
  createPlanStep,
  canExecuteStep,
  getNextSteps,
  isPlanComplete,
  hasPlanFailures,
  getPlanProgress,
  DefaultStepExecutor,
  StepStatus,
  type LLMClient,
  type StepExecutor,
  type PlanStep,
} from '../../patterns/planning';
import { Message, createMessage } from '../../core/interfaces';

/**
 * Mock LLM client that returns a plan.
 *
 * Implements `complete(messages)` — the contract the shipped adapters in
 * `src/adapters/` implement. Was `chat(messages)` until #805, a method no
 * adapter has, so this suite passed while `PlanningAgent` could not be used
 * with a real LLM. Do not rename it back.
 */
class MockLLMClient implements LLMClient {
  private response: string;
  callCount = 0;

  constructor(response: string) {
    this.response = response;
  }

  async complete(messages: Message[]): Promise<Message> {
    this.callCount++;
    return createMessage('assistant', this.response);
  }
}

/** LLM that returns a structured plan */
class StructuredPlanLLM implements LLMClient {
  async complete(messages: Message[]): Promise<Message> {
    return createMessage(
      'assistant',
      'Goal: Complete the task\nSteps:\n1. First step\n2. Second step\n3. Third step'
    );
  }
}

/** Failing step executor */
class FailingStepExecutor implements StepExecutor {
  async execute(step: PlanStep, context: Record<string, any>): Promise<string> {
    throw new Error('step failed');
  }
}

describe('Plan Utility Functions', () => {
  describe('createPlanStep', () => {
    it('should create a step with default values', () => {
      const step = createPlanStep('Do something', 0);

      expect(step.description).toBe('Do something');
      expect(step.stepNumber).toBe(0);
      expect(step.status).toBe(StepStatus.PENDING);
      expect(step.dependencies).toEqual([]);
      expect(step.timestamp).toBeInstanceOf(Date);
    });

    it('should create a step with dependencies', () => {
      const step = createPlanStep('Final step', 2, [0, 1]);

      expect(step.dependencies).toEqual([0, 1]);
    });
  });

  describe('createPlan', () => {
    it('should create a plan with empty steps', () => {
      const plan = createPlan('Accomplish goal');

      expect(plan.goal).toBe('Accomplish goal');
      expect(plan.steps).toHaveLength(0);
      expect(plan.createdAt).toBeInstanceOf(Date);
    });

    it('should create a plan with steps', () => {
      const steps = [createPlanStep('Step 1', 0), createPlanStep('Step 2', 1)];
      const plan = createPlan('My goal', steps);

      expect(plan.steps).toHaveLength(2);
    });
  });

  describe('canExecuteStep', () => {
    it('should return true for step with no dependencies', () => {
      const step = createPlanStep('Standalone step', 0);
      expect(canExecuteStep(step, [])).toBe(true);
    });

    it('should return false when dependencies not completed', () => {
      const step = createPlanStep('Dependent step', 1, [0]);
      expect(canExecuteStep(step, [])).toBe(false);
    });

    it('should return true when all dependencies completed', () => {
      const step = createPlanStep('Dependent step', 2, [0, 1]);
      expect(canExecuteStep(step, [0, 1])).toBe(true);
    });
  });

  describe('isPlanComplete', () => {
    it('should return true for empty plan', () => {
      const plan = createPlan('Goal');
      expect(isPlanComplete(plan)).toBe(true);
    });

    it('should return false when steps are pending', () => {
      const plan = createPlan('Goal', [createPlanStep('Step', 0)]);
      expect(isPlanComplete(plan)).toBe(false);
    });

    it('should return true when all steps are completed', () => {
      const steps = [createPlanStep('Step', 0)];
      steps[0].status = StepStatus.COMPLETED;
      const plan = createPlan('Goal', steps);
      expect(isPlanComplete(plan)).toBe(true);
    });

    it('should return true when steps are skipped', () => {
      const steps = [createPlanStep('Step', 0)];
      steps[0].status = StepStatus.SKIPPED;
      const plan = createPlan('Goal', steps);
      expect(isPlanComplete(plan)).toBe(true);
    });
  });

  describe('hasPlanFailures', () => {
    it('should return false when no failures', () => {
      const plan = createPlan('Goal', [createPlanStep('Step', 0)]);
      expect(hasPlanFailures(plan)).toBe(false);
    });

    it('should return true when a step failed', () => {
      const steps = [createPlanStep('Step', 0)];
      steps[0].status = StepStatus.FAILED;
      const plan = createPlan('Goal', steps);
      expect(hasPlanFailures(plan)).toBe(true);
    });
  });

  describe('getPlanProgress', () => {
    it('should return 0 for empty plan', () => {
      const plan = createPlan('Goal');
      expect(getPlanProgress(plan)).toBe(0);
    });

    it('should return 0 when no steps completed', () => {
      const plan = createPlan('Goal', [createPlanStep('Step', 0)]);
      expect(getPlanProgress(plan)).toBe(0);
    });

    it('should return 50 when half completed', () => {
      const steps = [createPlanStep('Step1', 0), createPlanStep('Step2', 1)];
      steps[0].status = StepStatus.COMPLETED;
      const plan = createPlan('Goal', steps);
      expect(getPlanProgress(plan)).toBe(50);
    });

    it('should return 100 when all completed', () => {
      const steps = [createPlanStep('Step', 0)];
      steps[0].status = StepStatus.COMPLETED;
      const plan = createPlan('Goal', steps);
      expect(getPlanProgress(plan)).toBe(100);
    });
  });

  describe('getNextSteps', () => {
    it('should return pending steps with no dependencies', () => {
      const plan = createPlan('Goal', [
        createPlanStep('Step1', 0),
        createPlanStep('Step2', 1),
      ]);

      const next = getNextSteps(plan);
      expect(next).toHaveLength(2);
    });

    it('should not return steps with unmet dependencies', () => {
      const steps = [
        createPlanStep('Step1', 0),
        createPlanStep('Step2', 1, [0]),
      ];
      const plan = createPlan('Goal', steps);

      const next = getNextSteps(plan);
      expect(next).toHaveLength(1);
      expect(next[0].stepNumber).toBe(0);
    });

    it('should return step when dependency is completed', () => {
      const steps = [
        createPlanStep('Step1', 0),
        createPlanStep('Step2', 1, [0]),
      ];
      steps[0].status = StepStatus.COMPLETED;
      const plan = createPlan('Goal', steps);

      const next = getNextSteps(plan);
      expect(next).toHaveLength(1);
      expect(next[0].stepNumber).toBe(1);
    });
  });
});

describe('DefaultStepExecutor', () => {
  it('should execute a step and return completion message', async () => {
    const executor = new DefaultStepExecutor();
    const step = createPlanStep('Do something', 0);

    const result = await executor.execute(step, {});

    expect(result).toContain('Completed');
    expect(result).toContain('Do something');
  });
});

describe('PlanningAgent', () => {
  describe('Constructor', () => {
    it('should create agent with LLM client', () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm);

      expect(agent.name).toBe('PlanningAgent');
    });

    it('should use DefaultStepExecutor when none provided', () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm);

      expect(agent).toBeDefined();
    });

    it('should accept custom config options', () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm, undefined, {
        maxSteps: 5,
        allowReplanning: true,
      });

      expect(agent).toBeDefined();
    });
  });

  describe('Processing', () => {
    it('should process a task and return a result message', async () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm);

      const result = await agent.process(createMessage('user', 'Organize a meeting'));

      expect(result.role).toBe('assistant');
      expect(typeof result.content).toBe('string');
      expect(String(result.content)).toContain('Task completed');
    });

    it('should show the goal in the result', async () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm);

      const result = await agent.process(createMessage('user', 'Write a report'));

      expect(String(result.content)).toContain('Goal');
    });

    it('should track current plan after processing', async () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm);

      await agent.process(createMessage('user', 'Do something'));

      expect(agent.getPlan()).toBeDefined();
    });

    it('should getProgress return number between 0 and 100', async () => {
      const llm = new StructuredPlanLLM();
      const agent = new PlanningAgent(llm);

      await agent.process(createMessage('user', 'Do something'));

      const progress = agent.getProgress();
      expect(progress).toBeGreaterThanOrEqual(0);
      expect(progress).toBeLessThanOrEqual(100);
    });
  });
});
