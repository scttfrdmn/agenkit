/**
 * Tests for LiteLLM adapter, focused on CallOptions.seed/stop wiring (#818).
 *
 * Full LiteLLM adapter coverage lives in integration/manual tests; this file
 * targets the specific defect #818 was filed about: seed and stop being
 * accepted by CallOptions and never reaching the provider request.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LiteLLMAdapter } from '../../../adapters/litellm';
import { getSimpleTestMessage } from './fixtures';

describe('LiteLLM Adapter: CallOptions wiring (#818)', () => {
  let adapter: LiteLLMAdapter;
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    adapter = new LiteLLMAdapter({ model: 'gpt-4' });

    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 'test-id',
        object: 'chat.completion',
        created: Date.now(),
        model: 'gpt-4',
        choices: [{ index: 0, message: { role: 'assistant', content: 'hi' }, finish_reason: 'stop' }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }),
    } as any);
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it('forwards seed and stop via processWith', async () => {
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { seed: 918273645, stop: ['END', 'STOP'] });

    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body.seed).toBe(918273645);
    expect(body.stop).toEqual(['END', 'STOP']);
  });
});
