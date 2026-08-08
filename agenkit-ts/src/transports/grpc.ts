/**
 * gRPC Transport - Efficient RPC-based agent communication
 *
 * Provides high-performance communication using gRPC with Protocol Buffers.
 * Supports unary RPC, server streaming, and bidirectional streaming.
 *
 * @packageDocumentation
 */

import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import { Agent, Message } from '../core/interfaces';
import * as path from 'path';

// ── Internal proto types ──────────────────────────────────────────────────────
// These mirror the protobuf message shapes defined in proto/agent.proto.

/** A message as represented in the proto wire format */
interface GrpcProtoMessage {
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

/** A gRPC error object returned in response/chunk envelopes */
interface GrpcProtoError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

/** Unary Process RPC response */
interface GrpcProtoResponse {
  version: string;
  id: string;
  timestamp: string;
  type: string;
  message?: GrpcProtoMessage;
  error?: GrpcProtoError;
  metadata?: Record<string, unknown>;
}

/** A streaming chunk returned by ProcessStream */
type GrpcProtoChunk = GrpcProtoResponse;

/** Event-emitting stream returned by client.ProcessStream() */
interface GrpcCallStream {
  on(event: 'data', callback: (chunk: GrpcProtoChunk) => void): this;
  on(event: 'error', callback: (error: Error) => void): this;
  on(event: 'end', callback: () => void): this;
  cancel(): void;
}

/** The gRPC client stub generated from the AgentService proto definition */
interface GrpcAgentServiceClient {
  Process(
    request: Record<string, unknown>,
    options: { deadline?: number },
    callback: (error: grpc.ServiceError | null, response: GrpcProtoResponse) => void,
  ): void;
  ProcessStream(request: Record<string, unknown>): GrpcCallStream;
  close(): void;
}

/** The loaded agenkit proto package — provides the AgentService constructor */
interface GrpcProtoPackage {
  AgentService: (new (
    address: string,
    credentials: grpc.ChannelCredentials,
  ) => GrpcAgentServiceClient) & { service: grpc.ServiceDefinition };
}

/**
 * gRPC client configuration
 */
export interface GrpcTransportConfig {
  /** gRPC server address (e.g., "localhost:50051") */
  address: string;
  /** Agent name for routing */
  agentName?: string;
  /** Connection timeout in milliseconds */
  timeout?: number;
  /** Enable TLS/SSL */
  useTLS?: boolean;
  /** TLS credentials (if useTLS is true) */
  credentials?: grpc.ChannelCredentials;
}

/**
 * gRPC server configuration
 */
export interface GrpcServerConfig {
  /** gRPC server address (e.g., "0.0.0.0:50051") */
  address: string;
  /** Enable TLS/SSL */
  useTLS?: boolean;
  /** TLS server credentials (if useTLS is true) */
  credentials?: grpc.ServerCredentials;
}

/**
 * gRPC transport error
 */
export class GrpcTransportError extends Error {
  constructor(
    message: string,
    public code: grpc.status,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'GrpcTransportError';
  }
}

/**
 * GrpcAgent - Client for communicating with remote agents via gRPC
 *
 * @example
 * ```typescript
 * const agent = new GrpcAgent('my-agent', {
 *   address: 'localhost:50051'
 * });
 *
 * const response = await agent.process({
 *   role: 'user',
 *   content: 'Hello'
 * });
 * ```
 */
export class GrpcAgent implements Agent {
  private client: GrpcAgentServiceClient | null = null;
  private packageDefinition: protoLoader.PackageDefinition;
  private proto: GrpcProtoPackage;
  private connected: boolean = false;

  constructor(
    private _name: string,
    private config: GrpcTransportConfig,
  ) {
    // Load proto file
    const PROTO_PATH = path.join(__dirname, '../../proto/agent.proto');
    this.packageDefinition = protoLoader.loadSync(PROTO_PATH, {
      keepCase: false,  // Use camelCase for field names
      longs: String,
      enums: String,
      defaults: false,  // Don't apply default values
      oneofs: true,
    });

    // Load gRPC package
    this.proto = grpc.loadPackageDefinition(this.packageDefinition).agenkit as unknown as GrpcProtoPackage;
  }

  get name(): string {
    return this._name;
  }

  /**
   * Connect to the gRPC server
   */
  async connect(): Promise<void> {
    if (this.connected) {
      return;
    }

    const credentials = this.config.useTLS
      ? this.config.credentials || grpc.credentials.createSsl()
      : grpc.credentials.createInsecure();

    this.client = new (this.proto.AgentService)(this.config.address, credentials);
    this.connected = true;
  }

  /**
   * Disconnect from the gRPC server
   */
  async close(): Promise<void> {
    if (this.client) {
      this.client.close();
      this.connected = false;
    }
  }

