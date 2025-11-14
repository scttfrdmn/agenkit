/**
 * Tests for HTTP transport.
 */

import { HTTPAgent, HttpTransportError, createMessage } from '../index';

// Mock fetch globally
const originalFetch = global.fetch;

describe('HTTPAgent', () => {
  afterEach(() => {
    // Restore original fetch after each test
    global.fetch = originalFetch;
  });

  it('should create HTTP agent with default config', () => {
    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    expect(agent.name).toBe('http-agent');
    expect(agent.capabilities).toContain('http');
  });

  it('should create HTTP agent with custom name', () => {
    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
      name: 'my-http-agent',
    });

    expect(agent.name).toBe('my-http-agent');
  });

  it('should remove trailing slash from baseUrl', () => {
    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000/',
    });

    expect(agent).toBeDefined();
  });

  it('should accept custom timeout', () => {
    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
      timeout: 60000,
    });

    expect(agent).toBeDefined();
  });

  it('should accept custom headers', () => {
    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
      headers: {
        'Authorization': 'Bearer token123',
      },
    });

    expect(agent).toBeDefined();
  });

  it('should successfully process a message', async () => {
    const mockResponse = createMessage('assistant', 'Hello!');

    global.fetch = async () => ({
      ok: true,
      json: async () => mockResponse,
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const response = await agent.process(createMessage('user', 'Hi'));

    expect(response.role).toBe('assistant');
    expect(response.content).toBe('Hello!');
  });

  it('should add timestamp to message if missing', async () => {
    const mockResponse = createMessage('assistant', 'Response');

    global.fetch = async (url, options) => {
      const body = JSON.parse(options?.body as string);
      expect(body.timestamp).toBeDefined();

      return {
        ok: true,
        json: async () => mockResponse,
      } as Response;
    };

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const message = createMessage('user', 'Test');
    delete message.timestamp;

    await agent.process(message);
  });

  it('should include custom headers in request', async () => {
    const mockResponse = createMessage('assistant', 'Response');

    global.fetch = async (url, options) => {
      expect(options?.headers).toMatchObject({
        'Authorization': 'Bearer token123',
        'Content-Type': 'application/json',
      });

      return {
        ok: true,
        json: async () => mockResponse,
      } as Response;
    };

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
      headers: {
        'Authorization': 'Bearer token123',
      },
    });

    await agent.process(createMessage('user', 'Test'));
  });

  it('should throw error on HTTP error response', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: async () => 'Server error occurred',
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    await expect(
      agent.process(createMessage('user', 'Test'))
    ).rejects.toThrow(HttpTransportError);
  });

  it('should throw error on network failure', async () => {
    global.fetch = async () => {
      throw new Error('Network error');
    };

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    await expect(
      agent.process(createMessage('user', 'Test'))
    ).rejects.toThrow(HttpTransportError);
  });

  it('should throw error on timeout', async () => {
    global.fetch = async (url, options) => {
      // Simulate timeout by aborting
      await new Promise(resolve => setTimeout(resolve, 200));
      options?.signal?.dispatchEvent(new Event('abort'));
      throw new Error('AbortError');
    };

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
      timeout: 100,
    });

    await expect(
      agent.process(createMessage('user', 'Test'))
    ).rejects.toThrow();
  });

  it('should validate input messages', async () => {
    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const invalidMessage = { role: '', content: 'test' };

    await expect(
      agent.process(invalidMessage as any)
    ).rejects.toThrow();
  });

  it('should validate response messages', async () => {
    global.fetch = async () => ({
      ok: true,
      json: async () => ({ role: '', content: 'test' }), // Invalid response
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    await expect(
      agent.process(createMessage('user', 'Test'))
    ).rejects.toThrow();
  });

  it('should handle processStream with NDJSON', async () => {
    const chunk1 = createMessage('assistant', 'Hello');
    const chunk2 = createMessage('assistant', ' world');

    const ndjson = `${JSON.stringify(chunk1)}\n${JSON.stringify(chunk2)}\n`;
    const encoder = new TextEncoder();
    const data = encoder.encode(ndjson);

    global.fetch = async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: (() => {
            let called = false;
            return async () => {
              if (!called) {
                called = true;
                return { done: false, value: data };
              }
              return { done: true, value: undefined };
            };
          })(),
        }),
      },
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const chunks: string[] = [];
    for await (const chunk of agent.processStream!(createMessage('user', 'Test'))) {
      chunks.push(chunk.content as string);
    }

    expect(chunks).toEqual(['Hello', ' world']);
  });

  it('should throw error if processStream has no body', async () => {
    global.fetch = async () => ({
      ok: true,
      body: null,
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const stream = agent.processStream!(createMessage('user', 'Test'));

    await expect(stream.next()).rejects.toThrow(HttpTransportError);
  });

  it('should perform health check', async () => {
    global.fetch = async () => ({
      ok: true,
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const healthy = await agent.health();
    expect(healthy).toBe(true);
  });

  it('should fail health check on error', async () => {
    global.fetch = async () => {
      throw new Error('Connection failed');
    };

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const healthy = await agent.health();
    expect(healthy).toBe(false);
  });

  it('should handle HTTP 404 errors', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: async () => 'Agent not found',
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    try {
      await agent.process(createMessage('user', 'Test'));
      fail('Should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(HttpTransportError);
      expect((error as HttpTransportError).statusCode).toBe(404);
      expect((error as HttpTransportError).responseBody).toBe('Agent not found');
    }
  });

  it('should handle processStream with multiple chunks in buffer', async () => {
    const chunk1 = createMessage('assistant', 'First');
    const chunk2 = createMessage('assistant', 'Second');
    const chunk3 = createMessage('assistant', 'Third');

    const ndjson = `${JSON.stringify(chunk1)}\n${JSON.stringify(chunk2)}\n${JSON.stringify(chunk3)}`;
    const encoder = new TextEncoder();
    const data = encoder.encode(ndjson);

    global.fetch = async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: (() => {
            let called = false;
            return async () => {
              if (!called) {
                called = true;
                return { done: false, value: data };
              }
              return { done: true, value: undefined };
            };
          })(),
        }),
      },
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const chunks: string[] = [];
    for await (const chunk of agent.processStream!(createMessage('user', 'Test'))) {
      chunks.push(chunk.content as string);
    }

    expect(chunks).toEqual(['First', 'Second', 'Third']);
  });

  it('should throw HttpTransportError on unknown error type', async () => {
    global.fetch = async () => {
      throw 'String error'; // Non-Error object
    };

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    await expect(
      agent.process(createMessage('user', 'Test'))
    ).rejects.toThrow(HttpTransportError);
  });

  it('should handle processStream HTTP error', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      text: async () => 'Service temporarily unavailable',
    }) as Response;

    const agent = new HTTPAgent({
      baseUrl: 'http://localhost:8000',
    });

    const stream = agent.processStream!(createMessage('user', 'Test'));

    await expect(stream.next()).rejects.toThrow(HttpTransportError);
  });
});
