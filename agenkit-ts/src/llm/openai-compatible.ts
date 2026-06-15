/**
 * OpenAI-Compatible LLM adapter.
 *
 * Generic adapter for OpenAI-compatible inference services like vLLM,
 * llama.cpp, SGLang, TensorRT-LLM, and others.
 *
 * This adapter enables Agenkit to work with any service implementing the
 * OpenAI Chat Completions API by configuring the OpenAI SDK with a custom
 * base URL.
 *
 * Supported services:
 * - vLLM: High-throughput batch inference
 * - llama.cpp: Lightweight C++ implementation (CPU-friendly)
 * - SGLang: Optimized for complex prompts
 * - TensorRT-LLM: NVIDIA GPU optimized
 * - OpenLLM: Multi-model serving platform
 * - MLC LLM: Mobile and edge deployment
 * - Text Generation Inference (TGI): HuggingFace inference server
 * - Inferflow: High-performance inference
 *
 * Example - vLLM local deployment:
 *
 *   const agent = new OpenAICompatibleAgent({
 *     baseURL: 'http://localhost:8000/v1',
 *     model: 'meta-llama/Llama-2-7b-chat-hf',
 *     provider: 'vllm',
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 *
 * Example - llama.cpp server:
 *
 *   const agent = new OpenAICompatibleAgent({
 *     baseURL: 'http://localhost:8080/v1',
 *     model: 'llama-2-7b-chat',
 *     provider: 'llamacpp',
 *   });
 *
 * Example - Streaming:
 *
 *   for await (const chunk of agent.processStream(message)) {
 *     process.stdout.write(chunk.content as string);
 *   }
 */

import OpenAI from 'openai';
import { Agent, Message, createMessage } from '../core/interfaces.js';

/**
 * OpenAI-Compatible adapter configuration.
 */
export interface OpenAICompatibleConfig {
  /**
   * Base URL of the inference service (e.g., "http://localhost:8000/v1").
   * Must include the /v1 suffix for most services.
   */
  baseURL: string;

  /**
   * Model name/identifier used by the inference service.
   * Format varies by service:
   * - vLLM: "meta-llama/Llama-2-7b-chat-hf"
   * - llama.cpp: "llama-2-7b-chat"
   * - SGLang: "meta-llama/Llama-2-13b-chat-hf"
   */
  model: string;

  /**
   * Optional provider name for metadata and debugging.
   * Examples: "vllm", "llamacpp", "sglang", "tensorrt"
   */
  provider?: string;

  /**
   * Optional API key. Most local services don't require authentication,
   * so this can be omitted. Defaults to "not-needed".
   */
  apiKey?: string;

  /** Agent name (default: derived from provider or "openai-compatible") */
  name?: string;

  /** Temperature (default: 0.7) */
  temperature?: number;

  /** Max tokens (default: 1024) */
  maxTokens?: number;

  /** Top P (default: 1.0) */
  topP?: number;

  /** Request timeout in milliseconds (default: 60000) */
  timeout?: number;

  /** Additional OpenAI client options */
  options?: Partial<OpenAI.Chat.ChatCompletionCreateParams>;
}

/**
 * OpenAICompatibleAgent implements Agent interface for OpenAI-compatible services.
 *
 * This adapter provides a consistent interface across different local and
 * self-hosted inference engines by using the OpenAI SDK with a custom base URL.
 *
 * Features:
 * - Works with 8+ OpenAI-compatible inference services
 * - Streaming support
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Provider metadata for debugging and monitoring
 * - Automatic message format conversion
 *
 * Usage:
 *
 *   // vLLM local deployment
 *   const agent = new OpenAICompatibleAgent({
 *     baseURL: 'http://localhost:8000/v1',
 *     model: 'meta-llama/Llama-2-7b-chat-hf',
 *     provider: 'vllm',
 *   });
 *
 *   // Basic completion
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'What is machine learning?',
 *   });
 *   console.log(response.content);
 *
 *   // Streaming
 *   for await (const chunk of agent.processStream(message)) {
 *     process.stdout.write(chunk.content as string);
 *   }
 *
 *   // Access metadata
 *   console.log(response.metadata?.provider);  // "vllm"
 *   console.log(response.metadata?.baseURL);   // "http://localhost:8000/v1"
 */
