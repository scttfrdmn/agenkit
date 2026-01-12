/**
 * Transport layer for agent communication.
 *
 * Provides abstract base class for different transport implementations
 * (TCP, Unix sockets, HTTP, WebSocket, gRPC, etc.).
 */

import { ConnectionError, ConnectionClosedError, MalformedPayloadError } from './errors';
import { encodeBytes, decodeBytes, ProtocolEnvelope } from './codec';

export const MAX_MESSAGE_SIZE = 10 * 1024 * 1024; // 10 MB

/**
 * Abstract transport layer for agent communication.
 */
export abstract class Transport {
  /**
   * Establish connection.
   *
   * @throws ConnectionError if connection fails
   */
  abstract connect(): Promise<void>;

  /**
   * Send data over the transport.
   *
   * @param data Bytes to send
   * @throws ConnectionError if send fails
   * @throws ConnectionClosedError if connection is closed
   */
  abstract send(data: Buffer): Promise<void>;

  /**
   * Receive data from the transport.
   *
   * @returns Received bytes
   * @throws ConnectionError if receive fails
   * @throws ConnectionClosedError if connection is closed
   */
  abstract receive(): Promise<Buffer>;

  /**
   * Receive exactly n bytes.
   *
   * @param n Number of bytes to receive
   * @returns Exactly n bytes
   * @throws ConnectionError if receive fails
   * @throws ConnectionClosedError if connection closes before receiving all bytes
   */
  abstract receiveExactly(n: number): Promise<Buffer>;

  /**
   * Close the connection.
   */
  abstract close(): Promise<void>;

  /**
   * Check if transport is connected.
   *
   * @returns true if connected, false otherwise
   */
  abstract get isConnected(): boolean;

  /**
   * Send length-prefixed framed data.
   *
   * Frame format: [4-byte length (big-endian)] + [data]
   *
   * @param data Data to send
   * @throws Error if data exceeds maximum message size
   * @throws ConnectionError if send fails
   */
  async sendFramed(data: Buffer): Promise<void> {
    if (data.length > MAX_MESSAGE_SIZE) {
      throw new Error(
        `Message size ${data.length} exceeds maximum ${MAX_MESSAGE_SIZE}`,
      );
    }

    // Pack length as 4-byte big-endian unsigned integer
    const lengthPrefix = Buffer.alloc(4);
    lengthPrefix.writeUInt32BE(data.length, 0);

    await this.send(Buffer.concat([lengthPrefix, data]));
  }

  /**
   * Receive length-prefixed framed data.
   *
   * @returns Received data (without length prefix)
   * @throws ConnectionError if receive fails
   * @throws MalformedPayloadError if frame is invalid
   */
  async receiveFramed(): Promise<Buffer> {
    // Read 4-byte length prefix
    const lengthBytes = await this.receiveExactly(4);
    const length = lengthBytes.readUInt32BE(0);

    if (length > MAX_MESSAGE_SIZE) {
      throw new MalformedPayloadError(
        `Message size ${length} exceeds maximum ${MAX_MESSAGE_SIZE}`,
        { length },
      );
    }

    // Read exact payload
    return await this.receiveExactly(length);
  }

  /**
   * Send envelope dictionary directly (fast path for gRPC/protobuf).
   *
   * This is an optional optimization that allows transports to skip JSON
   * encoding/decoding. Transports that work natively with structured data
   * (e.g. gRPC with protobuf) can override this method.
   *
   * Default implementation encodes to JSON for backward compatibility.
   *
   * @param envelope Envelope dictionary to send
   * @throws ConnectionError if send fails
   */
  async sendFramedEnvelope(envelope: ProtocolEnvelope): Promise<void> {
    const data = encodeBytes(envelope);
    await this.sendFramed(data);
  }

  /**
   * Receive envelope dictionary directly (fast path for gRPC/protobuf).
   *
   * This is an optional optimization that allows transports to skip JSON
   * encoding/decoding. Transports that work natively with structured data
   * (e.g. gRPC with protobuf) can override this method.
   *
   * Default implementation decodes from JSON for backward compatibility.
   *
   * @returns Envelope dictionary
   * @throws ConnectionError if receive fails
   * @throws MalformedPayloadError if data cannot be decoded
   */
  async receiveFramedEnvelope(): Promise<ProtocolEnvelope> {
    const data = await this.receiveFramed();
    return decodeBytes(data);
  }
}

/**
 * Parse endpoint string and return appropriate transport type.
 *
 * Supported formats:
 *   - tcp://host:port -> TCP Transport
 *   - http://host:port -> HTTP Transport
 *   - https://host:port -> HTTPS Transport
 *   - ws://host:port -> WebSocket Transport
 *   - wss://host:port -> WebSocket Secure Transport
 *   - grpc://host:port -> gRPC Transport (insecure, for local testing)
 *   - grpcs://host:port -> gRPC Transport with TLS (for production)
 *
 * @param endpoint Endpoint string
 * @returns Transport instance
 * @throws Error if endpoint format is unsupported
 */
export function parseEndpoint(endpoint: string): Transport {
  if (endpoint.startsWith('tcp://')) {
    const { TCPTransport } = require('./tcp');
    const tcpPart = endpoint.slice(6);
    const colonIdx = tcpPart.lastIndexOf(':');
    if (colonIdx === -1) {
      throw new Error(`Invalid TCP endpoint format: ${endpoint}`);
    }
    const host = tcpPart.slice(0, colonIdx);
    const port = parseInt(tcpPart.slice(colonIdx + 1), 10);
    if (isNaN(port) || port <= 0 || port > 65535) {
      throw new Error(`Invalid port in TCP endpoint: ${endpoint}`);
    }
    return new TCPTransport(host, port);
  }

  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
    const { HTTPTransport } = require('./http');
    return new HTTPTransport({ baseUrl: endpoint });
  }

  if (endpoint.startsWith('ws://') || endpoint.startsWith('wss://')) {
    const { WebSocketAgent } = require('./websocket');
    return new WebSocketAgent({ url: endpoint });
  }

  if (endpoint.startsWith('grpc://') || endpoint.startsWith('grpcs://')) {
    const { GRPCTransport } = require('./grpc-transport');
    return new GRPCTransport(endpoint);
  }

  throw new Error(`Unsupported endpoint format: ${endpoint}`);
}
