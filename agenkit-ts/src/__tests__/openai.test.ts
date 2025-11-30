/**
 * Tests for OpenAI adapter
 */

import { describe, it, expect } from 'vitest';
import { OpenAIAdapter } from '../adapters/openai';
import { createMessage } from '../core/interfaces';

describe('OpenAIAdapter', () => {
  describe('initialization', () => {
    it('should create with default config', () => {
      const adapter = new OpenAIAdapter({ apiKey: 'test-key' });
      expect(adapter.name()).toBe('openai-gpt-4-turbo');
    });

    it('should create with custom model', () => {
      const adapter = new OpenAIAdapter({
        apiKey: 'test-key',
        model: 'gpt-4o',
      });
      expect(adapter.name()).toBe('openai-gpt-4o');
    });

    it('should have correct capabilities', () => {
      const adapter = new OpenAIAdapter({ apiKey: 'test-key' });
      const caps = adapter.capabilities();
      expect(caps).toContain('completion');
      expect(caps).toContain('streaming');
      expect(caps).toContain('chat');
    });
  });

  describe('name', () => {
    it('should return agent name with model', () => {
      const adapter = new OpenAIAdapter({
        apiKey: 'test-key',
        model: 'gpt-4-turbo',
      });
      expect(adapter.name()).toBe('openai-gpt-4-turbo');
    });
  });

  describe('configuration', () => {
    it('should use custom temperature', () => {
      const adapter = new OpenAIAdapter({
        apiKey: 'test-key',
        temperature: 0.5,
      });
      expect(adapter.name()).toBe('openai-gpt-4-turbo');
    });

    it('should use custom maxTokens', () => {
      const adapter = new OpenAIAdapter({
        apiKey: 'test-key',
        maxTokens: 2048,
      });
      expect(adapter.name()).toBe('openai-gpt-4-turbo');
    });

    it('should use environment variable for API key', () => {
      const oldKey = process.env.OPENAI_API_KEY;
      process.env.OPENAI_API_KEY = 'env-test-key';

      const adapter = new OpenAIAdapter();
      expect(adapter.name()).toBe('openai-gpt-4-turbo');

      if (oldKey) {
        process.env.OPENAI_API_KEY = oldKey;
      } else {
        delete process.env.OPENAI_API_KEY;
      }
    });
  });

  describe('message processing', () => {
    it('should handle user messages', () => {
      const adapter = new OpenAIAdapter({ apiKey: 'test-key' });
      const message = createMessage({
        role: 'user',
        content: 'Hello, how are you?',
      });

      expect(message.role).toBe('user');
      expect(message.content).toBe('Hello, how are you?');
      expect(message.timestamp).toBeDefined();
    });

    it('should validate message format', () => {
      const adapter = new OpenAIAdapter({ apiKey: 'test-key' });
      const message = createMessage({
        role: 'user',
        content: 'Test message',
      });

      expect(message.role).toBe('user');
      expect(typeof message.content).toBe('string');
    });
  });

  // Integration tests that require actual API key
  describe.skipIf(!process.env.OPENAI_API_KEY)('integration tests', () => {
    it('should process a message with real API', async () => {
      const adapter = new OpenAIAdapter({
        model: 'gpt-4-turbo',
        temperature: 0.7,
        maxTokens: 100,
      });

      const message = createMessage({
        role: 'user',
        content: 'Say "Hello, World!" and nothing else.',
      });

      const response = await adapter.process(message);

      expect(response.role).toBe('assistant');
      expect(typeof response.content).toBe('string');
      expect(response.content).toBeTruthy();
      expect(response.metadata).toBeDefined();
      expect(response.metadata?.model).toBeTruthy();
      expect(response.metadata?.usage).toBeDefined();
    }, 30000);

    it('should stream responses with real API', async () => {
      const adapter = new OpenAIAdapter({
        model: 'gpt-4-turbo',
        temperature: 0.7,
        maxTokens: 50,
      });

      const message = createMessage({
        role: 'user',
        content: 'Count to 3.',
      });

      const chunks: string[] = [];
      for await (const chunk of adapter.processStream!(message)) {
        expect(chunk.role).toBe('assistant');
        expect(typeof chunk.content).toBe('string');
        chunks.push(chunk.content as string);
      }

      expect(chunks.length).toBeGreaterThan(0);
      const fullResponse = chunks.join('');
      expect(fullResponse.length).toBeGreaterThan(0);
    }, 30000);

    it('should handle multi-turn conversation', async () => {
      const adapter = new OpenAIAdapter({
        model: 'gpt-4-turbo',
        temperature: 0.7,
        maxTokens: 100,
      });

      const conversation = [
        createMessage({ role: 'user', content: 'My name is Alice.' }),
      ];

      const response1 = await adapter.complete!(conversation);
      expect(response1.role).toBe('assistant');

      conversation.push(
        createMessage({ role: 'assistant', content: response1.content as string }),
      );
      conversation.push(createMessage({ role: 'user', content: 'What is my name?' }));

      const response2 = await adapter.complete!(conversation);
      expect(response2.role).toBe('assistant');
      expect(typeof response2.content).toBe('string');
    }, 30000);
  });
});
