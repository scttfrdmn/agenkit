/**
 * Budget management for cost tracking and control.
 *
 * This package provides tools for tracking LLM costs and enforcing budgets,
 * essential for managing expenses in long-running autonomous agents.
 *
 * Classes:
 *   ModelPricing: Pricing data for LLM models (January 2026 rates)
 *   Cost: Single cost record interface
 *   CostTracker: Track costs per session, agent, and globally
 *   Storage: Abstract interface for cost storage backends
 *   MemoryStorage: In-memory cost storage implementation
 *   InMemoryStorage: Deprecated alias for MemoryStorage
 *
 * Example:
 *   import { CostTracker } from 'agenkit';
 *
 *   // Track costs
 *   const tracker = new CostTracker();
 *   await tracker.recordCost({
 *     sessionId: 'session-123',
 *     agentName: 'assistant',
 *     model: 'claude-sonnet-4',
 *     inputTokens: 1000,
 *     outputTokens: 500,
 *   });
 *
 *   // Get session cost
 *   const cost = await tracker.getSessionCost('session-123');
 *   console.log(`Session cost: $${cost.toFixed(2)}`);
 */

export { ModelPricing } from './models';
export { Cost, costToDict, Storage, MemoryStorage, InMemoryStorage, CostTracker } from './tracker';
export { BudgetConfig, BudgetExceededError, BudgetWarning, BudgetLimiter } from './limiter';
