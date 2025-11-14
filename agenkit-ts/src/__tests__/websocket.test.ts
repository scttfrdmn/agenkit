/**
 * Tests for WebSocket transport.
 *
 * Note: These are basic unit tests. Full integration tests would require
 * a WebSocket server implementation.
 */

import { WebSocketAgent, WebSocketTransportError, createMessage } from '../index';

describe('WebSocketAgent', () => {
  it('should create WebSocket agent with default config', () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
    });

    expect(agent.name).toBe('websocket-agent');
    expect(agent.capabilities).toContain('websocket');
  });

  it('should create WebSocket agent with custom name', () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
      name: 'my-ws-agent',
    });

    expect(agent.name).toBe('my-ws-agent');
  });

  it('should accept wss:// URLs', () => {
    const agent = new WebSocketAgent({
      url: 'wss://secure.example.com',
    });

    expect(agent).toBeDefined();
  });

  it('should accept custom retry configuration', () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
      maxRetries: 10,
      initialRetryDelay: 500,
    });

    expect(agent).toBeDefined();
  });

  it('should accept custom ping configuration', () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
      pingInterval: 60000,
      pingTimeout: 20000,
    });

    expect(agent).toBeDefined();
  });

  it('should accept custom headers', () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
      headers: {
        'Authorization': 'Bearer token123',
        'X-Custom-Header': 'value',
      },
    });

    expect(agent).toBeDefined();
  });

  it('should report not connected initially', () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
    });

    expect(agent.isConnected).toBe(false);
  });

  it('should fail health check when not connected', async () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
    });

    const healthy = await agent.health();
    expect(healthy).toBe(false);
  });

  it('should throw error when processing without connection', async () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:9999', // Non-existent server
      maxRetries: 1,
      initialRetryDelay: 10,
    });

    await expect(
      agent.process(createMessage('user', 'Hello'))
    ).rejects.toThrow(WebSocketTransportError);
  });

  it('should validate messages before processing', async () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
    });

    const invalidMessage = { role: '', content: 'test' };

    await expect(
      agent.process(invalidMessage as any)
    ).rejects.toThrow();
  });

  it('should add timestamp if missing', async () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:9999',
      maxRetries: 1,
      initialRetryDelay: 10,
    });

    const message = createMessage('user', 'Hello');
    delete message.timestamp;

    // Will fail to connect, but should add timestamp before that
    try {
      await agent.process(message);
    } catch (error) {
      // Expected to fail
    }

    // Message should have timestamp added
    expect(message.timestamp).toBeDefined();
  });

  it('should allow manual close', async () => {
    const agent = new WebSocketAgent({
      url: 'ws://localhost:8080',
    });

    await agent.close();
    expect(agent.isConnected).toBe(false);
  });
});
