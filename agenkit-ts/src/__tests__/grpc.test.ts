/**
 * Tests for gRPC transport.
 */

import { GrpcAgent, GrpcServer, GrpcTransportError, createMessage } from '../index';
import * as grpc from '@grpc/grpc-js';

// Mock agent for testing
const createMockAgent = () => ({
  name: 'test-agent',
  async process(message: any) {
    return {
      role: 'assistant',
      content: `Echo: ${message.content}`,
      metadata: message.metadata || {},
    };
  },
  async *processStream(message: any) {
    yield { role: 'assistant', content: 'Chunk 1', metadata: {} };
    yield { role: 'assistant', content: 'Chunk 2', metadata: {} };
  },
});

// None of the tests below ever bind a real listening socket for this
// address — the client is either never connected, or is expected to fail
// because no server is running. Port 0 keeps that intent honest (no real
// port is ever claimed) instead of hardcoding an arbitrary literal that
// reads as if it mattered.
const UNUSED_ADDRESS = 'localhost:0';

describe('GrpcAgent', () => {
  it('should create gRPC agent with default config', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    expect(agent.name).toBe('test-agent');
  });

  it('should create gRPC agent with custom timeout', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
      timeout: 5000,
    });

    expect(agent.name).toBe('test-agent');
  });

  it('should create gRPC agent with TLS disabled', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
      useTLS: false,
    });

    expect(agent.name).toBe('test-agent');
  });

  it('should create gRPC agent with agent name for routing', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
      agentName: 'my-agent',
    });

    expect(agent.name).toBe('test-agent');
  });

  it('should handle connection lifecycle', async () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    // Should be able to connect
    await expect(agent.connect()).resolves.not.toThrow();

    // Should be able to close
    await expect(agent.close()).resolves.not.toThrow();
  });

  it('should auto-connect if not connected', async () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    // Process should auto-connect (will fail due to no server, but should not throw connection error)
    try {
      await agent.process(createMessage('user', 'Hello'));
    } catch (error) {
      // Expected to fail since no server is running
      expect(error).toBeDefined();
    }
  });

  it('should generate unique request IDs', async () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    const id1 = (agent as any).generateId();
    const id2 = (agent as any).generateId();

    expect(id1).not.toBe(id2);
    expect(id1).toMatch(/^\d+-[a-z0-9]+$/);
  });

  it('should convert message to proto format', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    const message = createMessage('user', 'Hello');
    const proto = (agent as any).messageToProto(message);

    expect(proto.role).toBe('user');
    expect(proto.content).toBe('Hello');
    expect(proto.metadata).toBeDefined();
    expect(proto.timestamp).toBeDefined();
  });

  it('should convert proto to message format', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    const proto = {
      role: 'assistant',
      content: 'Hello!',
      metadata: { test: 'value' },
    };

    const message = (agent as any).protoToMessage(proto);

    expect(message.role).toBe('assistant');
    expect(message.content).toBe('Hello!');
    expect(message.metadata).toEqual({ test: 'value' });
  });

  it('should handle empty metadata', () => {
    const agent = new GrpcAgent('test-agent', {
      address: UNUSED_ADDRESS,
    });

    const proto = {
      role: 'assistant',
      content: 'Hello!',
      metadata: null,
    };

    const message = (agent as any).protoToMessage(proto);

    expect(message.metadata).toEqual({});
  });
});

