/**
 * Autonomous Pattern Example
 *
 * Demonstrates:
 * - Autonomous agent operation with minimal supervision
 * - Goal-based task management
 * - Self-directed execution
 * - Progress tracking
 * - Stop conditions and manual control
 *
 * WHY use this pattern:
 * ✅ Agents operate independently toward objectives
 * ✅ Self-directed goal management
 * ✅ Long-running tasks without constant supervision
 * ✅ Adaptive behavior based on progress
 * ✅ Flexible control (stop conditions, manual stop)
 *
 * WHEN to use:
 * - Long-running tasks that don't need constant supervision
 * - Self-directed research and exploration
 * - Continuous improvement systems
 * - Automated workflows and maintenance
 * - Tasks where agent should decide how to proceed
 *
 * WHEN NOT to use:
 * - Simple one-shot tasks (use Task pattern)
 * - Highly controlled workflows (use Planning pattern)
 * - Interactive tasks needing human input at each step
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/autonomous-pattern.js
 */

import { AutonomousAgent, Goal, createGoal } from '../../src/patterns/autonomous';
import { Message } from '../../src/core/interfaces';

/**
 * Research agent that autonomously gathers information
 */
class ResearchAgent extends AutonomousAgent {
  private researchResults: string[] = [];

  async workOnGoal(goal: Goal): Promise<string> {
    // Simulate research work
    await new Promise(resolve => setTimeout(resolve, 100));

    const result = `Researched: ${goal.description}`;
    this.researchResults.push(result);

    // Mark goal as making progress
    goal.progress = 1.0;
    goal.status = 'completed';

    return result;
  }

  getResearchResults(): string[] {
    return [...this.researchResults];
  }
}

/**
 * Monitoring agent that checks system status
 */
class MonitoringAgent extends AutonomousAgent {
  private checks: number = 0;

  async workOnGoal(goal: Goal): Promise<string> {
    // Simulate monitoring check
    await new Promise(resolve => setTimeout(resolve, 50));

    this.checks += 1;

    const result = `Monitoring check ${this.checks}: ${goal.description}`;

    // Mark as partially complete (continuous monitoring)
    goal.progress = Math.min(goal.progress + 0.2, 1.0);

    if (goal.progress >= 1.0) {
      goal.status = 'completed';
    }

    return result;
  }

