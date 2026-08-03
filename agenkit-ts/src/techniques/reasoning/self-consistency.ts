/**
 * Self-Consistency Reasoning Technique
 *
 * Self-Consistency improves reliability by generating multiple independent reasoning
 * paths and using voting to select the most consistent answer.
 *
 * Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
 * Wang et al., 2022 - https://arxiv.org/abs/2203.11171
 *
 * Key features:
 * - Parallel sampling for performance
 * - Multiple voting strategies (majority, weighted, first)
 * - Customizable answer extraction
 * - Consistency scoring for confidence measurement
 */

import { Agent, Message, createMessage } from '../../core/interfaces';
import {
  CallOptions,
  mergeCallOptions,
  processWithOptions,
  supportsOptions,
  validateCallOptions,
} from '../../core/call-options';

/**
 * Voting strategy for answer aggregation.
 */
export type VotingStrategy = 'majority' | 'weighted' | 'first';

/**
 * Answer extractor function type.
 */
export type AnswerExtractor = (text: string) => string;

/**
 * Configuration options for Self-Consistency.
 */
export interface SelfConsistencyConfig {
  /** Number of independent samples to generate (default: 5) */
  numSamples?: number;

  /** Voting strategy for answer aggregation (default: 'majority') */
  votingStrategy?: VotingStrategy;

  /**
   * Sampling temperature for diversity, 0-2 (optional).
   *
   * Forwarded per sample to the wrapped agent when that agent implements the
   * optional `processWith` capability. An agent that does not generates its
   * samples at whatever temperature it was configured with, so the diversity this
   * technique depends on may not materialize — `temperatureApplied` reports which
   * case applies. Until v0.88.0 this option was accepted and silently discarded
   * (#801).
   */
  temperature?: number;

  /** Custom answer extraction function (optional) */
  answerExtractor?: AnswerExtractor;
}

/**
 * Default answer extractor that looks for common answer patterns.
 *
 * Patterns recognized:
 * - "Therefore, X" / "Thus, X" / "So, X"
 * - "The answer is X"
 * - "= X" (for math)
 * - "Conclusion: X" / "Result: X"
 * - Last non-empty line (fallback)
 */
function defaultAnswerExtractor(text: string): string {
  // Try explicit answer markers
  const patterns = [
    /(?:therefore|thus|so),?\s+(?:the answer is\s+)?(.+?)(?:\.|$)/i,
    /(?:the answer is|answer:)\s+(.+?)(?:\.|$)/i,
    /=\s*(.+?)(?:\n|$)/,
    /(?:conclusion|result):\s*(.+?)(?:\.|$)/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      return match[1].trim();
    }
  }

  // Fallback: use last non-empty line
  const lines = text.split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (line) {
      return line;
    }
  }

  return text.trim();
}

/**
 * Self-Consistency agent that wraps a base agent.
 *
 * Usage:
 * ```typescript
 * const sc = new SelfConsistencyAgent(baseAgent, {
 *   numSamples: 5,
 *   votingStrategy: 'majority',
 * });
 *
 * const response = await sc.process(message);
 * console.log(`Consensus: ${response.content}`);
 * console.log(`Confidence: ${response.metadata.consistency_score}`);
 * ```
 */
