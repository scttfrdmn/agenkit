/**
 * Context-aware metrics for extreme-scale evaluation.
 *
 * Designed for systems that operate at very large context windows (1M+ tokens).
 * Tracks context length, compression ratios, and growth over time.
 *
 * Example:
 * ```typescript
 * const metric = new ContextMetrics();
 * const length = await metric.measure(agent, inputMsg, outputMsg, {
 *   conversationHistory: [...messages],
 * });
 * console.log(`Context length: ${length} tokens`);
 * ```
 */

import { Agent, Message } from '../core/interfaces';
import { Metric } from './quality-metrics';

/**
 * Agent interface with context stats capability.
 */
export interface AgentWithContextStats extends Agent {
  /**
   * Get context statistics for a session.
   *
   * @param sessionId Session identifier
   * @returns Context statistics
   */
  getContextStats(sessionId: string): Promise<Record<string, number>>;
}

/**
 * Check if agent supports context stats.
 *
 * @param agent Agent to check
 * @returns True if agent has getContextStats method
 */
function hasContextStats(agent: Agent): agent is AgentWithContextStats {
  return 'getContextStats' in agent && typeof agent.getContextStats === 'function';
}

/**
 * Track context length and growth over agent lifecycle.
 *
 * Essential for extreme-scale systems that operate at 1M-25M+ token contexts.
 * Measures:
 * - Raw context token count
 * - Compressed context token count (if compression used)
 * - Compression ratio
 * - Context growth rate
 *
 * Example:
 * ```typescript
 * const contextMetric = new ContextMetrics();
 * const evaluator = new Evaluator(agent, [contextMetric]);
 * const result = await evaluator.evaluate(testCases);
 * console.log('Growth rate:', result.aggregatedMetrics.context_length.growth_rate);
 * ```
 */
export class ContextMetrics implements Metric {
  readonly name = 'context_length';

  /**
   * Measure context length metrics.
   *
   * Attempts to get context length from:
   * 1. Agent's getContextStats method (if available)
   * 2. Input message metadata
   * 3. Conversation history in context
   * 4. Defaults to 0
   *
   * @param agent Agent being evaluated
   * @param inputMessage Input message
   * @param outputMessage Agent response
   * @param context Additional context with session history
   * @returns Current context length in tokens
   */
  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    const ctx = context || {};

    // Try to get context stats from agent
    if (hasContextStats(agent)) {
      const sessionId = String(ctx.sessionId || 'default');
      const stats = await agent.getContextStats(sessionId);
      return stats.context_length || 0;
    }

    // Try message metadata
    if (inputMessage.metadata?.context_length) {
      return Number(inputMessage.metadata.context_length);
    }

    // Try conversation history
    if (ctx.conversationHistory && Array.isArray(ctx.conversationHistory)) {
      const history = ctx.conversationHistory as Message[];
      const totalTokens = history.reduce(
        (sum, msg) => sum + this.estimateTokens(String(msg.content)),
        0
      );
      return totalTokens;
    }

    return 0;
  }

  /**
   * Aggregate context length measurements.
   *
   * Computes statistics useful for understanding context growth:
   * - mean: Average context length
   * - min: Minimum context length
   * - max: Maximum context length
   * - final: Final context length
   * - growth_rate: Average tokens added per measurement
   *
   * @param measurements List of context lengths over time
   * @returns Aggregated statistics
   */
  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return {
        mean: 0,
        min: 0,
        max: 0,
        final: 0,
        growth_rate: 0,
      };
    }

    const sum = measurements.reduce((a, b) => a + b, 0);
    const mean = sum / measurements.length;
    const min = Math.min(...measurements);
    const max = Math.max(...measurements);
    const final = measurements[measurements.length - 1];

    // Calculate growth rate (tokens per measurement)
    const growthRate =
      measurements.length > 1
        ? (measurements[measurements.length - 1] - measurements[0]) / measurements.length
        : 0;

    return {
      mean,
      min,
      max,
      final,
      growth_rate: growthRate,
    };
  }

  /**
   * Estimate token count from text.
   *
   * Uses rough heuristic: 4 characters ≈ 1 token
   *
   * @param content Text content
   * @returns Estimated token count
   */
  private estimateTokens(content: string): number {
    return Math.floor(content.length / 4);
  }
}

