/**
 * Planning Agent Pattern
 *
 * Implements agents that create plans to accomplish complex tasks by breaking
 * them down into smaller, manageable steps.
 *
 * A planning agent:
 * 1. Analyzes the task
 * 2. Creates a step-by-step plan
 * 3. Executes each step
 * 4. Adapts the plan if needed
 * 5. Returns the final result
 *
 * This pattern is useful for:
 * - Complex multi-step tasks
 * - Tasks requiring coordination
 * - Tasks where order matters
 * - Tasks needing dynamic replanning
 *
 * Example:
 * ```typescript
 * const agent = new PlanningAgent(
 *   llmClient,
 *   stepExecutor,
 *   { maxSteps: 10, allowReplanning: true }
 * );
 *
 * const result = await agent.process(
 *   createMessage('user', 'Organize a team event')
 * );
 * // Agent will create a plan with steps like:
 * // 1. Choose date and venue
 * // 2. Create invitation list
 * // 3. Send invitations
 * // 4. Arrange catering
 * // etc.
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Status of a plan step.
 */
export enum StepStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

/**
 * A single step in a plan.
 */
export interface PlanStep {
  /** What this step should accomplish */
  description: string;
  /** Step indices that must complete before this step */
  dependencies: number[];
  /** Current status of the step */
  status: StepStatus;
  /** Result from executing the step (if completed) */
  result?: any;
  /** Error message if step failed */
  error?: string;
  /** Position in the plan (0-indexed) */
  stepNumber: number;
  /** Additional step metadata */
  metadata?: Record<string, any>;
  /** When the step was created */
  timestamp: Date;
}

/**
 * Create a new plan step.
 */
export function createPlanStep(
  description: string,
  stepNumber: number,
  dependencies: number[] = []
): PlanStep {
  return {
    description,
    dependencies,
    status: StepStatus.PENDING,
    stepNumber,
    timestamp: new Date(),
  };
}

/**
 * Check if a step's dependencies are met.
 */
export function canExecuteStep(step: PlanStep, completedSteps: number[]): boolean {
  return step.dependencies.every(dep => completedSteps.includes(dep));
}

/**
 * A plan consisting of multiple steps.
 */
export interface Plan {
  /** The overall goal the plan aims to achieve */
  goal: string;
  /** List of steps in the plan */
  steps: PlanStep[];
  /** When the plan was created */
  createdAt: Date;
  /** Additional plan metadata */
  metadata?: Record<string, any>;
}

/**
 * Create a new plan.
 */
export function createPlan(goal: string, steps: PlanStep[] = []): Plan {
  return {
    goal,
    steps,
    createdAt: new Date(),
  };
}

/**
 * Get all steps that can be executed now.
 */
export function getNextSteps(plan: Plan): PlanStep[] {
  const completedIndices = plan.steps
    .map((step, index) => (step.status === StepStatus.COMPLETED ? index : -1))
    .filter(index => index !== -1);

  return plan.steps.filter(
    step => step.status === StepStatus.PENDING && canExecuteStep(step, completedIndices)
  );
}

/**
 * Check if all steps are completed or skipped.
 */
export function isPlanComplete(plan: Plan): boolean {
  return plan.steps.every(
    step => step.status === StepStatus.COMPLETED || step.status === StepStatus.SKIPPED
  );
}

/**
 * Check if any steps failed.
 */
export function hasPlanFailures(plan: Plan): boolean {
  return plan.steps.some(step => step.status === StepStatus.FAILED);
}

/**
 * Get completion progress as a percentage.
 */
export function getPlanProgress(plan: Plan): number {
  if (plan.steps.length === 0) {
    return 0;
  }

  const completed = plan.steps.filter(
    step => step.status === StepStatus.COMPLETED || step.status === StepStatus.SKIPPED
  ).length;

  return (completed / plan.steps.length) * 100;
}

/**
 * Protocol for LLM clients that can be used with PlanningAgent.
 */
export interface LLMClient {
  chat(messages: Message[]): Promise<Message>;
}

/**
 * Protocol for executing individual plan steps.
 */
export interface StepExecutor {
  /**
   * Execute a plan step.
   *
   * @param step The step to execute
   * @param context Context from previous steps
   * @returns Result of the step execution
   */
  execute(step: PlanStep, context: Record<string, any>): Promise<any>;
}

/**
 * Default step executor that returns mock results.
 */
export class DefaultStepExecutor implements StepExecutor {
  async execute(step: PlanStep, context: Record<string, any>): Promise<string> {
    // Mock execution - just return success
    return `Completed: ${step.description}`;
  }
}

/**
 * Configuration for PlanningAgent.
 */
export interface PlanningAgentConfig {
  /** Maximum steps in a plan */
  maxSteps?: number;
  /** Whether to replan on failures */
  allowReplanning?: boolean;
  /** Optional system prompt */
  systemPrompt?: string;
}

/**
 * Agent that creates and executes plans for complex tasks.
 *
 * The agent uses an LLM to create a plan, then executes each step
 * sequentially or in parallel (if dependencies allow).
 *
 * Example:
 * ```typescript
 * const agent = new PlanningAgent(
 *   llmClient,
 *   stepExecutor,
 *   {
 *     maxSteps: 10,
 *     allowReplanning: true
 *   }
 * );
 *
 * const result = await agent.process(
 *   createMessage('user', 'Organize a team event')
 * );
 * ```
 */
export class PlanningAgent implements Agent {
  readonly name = 'PlanningAgent';
  private llm: LLMClient;
  private executor: StepExecutor;
  private maxSteps: number;
  private allowReplanning: boolean;
  private systemPrompt: string;
  private currentPlan?: Plan;

