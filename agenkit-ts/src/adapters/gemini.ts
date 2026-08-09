/**
 * Google Gemini LLM adapter.
 *
 * Provides integration with Google's Gemini models (Gemini 2.0, Gemini 1.5 Pro, etc.).
 * Supports both completion and streaming modes.
 *
 * @example
 * ```typescript
 * import { GeminiAdapter } from './adapters/gemini';
 *
 * const adapter = new GeminiAdapter({
 *   apiKey: process.env.GEMINI_API_KEY,
 *   model: 'gemini-2.0-flash-exp',
 *   temperature: 0.7,
 * });
 *
 * const response = await adapter.process({
 *   role: 'user',
 *   content: 'Hello, Gemini!',
 * });
 * console.log(response.content);
 * ```
 */

import {
  GoogleGenerativeAI,
  type GenerativeModel,
  type Content,
  type Part,
  type GenerateContentResult,
  type EnhancedGenerateContentResponse,
} from '@google/generative-ai';
import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';
import type { CallOptions } from '../core/call-options';

/**
 * Configuration for Gemini adapter.
 */
export interface GeminiConfig {
  /** Google API key. If not provided, uses GEMINI_API_KEY or GOOGLE_API_KEY environment variable */
  apiKey?: string;

  /** Model to use (e.g., 'gemini-2.0-flash-exp', 'gemini-1.5-pro') */
  model?: string;

  /** Temperature for sampling (0.0 - 2.0) */
  temperature?: number;

  /** Maximum tokens to generate */
  maxTokens?: number;

  /** Top-p sampling parameter */
  topP?: number;

  /** Top-k sampling parameter */
  topK?: number;

  /** Stop sequences */
  stopSequences?: string[];

  /** Number of candidate responses to generate */
  candidateCount?: number;

  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Gemini adapter implementing the Agent interface.
 *
 * Features:
 * - Support for Gemini 2.0, Gemini 1.5 Pro, and other Gemini models
 * - Streaming and non-streaming completion
 * - Full metadata tracking (tokens, finish reason, model)
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Automatic message format conversion
 * - System message support (prepended as user message)
 */
export class GeminiAdapter implements Agent {
  private client: GoogleGenerativeAI;
  private config: Required<Omit<GeminiConfig, 'apiKey'>>;

  /**
   * Creates a new Gemini adapter.
   *
   * @param config - Configuration options
   */
  constructor(config: GeminiConfig = {}) {
    const apiKey =
      config.apiKey || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;

    if (!apiKey) {
      throw new Error(
        'Gemini API key required: provide apiKey parameter or set GEMINI_API_KEY or GOOGLE_API_KEY environment variable',
      );
    }

    this.config = {
      model: config.model || 'gemini-2.0-flash-exp',
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens ?? 8192,
      topP: config.topP ?? 1.0,
      topK: config.topK ?? 40,
      stopSequences: config.stopSequences || [],
      candidateCount: config.candidateCount ?? 1,
      timeout: config.timeout ?? 60000,
    };

    this.client = new GoogleGenerativeAI(apiKey);
  }

