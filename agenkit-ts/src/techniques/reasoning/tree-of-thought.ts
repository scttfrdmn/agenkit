/**
 * Tree-of-Thought (ToT) Reasoning Technique
 *
 * Explores multiple reasoning paths simultaneously using tree search with
 * branching, evaluation, and backtracking.
 *
 * This technique builds a tree of reasoning paths, evaluates each path,
 * and uses search strategies to find the best solution. More sophisticated
 * than Chain-of-Thought for problems requiring exploration of solution space.
 *
 * References:
 *   - Paper: https://arxiv.org/abs/2305.10601 (Yao et al., 2023)
 *   - Tree search with LLM-generated thoughts
 *   - Systematic exploration of reasoning space
 *
 * @example
 * Basic usage:
 * ```typescript
 * import { TreeOfThought } from '@agenkit/techniques/reasoning';
 * import { createMessage } from '@agenkit';
 *
 * // Custom evaluator function
 * function scoreReasoning(text: string): number {
 *   // Simple heuristic: longer = more detailed = better
 *   return Math.min(text.length / 1000, 1.0);
 * }
 *
 * const tot = new TreeOfThought(myAgent, {
 *   branchingFactor: 3,
 *   maxDepth: 4,
 *   evaluator: scoreReasoning,
 * });
 *
 * const response = await tot.process(createMessage('user', 'Plan a 3-day trip to Tokyo'));
 *
 * // Access reasoning tree
 * const treeStats = response.metadata?.reasoning_tree_stats;
 * console.log(`Explored ${treeStats.total_nodes} reasoning paths`);
 * ```
 */

import type { Agent, Message } from '../../core/interfaces';
import { ReasoningTree, NodeState, type ReasoningNode } from './reasoning-tree';

/**
 * Search strategy for tree exploration.
 */
export type SearchStrategy = 'bfs' | 'dfs' | 'best-first';

/**
 * Function that evaluates and scores a reasoning path.
 * Should return a score between 0.0 and 1.0, where 1.0 is best.
 */
export type EvaluatorFunction = (text: string) => number;

/**
 * Configuration options for Tree-of-Thought agent.
 */
export interface TreeOfThoughtConfig {
  /**
   * Number of alternative reasoning paths to explore at each step.
   * Higher values explore more but cost more tokens.
   * Default: 3
   */
  branchingFactor?: number;

  /**
   * Maximum depth of reasoning tree.
   * Limits how many reasoning steps to take.
   * Default: 5
   */
  maxDepth?: number;

  /**
   * Function that scores a reasoning path (returns 0.0-1.0).
   * If undefined, uses a simple length-based heuristic.
   */
  evaluator?: EvaluatorFunction;

  /**
   * Search strategy to use:
   * - "bfs": Breadth-first search (explore all at same depth first)
   * - "dfs": Depth-first search (explore deep paths first)
   * - "best-first": Always expand highest-scoring node
   * Default: "best-first"
   */
  strategy?: SearchStrategy;

  /**
   * Prune paths with score below this threshold (0.0-1.0).
   * Lower values prune more aggressively.
   * Default: 0.3
   */
  pruneThreshold?: number;
}

/**
 * Tree-of-Thought reasoning technique.
 *
 * Explores multiple reasoning paths in a tree structure, evaluates each path,
 * and selects the best solution using configurable search strategies.
 *
 * This technique is particularly effective for:
 * - Creative problem-solving requiring exploration
 * - Planning and strategy tasks with multiple approaches
 * - Problems where single path may lead to dead ends
 * - Tasks benefiting from considering alternatives
 *
 * @example
 * ```typescript
 * const tot = new TreeOfThought(myAgent, {
 *   branchingFactor: 3,
 *   maxDepth: 4,
 *   evaluator: myScoringFn,
 *   strategy: 'best-first',
 * });
 * const response = await tot.process(createMessage('user', 'Plan a trip'));
 * console.log(`Best path score: ${response.metadata?.best_score}`);
 * ```
 */
export class TreeOfThought implements Agent {
  private agent: Agent;
  private config: Required<TreeOfThoughtConfig>;

  /**
   * Create a Tree-of-Thought reasoning agent.
   *
   * @param agent Base agent to wrap with ToT reasoning
   * @param config Optional configuration
   */
  constructor(agent: Agent, config: TreeOfThoughtConfig = {}) {
    this.agent = agent;
    this.config = {
      branchingFactor: config.branchingFactor ?? 3,
      maxDepth: config.maxDepth ?? 5,
      evaluator: config.evaluator ?? this.defaultEvaluator.bind(this),
      strategy: config.strategy ?? 'best-first',
      pruneThreshold: config.pruneThreshold ?? 0.3,
    };
  }

