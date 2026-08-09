/**
 * LiteLLM proxy adapter for universal LLM access.
 *
 * Provides integration with LiteLLM, a universal LLM gateway that offers
 * an OpenAI-compatible API for 100+ LLM providers. Supports both completion
 * and streaming modes.
 *
 * @example
 * ```typescript
 * import { LiteLLMAdapter } from './adapters/litellm';
 *
 * const adapter = new LiteLLMAdapter({
 *   baseUrl: 'http://localhost:4000',
 *   model: 'gpt-4',
 *   apiKey: 'sk-litellm-...',
 * });
 *
 * const response = await adapter.process({
 *   role: 'user',
 *   content: 'Hello, LiteLLM!',
 * });
 * console.log(response.content);
 * ```
 *
 * Supported providers through LiteLLM:
 * - OpenAI (gpt-4, gpt-3.5-turbo)
 * - Anthropic (claude-3-5-sonnet-20241022)
 * - AWS Bedrock (bedrock/anthropic.claude-v2)
 * - Google Gemini (gemini/gemini-pro)
 * - Azure OpenAI (azure/gpt-4)
 * - Cohere (command-r-plus)
 * - Local models (ollama/llama2, ollama/mistral)
 * - And 100+ more!
 */

import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';
import type { CallOptions } from '../core/call-options';

/**
 * Configuration for LiteLLM adapter.
 */
export interface LiteLLMConfig {
  /** LiteLLM proxy base URL (default: 'http://localhost:4000') */
  baseUrl?: string;

  /** Model identifier in LiteLLM format (e.g., 'gpt-4', 'claude-3-5-sonnet-20241022', 'bedrock/anthropic.claude-v2') */
  model?: string;

  /** API key for LiteLLM proxy authentication (optional) */
  apiKey?: string;

  /** Temperature for sampling (0.0 - 2.0) */
  temperature?: number;

  /** Maximum tokens to generate */
  maxTokens?: number;

  /** Top-p sampling parameter */
  topP?: number;

  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Message format for LiteLLM API (OpenAI-compatible).
 */
interface LiteLLMMessage {
  role: string;
  content: string;
}

/**
 * Request format for LiteLLM chat API.
 */
interface LiteLLMRequest {
  model: string;
  messages: LiteLLMMessage[];
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  stream?: boolean;
  /** Provider-side sampling seed. LiteLLM forwards this to providers that support it (#818). */
  seed?: number;
  /** Stop sequences. LiteLLM forwards this to providers that support it (#818). */
  stop?: string[];
}

/**
 * Response format from LiteLLM chat API.
 */
interface LiteLLMResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: LiteLLMChoice[];
  usage: LiteLLMUsage;
}

/**
 * Choice in LiteLLM response.
 */
interface LiteLLMChoice {
  index: number;
  message: LiteLLMMessage;
  finish_reason: string;
}

/**
 * Token usage information.
 */
interface LiteLLMUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/**
 * Streaming chunk from LiteLLM.
 */
interface LiteLLMStreamChunk {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: LiteLLMStreamChoice[];
}

/**
 * Streaming choice.
 */
interface LiteLLMStreamChoice {
  index: number;
  delta: LiteLLMDelta;
  finish_reason?: string | null;
}

/**
 * Delta in streaming response.
 */
interface LiteLLMDelta {
  role?: string;
  content?: string;
}

/**
 * LiteLLM adapter implementing the Agent interface.
 *
 * Features:
 * - Support for 100+ LLM providers through LiteLLM proxy
 * - OpenAI-compatible API
 * - Streaming and non-streaming completion
 * - Full metadata tracking (tokens, finish reason, model)
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Automatic message format conversion
 * - API key authentication support
 */
export class LiteLLMAdapter implements Agent {
  private config: Required<Omit<LiteLLMConfig, 'apiKey'>> & { apiKey?: string };

  /**
   * Creates a new LiteLLM adapter.
   *
   * @param config - Configuration options
   */
  constructor(config: LiteLLMConfig = {}) {
    this.config = {
      baseUrl: config.baseUrl || 'http://localhost:4000',
      model: config.model || 'gpt-3.5-turbo',
      apiKey: config.apiKey,
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens ?? 1024,
      topP: config.topP ?? 1.0,
      timeout: config.timeout ?? 60000,
    };
  }

  /**
   * Returns the agent name.
   */
  get name(): string {
    return `litellm-${this.config.model}`;
  }

  /**
   * Returns agent capabilities.
   */
  get capabilities(): string[] {
    return ['completion', 'streaming', 'chat', 'universal-gateway'];
  }

  /**
   * Processes a message and returns a response.
   *
   * @param message - Input message
   * @returns Promise resolving to response message
   */
  async process(message: Message): Promise<Message> {
    return this.processWith(message, {});
  }

