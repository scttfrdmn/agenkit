/**
 * Tests for OpenAI LLM adapter.
 *
 * Tests both unit tests (with mocked API) and integration tests (with real API).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OpenAIAdapter } from '../../../adapters/openai';
import {
  getSimpleTestMessage,
  getTestMessages,
  getExpectedResponseContent,
  createMockOpenAIClient,
  getMockOpenAIStreamChunks,
  getOpenAIApiKey,
} from './fixtures';

// ============================================
// Unit Tests (Mocked API)
// ============================================

describe('OpenAI Adapter: Unit Tests', () => {
  let adapter: OpenAIAdapter;
  let mockClient: ReturnType<typeof createMockOpenAIClient>;

  beforeEach(() => {
    mockClient = createMockOpenAIClient();
    adapter = new OpenAIAdapter({ apiKey: 'test-key' });
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

  it('should pass temperature and max_tokens options', async () => {
    const message = getSimpleTestMessage();

    // Override adapter config
    (adapter as any).config.temperature = 0.5;
    (adapter as any).config.maxTokens = 100;

    await adapter.complete([message]);

    // Verify mock was called with correct parameters
    expect(mockClient.chat.completions.create).toHaveBeenCalledWith(
      expect.objectContaining({
        temperature: 0.5,
        max_tokens: 100,
      })
    );
  });

  it('should convert user message correctly', async () => {
    const message = getSimpleTestMessage();
    await adapter.complete([message]);

    const callArgs = mockClient.chat.completions.create.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(1);
    expect(callArgs.messages[0].role).toBe('user');
    expect(callArgs.messages[0].content).toBe('Hello!');
  });

  it('should include system message', async () => {
    const messages = getTestMessages();
    await adapter.complete(messages);

    const callArgs = mockClient.chat.completions.create.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(2);
    expect(callArgs.messages[0].role).toBe('system');
    expect(callArgs.messages[0].content).toBe('You are a helpful assistant.');
    expect(callArgs.messages[1].role).toBe('user');
  });

  it('should handle assistant role correctly', async () => {
    const messages = [
      { role: 'user' as const, content: 'Hi', metadata: {} },
      { role: 'assistant' as const, content: 'Hello', metadata: {} },
      { role: 'user' as const, content: 'How are you?', metadata: {} },
    ];

    await adapter.complete(messages);

    const callArgs = mockClient.chat.completions.create.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(3);
    expect(callArgs.messages[0].role).toBe('user');
    expect(callArgs.messages[1].role).toBe('assistant');
    expect(callArgs.messages[2].role).toBe('user');
  });

  it('should return correct model name', () => {
    const customAdapter = new OpenAIAdapter({
      apiKey: 'test-key',
      model: 'gpt-4o',
    });
    expect(customAdapter.name).toBe('openai-gpt-4o');
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

    expect(response.metadata.model).toBe('gpt-4');
    expect(response.metadata.finish_reason).toBe('stop');
    expect(response.metadata.id).toBe('chatcmpl-test123');
  });

  it('should handle streaming chunks', async () => {
    // Mock streaming response
    const streamMock = vi.fn().mockReturnValue(getMockOpenAIStreamChunks());
    mockClient.chat.completions.create = streamMock;

    const message = getSimpleTestMessage();
    const chunks: string[] = [];

    for await (const chunk of adapter.completeStream([message])) {
      chunks.push(chunk.content);
      expect(chunk.role).toBe('assistant');
      expect(chunk.metadata.chunk).toBe(true);
    }

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.join('')).toBe("Hello! I'm doing well.");
  });

  it('should support custom base URL', () => {
    const customAdapter = new OpenAIAdapter({
      apiKey: 'test-key',
      baseURL: 'https://custom.api.com/v1',
    });

    // Verify client was created with custom baseURL
    expect((customAdapter as any).client.baseURL).toBe('https://custom.api.com/v1');
  });

  it('should support frequency and presence penalties', async () => {
    const message = getSimpleTestMessage();

    // Override adapter config
    (adapter as any).config.frequencyPenalty = 0.5;
    (adapter as any).config.presencePenalty = 0.3;

    await adapter.complete([message]);

    expect(mockClient.chat.completions.create).toHaveBeenCalledWith(
      expect.objectContaining({
        frequency_penalty: 0.5,
        presence_penalty: 0.3,
      })
    );
  });
});

// ============================================
// Integration Tests (Real API)
// ============================================

describe('OpenAI Adapter: Integration Tests', () => {
  it.skipIf(!getOpenAIApiKey())('should work with real API', async () => {
    const adapter = new OpenAIAdapter({
      apiKey: getOpenAIApiKey(),
      model: 'gpt-3.5-turbo',
      maxTokens: 50,
    });

    const message = getSimpleTestMessage();
    const response = await adapter.complete([message]);

    expect(response.role).toBe('assistant');
    expect(response.content.length).toBeGreaterThan(0);
    expect(response.metadata.usage.prompt_tokens).toBeGreaterThan(0);
    expect(response.metadata.usage.completion_tokens).toBeGreaterThan(0);
  });

  it.skipIf(!getOpenAIApiKey())('should stream with real API', async () => {
    const adapter = new OpenAIAdapter({
      apiKey: getOpenAIApiKey(),
      model: 'gpt-3.5-turbo',
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

  it.skipIf(!getOpenAIApiKey())('should handle system message with real API', async () => {
    const adapter = new OpenAIAdapter({
      apiKey: getOpenAIApiKey(),
      model: 'gpt-3.5-turbo',
      maxTokens: 50,
    });

    const messages = getTestMessages();
    const response = await adapter.complete(messages);

    expect(response.role).toBe('assistant');
    expect(response.content.length).toBeGreaterThan(0);
  });
});
