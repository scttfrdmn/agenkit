/**
 * Least-to-Most Prompting Technique
 *
 * Breaks complex problems into simpler subproblems, solves them sequentially
 * from simplest to most complex, using solutions to build up to the final answer.
 *
 * This technique is particularly effective for compositional reasoning where
 * complex problems can be decomposed into manageable pieces.
 *
 * References:
 *   - Paper: https://arxiv.org/abs/2205.10625 (Zhou et al., 2022)
 *   - "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models"
 *   - Effective for math, symbolic manipulation, compositional generalization
 *
 * @example
 * Basic usage:
 * ```typescript
 * import { LeastToMost } from '@agenkit/techniques/reasoning';
 * import { createMessage } from '@agenkit';
 *
 * const ltm = new LeastToMost(myAgent, {
 *   maxSubproblems: 5,
 *   composeSolutions: true,
 * });
 *
 * const response = await ltm.process(createMessage('user',
 *   'Calculate the total cost of 3 apples at $2 each and 2 oranges at $3 each'
 * ));
 *
 * // Access subproblems and solutions
 * console.log(response.metadata?.subproblems);
 * console.log(response.metadata?.subproblem_solutions);
 * ```
 *
 * @example
 * Custom decomposer:
 * ```typescript
 * const ltm = new LeastToMost(myAgent, {
 *   decomposer: (problem) => [
 *     'Step 1: Break down the problem',
 *     'Step 2: Solve each part',
 *     'Step 3: Combine results',
 *   ],
 * });
 * ```
 */

import type { Agent, Message } from '../../core/interfaces';
import type { CallOptions } from '../../core/call-options';
import { processWithOptions } from '../../core/call-options';

/**
 * Represents a subproblem in the decomposition.
 */
export interface Subproblem {
  /** The content/description of the subproblem */
  content: string;

  /** Difficulty level (0 = easiest) */
  difficulty: number;

  /** Indices of subproblems this depends on */
  dependencies: number[];
}

/**
 * Custom function to decompose a problem into ordered subproblem strings
 * (simplest to hardest). May be sync or async.
 */
export type DecomposerFunction = (
  problem: string,
) => string[] | Promise<string[]>;

/**
 * Configuration options for Least-to-Most agent.
 */
export interface LeastToMostConfig {
  /**
   * Custom function to decompose problems into subproblems.
   * If not provided, uses LLM to decompose.
   *
   * @param problem The problem to decompose
   * @returns Array of subproblem strings (ordered from simplest to hardest)
   */
  decomposer?: DecomposerFunction;

  /**
   * Maximum number of subproblems to generate.
   * Limits decomposition depth.
   * Default: 5
   */
  maxSubproblems?: number;

  /**
   * Whether to use previous subproblem solutions as context
   * when solving harder problems.
   * Default: true
   */
  composeSolutions?: boolean;
}

/**
 * Least-to-Most prompting technique.
 *
 * Decomposes complex problems into simpler subproblems, solves them
 * sequentially from easiest to hardest, using previous solutions as
 * context for solving harder problems.
 *
 * This technique is particularly effective for:
 * - Compositional reasoning tasks
 * - Multi-step math problems
 * - Problems that naturally decompose into stages
 * - Tasks where simpler subtasks inform harder ones
 *
 * @example
 * ```typescript
 * const ltm = new LeastToMost(myAgent, {
 *   maxSubproblems: 5,
 *   composeSolutions: true,
 * });
 *
 * const response = await ltm.process(
 *   createMessage('user', 'Calculate 3*4 + 2*5')
 * );
 *
 * console.log(`Solved in ${response.metadata?.num_subproblems} steps`);
 * ```
 */
export class LeastToMost implements Agent {
  private agent: Agent;
  private config: Required<LeastToMostConfig>;

  /**
   * Create a Least-to-Most reasoning agent.
   *
   * @param agent Base agent to use for LLM calls
   * @param config Optional configuration
   */
  constructor(agent: Agent, config: LeastToMostConfig = {}) {
    this.agent = agent;
    this.config = {
      decomposer: config.decomposer,
      maxSubproblems: config.maxSubproblems ?? 5,
      composeSolutions: config.composeSolutions ?? true,
    } as Required<LeastToMostConfig>;
  }

  /**
   * Agent identifier.
   */
  get name(): string {
    return 'least_to_most';
  }

  /**
   * Agent capabilities.
   */
  get capabilities(): string[] {
    return [
      'reasoning',
      'decomposition',
      'compositional_reasoning',
      'least_to_most',
      'sequential_solving',
    ];
  }

