/**
 * Cost tracking for LLM usage.
 *
 * Tracks costs per session, per agent, and globally for budget management.
 */

import { ModelPricing } from './models';

/**
 * Single cost record.
 */
export interface Cost {
  /** Session identifier */
  sessionId: string;

  /** Agent name */
  agentName: string;

  /** Model identifier */
  model: string;

  /** Number of input tokens */
  inputTokens: number;

  /** Number of output tokens */
  outputTokens: number;

  /** Number of thinking/reasoning tokens (o3, Claude 4 extended) */
  thinkingTokens: number;

  /** Cost for input tokens ($) */
  inputCost: number;

  /** Cost for output tokens ($) */
  outputCost: number;

  /** Cost for thinking tokens ($) */
  thinkingCost: number;

  /** Total cost ($) */
  totalCost: number;

  /** When cost was recorded */
  timestamp: Date;

  /** Additional metadata */
  metadata: Record<string, unknown>;
}

/**
 * Convert Cost to dictionary.
 */
export function costToDict(cost: Cost): Record<string, unknown> {
  return {
    ...cost,
    timestamp: cost.timestamp.toISOString(),
  };
}

/**
 * Abstract interface for cost storage backends.
 */
export interface Storage {
  /**
   * Store a cost record.
   */
  store(cost: Cost): Promise<void>;

  /**
   * Query cost records.
   */
  query(options?: {
    sessionId?: string;
    agentName?: string;
    startTime?: Date;
    endTime?: Date;
  }): Promise<Cost[]>;
}

/**
 * In-memory storage for cost records.
 */
export class InMemoryStorage implements Storage {
  private costs: Cost[] = [];

  /**
   * Store cost record in memory.
   */
  async store(cost: Cost): Promise<void> {
    this.costs.push(cost);
  }

  /**
   * Query cost records from memory.
   */
  async query(options?: {
    sessionId?: string;
    agentName?: string;
    startTime?: Date;
    endTime?: Date;
  }): Promise<Cost[]> {
    const results: Cost[] = [];

    for (const cost of this.costs) {
      // Filter by session_id
      if (options?.sessionId && cost.sessionId !== options.sessionId) {
        continue;
      }

      // Filter by agent_name
      if (options?.agentName && cost.agentName !== options.agentName) {
        continue;
      }

      // Filter by time range
      if (options?.startTime && cost.timestamp < options.startTime) {
        continue;
      }
      if (options?.endTime && cost.timestamp > options.endTime) {
        continue;
      }

      results.push(cost);
    }

    return results;
  }
}

/**
 * Track LLM costs per session, agent, and globally.
 *
 * Features:
 * - Per-session cost tracking
 * - Per-agent cost tracking
 * - Global cost tracking
 * - Cost breakdown by model
 * - Time-series cost data
 *
 * Example:
 *   const tracker = new CostTracker();
 *   await tracker.recordCost({
 *     sessionId: 'user-123',
 *     agentName: 'assistant',
 *     model: 'claude-sonnet-4',
 *     inputTokens: 1000,
 *     outputTokens: 500,
 *   });
 *   const total = await tracker.getSessionCost('user-123');
 *   console.log(`Session cost: $${total.toFixed(2)}`);
 *   // Session cost: $0.01
 */
export class CostTracker {
  private storage: Storage;
  private modelPricing: ModelPricing;

  constructor(storage?: Storage) {
    this.storage = storage || new InMemoryStorage();
    this.modelPricing = new ModelPricing();
  }

  /**
   * Record a cost event.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const cost = await tracker.recordCost({
   *     sessionId: 'session-1',
   *     agentName: 'assistant',
   *     model: 'claude-sonnet-4',
   *     inputTokens: 1000,
   *     outputTokens: 500,
   *     thinkingTokens: 5000,
   *   });
   *   console.log(`$${cost.totalCost.toFixed(4)}`);
   *   // $0.0180
   */
  async recordCost(params: {
    sessionId: string;
    agentName: string;
    model: string;
    inputTokens: number;
    outputTokens: number;
    thinkingTokens?: number;
    metadata?: Record<string, unknown>;
  }): Promise<Cost> {
    const { sessionId, agentName, model, inputTokens, outputTokens, thinkingTokens = 0, metadata = {} } = params;

    // Calculate costs
    const inputCost = this.modelPricing.calculate(model, inputTokens, 'input');
    const outputCost = this.modelPricing.calculate(model, outputTokens, 'output');

    // Thinking tokens typically use output token pricing
    // (some models may charge differently, but this is a reasonable default)
    const thinkingCost =
      thinkingTokens > 0 ? this.modelPricing.calculate(model, thinkingTokens, 'output') : 0.0;

    const totalCost = inputCost + outputCost + thinkingCost;

    // Create record
    const cost: Cost = {
      sessionId,
      agentName,
      model,
      inputTokens,
      outputTokens,
      thinkingTokens,
      inputCost,
      outputCost,
      thinkingCost,
      totalCost,
      timestamp: new Date(),
      metadata,
    };

    // Store
    await this.storage.store(cost);

    return cost;
  }

