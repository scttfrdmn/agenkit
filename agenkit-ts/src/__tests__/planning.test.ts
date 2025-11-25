/**
 * Tests for Planning Agent pattern.
 */

import {
  PlanningAgent,
  StepStatus,
  Plan,
  PlanStep,
  createPlan,
  createPlanStep,
  getNextSteps,
  isPlanComplete,
  hasPlanFailures,
  getPlanProgress,
  canExecuteStep,
  LLMClient,
  StepExecutor,
  DefaultStepExecutor,
} from '../patterns/planning';
import { Message, createMessage } from '../core/interfaces';

// ============================================================================
// Mock Implementations
// ============================================================================

class MockLLMClient implements LLMClient {
  private responses: string[];
  private callCount: number;

  constructor(responses: string[]) {
    this.responses = responses;
    this.callCount = 0;
  }

  async chat(messages: Message[]): Promise<Message> {
    const response = this.responses[this.callCount] || this.responses[0];
    this.callCount++;
    return createMessage('assistant', response);
  }

  getCallCount(): number {
    return this.callCount;
  }
}

class MockStepExecutor implements StepExecutor {
  private shouldFail: boolean;
  private executedSteps: PlanStep[];

  constructor(shouldFail: boolean = false) {
    this.shouldFail = shouldFail;
    this.executedSteps = [];
  }

  async execute(step: PlanStep, context: Record<string, any>): Promise<string> {
    this.executedSteps.push(step);

    if (this.shouldFail) {
      throw new Error('Step execution failed');
    }

    return `Completed: ${step.description}`;
  }

  getExecutedSteps(): PlanStep[] {
    return this.executedSteps;
  }
}

// ============================================================================
// PlanStep Tests
// ============================================================================

describe('PlanStep', () => {
  it('should create a plan step', () => {
    const step = createPlanStep('Test step', 0);

    expect(step.description).toBe('Test step');
    expect(step.stepNumber).toBe(0);
    expect(step.status).toBe(StepStatus.PENDING);
    expect(step.dependencies).toEqual([]);
    expect(step.timestamp).toBeInstanceOf(Date);
  });

  it('should create step with dependencies', () => {
    const step = createPlanStep('Test step', 1, [0]);

    expect(step.dependencies).toEqual([0]);
  });

  it('should check if step can execute with no dependencies', () => {
    const step = createPlanStep('Test step', 0);

    expect(canExecuteStep(step, [])).toBe(true);
  });

  it('should check if step can execute with met dependencies', () => {
    const step = createPlanStep('Test step', 2, [0, 1]);

    expect(canExecuteStep(step, [0, 1])).toBe(true);
  });

  it('should check if step cannot execute with unmet dependencies', () => {
    const step = createPlanStep('Test step', 2, [0, 1]);

    expect(canExecuteStep(step, [0])).toBe(false);
    expect(canExecuteStep(step, [])).toBe(false);
  });
});

// ============================================================================
// Plan Tests
// ============================================================================