  /**
   * Decompose problem into subproblems.
   *
   * Uses custom decomposer if provided, otherwise uses LLM.
   *
   * @param problem Original problem to decompose
   * @param options Per-call inference options, forwarded to the wrapped agent
   * @returns List of Subproblem objects ordered from easiest to hardest
   */
  private async decompose(problem: string, options?: CallOptions): Promise<Subproblem[]> {
    if (this.config.decomposer) {
      // Use custom decomposer
      const subproblemTexts = await Promise.resolve(this.config.decomposer(problem));
      return subproblemTexts.slice(0, this.config.maxSubproblems).map((text, i) => ({
        content: text,
        difficulty: i,
        dependencies: [],
      }));
    }

    // Use LLM to decompose
    const decompositionPrompt = `Break down this problem into simpler subproblems, ordered from easiest to hardest.
List each subproblem on a separate line, numbered 1, 2, 3, etc.

Problem: ${problem}

Subproblems (from simplest to most complex):`;

    const response = await processWithOptions(
      this.agent,
      {
        role: 'user',
        content: decompositionPrompt,
        metadata: {},
      },
      options,
    );

    // Parse subproblems from response
    const subproblems: Subproblem[] = [];
    const responseText = String(response.content);
    const lines = responseText.trim().split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      // Only match lines that START with a number followed by . or )
      if (!/^\d+[.)]/.test(line)) continue;

      // Remove numbering (1., 1), etc.)
      const cleaned = line.replace(/^\d+[.)]\s*/, '');

      if (cleaned && subproblems.length < this.config.maxSubproblems) {
        subproblems.push({
          content: cleaned,
          difficulty: i,
          dependencies: [],
        });
      }
    }

    // If decomposition failed or no valid numbered steps found, treat as atomic problem
    if (subproblems.length === 0) {
      subproblems.push({
        content: problem,
        difficulty: 0,
        dependencies: [],
      });
    }

    return subproblems;
  }

  /**
   * Solve one subproblem, optionally using previous solutions as context.
   *
   * @param subproblem Subproblem to solve
   * @param previousSolutions Solutions to previous (easier) subproblems
   * @param options Per-call inference options, forwarded to the wrapped agent
   * @returns Solution to this subproblem
   */
  private async solveSubproblem(
    subproblem: Subproblem,
    previousSolutions: string[],
    options?: CallOptions,
  ): Promise<string> {
    let prompt: string;

    if (this.config.composeSolutions && previousSolutions.length > 0) {
      // Include previous solutions as context
      const context = previousSolutions
        .map((sol, i) => `Previous solution ${i + 1}: ${sol}`)
        .join('\n');

      prompt = `Given these previous solutions to simpler subproblems:

${context}

Now solve this subproblem:
${subproblem.content}

Solution:`;
    } else {
      // Solve without context
      prompt = `Solve this subproblem:

${subproblem.content}

Solution:`;
    }

    const response = await processWithOptions(
      this.agent,
      {
        role: 'user',
        content: prompt,
        metadata: {},
      },
      options,
    );

    return String(response.content).trim();
  }

  /**
   * Process message with Least-to-Most prompting.
   *
   * Decomposes the problem, solves subproblems sequentially from easiest
   * to hardest, and composes the final solution.
   *
   * @param message Input message with problem
   * @returns Message with final solution and metadata
   *
   * Metadata includes:
   * - subproblems: List of subproblem texts
   * - subproblem_solutions: List of solutions to each subproblem
   * - num_subproblems: Number of subproblems generated
   * - compose_solutions: Whether solutions were composed
   * - technique: Always "least_to_most"
   *
   * @example
   * ```typescript
   * const response = await ltm.process(
   *   createMessage('user', 'Calculate 3*4 + 2*5')
   * );
   * console.log(response.metadata?.subproblems);
   * console.log(response.metadata?.subproblem_solutions);
   * ```
   */
  async process(message: Message): Promise<Message> {
    return this.processWith(message, {});
  }

  /**
   * Process message with Least-to-Most prompting and per-call options.
   *
   * Implements the optional `processWith` capability. The options reach both
   * phases — decomposition and every subproblem solve — because a temperature
   * that reaches only some of the LLM calls in a multi-phase technique is not the
   * temperature the caller asked for (#801).
   *
   * @param message Input message with problem
   * @param options Per-call inference options
   * @returns Message with final solution and metadata
   */
  async processWith(message: Message, options: CallOptions): Promise<Message> {
    const problem = String(message.content);

    // Step 1: Decompose problem
    const subproblems = await this.decompose(problem, options);

    // Step 2: Solve subproblems sequentially
    const solutions: string[] = [];
    for (const subproblem of subproblems) {
      const solution = await this.solveSubproblem(subproblem, solutions, options);
      solutions.push(solution);
    }

    // Step 3: Final solution is the last one (hardest problem)
    const finalSolution = solutions.length > 0 ? solutions[solutions.length - 1] : '';

    return {
      role: 'assistant',
      content: finalSolution,
      metadata: {
        technique: 'least_to_most',
        num_subproblems: subproblems.length,
        subproblems: subproblems.map((sp) => sp.content),
        subproblem_solutions: solutions,
        compose_solutions: this.config.composeSolutions,
      },
      timestamp: new Date().toISOString(),
    };
  }
}

/**
 * Factory function to create a Least-to-Most agent.
 *
 * @param agent Base agent to wrap
 * @param config Optional configuration
 * @returns Configured LeastToMost agent
 *
 * @example
 * ```typescript
 * const ltm = createLeastToMost(myAgent, {
 *   maxSubproblems: 3,
 *   composeSolutions: true,
 * });
 * ```
 */
export function createLeastToMost(agent: Agent, config?: LeastToMostConfig): LeastToMost {
  return new LeastToMost(agent, config);
}
