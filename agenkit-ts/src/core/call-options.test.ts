/**
 * Tests for per-call inference options (#801).
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message, createMessage } from './interfaces';
import {
  CallOptions,
  callOptionsToParams,
  isCallOptionsEmpty,
  mergeCallOptions,
  processWithOptions,
  supportsOptions,
  validateCallOptions,
} from './call-options';

/**
 * An agent that implements processWith and records which path it was entered by.
 *
 * Recording the path matters as much as recording the options: the bug this file
 * guards against is a caller that takes the plain process path and silently drops
 * what it was handed, which a test that only inspects the returned message cannot
 * distinguish from success.
 */
class OptionsRecordingAgent implements Agent {
  readonly name = 'options_agent';
  readonly capabilities = ['options'];

  processCalls = 0;
  processWithCalls = 0;
  lastOptions?: CallOptions;

  async process(_message: Message): Promise<Message> {
    this.processCalls += 1;
    return createMessage('assistant', 'plain');
  }

  async processWith(_message: Message, options: CallOptions): Promise<Message> {
    this.processWithCalls += 1;
    this.lastOptions = options;
    return createMessage('assistant', 'with-options');
  }
}

/** An agent with no processWith capability. */
class PlainAgent implements Agent {
  readonly name = 'plain_agent';
  processCalls = 0;

  async process(message: Message): Promise<Message> {
    this.processCalls += 1;
    return createMessage('assistant', `Processed: ${String(message.content)}`);
  }
}

describe('validateCallOptions', () => {
  it('accepts an empty options object', () => {
    expect(() => validateCallOptions({})).not.toThrow();
  });

  it('accepts temperature 0, which is a real request', () => {
    // Greedy decoding. Validation must not confuse the zero value with "unset".
    expect(() => validateCallOptions({ temperature: 0 })).not.toThrow();
  });

  it.each([-0.1, 2.1, NaN])('rejects temperature %s', (temperature) => {
    expect(() => validateCallOptions({ temperature })).toThrow(
      /temperature must be between 0 and 2/,
    );
  });

  it.each([0, -1, 1.5])('rejects maxTokens %s', (maxTokens) => {
    expect(() => validateCallOptions({ maxTokens })).toThrow(
      /maxTokens must be a positive integer/,
    );
  });

  it.each([-0.1, 1.1])('rejects topP %s', (topP) => {
    expect(() => validateCallOptions({ topP })).toThrow(/topP must be between 0 and 1/);
  });

  it('rejects a non-integer seed', () => {
    expect(() => validateCallOptions({ seed: 1.5 })).toThrow(/seed must be an integer/);
  });

  it('accepts values at the range boundaries', () => {
    expect(() =>
      validateCallOptions({ temperature: 2, topP: 1, maxTokens: 1, seed: 0 }),
    ).not.toThrow();
  });
});

describe('isCallOptionsEmpty', () => {
  it('treats undefined and {} as empty', () => {
    expect(isCallOptionsEmpty(undefined)).toBe(true);
    expect(isCallOptionsEmpty({})).toBe(true);
  });

  it('treats an empty extra map as empty', () => {
    expect(isCallOptionsEmpty({ extra: {} })).toBe(true);
  });

  it('treats temperature 0 as set', () => {
    // The whole point of "undefined means unset": a falsy-but-present value is a
    // request that must survive the empty check and reach the provider.
    expect(isCallOptionsEmpty({ temperature: 0 })).toBe(false);
  });

  it.each([
    ['temperature', { temperature: 0.7 }],
    ['maxTokens', { maxTokens: 32 }],
    ['topP', { topP: 0.9 }],
    ['seed', { seed: 42 }],
    ['stop', { stop: ['\n'] }],
    ['extra', { extra: { logit_bias: {} } }],
  ] as [string, CallOptions][])('treats a set %s as non-empty', (_name, options) => {
    expect(isCallOptionsEmpty(options)).toBe(false);
  });
});

describe('callOptionsToParams', () => {
  it('omits unset fields rather than emitting undefined', () => {
    // A key present with an undefined value would still override a provider
    // default in most HTTP clients, so absence has to mean absence.
    const params = callOptionsToParams({ temperature: 0.7 });
    expect(params).toEqual({ temperature: 0.7 });
    expect(Object.keys(params)).toEqual(['temperature']);
  });

  it('emits temperature 0', () => {
    expect(callOptionsToParams({ temperature: 0 })).toEqual({ temperature: 0 });
  });

  it('renames camelCase fields to the snake_case wire format', () => {
    expect(callOptionsToParams({ maxTokens: 100, topP: 0.9 })).toEqual({
      max_tokens: 100,
      top_p: 0.9,
    });
  });

  it('passes extra through by key', () => {
    expect(callOptionsToParams({ extra: { frequency_penalty: 0.5 } })).toEqual({
      frequency_penalty: 0.5,
    });
  });

  it('copies stop rather than aliasing the caller array', () => {
    const stop = ['\n'];
    const params = callOptionsToParams({ stop });
    (params.stop as string[]).push('END');
    expect(stop).toEqual(['\n']);
  });

  it('returns an empty object for no options', () => {
    expect(callOptionsToParams(undefined)).toEqual({});
  });
});