  /**
   * Returns the agent name.
   */
  get name(): string {
    return `gemini-${this.config.model}`;
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
   * Processes a message with per-call inference options (#818).
   *
   * `stop` is translated to Gemini's `stopSequences` — the GenerationConfig has
   * no `stop` field. `seed` has no equivalent in this SDK
   * (`@google/generative-ai`'s `GenerationConfig` has no seed field, unlike
   * Google's Python `google-genai` SDK), so a caller who set one is warned
   * rather than left to discover — empirically, via non-reproducible output —
   * that it had no effect.
   *
   * @param message - Input message
   * @param options - Per-call inference options
   * @returns Promise resolving to response message
   */
  async processWith(message: Message, options: CallOptions): Promise<Message> {
    validateMessage(message);

    if (options.seed !== undefined) {
      console.warn(
        `GeminiAdapter does not support 'seed': the @google/generative-ai SDK's ` +
          "GenerationConfig has no sampling-seed field. The value was not sent to the provider.",
      );
    }

    const model = this.getModel(options);
    const { history, lastMessage } = this.convertMessages([message]);

    const chat = model.startChat({
      history,
    });

    const result = await chat.sendMessage(lastMessage);
    const response = result.response;

    const content = this.extractContent(response);

    return createMessage({
      role: 'assistant',
      content,
      metadata: {
        model: this.config.model,
        usage: this.extractUsage(response),
        finish_reason: this.extractFinishReason(response),
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

    const model = this.getModel();
    const { history, lastMessage } = this.convertMessages([message]);

    const chat = model.startChat({
      history,
    });

    const result = await chat.sendMessageStream(lastMessage);

    for await (const chunk of result.stream) {
      const content = this.extractContent(chunk);
      if (content) {
        yield createMessage({
          role: 'assistant',
          content,
          metadata: {
            chunk: true,
            model: this.config.model,
          },
        });
      }
    }
  }

  /**
   * Completes a multi-turn conversation.
   *
   * @param messages - Array of conversation messages
   * @returns Promise resolving to response message
   */
  async complete(messages: Message[]): Promise<Message> {
    messages.forEach(validateMessage);

    const model = this.getModel();
    const { history, lastMessage } = this.convertMessages(messages);

    const chat = model.startChat({
      history,
    });

    const result = await chat.sendMessage(lastMessage);
    const response = result.response;

    const content = this.extractContent(response);

    return createMessage({
      role: 'assistant',
      content,
      metadata: {
        model: this.config.model,
        usage: this.extractUsage(response),
        finish_reason: this.extractFinishReason(response),
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

    const model = this.getModel();
    const { history, lastMessage } = this.convertMessages(messages);

    const chat = model.startChat({
      history,
    });

    const result = await chat.sendMessageStream(lastMessage);

    for await (const chunk of result.stream) {
      const content = this.extractContent(chunk);
      if (content) {
        yield createMessage({
          role: 'assistant',
          content,
          metadata: {
            chunk: true,
            model: this.config.model,
          },
        });
      }
    }
  }

  /**
   * Gets a configured Gemini model.
   *
   * @param options - Optional per-call inference options that override the
   *   adapter's configured defaults (#818). `stop` overrides `stopSequences`
   *   entirely rather than merging, matching how `options.temperature` etc.
   *   already override rather than merge with the adapter's config.
   * @returns Configured GenerativeModel instance
   */
  private getModel(options?: CallOptions): GenerativeModel {
    const stopSequences = options?.stop ?? this.config.stopSequences;
    return this.client.getGenerativeModel({
      model: this.config.model,
      generationConfig: {
        temperature: options?.temperature ?? this.config.temperature,
        maxOutputTokens: options?.maxTokens ?? this.config.maxTokens,
        topP: options?.topP ?? this.config.topP,
        topK: this.config.topK,
        stopSequences: stopSequences.length > 0 ? stopSequences : undefined,
        candidateCount: this.config.candidateCount,
      },
    });
  }

  /**
   * Converts AgentKit messages to Gemini format.
   *
   * @param messages - AgentKit messages
   * @returns Gemini-formatted history and last message
   */
  private convertMessages(messages: Message[]): {
    history: Content[];
    lastMessage: string | Part[];
  } {
    if (messages.length === 0) {
      return { history: [], lastMessage: '' };
    }

    const history: Content[] = [];

    for (let i = 0; i < messages.length - 1; i++) {
      const msg = messages[i];
      const role = this.mapRole(msg.role);
      const contentStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

      history.push({
        role,
        parts: [{ text: contentStr }],
      });
    }

    const lastMsg = messages[messages.length - 1];
    const lastContent = typeof lastMsg.content === 'string' ? lastMsg.content : JSON.stringify(lastMsg.content);

    return {
      history,
      lastMessage: lastContent,
    };
  }

  /**
   * Maps AgentKit role to Gemini role.
   *
   * @param role - AgentKit role
   * @returns Gemini role ('user' or 'model')
   */
  private mapRole(role: string): string {
    switch (role) {
      case 'user':
      case 'system':
        return 'user';
      case 'assistant':
      case 'agent':
      default:
        return 'model';
    }
  }

  /**
   * Extracts text content from a Gemini response.
   *
   * @param response - Gemini response
   * @returns Extracted text content
   */
  private extractContent(response: EnhancedGenerateContentResponse): string {
    if (!response.candidates || response.candidates.length === 0) {
      return '';
    }

    const candidate = response.candidates[0];
    if (!candidate.content || !candidate.content.parts) {
      return '';
    }

    let content = '';
    for (const part of candidate.content.parts) {
      if ('text' in part && part.text) {
        content += part.text;
      }
    }

    return content;
  }

  /**
   * Extracts usage metadata from a Gemini response.
   *
   * @param response - Gemini response
   * @returns Usage metadata
   */
  private extractUsage(response: EnhancedGenerateContentResponse): Record<string, number> {
    if (!response.usageMetadata) {
      return {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
      };
    }

    return {
      prompt_tokens: response.usageMetadata.promptTokenCount || 0,
      completion_tokens: response.usageMetadata.candidatesTokenCount || 0,
      total_tokens: response.usageMetadata.totalTokenCount || 0,
    };
  }

  /**
   * Extracts finish reason from a Gemini response.
   *
   * @param response - Gemini response
   * @returns Finish reason string
   */
  private extractFinishReason(response: EnhancedGenerateContentResponse): string {
    if (!response.candidates || response.candidates.length === 0) {
      return 'unknown';
    }

    const candidate = response.candidates[0];
    return candidate.finishReason || 'unknown';
  }

  /**
   * Gets the underlying Google Generative AI client.
   *
   * @returns The GoogleGenerativeAI instance
   */
  getClient(): GoogleGenerativeAI {
    return this.client;
  }
}
