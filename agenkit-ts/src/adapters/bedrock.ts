/**
 * Amazon Bedrock LLM adapter for foundation models.
 *
 * Provides integration with Amazon Bedrock's foundation models including
 * Claude, Llama, Mistral, and Titan. Supports both completion and streaming modes.
 *
 * @example
 * ```typescript
 * import { BedrockAdapter } from './adapters/bedrock';
 *
 * const adapter = new BedrockAdapter({
 *   region: 'us-east-1',
 *   modelId: 'anthropic.claude-sonnet-5',
 * });
 *
 * const response = await adapter.process({
 *   role: 'user',
 *   content: 'Hello, Claude!',
 * });
 * console.log(response.content);
 * ```
 */

import {
  BedrockRuntimeClient,
  ConverseCommand,
  ConverseStreamCommand,
  type ConverseCommandInput,
  type ConverseStreamCommandInput,
  type Message as BedrockMessage,
  type ContentBlock,
  type SystemContentBlock,
  type InferenceConfiguration,
  ConversationRole,
} from '@aws-sdk/client-bedrock-runtime';
import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';
import type { CallOptions } from '../core/call-options';

/**
 * Configuration for Bedrock adapter.
 */
export interface BedrockConfig {
  /** AWS region (default: 'us-east-1') */
  region?: string;

  /** Bedrock model identifier (e.g., 'anthropic.claude-sonnet-5') */
  modelId?: string;

  /** AWS access key ID (optional - uses default credential chain if not provided) */
  accessKeyId?: string;

  /** AWS secret access key (optional - uses default credential chain if not provided) */
  secretAccessKey?: string;

  /** AWS session token (optional) */
  sessionToken?: string;

  /** Custom endpoint URL (optional - for VPC endpoints) */
  endpoint?: string;

  /** Temperature for sampling (0.0 - 1.0) */
  temperature?: number;

  /** Maximum tokens to generate */
  maxTokens?: number;

  /** Top-p sampling parameter */
  topP?: number;

  /** Stop sequences */
  stopSequences?: string[];

  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Bedrock adapter implementing the Agent interface.
 *
 * Features:
 * - Support for Claude, Llama, Mistral, Titan, and other Bedrock models
 * - Streaming and non-streaming completion
 * - Full metadata tracking (tokens, stop reason, model)
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Automatic message format conversion
 * - AWS credential chain support
 * - System message support
 *
 * Popular model IDs:
 * - anthropic.claude-sonnet-5 - Claude Sonnet 5
 * - anthropic.claude-haiku-4-5 - Claude Haiku 4.5
 * - meta.llama3-70b-instruct-v1:0 - Llama 3 70B
 * - mistral.mistral-large-2402-v1:0 - Mistral Large
 * - amazon.titan-text-premier-v1:0 - Amazon Titan
 */
export class BedrockAdapter implements Agent {
  private client: BedrockRuntimeClient;
  private config: Required<Omit<BedrockConfig, 'accessKeyId' | 'secretAccessKey' | 'sessionToken' | 'endpoint'>>;

  /**
   * Creates a new Bedrock adapter.
   *
   * @param config - Configuration options
   */
  constructor(config: BedrockConfig = {}) {
    this.config = {
      region: config.region || 'us-east-1',
      modelId: config.modelId || 'anthropic.claude-sonnet-5',
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens ?? 4096,
      topP: config.topP ?? 1.0,
      stopSequences: config.stopSequences || [],
      timeout: config.timeout ?? 60000,
    };

    const clientConfig: any = {
      region: this.config.region,
    };

    if (config.accessKeyId && config.secretAccessKey) {
      clientConfig.credentials = {
        accessKeyId: config.accessKeyId,
        secretAccessKey: config.secretAccessKey,
        sessionToken: config.sessionToken,
      };
    }

    if (config.endpoint) {
      clientConfig.endpoint = config.endpoint;
    }

    this.client = new BedrockRuntimeClient(clientConfig);
  }

  /**
   * Returns the agent name.
   */
  get name(): string {
    return `bedrock-${this.config.modelId}`;
  }