export class OpenAICompatibleAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];

  private client: OpenAI;
  private model: string;
  private provider: string;
  private baseURL: string;
  private temperature: number;
  private maxTokens: number;
  private topP: number;
  private options: Partial<OpenAI.Chat.ChatCompletionCreateParams>;

  constructor(config: OpenAICompatibleConfig) {
    // Set provider and name
    this.provider = config.provider || 'openai_compatible';
    this.name = config.name || this.provider;

    // Initialize OpenAI client with custom base URL
    this.client = new OpenAI({
      baseURL: config.baseURL,
      apiKey: config.apiKey || 'not-needed',
      timeout: config.timeout || 60000,
    });

    this.model = config.model;
    this.baseURL = config.baseURL;
    this.temperature = config.temperature ?? 0.7;
    this.maxTokens = config.maxTokens || 1024;
    this.topP = config.topP ?? 1.0;
    this.options = config.options || {};

    // Set capabilities based on provider
    this.capabilities = [
      'openai-compatible',
      'chat',
      'streaming',
      this.provider,
    ];
  }

  /**
   * Convert agenkit Message to OpenAI message format.
   *
   * OpenAI-compatible services expect messages in the format:
   * - role: "system", "user", or "assistant"
   * - content: string
   *
   * Agenkit uses generic roles which get mapped to OpenAI format.
   */
  private toOpenAIMessage(
    message: Message,
  ): OpenAI.Chat.ChatCompletionMessageParam {
    const content =
      typeof message.content === 'string'
        ? message.content
        : JSON.stringify(message.content);

    // Map roles for OpenAI compatibility
    let role: 'system' | 'user' | 'assistant';
    if (message.role === 'system') {
      role = 'system';
    } else if (message.role === 'assistant' || message.role === 'agent') {
      role = 'assistant';
    } else {
      role = 'user';
    }

    return { role, content };
  }

  /**
   * Process a message using the OpenAI-compatible service.
   *
   * @param message Input message
   * @returns Response message with metadata including:
   *   - model: Model identifier used
   *   - usage: Token counts (prompt_tokens, completion_tokens, total_tokens)
   *   - finish_reason: Why generation stopped
   *   - provider: Provider name for debugging
   *   - baseURL: Service URL for debugging
   *   - id: Response ID from the service
   */
  async process(message: Message): Promise<Message> {
    const openaiMessage = this.toOpenAIMessage(message);

    // Spreading `...this.options` defeats TS's literal-narrowing on
    // `stream: false`, so the result is typed as the streaming/non-streaming
    // union. We pass stream:false, so assert the non-streaming response.
    const response = (await this.client.chat.completions.create({
      model: this.model,
      messages: [openaiMessage],
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      top_p: this.topP,
      ...this.options,
      stream: false,
    })) as OpenAI.Chat.ChatCompletion;

    // Check for valid response
    if (!response.choices || response.choices.length === 0) {
      throw new Error('Service returned no choices');
    }

    const choice = response.choices[0];
    const content = choice.message.content || '';

    return createMessage('assistant', content, {
      model: response.model,
      usage: {
        prompt_tokens: response.usage?.prompt_tokens || 0,
        completion_tokens: response.usage?.completion_tokens || 0,
        total_tokens: response.usage?.total_tokens || 0,
      },
      finish_reason: choice.finish_reason,
      id: response.id,
      provider: this.provider,
      baseURL: this.baseURL,
    });
  }

  /**
   * Process a message with streaming response.
   *
   * This method streams response chunks as they're generated by the service,
   * enabling real-time display and lower perceived latency.
   *
   * @param message Input message
   * @returns Async iterator of response chunks
   *
   * Example:
   *
   *   const message = { role: 'user', content: 'Count to 10' };
   *   for await (const chunk of agent.processStream(message)) {
   *     process.stdout.write(chunk.content as string);
   *   }
   *
   * Note: Not all OpenAI-compatible services support streaming. If the service
   * doesn't support it, you'll get an error from the underlying service.
   */
  async *processStream(
    message: Message,
  ): AsyncGenerator<Message, void, undefined> {
    const openaiMessage = this.toOpenAIMessage(message);

    // See process(): the options spread defeats stream-literal narrowing, so
    // assert the streaming response type (we pass stream:true).
    const stream = (await this.client.chat.completions.create({
      model: this.model,
      messages: [openaiMessage],
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      top_p: this.topP,
      ...this.options,
      stream: true,
    })) as AsyncIterable<OpenAI.Chat.ChatCompletionChunk>;

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        yield createMessage('assistant', delta.content, {
          model: this.model,
          streaming: true,
          provider: this.provider,
        });
      }
    }
  }

  /**
   * Get the underlying OpenAI client.
   *
   * This provides an escape hatch for accessing OpenAI SDK features
   * not exposed by the minimal Agent interface.
   *
   * Warning: Using getClient() breaks provider portability. Code that uses
   * getClient() will need changes when switching between services.
   */
  getClient(): OpenAI {
    return this.client;
  }
}
