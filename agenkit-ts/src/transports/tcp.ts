/**
 * TCP socket transport implementation.
 *
 * Provides transport layer over TCP sockets for agent communication.
 */

import { Socket } from 'net';
import { Transport } from './transport';
import { ConnectionError, ConnectionClosedError } from './errors';

/**
 * TCP socket transport.
 */
export class TCPTransport extends Transport {
  private host: string;
  private port: number;
  private socket: Socket | null = null;
  private connected = false;
  private receiveBuffer: Buffer = Buffer.alloc(0);

  constructor(host: string, port: number) {
    super();
    this.host = host;
    this.port = port;
  }

  /**
   * Connect to TCP socket.
   *
   * @throws ConnectionError if connection fails
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new Socket();

        this.socket.on('connect', () => {
          this.connected = true;
          resolve();
        });

        this.socket.on('error', (error) => {
          if (!this.connected) {
            reject(
              new ConnectionError(
                `Failed to connect to ${this.host}:${this.port}: ${error.message}`,
              ),
            );
          }
        });

        this.socket.on('close', () => {
          this.connected = false;
          this.socket = null;
        });

        // Setup data handler for buffering. The 'data' event payload is typed
        // string | Buffer; normalize to Buffer before concatenating.
        this.socket.on('data', (data: Buffer | string) => {
          const chunk = typeof data === 'string' ? Buffer.from(data) : data;
          this.receiveBuffer = Buffer.concat([this.receiveBuffer, chunk]);
        });

        this.socket.connect(this.port, this.host);
      } catch (error) {
        reject(
          new ConnectionError(
            `Failed to connect: ${error instanceof Error ? error.message : String(error)}`,
          ),
        );
      }
    });
  }

  /**
   * Send data over TCP socket.
   *
   * @param data Bytes to send
   * @throws ConnectionError if not connected or send fails
   */
  async send(data: Buffer): Promise<void> {
    if (!this.isConnected || !this.socket) {
      throw new ConnectionError('Not connected');
    }

    return new Promise((resolve, reject) => {
      this.socket!.write(data, (error) => {
        if (error) {
          reject(new ConnectionError(`Failed to send data: ${error.message}`));
        } else {
          resolve();
        }
      });
    });
  }

  /**
   * Receive data from TCP socket.
   *
   * @returns Received bytes (up to 64KB)
   * @throws ConnectionError if not connected or receive fails
   * @throws ConnectionClosedError if connection is closed
   */
  async receive(): Promise<Buffer> {
    if (!this.isConnected || !this.socket) {
      throw new ConnectionError('Not connected');
    }

    // Wait for data in buffer
    while (this.receiveBuffer.length === 0) {
      await new Promise((resolve) => setTimeout(resolve, 10));
      if (!this.isConnected) {
        throw new ConnectionClosedError('Connection closed by peer');
      }
    }

    // Return up to 64KB
    const bytesToReturn = Math.min(this.receiveBuffer.length, 65536);
    const data = this.receiveBuffer.subarray(0, bytesToReturn);
    this.receiveBuffer = this.receiveBuffer.subarray(bytesToReturn);

    return data;
  }

  /**
   * Receive exactly n bytes from TCP socket.
   *
   * @param n Number of bytes to receive
   * @returns Exactly n bytes
   * @throws ConnectionError if not connected or receive fails
   * @throws ConnectionClosedError if connection closes before receiving all bytes
   */
  async receiveExactly(n: number): Promise<Buffer> {
    if (!this.isConnected || !this.socket) {
      throw new ConnectionError('Not connected');
    }

    // Wait until we have enough bytes in buffer
    while (this.receiveBuffer.length < n) {
      await new Promise((resolve) => setTimeout(resolve, 10));
      if (!this.isConnected) {
        throw new ConnectionClosedError(
          `Connection closed while expecting ${n - this.receiveBuffer.length} more bytes`,
        );
      }
    }

    // Extract exactly n bytes
    const data = this.receiveBuffer.subarray(0, n);
    this.receiveBuffer = this.receiveBuffer.subarray(n);

    return data;
  }

  /**
   * Close TCP socket connection.
   */
  async close(): Promise<void> {
    if (this.socket) {
      return new Promise((resolve) => {
        this.socket!.once('close', () => {
          this.socket = null;
          this.connected = false;
          resolve();
        });
        this.socket!.destroy();
      });
    }
  }

  /**
   * Check if TCP socket is connected.
   *
   * @returns true if connected, false otherwise
   */
  get isConnected(): boolean {
    return this.connected && this.socket !== null && !this.socket.destroyed;
  }
}