  /**
   * Process a message using unary RPC
   */
  async process(message: Message): Promise<Message> {
    if (!this.connected) {
      await this.connect();
    }

    const request = {
      version: '1.0',
      id: this.generateId(),
      timestamp: new Date().toISOString(),
      method: 'process',
      agent_name: this.config.agentName || this._name,
      messages: [this.messageToProto(message)],
      metadata: message.metadata || {},
    };

    return new Promise((resolve, reject) => {
      const deadline = this.config.timeout
        ? Date.now() + this.config.timeout
        : undefined;

      this.client!.Process(
        request,
        { deadline },
        (error: grpc.ServiceError | null, response: GrpcProtoResponse) => {
          if (error) {
            reject(
              new GrpcTransportError(
                error.message,
                error.code,
                error.details,
              ),
            );
            return;
          }

          if (response.type === 'RESPONSE_TYPE_ERROR' || response.error) {
            reject(
              new GrpcTransportError(
                response.error?.message || 'Unknown error',
                grpc.status.UNKNOWN,
                response.error?.details,
              ),
            );
            return;
          }

          if (!response.message) {
            reject(
              new GrpcTransportError(
                'Response missing message payload',
                grpc.status.UNKNOWN,
              ),
            );
            return;
          }

          resolve(this.protoToMessage(response.message));
        },
      );
    });
  }

  /**
   * Process a message with streaming response
   */
  async *processStream(message: Message): AsyncGenerator<Message> {
    if (!this.connected) {
      await this.connect();
    }

    const request = {
      version: '1.0',
      id: this.generateId(),
      timestamp: new Date().toISOString(),
      method: 'stream',
      agent_name: this.config.agentName || this._name,
      messages: [this.messageToProto(message)],
      metadata: message.metadata || {},
    };

    const call = this.client!.ProcessStream(request);

    try {
      for await (const chunk of this.streamToAsyncIterator(call)) {
        if (chunk.type === 'CHUNK_TYPE_ERROR' || chunk.error) {
          throw new GrpcTransportError(
            chunk.error?.message || 'Stream error',
            grpc.status.UNKNOWN,
            chunk.error?.details,
          );
        }

        if (chunk.type === 'CHUNK_TYPE_END') {
          break;
        }

        if (chunk.message) {
          yield this.protoToMessage(chunk.message);
        }
      }
    } finally {
      call.cancel();
    }
  }

  /**
   * Convert gRPC stream to async iterator
   */
  private async *streamToAsyncIterator(call: GrpcCallStream): AsyncGenerator<GrpcProtoChunk> {
    const queue: GrpcProtoChunk[] = [];
    let error: Error | null = null;
    let done = false;

    call.on('data', (chunk: GrpcProtoChunk) => {
      queue.push(chunk);
    });

    call.on('error', (err: Error) => {
      error = err;
    });

    call.on('end', () => {
      done = true;
    });

    while (!done || queue.length > 0) {
      if (error) {
        throw error;
      }

      if (queue.length > 0) {
        yield queue.shift()!;
      } else {
        // Wait a bit before checking again
        await new Promise((resolve) => setTimeout(resolve, 10));
      }
    }
  }

