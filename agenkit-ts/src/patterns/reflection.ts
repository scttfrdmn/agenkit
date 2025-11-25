/**
 * Reflection Pattern - Self-Critique and Iterative Refinement
 *
 * The Reflection pattern enables agents to review and improve their own outputs
 * through an iterative cycle of generation, critique, and refinement.
 *
 * Key Concepts:
 * - Generator: Agent that produces initial output
 * - Critic: Agent that evaluates output quality and provides feedback
 * - Iteration: Repeated refinement based on critique
 * - Quality Threshold: Stop when output quality is sufficient
 * - Improvement Threshold: Stop when incremental improvements become minimal
 *
 * Use Cases:
 * - Code generation with self-review
 * - Content creation with quality improvement
 * - Multi-draft writing and editing
 * - Error detection and correction
 * - Iterative problem solving
 *
 * Example:
 * ```typescript
 * const agent = new ReflectionAgent({
 *   generator: myGeneratorAgent,
 *   critic: myCriticAgent,
 *   maxIterations: 5,
 *   qualityThreshold: 0.9
 * });
 *
 * const result = await agent.process({
 *   role: 'user',
 *   content: 'Write a function to check if a number is prime'
 * });
 *
 * console.log(result.metadata?.reflectionIterations); // 3
 * console.log(result.metadata?.finalQualityScore);    // 0.95
 * console.log(result.metadata?.stopReason);           // "quality_threshold_met"
 * ```
 *
 * References:
 * - Reflexion: Language Agents with Verbal Reinforcement Learning (https://arxiv.org/abs/2303.11366)
 * - Self-Refine: Iterative Refinement with Self-Feedback (https://arxiv.org/abs/2303.17651)
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/** Reason why reflection loop stopped */
export enum StopReason {
  QUALITY_THRESHOLD_MET = 'quality_threshold_met',
  MINIMAL_IMPROVEMENT = 'minimal_improvement',
  MAX_ITERATIONS = 'max_iterations',
  PERFECT_SCORE = 'perfect_score',
}

/** Format expected from critic agent */
export enum CritiqueFormat {
  /** JSON: {"score": 0.8, "feedback": "..."} */
  STRUCTURED = 'structured',
  /** Free text with score extracted */
  FREE_FORM = 'free_form',
}

/**
 * Single iteration in the reflection loop.
 */
export interface ReflectionStep {
  /** Iteration number (1-indexed) */
  iteration: number;
  /** Generated output for this iteration */
  output: string;
  /** Feedback from critic */
  critique: string;
  /** Quality score (0.0-1.0) */
  qualityScore: number;
  /** Improvement over previous iteration */
  improvement: number;
  /** When this iteration occurred */
  timestamp: string;
}

/**
 * Configuration for ReflectionAgent.
 */
export interface ReflectionConfig {
  /** Agent that produces/refines output */
  generator: Agent;
  /** Agent that evaluates output (returns score + feedback) */
  critic: Agent;
  /** Maximum refinement iterations (default: 5) */
  maxIterations?: number;
  /** Stop when score exceeds this (default: 0.9) */
  qualityThreshold?: number;
  /** Min improvement to continue (default: 0.05) */
  improvementThreshold?: number;
  /** Expected format from critic (default: structured) */
  critiqueFormat?: CritiqueFormat;
  /** Include full reflection history in output (default: false) */
  verbose?: boolean;
}

/**
 * Agent that iteratively refines output through self-critique.
 *
 * The reflection loop:
 * 1. Generator creates initial output
 * 2. Critic evaluates output, provides score and feedback
 * 3. Generator refines output based on feedback
 * 4. Repeat until quality threshold, minimal improvement, or max iterations
 *
 * Performance Characteristics:
 * - Latency: N × (generator + critic), where N = number of iterations
 * - Quality: Generally improves with iterations
 * - Cost: N × (generator cost + critic cost)
 * - Best for: Tasks where quality improvement justifies additional cost
 */
export class ReflectionAgent implements Agent {
  readonly name = 'ReflectionAgent';

