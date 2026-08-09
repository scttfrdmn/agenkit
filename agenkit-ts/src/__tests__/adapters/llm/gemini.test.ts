/**
 * Tests for Gemini LLM adapter, focused on CallOptions.seed/stop wiring (#818).
 *
 * Full Gemini adapter coverage lives in integration/manual tests; this file
 * targets the specific defect #818 was filed about: seed and stop being
 * accepted by CallOptions and never reaching the provider request.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GeminiAdapter } from '../../../adapters/gemini';
import { getSimpleTestMessage } from './fixtures';

describe('Gemini Adapter: CallOptions wiring (#818)', () => {
  let adapter: GeminiAdapter;
  let getGenerativeModelMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    adapter = new GeminiAdapter({ apiKey: 'test-key' });

    const mockResponse = {
      candidates: [
        {
          content: { parts: [{ text: 'hi' }] },
        },
      ],
      usageMetadata: undefined,
    };

    const mockChat = {
      sendMessage: vi.fn().mockResolvedValue({ response: mockResponse }),
    };

    getGenerativeModelMock = vi.fn().mockReturnValue({
      startChat: vi.fn().mockReturnValue(mockChat),
    });

    // Replace internal client with a mock so getGenerativeModel's config
    // argument can be inspected directly.
    (adapter as any).client = { getGenerativeModel: getGenerativeModelMock };
  });

  it('warns and drops unsupported seed rather than silently dropping it', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { seed: 918273645 });

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("does not support 'seed'"));

    warnSpy.mockRestore();
  });

  it('translates stop to stopSequences via processWith', async () => {
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { stop: ['END', 'STOP'] });

    const config = getGenerativeModelMock.mock.calls[0][0];
    expect(config.generationConfig.stopSequences).toEqual(['END', 'STOP']);
  });
});
