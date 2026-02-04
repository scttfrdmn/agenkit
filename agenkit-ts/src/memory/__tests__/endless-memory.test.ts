/**
 * Tests for EndlessMemory integration.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Message } from '../../core/interfaces';
import { EndlessMemory, EndlessClient } from '../endless-memory';

/**
 * Mock endless client for testing.
 */
class MockEndlessClient implements EndlessClient {
  private storage: Map<string, Array<Record<string, unknown>>> = new Map();

  async storeContext(
    sessionId: string,
    messages: Array<Record<string, unknown>>,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    const existing = this.storage.get(sessionId) || [];
    this.storage.set(sessionId, [...existing, ...messages]);
  }

  async retrieveContext(
    sessionId: string,
    query?: string,
    limit: number = 10
  ): Promise<Array<Record<string, unknown>>> {
    const messages = this.storage.get(sessionId) || [];

    // Simple query filtering (mock semantic search)
    let results = messages;
    if (query) {
      results = messages.filter((msg) =>
        (msg.content as string)?.toLowerCase().includes(query.toLowerCase())
      );
    }

    return results.slice(-limit);
  }

  async summarizeContext(sessionId: string): Promise<string> {
    const messages = this.storage.get(sessionId) || [];
    return `Summary of ${messages.length} messages in session ${sessionId}`;
  }

  async clearContext(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }
}

describe('EndlessMemory', () => {
  let client: MockEndlessClient;
  let memory: EndlessMemory;
  const sessionId = 'test-session-123';

  beforeEach(() => {
    client = new MockEndlessClient();
    memory = new EndlessMemory(client);
  });

  describe('constructor', () => {
    it('should create EndlessMemory with client', () => {
      expect(memory).toBeInstanceOf(EndlessMemory);
      expect(memory.capabilities).toContain('infinite_context');
    });
  });

  describe('store', () => {
    it('should store message in endless context', async () => {
      const message: Message = { role: 'user', content: 'Hello world' };

      await memory.store(sessionId, message);

      const retrieved = await memory.retrieve(sessionId);
      expect(retrieved).toHaveLength(1);
      expect(retrieved[0].content).toBe('Hello world');
    });

    it('should store message with metadata', async () => {
      const message: Message = { role: 'user', content: 'Important message' };
      const metadata = { importance: 'high', tags: ['critical'] };

      await memory.store(sessionId, message, metadata);

      const retrieved = await memory.retrieve(sessionId);
      expect(retrieved).toHaveLength(1);
    });

    it('should store multiple messages', async () => {
      await memory.store(sessionId, { role: 'user', content: 'Message 1' });
      await memory.store(sessionId, { role: 'assistant', content: 'Response 1' });
      await memory.store(sessionId, { role: 'user', content: 'Message 2' });

      const retrieved = await memory.retrieve(sessionId);
      expect(retrieved).toHaveLength(3);
    });
  });

  describe('retrieve', () => {
    beforeEach(async () => {
      await memory.store(sessionId, { role: 'user', content: 'What is pricing?' });
      await memory.store(sessionId, { role: 'assistant', content: 'Our pricing starts at $10/month' });
      await memory.store(sessionId, { role: 'user', content: 'Tell me about features' });
      await memory.store(sessionId, { role: 'assistant', content: 'We have many features' });
    });

    it('should retrieve all messages by default', async () => {
      const messages = await memory.retrieve(sessionId);
      expect(messages).toHaveLength(4);
    });

    it('should retrieve with limit', async () => {
      const messages = await memory.retrieve(sessionId, { limit: 2 });
      expect(messages).toHaveLength(2);
      expect(messages[0].content).toBe('Tell me about features');
      expect(messages[1].content).toBe('We have many features');
    });

    it('should support semantic query (mock)', async () => {
      const messages = await memory.retrieve(sessionId, {
        query: 'pricing',
      });

      expect(messages.length).toBeGreaterThan(0);
      expect(
        messages.some((m) => (m.content as string).toLowerCase().includes('pricing'))
      ).toBe(true);
    });

    it('should return empty array for non-existent session', async () => {
      const messages = await memory.retrieve('non-existent-session');
      expect(messages).toHaveLength(0);
    });
  });

  describe('summarize', () => {
    beforeEach(async () => {
      await memory.store(sessionId, { role: 'user', content: 'Hello' });
      await memory.store(sessionId, { role: 'assistant', content: 'Hi there' });
    });

    it('should return summary message', async () => {
      const summary = await memory.summarize(sessionId);

      expect(summary.role).toBe('system');
      expect(summary.content).toContain('Summary');
      expect(summary.content).toContain(sessionId);
    });
  });

  describe('clear', () => {
    beforeEach(async () => {
      await memory.store(sessionId, { role: 'user', content: 'Test' });
    });

    it('should clear all messages for session', async () => {
      let messages = await memory.retrieve(sessionId);
      expect(messages).toHaveLength(1);

      await memory.clear(sessionId);

      messages = await memory.retrieve(sessionId);
      expect(messages).toHaveLength(0);
    });

    it('should not affect other sessions', async () => {
      const otherSession = 'other-session';
      await memory.store(otherSession, { role: 'user', content: 'Other' });

      await memory.clear(sessionId);

      const otherMessages = await memory.retrieve(otherSession);
      expect(otherMessages).toHaveLength(1);
    });
  });

  describe('capabilities', () => {
    it('should list all capabilities', () => {
      const caps = memory.capabilities;

      expect(caps).toContain('infinite_context');
      expect(caps).toContain('compression');
      expect(caps).toContain('semantic_search');
      expect(caps).toContain('cross_session_knowledge');
      expect(caps).toContain('automatic_summarization');
    });
  });

  describe('integration scenarios', () => {
    it('should handle very long conversations', async () => {
      // Simulate 100 message conversation
      for (let i = 0; i < 100; i++) {
        await memory.store(
          sessionId,
          { role: i % 2 === 0 ? 'user' : 'assistant', content: `Message ${i}` }
        );
      }

      const allMessages = await memory.retrieve(sessionId, { limit: 100 });
      expect(allMessages).toHaveLength(100);

      const recentMessages = await memory.retrieve(sessionId, { limit: 5 });
      expect(recentMessages).toHaveLength(5);
    });

    it('should support cross-session retrieval pattern', async () => {
      const session1 = 'session-1';
      const session2 = 'session-2';

      await memory.store(session1, { role: 'user', content: 'Session 1 message' });
      await memory.store(session2, { role: 'user', content: 'Session 2 message' });

      const messages1 = await memory.retrieve(session1);
      const messages2 = await memory.retrieve(session2);

      expect(messages1).toHaveLength(1);
      expect(messages2).toHaveLength(1);
      expect(messages1[0].content).not.toBe(messages2[0].content);
    });
  });
});
