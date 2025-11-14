/**
 * Tests for LocalAgent adapter.
 */

import { LocalAgent, createMessage, createEchoAgent, createCounterAgent } from '../index';

describe('LocalAgent', () => {
  describe('basic functionality', () => {
    it('should process a simple message', async () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async (msg) => createMessage('assistant', `Received: ${msg.content}`),
      });

      const response = await agent.process(createMessage('user', 'Hello'));

      expect(response.role).toBe('assistant');
      expect(response.content).toBe('Received: Hello');
      expect(response.timestamp).toBeDefined();
    });

    it('should validate agent name', () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      expect(agent.name).toBe('test');
    });

    it('should add timestamp to messages without one', async () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      const message = { role: 'user', content: 'Hello' };
      const response = await agent.process(message);

      expect(message.timestamp).toBeDefined();
      expect(response.timestamp).toBeDefined();
    });

    it('should preserve message timestamps', async () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async (msg) => ({
          role: 'assistant',
          content: msg.content,
          timestamp: '2025-01-01T00:00:00.000Z',
        }),
      });

      const response = await agent.process(createMessage('user', 'Hello'));

      expect(response.timestamp).toBe('2025-01-01T00:00:00.000Z');
    });
  });

  describe('echo agent', () => {
    it('should echo messages', async () => {
      const agent = createEchoAgent('echo-test');

      const response = await agent.process(createMessage('user', 'Test message'));

      expect(response.role).toBe('assistant');
      expect(response.content).toBe('Echo: Test message');
      expect(agent.name).toBe('echo-test');
      expect(agent.capabilities).toContain('echo');
    });
  });

  describe('counter agent', () => {
    it('should count messages', async () => {
      const agent = createCounterAgent('counter-test');

      const response1 = await agent.process(createMessage('user', 'First'));
      expect(response1.content).toBe('Message 1: First');
      expect(response1.metadata?.count).toBe(1);

      const response2 = await agent.process(createMessage('user', 'Second'));
      expect(response2.content).toBe('Message 2: Second');
      expect(response2.metadata?.count).toBe(2);

      const response3 = await agent.process(createMessage('user', 'Third'));
      expect(response3.content).toBe('Message 3: Third');
      expect(response3.metadata?.count).toBe(3);
    });
  });

  describe('streaming', () => {
    it('should support streaming', async () => {
      const agent = new LocalAgent({
        name: 'streaming-test',
        process: async (msg) => createMessage('assistant', msg.content),
        processStream: async function* (msg) {
          const content = String(msg.content);
          for (const char of content) {
            yield createMessage('assistant', char);
          }
        },
      });

      const chunks: string[] = [];
      for await (const chunk of agent.processStream!(createMessage('user', 'Hello'))) {
        chunks.push(String(chunk.content));
      }

      expect(chunks).toEqual(['H', 'e', 'l', 'l', 'o']);
    });

    it('should throw error if streaming not supported', async () => {
      const agent = new LocalAgent({
        name: 'no-stream',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      await expect(async () => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        for await (const _chunk of agent.processStream!(createMessage('user', 'Hello'))) {
          // Should not reach here
        }
      }).rejects.toThrow('does not support streaming');
    });
  });

  describe('error handling', () => {
    it('should propagate errors from process function', async () => {
      const agent = new LocalAgent({
        name: 'error-test',
        process: async () => {
          throw new Error('Processing failed');
        },
      });

      await expect(agent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        'Processing failed',
      );
    });

    it('should validate input messages', async () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async (msg) => createMessage('assistant', msg.content),
      });

      await expect(
        agent.process({ role: '', content: 'Hello' }),
      ).rejects.toThrow('Message role must be a non-empty string');

      await expect(
        agent.process({ role: 'user', content: null } as any),
      ).rejects.toThrow('Message content cannot be undefined or null');
    });

    it('should validate output messages', async () => {
      const agent = new LocalAgent({
        name: 'test',
        process: async () => ({ role: '', content: 'Hello' }),
      });

      await expect(agent.process(createMessage('user', 'Hello'))).rejects.toThrow(
        'Message role must be a non-empty string',
      );
    });
  });
});
