/**
 * Planning Pattern Example
 *
 * Demonstrates:
 * - Breaking complex tasks into steps
 * - Plan creation and execution
 * - Step dependencies and ordering
 * - Progress tracking
 * - Failure handling and recovery
 *
 * WHY use this pattern:
 * ✅ Breaks complex tasks into manageable steps
 * ✅ Handles dependencies between steps
 * ✅ Tracks progress through multi-step workflows
 * ✅ Adapts to failures (replanning, retry)
 * ✅ Makes agent reasoning transparent
 *
 * WHEN to use:
 * - Multi-step tasks requiring coordination
 * - Tasks where order and dependencies matter
 * - Complex workflows needing progress tracking
 * - Tasks that may need replanning on failures
 * - When you need visibility into agent reasoning
 *
 * WHEN NOT to use:
 * - Simple single-step tasks
 * - Tasks without dependencies
 * - Real-time reactive tasks (use ReAct instead)
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/planning-pattern.js
 */

import { Agent, Message, createMessage } from '../../src/core/interfaces';
import {
  Plan,
  PlanStep,
  StepStatus,
  createPlan,
  createPlanStep,
  getNextSteps,
  isPlanComplete,
} from '../../src/patterns/planning';

/**
 * Mock planner that generates plans for demonstration
 */
class MockPlanner implements Agent {
  constructor() {}  // No LLM needed for mock

  name(): string {
    return 'PlanningAgent';
  }

  capabilities(): string[] {
    return ['planning', 'task-breakdown'];
  }

  async process(message: Message): Promise<Message> {
    // Mock planner generates predefined plans based on keywords
    // In production, replace with real LLM to generate dynamic plans
    const task = message.content.toLowerCase();

    let planText = '';

    if (task.includes('deploy') || task.includes('website')) {
      planText = `Goal: Deploy website to production

Steps:
1. Run tests to ensure code quality
2. Build production assets
3. Create database backup
4. Deploy to staging environment
5. Run smoke tests on staging
6. Deploy to production`;
    } else if (task.includes('organize') && task.includes('event')) {
      planText = `Goal: Organize a successful team event

Steps:
1. Choose date and venue
2. Create invitation list
3. Send invitations
4. Arrange catering
5. Confirm attendees
6. Prepare materials`;
    } else if (task.includes('research')) {
      planText = `Goal: Complete research project

Steps:
1. Review existing literature
2. Design research methodology
3. Collect data
4. Analyze results
5. Write report`;
    } else {
      planText = `Goal: Complete the task

Steps:
1. Break down the task
2. Execute each part
3. Verify results`;
    }

    return createMessage({ role: 'assistant', content: planText });
  }
}

/**
 * Simple step executor for demonstration
 */
class SimpleStepExecutor {
  private executionLog: string[] = [];
  private failSteps: number[];

  constructor(failSteps: number[] = []) {
    this.failSteps = failSteps;
  }

  async execute(step: PlanStep): Promise<string> {
    this.executionLog.push(`Executing step ${step.stepNumber}: ${step.description}`);

    // Simulate execution time
    await new Promise(resolve => setTimeout(resolve, 100));

    // Simulate failure for specific steps
    if (this.failSteps.includes(step.stepNumber)) {
      throw new Error(`Step ${step.stepNumber} failed (simulated failure)`);
    }

    return `Completed: ${step.description}`;
  }

  getLog(): string[] {
    return [...this.executionLog];
  }
}

/**
 * Parse plan text into Plan object
 */
