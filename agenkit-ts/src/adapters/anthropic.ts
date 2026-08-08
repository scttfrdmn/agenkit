/**
 * Anthropic Claude LLM adapter.
 *
 * Provides integration with Anthropic's Claude models (Claude 3.5 Sonnet, Opus, Haiku, etc.).
 * Supports both completion and streaming modes.
 *
 * @example
 * ```typescript
 * import { AnthropicAdapter } from './adapters/anthropic';
 *
 * const adapter = new AnthropicAdapter({
 *   apiKey: process.env.ANTHROPIC_API_KEY,
 *   model: 'claude-sonnet-5',
 *   temperature: 0.7,
 *   maxTokens: 1024,
 * });
 *
 * const response = await adapter.process({
 *   role: 'user',
 *   content: 'Hello, Claude!',
 * });
 * console.log(response.content);
 * ```
 */

import Anthropic from '@anthropic-ai/sdk';
import type { MessageParam, MessageStreamEvent } from '@anthropic-ai/sdk/resources/messages';
import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';

/**
 * Configuration for Anthropic adapter.
 */
export interface AnthropicConfig {
  /** Anthropic API key. If not provided, uses ANTHROPIC_API_KEY environment variable */
  apiKey?: string;

  /** Model to use (e.g., 'claude-sonnet-5', 'claude-opus-5') */
  model?: string;

  /** Temperature for sampling (0.0 - 1.0) */
  temperature?: number;

  /** Maximum tokens to generate */
  maxTokens?: number;

  /** Top-p sampling parameter */
  topP?: number;

  /** Top-k sampling parameter */
  topK?: number;

  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Anthropic adapter implementing the Agent interface.
 *
 * Features:
 * - Support for Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku, and other Claude models
 * - Streaming and non-streaming completion
 * - Full metadata tracking (tokens, stop reason, model)
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Automatic message format conversion
 * - System message support
 */
export class AnthropicAdapter implements Agent {
  private client: Anthropic;
  private config: Required<Omit<AnthropicConfig, 'apiKey'>>;

  /**
   * Creates a new Anthropic adapter.
   *
   * @param config - Configuration options
   */
  constructor(config: AnthropicConfig = {}) {
    this.config = {
      model: config.model || 'claude-sonnet-5',
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens ?? 1024,
      topP: config.topP ?? 1.0,
      topK: config.topK ?? 5,
      timeout: config.timeout ?? 60000,
    };

    this.client = new Anthropic({
      apiKey: config.apiKey || process.env.ANTHROPIC_API_KEY,
      timeout: this.config.timeout,
    });
  }

  /**
   * Agent name.
   */
  get name(): string {
    return `anthropic-${this.config.model}`;
  }

  /**
   * Agent capabilities.
   */
  get capabilities(): string[] {
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

    const { messages, system } = this.convertToAnthropicFormat([message]);

    const response = await this.client.messages.create({
      model: this.config.model,
      messages,
      system,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature,
      top_p: this.config.topP,
      top_k: this.config.topK,
    });

    const textContent = response.content
      .filter((block) => block.type === 'text')
      .map((block) => (block.type === 'text' ? block.text : ''))
      .join('');

    return createMessage({
      role: 'assistant',
      content: textContent,
      metadata: {
        model: response.model,
        usage: {
          prompt_tokens: response.usage.input_tokens,
          completion_tokens: response.usage.output_tokens,
          total_tokens: response.usage.input_tokens + response.usage.output_tokens,
        },
        stop_reason: response.stop_reason,
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

    const { messages, system } = this.convertToAnthropicFormat([message]);

    const stream = await this.client.messages.create({
      model: this.config.model,
      messages,
      system,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature,
      top_p: this.config.topP,
      top_k: this.config.topK,
      stream: true,
    });

    for await (const event of stream) {
      if (event.type === 'content_block_delta') {
        if (event.delta.type === 'text_delta') {
          yield createMessage({
            role: 'assistant',
            content: event.delta.text,
            metadata: {
              chunk: true,
              index: event.index,
            },
          });
        }
      } else if (event.type === 'message_stop') {
        // Stream complete
        break;
      }
    }
  }

  /**
   * Converts AgentKit messages to Anthropic format.
   *
   * @param messages - AgentKit messages
   * @returns Anthropic-formatted messages and optional system message
   */
  private convertToAnthropicFormat(messages: Message[]): {
    messages: MessageParam[];
    system?: string;
  } {
    let system: string | undefined;
    const anthropicMessages: MessageParam[] = [];

    for (const msg of messages) {
      // Extract system messages
      if (msg.role === 'system') {
        system = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
        continue;
      }

      // Convert user/assistant messages
      if (msg.role === 'user' || msg.role === 'assistant') {
        anthropicMessages.push({
          role: msg.role,
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
        });
      } else {
        // Unknown roles become user messages
        anthropicMessages.push({
          role: 'user',
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
        });
      }
    }

    return { messages: anthropicMessages, system };
  }

  /**
   * Completes a multi-turn conversation.
   *
   * @param messages - Array of conversation messages
   * @returns Promise resolving to response message
   */
  async complete(messages: Message[]): Promise<Message> {
    messages.forEach(validateMessage);

    const { messages: anthropicMessages, system } = this.convertToAnthropicFormat(messages);

    const response = await this.client.messages.create({
      model: this.config.model,
      messages: anthropicMessages,
      system,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature,
      top_p: this.config.topP,
      top_k: this.config.topK,
    });

    const textContent = response.content
      .filter((block) => block.type === 'text')
      .map((block) => (block.type === 'text' ? block.text : ''))
      .join('');

    return createMessage({
      role: 'assistant',
      content: textContent,
      metadata: {
        model: response.model,
        usage: {
          prompt_tokens: response.usage.input_tokens,
          completion_tokens: response.usage.output_tokens,
          total_tokens: response.usage.input_tokens + response.usage.output_tokens,
        },
        stop_reason: response.stop_reason,
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

    const { messages: anthropicMessages, system } = this.convertToAnthropicFormat(messages);

    const stream = await this.client.messages.create({
      model: this.config.model,
      messages: anthropicMessages,
      system,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature,
      top_p: this.config.topP,
      top_k: this.config.topK,
      stream: true,
    });

    for await (const event of stream) {
      if (event.type === 'content_block_delta') {
        if (event.delta.type === 'text_delta') {
          yield createMessage({
            role: 'assistant',
            content: event.delta.text,
            metadata: {
              chunk: true,
              index: event.index,
            },
          });
        }
      } else if (event.type === 'message_stop') {
        break;
      }
    }
  }
}