describe('Plan', () => {
  it('should create an empty plan', () => {
    const plan = createPlan('Test goal');

    expect(plan.goal).toBe('Test goal');
    expect(plan.steps).toEqual([]);
    expect(plan.createdAt).toBeInstanceOf(Date);
  });

  it('should create plan with steps', () => {
    const steps = [createPlanStep('Step 1', 0), createPlanStep('Step 2', 1)];
    const plan = createPlan('Test goal', steps);

    expect(plan.steps).toHaveLength(2);
    expect(plan.steps[0].description).toBe('Step 1');
  });

  it('should get next executable steps', () => {
    const steps = [
      createPlanStep('Step 1', 0),
      createPlanStep('Step 2', 1, [0]),
      createPlanStep('Step 3', 2, [0, 1]),
    ];
    const plan = createPlan('Test', steps);

    const nextSteps = getNextSteps(plan);

    // Only step 1 can execute (no dependencies)
    expect(nextSteps).toHaveLength(1);
    expect(nextSteps[0].stepNumber).toBe(0);
  });

  it('should get next steps after completion', () => {
    const steps = [
      createPlanStep('Step 1', 0),
      createPlanStep('Step 2', 1, [0]),
      createPlanStep('Step 3', 2, [0]),
    ];
    steps[0].status = StepStatus.COMPLETED;
    const plan = createPlan('Test', steps);

    const nextSteps = getNextSteps(plan);

    // Steps 2 and 3 can now execute
    expect(nextSteps).toHaveLength(2);
  });

  it('should check if plan is complete', () => {
    const steps = [createPlanStep('Step 1', 0), createPlanStep('Step 2', 1)];
    const plan = createPlan('Test', steps);

    expect(isPlanComplete(plan)).toBe(false);

    steps[0].status = StepStatus.COMPLETED;
    steps[1].status = StepStatus.COMPLETED;

    expect(isPlanComplete(plan)).toBe(true);
  });

  it('should check if plan has failures', () => {
    const steps = [createPlanStep('Step 1', 0), createPlanStep('Step 2', 1)];
    const plan = createPlan('Test', steps);

    expect(hasPlanFailures(plan)).toBe(false);

    steps[0].status = StepStatus.FAILED;

    expect(hasPlanFailures(plan)).toBe(true);
  });

  it('should calculate plan progress', () => {
    const steps = [
      createPlanStep('Step 1', 0),
      createPlanStep('Step 2', 1),
      createPlanStep('Step 3', 2),
      createPlanStep('Step 4', 3),
    ];
    const plan = createPlan('Test', steps);

    expect(getPlanProgress(plan)).toBe(0);

    steps[0].status = StepStatus.COMPLETED;
    expect(getPlanProgress(plan)).toBe(25);

    steps[1].status = StepStatus.COMPLETED;
    expect(getPlanProgress(plan)).toBe(50);

    steps[2].status = StepStatus.SKIPPED;
    expect(getPlanProgress(plan)).toBe(75);

    steps[3].status = StepStatus.COMPLETED;
    expect(getPlanProgress(plan)).toBe(100);
  });

  it('should handle empty plan progress', () => {
    const plan = createPlan('Test', []);

    expect(getPlanProgress(plan)).toBe(0);
  });
});

// ============================================================================
// DefaultStepExecutor Tests
// ============================================================================

describe('DefaultStepExecutor', () => {
  it('should execute step successfully', async () => {
    const executor = new DefaultStepExecutor();
    const step = createPlanStep('Test step', 0);

    const result = await executor.execute(step, {});

    expect(result).toContain('Completed');
    expect(result).toContain('Test step');
  });
});

// ============================================================================
// PlanningAgent Tests
// ============================================================================