  /**
   * Agent identifier.
   */
  get name(): string {
    return 'tree_of_thought';
  }

  /**
   * Agent capabilities.
   */
  get capabilities(): string[] {
    return [
      'reasoning',
      'tree_search',
      'multi_path_exploration',
      'backtracking',
      'tree_of_thought',
      'planning',
    ];
  }

  /**
   * Default evaluator using simple heuristics.
   *
   * Scores based on text length (more detailed = better) with
   * a cap to avoid favoring extremely verbose reasoning.
   *
   * @param text Reasoning text to evaluate
   * @returns Score between 0.0 and 1.0
   */
  private defaultEvaluator(text: string): number {
    // Penalize very short responses
    if (text.length < 50) {
      return 0.2;
    }

    // Favor moderate length (100-500 chars optimal)
    const lengthScore = Math.min(text.length / 500, 1.0);

    // Bonus for structured reasoning (numbered steps)
    const hasStructure = ['1.', '2.', '-', '•'].some((marker) => text.includes(marker));
    const structureBonus = hasStructure ? 0.1 : 0.0;

    return Math.min(lengthScore + structureBonus, 1.0);
  }

  /**
   * Generate N alternative reasoning branches in parallel.
   *
   * @param prompt Prompt to generate from
   * @param n Number of branches to generate
   * @returns Array of generated reasoning texts
   */
  private async generateBranches(prompt: string, n: number): Promise<string[]> {
    // Generate N branches in parallel for speed
    const branchPromises = Array.from({ length: n }, (_, i) => {
      // Add variation to prompt to encourage diversity
      const variedPrompt = `${prompt}\n\nAlternative approach #${i + 1}:`;

      return this.agent
        .process({
          role: 'user',
          content: variedPrompt,
          metadata: {},
        })
        .then((response) => String(response.content));
    });

    return Promise.all(branchPromises);
  }

  /**
   * Expand a node by generating child branches.
   *
   * @param tree Reasoning tree
   * @param nodeId Node to expand
   * @param query Original query for context
   * @returns Array of new child node IDs
   */
  private async expandNode(
    tree: ReasoningTree,
    nodeId: number,
    query: string,
  ): Promise<number[]> {
    const node = tree.getNode(nodeId);
    if (!node) {
      return [];
    }

    // Build prompt with path so far
    const pathText = tree.getPathText(nodeId);
    const prompt = `Original question: ${query}\n\nReasoning so far:\n${pathText}\n\nContinue reasoning:`;

    // Generate branches
    const branches = await this.generateBranches(prompt, this.config.branchingFactor);

    // Add branches as children
    const childIds: number[] = [];
    for (const branchText of branches) {
      // Score the branch
      const fullPath = `${pathText}\n${branchText}`;
      const score = this.config.evaluator(fullPath);

      // Add child node
      const childId = tree.addChild(nodeId, branchText, score);

      // Prune if score too low
      if (score < this.config.pruneThreshold) {
        tree.pruneNode(childId);
      } else {
        childIds.push(childId);
      }
    }

    // Mark node as evaluated
    node.state = NodeState.Evaluated;

    return childIds;
  }

  /**
   * Breadth-first search through reasoning tree.
   *
   * @param tree Reasoning tree
   * @param rootId Root node ID
   * @param query Original query
   */
  private async searchBFS(tree: ReasoningTree, rootId: number, query: string): Promise<void> {
    const queue: number[] = [rootId];

    while (queue.length > 0) {
      const nodeId = queue.shift()!;
      const node = tree.getNode(nodeId);

      if (!node || node.state === NodeState.Pruned) {
        continue;
      }

      // Stop if max depth reached
      if (node.depth >= this.config.maxDepth) {
        node.state = NodeState.Terminal;
        continue;
      }

      // Expand node
      const childIds = await this.expandNode(tree, nodeId, query);
      queue.push(...childIds);
    }
  }

  /**
   * Depth-first search through reasoning tree.
   *
   * @param tree Reasoning tree
   * @param rootId Root node ID
   * @param query Original query
   */
  private async searchDFS(tree: ReasoningTree, rootId: number, query: string): Promise<void> {
    const stack: number[] = [rootId];

    while (stack.length > 0) {
      const nodeId = stack.pop()!;
      const node = tree.getNode(nodeId);

      if (!node || node.state === NodeState.Pruned) {
        continue;
      }

      // Stop if max depth reached
      if (node.depth >= this.config.maxDepth) {
        node.state = NodeState.Terminal;
        continue;
      }

      // Expand node
      const childIds = await this.expandNode(tree, nodeId, query);
      // Reverse to maintain left-to-right order
      stack.push(...childIds.reverse());
    }
  }

