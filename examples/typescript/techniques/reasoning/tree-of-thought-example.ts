/**
 * Tree-of-Thought Reasoning Example
 *
 * This example demonstrates the Tree-of-Thought (ToT) reasoning technique,
 * which explores multiple reasoning paths simultaneously using tree search
 * with branching, evaluation, and backtracking.
 *
 * Reference: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
 * Yao et al., 2023 - https://arxiv.org/abs/2305.10601
 */

import { Agent, Message, createMessage } from '../../../../agenkit-ts/src/core/interfaces';
import { TreeOfThought } from '../../../../agenkit-ts/src/techniques/reasoning/tree-of-thought';

/**
 * Mock agent that generates diverse reasoning branches.
 */
class CreativeAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];
  private callCount: number;

  constructor() {
    this.name = 'creative_agent';
    this.capabilities = ['reasoning', 'creativity'];
    this.callCount = 0;
  }

  async process(message: Message): Promise<Message> {
    this.callCount++;
    const query = String(message.content);

    // Generate diverse reasoning paths
    const approaches = [
      `Approach A (call ${this.callCount}): Start by analyzing the requirements systematically and identifying key constraints.`,
      `Approach B (call ${this.callCount}): Take a creative angle by considering unconventional solutions first.`,
      `Approach C (call ${this.callCount}): Build incrementally from simple cases to complex ones.`,
      `Step ${this.callCount}: Continue refining the most promising path with additional details and considerations.`,
    ];

    const response = approaches[this.callCount % approaches.length];
    return createMessage('assistant', response);
  }
}

/**
 * Example 1: Basic Tree-of-Thought with Best-First Search
 */
async function example1(): Promise<void> {
  console.log('Example 1: Basic Tree-of-Thought with Best-First Search');
  console.log('-'.repeat(60));

  const baseAgent = new CreativeAgent();

  const tot = new TreeOfThought(baseAgent, {
    branchingFactor: 3,
    maxDepth: 2,
    strategy: 'best-first',
  });

  const message = createMessage('user', 'Design a sustainable urban transportation system');
  const response = await tot.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`\nBest Reasoning Path:`);

  const path = response.metadata?.reasoning_path as string[];
  path.forEach((step, i) => {
    console.log(`\nStep ${i + 1}:`);
    console.log(`  ${step.substring(0, 100)}${step.length > 100 ? '...' : ''}`);
  });

  const stats = response.metadata?.reasoning_tree_stats as any;
  console.log(`\nTree Statistics:`);
  console.log(`  Total Nodes Explored: ${stats.totalNodes}`);
  console.log(`  Maximum Depth: ${stats.maxDepth}`);
  console.log(`  Leaf Nodes: ${stats.numLeaves}`);
  console.log(`  Best Path Score: ${stats.bestScore.toFixed(2)}`);

  console.log();
}

/**
 * Example 2: Comparing Search Strategies
 */
async function example2(): Promise<void> {
  console.log('Example 2: Comparing Search Strategies');
  console.log('-'.repeat(60));

  const baseAgent = new CreativeAgent();
  const query = 'Plan a 3-day educational workshop';

  // Test all three strategies
  const strategies: Array<'bfs' | 'dfs' | 'best-first'> = ['bfs', 'dfs', 'best-first'];

  for (const strategy of strategies) {
    const tot = new TreeOfThought(baseAgent, {
      branchingFactor: 2,
      maxDepth: 2,
      strategy,
    });

    const response = await tot.process(createMessage('user', query));
    const stats = response.metadata?.reasoning_tree_stats as any;

    console.log(`\n${strategy.toUpperCase()} Strategy:`);
    console.log(`  Nodes Explored: ${stats.totalNodes}`);
    console.log(`  Leaves: ${stats.numLeaves}`);
    console.log(`  Best Score: ${stats.bestScore.toFixed(2)}`);
  }

  console.log('\nStrategy Comparison:');
  console.log('  - BFS: Explores all nodes at same depth first (breadth-first)');
  console.log('  - DFS: Explores deep paths first (depth-first)');
  console.log('  - Best-First: Always expands highest-scoring node (greedy)');

  console.log();
}

/**
 * Example 3: Custom Evaluator Function
 */
async function example3(): Promise<void> {
  console.log('Example 3: Custom Evaluator Function');
  console.log('-'.repeat(60));

  const baseAgent = new CreativeAgent();

  // Custom evaluator that favors responses with "Approach A"
  const customEvaluator = (text: string): number => {
    let score = Math.min(text.length / 500, 1.0); // Base score from length

    // Bonus for "Approach A"
    if (text.includes('Approach A')) {
      score = Math.min(score + 0.3, 1.0);
    }

    // Bonus for detailed analysis
    if (text.includes('systematically') || text.includes('constraints')) {
      score = Math.min(score + 0.1, 1.0);
    }

    return score;
  };

  const tot = new TreeOfThought(baseAgent, {
    branchingFactor: 3,
    maxDepth: 2,
    evaluator: customEvaluator,
    strategy: 'best-first',
  });

  const message = createMessage('user', 'Solve this problem optimally');
  const response = await tot.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`\nBest Path (with custom evaluator):`);

  const pathText = String(response.content);
  const lines = pathText.split('\n').slice(0, 5);
  lines.forEach((line) => console.log(`  ${line}`));

  console.log(`\nBest Score: ${(response.metadata?.best_score as number).toFixed(2)}`);
  console.log('\nNote: Custom evaluator favored paths with "Approach A"');
  console.log('and systematic analysis keywords.');

  console.log();
}

