/**
 * Tests for Bedrock LLM adapter, focused on CallOptions.seed/stop wiring (#818).
 *
 * Full Bedrock adapter coverage lives in integration/manual tests; this file
 * targets the specific defect #818 was filed about: seed and stop being
 * accepted by CallOptions and never reaching the provider request.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BedrockAdapter } from '../../../adapters/bedrock';
import { getSimpleTestMessage } from './fixtures';

describe('Bedrock Adapter: CallOptions wiring (#818)', () => {
  let adapter: BedrockAdapter;
  let sendMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    adapter = new BedrockAdapter({ modelId: 'anthropic.claude-3-haiku-20240307-v1:0' });

    sendMock = vi.fn().mockResolvedValue({
      output: { message: { content: [{ text: 'hi' }] } },
      stopReason: 'end_turn',
      usage: { inputTokens: 1, outputTokens: 1, totalTokens: 2 },
    });

    (adapter as any).client = { send: sendMock };
  });

  it('translates stop to inferenceConfig.stopSequences via processWith', async () => {
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { stop: ['END', 'STOP'] });

    const input = sendMock.mock.calls[0][0].input;
    expect(input.inferenceConfig.stopSequences).toEqual(['END', 'STOP']);
    expect(input.stop).toBeUndefined();
  });

  it('warns and drops unsupported seed via processWith', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { seed: 918273645 });

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("does not support 'seed'"));
    const input = sendMock.mock.calls[0][0].input;
    expect(input.inferenceConfig.seed).toBeUndefined();
    expect(input.seed).toBeUndefined();

    warnSpy.mockRestore();
  });
});