  /**
   * Best-first search - always expand highest scoring node.
   *
   * @param tree Reasoning tree
   * @param rootId Root node ID
   * @param query Original query
   */
  private async searchBestFirst(
    tree: ReasoningTree,
    rootId: number,
    query: string,
  ): Promise<void> {
    // Priority queue (list of node IDs, sorted by score)
    const openNodes: number[] = [rootId];

    while (openNodes.length > 0) {
      // Sort by score (highest first)
      openNodes.sort((a, b) => {
        const nodeA = tree.getNode(a);
        const nodeB = tree.getNode(b);
        const scoreA = nodeA ? nodeA.score : 0;
        const scoreB = nodeB ? nodeB.score : 0;
        return scoreB - scoreA;
      });

      // Pop highest scoring node
      const nodeId = openNodes.shift()!;
      const node = tree.getNode(nodeId);

      if (!node || node.state === NodeState.Pruned) {
        continue;
      }

      // Stop if max depth reached
      if (node.depth >= this.config.maxDepth) {
        node.state = NodeState.Terminal;
        continue;
      }

      // Expand node
      const childIds = await this.expandNode(tree, nodeId, query);
      openNodes.push(...childIds);
    }
  }

  /**
   * Process message with Tree-of-Thought reasoning.
   *
   * Builds a reasoning tree, explores multiple paths using the configured
   * search strategy, and returns the best complete reasoning path.
   *
   * @param message Input message with query content
   * @returns Message with best reasoning path and metadata
   *
   * Metadata includes:
   * - reasoning_tree_stats: Tree statistics
   * - reasoning_path: Array of steps in best path
   * - num_steps: Number of steps in best path
   * - best_score: Score of best path
   * - technique: Always "tree_of_thought"
   * - search_strategy: Strategy used
   *
   * @throws Error if invalid search strategy specified
   *
   * @example
   * ```typescript
   * const response = await tot.process(createMessage('user', 'Plan a trip'));
   * console.log(`Explored ${response.metadata?.reasoning_tree_stats?.total_nodes} paths`);
   * console.log(`Best path score: ${response.metadata?.best_score}`);
   * ```
   */
  async process(message: Message): Promise<Message> {
    const query = String(message.content);

    // Create reasoning tree
    const tree = new ReasoningTree();
    const rootId = tree.createRoot(query);

    // Run search strategy
    if (this.config.strategy === 'bfs') {
      await this.searchBFS(tree, rootId, query);
    } else if (this.config.strategy === 'dfs') {
      await this.searchDFS(tree, rootId, query);
    } else if (this.config.strategy === 'best-first') {
      await this.searchBestFirst(tree, rootId, query);
    } else {
      throw new Error(`Invalid strategy: ${this.config.strategy}`);
    }

    // Get best leaf node
    const bestLeaf = tree.getBestLeaf();

    if (!bestLeaf) {
      // No valid path found
      return {
        role: 'assistant',
        content: 'Unable to find valid reasoning path.',
        metadata: {
          technique: 'tree_of_thought',
          search_strategy: this.config.strategy,
          reasoning_tree_stats: tree.getStatistics(),
          error: 'no_valid_path',
        },
      };
    }

    // Get best path
    const bestPath = tree.getPath(bestLeaf.id);
    const pathText = tree.getPathText(bestLeaf.id);

    return {
      role: 'assistant',
      content: pathText,
      metadata: {
        technique: 'tree_of_thought',
        search_strategy: this.config.strategy,
        reasoning_tree_stats: tree.getStatistics(),
        reasoning_path: bestPath.map((node) => node.content),
        num_steps: bestPath.length,
        best_score: bestLeaf.score,
      },
    };
  }
}

/**
 * Factory function to create a Tree-of-Thought agent.
 *
 * @param agent Base agent to wrap
 * @param config Optional configuration
 * @returns Configured TreeOfThought agent
 *
 * @example
 * ```typescript
 * const tot = createTreeOfThought(myAgent, {
 *   branchingFactor: 5,
 *   strategy: 'best-first',
 * });
 * ```
 */
export function createTreeOfThought(
  agent: Agent,
  config?: TreeOfThoughtConfig,
): TreeOfThought {
  return new TreeOfThought(agent, config);
}
