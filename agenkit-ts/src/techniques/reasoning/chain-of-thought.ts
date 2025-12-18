/**
 * Chain-of-Thought (CoT) Reasoning Technique
 *
 * Encourages step-by-step reasoning through structured prompting.
 *
 * This technique applies structured prompting to encourage LLMs to show their
 * reasoning process explicitly, leading to more accurate and explainable results.
 *
 * References:
 *   - Paper: https://arxiv.org/abs/2201.11903 (Wei et al., 2022)
 *   - "Let's think step by step" prompting
 *   - Critical for modern reasoning models (o3, Opus 4)
 *
 * @example
 * Basic usage:
 * ```typescript
 * import { ChainOfThought } from '@agenkit/techniques/reasoning';
 * import { createMessage } from '@agenkit';
 *
 * const cot = new ChainOfThought(myAgent);
 * const response = await cot.process(createMessage('user', 'What is 15 * 24?'));
 * console.log(response.metadata?.reasoning_steps);
 * ```
 *
 * @example
 * Custom prompt template:
 * ```typescript
 * const cot = new ChainOfThought(myAgent, {
 *   promptTemplate: 'Solve step by step:\n{query}',
 *   maxSteps: 5,
 * });
 * ```
 */

import type { Agent, Message } from '../../core/interfaces';

/**
 * Configuration options for Chain-of-Thought agent.
 */
export interface ChainOfThoughtConfig {
  /**
   * Template string with {query} placeholder for formatting the CoT prompt.
   * Default: "Let's think step by step:\n{query}"
   */
  promptTemplate?: string;

  /**
   * Whether to extract and track individual reasoning steps in the response metadata.
   * Default: true
   */
  parseSteps?: boolean;

  /**
   * String delimiter for splitting steps when using simple delimiter-based parsing.
   * Default: "\n"
   */
  stepDelimiter?: string;

  /**
   * Maximum number of reasoning steps to extract. Undefined means unlimited.
   * Useful for limiting verbosity.
   */
  maxSteps?: number;
}

/**
 * Chain-of-Thought reasoning technique.
 *
 * Applies structured prompting to encourage step-by-step reasoning,
 * optionally parsing and tracking individual reasoning steps.
 *
 * This technique is particularly effective for:
 * - Mathematical reasoning
 * - Logical deduction
 * - Complex problem-solving
 * - Multi-step tasks requiring explanation
 *
 * @example
 * ```typescript
 * const cot = new ChainOfThought(myAgent, {
 *   promptTemplate: 'Reason carefully:\n{query}',
 *   maxSteps: 5,
 * });
 * const response = await cot.process(createMessage('user', 'Calculate 15*24'));
 * console.log(`Steps: ${response.metadata?.reasoning_steps?.length}`);
 * ```
 */
export class ChainOfThought implements Agent {
  private agent: Agent;
  private config: Required<ChainOfThoughtConfig>;

  /**
   * Create a Chain-of-Thought reasoning agent.
   *
   * @param agent Base agent to wrap with CoT prompting
   * @param config Optional configuration
   */
  constructor(agent: Agent, config: ChainOfThoughtConfig = {}) {
    this.agent = agent;
    this.config = {
      promptTemplate: config.promptTemplate ?? "Let's think step by step:\n{query}",
      parseSteps: config.parseSteps ?? true,
      stepDelimiter: config.stepDelimiter ?? '\n',
      maxSteps: config.maxSteps ?? undefined,
    } as Required<ChainOfThoughtConfig>;
  }

  /**
   * Agent identifier.
   */
  get name(): string {
    return 'chain_of_thought';
  }

  /**
   * Agent capabilities.
   */
  get capabilities(): string[] {
    return ['reasoning', 'step_by_step', 'chain_of_thought', 'explainable_ai'];
  }

