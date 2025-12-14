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

  /** Sampling temperature for diversity (optional) */
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
    this.temperature = config.temperature;
    this.answerExtractor = config.answerExtractor ?? defaultAnswerExtractor;
  }

  /**
   * Process a message with Self-Consistency.
   *
   * Generates multiple independent samples, extracts answers, and uses
   * voting to determine the most consistent answer.
   */
  async process(message: Message): Promise<Message> {
    // Generate multiple samples in parallel
    const { fullResponses, extractedAnswers } = await this.generateSamples(message);

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
    });
  }

  /**
   * Generate multiple samples in parallel.
   */
  private async generateSamples(
    message: Message,
  ): Promise<{ fullResponses: string[]; extractedAnswers: string[] }> {
    // Generate samples in parallel
    const samplePromises = Array.from({ length: this.numSamples }, () => this.sampleOnce(message));

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
   */
  private async sampleOnce(
    message: Message,
  ): Promise<{ fullResponse: string; extractedAnswer: string }> {
    // TODO: If temperature supported, pass it to agent
    const response = await this.agent.process(message);

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
