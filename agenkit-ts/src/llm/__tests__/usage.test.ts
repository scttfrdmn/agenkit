/**
 * Tests for typed token usage normalization.
 */

import { describe, it, expect } from 'vitest';
import { usageFromMessage, Usage } from '../usage';
import { createMessage, Message } from '../../core/interfaces';

function msg(metadata?: Record<string, unknown>): Message {
  return createMessage('assistant', 'hi', metadata);
}

const zero: Usage = {
  promptTokens: 0,
  completionTokens: 0,
  totalTokens: 0,
  cacheReadTokens: 0,
  cacheCreationTokens: 0,
};

describe('usageFromMessage', () => {
  it('returns ok=false for null/undefined message', () => {
    expect(usageFromMessage(null)).toEqual([zero, false]);
    expect(usageFromMessage(undefined)).toEqual([zero, false]);
  });

  it('returns ok=false when no usage metadata is present', () => {
    expect(usageFromMessage(msg({ model: 'x' }))).toEqual([zero, false]);
    expect(usageFromMessage(msg())).toEqual([zero, false]);
  });

  it('normalizes nested usage object (adapters convention)', () => {
    const [u, ok] = usageFromMessage(
      msg({ usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } }),
    );
    expect(ok).toBe(true);
    expect(u).toEqual({ ...zero, promptTokens: 10, completionTokens: 5, totalTokens: 15 });
  });

  it('normalizes flat top-level token keys (llm convention)', () => {
    const [u, ok] = usageFromMessage(
      msg({ input_tokens: 30, output_tokens: 7, total_tokens: 37, model: 'x' }),
    );
    expect(ok).toBe(true);
    expect(u).toEqual({ ...zero, promptTokens: 30, completionTokens: 7, totalTokens: 37 });
  });

  it('derives total when absent', () => {
    const [u, ok] = usageFromMessage(msg({ usage: { prompt_tokens: 8, completion_tokens: 2 } }));
    expect(ok).toBe(true);
    expect(u.totalTokens).toBe(10);
  });

  it('reads Bedrock-style normalized cache keys', () => {
    const [u, ok] = usageFromMessage(
      msg({
        usage: {
          prompt_tokens: 1000,
          completion_tokens: 50,
          total_tokens: 1050,
          cache_read_tokens: 900,
          cache_creation_tokens: 100,
        },
      }),
    );
    expect(ok).toBe(true);
    expect(u.cacheReadTokens).toBe(900);
    expect(u.cacheCreationTokens).toBe(100);
  });

  it('reads raw provider cache key aliases', () => {
    const [u, ok] = usageFromMessage(
      msg({
        usage: {
          input_tokens: 20,
          output_tokens: 4,
          cache_read_input_tokens: 15,
          cache_creation_input_tokens: 5,
        },
      }),
    );
    expect(ok).toBe(true);
    expect(u).toEqual({
      promptTokens: 20,
      completionTokens: 4,
      totalTokens: 24,
      cacheReadTokens: 15,
      cacheCreationTokens: 5,
    });
  });

  it('ignores non-numeric values', () => {
    const [u, ok] = usageFromMessage(
      msg({ usage: { prompt_tokens: 'x', completion_tokens: 5 } }),
    );
    expect(ok).toBe(true);
    expect(u.promptTokens).toBe(0);
    expect(u.completionTokens).toBe(5);
  });
});
