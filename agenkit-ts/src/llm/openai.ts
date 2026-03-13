/**
 * OpenAI LLM adapter.
 *
 * Implements Agent interface for OpenAI's Chat Completion API.
 */

import OpenAI from 'openai';
import { Agent, Message, createMessage } from '../core/interfaces';
import { validateLLMParams } from './validation';

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

    // Validate temperature and maxTokens using shared utility
    const temperature = config.temperature !== undefined ? config.temperature : 0.7;
    validateLLMParams({
      temperature,
      max_tokens: config.maxTokens,
    });
    this.temperature = temperature;
    this.maxTokens = config.maxTokens;

    // Validate options if provided
    if (config.options) {
      this.validateOptions(config.options);
    }
    this.options = config.options || {};
  }

  /**
   * Validate LLM parameters.
   */
  private validateOptions(options: Partial<OpenAI.Chat.ChatCompletionCreateParams>): void {
    // Use shared validation utility
    // Note: OpenAI types use `number | null` but we only validate non-null values
    validateLLMParams({
      temperature: options.temperature ?? undefined,
      max_tokens: options.max_tokens ?? undefined,
      top_p: options.top_p ?? undefined,
      frequency_penalty: options.frequency_penalty ?? undefined,
      presence_penalty: options.presence_penalty ?? undefined,
    });
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
      stop_reason: choice.finish_reason,
      input_tokens: completion.usage?.prompt_tokens ?? 0,
      output_tokens: completion.usage?.completion_tokens ?? 0,
      total_tokens: completion.usage?.total_tokens ?? 0,
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