  /**
   * Process message with Chain-of-Thought reasoning.
   *
   * Applies the CoT prompt template to the input message, generates a
   * response using the wrapped agent, and optionally parses reasoning steps.
   *
   * @param message Input message with query content
   * @returns Message with response content and metadata
   *
   * Metadata includes (if parseSteps=true):
   * - reasoning_steps: List of extracted reasoning steps
   * - num_steps: Number of steps found
   * - technique: Always "chain_of_thought"
   *
   * @throws Error if prompt template doesn't contain {query} placeholder
   *
   * @example
   * ```typescript
   * const response = await cot.process(createMessage('user', 'Calculate 15*24'));
   * console.log(`Steps: ${response.metadata?.num_steps}`);
   * ```
   */
  async process(message: Message): Promise<Message> {
    // Apply CoT prompting
    const content = String(message.content);
    if (!this.config.promptTemplate.includes('{query}')) {
      throw new Error('Prompt template must contain {query} placeholder');
    }
    const cotPrompt = this.config.promptTemplate.replace('{query}', content);

    // Get response from agent
    const response = await this.agent.process({
      role: 'user',
      content: cotPrompt,
      metadata: {},
    });

    // Parse steps if requested
    if (this.config.parseSteps) {
      const responseText = String(response.content);
      const steps = this.parseSteps(responseText);

      return {
        role: 'assistant',
        content: response.content,
        metadata: {
          ...(response.metadata || {}),
          reasoning_steps: steps,
          num_steps: steps.length,
          technique: 'chain_of_thought',
        },
        timestamp: response.timestamp,
      };
    }

    return {
      role: 'assistant',
      content: response.content,
      metadata: {
        ...(response.metadata || {}),
        technique: 'chain_of_thought',
      },
      timestamp: response.timestamp,
    };
  }

  /**
   * Parse reasoning steps from response text.
   *
   * Supports multiple common step formats:
   * - Numbered steps (1. Step one, 2. Step two)
   * - Bullet points (- Step, * Step, • Step)
   * - Newline-separated thoughts (fallback)
   *
   * The parser tries formats in order: numbered, bullets, delimiter-based.
   *
   * @param text Response text to parse
   * @returns List of reasoning step strings, stripped of formatting
   *
   * @example
   * ```typescript
   * const steps = cot.parseSteps('1. First\n2. Second\n3. Third');
   * console.log(steps.length); // 3
   * ```
   */
  private parseSteps(text: string): string[] {
    // Try numbered steps first (1. 2. 3. or 1) 2) 3))
    const numberedRegex = /^\d+[.)]\s*(.+)$/gm;
    const numberedMatches = Array.from(text.matchAll(numberedRegex));

    if (numberedMatches.length >= 2) {
      const steps = numberedMatches.map((match) => match[1].trim());
      return this.limitSteps(steps);
    }

    // Try bullet points (-, *, •)
    const bulletRegex = /^[•\-*]\s*(.+)$/gm;
    const bulletMatches = Array.from(text.matchAll(bulletRegex));

    if (bulletMatches.length >= 2) {
      const steps = bulletMatches.map((match) => match[1].trim());
      return this.limitSteps(steps);
    }

    // Fall back to delimiter-based splitting
    const steps = text
      .split(this.config.stepDelimiter)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    return this.limitSteps(steps);
  }

  /**
   * Apply max_steps limit if configured.
   *
   * @param steps Array of steps to limit
   * @returns Limited array of steps
   */
  private limitSteps(steps: string[]): string[] {
    if (this.config.maxSteps !== undefined && steps.length > this.config.maxSteps) {
      return steps.slice(0, this.config.maxSteps);
    }
    return steps;
  }
}

/**
 * Factory function to create a Chain-of-Thought agent.
 *
 * @param agent Base agent to wrap
 * @param config Optional configuration
 * @returns Configured ChainOfThought agent
 *
 * @example
 * ```typescript
 * const cot = createChainOfThought(myAgent, { maxSteps: 5 });
 * ```
 */
export function createChainOfThought(
  agent: Agent,
  config?: ChainOfThoughtConfig,
): ChainOfThought {
  return new ChainOfThought(agent, config);
}
