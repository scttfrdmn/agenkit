/**
 * Tests for OpenAI-Compatible LLM adapter.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { OpenAICompatibleAgent } from '../openai-compatible';
import { Message } from '../../core/interfaces';

// Mock the OpenAI SDK
vi.mock('openai', () => {
  class MockOpenAI {
    chat = {
      completions: {
        create: vi.fn(),
      },
    };
  }
  return {
    default: MockOpenAI,
  };
});

describe('OpenAICompatibleAgent', () => {
  describe('Initialization', () => {
    it('should initialize with required parameters', () => {
      const agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
      });

      expect(agent.name).toBe('vllm');
      expect(agent.capabilities).toContain('openai-compatible');
      expect(agent.capabilities).toContain('vllm');
      expect(agent.capabilities).toContain('chat');
      expect(agent.capabilities).toContain('streaming');
    });

    it('should initialize without provider', () => {
      const agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
      });

      expect(agent.name).toBe('openai_compatible');
      expect(agent.capabilities).toContain('openai_compatible');
    });

    it('should use custom name if provided', () => {
      const agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
        name: 'my-custom-agent',
      });

      expect(agent.name).toBe('my-custom-agent');
    });

    it('should initialize with all optional parameters', () => {
      const agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
        apiKey: 'test-key',
        temperature: 0.5,
        maxTokens: 2048,
        topP: 0.95,
        timeout: 30000,
      });

      expect(agent.name).toBe('vllm');
    });
  });

  describe('Different Providers', () => {
    const providers = [
      { name: 'vLLM', baseURL: 'http://localhost:8000/v1', provider: 'vllm' },
      {
        name: 'llama.cpp',
        baseURL: 'http://localhost:8080/v1',
        provider: 'llamacpp',
      },
      {
        name: 'SGLang',
        baseURL: 'http://localhost:30000/v1',
        provider: 'sglang',
      },
      {
        name: 'TensorRT-LLM',
        baseURL: 'http://localhost:8001/v1',
        provider: 'tensorrt',
      },
      {
        name: 'OpenLLM',
        baseURL: 'http://localhost:3000/v1',
        provider: 'openllm',
      },
      {
        name: 'MLC LLM',
        baseURL: 'http://localhost:8088/v1',
        provider: 'mlc',
      },
      {
        name: 'TGI',
        baseURL: 'http://localhost:8080/v1',
        provider: 'tgi',
      },
      {
        name: 'Inferflow',
        baseURL: 'http://localhost:8000/v1',
        provider: 'inferflow',
      },
    ];

    providers.forEach((p) => {
      it(`should initialize for ${p.name}`, () => {
        const agent = new OpenAICompatibleAgent({
          baseURL: p.baseURL,
          model: 'test-model',
          provider: p.provider,
        });

        expect(agent.name).toBe(p.provider);
        expect(agent.capabilities).toContain(p.provider);
      });
    });
  });

  describe('Message Processing', () => {
    let agent: OpenAICompatibleAgent;

    beforeEach(() => {
      agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
      });
    });

    it('should process a simple message', async () => {
      // Mock the API response
      const mockCreate = vi.fn().mockResolvedValue({
        id: 'test-id-123',
        model: 'llama-2-7b',
        choices: [
          {
            message: {
              role: 'assistant',
              content: 'Hello! How can I help you?',
            },
            finish_reason: 'stop',
          },
        ],
        usage: {
          prompt_tokens: 10,
          completion_tokens: 8,
          total_tokens: 18,
        },
      });

      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: 'Hello',
      };

      const response = await agent.process(message);

      expect(response.role).toBe('assistant');
      expect(response.content).toBe('Hello! How can I help you?');
      expect(response.metadata?.model).toBe('llama-2-7b');
      expect(response.metadata?.provider).toBe('vllm');
      expect(response.metadata?.baseURL).toBe('http://localhost:8000/v1');
      expect(response.metadata?.usage).toEqual({
        prompt_tokens: 10,
        completion_tokens: 8,
        total_tokens: 18,
      });

      // Verify API was called correctly
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          model: 'llama-2-7b',
          messages: [{ role: 'user', content: 'Hello' }],
          stream: false,
        }),
      );
    });

    it('should process message with custom parameters', async () => {
      const mockCreate = vi.fn().mockResolvedValue({
        id: 'test-id-123',
        model: 'llama-2-7b',
        choices: [
          {
            message: {
              role: 'assistant',
              content: 'Response',
            },
            finish_reason: 'stop',
          },
        ],
        usage: {
          prompt_tokens: 5,
          completion_tokens: 1,
          total_tokens: 6,
        },
      });

      agent.getClient().chat.completions.create = mockCreate;

      const customAgent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
        temperature: 0.5,
        maxTokens: 100,
        topP: 0.9,
      });

      customAgent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: 'Test',
      };

      await customAgent.process(message);

      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          temperature: 0.5,
          max_tokens: 100,
          top_p: 0.9,
        }),
      );
    });

    it('should handle system messages', async () => {
      const mockCreate = vi.fn().mockResolvedValue({
        id: 'test-id-123',
        model: 'llama-2-7b',
        choices: [
          {
            message: {
              role: 'assistant',
              content: 'Understood',
            },
            finish_reason: 'stop',
          },
        ],
        usage: {
          prompt_tokens: 10,
          completion_tokens: 2,
          total_tokens: 12,
        },
      });

      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'system',
        content: 'You are a helpful assistant',
      };

      await agent.process(message);

      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: [
            { role: 'system', content: 'You are a helpful assistant' },
          ],
        }),
      );
    });

    it('should handle agent role conversion', async () => {
      const mockCreate = vi.fn().mockResolvedValue({
        id: 'test-id-123',
        model: 'llama-2-7b',
        choices: [
          {
            message: {
              role: 'assistant',
              content: 'Response',
            },
            finish_reason: 'stop',
          },
        ],
        usage: {
          prompt_tokens: 5,
          completion_tokens: 1,
          total_tokens: 6,
        },
      });

      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'agent',
        content: 'Previous response',
      };

      await agent.process(message);

      // agent role should be converted to assistant
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: [{ role: 'assistant', content: 'Previous response' }],
        }),
      );
    });

    it('should handle non-string content', async () => {
      const mockCreate = vi.fn().mockResolvedValue({
        id: 'test-id-123',
        model: 'llama-2-7b',
        choices: [
          {
            message: {
              role: 'assistant',
              content: 'Response',
            },
            finish_reason: 'stop',
          },
        ],
        usage: {
          prompt_tokens: 10,
          completion_tokens: 1,
          total_tokens: 11,
        },
      });

      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: { type: 'complex', data: [1, 2, 3] },
      };

      await agent.process(message);

      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: [
            {
              role: 'user',
              content: JSON.stringify({ type: 'complex', data: [1, 2, 3] }),
            },
          ],
        }),
      );
    });

    it('should throw error when no choices returned', async () => {
      const mockCreate = vi.fn().mockResolvedValue({
        id: 'test-id-123',
        model: 'llama-2-7b',
        choices: [],
        usage: {
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
        },
      });

      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: 'Test',
      };

      await expect(agent.process(message)).rejects.toThrow(
        'Service returned no choices',
      );
    });

    it('should handle API errors', async () => {
      const mockCreate = vi
        .fn()
        .mockRejectedValue(new Error('Connection refused'));

      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: 'Test',
      };

      await expect(agent.process(message)).rejects.toThrow(
        'Connection refused',
      );
    });
  });

  describe('Streaming', () => {
    let agent: OpenAICompatibleAgent;

    beforeEach(() => {
      agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
      });
    });

    it('should stream response chunks', async () => {
      // Mock stream response
      const mockStream = {
        async *[Symbol.asyncIterator]() {
          yield {
            id: 'chunk-1',
            model: 'llama-2-7b',
            choices: [
              {
                delta: { content: 'Hello' },
                finish_reason: null,
              },
            ],
          };
          yield {
            id: 'chunk-2',
            model: 'llama-2-7b',
            choices: [
              {
                delta: { content: ' world' },
                finish_reason: null,
              },
            ],
          };
          yield {
            id: 'chunk-3',
            model: 'llama-2-7b',
            choices: [
              {
                delta: { content: '!' },
                finish_reason: 'stop',
              },
            ],
          };
        },
      };

      const mockCreate = vi.fn().mockResolvedValue(mockStream);
      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: 'Test streaming',
      };

      const chunks: Message[] = [];
      for await (const chunk of agent.processStream(message)) {
        chunks.push(chunk);
      }

      expect(chunks).toHaveLength(3);
      expect(chunks[0].content).toBe('Hello');
      expect(chunks[1].content).toBe(' world');
      expect(chunks[2].content).toBe('!');

      // All chunks should have streaming metadata
      chunks.forEach((chunk) => {
        expect(chunk.metadata?.streaming).toBe(true);
        expect(chunk.metadata?.provider).toBe('vllm');
        expect(chunk.metadata?.model).toBe('llama-2-7b');
      });

      // Verify API was called with stream: true
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          stream: true,
        }),
      );
    });

    it('should handle empty content in stream chunks', async () => {
      const mockStream = {
        async *[Symbol.asyncIterator]() {
          yield {
            id: 'chunk-1',
            model: 'llama-2-7b',
            choices: [
              {
                delta: {},
                finish_reason: null,
              },
            ],
          };
          yield {
            id: 'chunk-2',
            model: 'llama-2-7b',
            choices: [
              {
                delta: { content: 'Hello' },
                finish_reason: null,
              },
            ],
          };
        },
      };

      const mockCreate = vi.fn().mockResolvedValue(mockStream);
      agent.getClient().chat.completions.create = mockCreate;

      const message: Message = {
        role: 'user',
        content: 'Test',
      };

      const chunks: Message[] = [];
      for await (const chunk of agent.processStream(message)) {
        chunks.push(chunk);
      }

      // Should only yield chunk with content
      expect(chunks).toHaveLength(1);
      expect(chunks[0].content).toBe('Hello');
    });
  });

  describe('Client Access', () => {
    it('should provide access to underlying client', () => {
      const agent = new OpenAICompatibleAgent({
        baseURL: 'http://localhost:8000/v1',
        model: 'llama-2-7b',
        provider: 'vllm',
      });

      const client = agent.getClient();
      expect(client).toBeDefined();
      expect(client.chat).toBeDefined();
      expect(client.chat.completions).toBeDefined();
    });
  });
});
