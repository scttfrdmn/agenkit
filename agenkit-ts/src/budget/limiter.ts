/**
 * Budget limiting middleware for cost control.
 *
 * Wraps an agent with budget enforcement, stopping execution when budgets are
 * exceeded. Supports per-session, per-agent, and global budgets with configurable
 * actions when limits are reached.
 *
 * Modeled on the Go and Python BudgetLimiter implementations for cross-language
 * parity.
 *
 * Example:
 *   const tracker = new CostTracker();
 *   const limiter = new BudgetLimiter(myAgent, tracker, {
 *     sessionLimit: 10.00,
 *     onBudgetExceeded: 'error',
 *   });
 *   const response = await limiter.process(message);
 */

import { Agent, Message } from '../core/interfaces';
import { CostTracker } from './tracker';

/**
 * Configuration for budget enforcement.
 */
export interface BudgetConfig {
  /** Maximum cost per session in USD (undefined = unlimited) */
  sessionLimit?: number;

  /** Maximum cost per agent across all sessions in USD (undefined = unlimited) */
  agentLimit?: number;

  /** Maximum global cost in USD (undefined = unlimited) */
  globalLimit?: number;

  /**
   * Fraction of budget at which a warning is issued (0–1, default 0.8).
   * Only applies when onBudgetExceeded is 'warning'.
   */
  warningThreshold?: number;

  /**
   * Action to take when a budget is exceeded:
   * - 'error': throw BudgetExceededError (default)
   * - 'warning': log a warning and continue
   * - 'switch_model': set metadata.model to switchToModel and continue
   */
  onBudgetExceeded?: 'error' | 'warning' | 'switch_model';

  /** Model to switch to when onBudgetExceeded is 'switch_model' */
  switchToModel?: string;
}

/**
 * Thrown when a budget is exceeded and onBudgetExceeded is 'error'.
 */
export class BudgetExceededError extends Error {
  constructor(
    message: string,
    public readonly level: 'session' | 'agent' | 'global',
    public readonly current: number,
    public readonly limit: number,
  ) {
    super(message);
    this.name = 'BudgetExceededError';
  }
}

/**
 * Carries budget warning details when onBudgetExceeded is 'warning' and the
 * warningThreshold has been reached.
 */
export class BudgetWarning {
  constructor(
    public readonly level: 'session' | 'agent' | 'global',
    public readonly current: number,
    public readonly limit: number,
    public readonly threshold: number,
  ) {}

  toString(): string {
    const pct = Math.round((this.current / this.limit) * 100);
    return (
      `BudgetWarning[${this.level}]: $${this.current.toFixed(4)} / $${this.limit.toFixed(2)}` +
      ` (${pct}% — threshold ${Math.round(this.threshold * 100)}%)`
    );
  }
}

/**
 * Budget-enforcing agent wrapper.
 *
 * Checks budgets before each call to `process()`. On budget exceeded:
 * - 'error' action: throws BudgetExceededError
 * - 'warning' action: logs a warning and continues
 * - 'switch_model' action: adds/overwrites metadata.model and continues
 *
 * Example:
 *   const tracker = new CostTracker();
 *   const limiter = new BudgetLimiter(myAgent, tracker, {
 *     sessionLimit: 5.00,
 *     onBudgetExceeded: 'error',
 *   });
 *
 *   try {
 *     const response = await limiter.process(message);
 *   } catch (e) {
 *     if (e instanceof BudgetExceededError) {
 *       console.log(`Budget exceeded: ${e.message}`);
 *     }
 *   }
 */
export class BudgetLimiter implements Agent {
  private readonly action: 'error' | 'warning' | 'switch_model';
  private readonly warningThreshold: number;

  constructor(
    private readonly agent: Agent,
    private readonly tracker: CostTracker,
    private readonly config: BudgetConfig,
  ) {
    this.action = config.onBudgetExceeded ?? 'error';
    this.warningThreshold = config.warningThreshold ?? 0.8;

    if (this.action === 'switch_model' && !config.switchToModel) {
      throw new Error("switchToModel is required when onBudgetExceeded is 'switch_model'");
    }
  }

