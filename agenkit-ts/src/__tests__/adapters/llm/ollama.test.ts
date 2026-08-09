/**
 * Tests for Ollama adapter, focused on CallOptions.seed/stop wiring (#818).
 *
 * Full Ollama adapter coverage lives in integration/manual tests; this file
 * targets the specific defect #818 was filed about: seed and stop being
 * accepted by CallOptions and never reaching the provider request.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { OllamaAdapter } from '../../../adapters/ollama';
import { getSimpleTestMessage } from './fixtures';

describe('Ollama Adapter: CallOptions wiring (#818)', () => {
  let adapter: OllamaAdapter;
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    adapter = new OllamaAdapter({ model: 'llama2' });

    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        model: 'llama2',
        created_at: new Date().toISOString(),
        message: { role: 'assistant', content: 'hi' },
        done: true,
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
    expect(body.options.seed).toBe(918273645);
    expect(body.options.stop).toEqual(['END', 'STOP']);
  });
});