  private generator: Agent;
  private critic: Agent;
  private maxIterations: number;
  private qualityThreshold: number;
  private improvementThreshold: number;
  private critiqueFormat: CritiqueFormat;
  private verbose: boolean;
  private history: ReflectionStep[] = [];

  constructor(config: ReflectionConfig) {
    // Validate configuration
    if (!config.generator) {
      throw new Error('generator is required');
    }
    if (!config.critic) {
      throw new Error('critic is required');
    }

    // Set defaults
    this.generator = config.generator;
    this.critic = config.critic;
    this.maxIterations = config.maxIterations ?? 5;
    this.qualityThreshold = config.qualityThreshold ?? 0.9;
    this.improvementThreshold = config.improvementThreshold ?? 0.05;
    this.critiqueFormat = config.critiqueFormat ?? CritiqueFormat.STRUCTURED;
    this.verbose = config.verbose ?? false;

    // Validate ranges
    if (this.maxIterations < 1) {
      throw new Error('maxIterations must be at least 1');
    }
    if (this.qualityThreshold < 0.0 || this.qualityThreshold > 1.0) {
      throw new Error('qualityThreshold must be between 0.0 and 1.0');
    }
    if (this.improvementThreshold < 0.0 || this.improvementThreshold > 1.0) {
      throw new Error('improvementThreshold must be between 0.0 and 1.0');
    }
  }

  get capabilities(): string[] {
    const caps = new Set<string>();
    if (this.generator.capabilities) {
      this.generator.capabilities.forEach(c => caps.add(c));
    }
    if (this.critic.capabilities) {
      this.critic.capabilities.forEach(c => caps.add(c));
    }
    caps.add('reflection');
    caps.add('self-critique');
    return Array.from(caps);
  }

  /**
   * Execute reflection loop.
   *
   * @param message User's request/task
   * @returns Message containing refined output with reflection metadata
   *
   * Metadata Structure:
   * - reflectionIterations: Number of iterations performed
   * - finalQualityScore: Final quality score achieved
   * - stopReason: Why the loop stopped
   * - reflectionHistory: List of ReflectionStep (if verbose=true)
   * - initialQualityScore: Quality score of first output
   * - totalImprovement: Improvement from first to final
   */
  async process(message: Message): Promise<Message> {
    this.history = []; // Reset for new task

    // Initial generation
    let output = await this.generator.process(message);
    let previousScore = 0.0;

    for (let iteration = 1; iteration <= this.maxIterations; iteration++) {
      // Critique current output
      const critiqueMessage = this.buildCritiquePrompt(
        String(message.content),
        String(output.content)
      );
      const critiqueResponse = await this.critic.process(critiqueMessage);

      // Parse critique (score + feedback)
      const { score, feedback } = this.parseCritique(String(critiqueResponse.content));
      const improvement = score - previousScore;

      // Record step
      const step: ReflectionStep = {
        iteration,
        output: String(output.content),
        critique: feedback,
        qualityScore: score,
        improvement,
        timestamp: new Date().toISOString(),
      };
      this.history.push(step);

      // Check stopping conditions
      const { stopReason, shouldStop } = this.checkStopConditions(score, improvement);

      if (shouldStop) {
        return this.formatResult(output, stopReason);
      }

      // Refine based on critique
      const refineMessage = this.buildRefinementPrompt(
        String(message.content),
        String(output.content),
        feedback
      );
      output = await this.generator.process(refineMessage);
      previousScore = score;
    }

    // Max iterations reached
    return this.formatResult(output, StopReason.MAX_ITERATIONS);
  }

