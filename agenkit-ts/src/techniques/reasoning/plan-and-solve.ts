/**
 * Plan-and-Solve Prompting Technique
 *
 * Explicitly separates planning (devising a solution strategy) from solving
 * (executing the strategy). Creates more structured reasoning than pure CoT
 * by forcing an upfront planning phase.
 *
 * Reference:
 * - Paper: https://arxiv.org/abs/2305.04091
 * - "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning"
 */

import type { Agent, Message } from '../../core/interfaces';

export interface PlanStep {
  description: string;
  order: number;
  dependencies: number[];
  estimatedComplexity: number;
  result?: string;
  executed: boolean;
}

export interface Plan {
  steps: PlanStep[];
  problem: string;
  strategy?: string;
  validated: boolean;
  validationNotes?: string;
}

export type PlannerFunc = (problem: string) => Promise<Plan>;
export type SolverFunc = (step: PlanStep, previousResults: string[]) => Promise<string>;

export interface PlanAndSolveConfig {
  planner?: PlannerFunc;
  solver?: SolverFunc;
  validatePlan?: boolean;
  allowReplanning?: boolean;
}

export class PlanAndSolve implements Agent {
  private readonly llm: Agent;
  private readonly planner?: PlannerFunc;
  private readonly solver?: SolverFunc;
  private readonly validatePlanFlag: boolean;
  private readonly allowReplanning: boolean;

  constructor(llm: Agent, config: PlanAndSolveConfig = {}) {
    this.llm = llm;
    this.planner = config.planner;
    this.solver = config.solver;
    this.validatePlanFlag = config.validatePlan ?? true;
    this.allowReplanning = config.allowReplanning ?? false;
  }

  get name(): string {
    return 'plan_and_solve';
  }

  get capabilities(): string[] {
    return ['reasoning', 'planning', 'plan_and_solve', 'strategic_thinking', 'step_by_step_execution'];
  }

  private async llmCall(prompt: string): Promise<string> {
    const response = await this.llm.process({ role: 'user', content: prompt });
    return typeof response.content === 'string' ? response.content : String(response.content);
  }

  private async createPlan(problem: string): Promise<Plan> {
    if (this.planner) {
      return this.planner(problem);
    }

    const prompt = `Create a detailed step-by-step plan to solve this problem.
List each step on a separate line, numbered 1, 2, 3, etc.
Focus on WHAT needs to be done, not HOW to do it yet.

Problem: ${problem}

Solution Plan:`;

    const response = await this.llmCall(prompt);
    const steps: PlanStep[] = [];
    const lines = response.trim().split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const cleaned = line.replace(/^\d+[.)]\s*/, '');
      if (cleaned) {
        steps.push({
          description: cleaned,
          order: i,
          dependencies: [],
          estimatedComplexity: 1,
          executed: false,
        });
      }
    }

    return { steps, problem, validated: false };
  }

  private async validatePlan(plan: Plan): Promise<Plan> {
    const prompt = `Review this solution plan for completeness and feasibility.
Is this plan sufficient to solve the problem? Are there any missing steps or issues?

Problem: ${plan.problem}

Plan:
${this.formatPlan(plan)}

Validation (answer "VALID" or describe issues):`;

    const response = await this.llmCall(prompt);
    const responseUpper = response.toUpperCase();
    // Check for INVALID first to avoid matching "VALID" inside "INVALID"
    const isValid = !responseUpper.includes('INVALID') &&
                    (responseUpper.includes('VALID') || responseUpper.includes('YES'));

    return {
      ...plan,
      validated: isValid,
      validationNotes: response.trim(),
    };
  }

  private formatPlan(plan: Plan): string {
    return plan.steps
      .map((step, i) => {
        const status = step.executed ? '✓' : '○';
        return `${i + 1}. [${status}] ${step.description}`;
      })
      .join('\n');
  }

  private async executeStep(step: PlanStep, previousResults: string[]): Promise<string> {
    if (this.solver) {
      return this.solver(step, previousResults);
    }

    let prompt: string;
    if (previousResults.length > 0) {
      const context = previousResults
        .map((result, i) => `Previous step ${i + 1} result: ${result}`)
        .join('\n');

      prompt = `Execute this step of the plan, using previous results as context.

Previous Results:
${context}

Current Step: ${step.description}

Execution Result:`;
    } else {
      prompt = `Execute this step of the plan:

Step: ${step.description}

Execution Result:`;
    }

    const result = await this.llmCall(prompt);
    return result.trim();
  }

  private async executePlan(plan: Plan): Promise<string[]> {
    const results: string[] = [];

    for (const step of plan.steps) {
      const result = await this.executeStep(step, results);
      step.result = result;
      step.executed = true;
      results.push(result);
    }

    return results;
  }

  async process(message: Message): Promise<Message> {
    const problem = typeof message.content === 'string' ? message.content : String(message.content);
    let plan = await this.createPlan(problem);

    if (this.validatePlanFlag) {
      plan = await this.validatePlan(plan);

      if (!plan.validated && this.allowReplanning) {
        const improvedPrompt = `The previous plan had issues. Create an improved plan.

Problem: ${problem}

Previous Plan Issues:
${plan.validationNotes}

Improved Plan:`;

        await this.llmCall(improvedPrompt);
        plan = await this.createPlan(problem);
        plan = await this.validatePlan(plan);
      }
    }

    const executionResults = await this.executePlan(plan);
    const finalSolution = executionResults.length > 0 ? executionResults[executionResults.length - 1] : '';

    return {
      role: 'assistant',
      content: finalSolution,
      metadata: {
        technique: 'plan_and_solve',
        plan_steps: plan.steps.map(s => s.description),
        execution_steps: executionResults,
        num_steps: plan.steps.length,
        validated: plan.validated,
        validation_notes: plan.validationNotes,
        allow_replanning: this.allowReplanning,
        ...(plan.strategy && { strategy: plan.strategy }),
      },
    };
  }
}