  get name(): string {
    return this.agent.name;
  }

  /**
   * Process a message with budget enforcement.
   *
   * Extracts session_id and agent_name from message.metadata when present.
   * Checks configured budget limits before forwarding to the wrapped agent.
   *
   * @throws BudgetExceededError when limit exceeded and action is 'error'
   */
  async process(message: Message): Promise<Message> {
    const sessionId = (message.metadata?.['session_id'] as string) ?? 'default';
    const agentName = this.agent.name;

    await this.checkBudgets(sessionId, agentName, message);

    return this.agent.process(message);
  }

  /**
   * Return remaining budget for the given session and agent.
   *
   * A `null` value means unlimited (no limit configured).
   */
  async getRemainingBudget(
    sessionId = 'default',
    agentName?: string,
  ): Promise<Record<string, number | null>> {
    const name = agentName ?? this.agent.name;
    const result: Record<string, number | null> = {
      session: null,
      agent: null,
      global: null,
    };

    if (this.config.sessionLimit !== undefined) {
      const current = await this.tracker.getSessionCost(sessionId);
      result['session'] = Math.max(0, this.config.sessionLimit - current);
    }

    if (this.config.agentLimit !== undefined) {
      const current = await this.tracker.getAgentCost(name);
      result['agent'] = Math.max(0, this.config.agentLimit - current);
    }

    if (this.config.globalLimit !== undefined) {
      const current = await this.tracker.getGlobalCost();
      result['global'] = Math.max(0, this.config.globalLimit - current);
    }

    return result;
  }

  private async checkBudgets(
    sessionId: string,
    agentName: string,
    message: Message,
  ): Promise<void> {
    if (this.config.sessionLimit !== undefined) {
      const current = await this.tracker.getSessionCost(sessionId);
      if (current >= this.config.sessionLimit) {
        await this.handleExceeded(
          'session',
          current,
          this.config.sessionLimit,
          message,
        );
      } else if (
        this.action === 'warning' &&
        current / this.config.sessionLimit >= this.warningThreshold
      ) {
        const warning = new BudgetWarning(
          'session',
          current,
          this.config.sessionLimit,
          this.warningThreshold,
        );
        console.warn(warning.toString());
      }
    }

    if (this.config.agentLimit !== undefined) {
      const current = await this.tracker.getAgentCost(agentName);
      if (current >= this.config.agentLimit) {
        await this.handleExceeded(
          'agent',
          current,
          this.config.agentLimit,
          message,
        );
      } else if (
        this.action === 'warning' &&
        current / this.config.agentLimit >= this.warningThreshold
      ) {
        const warning = new BudgetWarning(
          'agent',
          current,
          this.config.agentLimit,
          this.warningThreshold,
        );
        console.warn(warning.toString());
      }
    }

    if (this.config.globalLimit !== undefined) {
      const current = await this.tracker.getGlobalCost();
      if (current >= this.config.globalLimit) {
        await this.handleExceeded(
          'global',
          current,
          this.config.globalLimit,
          message,
        );
      } else if (
        this.action === 'warning' &&
        current / this.config.globalLimit >= this.warningThreshold
      ) {
        const warning = new BudgetWarning(
          'global',
          current,
          this.config.globalLimit,
          this.warningThreshold,
        );
        console.warn(warning.toString());
      }
    }
  }

  private async handleExceeded(
    level: 'session' | 'agent' | 'global',
    current: number,
    limit: number,
    message: Message,
  ): Promise<void> {
    const msg = `${level} budget $${limit.toFixed(2)} exceeded (current: $${current.toFixed(4)})`;

    switch (this.action) {
      case 'error':
        throw new BudgetExceededError(msg, level, current, limit);
      case 'warning':
        console.warn(`WARNING: Budget exceeded: ${msg}`);
        break;
      case 'switch_model':
        console.info(`INFO: Budget threshold reached: ${msg}, switching to ${this.config.switchToModel}`);
        if (!message.metadata) {
          (message as { metadata: Record<string, unknown> }).metadata = {};
        }
        message.metadata!['model'] = this.config.switchToModel;
        break;
    }
  }
}
