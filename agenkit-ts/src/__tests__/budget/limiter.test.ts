import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Message } from '../../core/interfaces';
import { CostTracker, MemoryStorage } from '../../budget/tracker';
import { BudgetLimiter, BudgetExceededError } from '../../budget/limiter';

// ── helpers ──────────────────────────────────────────────────────────────────

class MockAgent {
  readonly name = 'mock_agent';

  async process(message: Message): Promise<Message> {
    return { role: 'assistant', content: `echo: ${message.content}` };
  }
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('BudgetLimiter', () => {
  let agent: MockAgent;
  let tracker: CostTracker;

  beforeEach(() => {
    agent = new MockAgent();
    tracker = new CostTracker(new MemoryStorage());
  });

  // ── constructor validation ──────────────────────────────────────────────

  it('should throw if switch_model action is used without switchToModel', () => {
    expect(
      () =>
        new BudgetLimiter(agent, tracker, {
          sessionLimit: 10,
          onBudgetExceeded: 'switch_model',
          // switchToModel omitted
        }),
    ).toThrow("switchToModel is required");
  });

  it('should create a limiter with valid switch_model config', () => {
    expect(
      () =>
        new BudgetLimiter(agent, tracker, {
          sessionLimit: 10,
          onBudgetExceeded: 'switch_model',
          switchToModel: 'claude-haiku-4-5',
        }),
    ).not.toThrow();
  });

  it('should expose the wrapped agent name', () => {
    const limiter = new BudgetLimiter(agent, tracker, {});
    expect(limiter.name).toBe('mock_agent');
  });

  // ── session limit ───────────────────────────────────────────────────────

  it('should enforce session limit — error action', async () => {
    const getSessionCost = vi.spyOn(tracker, 'getSessionCost').mockResolvedValue(10.01);
    const limiter = new BudgetLimiter(agent, tracker, {
      sessionLimit: 10.0,
      onBudgetExceeded: 'error',
    });

    const message: Message = {
      role: 'user',
      content: 'hello',
      metadata: { session_id: 'sess-1' },
    };

    await expect(limiter.process(message)).rejects.toThrow(BudgetExceededError);
    await expect(limiter.process(message)).rejects.toMatchObject({
      level: 'session',
    });

    getSessionCost.mockRestore();
  });

  it('should allow processing when session cost is below limit', async () => {
    const getSessionCost = vi.spyOn(tracker, 'getSessionCost').mockResolvedValue(5.0);
    const limiter = new BudgetLimiter(agent, tracker, {
      sessionLimit: 10.0,
      onBudgetExceeded: 'error',
    });

    const message: Message = { role: 'user', content: 'hello' };
    const response = await limiter.process(message);
    expect(response.role).toBe('assistant');

    getSessionCost.mockRestore();
  });

  // ── agent limit ─────────────────────────────────────────────────────────

  it('should enforce agent limit — error action', async () => {
    const getAgentCost = vi.spyOn(tracker, 'getAgentCost').mockResolvedValue(20.0);
    const limiter = new BudgetLimiter(agent, tracker, {
      agentLimit: 15.0,
      onBudgetExceeded: 'error',
    });

    const message: Message = { role: 'user', content: 'hello' };
    await expect(limiter.process(message)).rejects.toThrow(BudgetExceededError);
    await expect(limiter.process(message)).rejects.toMatchObject({ level: 'agent' });

    getAgentCost.mockRestore();
  });

  // ── global limit ────────────────────────────────────────────────────────

  it('should enforce global limit — error action', async () => {
    const getGlobalCost = vi.spyOn(tracker, 'getGlobalCost').mockResolvedValue(100.5);
    const limiter = new BudgetLimiter(agent, tracker, {
      globalLimit: 100.0,
      onBudgetExceeded: 'error',
    });

    const message: Message = { role: 'user', content: 'hello' };
    await expect(limiter.process(message)).rejects.toThrow(BudgetExceededError);
    await expect(limiter.process(message)).rejects.toMatchObject({ level: 'global' });

    getGlobalCost.mockRestore();
  });

  // ── warning action ──────────────────────────────────────────────────────

  it('should log warning and continue when warning action and budget exceeded', async () => {
    const getSessionCost = vi.spyOn(tracker, 'getSessionCost').mockResolvedValue(11.0);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const limiter = new BudgetLimiter(agent, tracker, {
      sessionLimit: 10.0,
      onBudgetExceeded: 'warning',
    });

    const message: Message = { role: 'user', content: 'hello' };
    const response = await limiter.process(message);

    // Should still process
    expect(response.role).toBe('assistant');
    // Should have warned
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Budget exceeded'));

    getSessionCost.mockRestore();
    warnSpy.mockRestore();
  });

  it('should emit warning at threshold even when limit not yet reached', async () => {
    // 90% of limit reached — threshold is 0.8 by default
    const getSessionCost = vi.spyOn(tracker, 'getSessionCost').mockResolvedValue(9.0);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const limiter = new BudgetLimiter(agent, tracker, {
      sessionLimit: 10.0,
      onBudgetExceeded: 'warning',
      warningThreshold: 0.8,
    });

    const message: Message = { role: 'user', content: 'hello' };
    await limiter.process(message);

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('BudgetWarning[session]'));

    getSessionCost.mockRestore();
    warnSpy.mockRestore();
  });

  // ── switch_model action ─────────────────────────────────────────────────

  it('should set model in metadata when switch_model action triggers', async () => {
    const getSessionCost = vi.spyOn(tracker, 'getSessionCost').mockResolvedValue(11.0);
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    const limiter = new BudgetLimiter(agent, tracker, {
      sessionLimit: 10.0,
      onBudgetExceeded: 'switch_model',
      switchToModel: 'claude-haiku-4-5',
    });

    const message: Message = { role: 'user', content: 'hello', metadata: {} };
    const response = await limiter.process(message);

    // Should still process
    expect(response.role).toBe('assistant');
    // Model should have been set in metadata
    expect(message.metadata!['model']).toBe('claude-haiku-4-5');

    getSessionCost.mockRestore();
    infoSpy.mockRestore();
  });

  // ── getRemainingBudget ──────────────────────────────────────────────────

  it('getRemainingBudget returns null for unconfigured limits', async () => {
    const limiter = new BudgetLimiter(agent, tracker, {
      sessionLimit: 10.0,
      // no agentLimit or globalLimit
    });
    vi.spyOn(tracker, 'getSessionCost').mockResolvedValue(3.0);

    const remaining = await limiter.getRemainingBudget('sess-1');
    expect(remaining['session']).toBeCloseTo(7.0);
    expect(remaining['agent']).toBeNull();
    expect(remaining['global']).toBeNull();
  });

  it('getRemainingBudget returns 0 when fully exhausted', async () => {
    const limiter = new BudgetLimiter(agent, tracker, {
      globalLimit: 50.0,
    });
    vi.spyOn(tracker, 'getGlobalCost').mockResolvedValue(55.0);

    const remaining = await limiter.getRemainingBudget();
    expect(remaining['global']).toBe(0);
  });
});
