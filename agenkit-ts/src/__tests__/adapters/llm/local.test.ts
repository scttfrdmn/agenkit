/**
 * Tests for Local adapter.
 *
 * Tests local function-based agents without external API dependencies.
 */

import { describe, it, expect } from 'vitest';
import { LocalAgent, createEchoAgent, createCounterAgent } from '../../../adapters/local';
import type { Message } from '../../../core/interfaces';
import { createMessage } from '../../../core/interfaces';

// ============================================
// Basic LocalAgent Tests
// ============================================

describe('LocalAgent: Basic Functionality', () => {
  it('should create agent with name', () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => createMessage('assistant', `Processed: ${msg.content}`),
    });

    expect(agent.name).toBe('test-agent');
  });

  it('should process message through function', async () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => createMessage('assistant', `Processed: ${msg.content}`),
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };
    const response = await agent.process(input);

    expect(response.role).toBe('assistant');
    expect(response.content).toBe('Processed: Hello');
  });

  it('should add timestamp if missing', async () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };
    const response = await agent.process(input);

    expect(response.timestamp).toBeDefined();
    expect(typeof response.timestamp).toBe('string');
  });

  it('should validate input message', async () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
    });

    // Invalid message (missing required fields)
    const invalidInput = { content: 'Hello' } as Message;

    await expect(agent.process(invalidInput)).rejects.toThrow();
  });

  it('should validate output message', async () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async () => ({ invalid: 'message' }) as any,
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    await expect(agent.process(input)).rejects.toThrow();
  });

  it('should support capabilities', () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
      capabilities: ['echo', 'transform'],
    });

    expect(agent.capabilities).toEqual(['echo', 'transform']);
  });
});

// ============================================
// Streaming Tests
// ============================================

describe('LocalAgent: Streaming', () => {
  it('should stream chunks through generator', async () => {
    const agent = new LocalAgent({
      name: 'streaming-agent',
      process: async (msg) => createMessage('assistant', 'Non-streaming response'),
      processStream: async function* (msg) {
        const words = (msg.content as string).split(' ');
        for (const word of words) {
          yield createMessage('assistant', word, { chunk: true });
        }
      },
    });

    const input: Message = { role: 'user', content: 'Hello world test', metadata: {} };
    const chunks: string[] = [];

    for await (const chunk of agent.processStream(input)) {
      chunks.push(chunk.content as string);
      expect(chunk.role).toBe('assistant');
      expect(chunk.metadata.chunk).toBe(true);
    }

    expect(chunks).toEqual(['Hello', 'world', 'test']);
  });

  it('should throw error if streaming not supported', async () => {
    const agent = new LocalAgent({
      name: 'non-streaming-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const chunk of agent.processStream(input)) {
        // Should not reach here
      }
    }).rejects.toThrow('does not support streaming');
  });

  it('should add timestamps to chunks', async () => {
    const agent = new LocalAgent({
      name: 'streaming-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
      processStream: async function* (msg) {
        yield createMessage('assistant', 'Chunk 1');
        yield createMessage('assistant', 'Chunk 2');
      },
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    for await (const chunk of agent.processStream(input)) {
      expect(chunk.timestamp).toBeDefined();
      expect(typeof chunk.timestamp).toBe('string');
    }
  });

  it('should validate streamed chunks', async () => {
    const agent = new LocalAgent({
      name: 'streaming-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
      processStream: async function* (msg) {
        yield { invalid: 'chunk' } as any;
      },
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const chunk of agent.processStream(input)) {
        // Should throw before reaching here
      }
    }).rejects.toThrow();
  });
});

// ============================================
// Helper Functions Tests
// ============================================

describe('LocalAgent: Helper Functions', () => {
  it('should create echo agent', async () => {
    const agent = createEchoAgent();

    expect(agent.name).toBe('echo');
    expect(agent.capabilities).toContain('echo');

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };
    const response = await agent.process(input);

    expect(response.content).toBe('Echo: Hello');
  });

  it('should create echo agent with custom name', async () => {
    const agent = createEchoAgent('custom-echo');

    expect(agent.name).toBe('custom-echo');
  });

  it('should create counter agent', async () => {
    const agent = createCounterAgent();

    expect(agent.name).toBe('counter');
    expect(agent.capabilities).toContain('counter');
  });

  it('should increment counter on each message', async () => {
    const agent = createCounterAgent();

    const input: Message = { role: 'user', content: 'Test', metadata: {} };

    const response1 = await agent.process(input);
    expect(response1.content).toBe('Message 1: Test');
    expect(response1.metadata.count).toBe(1);

    const response2 = await agent.process(input);
    expect(response2.content).toBe('Message 2: Test');
    expect(response2.metadata.count).toBe(2);

    const response3 = await agent.process(input);
    expect(response3.content).toBe('Message 3: Test');
    expect(response3.metadata.count).toBe(3);
  });

  it('should create counter agent with custom name', async () => {
    const agent = createCounterAgent('custom-counter');

    expect(agent.name).toBe('custom-counter');
  });
});

// ============================================
// Error Handling Tests
// ============================================

describe('LocalAgent: Error Handling', () => {
  it('should propagate errors from process function', async () => {
    const agent = new LocalAgent({
      name: 'error-agent',
      process: async () => {
        throw new Error('Processing failed');
      },
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    await expect(agent.process(input)).rejects.toThrow('Processing failed');
  });

  it('should propagate errors from stream function', async () => {
    const agent = new LocalAgent({
      name: 'error-agent',
      process: async (msg) => createMessage('assistant', 'Response'),
      processStream: async function* () {
        throw new Error('Streaming failed');
      },
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const chunk of agent.processStream(input)) {
        // Should not reach here
      }
    }).rejects.toThrow('Streaming failed');
  });

  it('should handle async errors in process function', async () => {
    const agent = new LocalAgent({
      name: 'async-error-agent',
      process: async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
        throw new Error('Async processing failed');
      },
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };

    await expect(agent.process(input)).rejects.toThrow('Async processing failed');
  });
});

// ============================================
// Metadata Preservation Tests
// ============================================

describe('LocalAgent: Metadata', () => {
  it('should preserve input metadata', async () => {
    let capturedInput: Message | null = null;

    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => {
        capturedInput = msg;
        return createMessage('assistant', 'Response');
      },
    });

    const input: Message = {
      role: 'user',
      content: 'Hello',
      metadata: { sessionId: '123', userId: 'alice' },
    };

    await agent.process(input);

    expect(capturedInput?.metadata.sessionId).toBe('123');
    expect(capturedInput?.metadata.userId).toBe('alice');
  });

  it('should allow adding metadata in response', async () => {
    const agent = new LocalAgent({
      name: 'test-agent',
      process: async (msg) => createMessage('assistant', 'Response', { processed: true }),
    });

    const input: Message = { role: 'user', content: 'Hello', metadata: {} };
    const response = await agent.process(input);

    expect(response.metadata.processed).toBe(true);
  });
});