describe('mergeCallOptions', () => {
  it('lets a set override field win', () => {
    expect(mergeCallOptions({ temperature: 0.2 }, { temperature: 0.9 })).toEqual({
      temperature: 0.9,
    });
  });

  it('lets an override temperature of 0 win', () => {
    expect(mergeCallOptions({ temperature: 0.9 }, { temperature: 0 })).toEqual({ temperature: 0 });
  });

  it('does not let an omitted override field erase the base', () => {
    expect(mergeCallOptions({ temperature: 0.5, maxTokens: 10 }, { maxTokens: 20 })).toEqual({
      temperature: 0.5,
      maxTokens: 20,
    });
  });

  it('does not let an explicitly-undefined override field erase the base', () => {
    // undefined means "did not ask", not "clear it". A naive `{...base, ...override}`
    // survives the omitted-key case above — a spread has nothing to copy for an
    // absent key — but wipes the base here, where the key is present and undefined.
    // That is the common shape in practice: `{ temperature: maybeUndefined }`.
    const merged = mergeCallOptions(
      { temperature: 0.5, maxTokens: 10 },
      { temperature: undefined, maxTokens: 20 },
    );
    expect(merged.temperature).toBe(0.5);
    expect(merged.maxTokens).toBe(20);
  });

  it('merges extra key by key', () => {
    expect(mergeCallOptions({ extra: { a: 1, b: 2 } }, { extra: { b: 3 } })).toEqual({
      extra: { a: 1, b: 3 },
    });
  });

  it('does not mutate either input', () => {
    const base: CallOptions = { temperature: 0.2, extra: { a: 1 } };
    const override: CallOptions = { temperature: 0.9, extra: { b: 2 } };
    mergeCallOptions(base, override);
    expect(base).toEqual({ temperature: 0.2, extra: { a: 1 } });
    expect(override).toEqual({ temperature: 0.9, extra: { b: 2 } });
  });

  it('handles both sides being absent', () => {
    expect(mergeCallOptions(undefined, undefined)).toEqual({});
  });
});

describe('supportsOptions', () => {
  it('is false for an agent without processWith', () => {
    expect(supportsOptions(new PlainAgent())).toBe(false);
  });

  it('is true for an agent with processWith', () => {
    expect(supportsOptions(new OptionsRecordingAgent())).toBe(true);
  });
});

describe('processWithOptions', () => {
  it('routes to processWith and preserves a temperature of 0', async () => {
    const agent = new OptionsRecordingAgent();
    const response = await processWithOptions(agent, createMessage('user', 'Q'), {
      temperature: 0,
      maxTokens: 32,
    });

    expect(agent.processWithCalls).toBe(1);
    expect(agent.processCalls).toBe(0);
    expect(response.content).toBe('with-options');
    expect(agent.lastOptions?.temperature).toBe(0);
    expect(agent.lastOptions?.maxTokens).toBe(32);
  });

  it('takes the plain path when no options are given', async () => {
    const agent = new OptionsRecordingAgent();
    await processWithOptions(agent, createMessage('user', 'Q'));

    expect(agent.processWithCalls).toBe(0);
    expect(agent.processCalls).toBe(1);
  });

  it('takes the plain path for an options object with nothing set', async () => {
    // An empty options set is indistinguishable from not asking, so an agent must
    // not be handed one just because this helper was used.
    const agent = new OptionsRecordingAgent();
    await processWithOptions(agent, createMessage('user', 'Q'), {});

    expect(agent.processWithCalls).toBe(0);
    expect(agent.processCalls).toBe(1);
  });

  it('still processes when the agent cannot honour options', async () => {
    // The options cannot be applied, but the call must succeed. Callers that need
    // to know whether the options landed check supportsOptions; that is what makes
    // the drop visible rather than silent.
    const agent = new PlainAgent();
    const response = await processWithOptions(agent, createMessage('user', 'Q'), {
      temperature: 0.7,
    });

    expect(agent.processCalls).toBe(1);
    expect(response.content).toBe('Processed: Q');
  });
});