function parsePlan(planText: string): Plan {
  const lines = planText.split('\n').map(l => l.trim()).filter(l => l);

  let goal = 'Complete the task';
  const steps: PlanStep[] = [];

  for (const line of lines) {
    if (line.startsWith('Goal:')) {
      goal = line.substring(5).trim();
    } else if (/^\d+\./.test(line)) {
      // Parse step: "1. Step description"
      const match = line.match(/^(\d+)\.\s+(.+)$/);
      if (match) {
        const stepNumber = parseInt(match[1], 10) - 1; // 0-indexed
        const description = match[2];
        const deps = stepNumber > 0 ? [stepNumber - 1] : []; // Simple sequential dependency
        steps.push(createPlanStep(description, stepNumber, deps));
      }
    }
  }

  return createPlan(goal, steps);
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Planning Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Basic planning
  console.log('-'.repeat(70));
  console.log('Example 1: Basic Plan Creation and Execution');
  console.log('-'.repeat(70));
  console.log();

  const planner = new MockPlanner();
  const executor = new SimpleStepExecutor();

  const task1 = createMessage({
    role: 'user',
    content: 'Organize a team event',
  });

  console.log(`Task: ${task1.content}`);
  console.log();

  // Generate plan
  const planResponse = await planner.process(task1);
  const plan1 = parsePlan(planResponse.content);

  console.log(`Plan created: ${plan1.goal}`);
  console.log(`Total steps: ${plan1.steps.length}`);
  console.log();

  // Display plan
  console.log('Steps:');
  plan1.steps.forEach(step => {
    const deps = step.dependencies.length > 0
      ? ` (depends on: ${step.dependencies.map(d => d + 1).join(', ')})`
      : '';
    console.log(`  ${step.stepNumber + 1}. ${step.description}${deps}`);
  });
  console.log();

  // Execute plan
  console.log('Executing plan:');
  const completed: number[] = [];

  while (!isPlanComplete(plan1)) {
    const nextSteps = getNextSteps(plan1);

    if (nextSteps.length === 0) {
      console.log('  No more steps can execute (possible failure or deadlock)');
      break;
    }

    for (const step of nextSteps) {
      step.status = StepStatus.IN_PROGRESS;
      try {
        const result = await executor.execute(step);
        step.status = StepStatus.COMPLETED;
        step.result = result;
        completed.push(step.stepNumber);
        console.log(`  ✓ Step ${step.stepNumber + 1}: ${step.description}`);
      } catch (error) {
        step.status = StepStatus.FAILED;
        step.error = error instanceof Error ? error.message : 'Unknown error';
        console.log(`  ✗ Step ${step.stepNumber + 1} failed: ${step.error}`);
      }
    }
  }

  console.log();
  console.log(`Progress: ${completed.length}/${plan1.steps.length} steps completed`);
  console.log();

  // Example 2: Plan with dependencies
  console.log('-'.repeat(70));
  console.log('Example 2: Complex Plan with Dependencies');
  console.log('-'.repeat(70));
  console.log();

  const task2 = createMessage({
    role: 'user',
    content: 'Deploy website to production',
  });

  console.log(`Task: ${task2.content}`);
  console.log();

  const planResponse2 = await planner.process(task2);
  const plan2 = parsePlan(planResponse2.content);

  console.log(`Plan: ${plan2.goal}`);
  console.log();

  console.log('Steps with dependencies:');
  plan2.steps.forEach(step => {
    const deps = step.dependencies.length > 0
      ? step.dependencies.map(d => `Step ${d + 1}`).join(', ')
      : 'None';
    console.log(`  Step ${step.stepNumber + 1}: ${step.description}`);
    console.log(`    Dependencies: ${deps}`);
  });
  console.log();

  // Example 3: Failure handling
  console.log('-'.repeat(70));
  console.log('Example 3: Handling Step Failures');
  console.log('-'.repeat(70));
  console.log();

  // Create executor that will fail on step 2
  const failingExecutor = new SimpleStepExecutor([2]);

  const task3 = createMessage({
    role: 'user',
    content: 'Complete research project',
  });

  console.log(`Task: ${task3.content}`);
  console.log();

  const planResponse3 = await planner.process(task3);
  const plan3 = parsePlan(planResponse3.content);

  console.log(`Plan: ${plan3.goal}`);
  console.log(`Steps: ${plan3.steps.length}`);
  console.log();

  console.log('Executing with simulated failure on step 3:');
  const completed3: number[] = [];

  while (!isPlanComplete(plan3)) {
    const nextSteps = getNextSteps(plan3);

    if (nextSteps.length === 0) {
      console.log('  No more steps can execute');
      break;
    }

    for (const step of nextSteps) {
      step.status = StepStatus.IN_PROGRESS;
      try {
        const result = await failingExecutor.execute(step);
        step.status = StepStatus.COMPLETED;
        step.result = result;
        completed3.push(step.stepNumber);
        console.log(`  ✓ Step ${step.stepNumber + 1}: ${step.description}`);
      } catch (error) {
        step.status = StepStatus.FAILED;
        step.error = error instanceof Error ? error.message : 'Unknown error';
        console.log(`  ✗ Step ${step.stepNumber + 1} failed: ${step.error}`);
        console.log(`    → Subsequent dependent steps cannot execute`);
      }
    }
  }

  console.log();
  console.log('Final status:');
  plan3.steps.forEach(step => {
    const statusIcon = {
      [StepStatus.COMPLETED]: '✓',
      [StepStatus.FAILED]: '✗',
      [StepStatus.PENDING]: '○',
      [StepStatus.IN_PROGRESS]: '⋯',
      [StepStatus.SKIPPED]: '⊘',
    }[step.status] || '?';

    console.log(`  ${statusIcon} Step ${step.stepNumber + 1}: ${step.description} (${step.status})`);
    if (step.error) {
      console.log(`    Error: ${step.error}`);
    }
  });
  console.log();

  // Example 4: Progress tracking
  console.log('-'.repeat(70));
  console.log('Example 4: Real-time Progress Tracking');
  console.log('-'.repeat(70));
  console.log();

  const task4 = createMessage({
    role: 'user',
    content: 'Organize a team event',
  });

  const planResponse4 = await planner.process(task4);
  const plan4 = parsePlan(planResponse4.content);

  console.log(`Task: ${plan4.goal}`);
  console.log(`Total steps: ${plan4.steps.length}`);
  console.log();

  const executor4 = new SimpleStepExecutor();
  const completed4: number[] = [];

  console.log('Executing with progress updates:');

  while (!isPlanComplete(plan4)) {
    const nextSteps = getNextSteps(plan4);

    if (nextSteps.length === 0) {
      break;
    }

    for (const step of nextSteps) {
      const progress = Math.round((completed4.length / plan4.steps.length) * 100);
      console.log(`  [${progress}%] Executing step ${step.stepNumber + 1}...`);

      step.status = StepStatus.IN_PROGRESS;
      try {
        await executor4.execute(step);
        step.status = StepStatus.COMPLETED;
        completed4.push(step.stepNumber);
      } catch (error) {
        step.status = StepStatus.FAILED;
      }
    }
  }

  const finalProgress = Math.round((completed4.length / plan4.steps.length) * 100);
  console.log(`  [${finalProgress}%] Complete!`);
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All planning examples completed!');
  console.log();
  console.log('Key Benefits of Planning Pattern:');
  console.log('  • Breaks complex tasks into steps automatically');
  console.log('  • Handles dependencies between steps');
  console.log('  • Tracks progress through workflows');
  console.log('  • Makes agent reasoning transparent');
  console.log('  • Adapts to failures and replans');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockPlanner with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude for plan generation)');
  console.log('  - OpenAIAdapter (GPT-4 for task breakdown)');
  console.log('  - LLMs will dynamically generate plans based on task description');
  console.log();
  console.log('When to Use Planning Pattern:');
  console.log('  • Multi-step tasks (deploy, organize, research)');
  console.log('  • Tasks with dependencies (step B needs step A)');
  console.log('  • Complex workflows needing tracking');
  console.log('  • Tasks that may need replanning');
  console.log();
  console.log('Pattern Comparison:');
  console.log('  • Planning: Break tasks into dependent steps');
  console.log('  • Orchestration: Coordinate multiple agents');
  console.log('  • ReAct: Reasoning + tool use (reactive)');
  console.log('  • Task: One-shot execution with cleanup');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