/**
 * Example 4: Pruning Low-Quality Paths
 */
async function example4(): Promise<void> {
  console.log('Example 4: Pruning Low-Quality Paths');
  console.log('-'.repeat(60));

  const baseAgent = new CreativeAgent();

  // Low pruning threshold (aggressive)
  console.log('With Aggressive Pruning (threshold = 0.5):');
  const totHighThreshold = new TreeOfThought(baseAgent, {
    branchingFactor: 3,
    maxDepth: 2,
    pruneThreshold: 0.5,
  });

  const message = createMessage('user', 'Optimize this process');
  const responseHigh = await totHighThreshold.process(message);
  const statsHigh = responseHigh.metadata?.reasoning_tree_stats as any;

  console.log(`  Total Nodes: ${statsHigh.totalNodes}`);
  console.log(`  Pruned Nodes: ${statsHigh.numPruned}`);
  console.log(`  Leaf Nodes: ${statsHigh.numLeaves}`);

  // High pruning threshold (lenient)
  console.log('\nWith Lenient Pruning (threshold = 0.2):');
  const totLowThreshold = new TreeOfThought(baseAgent, {
    branchingFactor: 3,
    maxDepth: 2,
    pruneThreshold: 0.2,
  });

  const responseLow = await totLowThreshold.process(message);
  const statsLow = responseLow.metadata?.reasoning_tree_stats as any;

  console.log(`  Total Nodes: ${statsLow.totalNodes}`);
  console.log(`  Pruned Nodes: ${statsLow.numPruned}`);
  console.log(`  Leaf Nodes: ${statsLow.numLeaves}`);

  console.log('\nPruning Trade-offs:');
  console.log('  - High threshold: Fewer nodes explored, faster, may miss good paths');
  console.log('  - Low threshold: More exploration, slower, better coverage');

  console.log();
}

/**
 * Example 5: Tree Statistics and Visualization
 */
async function example5(): Promise<void> {
  console.log('Example 5: Tree Statistics and Visualization');
  console.log('-'.repeat(60));

  const baseAgent = new CreativeAgent();

  const tot = new TreeOfThought(baseAgent, {
    branchingFactor: 3,
    maxDepth: 3,
    strategy: 'best-first',
  });

  const message = createMessage('user', 'Develop a comprehensive solution');
  const response = await tot.process(message);

  const stats = response.metadata?.reasoning_tree_stats as any;

  console.log('Detailed Tree Statistics:');
  console.log(`  Total Nodes: ${stats.totalNodes}`);
  console.log(`  Maximum Depth: ${stats.maxDepth}`);
  console.log(`  Leaf Nodes: ${stats.numLeaves}`);
  console.log(`  Evaluated Nodes: ${stats.numEvaluated}`);
  console.log(`  Pruned Nodes: ${stats.numPruned}`);
  console.log(`  Average Leaf Score: ${stats.avgScore.toFixed(2)}`);
  console.log(`  Best Leaf Score: ${stats.bestScore.toFixed(2)}`);

  console.log('\nReasoning Path Quality:');
  const bestScore = response.metadata?.best_score as number;
  if (bestScore > 0.7) {
    console.log('  ✓ High quality path found (score > 0.7)');
  } else if (bestScore > 0.4) {
    console.log('  ⚠ Moderate quality path (score 0.4-0.7)');
  } else {
    console.log('  ✗ Low quality path (score < 0.4)');
  }

  const path = response.metadata?.reasoning_path as string[];
  console.log(`\nBest Path (${response.metadata?.num_steps} steps):`);
  path.slice(0, 3).forEach((step, i) => {
    console.log(`  ${i + 1}. ${step.substring(0, 80)}${step.length > 80 ? '...' : ''}`);
  });
  if (path.length > 3) {
    console.log(`  ... (${path.length - 3} more steps)`);
  }

  console.log();
}

/**
 * Example 6: When to Use ToT vs CoT
 */
async function example6(): Promise<void> {
  console.log('Example 6: When to Use ToT vs CoT');
  console.log('-'.repeat(60));

  console.log('Use Tree-of-Thought (ToT) when:');
  console.log('  ✓ Problem has multiple valid approaches');
  console.log('  ✓ Need to explore solution space systematically');
  console.log('  ✓ Want to compare alternative reasoning paths');
  console.log('  ✓ Willing to trade speed for exploration');
  console.log('  ✓ Examples: Planning, strategy, creative problem-solving');

  console.log('\nUse Chain-of-Thought (CoT) when:');
  console.log('  ✓ Problem has a clear sequential solution');
  console.log('  ✓ Need explainable step-by-step reasoning');
  console.log('  ✓ Want faster results with single path');
  console.log('  ✓ Cost/token efficiency is important');
  console.log('  ✓ Examples: Math, logic, simple reasoning tasks');

  console.log('\nPerformance Comparison:');
  console.log('  - ToT explores O(branching_factor ^ depth) nodes');
  console.log('  - CoT follows a single linear path');
  console.log('  - ToT: More thorough but more expensive');
  console.log('  - CoT: Faster and cheaper but less exploration');

  console.log();
}

/**
 * Main function to run all examples.
 */
async function main(): Promise<void> {
  console.log('=== Tree-of-Thought Reasoning Examples ===\n');

  await example1();
  await example2();
  await example3();
  await example4();
  await example5();
  await example6();
}

// Run examples
main().catch((error) => {
  console.error('Error running examples:', error);
  process.exit(1);
});