  /**
   * Build prompt for critic to evaluate output.
   */
  private buildCritiquePrompt(originalQuery: string, currentOutput: string): Message {
    let prompt: string;

    if (this.critiqueFormat === CritiqueFormat.STRUCTURED) {
      prompt = `Evaluate the following output on a scale of 0.0 to 1.0.

Original Request:
${originalQuery}

Output to Evaluate:
${currentOutput}

Respond with JSON in this format:
{
  "score": 0.85,
  "feedback": "Your detailed feedback here..."
}`;
    } else {
      prompt = `Evaluate the following output on a scale of 0.0 to 1.0.
Include your score and detailed feedback.

Original Request:
${originalQuery}

Output to Evaluate:
${currentOutput}`;
    }

    return createMessage('user', prompt);
  }

  /**
   * Build prompt for generator to refine output.
   */
  private buildRefinementPrompt(
    originalQuery: string,
    currentOutput: string,
    critique: string
  ): Message {
    const prompt = `Original Request:
${originalQuery}

Current Output:
${currentOutput}

Feedback from Critic:
${critique}

Please refine the output based on this feedback. Produce an improved version that addresses the critique.`;

    return createMessage('user', prompt);
  }

  /**
   * Parse critique response to extract score and feedback.
   */
  private parseCritique(content: string): { score: number; feedback: string } {
    if (this.critiqueFormat === CritiqueFormat.STRUCTURED) {
      try {
        const parsed = JSON.parse(content);
        const score = Math.max(0.0, Math.min(1.0, parsed.score || 0.0));
        const feedback = parsed.feedback || content;
        return { score, feedback };
      } catch {
        // Fallback to free-form parsing
        return this.parseFreeFormCritique(content);
      }
    } else {
      return this.parseFreeFormCritique(content);
    }
  }

  /**
   * Parse free-form critique to extract score.
   */
  private parseFreeFormCritique(content: string): { score: number; feedback: string } {
    // Look for patterns like "Score: 0.85" or "8.5/10" or "85%"
    const scorePatterns = [
      /score[:\s]+([0-9.]+)/i,
      /([0-9.]+)\s*\/\s*10/,
      /([0-9.]+)%/,
      /rating[:\s]+([0-9.]+)/i,
    ];

    for (const pattern of scorePatterns) {
      const match = content.match(pattern);
      if (match) {
        let score = parseFloat(match[1]);

        // Normalize to 0.0-1.0
        if (score > 10.0) {
          score = score / 100.0; // Percentage
        } else if (score > 1.0) {
          score = score / 10.0; // Out of 10
        }

        return {
          score: Math.max(0.0, Math.min(1.0, score)),
          feedback: content,
        };
      }
    }

    // No score found, return 0.5 as default
    return { score: 0.5, feedback: content };
  }

  /**
   * Check if reflection loop should stop.
   */
  private checkStopConditions(
    score: number,
    improvement: number
  ): { stopReason: StopReason; shouldStop: boolean } {
    // Perfect score
    if (score >= 1.0) {
      return { stopReason: StopReason.PERFECT_SCORE, shouldStop: true };
    }

    // Quality threshold met
    if (score >= this.qualityThreshold) {
      return { stopReason: StopReason.QUALITY_THRESHOLD_MET, shouldStop: true };
    }

    // Minimal improvement (only check after first iteration)
    if (this.history.length > 1 && improvement < this.improvementThreshold) {
      return { stopReason: StopReason.MINIMAL_IMPROVEMENT, shouldStop: true };
    }

    return { stopReason: StopReason.MAX_ITERATIONS, shouldStop: false };
  }

  /**
   * Format final result with metadata.
   */
  private formatResult(output: Message, stopReason: StopReason): Message {
    const metadata: Record<string, unknown> = {
      reflectionIterations: this.history.length,
      stopReason,
    };

    if (this.history.length > 0) {
      const lastStep = this.history[this.history.length - 1];
      const firstStep = this.history[0];

      metadata.finalQualityScore = lastStep.qualityScore;
      metadata.initialQualityScore = firstStep.qualityScore;
      metadata.totalImprovement = lastStep.qualityScore - firstStep.qualityScore;

      if (this.verbose) {
        metadata.reflectionHistory = this.history;
      }
    }

    return {
      ...output,
      metadata: {
        ...output.metadata,
        ...metadata,
      },
    };
  }
}