/**
 * Statistics from compression evaluation.
 */
export interface CompressionStats {
  /** Raw token count before compression */
  rawTokens: number;
  /** Compressed token count */
  compressedTokens: number;
  /** Compression ratio (raw / compressed) */
  compressionRatio: number;
  /** Retrieval accuracy after compression */
  retrievalAccuracy: number;
  /** Context length that was tested */
  contextLengthTested: number;
  /** Timestamp of measurement */
  timestamp: Date;
}

/**
 * Create compression stats.
 *
 * @param rawTokens Raw token count
 * @param compressedTokens Compressed token count
 * @param retrievalAccuracy Retrieval accuracy (0-1)
 * @param contextLengthTested Context length tested
 * @returns Compression statistics
 */
export function createCompressionStats(
  rawTokens: number,
  compressedTokens: number,
  retrievalAccuracy: number,
  contextLengthTested: number
): CompressionStats {
  return {
    rawTokens,
    compressedTokens,
    compressionRatio: rawTokens / compressedTokens,
    retrievalAccuracy,
    contextLengthTested,
    timestamp: new Date(),
  };
}

/**
 * Convert compression stats to plain object.
 *
 * @param stats Compression statistics
 * @returns Plain object representation
 */
export function compressionStatsToDict(
  stats: CompressionStats
): Record<string, unknown> {
  return {
    raw_tokens: stats.rawTokens,
    compressed_tokens: stats.compressedTokens,
    compression_ratio: stats.compressionRatio,
    retrieval_accuracy: stats.retrievalAccuracy,
    context_length_tested: stats.contextLengthTested,
    timestamp: stats.timestamp.toISOString(),
  };
}

/**
 * Metric for tracking compression effectiveness.
 *
 * Measures compression ratio (raw tokens / compressed tokens).
 * Higher values indicate better compression.
 */
export class CompressionMetrics implements Metric {
  readonly name = 'compression_ratio';

  /**
   * Measure compression ratio.
   *
   * Looks for compression metadata in messages or context.
   *
   * @param agent Agent being evaluated
   * @param inputMessage Input message
   * @param outputMessage Agent response
   * @param context Additional context
   * @returns Compression ratio (or 1.0 if no compression)
   */
  async measure(
    agent: Agent,
    inputMessage: Message,
    outputMessage: Message,
    context?: Record<string, unknown>
  ): Promise<number> {
    // Try to get compression stats from message metadata
    if (inputMessage.metadata?.raw_tokens && inputMessage.metadata?.compressed_tokens) {
      const raw = Number(inputMessage.metadata.raw_tokens);
      const compressed = Number(inputMessage.metadata.compressed_tokens);
      return compressed > 0 ? raw / compressed : 1.0;
    }

    // Try to get from context
    if (context?.raw_tokens && context?.compressed_tokens) {
      const raw = Number(context.raw_tokens);
      const compressed = Number(context.compressed_tokens);
      return compressed > 0 ? raw / compressed : 1.0;
    }

    // No compression detected
    return 1.0;
  }

  /**
   * Aggregate compression ratio measurements.
   *
   * @param measurements List of compression ratios
   * @returns Statistics
   */
  aggregate(measurements: number[]): Record<string, number> {
    if (measurements.length === 0) {
      return { mean: 1.0, min: 1.0, max: 1.0, count: 0 };
    }

    const sum = measurements.reduce((a, b) => a + b, 0);
    return {
      mean: sum / measurements.length,
      min: Math.min(...measurements),
      max: Math.max(...measurements),
      count: measurements.length,
    };
  }
}