describe('GrpcServer', () => {
  it('should create gRPC server with agent', () => {
    const mockAgent = createMockAgent();
    const server = new GrpcServer(mockAgent, {
      address: '0.0.0.0:0',
    });

    expect(server).toBeDefined();
  });

  it('should create gRPC server with TLS disabled', () => {
    const mockAgent = createMockAgent();
    const server = new GrpcServer(mockAgent, {
      address: '0.0.0.0:0',
      useTLS: false,
    });

    expect(server).toBeDefined();
  });

  it('should start and stop server', async () => {
    const mockAgent = createMockAgent();
    // Bind an ephemeral port (:0) and let the OS pick a free one. Hardcoded
    // ports collide across parallel CI runs/workers (see #881, mirroring the
    // Go fix in #621), so every server in this file uses dynamic allocation.
    const server = new GrpcServer(mockAgent, {
      address: '127.0.0.1:0',
    });

    // Start server
    await expect(server.start()).resolves.not.toThrow();

    // Stop server
    await expect(server.stop()).resolves.not.toThrow();
  }, 10000); // Longer timeout for server operations

  it('should handle process requests', async () => {
    const mockAgent = createMockAgent();
    const server = new GrpcServer(mockAgent, {
      address: '127.0.0.1:0',
    });

    await server.start();

    // Create client to test, using the port the OS actually assigned.
    const client = new GrpcAgent('test-client', {
      address: server.address(),
    });

    try {
      const response = await client.process(createMessage('user', 'Hello'));
      expect(response.role).toBe('assistant');
      expect(response.content).toContain('Echo:');
    } finally {
      await server.stop();
      await client.close();
    }
  }, 15000);

  it('should handle streaming requests', async () => {
    const mockAgent = createMockAgent();
    const server = new GrpcServer(mockAgent, {
      address: '127.0.0.1:0',
    });

    await server.start();

    const client = new GrpcAgent('test-client', {
      address: server.address(),
    });

    try {
      const chunks: any[] = [];
      for await (const chunk of client.processStream(createMessage('user', 'Stream'))) {
        chunks.push(chunk);
      }

      expect(chunks.length).toBeGreaterThan(0);
      expect(chunks[0].role).toBe('assistant');
    } finally {
      await server.stop();
      await client.close();
    }
  }, 15000);

  it('should handle errors gracefully', async () => {
    const errorAgent = {
      name: 'error-agent',
      async process() {
        throw new Error('Intentional error');
      },
    };

    const server = new GrpcServer(errorAgent, {
      address: '127.0.0.1:0',
    });

    await server.start();

    const client = new GrpcAgent('test-client', {
      address: server.address(),
    });

    try {
      await expect(client.process(createMessage('user', 'Hello'))).rejects.toThrow();
    } finally {
      await server.stop();
      await client.close();
    }
  }, 15000);

  it('should handle non-streaming agents', async () => {
    const nonStreamingAgent = {
      name: 'non-streaming',
      async process(message: any) {
        return {
          role: 'assistant',
          content: `Response: ${message.content}`,
          metadata: {},
        };
      },
      // No processStream method
    };

    const server = new GrpcServer(nonStreamingAgent, {
      address: '127.0.0.1:0',
    });

    await server.start();

    const client = new GrpcAgent('test-client', {
      address: server.address(),
    });

    try {
      const chunks: any[] = [];
      for await (const chunk of client.processStream(createMessage('user', 'Test'))) {
        chunks.push(chunk);
      }

      // Should fall back to regular process
      expect(chunks.length).toBe(1);
      expect(chunks[0].content).toContain('Response:');
    } finally {
      await server.stop();
      await client.close();
    }
  }, 15000);

  it('should convert message formats correctly', () => {
    const mockAgent = createMockAgent();
    const server = new GrpcServer(mockAgent, {
      address: '0.0.0.0:0',
    });

    const message = createMessage('user', 'Test');
    const proto = (server as any).messageToProto(message);

    expect(proto.role).toBe('user');
    expect(proto.content).toBe('Test');
    expect(proto.timestamp).toBeDefined();

    const converted = (server as any).protoToMessage(proto);
    expect(converted.role).toBe('user');
    expect(converted.content).toBe('Test');
  });
});

describe('GrpcTransportError', () => {
  it('should create error with code and message', () => {
    const error = new GrpcTransportError('Test error', grpc.status.INTERNAL);

    expect(error.message).toBe('Test error');
    expect(error.code).toBe(grpc.status.INTERNAL);
    expect(error.name).toBe('GrpcTransportError');
  });

  it('should create error with details', () => {
    const error = new GrpcTransportError('Test error', grpc.status.INTERNAL, {
      key: 'value',
    });

    expect(error.details).toEqual({ key: 'value' });
  });

  it('should be instance of Error', () => {
    const error = new GrpcTransportError('Test', grpc.status.UNKNOWN);

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(GrpcTransportError);
  });
});
