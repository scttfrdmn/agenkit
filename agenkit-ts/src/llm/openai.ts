/**
 * OpenAI LLM adapter.
 *
 * Implements Agent interface for OpenAI's Chat Completion API.
 */

import OpenAI from 'openai';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * OpenAI adapter configuration.
 */
export interface OpenAIConfig {
  /** OpenAI API key */
  apiKey: string;

  /** Model to use (default: "gpt-4o") */
  model?: string;

  /** Agent name (default: "openai") */
  name?: string;

  /** Temperature (default: 0.7) */
  temperature?: number;

  /** Max tokens (default: undefined - let model decide) */
  maxTokens?: number;

  /** Additional OpenAI options */
  options?: Partial<OpenAI.Chat.ChatCompletionCreateParams>;
}

/**
 * OpenAIAgent implements Agent interface using OpenAI's API.
 *
 * Features:
 * - Full OpenAI Chat API support
 * - Streaming support
 * - Configurable model and parameters
 * - Automatic message format conversion
 *
 * Usage:
 *   const agent = new OpenAIAgent({
 *     apiKey: process.env.OPENAI_API_KEY!,
 *     model: 'gpt-4o',
 *     temperature: 0.7,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
export class OpenAIAgent implements Agent {
  readonly name: string;
  readonly capabilities = ['openai', 'chat', 'streaming'];

  private client: OpenAI;
  private model: string;
  private temperature: number;
  private maxTokens?: number;
  private options: Partial<OpenAI.Chat.ChatCompletionCreateParams>;

  constructor(config: OpenAIConfig) {
    this.name = config.name || 'openai';
    this.client = new OpenAI({ apiKey: config.apiKey });
    this.model = config.model || 'gpt-4o';
    this.temperature = config.temperature || 0.7;
    this.maxTokens = config.maxTokens;
    this.options = config.options || {};
  }

  /**
   * Convert agenkit Message to OpenAI message format.
   */
  private toOpenAIMessage(message: Message): OpenAI.Chat.ChatCompletionMessageParam {
    const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);

    switch (message.role) {
      case 'user':
        return { role: 'user', content };
      case 'assistant':
        return { role: 'assistant', content };
      case 'system':
        return { role: 'system', content };
      default:
        // Default to user for unknown roles
        return { role: 'user', content };
    }
  }

  /**
   * Process a message using OpenAI API.
   *
   * @param message Input message
   * @returns Response message
   */
  async process(message: Message): Promise<Message> {
    const openaiMessage = this.toOpenAIMessage(message);

    const completion = (await this.client.chat.completions.create({
      model: this.model,
      messages: [openaiMessage],
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      stream: false,
      ...this.options,
    })) as OpenAI.Chat.ChatCompletion;

    const choice = completion.choices[0];
    const content = choice.message.content || '';

    return createMessage('assistant', content, {
      model: this.model,
      finishReason: choice.finish_reason,
      usage: completion.usage,
      id: completion.id,
    });
  }

  /**
   * Process a message with streaming response.
   *
   * @param message Input message
   * @returns Async iterator of response chunks
   */
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    const openaiMessage = this.toOpenAIMessage(message);

    const stream = (await this.client.chat.completions.create({
      model: this.model,
      messages: [openaiMessage],
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      stream: true,
      ...this.options,
    })) as AsyncIterable<OpenAI.Chat.ChatCompletionChunk>;

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        yield createMessage('assistant', delta.content, {
          model: this.model,
          id: chunk.id,
        });
      }
    }
  }
}