describe('PlanningAgent', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const llm = new MockLLMClient(['Goal: Test\nSteps:\n1. Step 1']);
      const agent = new PlanningAgent(llm);

      expect(agent.name).toBe('PlanningAgent');
      expect(agent.getProgress()).toBe(0);
    });

    it('should create with custom executor', () => {
      const llm = new MockLLMClient(['Goal: Test\nSteps:\n1. Step 1']);
      const executor = new MockStepExecutor();
      const agent = new PlanningAgent(llm, executor);

      expect(agent.name).toBe('PlanningAgent');
    });

    it('should create with config options', () => {
      const llm = new MockLLMClient(['Goal: Test\nSteps:\n1. Step 1']);
      const agent = new PlanningAgent(llm, undefined, {
        maxSteps: 5,
        allowReplanning: true,
        systemPrompt: 'Custom prompt',
      });

      expect(agent.name).toBe('PlanningAgent');
    });
  });

  describe('Plan Creation', () => {
    it('should create a plan from LLM response', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step
3. Third step`;

      const llm = new MockLLMClient([llmResponse]);
      const executor = new MockStepExecutor();
      const agent = new PlanningAgent(llm, executor);

      await agent.process(createMessage('user', 'Do something'));

      const plan = agent.getPlan();
      expect(plan).toBeDefined();
      expect(plan?.goal).toContain('Test goal');
      expect(plan?.steps).toHaveLength(3);
      expect(plan?.steps[0].description).toBe('First step');
    });

    it('should respect max steps limit', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. Step 1
2. Step 2
3. Step 3
4. Step 4
5. Step 5
6. Step 6`;

      const llm = new MockLLMClient([llmResponse]);
      const executor = new MockStepExecutor();
      const agent = new PlanningAgent(llm, executor, { maxSteps: 3 });

      await agent.process(createMessage('user', 'Do something'));

      const plan = agent.getPlan();
      expect(plan?.steps).toHaveLength(3);
    });

    it('should handle different step numbering formats', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2) Second step
Step 3: Third step`;

      const llm = new MockLLMClient([llmResponse]);
      const executor = new MockStepExecutor();
      const agent = new PlanningAgent(llm, executor);

      await agent.process(createMessage('user', 'Do something'));

      const plan = agent.getPlan();
      expect(plan?.steps).toHaveLength(3);
    });
  });

  describe('Plan Execution', () => {
    it('should execute all steps successfully', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step`;

      const llm = new MockLLMClient([llmResponse]);
      const executor = new MockStepExecutor();
      const agent = new PlanningAgent(llm, executor);

      const result = await agent.process(createMessage('user', 'Do something'));

      expect(result.content).toContain('Task completed');
      expect(result.content).toContain('2/2');
      expect(executor.getExecutedSteps()).toHaveLength(2);
    });

    it('should track progress during execution', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step`;

      const llm = new MockLLMClient([llmResponse]);
      const executor = new MockStepExecutor();
      const agent = new PlanningAgent(llm, executor);

      await agent.process(createMessage('user', 'Do something'));

      expect(agent.getProgress()).toBe(100);
    });

    it('should handle step failures', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step`;

      const llm = new MockLLMClient([llmResponse]);
      const executor = new MockStepExecutor(true); // Will fail
      const agent = new PlanningAgent(llm, executor);

      const result = await agent.process(createMessage('user', 'Do something'));

      expect(result.content).toContain('✗');
      const plan = agent.getPlan();
      expect(hasPlanFailures(plan!)).toBe(true);
    });

    it('should pass context between steps', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step`;

      const llm = new MockLLMClient([llmResponse]);
      const executedContext: Record<string, any>[] = [];
      const customExecutor: StepExecutor = {
        async execute(step, context) {
          executedContext.push({ ...context });
          return `Result ${step.stepNumber}`;
        },
      };

      const agent = new PlanningAgent(llm, customExecutor);
      await agent.process(createMessage('user', 'Do something'));

      // Second step should have first step's result in context
      expect(executedContext[1]).toHaveProperty('step_0_result');
    });
  });

  describe('Replanning', () => {
    it('should not replan by default', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step`;

      const llm = new MockLLMClient([llmResponse, 'Replan response']);
      const executor = new MockStepExecutor(true);
      const agent = new PlanningAgent(llm, executor, { allowReplanning: false });

      await agent.process(createMessage('user', 'Do something'));

      // Should not call LLM for replanning
      expect(llm.getCallCount()).toBe(1);
    });

    it('should replan on failure when enabled', async () => {
      const llmResponse = `Goal: Test goal
Steps:
1. First step
2. Second step`;

      const llm = new MockLLMClient([llmResponse, 'Replan response']);
      const executor = new MockStepExecutor(true);
      const agent = new PlanningAgent(llm, executor, { allowReplanning: true });

      await agent.process(createMessage('user', 'Do something'));

      // Should call LLM for initial plan and replanning
      expect(llm.getCallCount()).toBeGreaterThan(1);
    });
  });
});
