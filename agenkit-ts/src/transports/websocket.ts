/**
 * WebSocket transport for agent communication.
 *
 * Implements the Agent interface for WebSocket-based communication,
 * providing real-time bidirectional communication with automatic reconnection.
 */

import WebSocket from 'ws';
import { Agent, Message, validateMessage } from '../core/interfaces';

/**
 * WebSocket transport configuration.
 */
export interface WebSocketTransportConfig {
  /** WebSocket URL (ws:// or wss://) */
  url: string;

  /** Agent name */
  name?: string;

  /** Maximum reconnection attempts (default: 5) */
  maxRetries?: number;

  /** Initial retry delay in milliseconds (default: 1000) */
  initialRetryDelay?: number;

  /** Ping interval in milliseconds (default: 30000) */
  pingInterval?: number;

  /** Ping timeout in milliseconds (default: 10000) */
  pingTimeout?: number;

  /** Custom headers for connection */
  headers?: Record<string, string>;
}

/**
 * WebSocket transport error.
 */
export class WebSocketTransportError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = 'WebSocketTransportError';
  }
}

/**
 * WebSocketAgent implements Agent interface over WebSocket transport.
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Ping/pong keepalive
 * - Binary and text frame support
 * - Request/response correlation
 * - Full TypeScript typing
 *
 * Usage:
 *   const agent = new WebSocketAgent({
 *     url: 'ws://localhost:8080',
 *     maxRetries: 5,
 *   });
 *
 *   await agent.connect();
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
export class WebSocketAgent implements Agent {
  readonly name: string;
  readonly capabilities = ['websocket'];

  private url: string;
  private maxRetries: number;
  private initialRetryDelay: number;
  private pingInterval: number;
  private pingTimeout: number;
  private headers: Record<string, string>;

  private ws: WebSocket | null = null;
  private connected = false;
  private reconnectLock = false;
  private pendingRequests = new Map<string, {
    resolve: (message: Message) => void;
    reject: (error: Error) => void;
  }>();
  private requestIdCounter = 0;
  private pingIntervalId: NodeJS.Timeout | null = null;

  constructor(config: WebSocketTransportConfig) {
    this.url = config.url;
    this.name = config.name || 'websocket-agent';
    this.maxRetries = config.maxRetries || 5;
    this.initialRetryDelay = config.initialRetryDelay || 1000;
    this.pingInterval = config.pingInterval || 30000;
    this.pingTimeout = config.pingTimeout || 10000;
    this.headers = config.headers || {};
  }

  /**
   * Establish WebSocket connection.
   */
  async connect(): Promise<void> {
    await this.connectWithRetry();
  }

  /**
   * Connect with exponential backoff retry logic.
   */
  private async connectWithRetry(): Promise<void> {
    let lastError: Error | null = null;
    let retryDelay = this.initialRetryDelay;

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        await this.establishConnection();
        this.setupPingInterval();
        return;
      } catch (error) {
        lastError = error as Error;

        if (attempt < this.maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          retryDelay *= 2; // Exponential backoff
        }
      }
    }

    throw new WebSocketTransportError(
      `Failed to connect after ${this.maxRetries} attempts: ${lastError?.message}`,
      'CONNECTION_FAILED'
    );
  }

  /**
   * Establish WebSocket connection.
   */
  private establishConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url, {
          headers: this.headers,
        });

        this.ws.on('open', () => {
          this.connected = true;
          resolve();
        });

        this.ws.on('error', (error) => {
          if (!this.connected) {
            reject(new WebSocketTransportError(
              `Connection error: ${error.message}`,
              'CONNECTION_ERROR'
            ));
          }
        });

        this.ws.on('close', () => {
          this.connected = false;
          this.cleanup();
        });

        this.ws.on('message', (data: WebSocket.Data) => {
          this.handleMessage(data);
        });

        this.ws.on('pong', () => {
          // Pong received, connection is alive
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Ensure connection is established, reconnect if necessary.
   */
  private async ensureConnected(): Promise<void> {
    if (!this.isConnected) {
      if (!this.reconnectLock) {
        this.reconnectLock = true;
        try {
          await this.connectWithRetry();
        } finally {
          this.reconnectLock = false;
        }
      } else {
        // Wait for ongoing reconnection
        while (this.reconnectLock) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
    }
  }

  /**
   * Setup ping interval for keepalive.
   */
  private setupPingInterval(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
    }

    this.pingIntervalId = setInterval(() => {
      if (this.ws && this.connected) {
        this.ws.ping();
      }
    }, this.pingInterval);
  }

  /**
   * Handle incoming WebSocket message.
   */
  private handleMessage(data: WebSocket.Data): void {
    try {
      const message = JSON.parse(data.toString()) as Message & { _requestId?: string };

      // Check if this is a response to a pending request
      if (message._requestId) {
        const pending = this.pendingRequests.get(message._requestId);
        if (pending) {
          this.pendingRequests.delete(message._requestId);
          // Remove internal field before resolving
          delete message._requestId;
          pending.resolve(message);
        }
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Process a message via WebSocket.
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

    // Ensure connected
    await this.ensureConnected();

    if (!this.ws) {
      throw new WebSocketTransportError('Not connected', 'NOT_CONNECTED');
    }

    // Generate request ID for correlation
    const requestId = `req_${++this.requestIdCounter}_${Date.now()}`;

    // Create promise for response
    const responsePromise = new Promise<Message>((resolve, reject) => {
      this.pendingRequests.set(requestId, { resolve, reject });

      // Set timeout
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId);
          reject(new WebSocketTransportError(
            'Request timeout',
            'TIMEOUT'
          ));
        }
      }, 30000); // 30 second timeout
    });

    // Send message with request ID
    const messageWithId = { ...message, _requestId: requestId };
    this.ws.send(JSON.stringify(messageWithId));

    return responsePromise;
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

    // Ensure connected
    await this.ensureConnected();

    if (!this.ws) {
      throw new WebSocketTransportError('Not connected', 'NOT_CONNECTED');
    }

    // Generate request ID
    const requestId = `stream_${++this.requestIdCounter}_${Date.now()}`;

    // Create async queue for chunks
    const chunkQueue: Message[] = [];
    let streamEnded = false;
    let streamError: Error | null = null;

    // Setup handler for this stream
    const originalHandler = this.ws.listeners('message')[0];

    const streamHandler = (data: WebSocket.Data) => {
      try {
        const msg = JSON.parse(data.toString()) as Message & {
          _requestId?: string;
          _streamEnd?: boolean;
        };

        if (msg._requestId === requestId) {
          if (msg._streamEnd) {
            streamEnded = true;
          } else {
            delete msg._requestId;
            chunkQueue.push(msg);
          }
        }
      } catch (error) {
        streamError = error as Error;
      }
    };

    this.ws.on('message', streamHandler);

    try {
      // Send streaming request
      const streamMessage = {
        ...message,
        _requestId: requestId,
        _stream: true
      };
      this.ws.send(JSON.stringify(streamMessage));

      // Yield chunks as they arrive
      while (!streamEnded && !streamError) {
        if (chunkQueue.length > 0) {
          yield chunkQueue.shift()!;
        } else {
          // Wait a bit before checking again
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      }

      // Yield any remaining chunks
      while (chunkQueue.length > 0) {
        yield chunkQueue.shift()!;
      }

      if (streamError) {
        throw streamError;
      }
    } finally {
      // Remove stream handler
      this.ws.removeListener('message', streamHandler);
    }
  }

  /**
   * Close WebSocket connection.
   */
  async close(): Promise<void> {
    this.cleanup();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Cleanup resources.
   */
  private cleanup(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }

    // Reject all pending requests
    for (const [requestId, pending] of this.pendingRequests) {
      pending.reject(new WebSocketTransportError(
        'Connection closed',
        'CONNECTION_CLOSED'
      ));
    }
    this.pendingRequests.clear();
  }

  /**
   * Check if WebSocket is connected.
   */
  get isConnected(): boolean {
    return this.connected && this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Health check.
   *
   * @returns true if connected, false otherwise
   */
  async health(): Promise<boolean> {
    return this.isConnected;
  }
}