  /**
   * Returns agent capabilities.
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
    return this.processWith(message, {});
  }

  /**
   * Builds the `inferenceConfig` block, applying per-call options over the
   * adapter's configured defaults (#818).
   *
   * `options.stop` maps to Bedrock's `stopSequences` — the Converse API's
   * `InferenceConfiguration` has no field named `stop`. `seed` has no
   * equivalent anywhere in the Converse API (no `inferenceConfig` field, and
   * passing it as a top-level parameter raises `ValidationException`), so a
   * caller who set one is warned rather than left to discover — empirically,
   * via non-reproducible output — that it had no effect.
   */
  private buildInferenceConfig(options: CallOptions): InferenceConfiguration {
    if (options.seed !== undefined) {
      console.warn(
        `BedrockAdapter does not support 'seed': the Converse API has no ` +
          'sampling-seed parameter. The value was not sent to the provider.',
      );
    }

    const inferenceConfig: InferenceConfiguration = {
      temperature: options.temperature ?? this.config.temperature,
      maxTokens: options.maxTokens ?? this.config.maxTokens,
      topP: options.topP ?? this.config.topP,
    };

    const stopSequences = options.stop ?? this.config.stopSequences;
    if (stopSequences.length > 0) {
      inferenceConfig.stopSequences = stopSequences;
    }

    return inferenceConfig;
  }