export class SelfConsistencyAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];

  private readonly agent: Agent;
  private readonly numSamples: number;
  private readonly votingStrategy: VotingStrategy;
  private readonly temperature?: number;
  private readonly answerExtractor: AnswerExtractor;

  constructor(agent: Agent, config: SelfConsistencyConfig = {}) {
    this.agent = agent;
    this.name = 'self_consistency';
    this.capabilities = [
      'reasoning',
      'self_consistency',
      'majority_voting',
      'reliability',
      'consensus',
    ];

    this.numSamples = config.numSamples ?? 5;
    this.votingStrategy = config.votingStrategy ?? 'majority';
    // Validate at construction, not on the first sample, and reuse the shared
    // validator so the two spellings of the bounds cannot drift apart.
    validateCallOptions({ temperature: config.temperature });
    this.temperature = config.temperature;
    this.answerExtractor = config.answerExtractor ?? defaultAnswerExtractor;
  }

  /**
   * Report whether the configured temperature actually reaches the LLM.
   *
   * False when a temperature is set but the wrapped agent has no `processWith`
   * capability — the samples are then generated at whatever temperature the agent
   * is configured with.
   *
   * Exposed rather than left implicit because a silently ignored temperature is
   * precisely the failure this fixes: the value was accepted and dropped for as
   * long as the config field existed, and a documented config option is an
   * explicit invitation to set it (#801).
   *
   * @returns True when the temperature is applied, or when none is set — there is
   *   then nothing to apply, so nothing was dropped.
   */
  temperatureApplied(): boolean {
    if (this.temperature === undefined) {
      return true;
    }
    return supportsOptions(this.agent);
  }

  /**
   * Merge the caller's options with the configured temperature.
   *
   * The configured temperature is applied last and therefore wins over a
   * temperature in the caller's options. That is deliberate: this technique's
   * correctness depends on sampling diversity, so a caller reaching through it
   * must not silently flatten the samples. Every other option passes through
   * untouched.
   */
  private callOptions(callerOptions?: CallOptions): CallOptions {
    if (this.temperature === undefined) {
      return mergeCallOptions(callerOptions);
    }
    return mergeCallOptions(callerOptions, { temperature: this.temperature });
  }

  /**
   * Process a message with Self-Consistency.
   *
   * Generates multiple independent samples, extracts answers, and uses
   * voting to determine the most consistent answer.
   */
  async process(message: Message): Promise<Message> {
    return this.processWith(message, {});
  }

  /**
   * Process a message with Self-Consistency and per-call options.
   *
   * Implements the optional `processWith` capability, so this technique can itself
   * be wrapped by another that varies options — the capability has to run in both
   * directions, or the chain breaks at the first link that only consumes options
   * (#801).
   *
   * The caller's options are merged with the configured temperature, which wins on
   * conflict; see `callOptions`.
   */
  async processWith(message: Message, options: CallOptions): Promise<Message> {
    // Generate multiple samples in parallel
    const { fullResponses, extractedAnswers } = await this.generateSamples(message, options);

    // Vote for consensus answer
    let consensusAnswer: string;
    let consistencyScore: number;

    switch (this.votingStrategy) {
      case 'majority':
        ({ answer: consensusAnswer, score: consistencyScore } = this.voteMajority(extractedAnswers));
        break;
      case 'weighted':
        ({ answer: consensusAnswer, score: consistencyScore } = this.voteWeighted(
          extractedAnswers,
          fullResponses,
        ));
        break;
      case 'first':
        ({ answer: consensusAnswer, score: consistencyScore } = this.voteFirst(extractedAnswers));
        break;
      default:
        throw new Error(`Invalid voting strategy: ${this.votingStrategy}`);
    }

    // Count answer occurrences for metadata
    const answerCounts = this.countAnswers(extractedAnswers);

    // Build response with metadata
    return createMessage('assistant', consensusAnswer, {
      technique: 'self_consistency',
      num_samples: this.numSamples,
      voting_strategy: this.votingStrategy,
      consistency_score: consistencyScore,
      samples: fullResponses,
      extracted_answers: extractedAnswers,
      answer_counts: answerCounts,
      base_agent: this.agent.name,
      // Report the temperature and whether it reached the LLM, matching the
      // Python and Go cores. undefined when unset — a caller must be able to tell
      // "not requested" from "requested and dropped", which temperature_applied
      // alone cannot express.
      temperature: this.temperature,
      temperature_applied: this.temperatureApplied(),
    });
  }

  /**
   * Generate multiple samples in parallel.
   */
  private async generateSamples(
    message: Message,
    options?: CallOptions,
  ): Promise<{ fullResponses: string[]; extractedAnswers: string[] }> {
    // Generate samples in parallel
    const samplePromises = Array.from({ length: this.numSamples }, () =>
      this.sampleOnce(message, options),
    );

    try {
      const samples = await Promise.all(samplePromises);

      const fullResponses = samples.map(s => s.fullResponse);
      const extractedAnswers = samples.map(s => s.extractedAnswer);

      return { fullResponses, extractedAnswers };
    } catch (error) {
      throw new Error(`Sampling failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Generate one sample from the base agent.
   *
   * The options are rebuilt per call rather than stored on the instance: samples
   * run concurrently in `generateSamples`, and a shared mutable options object
   * would be written by every one of them.
   */
  private async sampleOnce(
    message: Message,
    options?: CallOptions,
  ): Promise<{ fullResponse: string; extractedAnswer: string }> {
    const response = await processWithOptions(this.agent, message, this.callOptions(options));

    const fullResponse = String(response.content);
    const extractedAnswer = this.answerExtractor(fullResponse);

    return { fullResponse, extractedAnswer };
  }

  /**
   * Vote using majority (most common answer wins).
   */
  private voteMajority(answers: string[]): { answer: string; score: number } {
    if (answers.length === 0) {
      return { answer: '', score: 0.0 };
    }

    // Count answer occurrences (case-insensitive)
    const counts = new Map<string, number>();
    const originalCase = new Map<string, string>();

    for (const answer of answers) {
      const normalized = answer.toLowerCase().trim();
      counts.set(normalized, (counts.get(normalized) || 0) + 1);
      if (!originalCase.has(normalized)) {
        originalCase.set(normalized, answer);
      }
    }

    // Find most common
    let winningAnswer = '';
    let maxCount = 0;

    for (const [normalized, count] of Array.from(counts.entries())) {
      if (count > maxCount) {
        maxCount = count;
        winningAnswer = normalized;
      }
    }

    // Get original case version
    const winner = originalCase.get(winningAnswer) || winningAnswer;
    const consistencyScore = maxCount / answers.length;

    return { answer: winner, score: consistencyScore };
  }

  /**
   * Vote using weighted strategy (longer responses get more weight).
   */
  private voteWeighted(
    answers: string[],
    responses: string[],
  ): { answer: string; score: number } {
    if (answers.length === 0) {
      return { answer: '', score: 0.0 };
    }

    // Group answers by normalized form
    const groups = new Map<
      string,
      {
        original: string;
        weight: number;
        count: number;
      }
    >();

    for (let i = 0; i < answers.length; i++) {
      const normalized = answers[i].toLowerCase().trim();
      const existing = groups.get(normalized);

      if (existing) {
        existing.weight += responses[i].length;
        existing.count += 1;
      } else {
        groups.set(normalized, {
          original: answers[i],
          weight: responses[i].length,
          count: 1,
        });
      }
    }

    // Find highest weighted answer
    let winningAnswer = '';
    let maxWeight = 0;
    let totalWeight = 0;

    for (const group of Array.from(groups.values())) {
      totalWeight += group.weight;
      if (group.weight > maxWeight) {
        maxWeight = group.weight;
        winningAnswer = group.original;
      }
    }

    const consistencyScore = totalWeight > 0 ? maxWeight / totalWeight : 0.0;

    return { answer: winningAnswer, score: consistencyScore };
  }

  /**
   * Use first answer (no voting, for debugging).
   */
  private voteFirst(answers: string[]): { answer: string; score: number } {
    if (answers.length === 0) {
      return { answer: '', score: 0.0 };
    }
    return { answer: answers[0], score: 1.0 };
  }

  /**
   * Count answer occurrences (case-insensitive).
   */
  private countAnswers(answers: string[]): Record<string, number> {
    const counts: Record<string, number> = {};

    for (const answer of answers) {
      const normalized = answer.toLowerCase().trim();
      counts[normalized] = (counts[normalized] || 0) + 1;
    }

    return counts;
  }
}

/**
 * Factory function to create a Self-Consistency agent.
 *
 * @param agent Base agent to wrap
 * @param config Configuration options
 * @returns Self-Consistency agent
 */
export function createSelfConsistencyAgent(
  agent: Agent,
  config?: SelfConsistencyConfig,
): SelfConsistencyAgent {
  return new SelfConsistencyAgent(agent, config);
}
