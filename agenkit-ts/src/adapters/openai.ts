/**
 * OpenAI LLM adapter for GPT models.
 *
 * Provides integration with OpenAI's GPT-4, GPT-4o, GPT-3.5, and other models.
 * Supports both completion and streaming modes.
 *
 * @example
 * ```typescript
 * import { OpenAIAdapter } from './adapters/openai';
 *
 * const adapter = new OpenAIAdapter({
 *   apiKey: process.env.OPENAI_API_KEY,
 *   model: 'gpt-4-turbo',
 *   temperature: 0.7,
 * });
 *
 * const response = await adapter.process({
 *   role: 'user',
 *   content: 'Hello, GPT!',
 * });
 * console.log(response.content);
 * ```
 */

import OpenAI from 'openai';
import type { ChatCompletionMessageParam, ChatCompletionChunk } from 'openai/resources/chat/completions';
import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';

/**
 * Configuration for OpenAI adapter.
 */
export interface OpenAIConfig {
  /** OpenAI API key. If not provided, uses OPENAI_API_KEY environment variable */
  apiKey?: string;

  /** Model to use (e.g., 'gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo') */
  model?: string;

  /** Temperature for sampling (0.0 - 2.0) */
  temperature?: number;

  /** Maximum tokens to generate */
  maxTokens?: number;

  /** Top-p sampling parameter */
  topP?: number;

  /** Frequency penalty (-2.0 to 2.0) */
  frequencyPenalty?: number;

  /** Presence penalty (-2.0 to 2.0) */
  presencePenalty?: number;

  /** Base URL for API (for custom endpoints) */
  baseURL?: string;

  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * OpenAI adapter implementing the Agent interface.
 *
 * Features:
 * - Support for GPT-4, GPT-4o, GPT-3.5, and other OpenAI models
 * - Streaming and non-streaming completion
 * - Full metadata tracking (tokens, finish reason, model)
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Automatic message format conversion
 */
export class OpenAIAdapter implements Agent {
  private client: OpenAI;
  private config: Required<Omit<OpenAIConfig, 'apiKey' | 'baseURL' | 'timeout'>> & {
    baseURL?: string;
    timeout?: number;
  };

  /**
   * Creates a new OpenAI adapter.
   *
   * @param config - Configuration options
   */
  constructor(config: OpenAIConfig = {}) {
    this.config = {
      model: config.model || 'gpt-4-turbo',
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens ?? 1024,
      topP: config.topP ?? 1.0,
      frequencyPenalty: config.frequencyPenalty ?? 0.0,
      presencePenalty: config.presencePenalty ?? 0.0,
      baseURL: config.baseURL,
      timeout: config.timeout ?? 60000,
    };

    this.client = new OpenAI({
      apiKey: config.apiKey || process.env.OPENAI_API_KEY,
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
    });
  }

  /**
   * Returns the agent name.
   */
  name(): string {
    return `openai-${this.config.model}`;
  }

  /**
   * Returns agent capabilities.
   */
  capabilities(): string[] {
    return ['completion', 'streaming', 'chat'];
  }

  /**
   * Processes a message and returns a response.
   *
   * @param message - Input message
   * @returns Promise resolving to response message
   */
  async process(message: Message): Promise<Message> {
    validateMessage(message);

    const messages = this.convertToOpenAIFormat([message]);

    const response = await this.client.chat.completions.create({
      model: this.config.model,
      messages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
      frequency_penalty: this.config.frequencyPenalty,
      presence_penalty: this.config.presencePenalty,
    });

    const choice = response.choices[0];
    if (!choice || !choice.message) {
      throw new Error('OpenAI returned no response');
    }

    return createMessage({
      role: 'assistant',
      content: choice.message.content || '',
      metadata: {
        model: response.model,
        usage: {
          prompt_tokens: response.usage?.prompt_tokens || 0,
          completion_tokens: response.usage?.completion_tokens || 0,
          total_tokens: response.usage?.total_tokens || 0,
        },
        finish_reason: choice.finish_reason,
        created: response.created,
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

    const messages = this.convertToOpenAIFormat([message]);

    const stream = await this.client.chat.completions.create({
      model: this.config.model,
      messages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
      frequency_penalty: this.config.frequencyPenalty,
      presence_penalty: this.config.presencePenalty,
      stream: true,
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        yield createMessage({
          role: 'assistant',
          content: delta.content,
          metadata: {
            model: chunk.model,
            chunk: true,
            finish_reason: chunk.choices[0]?.finish_reason,
          },
        });
      }
    }
  }

  /**
   * Converts AgentKit messages to OpenAI format.
   *
   * @param messages - AgentKit messages
   * @returns OpenAI-formatted messages
   */
  private convertToOpenAIFormat(messages: Message[]): ChatCompletionMessageParam[] {
    return messages.map((msg) => {
      // Handle system messages
      if (msg.role === 'system') {
        return {
          role: 'system',
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
        };
      }

      // Handle user messages
      if (msg.role === 'user') {
        return {
          role: 'user',
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
        };
      }

      // Handle assistant messages
      if (msg.role === 'assistant') {
        return {
          role: 'assistant',
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
        };
      }

      // Default to user role for unknown types
      return {
        role: 'user',
        content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
      };
    });
  }

  /**
   * Completes a multi-turn conversation.
   *
   * @param messages - Array of conversation messages
   * @returns Promise resolving to response message
   */
  async complete(messages: Message[]): Promise<Message> {
    messages.forEach(validateMessage);

    const openaiMessages = this.convertToOpenAIFormat(messages);

    const response = await this.client.chat.completions.create({
      model: this.config.model,
      messages: openaiMessages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
      frequency_penalty: this.config.frequencyPenalty,
      presence_penalty: this.config.presencePenalty,
    });

    const choice = response.choices[0];
    if (!choice || !choice.message) {
      throw new Error('OpenAI returned no response');
    }

    return createMessage({
      role: 'assistant',
      content: choice.message.content || '',
      metadata: {
        model: response.model,
        usage: {
          prompt_tokens: response.usage?.prompt_tokens || 0,
          completion_tokens: response.usage?.completion_tokens || 0,
          total_tokens: response.usage?.total_tokens || 0,
        },
        finish_reason: choice.finish_reason,
        created: response.created,
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

    const openaiMessages = this.convertToOpenAIFormat(messages);

    const stream = await this.client.chat.completions.create({
      model: this.config.model,
      messages: openaiMessages,
      temperature: this.config.temperature,
      max_tokens: this.config.maxTokens,
      top_p: this.config.topP,
      frequency_penalty: this.config.frequencyPenalty,
      presence_penalty: this.config.presencePenalty,
      stream: true,
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        yield createMessage({
          role: 'assistant',
          content: delta.content,
          metadata: {
            model: chunk.model,
            chunk: true,
            finish_reason: chunk.choices[0]?.finish_reason,
          },
        });
      }
    }
  }
}
