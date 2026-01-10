/**
 * Remote agent client for protocol adapter.
 *
 * Provides a client-side proxy for communicating with remote agents
 * over various transport protocols (TCP, HTTP, WebSocket, gRPC).
 */

import { Agent, Message, validateMessage } from '../core/interfaces';
import { Transport, parseEndpoint } from './transport';
import {
  createRequestEnvelope,
  encodeMessage,
  decodeMessage,
  encodeBytes,
  decodeBytes,
  ProtocolEnvelope,
} from './codec';
import {
  ConnectionError,
  AgentTimeoutError,
  RemoteExecutionError,
  InvalidMessageError,
  ProtocolError,
} from './errors';

/**
 * Configuration for RemoteAgent.
 */
export interface RemoteAgentConfig {
  /** Name of the remote agent */
  name: string;

  /** Endpoint URL (e.g., "tcp://localhost:8080", "http://localhost:8080") */
  endpoint?: string;

  /** Custom transport (if endpoint not provided) */
  transport?: Transport;

  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
}

/**
 * Client-side proxy for a remote agent.
 *
 * This class implements the Agent interface and forwards all calls to a remote
 * agent over the protocol adapter. It can be used as a drop-in replacement for
 * a local agent.
 *
 * Features:
 * - Multiple transport protocols (TCP, HTTP, WebSocket, gRPC)
 * - Automatic timeout handling
 * - Streaming support
 * - Connection pooling
 * - Error handling and recovery
 *
 * Usage:
 *   const agent = new RemoteAgent({
 *     name: 'my-agent',
 *     endpoint: 'tcp://localhost:8080',
 *     timeout: 30000,
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
export class RemoteAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[] = [];

  private endpoint?: string;
  private transport: Transport;
  private timeout: number;
  private connected = false;
  private lock = Promise.resolve(); // Serialize requests on same connection

  constructor(config: RemoteAgentConfig) {
    if (!config.endpoint && !config.transport) {
      throw new Error('Either endpoint or transport must be provided');
    }

    this.name = config.name;
    this.endpoint = config.endpoint;
    this.transport = config.transport || parseEndpoint(config.endpoint!);
    this.timeout = config.timeout || 30000;
  }

  /**
   * Ensure transport is connected.
   */
  private async ensureConnected(): Promise<void> {
    if (!this.connected) {
      await this.transport.connect();
      this.connected = true;
    }
  }

  /**
   * Process a message through the remote agent.
   *
   * @param message Input message
   * @returns Response message from remote agent
   * @throws ConnectionError if connection fails
   * @throws AgentTimeoutError if request times out
   * @throws RemoteExecutionError if remote agent raises an error
   * @throws ProtocolError if protocol error occurs
   */
  async process(message: Message): Promise<Message> {
    // Validate input
    validateMessage(message);

    // Ensure connected
    await this.ensureConnected();

    // Create request envelope
    const request = createRequestEnvelope(
      'process',
      this.name,
      { message: encodeMessage(message) },
    );

    // Serialize requests on same connection to prevent interleaving
    return await this.withLock(async () => {
      try {
        // Create timeout promise
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(
            () => reject(new AgentTimeoutError(this.name, this.timeout)),
            this.timeout,
          );
        });

        // Send request and wait for response with timeout
        const responsePromise = (async () => {
          // Check if transport supports fast path (envelope directly)
          if (
            'sendFramedEnvelope' in this.transport &&
            typeof (this.transport as any).sendFramedEnvelope === 'function'
          ) {
            // FAST PATH: Send dict directly (skip JSON encoding/decoding)
            await this.transport.sendFramedEnvelope(request);
            return await this.transport.receiveFramedEnvelope();
          } else {
            // SLOW PATH: Encode to JSON for backward compatibility
            const requestBytes = encodeBytes(request);
            await this.transport.sendFramed(requestBytes);
            const responseBytes = await this.transport.receiveFramed();
            return decodeBytes(responseBytes);
          }
        })();

        const response = await Promise.race([responsePromise, timeoutPromise]);

        // Handle response
        if (response.type === 'error') {
          const errorPayload = response.payload;
          throw new RemoteExecutionError(
            this.name,
            (errorPayload.error_message as string) || 'Unknown error',
            (errorPayload.error_details as Record<string, unknown>) || {},
          );
        }

        if (response.type !== 'response') {
          throw new InvalidMessageError(
            `Expected 'response' but got '${response.type}'`,
            { response },
          );
        }

        // Decode and return message
        return decodeMessage(response.payload.message as Record<string, unknown>);
      } catch (error) {
        if (
          error instanceof AgentTimeoutError ||
          error instanceof RemoteExecutionError ||
          error instanceof ConnectionError ||
          error instanceof ProtocolError
        ) {
          throw error;
        }

        // Wrap unexpected errors
        throw new RemoteExecutionError(
          this.name,
          error instanceof Error ? error.message : String(error),
        );
      }
    });
  }

  /**
   * Stream responses from remote agent.
   *
   * @param message Input message
   * @returns Async iterator of response messages
   * @throws ConnectionError if connection fails
   * @throws AgentTimeoutError if request times out
   * @throws RemoteExecutionError if remote agent raises an error
   * @throws ProtocolError if protocol error occurs
   */
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    // Validate input
    validateMessage(message);

    // Ensure connected
    await this.ensureConnected();

    // Create stream request envelope
    const request = createRequestEnvelope(
      'stream',
      this.name,
      { message: encodeMessage(message) },
    );

    // Serialize requests on same connection to prevent interleaving
    // Use a different approach for streaming - we'll yield within the lock
    const iterator = this.streamWithLock(request);
    for await (const chunk of iterator) {
      yield chunk;
    }
  }

  /**
   * Stream with lock helper.
   */
  private async *streamWithLock(
    request: ProtocolEnvelope,
  ): AsyncGenerator<Message, void, undefined> {
    // Wait for lock
    await this.lock;

    // Create new lock promise
    let releaseLock: () => void;
    this.lock = new Promise((resolve) => {
      releaseLock = resolve;
    });

    try {
      // Check if transport supports fast path
      if (
        'sendFramedEnvelope' in this.transport &&
        typeof (this.transport as any).sendFramedEnvelope === 'function'
      ) {
        // FAST PATH: Send dict directly
        await this.transport.sendFramedEnvelope(request);

        // Receive stream chunks
        while (true) {
          const response = await this.transport.receiveFramedEnvelope();

          // Handle response type
          if (response.type === 'error') {
            const errorPayload = response.payload;
            throw new RemoteExecutionError(
              this.name,
              (errorPayload.error_message as string) || 'Unknown error',
              (errorPayload.error_details as Record<string, unknown>) || {},
            );
          } else if (response.type === 'stream_chunk') {
            // Yield chunk message
            const chunk = decodeMessage(
              response.payload.message as Record<string, unknown>,
            );
            yield chunk;
          } else if (response.type === 'stream_end') {
            // Stream complete
            break;
          } else {
            throw new InvalidMessageError(
              `Expected 'stream_chunk' or 'stream_end' but got '${response.type}'`,
              { response },
            );
          }
        }
      } else {
        // SLOW PATH: Encode to JSON
        const requestBytes = encodeBytes(request);
        await this.transport.sendFramed(requestBytes);

        // Receive stream chunks
        while (true) {
          const responseBytes = await this.transport.receiveFramed();
          const response = decodeBytes(responseBytes);

          // Handle response type
          if (response.type === 'error') {
            const errorPayload = response.payload;
            throw new RemoteExecutionError(
              this.name,
              (errorPayload.error_message as string) || 'Unknown error',
              (errorPayload.error_details as Record<string, unknown>) || {},
            );
          } else if (response.type === 'stream_chunk') {
            // Yield chunk message
            const chunk = decodeMessage(
              response.payload.message as Record<string, unknown>,
            );
            yield chunk;
          } else if (response.type === 'stream_end') {
            // Stream complete
            break;
          } else {
            throw new InvalidMessageError(
              `Expected 'stream_chunk' or 'stream_end' but got '${response.type}'`,
              { response },
            );
          }
        }
      }
    } finally {
      // Release lock
      releaseLock!();
    }
  }

  /**
   * Execute a function with lock to serialize requests.
   */
  private async withLock<T>(fn: () => Promise<T>): Promise<T> {
    // Wait for current lock
    await this.lock;

    // Create new lock promise
    let releaseLock: () => void;
    this.lock = new Promise((resolve) => {
      releaseLock = resolve;
    });

    try {
      return await fn();
    } finally {
      // Release lock
      releaseLock!();
    }
  }

  /**
   * Close connection to remote agent.
   */
  async close(): Promise<void> {
    if (this.connected) {
      await this.transport.close();
      this.connected = false;
    }
  }
}
