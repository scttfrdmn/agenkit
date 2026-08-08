/**
 * Anthropic (Claude) LLM adapter.
 *
 * Implements Agent interface for Anthropic's Messages API.
 */

import Anthropic from '@anthropic-ai/sdk';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Anthropic adapter configuration.
 */
export interface AnthropicConfig {
  /** Anthropic API key */
  apiKey: string;

  /** Model to use (default: "claude-sonnet-5") */
  /** @default "claude-sonnet-5" */
  model?: string;

  /** Agent name (default: "claude") */
  name?: string;

  /** Temperature (default: 1.0) */
  temperature?: number;

  /** Max tokens (default: 4096) */
  maxTokens?: number;

  /** Additional Anthropic options */
  options?: Partial<Anthropic.Messages.MessageCreateParams>;
}

/**
 * AnthropicAgent implements Agent interface using Anthropic's API.
 *
 * Features:
 * - Full Anthropic Messages API support
 * - Streaming support
 * - Configurable model and parameters
 * - Automatic message format conversion
 *
 * Usage:
 *   const agent = new AnthropicAgent({
 *     apiKey: process.env.ANTHROPIC_API_KEY!,
 *     model: 'claude-sonnet-5',
 *     temperature: 1.0,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
export class AnthropicAgent implements Agent {
  readonly name: string;
  readonly capabilities = ['anthropic', 'claude', 'chat', 'streaming'];

  private client: Anthropic;
  private model: string;
  private temperature: number;
  private maxTokens: number;
  private options: Partial<Anthropic.Messages.MessageCreateParams>;

  constructor(config: AnthropicConfig) {
    this.name = config.name || 'claude';
    this.client = new Anthropic({ apiKey: config.apiKey });
    this.model = config.model || 'claude-sonnet-5';

    // Validate temperature
    const temperature = config.temperature !== undefined ? config.temperature : 1.0;
    if (temperature < 0 || temperature > 2) {
      throw new Error(`temperature must be between 0 and 2, got ${temperature}`);
    }
    this.temperature = temperature;

    // Validate maxTokens
    const maxTokens = config.maxTokens !== undefined ? config.maxTokens : 4096;
    if (maxTokens <= 0) {
      throw new Error(`maxTokens must be positive, got ${maxTokens}`);
    }
    this.maxTokens = maxTokens;

    this.options = config.options || {};
  }

  /**
   * Convert agenkit Message to Anthropic message format.
   */
  private toAnthropicMessage(message: Message): Anthropic.Messages.MessageParam {
    const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);

    // Anthropic only supports 'user' and 'assistant' roles
    const role = message.role === 'assistant' ? 'assistant' : 'user';

    return { role, content };
  }

  /**
   * Process a message using Anthropic API.
   *
   * @param message Input message
   * @returns Response message
   */
  async process(message: Message): Promise<Message> {
    const anthropicMessage = this.toAnthropicMessage(message);

    const response = (await this.client.messages.create({
      model: this.model,
      messages: [anthropicMessage],
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      stream: false,
      ...this.options,
    })) as Anthropic.Messages.Message;

    // Extract text from content blocks
    const content = response.content
      .filter((block: Anthropic.Messages.ContentBlock) => block.type === 'text')
      .map((block: Anthropic.Messages.ContentBlock) => ('text' in block ? block.text : ''))
      .join('');

    return createMessage('assistant', content, {
      model: this.model,
      stop_reason: response.stop_reason,
      input_tokens: response.usage.input_tokens,
      output_tokens: response.usage.output_tokens,
      total_tokens: response.usage.input_tokens + response.usage.output_tokens,
      id: response.id,
    });
  }

  /**
   * Process a message with streaming response.
   *
   * @param message Input message
   * @returns Async iterator of response chunks
   */
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    const anthropicMessage = this.toAnthropicMessage(message);

    const stream = (await this.client.messages.create({
      model: this.model,
      messages: [anthropicMessage],
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      stream: true,
      ...this.options,
    })) as AsyncIterable<Anthropic.Messages.RawMessageStreamEvent>;

    for await (const event of stream) {
      if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
        yield createMessage('assistant', event.delta.text, {
          model: this.model,
        });
      }
    }
  }
}
