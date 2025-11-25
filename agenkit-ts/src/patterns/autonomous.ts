/**
 * Autonomous Agent Pattern
 *
 * An agent that operates independently with minimal human intervention:
 * - Sets its own goals based on high-level objectives
 * - Makes decisions about actions to take
 * - Monitors progress and adapts strategy
 * - Continues until objective is met or stopped
 *
 * This pattern is useful for:
 * - Long-running tasks
 * - Self-directed research
 * - Continuous improvement systems
 * - Automated workflows
 *
 * Key Concepts:
 * - Objective: High-level goal the agent is working towards
 * - Goals: Specific sub-tasks the agent pursues
 * - Iterations: Number of work cycles completed
 * - Stop Condition: Optional function to halt execution early
 *
 * Example:
 * ```typescript
 * import { AutonomousAgent } from 'agenkit';
 *
 * const agent = new AutonomousAgent(
 *   'Research and summarize AI trends',
 *   10
 * );
 *
 * agent.addGoal('Search for recent AI papers', 10);
 * agent.addGoal('Identify key trends', 5);
 * agent.addGoal('Write summary report', 1);
 *
 * const result = await agent.run();
 * // Agent operates independently until complete
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Goal status values.
 */
export type GoalStatus = 'active' | 'completed' | 'abandoned';

/**
 * A goal the autonomous agent is pursuing.
 */
export interface Goal {
  /** Goal description */
  description: string;
  /** Priority (higher = more important) */
  priority: number;
  /** Current status */
  status: GoalStatus;
  /** Progress (0.0 to 1.0) */
  progress: number;
  /** When the goal was created */
  createdAt: Date;
}

/**
 * Result of running an autonomous agent.
 */
export interface AutonomousResult {
  /** The objective being pursued */
  objective: string;
  /** Number of iterations completed */
  iterations: number;
  /** Number of goals completed */
  goalsCompleted: number;
  /** Results from each iteration */
  results: string[];
}

/**
 * Stop condition function.
 */
export type StopCondition = () => boolean;

/**
 * Create a new goal.
 */
export function createGoal(
  description: string,
  priority: number = 1,
  status: GoalStatus = 'active',
  progress: number = 0.0,
  createdAt?: Date
): Goal {
  return {
    description,
    priority,
    status,
    progress,
    createdAt: createdAt || new Date(),
  };
}

/**
 * Agent that operates autonomously toward objectives.
 *
 * The autonomous agent:
 * - Manages multiple goals with different priorities
 * - Works on the highest priority active goal each iteration
 * - Updates progress and marks goals as completed
 * - Runs until max iterations, all goals complete, or stop condition met
 *
 * Subclass and override `workOnGoal()` to implement custom behavior.
 */
export class AutonomousAgent implements Agent {
  readonly name = 'AutonomousAgent';

  /** High-level objective */
  public objective: string;
  /** Maximum iterations to run */
  public maxIterations: number;
  /** Optional stop condition */
  public stopCondition?: StopCondition;
  /** Goals being pursued */
  public goals: Goal[];
  /** Number of iterations completed */
  public iterationCount: number;
  /** Whether the agent is currently running */
  public isRunning: boolean;

  constructor(objective: string, maxIterations: number = 10, stopCondition?: StopCondition) {
    this.objective = objective;
    this.maxIterations = maxIterations;
    this.stopCondition = stopCondition;
    this.goals = [];
    this.iterationCount = 0;
    this.isRunning = false;
  }

  /**
   * Process a message (autonomous agents don't need messages).
   */
  async process(message: Message): Promise<Message> {
    return createMessage('assistant', `Autonomous agent working on: ${this.objective}`);
  }

  /**
   * Add a goal for the agent to pursue.
   */
  addGoal(description: string, priority: number = 1): Goal {
    const goal = createGoal(description, priority);
    this.goals.push(goal);
    return goal;
  }

  /**
   * Run the autonomous agent.
   *
   * Executes work iterations until:
   * - Max iterations reached
   * - All goals completed
   * - Stop condition met
   * - Agent manually stopped
   */
  async run(): Promise<AutonomousResult> {
    this.isRunning = true;
    const results: string[] = [];

    while (this.iterationCount < this.maxIterations && this.isRunning) {
      // Select next action
      const activeGoals = this.goals.filter(g => g.status === 'active');
      if (activeGoals.length === 0) {
        break;
      }

      this.iterationCount++;

      // Check stop condition (after increment to match Python behavior)
      if (this.stopCondition && this.stopCondition()) {
        break;
      }

      // Work on highest priority goal
      const goal = activeGoals.reduce((max, g) => (g.priority > max.priority ? g : max));
      const result = await this.workOnGoal(goal);
      results.push(result);

      // Update progress
      goal.progress += 0.2;
      if (goal.progress >= 1.0) {
        goal.status = 'completed';
      }
    }

    this.isRunning = false;

    return {
      objective: this.objective,
      iterations: this.iterationCount,
      goalsCompleted: this.goals.filter(g => g.status === 'completed').length,
      results,
    };
  }

  /**
   * Work on a specific goal.
   *
   * Override this method to implement custom behavior.
   */
  protected async workOnGoal(goal: Goal): Promise<string> {
    // Mock implementation
    return `Progress on: ${goal.description}`;
  }

  /**
   * Stop the autonomous agent.
   */
  stop(): void {
    this.isRunning = false;
  }

  /**
   * Get overall progress as a percentage (0-100).
   */
  getProgress(): number {
    if (this.goals.length === 0) {
      return 0.0;
    }

    const totalProgress = this.goals.reduce((sum, g) => sum + g.progress, 0);
    return (totalProgress / this.goals.length) * 100;
  }
}