  getCheckCount(): number {
    return this.checks;
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Autonomous Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Basic autonomous operation
  console.log('-'.repeat(70));
  console.log('Example 1: Basic Autonomous Operation');
  console.log('-'.repeat(70));
  console.log();

  const agent1 = new ResearchAgent('Research AI agent patterns', 5);

  // Add goals for the agent to pursue
  agent1.addGoal('Review reflection pattern', 3);
  agent1.addGoal('Review ReAct pattern', 3);
  agent1.addGoal('Review multiagent pattern', 2);

  console.log(`Objective: ${agent1.objective}`);
  console.log(`Max iterations: ${agent1.maxIterations}`);
  console.log(`Goals: ${agent1.goals.length}`);
  console.log();

  console.log('Goals to pursue:');
  agent1.goals.forEach((goal, i) => {
    console.log(`  ${i + 1}. ${goal.description} (priority: ${goal.priority})`);
  });
  console.log();

  console.log('Running autonomous agent...');
  const result1 = await agent1.run();

  console.log();
  console.log('Completed!');
  console.log(`  Iterations: ${result1.iterations}`);
  console.log(`  Goals completed: ${result1.goalsCompleted}/${agent1.goals.length}`);
  console.log(`  Overall progress: ${agent1.getProgress().toFixed(1)}%`);
  console.log();

  console.log('Research results:');
  agent1.getResearchResults().forEach((result, i) => {
    console.log(`  ${i + 1}. ${result}`);
  });
  console.log();

  // Example 2: Goal priority management
  console.log('-'.repeat(70));
  console.log('Example 2: Goal Priority Management');
  console.log('-'.repeat(70));
  console.log();

  const agent2 = new ResearchAgent('Complete multiple tasks', 10);

  // Add goals with different priorities
  agent2.addGoal('Low priority task', 1);
  agent2.addGoal('High priority task', 10);
  agent2.addGoal('Medium priority task', 5);
  agent2.addGoal('Another high priority', 10);

  console.log('Goals in order of priority:');
  const sortedGoals = [...agent2.goals].sort((a, b) => b.priority - a.priority);
  sortedGoals.forEach((goal, i) => {
    console.log(`  ${i + 1}. [Priority ${goal.priority}] ${goal.description}`);
  });
  console.log();

  console.log('Agent will process goals by priority (highest first)');
  console.log('Running...');
  const result2 = await agent2.run();

  console.log();
  console.log('Execution order (by priority):');
  result2.results.forEach((result, i) => {
    console.log(`  ${i + 1}. ${result}`);
  });
  console.log();

  // Example 3: Progress tracking
  console.log('-'.repeat(70));
  console.log('Example 3: Real-time Progress Tracking');
  console.log('-'.repeat(70));
  console.log();

  const agent3 = new ResearchAgent('Long-running research task', 15);

  agent3.addGoal('Phase 1: Literature review', 3);
  agent3.addGoal('Phase 2: Data collection', 2);
  agent3.addGoal('Phase 3: Analysis', 1);

  console.log(`Task: ${agent3.objective}`);
  console.log(`Total goals: ${agent3.goals.length}`);
  console.log();

  console.log('Tracking progress in real-time:');

  // Start agent in background
  const task3 = agent3.run();

  // Monitor progress
  let lastProgress = 0;
  const interval = setInterval(() => {
    const progress = agent3.getProgress();
    if (progress !== lastProgress) {
      const status = agent3.isRunning ? 'Running' : 'Stopped';
      console.log(`  [${status}] Progress: ${progress.toFixed(1)}% (Iteration: ${agent3.iterationCount})`);
      lastProgress = progress;
    }
  }, 150);

  await task3;
  clearInterval(interval);

  console.log(`  [Complete] Final progress: ${agent3.getProgress().toFixed(1)}%`);
  console.log();

  // Example 4: Stop conditions
  console.log('-'.repeat(70));
  console.log('Example 4: Custom Stop Conditions');
  console.log('-'.repeat(70));
  console.log();

  // Track external condition
  const context = {
    itemsProcessed: 0,
    target: 5,
  };

  const stopWhenTargetReached = (): boolean => {
    return context.itemsProcessed >= context.target;
  };

  class ProcessingAgent extends AutonomousAgent {
    async workOnGoal(goal: Goal): Promise<string> {
      context.itemsProcessed += 1;
      await new Promise(resolve => setTimeout(resolve, 50));

      goal.progress = 1.0;
      goal.status = 'completed';

      return `Processed item ${context.itemsProcessed}`;
    }
  }

  const agent4 = new ProcessingAgent(
    'Process items until target reached',
    100, // High iteration limit
    stopWhenTargetReached
  );

  agent4.addGoal('Process items', 1);

  console.log(`Target: Process ${context.target} items`);
  console.log(`Max iterations: ${agent4.maxIterations}`);
  console.log();

  console.log('Running with stop condition...');
  const result4 = await agent4.run();

  console.log();
  console.log(`Stopped after ${result4.iterations} iterations`);
  console.log(`Items processed: ${context.itemsProcessed}`);
  console.log('Stop condition triggered successfully!');
  console.log();

  // Example 5: Manual control
  console.log('-'.repeat(70));
  console.log('Example 5: Manual Stop Control');
  console.log('-'.repeat(70));
  console.log();

  const agent5 = new MonitoringAgent('Continuous monitoring task', 100);
  agent5.addGoal('Monitor system health', 1);

  console.log('Starting monitoring agent (will stop after 3 iterations)...');
  console.log();

  // Start agent in background
  const task5 = agent5.run();

  // Let it run for a bit
  await new Promise(resolve => setTimeout(resolve, 200));

  // Stop it manually
  console.log('Stopping agent manually...');
  agent5.stop();

  const result5 = await task5;

  console.log();
  console.log(`Agent stopped after ${result5.iterations} iterations`);
  console.log(`Monitoring checks performed: ${agent5.getCheckCount()}`);
  console.log('Manual control successful!');
  console.log();

  // Example 6: Dynamic goal management
  console.log('-'.repeat(70));
  console.log('Example 6: Dynamic Goal Management');
  console.log('-'.repeat(70));
  console.log();

  class AdaptiveAgent extends AutonomousAgent {
    private discoveries: string[] = [];

    async workOnGoal(goal: Goal): Promise<string> {
      await new Promise(resolve => setTimeout(resolve, 50));

      // Simulate discovery of new goals
      if (goal.description.includes('explore') && this.discoveries.length < 2) {
        const newGoalDesc = `Follow up on discovery ${this.discoveries.length + 1}`;
        this.addGoal(newGoalDesc, 5);
        this.discoveries.push(newGoalDesc);

        goal.progress = 1.0;
        goal.status = 'completed';

        return `Completed: ${goal.description} (discovered new goal!)`;
      }

      goal.progress = 1.0;
      goal.status = 'completed';

      return `Completed: ${goal.description}`;
    }

    getDiscoveries(): string[] {
      return [...this.discoveries];
    }
  }

  const agent6 = new AdaptiveAgent('Explore and adapt', 15);

  agent6.addGoal('Explore area A', 10);
  agent6.addGoal('Explore area B', 10);

  console.log(`Initial goals: ${agent6.goals.length}`);
  console.log();

  console.log('Running adaptive agent (may add goals dynamically)...');
  const result6 = await agent6.run();

  console.log();
  console.log(`Total goals created: ${agent6.goals.length}`);
  console.log(`Goals completed: ${result6.goalsCompleted}`);
  console.log(`Discoveries made: ${agent6.getDiscoveries().length}`);
  console.log();

  console.log('All goals:');
  agent6.goals.forEach((goal, i) => {
    const statusIcon = {
      'active': '○',
      'completed': '✓',
      'abandoned': '✗',
    }[goal.status] || '?';
    console.log(`  ${statusIcon} ${goal.description} (priority: ${goal.priority}, ${goal.status})`);
  });
  console.log();

  // Pattern comparison
  console.log('-'.repeat(70));
  console.log('Pattern Comparison');
  console.log('-'.repeat(70));
  console.log();

  console.log('Autonomous Pattern:');
  console.log('  • Agent operates independently toward objectives');
  console.log('  • Self-directed goal management');
  console.log('  • Adapts based on discoveries');
  console.log('  • Use for: research, monitoring, exploration');
  console.log();

  console.log('Planning Pattern:');
  console.log('  • Break tasks into predefined steps');
  console.log('  • Fixed plan with dependencies');
  console.log('  • Execute steps in order');
  console.log('  • Use for: deployment, workflows with fixed structure');
  console.log();

  console.log('Task Pattern:');
  console.log('  • One-shot execution with cleanup');
  console.log('  • Single operation, then done');
  console.log('  • Use for: summarization, classification');
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All autonomous examples completed!');
  console.log();
  console.log('Key Benefits of Autonomous Pattern:');
  console.log('  • Independent operation with minimal supervision');
  console.log('  • Goal-based task management');
  console.log('  • Adaptive behavior (add goals dynamically)');
  console.log('  • Flexible control (stop conditions, manual stop)');
  console.log('  • Progress tracking for long-running tasks');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace mock agents with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude for autonomous reasoning)');
  console.log('  - OpenAIAdapter (GPT-4 for self-directed tasks)');
  console.log('  - LLMs will make intelligent decisions about goal execution');
  console.log();
  console.log('When to Use Autonomous Pattern:');
  console.log('  • Self-directed research and exploration');
  console.log('  • Long-running monitoring tasks');
  console.log('  • Continuous improvement systems');
  console.log('  • Tasks where agent decides how to proceed');
  console.log('  • Workflows that adapt based on discoveries');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
