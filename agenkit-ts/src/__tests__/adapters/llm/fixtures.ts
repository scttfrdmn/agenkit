/**
 * Shared fixtures for LLM adapter tests.
 *
 * Provides mock clients, test data, and helper functions for testing
 * LLM adapters (Anthropic, OpenAI, etc.) without making real API calls.
 */

import { vi } from 'vitest';
import type { Message } from '../../../core/interfaces';

/**
 * Test message fixtures
 */
export function getSimpleTestMessage(): Message {
  return {
    role: 'user',
    content: 'Hello!',
    metadata: {},
  };
}

export function getTestMessages(): Message[] {
  return [
    {
      role: 'system',
      content: 'You are a helpful assistant.',
      metadata: {},
    },
    {
      role: 'user',
      content: 'Hello!',
      metadata: {},
    },
  ];
}

export function getExpectedResponseContent(): string {
  return "Hello! I'm doing well, thank you for asking.";
}

/**
 * Mock Anthropic response
 */
export function getMockAnthropicResponse() {
  return {
    id: 'msg_test123',
    type: 'message',
    role: 'assistant',
    content: [
      {
        type: 'text',
        text: getExpectedResponseContent(),
      },
    ],
    model: 'claude-3-5-sonnet-20241022',
    stop_reason: 'end_turn',
    usage: {
      input_tokens: 10,
      output_tokens: 15,
    },
  };
}

/**
 * Mock Anthropic client
 */
export function createMockAnthropicClient() {
  const mockCreate = vi.fn().mockResolvedValue(getMockAnthropicResponse());

  return {
    messages: {
      create: mockCreate,
    },
  };
}

/**
 * Mock Anthropic streaming response
 */
export function* getMockAnthropicStreamEvents() {
  yield {
    type: 'message_start',
    message: {
      id: 'msg_test123',
      type: 'message',
      role: 'assistant',
      content: [],
      model: 'claude-3-5-sonnet-20241022',
      usage: { input_tokens: 10, output_tokens: 0 },
    },
  };

  yield {
    type: 'content_block_start',
    index: 0,
    content_block: { type: 'text', text: '' },
  };

  const chunks = ['Hello', '! ', "I'm ", 'doing ', 'well.'];
  for (let i = 0; i < chunks.length; i++) {
    yield {
      type: 'content_block_delta',
      index: 0,
      delta: { type: 'text_delta', text: chunks[i] },
    };
  }

  yield {
    type: 'content_block_stop',
    index: 0,
  };

  yield {
    type: 'message_delta',
    delta: { stop_reason: 'end_turn' },
    usage: { output_tokens: 15 },
  };

  yield {
    type: 'message_stop',
  };
}

/**
 * Mock OpenAI response
 */
export function getMockOpenAIResponse() {
  return {
    id: 'chatcmpl-test123',
    object: 'chat.completion',
    created: Date.now(),
    model: 'gpt-4',
    choices: [
      {
        index: 0,
        message: {
          role: 'assistant',
          content: getExpectedResponseContent(),
        },
        finish_reason: 'stop',
      },
    ],
    usage: {
      prompt_tokens: 10,
      completion_tokens: 15,
      total_tokens: 25,
    },
  };
}

/**
 * Mock OpenAI client
 */
export function createMockOpenAIClient() {
  const mockCreate = vi.fn().mockResolvedValue(getMockOpenAIResponse());

  return {
    chat: {
      completions: {
        create: mockCreate,
      },
    },
  };
}

/**
 * Mock OpenAI streaming response
 */
export async function* getMockOpenAIStreamChunks() {
  const chunks = ['Hello', '! ', "I'm ", 'doing ', 'well.'];

  for (let i = 0; i < chunks.length; i++) {
    yield {
      id: 'chatcmpl-test123',
      object: 'chat.completion.chunk',
      created: Date.now(),
      model: 'gpt-4',
      choices: [
        {
          index: 0,
          delta: {
            content: chunks[i],
          },
          finish_reason: null,
        },
      ],
    };
  }

  // Final chunk with finish_reason
  yield {
    id: 'chatcmpl-test123',
    object: 'chat.completion.chunk',
    created: Date.now(),
    model: 'gpt-4',
    choices: [
      {
        index: 0,
        delta: {},
        finish_reason: 'stop',
      },
    ],
  };
}

/**
 * Check if API key is available (for integration tests)
 */
export function getAnthropicApiKey(): string | undefined {
  return process.env.ANTHROPIC_API_KEY;
}

export function getOpenAIApiKey(): string | undefined {
  return process.env.OPENAI_API_KEY;
}

export function getGeminiApiKey(): string | undefined {
  return process.env.GEMINI_API_KEY;
}

/**
 * Check if local Ollama server is available
 */
export async function isOllamaAvailable(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:11434/api/tags', {
      method: 'GET',
      signal: AbortSignal.timeout(1000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
