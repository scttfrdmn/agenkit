/**
 * Tests for Anthropic LLM adapter.
 *
 * Tests both unit tests (with mocked API) and integration tests (with real API).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnthropicAdapter } from '../../../adapters/anthropic';
import {
  getSimpleTestMessage,
  getTestMessages,
  getExpectedResponseContent,
  createMockAnthropicClient,
  getMockAnthropicStreamEvents,
  getAnthropicApiKey,
} from './fixtures';

// ============================================
// Unit Tests (Mocked API)
// ============================================

describe('Anthropic Adapter: Unit Tests', () => {
  let adapter: AnthropicAdapter;
  let mockClient: ReturnType<typeof createMockAnthropicClient>;

  beforeEach(() => {
    mockClient = createMockAnthropicClient();
    adapter = new AnthropicAdapter({ apiKey: 'test-key' });
    // Replace internal client with mock
    (adapter as any).client = mockClient;
  });

  it('should complete successfully with mocked API', async () => {
    const message = getSimpleTestMessage();
    const response = await adapter.complete([message]);

    expect(response.role).toBe('assistant');
    expect(response.content).toBe(getExpectedResponseContent());
    expect(response.metadata).toHaveProperty('usage');
    expect(response.metadata.usage.prompt_tokens).toBe(10);
    expect(response.metadata.usage.completion_tokens).toBe(15);
    expect(response.metadata.usage.total_tokens).toBe(25);
  });

  it('should pass max_tokens option', async () => {
    const message = getSimpleTestMessage();

    // Override adapter config
    (adapter as any).config.maxTokens = 100;

    await adapter.complete([message]);

    // Verify mock was called with correct parameters
    expect(mockClient.messages.create).toHaveBeenCalledWith(
      expect.objectContaining({
        max_tokens: 100,
      })
    );
  });

  // API version 2026-10-21 returns 400 for any of these, on every model (#1066)
  const SAMPLING_PARAMS = ['temperature', 'top_p', 'top_k'];

  it('should never send sampling parameters, even when configured', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const configured = new AnthropicAdapter({
      apiKey: 'test-key',
      temperature: 0.5,
      topP: 0.9,
      topK: 5,
    });
    (configured as any).client = mockClient;

    await configured.complete([getSimpleTestMessage()]);
    await configured.process(getSimpleTestMessage());

    expect(warn).toHaveBeenCalledTimes(1);
    expect(warn.mock.calls[0][0]).toContain('ignores temperature, topP, topK');
    for (const [params] of mockClient.messages.create.mock.calls) {
      for (const key of SAMPLING_PARAMS) expect(params).not.toHaveProperty(key);
    }
    warn.mockRestore();
  });

  it('should warn on per-call sampling options and not send them', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});

    await adapter.processWith(getSimpleTestMessage(), {
      temperature: 0.2,
      topP: 0.5,
      stop: ['END'],
    });

    expect(warn).toHaveBeenCalledTimes(1);
    expect(warn.mock.calls[0][0]).toContain('ignores temperature, topP');
    const params = mockClient.messages.create.mock.calls[0][0];
    for (const key of SAMPLING_PARAMS) expect(params).not.toHaveProperty(key);
    expect(params.stop_sequences).toEqual(['END']);
    warn.mockRestore();
  });

  it('should not warn when no sampling options are set', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const plain = new AnthropicAdapter({ apiKey: 'test-key' });
    (plain as any).client = mockClient;

    await plain.processWith(getSimpleTestMessage(), { maxTokens: 50 });

    expect(warn).not.toHaveBeenCalled();
    warn.mockRestore();
  });

  it('should convert user message correctly', async () => {
    const message = getSimpleTestMessage();
    await adapter.complete([message]);

    const callArgs = mockClient.messages.create.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(1);
    expect(callArgs.messages[0].role).toBe('user');
    expect(callArgs.messages[0].content).toBe('Hello!');
  });

  it('should extract system message', async () => {
    const messages = getTestMessages();
    await adapter.complete(messages);

    const callArgs = mockClient.messages.create.mock.calls[0][0];
    expect(callArgs.system).toBe('You are a helpful assistant.');
    // Only user message in messages array
    expect(callArgs.messages).toHaveLength(1);
    expect(callArgs.messages[0].role).toBe('user');
  });

  it('should handle assistant role correctly', async () => {
    const messages = [
      { role: 'user' as const, content: 'Hi', metadata: {} },
      { role: 'assistant' as const, content: 'Hello', metadata: {} },
      { role: 'user' as const, content: 'How are you?', metadata: {} },
    ];

    await adapter.complete(messages);

    const callArgs = mockClient.messages.create.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(3);
    expect(callArgs.messages[0].role).toBe('user');
    expect(callArgs.messages[1].role).toBe('assistant');
    expect(callArgs.messages[2].role).toBe('user');
  });

  it('should return correct model name', () => {
    const customAdapter = new AnthropicAdapter({
      apiKey: 'test-key',
      model: 'claude-3-opus-20240229',
    });
    expect(customAdapter.name).toBe('anthropic-claude-3-opus-20240229');
  });

  it('should include correct capabilities', () => {
    expect(adapter.capabilities).toContain('completion');
    expect(adapter.capabilities).toContain('streaming');
    expect(adapter.capabilities).toContain('chat');
  });

  it('should process single message via process()', async () => {
    const message = getSimpleTestMessage();
    const response = await adapter.process(message);

    expect(response.role).toBe('assistant');
    expect(response.content).toBe(getExpectedResponseContent());
  });

  it('should include model metadata', async () => {
    const message = getSimpleTestMessage();
    const response = await adapter.complete([message]);

    expect(response.metadata.model).toBe('claude-sonnet-5');
    expect(response.metadata.stop_reason).toBe('end_turn');
    expect(response.metadata.id).toBe('msg_test123');
  });

  it('should translate stop to stop_sequences via processWith (#818)', async () => {
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { stop: ['END', 'STOP'] });

    const callArgs = mockClient.messages.create.mock.calls[0][0];
    expect(callArgs.stop_sequences).toEqual(['END', 'STOP']);
    expect(callArgs.stop).toBeUndefined();
  });

  it('should warn and drop unsupported seed via processWith (#818)', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const message = getSimpleTestMessage();

    await adapter.processWith(message, { seed: 918273645 });

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("does not support 'seed'"));
    const callArgs = mockClient.messages.create.mock.calls[0][0];
    expect(callArgs.seed).toBeUndefined();

    warnSpy.mockRestore();
  });

  it('should handle streaming chunks', async () => {
    // Mock streaming response.
    //
    // The generator is created once, outside next(). Creating it *inside* next()
    // — as this previously did — returns the first event on every call and never
    // reports done, so the `for await` below spun forever and the whole file
    // hung. It never failed, which is why nothing noticed: CI runs
    // `timeout 300 npm test || true`, so the hang looked like a slow 5-minute
    // suite rather than a broken test (#658).
    const streamMock = vi.fn().mockReturnValue({
      [Symbol.asyncIterator]: () => {
        const gen = getMockAnthropicStreamEvents();
        return {
          async next() {
            return gen.next();
          },
        };
      },
    });

    mockClient.messages.create = streamMock;

    const message = getSimpleTestMessage();
    const chunks: string[] = [];

    for await (const chunk of adapter.completeStream([message])) {
      chunks.push(chunk.content);
      expect(chunk.role).toBe('assistant');
      expect(chunk.metadata.chunk).toBe(true);
    }

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.join('')).toBe('Hello! I\'m doing well.');
  });
});

// ============================================
// Integration Tests (Real API)
// ============================================

describe('Anthropic Adapter: Integration Tests', () => {
  it.skipIf(!getAnthropicApiKey())('should work with real API', async () => {
    const adapter = new AnthropicAdapter({
      apiKey: getAnthropicApiKey(),
      model: 'claude-3-haiku-20240307',
      maxTokens: 50,
    });

    const message = getSimpleTestMessage();
    const response = await adapter.complete([message]);

    expect(response.role).toBe('assistant');
    expect(response.content.length).toBeGreaterThan(0);
    expect(response.metadata.usage.prompt_tokens).toBeGreaterThan(0);
    expect(response.metadata.usage.completion_tokens).toBeGreaterThan(0);
  });

  it.skipIf(!getAnthropicApiKey())('should stream with real API', async () => {
    const adapter = new AnthropicAdapter({
      apiKey: getAnthropicApiKey(),
      model: 'claude-3-haiku-20240307',
      maxTokens: 50,
    });

    const message = getSimpleTestMessage();
    const chunks: string[] = [];

    for await (const chunk of adapter.completeStream([message])) {
      expect(chunk.role).toBe('assistant');
      expect(chunk.metadata.chunk).toBe(true);
      chunks.push(chunk.content);
    }

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.join('').length).toBeGreaterThan(0);
  });

  it.skipIf(!getAnthropicApiKey())('should handle system message with real API', async () => {
    const adapter = new AnthropicAdapter({
      apiKey: getAnthropicApiKey(),
      model: 'claude-3-haiku-20240307',
      maxTokens: 50,
    });

    const messages = getTestMessages();
    const response = await adapter.complete(messages);

    expect(response.role).toBe('assistant');
    expect(response.content.length).toBeGreaterThan(0);
  });
});
