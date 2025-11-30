/**
 * Ollama LLM adapter for local model inference.
 *
 * Provides integration with Ollama for running local LLMs like Llama 2, Mistral,
 * CodeLlama, and other models. Ideal for development, testing, and on-premises
 * deployments without API costs.
 *
 * @example
 * ```typescript
 * import { OllamaAdapter } from './adapters/ollama';
 *
 * const adapter = new OllamaAdapter({
 *   model: 'llama2',
 *   baseURL: 'http://localhost:11434',
 *   temperature: 0.7,
 * });
 *
 * const response = await adapter.process({
 *   role: 'user',
 *   content: 'Hello, Llama!',
 * });
 * console.log(response.content);
 * ```
 *
 * Setup:
 * 1. Install Ollama: https://ollama.ai/download
 * 2. Pull a model: `ollama pull llama2`
 * 3. Verify: `ollama list`
 * 4. Use with AgentKit!
 */

import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';

/**
 * Configuration for Ollama adapter.
 */
export interface OllamaConfig {
  /** Model to use (e.g., 'llama2', 'mistral', 'codellama') */
  model?: string;

  /** Ollama server base URL */
  baseURL?: string;

  /** Temperature for sampling (0.0 - 2.0) */
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
 * Message format for Ollama API.
 */
interface OllamaMessage {
  role: string;
  content: string;
}

/**
 * Request format for Ollama chat API.
 */
interface OllamaChatRequest {
  model: string;
  messages: OllamaMessage[];
  stream: boolean;
  options?: {
    temperature?: number;
    num_predict?: number;
    top_p?: number;
    top_k?: number;
  };
}

/**
 * Response format from Ollama chat API.
 */
interface OllamaChatResponse {
  model: string;
  created_at: string;
  message: {
    role: string;
    content: string;
  };
  done: boolean;
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
}

/**
 * Ollama adapter implementing the Agent interface.
 *
 * Features:
 * - Support for Llama 2, Mistral, CodeLlama, and other Ollama models
 * - Local inference (no API key required)
 * - Zero cost for development and testing
 * - Privacy-preserving (data never leaves your machine)
 * - Configurable parameters (temperature, max_tokens, etc.)
 * - Automatic message format conversion
 */
export class OllamaAdapter implements Agent {
  private config: Required<OllamaConfig>;

  /**
   * Creates a new Ollama adapter.
   *
   * @param config - Configuration options
   */
  constructor(config: OllamaConfig = {}) {
    this.config = {
      model: config.model || 'llama2',
      baseURL: config.baseURL || 'http://localhost:11434',
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens ?? 1024,
      topP: config.topP ?? 1.0,
      topK: config.topK ?? 40,
      timeout: config.timeout ?? 120000, // 2 minutes for local inference
    };
  }

  /**
   * Agent name for identification.
   */
  get name(): string {
    return `ollama-${this.config.model}`;
  }

  /**
   * Agent capabilities.
   */
  get capabilities(): string[] {
    return ['completion', 'local-inference', 'no-api-key'];
  }

  /**
   * Process a message through Ollama.
   *
   * @param message - Input message
   * @returns Response message with content and metadata
   */
  async process(message: Message): Promise<Message> {
    validateMessage(message);

    // Convert single message to array for API
    const messages: OllamaMessage[] = [{
      role: message.role,
      content: message.content,
    }];

    // Build request
    const request: OllamaChatRequest = {
      model: this.config.model,
      messages,
      stream: false,
      options: {
        temperature: this.config.temperature,
        num_predict: this.config.maxTokens,
        top_p: this.config.topP,
        top_k: this.config.topK,
      },
    };

    try {
      // Make HTTP request to Ollama
      const response = await fetch(`${this.config.baseURL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama API error (${response.status}): ${errorText}`);
      }

      const data: OllamaChatResponse = await response.json();

      // Build metadata
      const metadata: Record<string, any> = {
        model: data.model,
        created_at: data.created_at,
      };

      if (data.total_duration) {
        metadata.total_duration_ms = data.total_duration / 1_000_000;
      }

      if (data.prompt_eval_count || data.eval_count) {
        metadata.usage = {
          prompt_tokens: data.prompt_eval_count || 0,
          completion_tokens: data.eval_count || 0,
          total_tokens: (data.prompt_eval_count || 0) + (data.eval_count || 0),
        };
      }

      // Create response message
      return createMessage({
        role: data.message.role,
        content: data.message.content,
        metadata,
      });
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error(`Ollama request timeout after ${this.config.timeout}ms`);
        }
        throw new Error(`Ollama request failed: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Stream a response from Ollama (not yet implemented).
   *
   * @param message - Input message
   * @returns Async iterator of response chunks
   */
  async *stream(message: Message): AsyncGenerator<Message, void, unknown> {
    validateMessage(message);

    // Convert single message to array for API
    const messages: OllamaMessage[] = [{
      role: message.role,
      content: message.content,
    }];

    // Build request
    const request: OllamaChatRequest = {
      model: this.config.model,
      messages,
      stream: true,
      options: {
        temperature: this.config.temperature,
        num_predict: this.config.maxTokens,
        top_p: this.config.topP,
        top_k: this.config.topK,
      },
    };

    try {
      // Make HTTP request to Ollama
      const response = await fetch(`${this.config.baseURL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama API error (${response.status}): ${errorText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      // Parse streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split by newlines to handle multiple JSON objects
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep last incomplete line in buffer

        for (const line of lines) {
          if (line.trim()) {
            try {
              const data: OllamaChatResponse = JSON.parse(line);

              // Yield chunk
              yield createMessage({
                role: data.message.role,
                content: data.message.content,
                metadata: {
                  model: data.model,
                  done: data.done,
                },
              });

              if (data.done) {
                return;
              }
            } catch (e) {
              // Skip malformed JSON lines
              continue;
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error(`Ollama stream timeout after ${this.config.timeout}ms`);
        }
        throw new Error(`Ollama stream failed: ${error.message}`);
      }
      throw error;
    }
  }
}