  /**
   * Processes a message with per-call inference options (#818).
   *
   * `seed` and `stop` map onto LiteLLM's OpenAI-compatible request body
   * unchanged — LiteLLM normalizes both to whatever the routed provider
   * supports, and forwards them as-is when the provider does not.
   *
   * @param message - Input message
   * @param options - Per-call inference options
   * @returns Promise resolving to response message
   */
  async processWith(message: Message, options: CallOptions): Promise<Message> {
    validateMessage(message);

    const messages = this.convertMessages([message]);

    const request: LiteLLMRequest = {
      model: this.config.model,
      messages,
      temperature: options.temperature ?? this.config.temperature,
      max_tokens: options.maxTokens ?? this.config.maxTokens,
      top_p: options.topP ?? this.config.topP,
      ...(options.seed !== undefined ? { seed: options.seed } : {}),
      ...(options.stop !== undefined ? { stop: options.stop } : {}),
    };

    const response = await this.makeRequest(request);

    if (!response.choices || response.choices.length === 0) {
      throw new Error('LiteLLM returned no choices');
    }

    const choice = response.choices[0];

    return createMessage({
      role: 'assistant',
      content: choice.message.content,
      metadata: {
        model: response.model,
        usage: {
          prompt_tokens: response.usage.prompt_tokens,
          completion_tokens: response.usage.completion_tokens,
          total_tokens: response.usage.total_tokens,
        },
        finish_reason: choice.finish_reason,
        id: response.id,
      },
    });
  }

  /**
   * Processes a message and streams the response.
   *
   * @param message - Input message
   * @returns Async generator yielding response chunks
   */
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    validateMessage(message);

    const messages = this.convertMessages([message]);

    const request: LiteLLMRequest = {
      model: this.config.model,
      messages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
      stream: true,
    };

    yield* this.makeStreamRequest(request);
  }

  /**
   * Completes a multi-turn conversation.
   *
   * @param messages - Array of conversation messages
   * @returns Promise resolving to response message
   */
  async complete(messages: Message[]): Promise<Message> {
    messages.forEach(validateMessage);

    const litellmMessages = this.convertMessages(messages);

    const request: LiteLLMRequest = {
      model: this.config.model,
      messages: litellmMessages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
    };

    const response = await this.makeRequest(request);

    if (!response.choices || response.choices.length === 0) {
      throw new Error('LiteLLM returned no choices');
    }

    const choice = response.choices[0];

    return createMessage({
      role: 'assistant',
      content: choice.message.content,
      metadata: {
        model: response.model,
        usage: {
          prompt_tokens: response.usage.prompt_tokens,
          completion_tokens: response.usage.completion_tokens,
          total_tokens: response.usage.total_tokens,
        },
        finish_reason: choice.finish_reason,
        id: response.id,
      },
    });
  }

  /**
   * Streams a multi-turn conversation.
   *
   * @param messages - Array of conversation messages
   * @returns Async generator yielding response chunks
   */
  async *completeStream(messages: Message[]): AsyncGenerator<Message, void, undefined> {
    messages.forEach(validateMessage);

    const litellmMessages = this.convertMessages(messages);

    const request: LiteLLMRequest = {
      model: this.config.model,
      messages: litellmMessages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
      stream: true,
    };

    yield* this.makeStreamRequest(request);
  }

  /**
   * Converts AgentKit messages to LiteLLM format.
   *
   * @param messages - AgentKit messages
   * @returns LiteLLM-formatted messages
   */
  private convertMessages(messages: Message[]): LiteLLMMessage[] {
    return messages.map((msg) => {
      let role: string;
      switch (msg.role) {
        case 'system':
        case 'user':
          role = msg.role;
          break;
        case 'assistant':
        case 'agent':
        default:
          role = 'assistant';
          break;
      }

      const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

      return {
        role,
        content,
      };
    });
  }

  /**
   * Makes an HTTP request to LiteLLM proxy.
   *
   * @param request - Request payload
   * @returns Response from LiteLLM
   */
  private async makeRequest(request: LiteLLMRequest): Promise<LiteLLMResponse> {
    const url = `${this.config.baseUrl}/chat/completions`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`LiteLLM API error (${response.status}): ${errorText}`);
      }

      return (await response.json()) as LiteLLMResponse;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error(`LiteLLM request timeout after ${this.config.timeout}ms`);
        }
        throw new Error(`LiteLLM request failed: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Makes a streaming HTTP request to LiteLLM proxy.
   *
   * @param request - Request payload
   * @returns Async generator yielding response chunks
   */
  private async *makeStreamRequest(request: LiteLLMRequest): AsyncGenerator<Message, void, undefined> {
    const url = `${this.config.baseUrl}/chat/completions`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`LiteLLM API error (${response.status}): ${errorText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) {
            continue;
          }

          const data = trimmed.substring(6);

          if (data === '[DONE]') {
            return;
          }

          try {
            const chunk: LiteLLMStreamChunk = JSON.parse(data);

            if (chunk.choices && chunk.choices.length > 0) {
              const choice = chunk.choices[0];
              if (choice.delta?.content) {
                yield createMessage({
                  role: 'assistant',
                  content: choice.delta.content,
                  metadata: {
                    chunk: true,
                    model: this.config.model,
                  },
                });
              }
            }
          } catch {
            continue;
          }
        }
      }
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error(`LiteLLM stream timeout after ${this.config.timeout}ms`);
        }
        throw new Error(`LiteLLM stream failed: ${error.message}`);
      }
      throw error;
    }
  }
}