  /**
   * Processes a message with per-call inference options (#818).
   *
   * @param message - Input message
   * @param options - Per-call inference options
   * @returns Promise resolving to response message
   */
  async processWith(message: Message, options: CallOptions): Promise<Message> {
    validateMessage(message);

    const { messages, system } = this.convertToBedrockFormat([message]);

    const inferenceConfig = this.buildInferenceConfig(options);

    const input: ConverseCommandInput = {
      modelId: this.config.modelId,
      messages,
      inferenceConfig,
    };

    if (system && system.length > 0) {
      input.system = system;
    }

    const command = new ConverseCommand(input);
    const response = await this.client.send(command);

    let content = '';
    if (response.output && 'message' in response.output) {
      const outputMessage = response.output.message;
      if (outputMessage?.content) {
        for (const block of outputMessage.content) {
          if ('text' in block && block.text) {
            content += block.text;
          }
        }
      }
    }

    return createMessage({
      role: 'assistant',
      content,
      metadata: {
        model: this.config.modelId,
        usage: {
          prompt_tokens: response.usage?.inputTokens || 0,
          completion_tokens: response.usage?.outputTokens || 0,
          total_tokens: response.usage?.totalTokens || 0,
          // Prompt-cache token counts (Anthropic-on-Bedrock), billed at a
          // reduced rate. Only present when prompt caching is active.
          ...(response.usage?.cacheReadInputTokens
            ? { cache_read_tokens: response.usage.cacheReadInputTokens }
            : {}),
          ...(response.usage?.cacheWriteInputTokens
            ? { cache_creation_tokens: response.usage.cacheWriteInputTokens }
            : {}),
        },
        stop_reason: response.stopReason || 'end_turn',
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

    const { messages, system } = this.convertToBedrockFormat([message]);

    const inferenceConfig: InferenceConfiguration = {
      temperature: this.config.temperature,
      maxTokens: this.config.maxTokens,
      topP: this.config.topP,
    };

    if (this.config.stopSequences.length > 0) {
      inferenceConfig.stopSequences = this.config.stopSequences;
    }

    const input: ConverseStreamCommandInput = {
      modelId: this.config.modelId,
      messages,
      inferenceConfig,
    };

    if (system && system.length > 0) {
      input.system = system;
    }

    const command = new ConverseStreamCommand(input);
    const response = await this.client.send(command);

    if (!response.stream) {
      return;
    }

    for await (const event of response.stream) {
      if (event.contentBlockDelta) {
        const delta = event.contentBlockDelta.delta;
        if (delta && 'text' in delta && delta.text) {
          yield createMessage({
            role: 'assistant',
            content: delta.text,
            metadata: {
              chunk: true,
              model: this.config.modelId,
            },
          });
        }
      } else if (event.messageStop) {
        break;
      }
    }
  }

  /**
   * Converts AgentKit messages to Bedrock format.
   *
   * @param messages - AgentKit messages
   * @returns Bedrock-formatted messages and optional system prompts
   */
  private convertToBedrockFormat(messages: Message[]): {
    messages: BedrockMessage[];
    system?: SystemContentBlock[];
  } {
    const bedrockMessages: BedrockMessage[] = [];
    const systemPrompts: SystemContentBlock[] = [];

    for (const msg of messages) {
      const contentStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

      if (msg.role === 'system') {
        systemPrompts.push({
          text: contentStr,
        });
        continue;
      }

      let role: ConversationRole;
      if (msg.role === 'user') {
        role = ConversationRole.USER;
      } else {
        role = ConversationRole.ASSISTANT;
      }

      const contentBlocks: ContentBlock[] = [
        {
          text: contentStr,
        },
      ];

      bedrockMessages.push({
        role,
        content: contentBlocks,
      });
    }

    return {
      messages: bedrockMessages,
      system: systemPrompts.length > 0 ? systemPrompts : undefined,
    };
  }

  /**
   * Completes a multi-turn conversation.
   *
   * @param messages - Array of conversation messages
   * @returns Promise resolving to response message
   */
  async complete(messages: Message[]): Promise<Message> {
    messages.forEach(validateMessage);

    const { messages: bedrockMessages, system } = this.convertToBedrockFormat(messages);

    const inferenceConfig: InferenceConfiguration = {
      temperature: this.config.temperature,
      maxTokens: this.config.maxTokens,
      topP: this.config.topP,
    };

    if (this.config.stopSequences.length > 0) {
      inferenceConfig.stopSequences = this.config.stopSequences;
    }

    const input: ConverseCommandInput = {
      modelId: this.config.modelId,
      messages: bedrockMessages,
      inferenceConfig,
    };

    if (system && system.length > 0) {
      input.system = system;
    }

    const command = new ConverseCommand(input);
    const response = await this.client.send(command);

    let content = '';
    if (response.output && 'message' in response.output) {
      const outputMessage = response.output.message;
      if (outputMessage?.content) {
        for (const block of outputMessage.content) {
          if ('text' in block && block.text) {
            content += block.text;
          }
        }
      }
    }

    return createMessage({
      role: 'assistant',
      content,
      metadata: {
        model: this.config.modelId,
        usage: {
          prompt_tokens: response.usage?.inputTokens || 0,
          completion_tokens: response.usage?.outputTokens || 0,
          total_tokens: response.usage?.totalTokens || 0,
          // Prompt-cache token counts (Anthropic-on-Bedrock), billed at a
          // reduced rate. Only present when prompt caching is active.
          ...(response.usage?.cacheReadInputTokens
            ? { cache_read_tokens: response.usage.cacheReadInputTokens }
            : {}),
          ...(response.usage?.cacheWriteInputTokens
            ? { cache_creation_tokens: response.usage.cacheWriteInputTokens }
            : {}),
        },
        stop_reason: response.stopReason || 'end_turn',
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

    const { messages: bedrockMessages, system } = this.convertToBedrockFormat(messages);

    const inferenceConfig: InferenceConfiguration = {
      temperature: this.config.temperature,
      maxTokens: this.config.maxTokens,
      topP: this.config.topP,
    };

    if (this.config.stopSequences.length > 0) {
      inferenceConfig.stopSequences = this.config.stopSequences;
    }

    const input: ConverseStreamCommandInput = {
      modelId: this.config.modelId,
      messages: bedrockMessages,
      inferenceConfig,
    };

    if (system && system.length > 0) {
      input.system = system;
    }

    const command = new ConverseStreamCommand(input);
    const response = await this.client.send(command);

    if (!response.stream) {
      return;
    }

    for await (const event of response.stream) {
      if (event.contentBlockDelta) {
        const delta = event.contentBlockDelta.delta;
        if (delta && 'text' in delta && delta.text) {
          yield createMessage({
            role: 'assistant',
            content: delta.text,
            metadata: {
              chunk: true,
              model: this.config.modelId,
            },
          });
        }
      } else if (event.messageStop) {
        break;
      }
    }
  }

  /**
   * Gets the underlying Bedrock client.
   *
   * @returns The BedrockRuntimeClient instance
   */
  getClient(): BedrockRuntimeClient {
    return this.client;
  }
}