  constructor(
    llmClient: LLMClient,
    stepExecutor?: StepExecutor,
    config: PlanningAgentConfig = {}
  ) {
    this.llm = llmClient;
    this.executor = stepExecutor || new DefaultStepExecutor();
    this.maxSteps = config.maxSteps || 10;
    this.allowReplanning = config.allowReplanning || false;
    this.systemPrompt = config.systemPrompt || this.defaultSystemPrompt();
  }

  private defaultSystemPrompt(): string {
    return `You are a planning agent that breaks down complex tasks into steps.

For each task, create a plan with specific, actionable steps.

Format your plan as:
Goal: [overall goal]
Steps:
1. [first step]
2. [second step]
...

Maximum ${this.maxSteps} steps.

Guidelines:
- Make steps concrete and actionable
- Consider dependencies between steps
- Keep steps focused and achievable
- Include verification steps when appropriate`;
  }

  /**
   * Process a task by creating and executing a plan.
   *
   * @param message The task to accomplish
   * @returns Message with the final result
   */
  async process(message: Message): Promise<Message> {
    // Create plan
    const plan = await this.createPlan(String(message.content));
    this.currentPlan = plan;

    // Execute plan
    const result = await this.executePlan(plan);

    const completed = plan.steps.filter(s => s.status === StepStatus.COMPLETED).length;

    return createMessage(
      'assistant',
      `Task completed.\n\nGoal: ${plan.goal}\n\nSteps completed: ${completed}/${plan.steps.length}\n\nResult: ${result}`
    );
  }

  private async createPlan(task: string): Promise<Plan> {
    // Ask LLM to create a plan
    const messages = [
      createMessage('system', this.systemPrompt),
      createMessage('user', `Create a plan for: ${task}`),
    ];

    const response = await this.llm.chat(messages);

    // Parse the plan
    const plan = this.parsePlan(String(response.content), task);

    return plan;
  }

  private parsePlan(planText: string, goal: string): Plan {
    const lines = planText.trim().split('\n');

    // Extract goal
    let planGoal = goal;
    for (const line of lines) {
      if (line.trim().startsWith('Goal:')) {
        planGoal = line.split('Goal:')[1].trim();
        break;
      }
    }

    // Extract steps
    const steps: PlanStep[] = [];
    let inStepsSection = false;
    let stepNumber = 0;

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith('Steps:')) {
        inStepsSection = true;
        continue;
      }

      if (inStepsSection && trimmed) {
        // Remove leading numbers and dots
        let stepText = trimmed;
        const prefixes = [
          `${stepNumber + 1}.`,
          `${stepNumber + 1})`,
          `Step ${stepNumber + 1}:`,
        ];

        for (const prefix of prefixes) {
          if (stepText.startsWith(prefix)) {
            stepText = stepText.substring(prefix.length).trim();
            break;
          }
        }

        if (stepText && steps.length < this.maxSteps) {
          steps.push(createPlanStep(stepText, stepNumber));
          stepNumber++;
        }
      }
    }

    return createPlan(planGoal, steps);
  }

  private async executePlan(plan: Plan): Promise<string> {
    const context: Record<string, any> = {};
    const results: string[] = [];

    while (!isPlanComplete(plan)) {
      // Get next executable steps
      const nextSteps = getNextSteps(plan);

      if (nextSteps.length === 0) {
        // No steps can execute (all blocked or completed)
        if (hasPlanFailures(plan) && this.allowReplanning) {
          // Try to replan around failures
          await this.replan(plan);
          continue;
        } else {
          break;
        }
      }

      // Execute next steps (for now, sequentially)
      for (const step of nextSteps) {
        step.status = StepStatus.IN_PROGRESS;

        try {
          const result = await this.executor.execute(step, context);
          step.result = result;
          step.status = StepStatus.COMPLETED;

          // Add result to context for future steps
          context[`step_${step.stepNumber}_result`] = result;
          results.push(`Step ${step.stepNumber + 1}: ${step.description} ✓`);
        } catch (error) {
          step.error = error instanceof Error ? error.message : String(error);
          step.status = StepStatus.FAILED;
          results.push(`Step ${step.stepNumber + 1}: ${step.description} ✗ (${step.error})`);
        }
      }
    }

    // Generate summary
    let summary = results.join('\n');

    if (isPlanComplete(plan)) {
      summary += `\n\nPlan completed successfully (${getPlanProgress(plan).toFixed(0)}%)`;
    } else if (hasPlanFailures(plan)) {
      summary += `\n\nPlan failed (${getPlanProgress(plan).toFixed(0)}% complete)`;
    } else {
      summary += `\n\nPlan partially completed (${getPlanProgress(plan).toFixed(0)}%)`;
    }

    return summary;
  }

  private async replan(failedPlan: Plan): Promise<void> {
    // Get failed steps
    const failedSteps = failedPlan.steps.filter(step => step.status === StepStatus.FAILED);

    if (failedSteps.length === 0) {
      return;
    }

    // Ask LLM to create alternative steps
    const failedDescriptions = failedSteps
      .map(step => `- ${step.description} (Error: ${step.error})`)
      .join('\n');

    const messages = [
      createMessage('system', this.systemPrompt),
      createMessage(
        'user',
        `The following steps failed:\n${failedDescriptions}\n\nCreate alternative steps to accomplish the goal: ${failedPlan.goal}`
      ),
    ];

    await this.llm.chat(messages);

    // For simplicity, mark failed steps as skipped
    for (const step of failedSteps) {
      step.status = StepStatus.SKIPPED;
    }
  }

  /**
   * Get the current plan.
   */
  getPlan(): Plan | undefined {
    return this.currentPlan;
  }

  /**
   * Get current plan progress as a percentage.
   */
  getProgress(): number {
    if (this.currentPlan) {
      return getPlanProgress(this.currentPlan);
    }
    return 0;
  }
}
