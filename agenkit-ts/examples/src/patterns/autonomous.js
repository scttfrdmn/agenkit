"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.AutonomousAgent = void 0;
exports.createGoal = createGoal;
const interfaces_1 = require("../core/interfaces");
/**
 * Create a new goal.
 */
function createGoal(description, priority = 1, status = 'active', progress = 0.0, createdAt) {
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
class AutonomousAgent {
    constructor(objective, maxIterations = 10, stopCondition) {
        this.name = 'AutonomousAgent';
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
    async process(message) {
        return (0, interfaces_1.createMessage)('assistant', `Autonomous agent working on: ${this.objective}`);
    }
    /**
     * Add a goal for the agent to pursue.
     */
    addGoal(description, priority = 1) {
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
    async run() {
        this.isRunning = true;
        const results = [];
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
    async workOnGoal(goal) {
        // Mock implementation
        return `Progress on: ${goal.description}`;
    }
    /**
     * Stop the autonomous agent.
     */
    stop() {
        this.isRunning = false;
    }
    /**
     * Get overall progress as a percentage (0-100).
     */
    getProgress() {
        if (this.goals.length === 0) {
            return 0.0;
        }
        const totalProgress = this.goals.reduce((sum, g) => sum + g.progress, 0);
        return (totalProgress / this.goals.length) * 100;
    }
}
exports.AutonomousAgent = AutonomousAgent;
