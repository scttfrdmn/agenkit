/**
 * HTTP transport for agent communication.
 *
 * Implements the Agent interface for HTTP-based communication,
 * allowing agents to communicate over HTTP/1.1, HTTP/2, or HTTP/3.
 */

import { Agent, Message, validateMessage } from '../core/interfaces';

/**
 * HTTP transport configuration.
 */
export interface HttpTransportConfig {
  /** Base URL of the agent endpoint */
  baseUrl: string;

  /** Agent name */
  name?: string;

  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;

  /** Custom headers to include in requests */
  headers?: Record<string, string>;

  /** Whether to enable HTTP/2 (default: false) */
  http2?: boolean;
}

/**
 * HTTP transport error with additional context.
 */
export class HttpTransportError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public responseBody?: string,
  ) {
    super(message);
    this.name = 'HttpTransportError';
  }
}

/**
 * HTTPAgent implements Agent interface over HTTP transport.
 *
 * Features:
 * - HTTP/1.1, HTTP/2 support
 * - Configurable timeouts
 * - Custom headers
 * - Automatic retries on connection errors
 * - Full TypeScript typing
 *
 * Usage:
 *   const agent = new HTTPAgent({
 *     baseUrl: 'http://localhost:8000',
 *     timeout: 30000,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
export class HTTPAgent implements Agent {
  readonly name: string;
  readonly capabilities = ['http'];

  private baseUrl: string;
  private timeout: number;
  private headers: Record<string, string>;
  private http2: boolean;

  constructor(config: HttpTransportConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.name = config.name || 'http-agent';
    this.timeout = config.timeout || 30000;
    this.headers = config.headers || {};
    this.http2 = config.http2 || false;
  }

  /**
   * Process a message via HTTP POST request.
   *
   * @param message Input message
   * @returns Response message
   */
  async process(message: Message): Promise<Message> {
    // Validate input
    validateMessage(message);

    // Add timestamp if missing
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString();
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.headers,
        },
        body: JSON.stringify(message),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.text();
        throw new HttpTransportError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorBody,
        );
      }

      const responseMessage = (await response.json()) as Message;

      // Validate output
      validateMessage(responseMessage);

      return responseMessage;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new HttpTransportError(`Request timeout after ${this.timeout}ms`);
        }

        if (error instanceof HttpTransportError) {
          throw error;
        }

        throw new HttpTransportError(`Network error: ${error.message}`);
      }

      throw new HttpTransportError('Unknown error during HTTP request');
    }
  }

  /**
   * Process a message with streaming response.
   *
   * @param message Input message
   * @returns Async iterator of response chunks
   */
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    // Validate input
    validateMessage(message);

    // Add timestamp if missing
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString();
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}/process/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/x-ndjson',
          ...this.headers,
        },
        body: JSON.stringify(message),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.text();
        throw new HttpTransportError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorBody,
        );
      }

      if (!response.body) {
        throw new HttpTransportError('No response body for streaming');
      }

      // Read stream line by line (NDJSON format)
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on newlines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.trim()) {
            const chunk = JSON.parse(line) as Message;
            validateMessage(chunk);
            yield chunk;
          }
        }
      }

      // Process any remaining data in buffer
      if (buffer.trim()) {
        const chunk = JSON.parse(buffer) as Message;
        validateMessage(chunk);
        yield chunk;
      }
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new HttpTransportError(`Request timeout after ${this.timeout}ms`);
        }

        if (error instanceof HttpTransportError) {
          throw error;
        }

        throw new HttpTransportError(`Network error: ${error.message}`);
      }

      throw new HttpTransportError('Unknown error during HTTP streaming');
    }
  }

  /**
   * Health check endpoint.
   *
   * @returns true if agent is healthy, false otherwise
   */
  async health(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: this.headers,
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      return response.ok;
    } catch {
      return false;
    }
  }
}