  /**
   * Get total cost for a session.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const cost = await tracker.getSessionCost('session-1');
   *   console.log(`$${cost.toFixed(2)}`);
   */
  async getSessionCost(sessionId: string): Promise<number> {
    const costs = await this.storage.query({ sessionId });
    return costs.reduce((sum, cost) => sum + cost.totalCost, 0.0);
  }

  /**
   * Get total cost for an agent across all sessions.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const cost = await tracker.getAgentCost('assistant');
   *   console.log(`$${cost.toFixed(2)}`);
   */
  async getAgentCost(agentName: string): Promise<number> {
    const costs = await this.storage.query({ agentName });
    return costs.reduce((sum, cost) => sum + cost.totalCost, 0.0);
  }

  /**
   * Get global cost across all sessions and agents.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const cost = await tracker.getGlobalCost();
   *   console.log(`Total: $${cost.toFixed(2)}`);
   */
  async getGlobalCost(): Promise<number> {
    const costs = await this.storage.query();
    return costs.reduce((sum, cost) => sum + cost.totalCost, 0.0);
  }

  /**
   * Get cost breakdown by model.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const breakdown = await tracker.getCostByModel();
   *   for (const [model, cost] of Object.entries(breakdown)) {
   *     console.log(`${model}: $${cost.toFixed(2)}`);
   *   }
   */
  async getCostByModel(sessionId?: string): Promise<Record<string, number>> {
    const costs = await this.storage.query(sessionId ? { sessionId } : undefined);
    const breakdown: Record<string, number> = {};

    for (const cost of costs) {
      breakdown[cost.model] = (breakdown[cost.model] || 0.0) + cost.totalCost;
    }

    return breakdown;
  }

  /**
   * Get cost statistics for a session.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const stats = await tracker.getSessionStats('session-1');
   *   console.log(stats);
   */
  async getSessionStats(sessionId: string): Promise<{
    totalCost: number;
    inputTokens: number;
    outputTokens: number;
    thinkingTokens: number;
    requestCount: number;
    models: string[];
  }> {
    const costs = await this.storage.query({ sessionId });

    const totalCost = costs.reduce((sum, cost) => sum + cost.totalCost, 0.0);
    const inputTokens = costs.reduce((sum, cost) => sum + cost.inputTokens, 0);
    const outputTokens = costs.reduce((sum, cost) => sum + cost.outputTokens, 0);
    const thinkingTokens = costs.reduce((sum, cost) => sum + cost.thinkingTokens, 0);
    const models = [...new Set(costs.map((cost) => cost.model))];

    return {
      totalCost,
      inputTokens,
      outputTokens,
      thinkingTokens,
      requestCount: costs.length,
      models,
    };
  }

  /**
   * Get recent costs (last N records).
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const recent = await tracker.getRecentCosts(10);
   *   for (const cost of recent) {
   *     console.log(`${cost.agentName}: $${cost.totalCost.toFixed(4)}`);
   *   }
   */
  async getRecentCosts(limit: number = 10): Promise<Cost[]> {
    const allCosts = await this.storage.query();
    // Sort by timestamp descending
    allCosts.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    return allCosts.slice(0, limit);
  }

  /**
   * Get costs within time range.
   *
   * Example:
   *   const tracker = new CostTracker();
   *   const start = new Date('2026-01-01');
   *   const end = new Date('2026-01-31');
   *   const costs = await tracker.getCostsByTimeRange(start, end);
   *   console.log(`Costs: ${costs.length}`);
   */
  async getCostsByTimeRange(startTime: Date, endTime: Date): Promise<Cost[]> {
    return await this.storage.query({ startTime, endTime });
  }
}