  /**
   * Convert Message to proto format
   */
  private messageToProto(message: Message): GrpcProtoMessage {
    return {
      role: message.role,
      content: typeof message.content === 'string' ? message.content : JSON.stringify(message.content),
      metadata: (message.metadata as Record<string, unknown>) || {},
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Convert proto message to Message
   */
  private protoToMessage(proto: GrpcProtoMessage): Message {
    return {
      role: proto.role,
      content: proto.content,
      metadata: proto.metadata || {},
    };
  }

  /**
   * Generate unique request ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * GrpcServer - Server for hosting agents via gRPC
 *
 * @example
 * ```typescript
 * const server = new GrpcServer(myAgent, {
 *   address: '0.0.0.0:50051'
 * });
 *
 * await server.start();
 * ```
 */
export class GrpcServer {
  private server: grpc.Server;
  private proto: GrpcProtoPackage;
  private packageDefinition: protoLoader.PackageDefinition;
  private boundPort: number | null = null;

  constructor(
    private agent: Agent,
    private config: GrpcServerConfig,
  ) {
    // Load proto file
    const PROTO_PATH = path.join(__dirname, '../../proto/agent.proto');
    this.packageDefinition = protoLoader.loadSync(PROTO_PATH, {
      keepCase: false,  // Use camelCase for field names
      longs: String,
      enums: String,
      defaults: false,  // Don't apply default values
      oneofs: true,
    });

    // Load gRPC package
    this.proto = grpc.loadPackageDefinition(this.packageDefinition).agenkit as unknown as GrpcProtoPackage;

    // Create server
    this.server = new grpc.Server();

    // Add service
    this.server.addService(this.proto.AgentService.service, {
      Process: this.handleProcess.bind(this),
      ProcessStream: this.handleProcessStream.bind(this),
      BidirectionalStream: this.handleBidirectionalStream.bind(this),
    });
  }

  /**
   * Start the gRPC server
   */
  async start(): Promise<void> {
    const credentials = this.config.useTLS
      ? this.config.credentials || grpc.ServerCredentials.createSsl(null, [])
      : grpc.ServerCredentials.createInsecure();

    return new Promise((resolve, reject) => {
      this.server.bindAsync(this.config.address, credentials, (error, port) => {
        if (error) {
          reject(error);
          return;
        }

        this.boundPort = port;
        this.server.start();
        resolve();
      });
    });
  }

  /**
   * Stop the gRPC server
   */
  async stop(): Promise<void> {
    return new Promise((resolve) => {
      this.server.tryShutdown(() => {
        resolve();
      });
    });
  }

  /**
   * The actual address the server is bound to, e.g. "127.0.0.1:54321".
   *
   * When `config.address` requests an ephemeral port (port `0`), the OS
   * assigns the real port only once `bindAsync`'s callback fires, so this
   * must be read back after `start()` resolves rather than assumed from
   * the configured address.
   */
  address(): string {
    if (this.boundPort === null) {
      throw new Error('GrpcServer.address() called before start(); no port has been bound yet');
    }

    const host = this.config.address.slice(0, this.config.address.lastIndexOf(':'));
    return `${host}:${this.boundPort}`;
  }

  /**
   * Handle unary Process RPC
   */
  private async handleProcess(
    call: grpc.ServerUnaryCall<any, any>,
    callback: grpc.sendUnaryData<any>,
  ): Promise<void> {
    try {
      const request = call.request;
      const message = this.protoToMessage(request.messages[0]);

      const response = await this.agent.process(message);

      callback(null, {
        version: '1.0',
        id: request.id,
        timestamp: new Date().toISOString(),
        type: 'RESPONSE_TYPE_MESSAGE',
        message: this.messageToProto(response),
        metadata: response.metadata || {},
      });
    } catch (error: unknown) {
      callback(null, {
        version: '1.0',
        id: call.request.id,
        timestamp: new Date().toISOString(),
        type: 'RESPONSE_TYPE_ERROR',
        error: {
          code: 'INTERNAL_ERROR',
          message: error instanceof Error ? error.message : String(error),
          details: {},
        },
      });
    }
  }

  /**
   * Handle streaming ProcessStream RPC
   */
  private async handleProcessStream(
    call: grpc.ServerWritableStream<any, any>,
  ): Promise<void> {
    try {
      const request = call.request;
      const message = this.protoToMessage(request.messages[0]);

      // Check if agent supports streaming
      if ('processStream' in this.agent && typeof this.agent.processStream === 'function') {
        const stream = this.agent.processStream(message);

        for await (const chunk of stream) {
          call.write({
            version: '1.0',
            id: request.id,
            timestamp: new Date().toISOString(),
            type: 'CHUNK_TYPE_MESSAGE',
            message: this.messageToProto(chunk),
          });
        }
      } else {
        // Fallback to regular process
        const response = await this.agent.process(message);
        call.write({
          version: '1.0',
          id: request.id,
          timestamp: new Date().toISOString(),
          type: 'CHUNK_TYPE_MESSAGE',
          message: this.messageToProto(response),
        });
      }

      // Send end marker
      call.write({
        version: '1.0',
        id: request.id,
        timestamp: new Date().toISOString(),
        type: 'CHUNK_TYPE_END',
      });

      call.end();
    } catch (error: unknown) {
      call.write({
        version: '1.0',
        id: call.request.id,
        timestamp: new Date().toISOString(),
        type: 'CHUNK_TYPE_ERROR',
        error: {
          code: 'INTERNAL_ERROR',
          message: error instanceof Error ? error.message : String(error),
          details: {},
        },
      });
      call.end();
    }
  }

  /**
   * Handle bidirectional BidirectionalStream RPC
   */
  private async handleBidirectionalStream(
    call: grpc.ServerDuplexStream<any, any>,
  ): Promise<void> {
    call.on('data', async (request: { id: string; messages: GrpcProtoMessage[] }) => {
      try {
        const message = this.protoToMessage(request.messages[0]);
        const response = await this.agent.process(message);

        call.write({
          version: '1.0',
          id: request.id,
          timestamp: new Date().toISOString(),
          type: 'RESPONSE_TYPE_MESSAGE',
          message: this.messageToProto(response),
          metadata: response.metadata || {},
        });
      } catch (error: unknown) {
        call.write({
          version: '1.0',
          id: request.id,
          timestamp: new Date().toISOString(),
          type: 'RESPONSE_TYPE_ERROR',
          error: {
            code: 'INTERNAL_ERROR',
            message: error instanceof Error ? error.message : String(error),
            details: {},
          },
        });
      }
    });

    call.on('end', () => {
      call.end();
    });

    call.on('error', (error) => {
      console.error('Bidirectional stream error:', error);
      call.end();
    });
  }

  /**
   * Convert proto message to Message
   */
  private protoToMessage(proto: GrpcProtoMessage): Message {
    return {
      role: proto.role,
      content: proto.content,
      metadata: proto.metadata || {},
    };
  }

  /**
   * Convert Message to proto format
   */
  private messageToProto(message: Message): GrpcProtoMessage {
    return {
      role: message.role,
      content: typeof message.content === 'string' ? message.content : JSON.stringify(message.content),
      metadata: (message.metadata as Record<string, unknown>) || {},
      timestamp: new Date().toISOString(),
    };
  }
}
